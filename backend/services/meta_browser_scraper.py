"""Meta Ads Library Browser Scraper -- renders pages with a real Playwright browser.

This module uses headless Chromium (via the shared BrowserPool) to scrape Meta's
Ads Library.  Because a real browser executes all JavaScript, Meta cannot block us
with the 403 / CAPTCHA walls that httpx-based scrapers encounter.

Key techniques:
  - Shared BrowserPool (no per-instance browser launch overhead)
  - Stealth launch args + injected JS to avoid headless-detection
  - networkidle wait + lazy-scroll to trigger infinite-scroll pagination
  - page.evaluate() DOM extraction for fully-rendered ad cards
  - Graceful degradation when the pool is unavailable or the page is blocked

Usage:
    scraper = MetaBrowserScraper(browser_pool)   # pass existing pool
    async with scraper:
        ads = await scraper.search_keyword("weight loss", "US")
        ads = await scraper.scrape_page("https://www.facebook.com/ads/library/?...")

The returned objects are standard :class:`MetaAd` instances compatible with the
existing router code.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import re
import sys
import time
from typing import TYPE_CHECKING, Any, Optional

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

# Import the dataclass so callers get a compatible type
from .meta_scraper import MetaAd

if TYPE_CHECKING:
    from ..browser.playwright_pool import BrowserInstance, BrowserPool

logger = logging.getLogger("adsrecon.meta_browser_scraper")

# --------------------------------------------------------------------------- stealth
# Anti-detection browser launch arguments.
# Keep in sync with playwright_pool.py LAUNCH_ARGS — these are additive only.
STEALTH_LAUNCH_ARGS: list[str] = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-web-security",
    "--disable-features=IsolateOrigins,site-per-process",
    "--window-size=1920,1080",
    "--start-maximized",
    # Anti-automation flags (remove headless fingerprint)
    "--disable-blink-features=AutomationControlled",
    "--exclude-switches=enable-automation",
    "--no-first-run",
    "--no-service-autorun",
    "--password-store=basic",
    "--disable-default-apps",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-sync",
    "--metrics-recording-only",
    "--mute-audio",
]

# JavaScript injected into every page immediately after navigation.
# Patches navigator properties that Meta (and other sites) check to detect
# headless / automated browsers.
STEALTH_SCRIPT: str = """
(function () {
    'use strict';

    // 1. Remove the webdriver flag — the primary headless detection vector
    Object.defineProperty(navigator, 'webdriver', {
        get: function () { return undefined; },
        configurable: true,
        enumerable: true,
    });

    // 2. Spoof plugins (headless Chrome exposes none by default)
    Object.defineProperty(navigator, 'plugins', {
        get: function () {
            return [
                { name: 'Chrome PDF Plugin',        filename: 'internal-pdf-viewer' },
                { name: 'Chrome PDF Viewer',        filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                { name: 'Native Client',            filename: 'internal-nacl-plugin' },
            ];
        },
        configurable: true,
        enumerable: true,
    });

    // 3. Spoof languages (headless often only exposes 'en-US')
    Object.defineProperty(navigator, 'languages', {
        get: function () { return ['en-US', 'en', 'en-GB']; },
        configurable: true,
        enumerable: true,
    });

    // 4. Mock Permissions.query() so the 'notifications' check doesn't fail
    const _origQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = function (params) {
        if (params.name === 'notifications') {
            return Promise.resolve({ state: Notification.permission === 'granted' ? 'granted' : 'denied' });
        }
        return _origQuery ? _origQuery.call(window.navigator.permissions, params) : Promise.resolve('denied');
    };

    // 5. Remove known automation detection globals injected by ChromeDriver / Puppeteer
    delete window.cdc_adoQpoasnfa86pfoZLjfGJNvsSh;
    delete window.$cdc_asdjflasutopfhvcZLmcfl_;
    delete window.__webdriver_evaluate;
    delete window.__selenium_evaluate;
    delete window.__webdriver_script_function;
    delete window.__webdriver_script_func;
    delete window.__webdriver_script_named;
    delete window.__fxdriver_evaluate;
    delete window.__driver_unwrapped;
    delete window.__webdriver_unwrapped;
    delete window.__driver_evaluate;
    delete window.__fxdriver_unwrapped;

    // 6. Patch Chrome runtime to hide automation extensions
    if (window.chrome && window.chrome.runtime) {
        try {
            Object.defineProperty(window.chrome.runtime, 'id', { get: () => undefined });
        } catch (_) {}
    }

    // 7. Remove any 'runner' classes added by automation tools
    try {
        document.documentElement.removeAttribute('webdriver');
        document.documentElement.classList.remove('grv-webdriver');
    } catch (_) {}

    // 8. Override chrome.send to prevent detection via command checking
    const _origSend = window.chrome && window.chrome.send;
    if (_origSend) {
        window.chrome.send = function () {};
    }
})();
"""

# --------------------------------------------------------------------------- DOM extraction

# JavaScript evaluated inside the rendered page to pull ad data.
# Targets the current Meta Ads Library DOM structure (as of 2024-2025).
# Falls back gracefully when selectors don't match.
EXTRACT_ADS_SCRIPT: str = r"""
function () {
    'use strict';
    var ads = [];

    // ------------------------------------------------------------------ helpers
    function txt(el) {
        return el ? (el.innerText || el.textContent || '').trim() : '';
    }

    function atr(el, name) {
        return el ? (el.getAttribute(name) || '').trim() : '';
    }

    function getFbclid(href) {
        if (!href) return '';
        var m = href.match(/[?&]fbclid=([^&\s]+)/);
        return m ? m[1] : '';
    }

    function getLandingUrl(href) {
        if (!href) return '';
        try {
            var u = new URL(href.startsWith('http') ? href : 'https://' + href);
            var p = u.searchParams;
            if (u.hostname === 'l.facebook.com' || u.hostname === 'lm.facebook.com') {
                var target = p.get('u') || p.get('url') || p.get('l');
                if (target) {
                    try { return decodeURIComponent(target); } catch (_) { return target; }
                }
            }
            if (u.hostname === 'lnk.sk') {
                var target = p.get('l') || p.get('url');
                if (target) {
                    try { return decodeURIComponent(target); } catch (_) { return target; }
                }
            }
            return href;
        } catch (_) { return href; }
    }

    // Find the ad card boundary by walking up from "Sponsored" element.
    // Sponsored is inside a <strong> which is nested 2-5 levels inside the card.
    // The card itself is ~356px wide. We walk up and look for the sized container.
    function findCardBoundary(el) {
        if (!el) return null;
        var depth = 0;
        var cur = el;
        var best = null;
        while (cur && depth < 15) {
            var tag = cur.tagName ? cur.tagName.toLowerCase() : '';
            if (tag === 'section' || tag === 'main' || tag === 'article') return cur;
            try {
                var r = cur.getBoundingClientRect();
                // Ad cards: ~356px wide, 150-620px tall (drop top>100 — page may be scrolled)
                if (r.width >= 300 && r.width <= 400 &&
                    r.height >= 150 && r.height <= 620) {
                    best = cur;
                }
            } catch (_) {}
            cur = cur.parentElement;
            depth++;
        }
        return best || el;
    }

    // Extract clean ad text from a card element
    // Removes: meta UI text, nav text, library IDs, dates, platform labels, age gates
    // Also strips the page name from the beginning of ad text
    function cleanAdText(card, pageName) {
        var raw = txt(card);
        // If the raw text contains age-gate or login wall, this is a blocked ad — skip
        if (/to see this content, you need to confirm your age|to see this ad,? ?log ?in/i.test(raw)) {
            return '';
        }
        // Patterns to strip from ad text
        var STRIP_RE = /library id:\s*\d+|started running on\s*\d+|platforms?\s*(facebook|instagram|messenger|audience network)?|active|inactive|view more|see less|branded content|united states|select country|current location|all\s*countries|allafghanistan|sponsored|learn more|see less|shop now|sign up|get offer|get started|get quote|book now|contact us|visit site|click here|order now|facebook|instagram|messenger/i;
        var cleaned = raw.replace(STRIP_RE, ' ').replace(/\s+/g, ' ').trim();
        // Strip page name from beginning (if present)
        if (pageName && cleaned.toLowerCase().startsWith(pageName.toLowerCase())) {
            cleaned = cleaned.slice(pageName.length).trim();
        }
        return cleaned.length >= 15 ? cleaned.slice(0, 500) : '';
    }

    // Extract the advertiser page name from the card
    function getPageName(card) {
        var SKIP = ['meta ad library', 'ad library', 'ad library report', 'ad library api',
                    'facebook', 'meta', 'learn more', 'see more', 'shop now', 'sign up',
                    'get offer', 'get started', 'get quote', 'book now', 'contact us',
                    'visit site', 'click here', 'order now', 'sponsored',
                    'to see this content', 'to see this ad', 'log in', 'confirm your age'];
        if (!card.querySelectorAll) return '';
        var links = card.querySelectorAll('a[href]');
        for (var i = 0; i < links.length; i++) {
            var t = txt(links[i]).trim();
            var low = t.toLowerCase();
            if (t.length > 2 && t.length < 150) {
                var isSkip = false;
                for (var s = 0; s < SKIP.length; s++) {
                    if (low.includes(SKIP[s])) { isSkip = true; break; }
                }
                if (!isSkip) return t;
            }
        }
        return '';
    }

    // ------------------------------------------------------------------ card discovery
    // Strategy: find elements containing "Sponsored" text (guaranteed to be ad cards)
    // and walk up to the card boundary.
    // Fallback: scan divs by size (356px wide, in content area, external links)
    var seenUrls = {};
    var seenTexts = {};
    var cardSet = new Set();

    function addCard(card) {
        if (!card || cardSet.has(card)) return;
        cardSet.add(card);
    }

    // Primary: find "Sponsored" text anchors — these are always ad card headers
    var allTextNodes;
    try {
        var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
        allTextNodes = [];
        var node;
        while (node = walker.nextNode()) {
            var v = (node.nodeValue || '').trim();
            if (v.length > 5 && v.length < 50) allTextNodes.push(node);
        }
    } catch (_) { allTextNodes = []; }

    for (var tni = 0; tni < allTextNodes.length; tni++) {
        var tn = allTextNodes[tni];
        if ((tn.nodeValue || '').trim().toLowerCase() === 'sponsored') {
            // Walk up from the text node's parent to find the card boundary
            var el = tn.parentElement;
            if (!el) continue;
            var boundary = findCardBoundary(el);
            if (boundary) addCard(boundary);
        }
    }

    // Secondary: find elements by size (ad cards are ~356px wide)
    if (cardSet.size < 3) {
        cardSet = new Set();
        var allDivs = document.querySelectorAll('div');
        for (var di = 0; di < allDivs.length; di++) {
            var dv = allDivs[di];
            try {
                var r = dv.getBoundingClientRect();
                // Ad cards: ~356px wide, 200-600px tall, in content (top > 180)
                if (r.width >= 340 && r.width <= 380 &&
                    r.height >= 180 && r.height <= 620) {
                    var boundary = findCardBoundary(dv);
                    if (boundary) addCard(boundary);
                }
            } catch (_) {}
        }
    }

    // ------------------------------------------------------------------ extract from cards
    var cardList = Array.from(cardSet);
    for (var ci = 0; ci < cardList.length; ci++) {
        var card = cardList[ci];

        // Skip nav/header/form
        var inBad = false;
        var par = card.parentElement;
        for (var pi = 0; pi < 8 && par; pi++) {
            var t = par.tagName ? par.tagName.toLowerCase() : '';
            if (t === 'nav' || t === 'header' || t === 'form') { inBad = true; break; }
            par = par.parentElement;
        }
        if (inBad) continue;

        var rawText = txt(card);
        if (rawText.length < 30) continue;

        // Get page name first (before cleaning ad text)
        var pageName = getPageName(card);
        var adText = cleanAdText(card, pageName);
        if (!adText) continue;
        if (seenTexts[adText]) continue;
        seenTexts[adText] = true;

        // Extract URLs, CTA, library ID
        // Meta ads: CTA links may be internal (/ads/...) or external (l.facebook.com)
        // We capture any link with fbclid OR any external http link
        var landingUrl = '', fbclid = '', libraryId = '', cta = '';
        var links = card.querySelectorAll ? card.querySelectorAll('a[href]') : [];
        for (var li = 0; li < links.length; li++) {
            var href = atr(links[li], 'href');
            if (!href) continue;

            if (!cta) {
                var ct = txt(links[li]).trim().toLowerCase();
                if (ct.length > 0 && ct.length < 80 &&
                    ct !== 'learn more' && ct !== 'sponsored' && ct !== 'see more') {
                    cta = txt(links[li]).trim();
                }
            }

            // Capture fbclid from ANY link (even internal /ads/ links)
            if (!fbclid) fbclid = getFbclid(href);

            // Landing URL: external links OR l.facebook.com redirects
            if (!landingUrl) {
                if (!href.startsWith('#')) {
                    landingUrl = getLandingUrl(href);
                }
            }

            if (!libraryId) {
                var m = href.match(/[?&]id=(\d+)/) || href.match(/\/ads\/[^/]+\/(\d+)/);
                if (m) libraryId = m[1];
            }
        }

        // Require either a landing URL or fbclid to be a valid ad
        if (!landingUrl && !fbclid) continue;
        if (landingUrl && seenUrls[landingUrl]) continue;
        if (landingUrl) seenUrls[landingUrl] = true;

        // Extract image
        var imageUrl = '';
        if (card.querySelector) {
            var imgs = card.querySelectorAll('img[src]');
            for (var ii = 0; ii < imgs.length; ii++) {
                var src = atr(imgs[ii], 'src') || '';
                if (!src || src.includes('static.xx.fbcdn.net') || src.includes('scontent')) continue;
                var ir;
                try { ir = imgs[ii].getBoundingClientRect(); } catch (_) {}
                if (ir && ir.width >= 80 && ir.height >= 60) {
                    imageUrl = src; break;
                }
            }
        }

        // Platforms
        var platforms = ['facebook'];
        var full = ((card.innerHTML || '') + (card.innerText || '')).toLowerCase();
        if (full.includes('instagram')) platforms.push('instagram');
        if (full.includes('messenger')) platforms.push('messenger');

        // Days running
        var daysRunning = 0;
        var dm = adText.match(/(\d+)\s*day/i);
        if (dm) daysRunning = parseInt(dm[1], 10) || 0;

        ads.push({
            text:        adText.slice(0, 500),
            pageName:    pageName.slice(0, 200),
            landingUrl:  landingUrl.slice(0, 1000),
            fbclid:      fbclid.slice(0, 500),
            libraryId:   libraryId || '',
            imageUrl:    imageUrl.slice(0, 1000),
            cta:         cta.slice(0, 100),
            platforms:   platforms,
            isActive:    true,
            daysRunning: daysRunning,
        });
    }

    return ads;
}
"""

# --------------------------------------------------------------------------- bot / wall detection

ACCESS_DENIED_PATTERNS = [
    "access restricted",
    "access denied",
    "login to facebook",
    "log in to continue",
    "sign in to facebook",
    "confirm your identity",
    "unusual login activity",
    "you can't use this feature",
    "something went wrong",
    "page not found",
    "this content isn't available right now",
    "check point",
    "please verify",
    "suspicious activity",
]


async def _detect_access_denied(page: Page) -> bool:
    """Return True if the current page is showing a block / login wall."""
    try:
        text = await page.content()
    except Exception:
        return False
    text_lower = text.lower()
    return any(pat in text_lower for pat in ACCESS_DENIED_PATTERNS)


# --------------------------------------------------------------------------- scraper


class MetaBrowserScraper:
    """
    Scrapes Meta Ads Library using a real Playwright browser from the shared pool.

    This approach uses headless Chromium to:
      1. Navigate to Meta Ads Library pages
      2. Execute all JavaScript (Meta uses JS heavily for ad rendering)
      3. Extract fully-rendered ad data from the DOM

    This is MORE RELIABLE than httpx-based scraping because:
      - Real browser fingerprint (User-Agent, WebGL, Canvas, etc.)
      - Full JavaScript execution
      - Cookie / session management built into the context
      - Anti-detection stealth injection

    The scraper does NOT create its own browser instances — it borrows from
    the shared :class:`BrowserPool`.  If the pool is None or exhausted, all
    methods return empty results gracefully.

    Usage::

        async with MetaBrowserScraper(browser_pool) as scraper:
            ads = await scraper.search_keyword("weight loss", "US")
            ads = await scraper.scrape_page("https://www.facebook.com/ads/library/?...")

    Args:
        browser_pool:  A pre-initialised :class:`BrowserPool` instance.
                       May be None (methods degrade to empty results with a warning).

    Keyword-argument options (passed as **kwargs):

        scroll_count        (int)   Number of lazy-scroll iterations.  Default: 5.
        scroll_delay_ms     (int)   Milliseconds to wait between scrolls.  Default: 800.
        network_timeout_ms  (int)   Network-idle timeout in ms.  Default: 20000.
        nav_timeout_ms      (int)   Page navigation timeout in ms.  Default: 30000.
        pool_wait_timeout   (float) Seconds to wait for a pool instance.  Default: 10.0.
        stealth             (bool)  Inject anti-detection JS on every page.  Default: True.
    """

    BASE_URL = "https://www.facebook.com/ads/library/"

    def __init__(
        self,
        browser_pool: Optional["BrowserPool"] = None,
        *,
        scroll_count: int = 5,
        scroll_delay_ms: int = 800,
        network_timeout_ms: int = 20000,
        nav_timeout_ms: int = 30000,
        pool_wait_timeout: float = 10.0,
        stealth: bool = True,
    ):
        self._pool: Optional["BrowserPool"] = browser_pool
        self.scroll_count = scroll_count
        self.scroll_delay_ms = scroll_delay_ms
        self.network_timeout_ms = network_timeout_ms
        self.nav_timeout_ms = nav_timeout_ms
        self.pool_wait_timeout = pool_wait_timeout
        self.stealth = stealth

        # Populated in __aenter__
        self._instance: Optional["BrowserInstance"] = None
        self._page: Optional[Page] = None
        self._active = False

    # ------------------------------------------------------------------ context manager

    async def __aenter__(self) -> "MetaBrowserScraper":
        if self._pool is None:
            logger.warning("MetaBrowserScraper: no BrowserPool provided — running in degraded mode")
            return self

        logger.debug("Waiting for a browser instance from the pool...")
        start = time.monotonic()
        waited = 0.0

        while waited < self.pool_wait_timeout:
            self._instance = await self._pool.acquire()
            if self._instance is not None:
                break
            await asyncio.sleep(0.5)
            waited = time.monotonic() - start

        if self._instance is None:
            logger.warning(
                f"No browser available after {self.pool_wait_timeout}s — running in degraded mode"
            )
            return self

        logger.debug(f"Browser acquired: {self._instance.instance_id}")

        try:
            self._page = await self._instance.context.new_page()
        except Exception as exc:
            logger.error(f"Failed to open new page: {exc}")
            await self._pool.release(self._instance)
            self._instance = None
            return self

        self._active = True
        logger.info("MetaBrowserScraper ready")
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._page is not None:
            try:
                await self._page.close()
            except Exception as exc:
                logger.debug(f"Error closing page: {exc}")
            self._page = None

        if self._instance is not None and self._pool is not None:
            await self._pool.release(self._instance)
            logger.debug(f"Browser released: {self._instance.instance_id}")
            self._instance = None

        self._active = False
        logger.debug("MetaBrowserScraper shut down")

    # ------------------------------------------------------------------ public API

    async def search_keyword(
        self,
        keyword: str,
        country: str = "US",
    ) -> list[MetaAd]:
        """
        Search the Ads Library by keyword and return matching ads.

        Navigation:
            https://www.facebook.com/ads/library/?search_type=keyword
                &q={keyword}&country={country}&active_status=active

        Args:
            keyword:  Search term.
            country:  2-letter country code.  Default ``US``.

        Returns:
            List of :class:`MetaAd` objects found on the rendered page.
        """
        logger.info(f"Browser search: keyword='{keyword}' country={country}")

        if not self._active or self._page is None:
            logger.warning("search_keyword called but scraper is not active — returning empty list")
            return []

        encoded = keyword.replace(" ", "+")
        url = (
            f"{self.BASE_URL}"
            f"?search_type=keyword&q={encoded}"
            f"&country={country}"
            f"&active_status=active"
            f"&ad_type=all"
        )

        try:
            await self._navigate_with_stealth(url)
            await self._scroll_and_wait()
        except Exception as exc:
            logger.error(f"search_keyword navigation failed: {exc}")
            return []

        return await self._extract_ads_from_page()

    async def scrape_page(self, page_url: str) -> list[MetaAd]:
        """
        Navigate to a specific transparency page URL and extract ads.

        The URL should contain ``view_all_page_id``:
            https://www.facebook.com/ads/library/?view_all_page_id=123456&...

        Args:
            page_url:  Full transparency page URL.

        Returns:
            List of :class:`MetaAd` objects found on the rendered page.
        """
        logger.info(f"Browser scrape: {page_url[:120]}")

        if not self._active or self._page is None:
            logger.warning("scrape_page called but scraper is not active — returning empty list")
            return []

        try:
            await self._navigate_with_stealth(page_url)
            await self._scroll_and_wait()
        except Exception as exc:
            logger.error(f"scrape_page navigation failed: {exc}")
            return []

        return await self._extract_ads_from_page()

    async def search_keyword_multi(
        self,
        keyword: str,
        countries: list[str],
    ) -> dict[str, list[MetaAd]]:
        """
        Search the Ads Library by keyword across multiple countries.

        Each country is queried sequentially using the same browser instance
        (cookies / session persist across searches, which may improve results).

        Args:
            keyword:   Search term.
            countries: List of 2-letter country codes (e.g. ``["US", "GB", "DE"]``).

        Returns:
            Dict mapping country code -> list of :class:`MetaAd` objects.
        """
        logger.info(f"Multi-country browser search: '{keyword}' in {countries}")
        results: dict[str, list[MetaAd]] = {}

        for country in countries:
            try:
                ads = await self.search_keyword(keyword, country)
                results[country] = ads
                logger.info(f"  {country}: {len(ads)} ads extracted")
            except Exception as exc:
                logger.warning(f"  {country}: error — {exc}")
                results[country] = []

        return results

    # ------------------------------------------------------------------ navigation helpers

    async def _navigate_with_stealth(self, url: str) -> None:
        """
        Navigate to ``url`` with anti-detection measures applied.

        Steps:
          1. Inject stealth JS before navigation
          2. Navigate with navigation_timeout
          3. Wait for networkidle
          4. Re-inject stealth JS after load (DOM may have reset it)
          5. Check for access-denied / login wall
        """
        if self._page is None:
            return

        # Inject once before navigation — covers the initial page load
        if self.stealth:
            await self._page.add_init_script(script=STEALTH_SCRIPT)

        try:
            await self._page.goto(
                url,
                wait_until="networkidle",
                timeout=self.nav_timeout_ms,
            )
        except PlaywrightTimeout:
            logger.warning(f"Navigation timeout ({self.nav_timeout_ms}ms) — trying domcontentloaded")
            try:
                await self._page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self.nav_timeout_ms,
                )
                await asyncio.sleep(3)
            except Exception as nav_exc:
                logger.error(f"Fallback navigation also failed: {nav_exc}")
                raise

        # Re-inject after load (some sites re-initialise the DOM)
        if self.stealth:
            try:
                await self._page.add_init_script(script=STEALTH_SCRIPT)
            except Exception as inj_exc:
                logger.debug(f"Re-inject stealth script failed: {inj_exc}")

        # Check for block pages
        if await _detect_access_denied(self._page):
            logger.warning(
                f"Access-denied / login wall detected on {url[:80]}. "
                "Consider using a different IP or proxy."
            )
            return

        logger.debug(f"Page loaded: {url[:80]}")

    async def _scroll_and_wait(self) -> None:
        """
        Perform lazy-scroll iterations to trigger infinite-scroll pagination.

        Each iteration:
          1. Scroll to the bottom of the page
          2. Wait ``scroll_delay_ms`` for new content to load
        """
        if self._page is None:
            return

        logger.debug(f"Scrolling {self.scroll_count} times (delay={self.scroll_delay_ms}ms)")

        for i in range(self.scroll_count):
            try:
                # Scroll to the bottom (smooth behavior gives more time to load)
                await self._page.evaluate(
                    "window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })"
                )
                await asyncio.sleep(self.scroll_delay_ms / 1000)

                # Also try "load more" button if present (some Meta pages have one)
                try:
                    load_more = self._page.locator('text="See more"').first
                    try:
                        await asyncio.wait_for(load_more.wait_for(state="visible", timeout=1.0), timeout=2.0)
                        await load_more.click()
                        await asyncio.sleep(self.scroll_delay_ms / 1000)
                    except (PlaywrightTimeout, asyncio.TimeoutError):
                        pass  # No "see more" button — not critical
                except Exception:
                    pass  # No "see more" button — not critical

            except PlaywrightTimeout:
                logger.debug(f"Scroll iteration {i + 1} timed out — continuing")
            except Exception as exc:
                logger.debug(f"Scroll iteration {i + 1} error: {exc}")

        # Snap back to top after scrolling (avoids weird render states)
        try:
            await self._page.evaluate("window.scrollTo({ top: 0 })")
            await asyncio.sleep(0.5)
        except Exception:
            pass

    # ------------------------------------------------------------------ extraction

    async def _extract_ads_from_page(self) -> list[MetaAd]:
        """
        Run the DOM extraction script inside the current page and return
        a list of :class:`MetaAd` objects.
        """
        if self._page is None:
            return []

        try:
            raw_results: list[dict[str, Any]] = await asyncio.wait_for(
                self._page.evaluate(EXTRACT_ADS_SCRIPT),
                timeout=15.0,
            )
        except Exception as exc:
            logger.error(f"page.evaluate extraction failed: {exc}")
            return []

        if not raw_results:
            logger.debug("No ads found on page (extraction returned empty list)")
            return []

        ads: list[MetaAd] = []
        seen_ids: set[str] = set()

        for raw in raw_results:
            try:
                # Build stable ID from text hash when no libraryId is available
                library_id = raw.get("libraryId") or self._generate_id(raw.get("text", ""))

                # Skip duplicates
                if library_id in seen_ids:
                    continue
                seen_ids.add(library_id)

                landing_url = raw.get("landingUrl", "") or ""
                fbclid = raw.get("fbclid") or self._extract_fbclid(landing_url)

                ad = MetaAd(
                    library_id=library_id,
                    page_id="",                     # page IDs are not easily extracted from the DOM
                    page_name=raw.get("pageName", ""),
                    ad_text=raw.get("text", ""),
                    primary_image_url=raw.get("imageUrl", ""),
                    video_url="",                   # video extraction requires additional DOM walking
                    landing_url=landing_url,
                    fbclid=fbclid,
                    platforms=raw.get("platforms", ["facebook"]),
                    days_running=raw.get("daysRunning", 0),
                    is_active=raw.get("isActive", True),
                    raw_html="",                     # raw_html not populated in browser mode
                    call_to_action=raw.get("cta", ""),
                )
                ads.append(ad)

            except Exception as convert_exc:
                logger.debug(f"MetaAd conversion error: {convert_exc}")
                continue

        logger.info(f"Browser extraction: {len(ads)} unique ads")
        return ads

    # ------------------------------------------------------------------ utilities

    @staticmethod
    def _generate_id(text: str) -> str:
        """Generate a deterministic short ID from ad text."""
        return hashlib.md5(text[:200].encode(), usedforsecurity=False).hexdigest()[:16]

    @staticmethod
    def _extract_fbclid(url: str) -> str:
        """Pull fbclid from a URL string."""
        if not url:
            return ""
        m = re.search(r"[?&]fbclid=([^&\s]+)", url)
        return m.group(1) if m else ""
