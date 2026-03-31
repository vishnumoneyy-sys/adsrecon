"""Landing Page Ripper -- uses Playwright to render and capture actual landers."""
import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup
from playwright.async_api import Page

from services.cloaking_bypass import CloakingBypassService, CloakResult

logger = logging.getLogger("adsrecon.ripper")


# --------------------------------------------------------------------------- models


@dataclass
class RipResult:
    """
    Result of a single landing-page rip operation.
    """
    success: bool
    screenshot_path: Optional[str] = None
    html_path: Optional[str] = None
    video_urls: list[str] = field(default_factory=list)
    phone_numbers: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    title: str = ""
    final_url: str = ""
    cloak_result: Optional[CloakResult] = None
    device_used: str = "desktop"
    error: Optional[str] = None
    # Enriched fields
    meta_description: str = ""
    social_tags: dict = field(default_factory=dict)
    dom_depth: int = 0          # rough complexity metric
    html_size_bytes: int = 0
    links_found: int = 0

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "screenshot_path": self.screenshot_path,
            "html_path": self.html_path,
            "video_urls": self.video_urls,
            "phone_numbers": self.phone_numbers,
            "emails": self.emails,
            "title": self.title,
            "final_url": self.final_url,
            "cloak_result": self.cloak_result.to_dict() if self.cloak_result else None,
            "device_used": self.device_used,
            "error": self.error,
            "meta_description": self.meta_description,
            "social_tags": self.social_tags,
            "dom_depth": self.dom_depth,
            "html_size_bytes": self.html_size_bytes,
            "links_found": self.links_found,
        }


# --------------------------------------------------------------------------- ripper


class LanderRipper:
    """
    Uses Playwright to fully render and capture landing pages.

    The key insight that makes this work:
      1. We visit the URL *with* the ``fbclid`` parameter appended.
         The lander's cloaking middleware checks fbclid to decide whether to
         show the real product page or a safe wall.
      2. Playwright executes all client-side JS (React SPAs, delayed redirects,
         cloaking scripts), so we capture the actual rendered state.
      3. We take a full-page screenshot, save the sanitised HTML, and extract
         signals: videos, phone numbers, email addresses, Open Graph tags.
      4. The cloaking-bypass service compares the expected domain vs the final
         URL to detect domain-mismatch cloaking.

    Args:
        browser_pool:       BrowserPool instance (see browser/playwright_pool.py).
        cloaking_service:  CloakingBypassService instance.
        screenshots_dir:   Directory to save full-page screenshots.
        html_dumps_dir:    Directory to save sanitised HTML dumps.
        default_delay:     Seconds to wait after navigation for dynamic content.
    """

    # Common phone patterns used across US / CA / UK / AU / intl landers
    PHONE_PATTERNS = [
        # Standard US/CA: (123) 456-7890, 123-456-7890, +1 123.456.7890
        r"\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}",
        # UK: +44 7xxx xxxxxx
        r"\+44[-.\s]?[7-9]\d{2}[-.\s]?\d{3}[-.\s]?\d{3,4}",
        # International: +XX XXX/XXXX XXXX
        r"\+[0-9]{1,4}[-.\s]?[0-9]{2,4}[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,4}",
    ]

    PHONE_RE = re.compile("|".join(PHONE_PATTERNS), re.IGNORECASE)

    # Common nutra lander TLDs (suspicious)
    SUSPICIOUS_TLDS = {
        ".top", ".xyz", ".buzz", ".cc", ".rest", ".fit", ".work",
        ".click", ".link", ".loan", ".date", ".racing", ".win",
        ".download", ".stream", ".party", ".casa", ".icu", ".pw",
    }

    def __init__(
        self,
        browser_pool,                  #: BrowserPool
        cloaking_service: CloakingBypassService,
        screenshots_dir: str,
        html_dumps_dir: str,
        default_delay: float = 2.0,
    ):
        self.browser_pool = browser_pool
        self.cloaking = cloaking_service
        self.screenshots_dir = Path(screenshots_dir)
        self.html_dumps_dir = Path(html_dumps_dir)
        self.default_delay = default_delay

        # Ensure artifact directories exist
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.html_dumps_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ public API

    async def rip(
        self,
        landing_url: str,
        fbclid: Optional[str] = None,
        device: str = "desktop",
        proxy: Optional[str] = None,
        wait_for_selector: Optional[str] = None,
        timeout_ms: int = 30000,
    ) -> RipResult:
        """
        Fully render and capture a landing page.

        Args:
            landing_url:       The ad destination URL (may or may not have fbclid).
            fbclid:            Explicit fbclid to inject. Auto-extracted if omitted.
            device:            ``desktop`` (1280x720) or ``mobile`` (390x844).
            proxy:             Optional proxy URL for the browser session.
            wait_for_selector: CSS selector to wait for before capturing.
            timeout_ms:        Navigation timeout in milliseconds.

        Returns:
            :class:`RipResult` with screenshot paths, extracted signals, and
            cloaking analysis.
        """
        logger.info(
            f"[Ripper] Starting rip — url={landing_url[:60]} device={device}"
            f" fbclid={'yes' if fbclid else 'no'}"
        )

        instance = await self.browser_pool.acquire()
        if not instance:
            return RipResult(
                success=False,
                device_used=device,
                error="No browser available — pool exhausted",
            )

        page: Optional[Page] = None

        try:
            page = await instance.context.new_page()

            # --- Device emulation ---
            await self._apply_device(page, device)

            # --- Proxy ---
            if proxy:
                await instance.context.set_proxy(proxy)

            # --- Build URL with fbclid ---
            url_to_visit = self._build_url(landing_url, fbclid)
            logger.debug(f"[Ripper] Visiting: {url_to_visit[:80]}")

            # --- Navigate ---
            try:
                response = await page.goto(
                    url_to_visit,
                    wait_until="domcontentloaded",
                    timeout=timeout_ms,
                )
                status_code = response.status if response else 0
            except asyncio.TimeoutError:
                logger.warning(f"[Ripper] Navigation timeout: {landing_url[:60]}")
                return RipResult(
                    success=False,
                    device_used=device,
                    error=f"Navigation timed out after {timeout_ms}ms",
                )
            except Exception as nav_err:
                logger.warning(f"[Ripper] Navigation error: {nav_err}")
                status_code = 0

            # --- Wait for dynamic content ---
            await asyncio.sleep(self.default_delay)

            # --- Optional: wait for a specific selector ---
            if wait_for_selector:
                try:
                    await page.wait_for_selector(wait_for_selector, timeout=10000)
                except Exception:
                    logger.debug(f"[Ripper] Selector '{wait_for_selector}' not found; continuing")
            else:
                # Fallback: wait for network to be idle (up to 5s)
                try:
                    await page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass

            # --- Extract metadata ---
            final_url = page.url
            title = await self._safe_title(page)
            meta_desc, social_tags = await self._extract_meta(page)
            dom_depth, links_count = await self._count_dom_metrics(page)

            # --- Take screenshot ---
            screenshot_path = await self._take_screenshot(page, landing_url, device)

            # --- Capture and save HTML ---
            html_content = await page.content()
            html_path = self._save_html(html_content, landing_url, device)
            html_size = len(html_content.encode("utf-8", errors="replace"))

            # --- Extract signals from HTML ---
            video_urls = self._extract_videos(html_content)
            phone_numbers = self._extract_phones(html_content)
            emails = self._extract_emails(html_content)

            # --- Cloaking analysis ---
            cloak_result = await self.cloaking.bypass(
                landing_url=landing_url,
                fbclid=fbclid,
                use_proxy=bool(proxy),
                proxy_url=proxy,
            )

            # --- Risk assessment ---
            self._log_risk_signals(
                landing_url=landing_url,
                final_url=final_url,
                cloak_result=cloak_result,
                phones=phone_numbers,
                emails=emails,
                videos=video_urls,
            )

            logger.info(
                f"[Ripper] ✅ Complete — {landing_url[:40]} → {final_url[:40]} "
                f"| title={title[:40]} | phones={len(phone_numbers)} "
                f"| videos={len(video_urls)} | cloaked={cloak_result.is_cloaked}"
            )

            return RipResult(
                success=True,
                screenshot_path=screenshot_path,
                html_path=html_path,
                video_urls=video_urls,
                phone_numbers=phone_numbers,
                emails=emails,
                title=title,
                final_url=final_url,
                cloak_result=cloak_result,
                device_used=device,
                error=None,
                meta_description=meta_desc,
                social_tags=social_tags,
                dom_depth=dom_depth,
                links_found=links_count,
                html_size_bytes=html_size,
            )

        except Exception as exc:
            logger.error(f"[Ripper] Unexpected error: {exc}", exc_info=True)
            return RipResult(
                success=False,
                device_used=device,
                error=str(exc),
            )

        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            await self.browser_pool.release(instance)

    async def rip_multiple(
        self,
        urls: list[str],
        fbclids: Optional[dict[str, str]] = None,
        device: str = "desktop",
        max_concurrent: int = 3,
    ) -> list[RipResult]:
        """
        Rip multiple URLs concurrently with a concurrency cap.

        Args:
            urls:           List of landing URLs to rip.
            fbclids:        Optional dict mapping url -> fbclid.
            device:         Device emulation to use.
            max_concurrent: Maximum simultaneous browser instances.

        Returns:
            List of :class:`RipResult` in the same order as ``urls``.
        """
        fbclids = fbclids or {}
        semaphore = asyncio.Semaphore(max_concurrent)

        async def rip_one(url: str) -> RipResult:
            async with semaphore:
                return await self.rip(
                    url,
                    fbclid=fbclids.get(url),
                    device=device,
                )

        return await asyncio.gather(*[rip_one(u) for u in urls])

    # ------------------------------------------------------------------ URL helpers

    def _get_tld(self, url: str) -> str:
        """Extract the TLD (e.g. .com, .top) from a URL."""
        try:
            from urllib.parse import urlparse
            netloc = urlparse(url).netloc
            parts = netloc.rsplit(".", 1)
            return "." + parts[-1] if parts else ""
        except Exception:
            return ""

    async def _apply_device(self, page: Page, device: str) -> None:
        """Configure viewport and user-agent for the target device."""
        if device == "mobile":
            await page.set_viewport_size({"width": 390, "height": 844})
            await page.set_extra_http_headers({
                "User-Agent": (
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
                    "Mobile/15E148 Safari/604.1"
                )
            })
        else:
            await page.set_viewport_size({"width": 1280, "height": 720})

    # ------------------------------------------------------------------ URL helpers

    def _build_url(self, url: str, fbclid: Optional[str]) -> str:
        """Append fbclid to the URL if it's not already present."""
        if not url:
            return ""
        url = url.strip()
        if fbclid and "fbclid=" not in url:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}fbclid={fbclid}"
        return url

    # ------------------------------------------------------------------ screenshot

    async def _take_screenshot(
        self,
        page: Page,
        landing_url: str,
        device: str,
    ) -> Optional[str]:
        """Save a full-page PNG screenshot and return the file path."""
        try:
            token = hashlib.md5(f"{landing_url}{device}".encode()).hexdigest()[:16]
            filename = f"{token}_{device}.png"
            path = self.screenshots_dir / filename

            await page.screenshot(
                path=str(path),
                full_page=True,
                timeout=15000,
            )

            return str(path)

        except Exception as exc:
            logger.error(f"[Ripper] Screenshot failed: {exc}")
            return None

    # ------------------------------------------------------------------ HTML

    def _save_html(
        self,
        html: str,
        landing_url: str,
        device: str,
    ) -> Optional[str]:
        """
        Sanitise and save the page HTML.

        Sanitisation removes:
          - <script> tags (prevents re-execution of obfuscated JS)
          - on* event attributes (e.g. onclick, onload)
          - <iframe> elements (external embeds)
          - data: URIs (often used in tracking pixels)
        """
        try:
            soup = BeautifulSoup(html, "lxml")

            # Remove scripts
            for tag in soup.find_all("script"):
                tag.decompose()

            # Remove event handlers
            for tag in soup.find_all(True):
                for attr in list(tag.attrs):
                    if attr.startswith("on") or attr in ("javascript:", "data-href"):
                        del tag[attr]

            # Remove iframes
            for iframe in soup.find_all("iframe"):
                iframe.decompose()

            # Remove tracking data: URIs from img src
            for img in soup.find_all("img"):
                src = img.get("src", "")
                if src.startswith("data:"):
                    img["src"] = ""

            # Remove FB pixel / Meta tracking divs by class
            for tag in soup.find_all(class_=re.compile(r"fb-pixel|meta-tracker", re.I)):
                tag.decompose()

            sanitized = str(soup.prettify())

            token = hashlib.md5(f"{landing_url}{device}".encode()).hexdigest()[:16]
            filename = f"{token}_{device}.html"
            path = self.html_dumps_dir / filename

            with open(path, "w", encoding="utf-8", errors="replace") as f:
                f.write(sanitized)

            return str(path)

        except Exception as exc:
            logger.error(f"[Ripper] HTML save failed: {exc}")
            return None

    # ------------------------------------------------------------------ extraction

    def _extract_videos(self, html: str) -> list[str]:
        """Find all video URLs (mp4, webm, mov) in the HTML."""
        videos: set[str] = set()
        soup = BeautifulSoup(html, "lxml")

        # <video> and <source>
        for video in soup.find_all("video"):
            for attr in ("src", "data-src", "poster"):
                val = video.get(attr, "")
                if val and not val.startswith("data:"):
                    videos.add(val)
            for source in video.find_all("source"):
                src = source.get("src", "")
                if src:
                    videos.add(src)

        # YouTube / Vimeo / TikTok embeds
        for iframe in soup.find_all("iframe"):
            src = iframe.get("src", "")
            if any(p in src for p in ("youtube.com/embed", "player.vimeo.com", "tiktok.com/embed")):
                videos.add(src)

        # Direct download links containing video extensions
        video_exts = (".mp4", ".webm", ".mov", ".m3u8")
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if any(href.lower().endswith(ext) for ext in video_exts):
                videos.add(href)

        return list(videos)[:10]

    def _extract_phones(self, html: str) -> list[str]:
        """Find phone numbers in the HTML using multiple regex patterns."""
        phones: set[str] = set()

        for match in self.PHONE_RE.finditer(html):
            raw = match.group()
            cleaned = re.sub(r"[^\d+]", "", raw)
            # Valid phone: at least 10 digits
            if len(cleaned) >= 10:
                phones.add(cleaned)

        return list(phones)[:5]

    def _extract_emails(self, html: str) -> list[str]:
        """Find email addresses in the HTML."""
        email_re = re.compile(
            r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
            re.IGNORECASE,
        )
        emails: set[str] = set()

        for match in email_re.finditer(html):
            email = match.group().lower()
            # Filter out common placeholder patterns
            if not any(
                placeholder in email
                for placeholder in (
                    "example.com", "example.org", "test.com",
                    "domain.com", "localhost", "yourname",
                )
            ):
                emails.add(email)

        return list(emails)[:5]

    # ------------------------------------------------------------------ page metadata

    async def _safe_title(self, page: Page) -> str:
        try:
            return (await page.title()) or ""
        except Exception:
            return ""

    async def _extract_meta(self, page: Page) -> tuple[str, dict]:
        """Extract Open Graph / Twitter Card meta tags."""
        meta_desc = ""
        social_tags: dict[str, str] = {}

        try:
            meta_desc = await page.evaluate("""() => {
                const el = document.querySelector(
                    'meta[name="description"], meta[property="og:description"]'
                );
                return el ? el.getAttribute('content') || '' : '';
            }""")

            og_tags = ["og:title", "og:image", "og:description", "og:url",
                       "twitter:title", "twitter:description", "twitter:image"]
            for tag in og_tags:
                val = await page.evaluate(
                    f"""() => {{
                        const el = document.querySelector(
                            'meta[property="{tag}"]'
                        ) || document.querySelector('meta[name="{tag}"]');
                        return el ? el.getAttribute('content') || '' : '';
                    }}"""
                )
                if val:
                    social_tags[tag] = val

        except Exception as exc:
            logger.debug(f"[Ripper] Meta extraction error: {exc}")

        return meta_desc, social_tags

    async def _count_dom_metrics(self, page: Page) -> tuple[int, int]:
        """Get DOM depth and link count for complexity scoring."""
        try:
            return await page.evaluate("""() => {
                // Max DOM depth
                function maxDepth(node, d = 0) {
                    if (!node.childNodes || !node.childNodes.length) return d;
                    return Math.max(...Array.from(node.childNodes).map(
                        n => maxDepth(n, d + 1)
                    ));
                }

                // Link count
                const links = document.querySelectorAll('a[href]').length;

                return [maxDepth(document.body, 0), links];
            }""")
        except Exception:
            return 0, 0

    # ------------------------------------------------------------------ risk logging

    def _log_risk_signals(
        self,
        landing_url: str,
        final_url: str,
        cloak_result: CloakResult,
        phones: list[str],
        emails: list[str],
        videos: list[str],
    ) -> None:
        """Log a structured risk summary for each rip."""
        signals: list[str] = []

        if cloak_result.is_cloaked:
            signals.append(f"CLOAKED({cloak_result.cloak_type})")

        if len(phones) >= 2:
            signals.append(f"MULTI_PHONE({len(phones)})")

        if len(emails) >= 2:
            signals.append(f"MULTI_EMAIL({len(emails)})")

        if len(videos) >= 2:
            signals.append(f"MULTI_VIDEO({len(videos)})")

        tld = self._get_tld(landing_url)
        if tld in self.SUSPICIOUS_TLDS:
            signals.append(f"SUSPICIOUS_TLD({tld})")

        if final_url != landing_url and not cloak_result.is_cloaked:
            signals.append("REDIRECT_NO_CLOAK")

        if signals:
            logger.warning(f"[RiskSignals] {' | '.join(signals)} | url={landing_url[:50]}")
