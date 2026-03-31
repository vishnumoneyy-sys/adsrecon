"""Debug the extraction to see card text after boundaries."""
import asyncio
import sys
import io

sys.path.insert(0, r"C:\AI_STACK\ADSRECON\backend")
from browser.playwright_pool import BrowserPool

EXTRACT_TEST = r"""
function () {
    function txt(el) {
        return el ? (el.innerText || el.textContent || '').trim() : '';
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

    var cardSet = new Set();

    // Sponsored approach
    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
    var node;
    var count = 0;
    while (node = walker.nextNode()) {
        var v = (node.nodeValue || '').trim();
        if (v.toLowerCase() === 'sponsored') {
            count++;
            var el = node.parentElement;
            if (el) {
                var b = findCardBoundary(el);
                if (b) cardSet.add(b);
            }
        }
    }

    var result = {
        sponsoredFound: count,
        totalCards: cardSet.size,
        samples: []
    };

    var i = 0;
    cardSet.forEach(function(card) {
        if (i < 3) {
            result.samples.push({
                tag: card.tagName,
                text: txt(card).substring(0, 150),
                class: (card.className || '').substring(0, 80)
            });
        }
        i++;
    });

    return result;
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
        await asyncio.sleep(2)  # Don't scroll back to top — keep ads in view

        result = await page.evaluate(EXTRACT_TEST)
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        print(f"Sponsored found: {result['sponsoredFound']}")
        print(f"Total unique cards: {result['totalCards']}")
        for i, card in enumerate(result['samples']):
            print(f"\nCard {i+1} tag={card['tag']} class={card['class'][:50]}")
            print(f"  Text: {card['text'][:100]}")

    finally:
        if browser:
            await pool.release(browser)
        await pool.close_all()


if __name__ == "__main__":
    asyncio.run(test())
