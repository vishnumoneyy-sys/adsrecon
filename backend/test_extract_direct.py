"""Test the extraction script directly on the page."""
import asyncio
import sys
import io

sys.path.insert(0, r"C:\AI_STACK\ADSRECON\backend")
from browser.playwright_pool import BrowserPool

EXTRACT_ADS_SCRIPT = r"""
function () {
    'use strict';
    var ads = [];

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

    function findCardBoundary(el) {
        if (!el) return null;
        var depth = 0;
        var cur = el;
        while (cur && depth < 12) {
            var tag = cur.tagName ? cur.tagName.toLowerCase() : '';
            if (tag === 'section' || tag === 'main' || tag === 'article') return cur;
            cur = cur.parentElement;
            depth++;
        }
        return el;
    }

    function cleanAdText(card) {
        var STRIP_RE = /library id:\s*\d+|started running on\s*\d+|platforms?\s*(facebook|instagram|messenger|audience network)?|active|inactive|view more|see less|branded content|united states|select country|current location|all\s*countries|allafghanistan|sponsored|learn more|see less|shop now|sign up|get offer|get started|get quote|book now|contact us|visit site|click here|order now|facebook|instagram|messenger/i;
        var raw = txt(card);
        var cleaned = raw.replace(STRIP_RE, ' ').replace(/\s+/g, ' ').trim();
        return cleaned.length >= 15 ? cleaned.slice(0, 500) : '';
    }

    function getPageName(card) {
        var SKIP = ['meta ad library', 'ad library', 'ad library report', 'ad library api',
                    'facebook', 'meta', 'learn more', 'see more', 'shop now', 'sign up',
                    'get offer', 'get started', 'get quote', 'book now', 'contact us',
                    'visit site', 'click here', 'order now', 'sponsored'];
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

    var seenUrls = {};
    var seenTexts = {};
    var cardSet = {};

    function addCard(card) {
        if (!card || cardSet.hasOwnProperty(card)) return;
        cardSet[card] = true;
    }

    // Test 1: find "Sponsored" text nodes
    var sponsoredCount = 0;
    var walker = null;
    try {
        walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
        var node;
        while (node = walker.nextNode()) {
            var v = (node.nodeValue || '').trim();
            if (v.toLowerCase() === 'sponsored') {
                sponsoredCount++;
                // Walk up from the text node's parent
                var el = node.parentElement;
                if (el) {
                    var boundary = findCardBoundary(el);
                    if (boundary) addCard(boundary);
                }
            }
        }
    } catch (_) {}

    // Test 2: find by size
    var sizeCount = 0;
    if (Object.keys(cardSet).length < 3) {
        cardSet = {};
        var allDivs = document.querySelectorAll('div');
        for (var di = 0; di < allDivs.length; di++) {
            var dv = allDivs[di];
            try {
                var r = dv.getBoundingClientRect();
                if (r.width >= 340 && r.width <= 380 &&
                    r.height >= 180 && r.height <= 620 &&
                    r.top > 180) {
                    sizeCount++;
                    var boundary = findCardBoundary(dv);
                    if (boundary) addCard(boundary);
                }
            } catch (_) {}
        }
    }

    // Debug: show what was found
    var debug = {
        sponsoredCount: sponsoredCount,
        sizeCount: sizeCount,
        totalCards: Object.keys(cardSet).length,
        cards: []
    };

    var cardList = Object.keys(cardSet);
    for (var ci = 0; ci < Math.min(cardList.length, 5); ci++) {
        var card = cardList[ci];
        debug.cards.push({
            rawText: txt(card).substring(0, 100),
            cleanText: cleanAdText(card).substring(0, 100),
            pageName: getPageName(card).substring(0, 50),
        });
    }

    return debug;
}
"""


async def test():
    pool = BrowserPool(pool_size=1)
    await pool.initialize()
    browser = None
    try:
        browser = await pool.acquire()
        page = await browser.context.new_page()

        STEALTH = """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        delete window.cdc_adoQpoasnfa86pfoZLjfGJNvsSh;
        delete window.$cdc_asdjflasutopfhvcZLmcfl_;
        """
        await page.add_init_script(script=STEALTH)

        url = "https://www.facebook.com/ads/library/?search_type=keyword&q=weight+loss&active_status=active&ad_type=all&country=US"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(3)

        for _ in range(6):
            await page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(1.2)
        await page.evaluate("window.scrollBy(0, 0)")
        await asyncio.sleep(2)

        result = await page.evaluate(EXTRACT_ADS_SCRIPT)
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        print(f"Sponsored text nodes: {result['sponsoredCount']}")
        print(f"Size-based elements: {result['sizeCount']}")
        print(f"Total cards: {result['totalCards']}")
        for i, card in enumerate(result['cards'][:5]):
            print(f"\n  Card {i+1}:")
            print(f"    Raw:    {card['rawText'][:80]}")
            print(f"    Clean:  {card['cleanText'][:80]}")
            print(f"    Page:   {card['pageName'][:50]}")

    finally:
        if browser:
            await pool.release(browser)
        await pool.close_all()


if __name__ == "__main__":
    asyncio.run(test())
