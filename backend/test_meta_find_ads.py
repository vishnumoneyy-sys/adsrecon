"""Find the ad card DOM structure from Meta Ads Library."""
import asyncio
import sys

sys.path.insert(0, r"C:\AI_STACK\ADSRECON\backend")
from browser.playwright_pool import BrowserPool


async def find_ad_structure():
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

        # Scroll to trigger ad loading
        for _ in range(6):
            await page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(1.2)
        await page.evaluate("window.scrollBy(0, 0)")
        await asyncio.sleep(2)

        # Find elements containing known ad text
        result = await page.evaluate("""
            () => {
                // Search for elements containing "weight loss" or "Meno" text
                const texts = [
                    'MenoChill', 'Black Girl', 'Wellmedr',
                    'doctor', 'weight loss', 'supplement'
                ];

                const found = [];
                const allDivs = document.querySelectorAll('div');

                for (const div of allDivs) {
                    const text = (div.textContent || '').trim();
                    // Check if this div has substantial ad-like text
                    if (text.length > 60 && text.length < 1000) {
                        // Find the nearest parent with x78zum5 class (common Meta container)
                        let parent = div;
                        for (let i = 0; i < 10; i++) {
                            if (!parent.parentElement) break;
                            parent = parent.parentElement;
                            const cls = parent.className || '';
                            // Look for a card-like container
                            if (cls.includes('x78zum5') && cls.includes('x1iyjqo2')) {
                                const rect = parent.getBoundingClientRect();
                                if (rect.width > 200 && rect.width < 500 && rect.height > 200 && rect.top > 150) {
                                    found.push({
                                        text: text.substring(0, 150),
                                        container_class: cls.substring(0, 200),
                                        rect: {w: Math.round(rect.width), h: Math.round(rect.height)},
                                    });
                                    break;
                                }
                            }
                        }
                    }
                    if (found.length >= 5) break;
                }
                return found;
            }
        """)

        for f in result:
            print(f"CLASS: {f['container_class']}")
            print(f"RECT:  {f['rect']}")
            print(f"TEXT:  {f['text'][:100]}")
            print()

        # Also: look at the XULE structure more carefully
        print("\n=== Analyzing full DOM structure ===")
        structure = await page.evaluate("""
            () => {
                // Find all elements at various levels that could be ad cards
                const results = {};

                // Count elements by their top-level x* class patterns
                const allDivs = Array.from(document.querySelectorAll('div'));
                const xPatterns = {};

                for (const div of allDivs) {
                    const cls = div.className || '';
                    const rect = div.getBoundingClientRect ? div.getBoundingClientRect() : null;
                    if (!rect || rect.width < 200 || rect.width > 500 || rect.height < 150 || rect.top < 200) continue;

                    // Get the primary class
                    const parts = cls.split(' ').filter(c => c.startsWith('x'));
                    if (parts.length > 0) {
                        const primary = parts[0];
                        if (!xPatterns[primary]) xPatterns[primary] = {count: 0, rects: []};
                        xPatterns[primary].count++;
                        xPatterns[primary].rects.push({w: Math.round(rect.width), h: Math.round(rect.height)});
                    }
                }

                // Sort by count
                const sorted = Object.entries(xPatterns).sort((a, b) => b[1].count - a[1].count);
                return sorted.slice(0, 10).map(([cls, data]) => ({
                    cls,
                    count: data.count,
                    sample_rects: data.rects.slice(0, 3)
                }));
            }
        """)
        for s in structure:
            print(f"Class: {s['cls']}, Count: {s['count']}, Rects: {s['sample_rects']}")

    finally:
        if browser:
            await pool.release(browser)
        await pool.close_all()


if __name__ == "__main__":
    import io, sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    asyncio.run(find_ad_structure())
