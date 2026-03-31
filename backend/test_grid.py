"""Find the correct ad grid container structure."""
import asyncio
import sys
import io

sys.path.insert(0, r"C:\AI_STACK\ADSRECON\backend")
from browser.playwright_pool import BrowserPool


async def test_grid():
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

        # Scroll
        for _ in range(6):
            await page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(1.2)
        await page.evaluate("window.scrollBy(0, 0)")
        await asyncio.sleep(2)

        result = await page.evaluate("""
            () => {
                // Find elements with known ad card dimensions (330-356px wide)
                var candidates = [];
                var allDivs = document.querySelectorAll('div');
                var seenRects = {};

                for (var d = 0; d < allDivs.length; d++) {
                    var div = allDivs[d];
                    var rect;
                    try { rect = div.getBoundingClientRect(); } catch(e) { continue; }

                    // Ad card: 280-400px wide, 150-600px tall, in main content (top > 150)
                    if (rect.width >= 280 && rect.width <= 420 &&
                        rect.height >= 150 && rect.height <= 600 &&
                        rect.top > 150) {

                        var key = Math.round(rect.width) + 'x' + Math.round(rect.height);
                        if (!seenRects[key]) {
                            seenRects[key] = [];
                        }
                        seenRects[key].push({
                            cls: div.className.substring(0, 120),
                            parent_cls: div.parentElement ? div.parentElement.className.substring(0, 80) : '',
                            depth: 0,
                            text: (div.innerText || '').trim().substring(0, 80),
                        });
                    }
                }

                return seenRects;
            }
        """)

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        print("Dimension-based analysis:")
        for key, items in sorted(result.items(), key=lambda x: -len(x[1])):
            if len(items) >= 2:
                print(f"\n  {key}: {len(items)} elements")
                for item in items[:2]:
                    print(f"    cls={item['cls']}")
                    print(f"    parent={item['parent_cls']}")
                    print(f"    text={item['text'][:60]}")

    finally:
        if browser:
            await pool.release(browser)
        await pool.close_all()


if __name__ == "__main__":
    asyncio.run(test_grid())
