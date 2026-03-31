"""Find exact DOM structure around Sponsored elements."""
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
        await asyncio.sleep(2)

        # Find the exact DOM path from Sponsored to the ad card
        result = await page.evaluate("""
            () => {
                var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                var node;
                var samples = [];
                var count = 0;
                while (node = walker.nextNode()) {
                    var v = (node.nodeValue || '').trim();
                    if (v.toLowerCase() === 'sponsored' && count < 2) {
                        count++;
                        // Build the DOM path upward
                        var path = [];
                        var cur = node.parentElement;
                        for (var i = 0; i < 10 && cur; i++) {
                            var tag = cur.tagName || '';
                            var cls = (cur.className || '').split(' ')[0] || '';  // first class only
                            try {
                                var r = cur.getBoundingClientRect();
                                path.push({
                                    tag: tag,
                                    cls: cls.substring(0, 20),
                                    text: (cur.innerText || '').trim().substring(0, 80),
                                    w: Math.round(r.width),
                                    h: Math.round(r.height),
                                    top: Math.round(r.top)
                                });
                            } catch (_) {}
                            cur = cur.parentElement;
                        }
                        samples.push(path);
                    }
                }
                return {count: count, samples: samples};
            }
        """)

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        print(f"Sponsored nodes found: {result['count']}")
        for si, sample in enumerate(result['samples']):
            print(f"\n=== Sample {si+1} ===")
            for pi, p in enumerate(sample):
                print(f"  {pi}: {p['tag']} cls={p['cls']:<20} w={p['w']} h={p['h']} top={p['top']}")
                print(f"      text: {p['text'][:60]}")

    finally:
        if browser:
            await pool.release(browser)
        await pool.close_all()


if __name__ == "__main__":
    asyncio.run(test())
