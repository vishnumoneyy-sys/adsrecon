"""Debug the extraction script to see what's happening."""
import asyncio
import sys

sys.path.insert(0, r"C:\AI_STACK\ADSRECON\backend")
from browser.playwright_pool import BrowserPool


async def test_extraction():
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

        # Test extraction directly
        result = await page.evaluate("""
            () => {
                var gridContainers = document.querySelectorAll(
                    'div[class*="x1rzvmms"][class*="x1ys307a"], ' +
                    'div[class*="x2izyaf"][class*="xso031l"], ' +
                    'div[class*="x9f619"][class*="x1n2onr6"][class*="x1ja2u2z"]'
                );
                return {
                    gridCount: gridContainers.length,
                    gridFirst: gridContainers.length > 0 ? {
                        class: gridContainers[0].className.substring(0, 100),
                        children: gridContainers[0].children.length,
                        firstChild: gridContainers[0].firstElementChild ? gridContainers[0].firstElementChild.className.substring(0, 100) : 'none'
                    } : null
                };
            }
        """)
        print("Grid containers:", result)

        # Test extractAdText on a known ad element
        result2 = await page.evaluate("""
            () => {
                // Find a div that has "Sponsored" in it
                var divs = document.querySelectorAll('div');
                var samples = [];
                for (var d = 0; d < divs.length && samples.length < 5; d++) {
                    var div = divs[d];
                    var rect = div.getBoundingClientRect();
                    var text = (div.innerText || '').trim();
                    if (rect.width >= 250 && rect.width <= 450 &&
                        rect.height >= 150 && rect.height <= 600 &&
                        rect.top > 120 && text.length >= 40) {
                        // Check if it has external links
                        var links = div.querySelectorAll('a[href]');
                        var hasExt = false;
                        for (var l = 0; l < links.length; l++) {
                            var href = links[l].href || '';
                            if (!href.startsWith('/') && !href.startsWith('#') && !href.includes('facebook.com')) {
                                hasExt = true; break;
                            }
                        }
                        samples.push({
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                            top: Math.round(rect.top),
                            textLen: text.length,
                            text: text.substring(0, 100),
                            hasExternal: hasExt
                        });
                    }
                }
                return samples;
            }
        """)
        print("Sample candidates:", len(result2))
        for s in result2:
            print(f"  {s['width']}x{s['height']} @top={s['top']} len={s['textLen']} ext={s['hasExternal']}")
            print(f"  TEXT: {s['text'][:80]}")

    finally:
        if browser:
            await pool.release(browser)
        await pool.close_all()


if __name__ == "__main__":
    asyncio.run(test_extraction())
