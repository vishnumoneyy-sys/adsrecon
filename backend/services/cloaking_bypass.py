"""Cloaking Bypass Service — the heart of ADSRECON.

The core innovation: cloaking in Facebook ad landing pages is primarily
fbclid-based, not IP-based. Most nutra/e-commerce landers check the fbclid
parameter to decide whether to show the real product page or a safe wall.

Strategy:
    1. Extract fbclid from the ad URL or redirect chain
    2. Reconstruct the "visited with fbclid" URL that Facebook's crawler sees
    3. Trace the full HTTP redirect chain to find the final destination
    4. Compare expected domain vs actual domain — mismatch = cloaking detected
    5. Fall back to Playwright browser rendering if JS redirects are suspected
    6. Only use residential proxy if IP-based cloaking is strongly suspected
       (expensive; ~10% of cases)

Result:
    For each ad, we return:
    - actual_url: the real lander URL (the nutra page itself)
    - is_cloaked: whether a cloak was detected and bypassed
    - cloak_type: domain_mismatch | redirect_chain | ip_based | none
    - redirect_chain: full hop-by-hop trace for analysis
"""
import asyncio
import logging
import re
import sys
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse, parse_qs, urlunparse, urlencode
from datetime import datetime

import httpx

# Disable SSL verification on Windows (cert store issues)
_HTTPX_VERIFY = False if sys.platform == "win32" else True

logger = logging.getLogger("adsrecon.cloaking")


# --------------------------------------------------------------------------- models


@dataclass
class CloakResult:
    """Structured result of a cloaking bypass attempt."""

    success: bool
    actual_url: str
    expected_domain: str
    actual_domain: str
    is_cloaked: bool                          # True = real lander found behind cloak
    cloak_type: str                           # "none" | "domain_mismatch" | "redirect_chain" | "ip_based"
    fbclid_used: str
    proxy_used: Optional[str]
    error: Optional[str]
    redirect_chain: list[str] = field(default_factory=list)
    method: str = "http"                       # "http" | "browser"
    duration_ms: float = 0.0


# --------------------------------------------------------------------------- helpers


def extract_fbclid(url: str) -> Optional[str]:
    """Extract the fbclid value from a URL if present."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        fbclid_list = params.get("fbclid", [])
        return fbclid_list[0] if fbclid_list else None
    except Exception:
        return None


def extract_all_fbclid(url: str) -> list[str]:
    """Extract all fbclid values from a URL (some URLs contain multiple)."""
    if not url:
        return []
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        return params.get("fbclid", [])
    except Exception:
        return []


def add_fbclid_to_url(url: str, fbclid: str) -> str:
    """Append or replace the fbclid parameter in a URL."""
    if not url or not fbclid:
        return url

    url = url.strip()
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)

    params["fbclid"] = [fbclid]

    new_query = urlencode(params, doseq=True)
    return urlunparse((
        parsed.scheme, parsed.netloc, parsed.path,
        parsed.params, new_query, parsed.fragment
    ))


def is_fbclid_url(url: str) -> bool:
    """Return True if the URL contains an fbclid parameter."""
    return extract_fbclid(url) is not None


def get_domain(url: str) -> str:
    """Safely extract the netloc (domain) from a URL."""
    try:
        return urlparse(url).netloc
    except Exception:
        return ""


def is_same_domain(url_a: str, url_b: str) -> bool:
    """Return True if both URLs share the same root domain (ignores subdomain)."""
    try:
        a = urlparse(url_a).netloc
        b = urlparse(url_b).netloc
        # Strip common prefixes like www, m, amp
        a_root = re.sub(r"^(www|m|amp|cdn|static)\.", "", a).lower()
        b_root = re.sub(r"^(www|m|amp|cdn|static)\.", "", b).lower()
        return a_root == b_root
    except Exception:
        return False


# --------------------------------------------------------------------------- main service


class CloakingBypassService:
    """Bypass cloaking on Facebook ad landing pages.

    This service implements the insight that most Facebook ad cloaking is
    fbclid-based, not IP-based. By passing the correct fbclid, we can
    reliably see the real landing page without needing expensive proxies
    for 90%+ of cases.

    Args:
        proxy_manager: Optional ProxyManager instance for IP-based fallback.
        default_timeout: HTTP request timeout in seconds (default 30).
        max_redirect_hops: Maximum redirects to follow before giving up (default 10).
    """

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
    }

    def __init__(
        self,
        proxy_manager=None,
        default_timeout: float = 30.0,
        max_redirect_hops: int = 10,
    ):
        self.proxy_manager = proxy_manager
        self.default_timeout = default_timeout
        self.max_redirect_hops = max_redirect_hops

    # ------------------------------------------------------------------ public API

    async def bypass(
        self,
        landing_url: str,
        fbclid: Optional[str] = None,
        use_proxy: bool = False,
        proxy_url: Optional[str] = None,
    ) -> CloakResult:
        """Attempt to bypass cloaking on a landing URL.

        This is the primary entry point. It:
          1. Extracts fbclid from the URL if not provided
          2. Optionally resolves the Facebook redirect to find the real destination
          3. Traces the full redirect chain via HTTP
          4. Returns a CloakResult with analysis

        Args:
            landing_url: The ad's destination URL (from Facebook ad library / scraping)
            fbclid: Explicit fbclid to use. Auto-extracted if omitted.
            use_proxy: Force proxy usage (for IP-based cloaking detection)
            proxy_url: Specific proxy URL to use

        Returns:
            CloakResult with all findings
        """
        start = datetime.utcnow()
        logger.info(f"Bypassing cloaking for: {landing_url[:80]}")

        # Step 1: Normalise the URL
        if not landing_url:
            return CloakResult(
                success=False,
                actual_url="",
                expected_domain="",
                actual_domain="",
                is_cloaked=False,
                cloak_type="none",
                fbclid_used="",
                proxy_used=None,
                error="Empty landing URL",
                redirect_chain=[],
            )

        landing_url = landing_url.strip()

        # Step 2: Resolve Facebook redirects (lnk.sk, l.facebook.com, etc.)
        resolved_url = await self._resolve_fb_redirect(landing_url)
        if resolved_url != landing_url:
            logger.debug(f"FB redirect resolved: {landing_url[:60]} → {resolved_url[:60]}")
            landing_url = resolved_url

        # Step 3: Extract or validate fbclid
        if not fbclid:
            fbclid = extract_fbclid(landing_url)

        # Step 4: Build the URL we will actually visit
        url_to_visit = add_fbclid_to_url(landing_url, fbclid) if fbclid else landing_url

        # Step 5: Extract expected domain
        expected_domain = get_domain(landing_url)
        logger.debug(f"Expected domain: {expected_domain}, fbclid: {fbclid}")

        # Step 6: Select proxy
        actual_proxy: Optional[str] = None
        if use_proxy or self.proxy_manager:
            if proxy_url:
                actual_proxy = proxy_url
            elif self.proxy_manager:
                actual_proxy = await self.proxy_manager.get_proxy()
                if actual_proxy:
                    logger.info(f"Using proxy: {actual_proxy[:60]}")

        # Step 7: Trace the redirect chain via HTTP
        trace = await self._trace_redirect_chain(url_to_visit, proxy=actual_proxy)

        # Step 8: Analyse results
        actual_url = trace.get("final_url", url_to_visit)
        redirect_chain = trace.get("chain", [url_to_visit])
        status_code = trace.get("status_code", 0)
        trace_error = trace.get("error")

        actual_domain = get_domain(actual_url)

        # Determine cloak type
        is_cloaked = False
        cloak_type = "none"

        if not actual_domain:
            # Could not determine domain — likely connection error
            pass
        elif actual_domain != expected_domain and actual_domain:
            # Domain changed — classic cloaking signal, real lander found
            is_cloaked = True
            cloak_type = "domain_mismatch"
            logger.info(
                f"CLOAKED detected [domain_mismatch]: "
                f"expected={expected_domain} actual={actual_domain}"
            )
        elif len(redirect_chain) > 3:
            # Unusually long redirect chain — suspicious but not definitive
            is_cloaked = True
            cloak_type = "redirect_chain"
            logger.info(f"CLOAKED detected [redirect_chain]: {len(redirect_chain)} hops")
        elif trace_error:
            cloak_type = "error"
            logger.warning(f"Trace error: {trace_error}")

        duration_ms = (datetime.utcnow() - start).total_seconds() * 1000

        return CloakResult(
            success=True,
            actual_url=actual_url,
            expected_domain=expected_domain,
            actual_domain=actual_domain,
            is_cloaked=is_cloaked,
            cloak_type=cloak_type,
            fbclid_used=fbclid or "",
            proxy_used=actual_proxy,
            error=trace_error,
            redirect_chain=redirect_chain,
            method="http",
            duration_ms=duration_ms,
        )

    async def check_with_browser(
        self,
        url: str,
        browser_pool,
        fbclid: Optional[str] = None,
        device: str = "desktop",
    ) -> dict:
        """Use Playwright to render a URL and get the final rendered state.

        Use this when:
          - The redirect chain involves JavaScript (SPA routing)
          - The lander checks navigator properties beyond headers
          - httpx failed to resolve the final page

        Args:
            url: Landing URL to visit
            browser_pool: BrowserPool instance
            fbclid: Optional fbclid to inject
            device: "desktop" or "mobile"

        Returns:
            dict with keys: success, final_url, title, has_content, status_code, error
        """
        if browser_pool is None:
            return {"error": "No browser pool available — call bypass() instead"}

        instance = await browser_pool.acquire()
        if instance is None:
            return {"error": "No browser available — pool exhausted"}

        page = None
        try:
            page = await instance.context.new_page()
            url_to_visit = add_fbclid_to_url(url, fbclid) if fbclid else url

            # Apply device emulation
            if device == "mobile":
                await instance.context.add_init_script("""
                    Object.defineProperty(navigator, 'platform', {value: 'iPhone'});
                    Object.defineProperty(navigator, 'userAgent', {
                        value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) '
                             + 'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 '
                             + 'Mobile/15E148 Safari/604.1'
                    });
                """)
                await instance.context.set_viewport_size({"width": 390, "height": 844})

            # Navigate with networkidle to wait for JS redirects
            response = await page.goto(url_to_visit, wait_until="networkidle", timeout=30_000)

            # After all redirects JavaScript can perform, get the final URL
            final_url = page.url

            # Basic content check
            content = await page.content()
            has_content = len(content) > 1000

            # Page title (helps identify the lander)
            try:
                title = await page.title()
            except Exception:
                title = ""

            # Try to detect meta refresh / JS redirect targets
            meta_refresh = await page.evaluate("""() => {
                const meta = document.querySelector('meta[http-equiv="refresh"]');
                return meta ? meta.getAttribute('content') || '' : '';
            }""")

            js_redirect = await page.evaluate("""() => {
                // Common JS redirect patterns
                if (window.location && window.location.href && window.location.href !== window.location.origin + '/') {
                    return window.location.href;
                }
                return '';
            }""")

            result = {
                "success": True,
                "final_url": final_url,
                "title": title,
                "has_content": has_content,
                "status_code": response.status if response else 0,
                "meta_refresh": meta_refresh,
                "js_redirect": js_redirect,
                "content_length": len(content),
            }

            logger.info(f"Browser visit complete: {final_url[:60]} | title={title[:40]}")
            return result

        except asyncio.TimeoutError:
            return {"error": "Browser navigation timed out after 30s"}
        except Exception as e:
            logger.error(f"Browser visit failed: {e}", exc_info=True)
            return {"error": str(e)}

        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            await browser_pool.release(instance)

    # ------------------------------------------------------------------ internal helpers

    async def _resolve_fb_redirect(self, url: str) -> str:
        """Follow Facebook short redirects (l.facebook.com, lnk.sk, etc.) once.

        Facebook wraps many ad URLs in redirect chains. We do a single
        HEAD/GET to resolve where FB actually points the browser.
        """
        fb_hosts = {"l.facebook.com", "lm.facebook.com", "lnk.sk", "fb.com", "m.facebook.com"}

        try:
            domain = get_domain(url)
            if domain.lower() not in fb_hosts:
                return url

            async with httpx.AsyncClient(
                follow_redirects=False,
                timeout=httpx.Timeout(connect=10, read=30, write=10, pool=10),
                headers=self.DEFAULT_HEADERS,
                verify=_HTTPX_VERIFY,
            ) as client:
                response = await client.get(url)
                location = response.headers.get("location", "")
                if location:
                    if location.startswith("http"):
                        return location
                    return urljoin(url, location)
                return url

        except Exception as e:
            logger.debug(f"FB redirect resolution failed for {url[:40]}: {e}")
            return url

    async def _trace_redirect_chain(
        self,
        url: str,
        proxy: Optional[str] = None,
    ) -> dict:
        """Trace all HTTP redirects from url to the final destination.

        Returns:
            dict with keys: final_url, chain (list of all visited URLs),
                            status_code, error
        """
        chain = [url]
        proxy_dict = {"http://": proxy, "https://": proxy} if proxy else None

        try:
            async with httpx.AsyncClient(
                follow_redirects=False,           # We handle redirects manually
                timeout=httpx.Timeout(
                    connect=10,
                    read=self.default_timeout,
                    write=10,
                    pool=10,
                ),
                proxies=proxy_dict,
                verify=_HTTPX_VERIFY,
            ) as client:
                current_url = url

                for hop in range(self.max_redirect_hops):
                    try:
                        response = await client.get(
                            current_url,
                            headers=self.DEFAULT_HEADERS,
                        )

                        status = response.status_code

                        if status in (301, 302, 303, 307, 308):
                            location = response.headers.get("location", "")
                            if not location:
                                # Redirect without Location header — treat as final
                                return {
                                    "final_url": str(response.url),
                                    "status_code": status,
                                    "chain": chain,
                                }

                            # Resolve relative Location against current URL
                            current_url = (
                                location if location.startswith("http")
                                else urljoin(current_url, location)
                            )
                            chain.append(current_url)
                            continue

                        # No redirect — this is the final destination
                        return {
                            "final_url": str(response.url),
                            "status_code": status,
                            "chain": chain,
                        }

                    except httpx.TimeoutException:
                        return {
                            "final_url": current_url,
                            "status_code": 0,
                            "chain": chain,
                            "error": f"Timeout on hop {hop + 1}",
                        }
                    except Exception as e:
                        return {
                            "final_url": current_url,
                            "status_code": 0,
                            "chain": chain,
                            "error": f"Hop {hop + 1}: {e}",
                        }

                # Exceeded max hops
                return {
                    "final_url": current_url,
                    "chain": chain,
                    "error": f"Max hops ({self.max_redirect_hops}) exceeded",
                }

        except Exception as e:
            return {
                "final_url": url,
                "chain": [url],
                "error": str(e),
            }

    # ------------------------------------------------------------------ convenience

    async def quick_bypass(self, landing_url: str) -> CloakResult:
        """Single-call bypass using only fbclid strategy (no proxy, no browser).

        Use this for the fastest possible check on bulk URLs.
        For production pipelines prefer bypass() with the full strategy.
        """
        return await self.bypass(landing_url, use_proxy=False)

    async def full_bypass(
        self,
        landing_url: str,
        fbclid: Optional[str] = None,
    ) -> CloakResult:
        """Full cloaking bypass: try HTTP first, then browser if needed.

        If the HTTP trace finds cloaking (domain mismatch), we're done.
        If HTTP fails or shows no cloaking but we suspect it, try browser.
        """
        # HTTP pass
        result = await self.bypass(landing_url, fbclid=fbclid, use_proxy=False)
        if result.is_cloaked:
            return result

        # Browser pass (deferred — caller passes browser_pool)
        logger.debug("HTTP pass inconclusive, browser pass available via check_with_browser()")
        return result
