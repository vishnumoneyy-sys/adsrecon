"""Meta Ad Library Graph API Scraper -- uses Facebook's official Graph API.

This is the PRIMARY scraping method because:
  - Free (no proxies needed)
  - Fast (direct API calls)
  - Reliable (official endpoint, no anti-bot)
  - Returns structured JSON with reach, demographics, spend data

Docs: https://developers.facebook.com/docs/graph-api/reference/ads_archive/
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

logger = logging.getLogger("adsrecon.graph_api")

# Graph API version - using latest stable
GRAPH_API_VERSION = "v25.0"
ADS_ARCHIVE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}/ads_archive"

# Fields to request from the API
AD_FIELDS = (
    "id,"
    "ad_creative_body,"
    "ad_delivery_start_time,"
    "ad_delivery_stop_time,"
    "ad_snapshot_url,"
    "bylines,"
    "currency,"
    "delivery_by_region,"
    "estimated_audience_size,"
    "languages,"
    "page_id,"
    "page_name,"
    "ad_metadata,"
    "impressions,"
    "spend,"
    "publisher_platforms,"
    "ad_active_status,"
    "ad_creation_time"
)


@dataclass
class GraphApiAd:
    """Represents an ad returned by the Graph API."""
    library_id: str = ""
    page_id: str = ""
    page_name: str = ""
    ad_text: str = ""
    landing_url: str = ""
    fbclid: str = ""
    platforms: list[str] = field(default_factory=list)
    impressions: str = ""
    spend: str = ""
    estimated_audience: str = ""
    is_active: bool = True
    ad_creation_time: str = ""
    ad_delivery_start: str = ""
    ad_delivery_stop: str = ""
    languages: list[str] = field(default_factory=list)
    countries: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "library_id": self.library_id,
            "page_id": self.page_id,
            "page_name": self.page_name,
            "ad_text": self.ad_text,
            "landing_url": self.landing_url,
            "fbclid": self.fbclid,
            "platforms": self.platforms,
            "impressions": self.impressions,
            "spend": self.spend,
            "estimated_audience": self.estimated_audience,
            "is_active": self.is_active,
            "ad_creation_time": self.ad_creation_time,
            "ad_delivery_start": self.ad_delivery_start,
            "ad_delivery_stop": self.ad_delivery_stop,
            "languages": self.languages,
            "countries": self.countries,
        }


def _parse_impressions(raw: dict) -> str:
    """Parse impressions from raw API data."""
    try:
        impr = raw.get("impressions", {}) or {}
        if isinstance(impr, dict):
            upper = impr.get("upper", "")
            lower = impr.get("lower", "")
            if upper and lower:
                return f"{lower}-{upper}"
            return str(upper or impr.get("estimate", ""))
        return str(impr)
    except Exception:
        return ""


def _parse_spend(raw: dict) -> str:
    """Parse spend from raw API data."""
    try:
        spend = raw.get("spend", {}) or {}
        if isinstance(spend, dict):
            upper = spend.get("upper", "")
            lower = spend.get("lower", "")
            if upper and lower:
                return f"{lower}-{upper}"
            return str(upper or "")
        return str(spend)
    except Exception:
        return ""


def _parse_countries(raw: dict) -> list[str]:
    """Parse delivery countries from raw API data."""
    try:
        regions = raw.get("delivery_by_region") or {}
        if isinstance(regions, dict):
            return list(regions.keys())
        return []
    except Exception:
        return []


def _extract_fbclid_from_bylines(bylines: list, page_id: str) -> tuple[str, str]:
    """Extract fbclid and landing URL from bylines."""
    fbclid = ""
    landing_url = ""
    try:
        if isinstance(bylines, list):
            for byline in bylines:
                if isinstance(byline, dict):
                    outer = byline.get("outer", {}) or {}
                    data = outer.get("data", []) or []
                    for item in data:
                        if isinstance(item, dict):
                            links = item.get("ad府_creative_link", []) or []
                            for link in links:
                                if isinstance(link, dict):
                                    href = link.get("uri", "")
                                    if "fbclid=" in href:
                                        from urllib.parse import parse_qs, urlparse
                                        qs = parse_qs(urlparse(href).query)
                                        fbclid_vals = qs.get("fbclid", [])
                                        if fbclid_vals:
                                            fbclid = fbclid_vals[0]
                                    if landing_url == "" and href and not href.startswith("/"):
                                        landing_url = href
    except Exception:
        pass
    return fbclid, landing_url


def _parse_ad(raw: dict) -> Optional[GraphApiAd]:
    """Parse a raw API ad into a GraphApiAd."""
    try:
        ad_id = str(raw.get("id", ""))
        page_id = str(raw.get("page_id", ""))
        page_name = str(raw.get("page_name", ""))
        ad_text = str(raw.get("ad_creative_body", ""))
        snapshot_url = str(raw.get("ad_snapshot_url", ""))

        # Get fbclid and landing from bylines or snapshot_url
        fbclid, landing_url = _extract_fbclid_from_bylines(
            raw.get("bylines", []), page_id
        )
        if not landing_url and snapshot_url:
            landing_url = snapshot_url

        platforms_raw = raw.get("publisher_platforms", []) or []
        platforms = [str(p) for p in platforms_raw if p]

        impressions = _parse_impressions(raw)
        spend = _parse_spend(raw)
        audience = str(raw.get("estimated_audience_size", ""))

        is_active = raw.get("ad_active_status", "") == "ACTIVE"
        creation_time = str(raw.get("ad_creation_time", ""))
        delivery_start = str(raw.get("ad_delivery_start_time", ""))
        delivery_stop = str(raw.get("ad_delivery_stop_time", ""))

        langs = raw.get("languages", []) or []
        languages = [str(l) for l in langs if l]
        countries = _parse_countries(raw)

        return GraphApiAd(
            library_id=ad_id,
            page_id=page_id,
            page_name=page_name,
            ad_text=ad_text,
            landing_url=landing_url,
            fbclid=fbclid,
            platforms=platforms,
            impressions=impressions,
            spend=spend,
            estimated_audience=audience,
            is_active=is_active,
            ad_creation_time=creation_time,
            ad_delivery_start=delivery_start,
            ad_delivery_stop=delivery_stop,
            languages=languages,
            countries=countries,
            raw=raw,
        )
    except Exception as e:
        logger.warning(f"Failed to parse ad: {e}")
        return None


class MetaGraphApiScraper:
    """
    Scrapes ads using Facebook's official Graph API.

    This is the preferred scraping method:
    - No proxies needed
    - No browser automation needed
    - Returns structured JSON with spend/impressions/demographics
    - Rate limited to ~1000 req/hour per token

    Usage:
        scraper = MetaGraphApiScraper(access_token="YOUR_TOKEN")
        ads = await scraper.search_ads(query="weight loss", country="US", limit=100)
    """

    def __init__(self, access_token: str, request_delay: float = 1.0):
        self.access_token = access_token
        self.request_delay = request_delay
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _make_request(
        self, params: dict[str, Any]
    ) -> tuple[list[dict], Optional[str], Optional[str]]:
        """
        Make a request to the ads_archive endpoint.
        Returns (ads, next_page_cursor, error_message).
        """
        client = await self._get_client()
        params["access_token"] = self.access_token
        params["fields"] = AD_FIELDS

        try:
            response = await client.get(ADS_ARCHIVE_URL, params=params)
            await asyncio.sleep(self.request_delay)

            if response.status_code == 200:
                data = response.json()
                ads = data.get("data", []) or []
                paging = data.get("paging", {}) or {}
                cursors = paging.get("cursors", {}) or {}
                next_cursor = cursors.get("after", "")
                return ads, next_cursor, None

            elif response.status_code == 400:
                err = response.json()
                err_msg = err.get("error", {}).get("message", response.text)
                logger.error(f"Graph API error: {err_msg}")
                return [], None, err_msg

            elif response.status_code == 613:
                return [], None, "RATE_LIMITED: Too many requests"

            else:
                return [], None, f"HTTP {response.status_code}: {response.text[:200]}"

        except httpx.TimeoutException:
            return [], None, "Request timeout"
        except Exception as e:
            logger.error(f"Graph API exception: {e}")
            return [], None, str(e)

    async def search_ads(
        self,
        query: str = "",
        country: str = "US",
        limit: int = 100,
        ad_status: str = "ACTIVE",
        platforms: Optional[list[str]] = None,
        offset: int = 0,
    ) -> tuple[list[GraphApiAd], Optional[str]]:
        """
        Search ads by keyword and country.

        Args:
            query: Search keyword(s)
            country: ISO country code (US, GB, DE, etc.)
            limit: Number of results (max ~1000 per call, paginate for more)
            ad_status: ACTIVE or ALL
            platforms: Filter by platform (facebook, instagram, etc.)
            offset: Result offset for pagination

        Returns:
            (list of GraphApiAd, error_message or None)
        """
        params: dict[str, Any] = {
            "ad_active_status": ad_status,
            "ad_reached_countries": [country],
            "limit": min(limit, 500),  # API caps at 500 per page
            "offset": offset,
        }

        if query:
            params["search_terms"] = query

        if platforms:
            params["publisher_platforms"] = platforms

        ads_raw, _, err = await self._make_request(params)

        if err:
            return [], err

        parsed = []
        for raw in ads_raw:
            ad = _parse_ad(raw)
            if ad and ad.ad_text:
                parsed.append(ad)

        return parsed, None

    async def search_ads_paginated(
        self,
        query: str = "",
        country: str = "US",
        max_ads: int = 500,
        ad_status: str = "ACTIVE",
    ) -> tuple[list[GraphApiAd], list[str]]:
        """
        Search ads with automatic pagination.

        Args:
            query: Search keyword(s)
            country: ISO country code
            max_ads: Maximum total ads to fetch (paginate until reached)
            ad_status: ACTIVE or ALL

        Returns:
            (list of GraphApiAd, list of error messages)
        """
        all_ads: list[GraphApiAd] = []
        errors: list[str] = []
        offset = 0
        page_size = 500

        while len(all_ads) < max_ads:
            ads, err = await self.search_ads(
                query=query,
                country=country,
                limit=page_size,
                ad_status=ad_status,
                offset=offset,
            )

            if err:
                if "RATE_LIMITED" in err:
                    errors.append(f"Rate limited at offset {offset}, stopping pagination")
                    break
                errors.append(err)
                break

            if not ads:
                break

            all_ads.extend(ads)
            logger.info(
                f"Graph API: fetched {len(ads)} ads (total: {len(all_ads)})"
            )

            if len(ads) < page_size:
                break  # No more pages

            offset += page_size

        return all_ads[:max_ads], errors

    async def search_multiple_countries(
        self,
        query: str = "",
        countries: Optional[list[str]] = None,
        max_per_country: int = 200,
        ad_status: str = "ACTIVE",
    ) -> dict[str, list[GraphApiAd]]:
        """
        Search ads across multiple countries sequentially.

        Args:
            query: Search keyword(s)
            countries: List of ISO country codes
            max_per_country: Max ads per country
            ad_status: ACTIVE or ALL

        Returns:
            Dict mapping country code -> list of ads
        """
        if countries is None:
            countries = ["US", "GB", "CA", "AU", "DE"]

        results: dict[str, list[GraphApiAd]] = {}
        errors_all: list[str] = []

        for country in countries:
            logger.info(f"Graph API: searching {country} for '{query}'")
            ads, errors = await self.search_ads_paginated(
                query=query,
                country=country,
                max_ads=max_per_country,
                ad_status=ad_status,
            )
            results[country] = ads
            errors_all.extend(errors)

            if errors_all and "RATE_LIMITED" in errors_all[-1]:
                logger.warning(f"Rate limited, stopping country search")
                break

        return results

    async def test_connection(self) -> tuple[bool, str]:
        """Test if the access token is valid."""
        try:
            client = await self._get_client()
            params = {
                "access_token": self.access_token,
                "fields": "id",
                "limit": 1,
            }
            response = await client.get(ADS_ARCHIVE_URL, params=params)
            data = response.json()

            if "error" in data:
                return False, data["error"].get("message", "Invalid token")

            return True, "Token valid"
        except Exception as e:
            return False, str(e)
