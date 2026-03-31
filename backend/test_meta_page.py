"""Quick diagnostic to inspect Meta Ads Library page structure."""
import asyncio
import sys
import json

sys.path.insert(0, r"C:\AI_STACK\ADSRECON\backend")

from browser.playwright_pool import BrowserPool


async def diagnose():
    pool = BrowserPool(pool_size=1)
    await pool.initialize()
    print("Pool ready")

    browser = None
    try:
        browser = await pool.acquire()
        page = await browser.context.new_page()

        # Stealth script
        STEALTH = """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        delete window.cdc_adoQpoasnfa86pfoZLjfGJNvsSh;
        delete window.$cdc_asdjflasutopfhvcZLmcfl_;
        """
        await page.add_init_script(script=STEALTH)

        url = "https://www.facebook.com/ads/library/?search_type=keyword&q=weight+loss&active_status=active&ad_type=all"
        print(f"Navigating to: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(5)

        # Take a screenshot
        screenshot_path = r"C:\AI_STACK\ADSRECON\test_screenshot.png"
        await page.screenshot(path=screenshot_path, full_page=False)
        print(f"Screenshot saved to {screenshot_path}")

        # Dump page title and some key elements
        title = await page.title()
        print(f"Page title: {title}")

        # Get all divs with data-* attributes that might be ad cards
        result = await page.evaluate("""
            () => {
                // Try to find the main container
                var main = document.querySelector('#content') || document.querySelector('main') || document.body;
                var html = main.innerHTML.substring(0, 5000);
                return {
                    body_classes: document.body.className.substring(0, 200),
                    body_id: document.body.id,
                    h1: document.querySelector('h1') ? document.querySelector('h1').textContent.trim() : 'none',
                    url: window.location.href,
                    sample_html: html.substring(0, 3000)
                };
            }
        """)
        print(json.dumps(result, indent=2))

        # Try different selectors
        selectors_test = await page.evaluate("""
            () => {
                return {
                    'div[role=article]': document.querySelectorAll('div[role=article]').length,
                    'article': document.querySelectorAll('article').length,
                    'div[data-pagelet]': document.querySelectorAll('div[data-pagelet]').length,
                    'div[data-testid]': document.querySelectorAll('div[data-testid]').length,
                    'div[data-ad-preview]': document.querySelectorAll('div[data-ad-preview]').length,
                    'div[aria-label]': document.querySelectorAll('div[aria-label]').length,
                    'div[id]': document.querySelectorAll('div[id]').length,
                    'a[href*=ads]': document.querySelectorAll('a[href*=ads]').length,
                    // Find any element with 'Ad' in it
                    'div[role=main]': document.querySelectorAll('div[role=main]').length,
                    'div[class*=Ad]': document.querySelectorAll('div[class*=Ad]').length,
                    'div[class*=ad]': document.querySelectorAll('div[class*=ad]').length,
                    'form[action*=ads]': document.querySelectorAll('form[action*=ads]').length,
                    'input[name=q]': document.querySelectorAll('input[name=q]').length,
                    'form': document.querySelectorAll('form').length,
                };
            }
        """)
        print("Selector counts:", json.dumps(selectors_test, indent=2))

    finally:
        if browser:
            await pool.release(browser)
        await pool.close_all()


if __name__ == "__main__":
    asyncio.run(diagnose())
