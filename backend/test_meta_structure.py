"""Deep diagnostic to understand Meta Ads Library page structure after full load."""
import asyncio
import sys
import json
import time

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

        # More aggressive stealth
        STEALTH = """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
        delete window.cdc_adoQpoasnfa86pfoZLjfGJNvsSh;
        delete window.$cdc_asdjflasutopfhvcZLmcfl_;
        window.chrome = {runtime: {}};
        """
        await page.add_init_script(script=STEALTH)

        url = "https://www.facebook.com/ads/library/?search_type=keyword&q=weight+loss&active_status=active&ad_type=all&country=US"
        print(f"Navigating to: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)

        # Wait for React to mount
        await asyncio.sleep(2)

        # Try different wait strategies
        print("\n--- Waiting for content ---")
        for strategy in ["networkidle", "load"]:
            try:
                await page.wait_for_load_state(strategy, timeout=5000)
                print(f"  {strategy}: OK")
            except Exception as e:
                print(f"  {strategy}: {e}")

        # Wait for potential ad content (up to 15 seconds)
        print("\nWaiting up to 15s for content...")
        try:
            await page.wait_for_function(
                "() => document.querySelectorAll('div').length > 1000",
                timeout=15000
            )
            print("  Content loaded (div count > 1000)")
        except Exception as e:
            print(f"  Timeout: {e}")

        # Take screenshot after waiting
        await page.screenshot(path=r"C:\AI_STACK\ADSRECON\test_screenshot2.png", full_page=False)
        print("Screenshot 2 saved")

        # Try to find the main ad container
        selectors_to_try = [
            # Facebook's own patterns
            'div[class*="x1n2onr6"]',  # Meta React base class
            'div[class*="x1n4k9"]',
            'div[class*="x6s0dn4"]',
            'div[class*="x78zum5"]',
            # Generic
            'div[class*="x1i"]',  # Common Meta prefix
            'div[class*="x9f"]',
            # By role
            '[role="feed"]',
            '[role="region"]',
            # Text-based
            '[data-ad-preview]',
            # Check for specific text
            'div:has-text("Active")',
            'div:has-text("See more")',
        ]

        print("\n--- Selector analysis ---")
        for sel in selectors_to_try:
            try:
                count = await page.locator(sel).count()
                if count > 0:
                    print(f"  {sel}: {count} found")
            except Exception as e:
                print(f"  {sel}: ERROR {e}")

        # Deep inspection of what's actually rendered
        print("\n--- Full page analysis ---")
        result = await page.evaluate("""
            () => {
                const body = document.body.innerHTML;
                return {
                    total_divs: document.querySelectorAll('div').length,
                    total_spans: document.querySelectorAll('span').length,
                    total_anchors: document.querySelectorAll('a').length,
                    body_len: body.length,
                    url_after_redirect: window.location.href,
                    title: document.title,
                    // Look for anything with ad text
                    possible_ad_text: Array.from(document.querySelectorAll('span, div')).filter(el => {
                        const t = el.textContent.trim();
                        return t.length > 30 && t.length < 300 && !el.querySelector('div, span, a');
                    }).map(el => el.textContent.trim().substring(0, 100)).slice(0, 5),
                    // Any visible non-navigation content
                    visible_text_samples: Array.from(document.querySelectorAll('body *')).filter(el => {
                        const style = window.getComputedStyle(el);
                        return style.display !== 'none' && style.visibility !== 'hidden' && el.textContent.trim().length > 50;
                    }).map(el => el.textContent.trim().substring(0, 150)).slice(0, 5),
                };
            }
        """)
        print(json.dumps(result, indent=2))

        # Try scrolling and wait again
        print("\n--- Scrolling ---")
        for i in range(3):
            await page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(1)
            div_count = await page.evaluate("() => document.querySelectorAll('div').length")
            print(f"  After scroll {i+1}: {div_count} divs")

        await page.screenshot(path=r"C:\AI_STACK\ADSRECON\test_screenshot3.png", full_page=False)
        print("Screenshot 3 saved")

    finally:
        if browser:
            await pool.release(browser)
        await pool.close_all()


if __name__ == "__main__":
    asyncio.run(diagnose())
