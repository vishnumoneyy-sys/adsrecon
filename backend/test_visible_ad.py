"""Find DOM structure of a visible ad card."""
import asyncio
import sys
import io

sys.path.insert(0, r"C:\AI_STACK\ADSRECON\backend")
from browser.playwright_pool import BrowserPool


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

        # Scroll down to load ads
        for _ in range(6):
            await page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(1.2)
        await asyncio.sleep(2)

        # Now find a Sponsored element that is in the visible area
        result = await page.evaluate("""
            () => {
                var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                var node;
                var found = null;
                while (node = walker.nextNode()) {
                    var v = (node.nodeValue || '').trim();
                    if (v.toLowerCase() === 'sponsored') {
                        var el = node.parentElement;
                        if (!el) continue;
                        try {
                            var r = el.getBoundingClientRect();
                            // Find one in the visible area (top > 100, top < 900)
                            if (r.top > 100 && r.top < 900) {
                                found = el;
                                break;
                            }
                        } catch (_) {}
                    }
                }

                if (!found) return {error: 'No visible Sponsored found'};

                // Walk up from this visible Sponsored element
                var path = [];
                var cur = found;
                for (var i = 0; i < 15 && cur; i++) {
                    try {
                        var r = cur.getBoundingClientRect();
                        path.push({
                            tag: cur.tagName || '',
                            cls: (cur.className || '').split(' ')[0].substring(0, 20),
                            text: (cur.innerText || '').trim().substring(0, 80),
                            w: Math.round(r.width),
                            h: Math.round(r.height),
                            top: Math.round(r.top)
                        });
                    } catch (_) {}
                    cur = cur.parentElement;
                }
                return path;
            }
        """)

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if 'error' in result:
            print(f"Error: {result['error']}")
        else:
            print(f"DOM path from visible Sponsored:")
            for pi, p in enumerate(result):
                print(f"  {pi}: {p['tag']:<6} cls={p['cls']:<20} w={p['w']} h={p['h']} top={p['top']}")
                print(f"      text: {p['text'][:60]}")

    finally:
        if browser:
            await pool.release(browser)
        await pool.close_all()


if __name__ == "__main__":
    asyncio.run(test())
