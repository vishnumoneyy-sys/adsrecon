"""Check what links are available in the ad cards."""
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

        for _ in range(6):
            await page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(1.2)
        await page.evaluate("window.scrollBy(0, 0)")
        await asyncio.sleep(2)

        # Find "Sponsored" text nodes and check their parent's links
        result = await page.evaluate("""
            () => {
                var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                var samples = [];
                var count = 0;
                var node;
                while (node = walker.nextNode()) {
                    var v = (node.nodeValue || '').trim();
                    if (v.toLowerCase() === 'sponsored' && count < 5) {
                        count++;
                        var el = node.parentElement;
                        if (!el) continue;

                        // Walk up to find card
                        var depth = 0;
                        var cur = el;
                        var best = el;
                        while (cur && depth < 12) {
                            try {
                                var r = cur.getBoundingClientRect();
                                if (r.width >= 300 && r.width <= 400 && r.height >= 150 && r.top > 100) {
                                    best = cur;
                                }
                            } catch (_) {}
                            cur = cur.parentElement;
                            depth++;
                        }

                        // Get all links in this card
                        var links = best.querySelectorAll ? best.querySelectorAll('a[href]') : [];
                        var linkData = [];
                        for (var li = 0; li < Math.min(links.length, 5); li++) {
                            linkData.push({
                                text: (links[li].innerText || '').trim().substring(0, 40),
                                href: links[li].href || ''
                            });
                        }
                        samples.push({
                            text: (best.innerText || '').trim().substring(0, 100),
                            links: linkData
                        });
                    }
                }
                return { count: count, samples: samples };
            }
        """)

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        print(f"Sponsored found: {result['count']}")
        for i, s in enumerate(result['samples']):
            print(f"\nCard {i+1}:")
            print(f"  Text: {s['text'][:80]}")
            for l in s['links']:
                print(f"  Link: [{l['text'][:30]:<30}] {l['href'][:80]}")

    finally:
        if browser:
            await pool.release(browser)
        await pool.close_all()


if __name__ == "__main__":
    asyncio.run(test())
