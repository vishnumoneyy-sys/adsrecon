"""Proxy Manager — DataImpulse residential proxy integration.

Manages a pool of rotating residential proxies from DataImpulse.
Each request can optionally use a geo-targeted proxy for accurate geo cloaking.

Docs: https://app.dataimpulse.com/docs
Auth format: http://user:pass@host:port
"""
import httpx
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("adsrecon.proxy")


@dataclass
class Proxy:
    """A single proxy endpoint with health metadata."""

    url: str
    geo: str
    working: bool = True
    last_checked: float = 0.0


class ProxyManager:
    """Manages DataImpulse residential proxy pool with geo-targeting support.

    Args:
        api_key: DataImpulse API key. If omitted the manager will only
                 return proxies from the pre-loaded local pool.
        local_pool: Optional list of pre-configured proxy URLs (used when no
                    API key is provided, e.g. in air-gapped environments).
    """

    DATAIMPULSE_ROTATE_URL = "https://app.dataimpulse.com/api/v1/rotate"
    HEALTHCHECK_URL = "https://httpbin.org/ip"
    REQUEST_TIMEOUT = 15.0  # seconds

    def __init__(
        self,
        api_key: str = "",
        local_pool: Optional[list[str]] = None,
        default_geo: str = "us",
    ):
        self.api_key = api_key.strip() if api_key else ""
        self.default_geo = default_geo
        self._local_pool: list[Proxy] = []
        self._current_local_index = 0

        if local_pool:
            for url in local_pool:
                self._local_pool.append(Proxy(url=url, geo="us", working=True))
            logger.info(f"Loaded {len(self._local_pool)} proxies into local pool")

    # --------------------------------------------------------------------- public API

    async def get_proxy(self, geo: str = "us") -> Optional[str]:
        """Return a proxy URL for the specified geo.

        Priority:
            1. DataImpulse API  → fresh rotating proxy (always preferred)
            2. Local pool       → round-robin fallback

        Args:
            geo: ISO country code (e.g. "us", "gb", "ca"). Passed to DataImpulse.

        Returns:
            Proxy URL string, or None if unavailable.
        """
        # Try DataImpulse first
        if self.api_key:
            proxy_url = await self._get_dataimpulse_proxy(geo)
            if proxy_url:
                return proxy_url
            logger.warning("DataImpulse returned no proxy; falling back to local pool")

        # Fallback to local pool (round-robin)
        return self._get_local_proxy()

    async def get_proxy_for_url(self, target_url: str) -> Optional[str]:
        """Return a geo-appropriate proxy for a given destination URL.

        Reads the domain TLD from target_url and maps it to a geo code.
        Falls back to default_geo if no mapping found.
        """
        import re

        # Extract country from common ccTLDs
        tld_match = re.search(r"\.([a-z]{2})(?:\/|$)", target_url)
        if tld_match:
            geo = tld_match.group(1)
        else:
            geo = self.default_geo

        return await self.get_proxy(geo=geo)

    async def check_proxy(self, proxy_url: str) -> bool:
        """Test whether a proxy is functional by connecting through it.

        Returns True if we can reach httpbin.org/ip through the proxy.
        """
        try:
            async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
                response = await client.get(
                    self.HEALTHCHECK_URL,
                    proxies={"http://": proxy_url, "https://": proxy_url},
                )
                ok = response.status_code == 200
                logger.debug(
                    f"Proxy {'OK' if ok else 'FAIL'} {proxy_url[:50]}: "
                    f"status={response.status_code}"
                )
                return ok
        except Exception as e:
            logger.debug(f"Proxy check failed for {proxy_url[:50]}: {e}")
            return False

    async def health_check_all(self) -> dict[str, bool]:
        """Check all proxies in the local pool and update their working flag.

        Returns:
            Dict mapping proxy URL → working status.
        """
        results = {}
        for proxy in self._local_pool:
            results[proxy.url] = await self.check_proxy(proxy.url)
            proxy.working = results[proxy.url]
            proxy.last_checked = 0.0  # callers should use time.time()
        logger.info(
            f"Proxy health check complete: "
            f"{sum(results.values())}/{len(results)} working"
        )
        return results

    # --------------------------------------------------------------------- internal

    async def _get_dataimpulse_proxy(self, geo: str = "us") -> Optional[str]:
        """Fetch a fresh rotating proxy from the DataImpulse API."""
        if not self.api_key:
            return None

        try:
            async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
                response = await client.get(
                    self.DATAIMPULSE_ROTATE_URL,
                    params={"geo": geo},
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )

                if response.status_code == 200:
                    data = response.json()
                    proxy_url = data.get("proxy_url") or data.get("proxy")
                    if proxy_url:
                        logger.info(f"DataImpulse proxy ({geo}): {proxy_url[:60]}")
                        return proxy_url
                elif response.status_code == 401:
                    logger.error("DataImpulse auth failed — check your API key")
                else:
                    logger.warning(
                        f"DataImpulse rotate returned {response.status_code}: "
                        f"{response.text[:100]}"
                    )

        except httpx.TimeoutException:
            logger.warning("DataImpulse API timed out")
        except Exception as e:
            logger.error(f"DataImpulse proxy fetch error: {e}", exc_info=True)

        return None

    def _get_local_proxy(self) -> Optional[str]:
        """Return the next proxy from the local pool using round-robin."""
        if not self._local_pool:
            return None

        attempts = 0
        while attempts < len(self._local_pool):
            proxy = self._local_pool[self._current_local_index]
            self._current_local_index = (self._current_local_index + 1) % len(self._local_pool)
            attempts += 1
            if proxy.working:
                logger.debug(f"Local proxy: {proxy.url}")
                return proxy.url

        logger.warning("All local proxies marked non-working")
        return None
