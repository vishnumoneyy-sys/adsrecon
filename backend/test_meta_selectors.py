"""Find the correct selectors for Meta Ads Library ad cards."""
import asyncio
import sys
import json

sys.path.insert(0, r"C:\AI_STACK\ADSRECON\backend")

from browser.playwright_pool import BrowserPool


async def find_selectors():
    pool = BrowserPool(pool_size=1)
    await pool.initialize()
    browser = None
    try:
        browser = await pool.acquire()
        page = await browser.context.new_page()

        STEALTH = """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
        delete window.cdc_adoQpoasnfa86pfoZLjfGJNvsSh;
        delete window.$cdc_asdjflasutopfhvcZLmcfl_;
        """
        await page.add_init_script(script=STEALTH)

        url = "https://www.facebook.com/ads/library/?search_type=keyword&q=weight+loss&active_status=active&ad_type=all&country=US"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(3)

        # Scroll to load ads
        for i in range(5):
            await page.evaluate("window.scrollBy(0, 600)")
            await asyncio.sleep(1.2)
        await page.evaluate("window.scrollBy(0, 0)")
        await asyncio.sleep(1)

        # Dump ALL elements that have meaningful text (to find ad card containers)
        result = await page.evaluate("""
            () => {
                // Find elements with substantial text that aren't nav elements
                const body = document.body;
                const results = [];

                // Walk all elements and find those with ad-like text
                function walk(node, depth) {
                    if (depth > 15) return;
                    if (node.nodeType !== 1) return; // Element node

                    const el = node;
                    const tag = el.tagName ? el.tagName.toLowerCase() : '';
                    const cls = el.className || '';
                    const id = el.id || '';

                    // Only look at divs/spans with meaningful content
                    const text = (el.textContent || '').trim();
                    if (text.length < 30) return;

                    // Skip navigation elements
                    if (cls.includes('x1hl2dhg') || cls.includes('x8t9es0')) return; // nav links
                    if (tag === 'nav' || tag === 'header') return;

                    // Record the element's location in the DOM tree
                    const rect = el.getBoundingClientRect ? el.getBoundingClientRect() : null;
                    if (rect && (rect.width < 100 || rect.height < 50)) return; // too small
                    if (rect && (rect.top < 200)) return; // above fold, likely nav

                    // Get surrounding structure
                    const parent = el.parentElement;
                    const grandparent = parent ? parent.parentElement : null;
                    results.push({
                        tag,
                        class: cls.substring(0, 150),
                        id,
                        text_preview: text.substring(0, 200),
                        rect: rect ? {w: Math.round(rect.width), h: Math.round(rect.height), top: Math.round(rect.top)} : null,
                        parent_tag: parent ? parent.tagName.toLowerCase() : '',
                        parent_class: parent ? (parent.className || '').substring(0, 80) : '',
                        grandparent_tag: grandparent ? grandparent.tagName.toLowerCase() : '',
                        grandparent_class: grandparent ? (grandparent.className || '').substring(0, 80) : '',
                    });
                }

                // Find all elements with substantial text in the body
                const allEls = document.querySelectorAll('div, span, article, section');
                for (const el of allEls) {
                    walk(el, 0);
                }

                return results;
            }
        """)

        print(f"Found {len(result)} candidate elements")
        # Show the most promising ones (largest, in-content)
        for r in result[:30]:
            print(f"\n---")
            print(f"  tag={r['tag']} class={r['class'][:80]}")
            print(f"  parent={r['parent_tag']} parent_cls={r['parent_class'][:60]}")
            print(f"  gp={r['grandparent_tag']} gp_cls={r['grandparent_class'][:60]}")
            print(f"  rect={r['rect']}")
            print(f"  text={r['text_preview'][:120]}")

    finally:
        if browser:
            await pool.release(browser)
        await pool.close_all()


if __name__ == "__main__":
    asyncio.run(find_selectors())
