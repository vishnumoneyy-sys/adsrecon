"""URL parsing and resolution utilities for ADSRECON."""
from urllib.parse import urlparse, parse_qs, unquote
import re
from typing import Optional


def extract_page_id(url: str) -> Optional[str]:
    """Extract page_id from Meta Ads Library URL.

    Handles formats like:
      - https://www.facebook.com/ads/library/?view_all_page_id=123456
      - https://www.facebook.com/somepage/123456
    """
    if not url:
        return None
    match = re.search(r"[?&]view_all_page_id=(\d+)", url)
    if match:
        return match.group(1)
    match = re.search(r"facebook\.com/(?:pg/)?([^/?]+)/(\d+)", url)
    if match:
        return match.group(2)
    return None


def extract_fbclid(url: str) -> Optional[str]:
    """Extract fbclid from a Meta redirect URL."""
    if not url:
        return None
    match = re.search(r"[?&]fbclid=([^&\s]+)", url)
    if match:
        return match.group(1)
    return None


def extract_landing_url_from_fb_redirect(redirect_url: str) -> Optional[str]:
    """Extract the actual destination from Facebook's l.php redirect URL.

    Handles both l.facebook.com and l.messenger.com redirectors.
    """
    if not redirect_url:
        return None
    if "l.facebook.com" in redirect_url or "l.messenger.com" in redirect_url:
        params = parse_qs(urlparse(redirect_url).query)
        urls = params.get("u", params.get("url", []))
        if urls:
            return unquote(urls[0])
    return redirect_url


def normalize_url(url: str) -> str:
    """Normalize a URL for consistent comparison.

    Strips query strings, fragments, and trailing slashes.
    """
    if not url:
        return ""
    url = url.strip()
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
    except Exception:
        return url


def is_clean_domain(url: str) -> bool:
    """Check if URL has a trusted, non-affiliate TLD."""
    if not url:
        return False
    try:
        domain = urlparse(url).netloc.lower()
        clean_tlds = {".com", ".org", ".net", ".io", ".co", ".gov", ".edu"}
        return any(domain.endswith(tld) for tld in clean_tlds)
    except Exception:
        return False


def is_suspicious_domain(url: str) -> bool:
    """Check if URL has a suspicious TLD common in nutra/affiliate offers."""
    if not url:
        return False
    try:
        domain = urlparse(url).netloc.lower()
        suspicious_tlds = {
            ".top", ".xyz", ".click", ".icu", ".loan", ".work", ".party",
            ".racing", ".win", ".review", ".stream", ".date", ".faith",
            ".bid", ".trade", ".download", ".click", ".space", ".online",
            ".site", ".fun", ".buzz", ".link", ".pro", ".live",
        }
        return any(domain.endswith(tld) for tld in suspicious_tlds)
    except Exception:
        return False


def build_fbclid_url(base_url: str, fbclid: str) -> str:
    """Append fbclid to a URL if not already present."""
    if not base_url or not fbclid:
        return base_url
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}fbclid={fbclid}"
