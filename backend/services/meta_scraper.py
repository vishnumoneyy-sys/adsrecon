"""Meta Ads Library Scraper -- extracts ads from public Ads Library pages.

This module uses Facebook's internal GraphQL API (what their own UI uses) to
bypass the 403 blocking that simple httpx requests encounter.

Key techniques:
  - Extract fb_dtsg token from initial page HTML
  - Extract session cookies (dbl跳 / datr, c_user, etc.) from the landing page
  - POST to https://www.facebook.com/api/graphql/ with browser-like headers
  - Fall back to HTML parsing when GraphQL is unavailable
"""
import asyncio
import hashlib
import json
import logging
import random
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse, urlunparse, urlencode

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("adsrecon.meta_scraper")


# --------------------------------------------------------------------------- models


@dataclass
class MetaAd:
    """Represents a single ad extracted from Meta Ads Library."""
    library_id: str
    page_id: str
    page_name: str
    ad_text: str
    primary_image_url: str
    video_url: str
    landing_url: str
    fbclid: str
    platforms: list[str] = field(default_factory=list)   # facebook, instagram, messenger, audience_network
    days_running: int = 0
    impressions: str = ""
    is_active: bool = True
    raw_html: str = ""
    variations_count: int = 0
    # Enriched fields
    created_time: str = ""
    estimated_daily_reach: str = ""
    ad_screenshot_url: str = ""
    call_to_action: str = ""
    target_audience: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "library_id": self.library_id,
            "page_id": self.page_id,
            "page_name": self.page_name,
            "ad_text": self.ad_text,
            "primary_image_url": self.primary_image_url,
            "video_url": self.video_url,
            "landing_url": self.landing_url,
            "fbclid": self.fbclid,
            "platforms": self.platforms,
            "days_running": self.days_running,
            "impressions": self.impressions,
            "is_active": self.is_active,
            "variations_count": self.variations_count,
            "created_time": self.created_time,
            "estimated_daily_reach": self.estimated_daily_reach,
            "ad_screenshot_url": self.ad_screenshot_url,
            "call_to_action": self.call_to_action,
            "target_audience": self.target_audience,
        }


# --------------------------------------------------------------------------- constants


GRAPHQL_ENDPOINT = "https://www.facebook.com/api/graphql/"
GRAPHQL_ADS_QUERY = "AdsDiscoveryGraphQL"
GRAPHQL_PAGE_QUERY = "AdsPageContentQuery"

# Realistic browser User-Agent strings (rotated to avoid fingerprinting)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
]


def _random_ua() -> str:
    return random.choice(USER_AGENTS)


# --------------------------------------------------------------------------- scraper


class MetaScraper:
    """
    Scrapes Meta's public Ads Library without authentication.

    Uses Facebook's internal GraphQL API (what their own UI uses) to avoid 403
    blocking. Falls back to HTML parsing when GraphQL is unavailable.

    URL formats
    -----------
    Page transparency:
        https://www.facebook.com/ads/library/?view_all_page_id=PAGE_ID&...
    Keyword search:
        https://www.facebook.com/ads/library/?search_type=keyword&q=KEYWORD&country=US
    """

    BASE_URL = "https://www.facebook.com/ads/library/"

    def __init__(self, delay_ms: int = 2500, timeout: float = 30.0):
        """
        Args:
            delay_ms:   Milliseconds to sleep between requests (rate-limit guard).
            timeout:    Request timeout in seconds.
        """
        self.delay_ms = delay_ms
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        # Session state extracted from the landing page
        self._fb_dtsg: str = ""
        self._dbl跳: str = ""   # datr cookie value
        self._c_user: str = ""  # user ID cookie (optional, may be empty)
        self._cookies: dict[str, str] = {"locale": "en_US", "wd": "1920x1080"}
        self._headers: dict[str, str] = {}
        self._session_initialized: bool = False

    # ------------------------------------------------------------------ context manager

    async def __aenter__(self) -> "MetaScraper":
        self._client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(self.timeout, connect=15),
            verify=False,  # Disable SSL on Windows (cert store issues)
        )
        return self

    async def __aexit__(self, *args) -> None:
        if self._client:
            await self._client.aclose()

    # ------------------------------------------------------------------ public API

    async def scrape_page(self, page_url: str) -> list[MetaAd]:
        """
        Scrape all ads from a Facebook page's transparency page.

        Tries GraphQL first, then falls back to HTML parsing.

        The page URL must contain ``view_all_page_id``:
          https://www.facebook.com/ads/library/?view_all_page_id=123456&...

        Returns:
            List of :class:`MetaAd` objects found on the page.
        """
        logger.info(f"Scraping page URL: {page_url[:100]}")

        if not self._client:
            raise RuntimeError("MetaScraper not entered as async context manager")

        page_id = self._extract_page_id(page_url)
        country = self._extract_country(page_url) or "US"

        await self._ensure_session()

        # Try GraphQL first
        ads = await self._graphql_scrape_page(page_id, country)
        if ads:
            logger.info(f"GraphQL extracted {len(ads)} ads from page {page_id}")
            return ads

        # Fall back to HTML
        logger.info(f"GraphQL returned no results for page {page_id}, falling back to HTML")
        html = await self._fetch_get(page_url, retries=3)
        if not html:
            logger.error("Failed to fetch page HTML (both GraphQL and HTML failed)")
            return []

        ads = self._parse_html(html, page_url)
        logger.info(f"HTML fallback extracted {len(ads)} ads from page transparency page")
        return ads

    async def scrape_page_by_id(self, page_id: str) -> list[MetaAd]:
        """
        Convenience: build the transparency URL from a numeric page ID and scrape it.
        """
        url = f"{self.BASE_URL}?view_all_page_id={page_id}&active_status=all&ad_type=all"
        return await self.scrape_page(url)

    async def search_keyword(
        self,
        keyword: str,
        country: str = "US",
        media_type: str = "all",
        count: int = 24,
        cursor: Optional[str] = None,
    ) -> list[MetaAd]:
        """
        Search the Ads Library by keyword using GraphQL.

        Args:
            keyword:    Search term.
            country:    2-letter country code (default US).
            media_type: ``all`` | ``image`` | ``video`` | ``carousel``
            count:      Number of ads to fetch per page (default 24).
            cursor:     Pagination cursor (None for first page).

        Returns:
            List of :class:`MetaAd` objects.
        """
        logger.info(f"Keyword GraphQL search: '{keyword}' country={country}")

        if not self._client:
            raise RuntimeError("MetaScraper not entered as async context manager")

        await self._ensure_session()

        # Try GraphQL keyword search
        ads = await self._graphql_keyword_search(keyword, country, media_type, count, cursor)
        if ads is not None:
            logger.info(f"GraphQL keyword search returned {len(ads)} ads for '{keyword}'")
            return ads

        # Fall back to HTML scraping
        logger.warning(f"GraphQL keyword search failed for '{keyword}', falling back to HTML")
        encoded = keyword.replace(" ", "+")
        url = (
            f"{self.BASE_URL}"
            f"?search_type=keyword&q={encoded}"
            f"&country={country}"
            f"&active_status=active"
            f"&ad_type={media_type}"
            f"&media_type={media_type}"
        )
        html = await self._fetch_get(url, retries=3)
        if not html:
            logger.error("Failed to fetch search results HTML")
            return []

        ads = self._parse_html(html, url)
        logger.info(f"HTML fallback found {len(ads)} ads for keyword '{keyword}'")
        return ads

    async def search_keyword_multi(
        self,
        keyword: str,
        countries: list[str],
        media_type: str = "all",
        count: int = 20,
    ) -> dict[str, list[MetaAd]]:
        """
        Search the Ads Library by keyword across multiple countries.

        Args:
            keyword:    Search term.
            countries:  List of 2-letter country codes (e.g. ["US", "GB", "DE"]).
            media_type: ``all`` | ``image`` | ``video`` | ``carousel``
            count:      Number of ads to fetch per country (default 20).

        Returns:
            Dict mapping country code -> list of :class:`MetaAd` objects.
        """
        logger.info(f"Multi-country keyword search: '{keyword}' in {countries}")
        results: dict[str, list[MetaAd]] = {}

        for country in countries:
            try:
                ads = await self.search_keyword(keyword, country, media_type, count)
                results[country] = ads
                logger.info(f"  {country}: {len(ads)} ads")
            except Exception as exc:
                logger.warning(f"  {country}: error -- {exc}")
                results[country] = []

        return results

    async def search_active_by_page(self, page_id: str, country: str = "US") -> list[MetaAd]:
        """
        Fetch all currently-active ads for a given page ID.
        """
        url = (
            f"{self.BASE_URL}"
            f"?view_all_page_id={page_id}"
            f"&active_status=active"
            f"&ad_type=all"
            f"&country={country}"
        )
        return await self.scrape_page(url)

    # ------------------------------------------------------------------ session management

    async def _ensure_session(self) -> bool:
        """
        Ensure we have a valid fb_dtsg token and session cookies by visiting
        the Ads Library landing page.

        Returns True if the session was successfully initialized.
        """
        if self._session_initialized:
            return True

        logger.debug("Initializing Facebook session (fetching landing page)...")

        headers = self._build_browser_headers()

        try:
            response = await self._client.get(
                self.BASE_URL,
                headers=headers,
                cookies=self._cookies,
            )
        except httpx.RequestError as exc:
            logger.error(f"Session init request failed: {exc}")
            return False

        # Handle 403 during session init
        if response.status_code == 403:
            logger.warning("Got 403 during session init -- trying with fresh cookies")
            await self._try_fresh_session()
            return self._session_initialized

        if response.status_code != 200:
            logger.warning(f"Session init returned HTTP {response.status_code}")
            return False

        html = response.text

        # Extract fb_dtsg from HTML
        self._fb_dtsg = self._extract_dtsg(html)
        if not self._fb_dtsg:
            logger.warning("Could not extract fb_dtsg from landing page")

        # Extract datr / dbl跳 cookie
        for cookie_name, cookie_domain in [("datr", ".facebook.com"), ("c_user", ".facebook.com")]:
            val = self._get_cookie_from_response(response, cookie_name)
            if val:
                self._cookies[cookie_name] = val
                if cookie_name == "datr":
                    self._dbl跳 = val

        # Merge any cookies set by the server
        for name, val in response.cookies.items():
            if name not in self._cookies or not self._cookies[name]:
                self._cookies[name] = val

        # Try to extract __aUserID / __aUserID simulation from HTML
        a_user_id = self._extract_a_user_id(html)
        if a_user_id:
            self._cookies["__aUserID"] = a_user_id

        self._session_initialized = True
        logger.debug(
            f"Session initialized: fb_dtsg={'yes' if self._fb_dtsg else 'NO'}, "
            f"dbl跳={self._dbl跳[:8] + '...' if self._dbl跳 else 'none'}"
        )
        return True

    async def _try_fresh_session(self) -> None:
        """
        Attempt to recover from a 403 by trying with completely fresh headers
        and cookies, rotating the User-Agent.
        """
        logger.info("Attempting fresh session (403 recovery)...")

        # Rotate User-Agent
        self._cookies = {
            "locale": "en_US",
            "wd": "1920x1080",
            "sb": str(random.randint(1400000000000, 1700000000000)),
        }
        self._fb_dtsg = ""
        self._dbl跳 = ""
        self._session_initialized = False

        # Try fetching the base Facebook page first (may set more cookies)
        try:
            resp = await self._client.get(
                "https://www.facebook.com/",
                headers=self._build_browser_headers(),
                cookies=self._cookies,
            )
            if resp.status_code == 200:
                for name, val in resp.cookies.items():
                    self._cookies[name] = val
                dtsg = self._extract_dtsg(resp.text)
                if dtsg:
                    self._fb_dtsg = dtsg
                    self._session_initialized = True
                    logger.info("Fresh session recovered via base Facebook page")
                    return
        except httpx.RequestError:
            pass

        # Try the ads library directly
        try:
            resp = await self._client.get(
                self.BASE_URL,
                headers=self._build_browser_headers(),
                cookies=self._cookies,
            )
            if resp.status_code == 200:
                self._fb_dtsg = self._extract_dtsg(resp.text)
                for name, val in resp.cookies.items():
                    self._cookies[name] = val
                self._session_initialized = True
                logger.info("Fresh session recovered via ads library page")
        except httpx.RequestError as exc:
            logger.error(f"Fresh session attempt also failed: {exc}")

    # ------------------------------------------------------------------ GraphQL helpers

    def _build_browser_headers(self, referer: Optional[str] = None) -> dict[str, str]:
        """Build a full set of browser-like request headers."""
        return {
            "User-Agent": _random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
            **({"Referer": referer} if referer else {}),
        }

    def _build_graphql_headers(self, referer: str) -> dict[str, str]:
        """Build headers for GraphQL POST requests."""
        return {
            "User-Agent": _random_ua(),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://www.facebook.com",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Referer": referer,
            "X-FB-Friendly-Name": GRAPHQL_ADS_QUERY,
            "X-CSRF-Token": self._fb_dtsg or "",
            "X-FB-Client-Token": self._fb_dtsg or "",
            "X-FB-Connection-Type": "WiFi",
            "X-FB-ET-Token": self._fb_dtsg or "",
            "DPR": "1",
            "Viewport-Width": "1920",
            "Viewport-Height": "1080",
        }

    def _build_graphql_body(
        self,
        operation_name: str,
        variables: dict[str, Any],
    ) -> dict[str, str]:
        """
        Build the application/x-www-form-urlencoded body for a GraphQL POST.

        The format Meta's JS client uses:
          __a=1&__ccg=EXCELLENT&__comet_req=1&fb_dtsg={dtsg}&fb_api_caller_class=RelayModern&fb_api_req_friendly_name={name}&variables={json}&server_timestamps=true&doc_id={doc_id}
        """
        body: dict[str, str] = {
            "__a": "1",
            "__ccg": "EXCELLENT",
            "__comet_req": "1",
            "fb_dtsg": self._fb_dtsg,
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": operation_name,
            "variables": json.dumps(variables, separators=(",", ":")),
            "server_timestamps": "true",
            "doc_id": self._GRAPHQL_DOC_IDS.get(operation_name, ""),
        }
        return body

    # Map operation names to their GraphQL doc IDs (found in Meta's JS bundles)
    _GRAPHQL_DOC_IDS: dict[str, str] = {
        GRAPHQL_ADS_QUERY: "7209182822829864",
        GRAPHQL_PAGE_QUERY: "6276034497163656",
    }

    # ------------------------------------------------------------------ GraphQL keyword search

    async def _graphql_keyword_search(
        self,
        keyword: str,
        country: str,
        media_type: str,
        count: int,
        cursor: Optional[str],
    ) -> Optional[list[MetaAd]]:
        """
        POST to the AdsDiscoveryGraphQL GraphQL endpoint.

        Returns None if GraphQL fails (so caller can fall back to HTML).
        """
        if not self._fb_dtsg:
            logger.debug("No fb_dtsg, cannot use GraphQL")
            return None

        variables = {
            "country": country,
            "search_terms": keyword,
            "count": count,
            "cursor": cursor,
            "media_type": media_type if media_type != "all" else None,
            "active_status": "active",
        }

        referer = (
            f"{self.BASE_URL}"
            f"?search_type=keyword&q={keyword.replace(' ', '+')}"
            f"&country={country}"
        )

        try:
            response = await self._graphql_post(
                self.BASE_URL,
                GRAPHQL_ADS_QUERY,
                variables,
                referer,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 403:
                logger.warning("GraphQL returned 403 -- session may be expired")
                self._session_initialized = False
                return None
            raise

        if response is None:
            return None

        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            logger.debug(f"GraphQL response not valid JSON: {exc}")
            return None

        # Navigate to ads data in the GraphQL response
        # Structure: {"data": {"viewer": {"ads_pdp": {"ads_data": {"data": [...]}}}}}
        try:
            ads_nodes = (
                data
                .get("data", {})
                .get("viewer", {})
                .get("ads_pdp", {})
                .get("ads_data", {})
                .get("data", [])
            )
        except Exception:
            logger.debug(f"Unexpected GraphQL response structure: {str(data)[:200]}")
            return None

        if not isinstance(ads_nodes, list):
            logger.debug(f"GraphQL ads_data.data is not a list: {type(ads_nodes)}")
            return None

        ads = [self._parse_graphql_ad_node(node, country) for node in ads_nodes]
        ads = [a for a in ads if a is not None]

        logger.debug(f"GraphQL parsed {len(ads)} ads from {len(ads_nodes)} nodes")
        return ads

    async def _graphql_scrape_page(
        self,
        page_id: str,
        country: str,
    ) -> list[MetaAd]:
        """
        Use GraphQL (AdsPageContentQuery) to fetch ads for a specific page.
        """
        if not self._fb_dtsg:
            return []

        variables = {
            "pageID": page_id,
            "country": country,
            "activeStatus": "all",
            "adType": "all",
            "count": 24,
            "cursor": None,
        }

        referer = f"{self.BASE_URL}?view_all_page_id={page_id}&active_status=all&ad_type=all&country={country}"

        try:
            response = await self._graphql_post(
                self.BASE_URL,
                GRAPHQL_PAGE_QUERY,
                variables,
                referer,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 403:
                logger.warning("GraphQL page scrape got 403")
                self._session_initialized = False
                return []
            raise

        if response is None:
            return []

        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError):
            return []

        try:
            ads_nodes = (
                data
                .get("data", {})
                .get("node", {})
                .get("ads_pd_content", {})
                .get("data", [])
            )
        except Exception:
            logger.debug(f"Unexpected page GraphQL structure: {str(data)[:200]}")
            return []

        if not isinstance(ads_nodes, list):
            return []

        ads = [self._parse_graphql_page_ad_node(node, page_id) for node in ads_nodes]
        return [a for a in ads if a is not None]

    async def _graphql_post(
        self,
        referer_url: str,
        operation_name: str,
        variables: dict[str, Any],
        referer: Optional[str] = None,
        retries: int = 3,
    ) -> Optional[httpx.Response]:
        """
        POST to the GraphQL endpoint with exponential backoff.

        Returns None on failure (caller decides whether to fall back to HTML).
        """
        body = self._build_graphql_body(operation_name, variables)
        headers = self._build_graphql_headers(referer or referer_url)
        cookies = {**self._cookies}

        for attempt in range(retries):
            await asyncio.sleep(self.delay_ms / 1000)

            try:
                response = await self._client.post(
                    GRAPHQL_ENDPOINT,
                    data={k: str(v) if v is not None else "" for k, v in body.items()},
                    headers=headers,
                    cookies=cookies,
                )

                if response.status_code == 200:
                    return response

                if response.status_code == 403:
                    logger.warning(f"GraphQL POST got 403 (attempt {attempt + 1})")
                    self._session_initialized = False
                    if attempt < retries - 1:
                        await self._ensure_session()
                        if not self._fb_dtsg:
                            return None
                        # Rebuild body with fresh fb_dtsg
                        body["fb_dtsg"] = self._fb_dtsg
                        headers["X-CSRF-Token"] = self._fb_dtsg
                        headers["X-FB-ET-Token"] = self._fb_dtsg
                        cookies = {**self._cookies}
                    else:
                        return None

                if response.status_code == 429:
                    wait_ms = self.delay_ms * (2 ** attempt) * 2
                    logger.warning(f"GraphQL rate-limited (429). Sleeping {wait_ms}ms")
                    await asyncio.sleep(wait_ms / 1000)
                    continue

                logger.warning(
                    f"GraphQL POST HTTP {response.status_code} "
                    f"(attempt {attempt + 1}/{retries})"
                )

            except httpx.RequestError as exc:
                logger.error(f"GraphQL POST request error (attempt {attempt + 1}): {exc}")
                await asyncio.sleep(1)

        return None

    # ------------------------------------------------------------------ GraphQL response parsing

    def _parse_graphql_ad_node(self, node: Any, country: str) -> Optional[MetaAd]:
        """
        Extract a MetaAd from a GraphQL AdsDiscoveryGraphQL result node.

        The actual node structure varies between Meta's API versions.
        We try multiple known shapes.
        """
        try:
            # Shape 1: top-level fields
            ad_id = str(node.get("id") or node.get("ad_id") or node.get("lib_id") or "")

            # Shape 2: nested in 'ad' or 'snapshot' field
            inner = node.get("ad") or node.get("snapshot") or node

            page_info = inner.get("page") or inner.get("pageInfo") or {}
            page_id = str(page_info.get("id") or inner.get("page_id") or "")
            page_name = str(page_info.get("name") or inner.get("page_name") or "")

            creative = inner.get("creative") or inner.get("ad_creative") or {}

            # Ad text
            ad_text = str(
                creative.get("body")
                or creative.get("ad_creative_body")
                or creative.get("text")
                or inner.get("body")
                or inner.get("ad_text")
                or ""
            )[:500]

            # Media
            video_url = str(
                creative.get("video_url")
                or creative.get("videoUrl")
                or inner.get("video_url")
                or ""
            )

            image_url = str(
                creative.get("image_url")
                or creative.get("imageUrl")
                or creative.get("primary_image_url")
                or inner.get("image_url")
                or ""
            )

            # CTA
            cta = creative.get("cta") or {}
            if isinstance(cta, dict):
                call_to_action = str(cta.get("text") or cta.get("type") or "")
            else:
                call_to_action = str(cta or "")

            # Landing URL
            link_data = creative.get("link_url") or creative.get("link") or creative.get("deeplink") or {}
            if isinstance(link_data, dict):
                raw_url = str(link_data.get("url") or link_data.get("link") or "")
            else:
                raw_url = str(link_data or inner.get("link") or inner.get("display_url") or "")

            fbclid = self._extract_fbclid(raw_url)
            landing_url = self._extract_landing_url(raw_url) if raw_url else ""

            # Platforms
            delivery = inner.get("delivery_info") or inner.get("delivery") or {}
            platforms: list[str] = ["facebook"]
            if isinstance(delivery, dict):
                if delivery.get("facebook"): platforms.append("facebook")
                if delivery.get("instagram"): platforms.append("instagram")
                if delivery.get("messenger"): platforms.append("messenger")
                if delivery.get("audience_network"): platforms.append("audience_network")

            # Audience targeting
            targeting = inner.get("targeting") or inner.get("targeting_info") or {}
            target_audience: dict[str, Any] = {}
            if isinstance(targeting, dict):
                target_audience = {
                    "age_range": targeting.get("age_range", ""),
                    "genders": targeting.get("genders", []),
                    "geo_locations": targeting.get("geo_locations", {}),
                    "interests": targeting.get("interests", []),
                }

            # Meta info
            is_active = inner.get("is_active") if isinstance(inner, dict) else True
            days = inner.get("days_running") or inner.get("run_time") or 0

            return MetaAd(
                library_id=ad_id,
                page_id=page_id,
                page_name=page_name,
                ad_text=ad_text,
                primary_image_url=image_url,
                video_url=video_url,
                landing_url=landing_url,
                fbclid=fbclid,
                platforms=platforms,
                days_running=int(days),
                is_active=is_active if isinstance(is_active, bool) else True,
                call_to_action=call_to_action,
                target_audience=target_audience,
            )

        except Exception as exc:
            logger.debug(f"Error parsing GraphQL ad node: {exc}")
            return None

    def _parse_graphql_page_ad_node(self, node: Any, page_id: str) -> Optional[MetaAd]:
        """Extract a MetaAd from an AdsPageContentQuery result node."""
        return self._parse_graphql_ad_node(node, "")

    # ------------------------------------------------------------------ HTTP helpers

    async def _fetch_get(self, url: str, retries: int = 3) -> Optional[str]:
        """GET request with retries and rate-limiting delay."""
        if not self._client:
            return None

        for attempt in range(retries):
            try:
                await asyncio.sleep(self.delay_ms / 1000)
                headers = self._build_browser_headers(referer="https://www.facebook.com/")
                response = await self._client.get(
                    url,
                    headers=headers,
                    cookies=self._cookies,
                )

                if response.status_code == 200:
                    return response.text

                if response.status_code == 403:
                    logger.warning(f"HTTP 403 for {url[:80]} -- attempting fresh session")
                    self._session_initialized = False
                    await self._ensure_session()
                    continue

                if response.status_code == 429:
                    wait_ms = self.delay_ms * (2 ** attempt)
                    logger.warning(f"Rate-limited (429). Sleeping {wait_ms}ms")
                    await asyncio.sleep(wait_ms / 1000)
                    continue

                logger.warning(f"HTTP {response.status_code} for {url[:80]}")

            except httpx.RequestError as exc:
                logger.error(f"Request error (attempt {attempt + 1}/{retries}): {exc}")
                await asyncio.sleep(1)

        return None

    # ------------------------------------------------------------------ parsing (HTML fallback)

    def _parse_html(self, html: str, source_url: str) -> list[MetaAd]:
        """
        Parse the Ads Library HTML and extract ad records.
        (Same as original -- kept as fallback.)
        """
        soup = BeautifulSoup(html, "lxml")

        page_id = self._extract_page_id(source_url)
        page_name = self._extract_page_name(soup)

        ads: list[MetaAd] = []

        # Try JSON embedded in scripts first (more reliable)
        script_ads = self._extract_from_scripts(soup, page_id, page_name)
        ads.extend(script_ads)

        # Fall back to HTML parsing
        html_ads = self._extract_from_html(soup, page_id, page_name)
        ads.extend(html_ads)

        # Deduplicate by library_id
        seen: set[str] = set()
        unique_ads: list[MetaAd] = []
        for ad in ads:
            if ad.library_id and ad.library_id not in seen:
                seen.add(ad.library_id)
                unique_ads.append(ad)

        logger.debug(f"Total unique ads after dedup: {len(unique_ads)}")
        return unique_ads

    # ------------------------------------------------------------------ script extraction (fallback)

    def _extract_from_scripts(
        self, soup: BeautifulSoup, page_id: str, page_name: str
    ) -> list[MetaAd]:
        """Find JSON data embedded in <script> tags. (Same as original.)"""
        ads: list[MetaAd] = []

        for script in soup.find_all("script"):
            text = script.string or ""
            if not text:
                continue

            if not any(marker in text.lower() for marker in (
                "ad_id", "ads_data", "libray_id", "adsrecon", "creative",
            )):
                continue

            try:
                found = self._parse_script_for_ads(text, page_id, page_name)
                ads.extend(found)
            except Exception as exc:
                logger.debug(f"Script parsing error: {exc}")

        return ads

    def _parse_script_for_ads(
        self, text: str, page_id: str, page_name: str
    ) -> list[MetaAd]:
        """Parse script text for ad objects. (Same as original.)"""
        ads: list[MetaAd] = []

        ad_id_pattern = re.compile(r'"ad_id"\s*:\s*"(\d+)"')
        creative_id_pattern = re.compile(r'"creative_id"\s*:\s*"(\d+)"')
        display_url_pattern = re.compile(r'"display_url"\s*:\s*"([^"]+)"')
        image_url_pattern = re.compile(r'"image_url"\s*:\s*"([^"]+)"')
        page_id_pattern = re.compile(r'"page_id"\s*:\s*"(\d+)"')
        page_name_pattern = re.compile(r'"page_name"\s*:\s*"([^"]+)"')
        ad_text_pattern = re.compile(r'"ad_creative_body"\s*:\s*"([^"]+)"')
        video_pattern = re.compile(r'"video_url"\s*:\s*"([^"]+)"')
        cta_pattern = re.compile(r'"cta_link"\s*:\s*"([^"]+)"')

        for m in ad_id_pattern.finditer(text):
            library_id = m.group(1)
            window = text[max(0, m.start() - 500) : m.end() + 500]

            ad = MetaAd(
                library_id=library_id,
                page_id=self._first_capture(page_id_pattern, window) or page_id,
                page_name=self._first_capture(page_name_pattern, window) or page_name,
                ad_text=self._first_capture(ad_text_pattern, window, max_len=500) or "",
                primary_image_url=self._first_capture(image_url_pattern, window) or "",
                video_url=self._first_capture(video_pattern, window) or "",
                landing_url=self._first_capture(display_url_pattern, window) or "",
                fbclid=self._extract_fbclid(self._first_capture(display_url_pattern, window) or ""),
                call_to_action=self._first_capture(cta_pattern, window) or "",
                platforms=["facebook"],
                raw_html=window[:2000],
            )
            ads.append(ad)

        json_blocks = re.findall(r"\{[^{}]{20,500}\}", text)
        for block in json_blocks[:5]:
            try:
                data = json.loads(block)
                if isinstance(data, dict) and self._looks_like_ad_data(data):
                    ad = self._dict_to_meta_ad(data, page_id, page_name)
                    if ad:
                        ads.append(ad)
            except (json.JSONDecodeError, ValueError):
                pass

        return ads

    def _first_capture(
        self, pattern: re.Pattern, text: str, max_len: int = 200
    ) -> Optional[str]:
        m = pattern.search(text)
        if not m:
            return None
        val = m.group(1)
        return val[:max_len] if max_len else val

    def _looks_like_ad_data(self, data: dict) -> bool:
        """Heuristic: does this dict look like an ad record? (Same as original.)"""
        keys = set(k.lower() for k in data.keys())
        ad_markers = {"ad_id", "creative_id", "page_id", "display_url", "ad_creative_body"}
        return bool(keys & ad_markers)

    # ------------------------------------------------------------------ HTML extraction (fallback)

    def _extract_from_html(
        self, soup: BeautifulSoup, page_id: str, page_name: str
    ) -> list[MetaAd]:
        """Parse ad data from HTML elements. (Same as original.)"""
        ads: list[MetaAd] = []

        candidate_selectors = [
            "div[data-testid='newsfeed-parsed-link']",
            "div[data-testid='fbFeedStory']",
            "div[data-pagelet='FeedUnit']",
            "div[aria-describedby]",
            "div.x1iyjqo2.x6ikm8r",
            "div.x1n2onr6",
            "div._4t2t",
            "div.userContentWrapper",
            "div._5pcm8",
            "div.x9f619",
            "div[tabindex='0']",
        ]

        found_elements: list = []
        for sel in candidate_selectors:
            try:
                elements = soup.select(sel)
                for el in elements:
                    if el not in found_elements:
                        found_elements.append(el)
            except Exception:
                pass

        for el in found_elements:
            ad = self._element_to_meta_ad(el, page_id, page_name)
            if ad and ad.library_id:
                ads.append(ad)

        return ads

    def _element_to_meta_ad(
        self, el, page_id: str, page_name: str
    ) -> Optional[MetaAd]:
        """Convert a DOM element into a :class:`MetaAd`. (Same as original.)"""
        try:
            library_id = ""

            for link in el.find_all("a", href=True):
                href = link["href"]
                mid = self._extract_library_id_from_url(href)
                if mid:
                    library_id = mid
                    break

            text_parts: list[str] = []
            for tag in el.find_all(["p", "span", "div", "h2", "h3"]):
                t = tag.get_text(strip=True)
                if len(t) > 20:
                    text_parts.append(t)
            ad_text = " ".join(text_parts[:4])[:500]

            video_url = ""
            video_el = el.find("video")
            if video_el:
                video_url = video_el.get("src", "") or video_el.get("data-src", "")

            primary_image_url = ""
            img_el = el.find("img")
            if img_el:
                src = img_el.get("src") or img_el.get("data-src", "") or img_el.get("data-fallback-src", "")
                width = img_el.get("width", "0")
                try:
                    if int(width) < 50:
                        primary_image_url = ""
                    else:
                        primary_image_url = src
                except ValueError:
                    primary_image_url = src

            landing_url = ""
            fbclid = ""
            for link in el.find_all("a", href=True):
                href = link["href"]
                if any(x in href for x in ("display_url", "l.facebook", "l.messenger", "lnk.sk")):
                    landing_url = self._extract_landing_url(href)
                    fbclid = self._extract_fbclid(href)
                    break

            if not landing_url:
                for link in el.find_all("a", href=True):
                    href = link["href"]
                    if href.startswith("http") and "facebook" not in href:
                        landing_url = self._extract_landing_url(href)
                        fbclid = self._extract_fbclid(href)
                        break

            cta_el = el.find("a", class_=re.compile(r"cta|button|learn", re.I))
            call_to_action = cta_el.get_text(strip=True) if cta_el else ""

            platforms = self._detect_platforms(el)

            raw = str(el)[:2000]

            return MetaAd(
                library_id=library_id,
                page_id=page_id,
                page_name=page_name,
                ad_text=ad_text,
                primary_image_url=primary_image_url,
                video_url=video_url,
                landing_url=landing_url,
                fbclid=fbclid,
                platforms=platforms,
                call_to_action=call_to_action,
                raw_html=raw,
            )

        except Exception as exc:
            logger.debug(f"Element -> MetaAd conversion error: {exc}")
            return None

    # ------------------------------------------------------------------ URL / text helpers

    def _extract_page_id(self, url: str) -> str:
        """Pull the numeric page ID out of a transparency URL."""
        if not url:
            return ""
        match = re.search(r"[?&]view_all_page_id=(\d+)", url)
        if match:
            return match.group(1)
        match = re.search(r"facebook\.com/(?:pg|.*?)/(\d+)", url)
        if match:
            return match.group(1)
        return ""

    def _extract_country(self, url: str) -> Optional[str]:
        """Extract the country parameter from a URL."""
        if not url:
            return None
        match = re.search(r"[?&]country=([A-Z]{2})", url)
        return match.group(1) if match else None

    def _extract_page_name(self, soup: BeautifulSoup) -> str:
        """Get the page name from the HTML <title> tag. (Same as original.)"""
        title_el = soup.find("title")
        if not title_el:
            return ""
        title_text = title_el.get_text(strip=True)
        if "Ads | " in title_text:
            return title_text.split("Ads | ", 1)[-1].strip()
        if "| " in title_text:
            return title_text.rsplit("|", 1)[0].strip()
        return title_text

    def _extract_dtsg(self, html: str) -> str:
        """
        Extract the fb_dtsg token from the HTML of a Facebook page.

        Meta embeds the token as:
          {'token':"ABCDEFG...", 'type':"...
        or in a JSON config block.
        """
        # Pattern 1: 'token':"VALUE"
        m = re.search(r"['\"]token['\"]:\s*['\"]([A-Za-z0-9%_-]{10,})['\"]", html)
        if m:
            return m.group(1)

        # Pattern 2: "dtsg":{"token":"VALUE" ...}
        m = re.search(r'"dtsg"\s*,\s*"token"\s*:\s*"([A-Za-z0-9%_-]{10,})"', html)
        if m:
            return m.group(1)

        # Pattern 3: var DtsgAcj = "VALUE";
        m = re.search(r'DtsgAcj\s*=\s*"([A-Za-z0-9%_-]{10,})"', html)
        if m:
            return m.group(1)

        # Pattern 4: input[name="fb_dtsg"] value="
        m = re.search(r'name="fb_dtsg"\s+value="([^"]+)"', html)
        if m:
            return m.group(1)

        # Pattern 5: "token":"VALUE" in a short window.__METADATA__ block
        m = re.search(r'"token"["\s:]+"([A-Za-z0-9%_-]{10,})"', html)
        if m:
            return m.group(1)

        return ""

    def _extract_a_user_id(self, html: str) -> str:
        """
        Attempt to extract __aUserID simulation value.
        Meta's JS sets this in the __initMqtt function.
        """
        m = re.search(r'"aUserID"\s*,\s*"?\s*(\d+)\s*"?",', html)
        if m:
            return m.group(1)
        m = re.search(r'"userID"\s*,\s*"?\s*(\d+)\s*"?",', html)
        if m:
            return m.group(1)
        return ""

    def _get_cookie_from_response(
        self, response: httpx.Response, name: str
    ) -> Optional[str]:
        """Get a cookie value from an httpx response by name."""
        for cookie in response.cookies.jar:
            if cookie.name == name:
                return cookie.value
        return None

    def _extract_library_id_from_url(self, url: str) -> str:
        """Extract the ad library ID from a URL string. (Same as original.)"""
        if not url:
            return ""
        match = re.search(r"[?&]id=(\d+)", url)
        if match:
            return match.group(1)
        match = re.search(r"/ads/[^/]+/(\d+)", url)
        if match:
            return match.group(1)
        return ""

    def _extract_landing_url(self, url: str) -> str:
        """
        Extract the true destination from Meta's redirect wrappers.
        (Same as original.)
        """
        if not url:
            return ""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        params = parse_qs(parsed.query)

        if domain in ("l.facebook.com", "lm.facebook.com", "l.messenger.com", "lnk.sk", "fb.com"):
            for key in ("u", "url", "l", "link"):
                if key in params:
                    from urllib.parse import unquote
                    target = unquote(params[key][0])
                    if target.startswith("http"):
                        return target
                    return urlparse(target).geturl()

        return url

    def _extract_fbclid(self, url: str) -> str:
        """Pull fbclid out of a URL. (Same as original.)"""
        if not url:
            return ""
        match = re.search(r"[?&]fbclid=([^&\s]+)", url)
        return match.group(1) if match else ""

    def _detect_platforms(self, el) -> list[str]:
        """Infer which Meta platforms this ad runs on. (Same as original.)"""
        platforms = ["facebook"]
        text_lower = el.get_text().lower()
        hrefs = " ".join(a.get("href", "") for a in el.find_all("a", href=True)).lower()

        if any(x in text_lower or x in hrefs for x in ("instagram", "ig:", "reels", "stories")):
            platforms.append("instagram")
        if any(x in text_lower or x in hrefs for x in ("messenger", " m.me ")):
            platforms.append("messenger")
        if "audience network" in text_lower or "audience_network" in hrefs:
            platforms.append("audience_network")

        return list(dict.fromkeys(platforms))

    # ------------------------------------------------------------------ JSON conversion

    def _dict_to_meta_ad(
        self, data: dict, page_id: str, page_name: str
    ) -> Optional[MetaAd]:
        """Convert a plain dict (from JSON) into a :class:`MetaAd`. (Same as original.)"""
        try:
            raw_url = str(
                data.get("landing_url")
                or data.get("display_url")
                or data.get("ad_creative_deeplink_url")
                or ""
            )

            return MetaAd(
                library_id=str(
                    data.get("ad_id")
                    or data.get("creative_id")
                    or data.get("id")
                    or ""
                ),
                page_id=str(
                    data.get("page_id")
                    or data.get("advertiser_id")
                    or page_id
                ),
                page_name=data.get("page_name") or page_name,
                ad_text=str(data.get("ad_creative_body", "") or data.get("ad_text", ""))[:500],
                primary_image_url=str(data.get("image_url") or data.get("primary_image_url") or ""),
                video_url=str(data.get("video_url") or ""),
                landing_url=self._extract_landing_url(raw_url),
                fbclid=self._extract_fbclid(raw_url),
                platforms=data.get("platforms", ["facebook"]),
                days_running=int(data.get("days_running", 0)),
                impressions=str(data.get("impressions", "")),
                is_active=bool(data.get("is_active", data.get("active_status") == "active")),
                variations_count=int(data.get("variations_count", 0)),
                call_to_action=str(data.get("cta_text") or data.get("call_to_action") or ""),
                raw_html="",
            )
        except Exception as exc:
            logger.debug(f"dict -> MetaAd conversion error: {exc}")
            return None
