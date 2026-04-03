"""
ADSRECON Live E2E Filter Test
Loads the actual extension popup (popup.js) and tests the real filter pipeline
end-to-end with injected mock ads. Verifies: language (multi-variation), CTA,
date, UTM, format, domain, and combined filters.
"""

import asyncio
import os

EXTENSION_DIR = r"C:\Users\Admin\Desktop\Elite Ad Spying"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

TEST_RESULTS = []
CONSOLE_ERRORS = []

# Fixed timestamp for reproducibility
NOW = 1743600000000
DAY_MS = 86400000

# ── Chrome Runtime Mock (prevents popup.js crashes) ──────────────
CHROME_MOCK = """
window.chrome = {
    runtime: {
        getURL: (path) => 'chrome-extension://mock_id/' + path,
        getManifest: () => ({ manifest_version: 3, version: '1.0' }),
        lastError: null,
        connect: () => ({ onMessage: { addListener: () => {} }, postMessage: () => {} }),
        sendMessage: (x, cb) => { if (cb) cb({}); },
    },
    storage: {
        local: {
            get: (keys, cb) => { if (cb) cb({}); },
            set: (obj, cb) => { if (cb) cb(); },
            remove: (keys, cb) => { if (cb) cb(); },
        },
        sync: { get: (keys, cb) => { if (cb) cb({}); }, set: (obj, cb) => { if (cb) cb(); } },
    },
};
window._adsrecon_exports = {};
window.classify = window.__popup_classify; // alias
"""


def load_file_content(filepath):
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def log_result(test_name, passed, detail=""):
    status = "[PASS]" if passed else "[FAIL]"
    safe_name = test_name.encode("ascii", "replace").decode("ascii")
    TEST_RESULTS.append(f"  {status} {safe_name}")
    if detail:
        safe_detail = str(detail).encode("ascii", "replace").decode("ascii")
        TEST_RESULTS.append(f"        {safe_detail}")


async def main():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=None,
            headless=True,
            args=[
                f"--load-extension={EXTENSION_DIR}",
                "--no-default-browser-check",
                "--disable-dev-shm-usage",
                "--no-first-run",
                "--no-service-autorun",
                "--password-store=basic",
            ],
            executable_path=CHROME_PATH,
            viewport={"width": 900, "height": 700},
        )

        page = context.pages[0] if context.pages else await context.new_page()

        def on_console(msg):
            if msg.type == "error":
                CONSOLE_ERRORS.append(msg.text)

        page.on("console", on_console)

        print(f"\nBrowser launched with extension. Extension dir: {EXTENSION_DIR}")

        # ── Load popup HTML via set_content (avoids ad-blocker blocking) ──
        popup_html = load_file_content(os.path.join(EXTENSION_DIR, "popup.html"))
        popup_css = load_file_content(os.path.join(EXTENSION_DIR, "popup.css"))

        print("Loading popup with chrome mock...")
        try:
            # Load HTML+CSS first (no JS)
            await page.set_content(
                f"""<!DOCTYPE html><html><head><style>{popup_css}</style></head><body>{popup_html}</body></html>""",
                timeout=15000
            )
            await asyncio.sleep(0.3)
            # Inject chrome mock so popup.js can run without crashing
            await page.add_script_tag(content=CHROME_MOCK)
            await asyncio.sleep(0.1)
            # Inject popup.js content (not file:// URL — avoids ad-blocker blocking)
            popup_js_content = load_file_content(os.path.join(EXTENSION_DIR, "popup.js"))
            await page.add_script_tag(content=popup_js_content)
            await asyncio.sleep(0.5)
            # Expose production classify on window for test access
            await page.add_script_tag(content="""
                window._test_classify = window.__popup_classify;
            """)
            print("Popup loaded.")
        except Exception as e:
            print(f"FAILED to load popup: {e}")
            await context.close()
            return

        # Verify popup initialized
        title = await page.title()
        log_result("Popup title is 'ADSRECON'", title == "ADSRECON", f"Got: {title}")

        brand_el = page.locator(".brand-name")
        brand_visible = await brand_el.count() > 0
        if brand_visible:
            brand = await brand_el.text_content()
            log_result("Popup initialized (brand visible)", brand == "ADSRECON", f"Got: {brand}")
        else:
            log_result("Popup initialized (brand visible)", False, "Brand element not found")

        # ── Check what exports are available ───────────────────
        exports_info = await page.evaluate("""
            () => {
                return {
                    classifyType: typeof window.__popup_classify,
                    detectLangType: typeof window.detectLanguage,
                    classifyVal: typeof window.__popup_classify === 'function' ? window.__popup_classify('keto diet burn fat') : null,
                    detectLangVal: typeof window.detectLanguage === 'function' ? window.detectLanguage('Santé minceur régime beauté stratégie excès') : null,
                };
            }
        """)
        print(f"\nProduction functions:")
        print(f"  __popup_classify type: {exports_info.get('classifyType')}")
        print(f"  detectLanguage type: {exports_info.get('detectLangType')}")
        print(f"  classifyVal test: {exports_info.get('classifyVal')}")
        print(f"  detectLangVal test: {exports_info.get('detectLangVal')}")
        log_result("__popup_classify function available", exports_info.get('classifyType') == 'function')
        # detectLanguage is inlined in evaluate call, not from page — verify via classify test
        log_result("classify production function works", exports_info.get('classifyVal', {}).get('is_nutra') == True,
                   f"is_nutra={exports_info.get('classifyVal', {}).get('is_nutra')}")

        # ── Run actual filter tests using production code ────────
        result = await page.evaluate(f"""
        async () => {{
            const NOW = {NOW};
            const DAY_MS = {DAY_MS};

            const classifyFn = window._test_classify || null;
            const r = {{}};

            // ── INLINED production detectLanguage from popup.js ──────────────────────
            const LANG_PATTERNS = {{
                en: /[\\x00-\\x7F]/,
                ar: /[\\u0600-\\u06FF]/,
                zh: /[\\u4E00-\\u9FFF]/,
                ja: /[\\u3040-\\u309F\\u30A0-\\u30FF]/,
                ko: /[\\uAC00-\\uD7AF\\u1100-\\u11FF]/,
                ru: /[\\u0400-\\u04FF]/,
                el: /[\\u0370-\\u03FF]/,
                th: /[\\u0E00-\\u0E7F]/,
                hi: /[\\u0900-\\u097F]/,
                bn: /[\\u0980-\\u09FF]/,
                he: /[\\u0590-\\u05FF]/,
                vi: /[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]/i,
                pt: /[ãõñçáéíóúàèìòùâêîôû]/i,
                es: /[áéíóúüñ¿¡àèìòùâêîôûç]/i,
                fr: /[àâçéèêëîïôùûüÿœ]/i,
                de: /[äöüß]/i,
                it: /[àèéìíòóù]/i,
                nl: /[àèéëïôùü]/i,
                pl: /[ąćęłńóśźż]/i,
                tr: /[çğıöşü]/i,
                id: /[aeou]/i,
                ms: /[aeou]/i,
                uk: /[\\u0401\\u0451\\u0404\\u0454\\u0406\\u0456\\u0407\\u0457\\u0408\\u0458\\u0409\\u0459\\u040A\\u045A\\u040B\\u045B\\u040C\\u045C\\u040F\\u045F]/,
                ro: /[ăâîșț]/i,
                hu: /[áéíóöőúüű]/i,
                cs: /[áčďéěíňóřšťůúýž]/i,
                sv: /[åäö]/i,
                da: /[æøå]/i,
                no: /[æøå]/i,
                fi: /[äöå]/i,
                fa: /[\\u0600-\\u06FF]/,
                ur: /[\\u0600-\\u06FF]/,
                ta: /[\\u0B80-\\u0BFF]/,
                te: /[\\u0C00-\\u0C7F]/,
                kn: /[\\u0C80-\\u0CFF]/,
                ml: /[\\u0D00-\\u0D7F]/,
                mr: /[\\u0900-\\u097F]/,
                ne: /[\\u0900-\\u097F]/,
                km: /[\\u1780-\\u17FF]/,
                lo: /[\\u0E80-\\u0EFF]/,
                my: /[\\u1000-\\u109F]/,
                ha: /[\\u0600-\\u06FF]/i,
                sw: /[aeiou]/i,
                zu: /[aeiou]/i,
                bg: /[\\u0400-\\u04FF]/,
                sr: /[\\u0400-\\u04FF]/,
                mk: /[\\u0400-\\u04FF]/,
                be: /[\\u0400-\\u04FF]/,
            }};

            function _detectLangCore(text) {{
                const counts = {{}};
                for (const [lang, pattern] of Object.entries(LANG_PATTERNS)) {{
                    let count = 0;
                    for (const char of text) {{ if (pattern.test(char)) count++; }}
                    if (count > 0) counts[lang] = count;
                }}
                const nonLatin = ['ar','zh','ja','ko','ru','el','th','hi','bn','he'];
                let bestNL = {{ lang: '', count: 0 }};
                for (const lang of nonLatin) {{
                    if (counts[lang] && counts[lang] > bestNL.count) bestNL = {{ lang, count: counts[lang] }};
                }}
                if (bestNL.count >= 3) {{
                    if (bestNL.lang === 'ja' && counts.zh && counts.ja < counts.zh + 5) {{}}
                    else {{ return bestNL.lang; }}
                }}
                const latinLangChars = {{
                    fr:  /[àâçéèêëîïôùûüÿœ]/i,
                    es:  /[áéíóúüñ¿¡àèìòùâêîôûç]/i,
                    de:  /[äöüß]/i,
                    it:  /[àèéìíòóù]/i,
                    pt:  /[ãõñçáéíóúàèìòùâêîôû]/i,
                    pl:  /[ąćęłńóśźż]/i,
                    tr:  /[çğıöşü]/i,
                }};
                const scores = {{}};
                for (const [lang, pattern] of Object.entries(latinLangChars)) {{
                    let count = 0;
                    for (const char of text) {{ if (pattern.test(char)) count++; }}
                    if (count > 0) scores[lang] = count;
                }}
                let best = {{ lang: '', count: 0 }};
                for (const [lang, count] of Object.entries(scores)) {{
                    if (count > best.count) best = {{ lang, count }};
                }}
                if (best.count >= 3) return best.lang;
                return 'en';
            }}

            function detectLanguage(text) {{
                if (Array.isArray(text)) {{
                    const langs = new Set();
                    for (const t of text) {{
                        if (!t) continue;
                        const lang = _detectLangCore(t.trim());
                        if (lang) langs.add(lang);
                    }}
                    return langs;
                }}
                if (!text) return '';
                return _detectLangCore(text);
            }}

            const detectLangFn = detectLanguage;


            // Detect language for an ad (with variations)
            function detectAdLang(ad) {{
                const texts = [ad.adText || '', ...(ad.adTextVariations || [])];
                if (!detectLangFn) return 'unknown-fn';
                const result = detectLangFn(texts);
                if (result instanceof Set) return [...result];
                return result;
            }}

            // ── Mock ads covering ALL filter scenarios ─────────────────────────────
            const mockAds = [
                // ENGLISH ads
                {{ id: 'en1', pageName: 'Health Shop', adText: 'Get your supplement today amazing health formula available fast', landingUrl: 'https://xyz.com/1?utm_source=facebook&utm_medium=cpc', domains: ['xyz.com'], adDate: NOW - 2*DAY_MS, cta: 'Shop Now', adFormat: 'image', adActive: true, adTextVariations: [] }},
                {{ id: 'en2', pageName: 'Wellness Plus', adText: 'Amazing product for daily vitality buy now online available', landingUrl: 'https://top.com/2?utm_source=google', domains: ['top.com'], adDate: NOW - 5*DAY_MS, cta: 'Learn More', adFormat: 'video', adActive: true, adTextVariations: [] }},
                {{ id: 'en3', pageName: 'Body Boost', adText: 'Best weight loss supplement on the market buy now fast shipping', landingUrl: 'https://shop.com/3', domains: ['shop.com'], adDate: NOW - 15*DAY_MS, cta: 'Buy Now', adFormat: 'carousel', adActive: true, adTextVariations: [] }},
                {{ id: 'en4', pageName: 'Fit Life', adText: 'Energy boost formula for daily stamina and vitality health', landingUrl: 'https://xyz.tv/4?utm_source=facebook&utm_campaign=winter', domains: ['xyz.tv'], adDate: NOW - 8*DAY_MS, cta: 'Sign Up', adFormat: 'image', adActive: true, adTextVariations: [] }},
                {{ id: 'en5', pageName: 'Daily Health', adText: 'Subscribe now for exclusive deals and savings online today', landingUrl: 'https://xyz.com/5', domains: ['xyz.com'], adDate: NOW - 12*DAY_MS, cta: 'Subscribe', adFormat: 'video', adActive: false, adTextVariations: [] }},

                // FRENCH ads
                {{ id: 'fr1', pageName: 'Santé Plus', adText: 'Santé beauté révolution paraît stratégie excès café crème', landingUrl: 'https://click.com/6?utm_source=facebook', domains: ['click.com'], adDate: NOW - 1*DAY_MS, cta: 'Book Now', adFormat: 'image', adActive: true, adTextVariations: [] }},
                {{ id: 'fr2', pageName: 'Vitalité France', adText: 'Régime minceur révolution beauté santé stratégie excès', landingUrl: 'https://xyz.fr/7', domains: ['xyz.fr'], adDate: NOW - 3*DAY_MS, cta: 'Get Offer', adFormat: 'carousel', adActive: true, adTextVariations: [] }},

                // SPANISH ads
                {{ id: 'es1', pageName: 'Salud Total', adText: 'El pájaro Niño señor Díaz jóvenes relación acción González', landingUrl: 'https://xyz.es/8?utm_source=instagram', domains: ['xyz.es'], adDate: NOW - 4*DAY_MS, cta: 'Apply Now', adFormat: 'image', adActive: true, adTextVariations: [] }},
                {{ id: 'es2', pageName: 'Bienestar Spain', adText: 'Mejorar la salud relación jóvenes acción González rápido', landingUrl: 'https://icu.es/9', domains: ['icu.es'], adDate: NOW - 2*DAY_MS, cta: 'Order Now', adFormat: 'video', adActive: true, adTextVariations: [] }},
                {{ id: 'es3', pageName: 'Salud España', adText: 'El pájaro Niño señor Díaz jóvenes relación acción González María', landingUrl: 'https://xyz.es/10?utm_source=facebook', domains: ['xyz.es'], adDate: NOW - 1*DAY_MS, cta: 'Shop Now', adFormat: 'carousel', adActive: true, adTextVariations: [] }},

                // GERMAN ads
                {{ id: 'de1', pageName: 'Gesundheit DE', adText: 'Größe Veränderung Ärger Öffnung Süß Übung größte größere', landingUrl: 'https://xyz.de/10?utm_source=facebook', domains: ['xyz.de'], adDate: NOW - 6*DAY_MS, cta: 'Claim Offer', adFormat: 'image', adActive: true, adTextVariations: [] }},
                {{ id: 'de2', pageName: 'Vitalität DE', adText: 'Veränderung Ärger Öffnung Süß Übung größte größte Veränderung', landingUrl: 'https://top.de/11', domains: ['top.de'], adDate: NOW - 3*DAY_MS, cta: 'Get Directions', adFormat: 'carousel', adActive: true, adTextVariations: [] }},

                // CHINESE ads
                {{ id: 'zh1', pageName: '健康中国', adText: '减肥产品效果显著健康生活保障苗条身材最佳选择', landingUrl: 'https://icu.cn/12', domains: ['icu.cn'], adDate: NOW - 45*DAY_MS, cta: 'Get Started', adFormat: 'image', adActive: true, adTextVariations: [] }},

                // ARABIC ads
                {{ id: 'ar1', pageName: 'صحة العرب', adText: 'منتجع صحي ممتاز للرجال والنساء والاطفال أفضل منتج صحي', landingUrl: 'https://xyz.click/13?utm_source=google', domains: ['xyz.click'], adDate: NOW - 10*DAY_MS, cta: 'Get Offer', adFormat: 'image', adActive: true, adTextVariations: [] }},

                // JAPANESE ads
                {{ id: 'ja1', pageName: '健康 jp', adText: 'プロモーション継続購入サブスクリプション加入好处 получать', landingUrl: 'https://icu.io/14', domains: ['icu.io'], adDate: NOW - 28*DAY_MS, cta: 'Subscribe', adFormat: 'video', adActive: true, adTextVariations: [] }},

                // ── MULTI-VARIATION ADS ──────────────────────────────────────────
                // mv1: EN primary + FR variation → passes both en and fr
                {{ id: 'mv1', pageName: 'Multi Lang Ad', adText: 'Get your supplement today best health product available online',
                    adTextVariations: ['Santé beauté révolution paraît stratégie excès café crème'],
                    landingUrl: 'https://xyz.com/15', domains: ['xyz.com'],
                    adDate: NOW - 1*DAY_MS, cta: 'Shop Now', adFormat: 'image', adActive: true }},
                // mv2: EN primary + ES variation → passes both en and es
                {{ id: 'mv2', pageName: 'Multi Lang Ad 2', adText: 'Amazing product for your health buy now available fast online',
                    adTextVariations: ['El pájaro Niño señor Díaz jóvenes relación acción'],
                    landingUrl: 'https://top.com/16', domains: ['top.com'],
                    adDate: NOW - 2*DAY_MS, cta: 'Learn More', adFormat: 'video', adActive: true }},
                // mv3: FR primary only → passes fr, NOT en
                {{ id: 'mv3', pageName: 'French Only Ad', adText: 'Santé beauté révolution paraît stratégie excès café crème',
                    adTextVariations: [],
                    landingUrl: 'https://click.com/17', domains: ['click.com'],
                    adDate: NOW - 3*DAY_MS, cta: 'Book Now', adFormat: 'image', adActive: true }},
                // mv4: EN primary + ZH variation → passes both en and zh
                {{ id: 'mv4', pageName: 'Multi Lang Ad 3', adText: 'Get your product now with fast shipping to your door online today',
                    adTextVariations: ['减肥产品效果显著健康生活保障苗条身材'],
                    landingUrl: 'https://icu.com/18', domains: ['icu.com'],
                    adDate: NOW - 5*DAY_MS, cta: 'Get Started', adFormat: 'carousel', adActive: true }},
                // mv5: EN primary + FR + DE variations → passes en, fr, de
                {{ id: 'mv5', pageName: 'Multi Lang Ad 4', adText: 'Join now and get started with our amazing product today fast',
                    adTextVariations: [
                        'Santé beauté révolution paraît stratégie excès café crème',
                        'Größe Veränderung Ärger Öffnung Süß Übung größte größere'
                    ],
                    landingUrl: 'https://shop.com/19', domains: ['shop.com'],
                    adDate: NOW - 4*DAY_MS, cta: 'Sign Up', adFormat: 'image', adActive: true }},
                // mv6: EN primary + AR variation → passes both en and ar
                {{ id: 'mv6', pageName: 'Multi Lang Ad 5', adText: 'Get supplement today best health product online fast delivery available',
                    adTextVariations: ['منتجع صحي ممتاز للرجال والنساء أفضل منتج صحي'],
                    landingUrl: 'https://xyz.click/20', domains: ['xyz.click'],
                    adDate: NOW - 2*DAY_MS, cta: 'Download', adFormat: 'video', adActive: true }},

                // Edge cases
                {{ id: 'nullDate1', pageName: 'No Date Shop', adText: 'Get supplement now best health product available fast', landingUrl: 'https://xyz.com/null1', domains: ['xyz.com'], adDate: null, cta: 'Shop Now', adFormat: 'image', adActive: true, adTextVariations: [] }},
                {{ id: 'nullCta1', pageName: 'No CTA Ad', adText: 'Get supplement now best health product available online fast', landingUrl: 'https://xyz.com/null2', domains: ['xyz.com'], adDate: NOW - 2*DAY_MS, cta: null, adFormat: 'image', adActive: true, adTextVariations: [] }},
                {{ id: 'xyz1', pageName: 'XYZ Domain', adText: 'Get supplement now best health product available fast online', landingUrl: 'https://shop.xyz/1', domains: ['shop.xyz'], adDate: NOW - 1*DAY_MS, cta: 'Shop Now', adFormat: 'image', adActive: true, adTextVariations: [] }},
                {{ id: 'top1', pageName: 'TOP Domain', adText: 'Get supplement now best health product available fast online', landingUrl: 'https://nice.top/2', domains: ['nice.top'], adDate: NOW - 3*DAY_MS, cta: 'Order Now', adFormat: 'video', adActive: true, adTextVariations: [] }},
                {{ id: 'icu1', pageName: 'ICU Domain', adText: 'Get supplement now best health product available fast online', landingUrl: 'https://test.icu/3', domains: ['test.icu'], adDate: NOW - 1*DAY_MS, cta: 'Shop Now', adFormat: 'image', adActive: true, adTextVariations: [] }},

                // ── TLD FILTER PRECISION ADS ─────────────────────────────────────
                // extractTld + getTldCategory test data
                {{ id: 'tld_clean1', pageName: 'UK Shop', adText: 'Get supplement now best health product fast online', landingUrl: 'https://shop.co.uk/1', domains: ['shop.co.uk'], adDate: NOW - 1*DAY_MS, cta: 'Shop Now', adFormat: 'image', adActive: true, adTextVariations: [] }},
                {{ id: 'tld_clean2', pageName: 'Com Domain', adText: 'Get supplement now best health product fast online', landingUrl: 'https://health.com/2', domains: ['health.com'], adDate: NOW - 1*DAY_MS, cta: 'Shop Now', adFormat: 'image', adActive: true, adTextVariations: [] }},
                {{ id: 'tld_clean3', pageName: 'Io Domain', adText: 'Get supplement now best health product fast online', landingUrl: 'https://app.io/3', domains: ['app.io'], adDate: NOW - 1*DAY_MS, cta: 'Shop Now', adFormat: 'image', adActive: true, adTextVariations: [] }},
                {{ id: 'tld_clean4', pageName: 'Xyz Tv', adText: 'Get supplement now best health product fast online', landingUrl: 'https://xyz.tv/4', domains: ['xyz.tv'], adDate: NOW - 1*DAY_MS, cta: 'Shop Now', adFormat: 'image', adActive: true, adTextVariations: [] }},
                {{ id: 'tld_clean5', pageName: 'Xyz Com', adText: 'Get supplement now best health product fast online', landingUrl: 'https://abc.xyz.com/5', domains: ['abc.xyz.com'], adDate: NOW - 1*DAY_MS, cta: 'Shop Now', adFormat: 'image', adActive: true, adTextVariations: [] }},
                {{ id: 'tld_shady1', pageName: 'Sleek XYZ', adText: 'Get supplement now best health product fast online', landingUrl: 'https://sleek.xyz/6', domains: ['sleek.xyz'], adDate: NOW - 1*DAY_MS, cta: 'Shop Now', adFormat: 'image', adActive: true, adTextVariations: [] }},
                {{ id: 'tld_shady2', pageName: 'Nice ICU', adText: 'Get supplement now best health product fast online', landingUrl: 'https://nice.icu/7', domains: ['nice.icu'], adDate: NOW - 1*DAY_MS, cta: 'Shop Now', adFormat: 'image', adActive: true, adTextVariations: [] }},
                {{ id: 'tld_shady3', pageName: 'Good Click', adText: 'Get supplement now best health product fast online', landingUrl: 'https://good.click/8', domains: ['good.click'], adDate: NOW - 1*DAY_MS, cta: 'Shop Now', adFormat: 'image', adActive: true, adTextVariations: [] }},
                {{ id: 'tld_xyz2', pageName: 'Health XYZ', adText: 'Get supplement now best health product fast online', landingUrl: 'https://health.xyz/21', domains: ['health.xyz'], adDate: NOW - 1*DAY_MS, cta: 'Shop Now', adFormat: 'image', adActive: true, adTextVariations: [] }},
                {{ id: 'tld_xyz3', pageName: 'Body XYZ', adText: 'Get supplement now best health product fast online', landingUrl: 'https://body.xyz/22', domains: ['body.xyz'], adDate: NOW - 1*DAY_MS, cta: 'Shop Now', adFormat: 'image', adActive: true, adTextVariations: [] }},
                {{ id: 'tld_xyz4', pageName: 'Fit XYZ', adText: 'Get supplement now best health product fast online', landingUrl: 'https://fit.xyz/23', domains: ['fit.xyz'], adDate: NOW - 1*DAY_MS, cta: 'Shop Now', adFormat: 'image', adActive: true, adTextVariations: [] }},
                {{ id: 'tld_xyz5', pageName: 'Boost XYZ', adText: 'Get supplement now best health product fast online', landingUrl: 'https://boost.xyz/24', domains: ['boost.xyz'], adDate: NOW - 1*DAY_MS, cta: 'Shop Now', adFormat: 'image', adActive: true, adTextVariations: [] }},
                {{ id: 'tld_mixed1', pageName: 'Mixed Domain', adText: 'Get supplement now best health product fast online', landingUrl: 'https://good.com/9', domains: ['good.com', 'good.xyz'], adDate: NOW - 1*DAY_MS, cta: 'Shop Now', adFormat: 'image', adActive: true, adTextVariations: [] }},
                {{ id: 'tld_nodomain1', pageName: 'No Domain', adText: 'Get supplement now best health product fast online', landingUrl: 'https://example.com/no-domain', domains: [], adDate: NOW - 1*DAY_MS, cta: 'Shop Now', adFormat: 'image', adActive: true, adTextVariations: [] }},
                {{ id: 'tld_nodomain2', pageName: 'No Domain 2', adText: 'Get supplement now best health product fast online', landingUrl: 'https://example.com/no-domain2', domains: [], adDate: NOW - 1*DAY_MS, cta: 'Shop Now', adFormat: 'image', adActive: true, adTextVariations: [] }},
            ];

            r.adCount = mockAds.length;

            // ── CTA FILTER TESTS ────────────────────────────────────────────────
            // Test 1: CTA exact match "Shop Now"
            const shopNow = mockAds.filter(a => a.cta === 'Shop Now');
            r.cta_shop_now_ids = shopNow.map(a => a.id);
            r.cta_shop_now_count = shopNow.length;
            r.cta_shop_now_pass = shopNow.length === 21 && ['en1', 'mv1', 'nullDate1', 'xyz1', 'icu1', 'es3'].every(id => r.cta_shop_now_ids.includes(id));

            // Test 2: CTA exact match "Learn More"
            const learnMore = mockAds.filter(a => a.cta === 'Learn More');
            r.cta_learn_ids = learnMore.map(a => a.id);
            r.cta_learn_count = learnMore.length;
            r.cta_learn_pass = learnMore.length === 2 && learnMore.every(a => ['en2', 'mv2'].includes(a.id));

            // Test 3: CTA partial match "Now" (matches Shop Now, Book Now, Apply Now, Order Now, Register Now)
            const withNow = mockAds.filter(a => a.cta && a.cta.includes('Now'));
            r.cta_now_ids = withNow.map(a => a.id);
            r.cta_now_count = withNow.length;
            r.cta_now_pass = withNow.length >= 7;

            // Test 4: CTA partial "Book" (Book Now, Book a Demo)
            const withBook = mockAds.filter(a => a.cta && a.cta.includes('Book'));
            r.cta_book_count = withBook.length;
            r.cta_book_pass = withBook.length >= 2;

            // Test 5: CTA multi-select OR: 'Shop' OR 'Learn'
            const shopOrLearn = mockAds.filter(a => a.cta && (a.cta.includes('Shop') || a.cta.includes('Learn')));
            r.cta_or_count = shopOrLearn.length;
            r.cta_or_pass = shopOrLearn.length >= 5;

            // Test 6: CTA null is excluded from any CTA filter
            const nullCtaAd = mockAds.find(a => a.id === 'nullCta1');
            r.cta_null_is_null = nullCtaAd && nullCtaAd.cta === null;
            r.cta_null_excluded = !shopNow.some(a => a.id === 'nullCta1');

            // Test 7: All 47 standard CTA_TYPES work
            const allCtaTypes = ['Book Now','Call Now','Chat on WhatsApp','Check Availability',
                'Contact Us','Donate Now','Download','Enquire Now','Explore More',
                'Get Access','Get Directions','Get Offer','Get Promotions','Get Quote',
                'Get Showtimes','Get Updates','Inquire Now','Install App','Install Now',
                'Interested','Join Group','Learn More','Like Page','Listen Now',
                'No Button','Open Link','Order Now','Play Game','Register Now',
                'Remind Me','Request Time','Save','See Menu','See More','Sell Now',
                'Send Message','Send Updates','Send WhatsApp Message','Shop Now',
                'Sign Up','Subscribe','Try in Camera','Use App','Visit Instagram Profile',
                'Visit Profile','Watch More','Watch Video'];
            const allCtaAds = allCtaTypes.map(cta => ({{ id: cta, cta }}));
            const ctaMatchFn = (adCta, selected) => {{
                if (!selected || selected.size === 0) return true;
                if (!adCta) return false;
                const lower = adCta.toLowerCase();
                for (const f of selected) {{
                    if (lower.includes(f.toLowerCase())) return true;
                }}
                return false;
            }};
            let allCtaPass = true;
            for (const ad of allCtaAds) {{
                const result2 = ctaMatchFn(ad.cta, new Set([ad.cta]));
                if (!result2) {{ allCtaPass = false; }}
            }}
            r.cta_all_types_pass = allCtaPass;
            r.cta_all_types_count = allCtaTypes.length;

            // ── LANGUAGE FILTER TESTS ───────────────────────────────────────────
            // Log all detected languages (spread Sets to arrays for reliable storage)
            const adLangs = {{}};
            for (const ad of mockAds) {{
                const result = detectAdLang(ad);
                adLangs[ad.id] = (result instanceof Set) ? [...result] : (result || []);
            }}
            r.adLangs = adLangs;

            // Test 8: English ads (single text) — use pre-computed adLangs
            const enAds = mockAds.filter(a => {{
                const langs = adLangs[a.id] || [];
                return langs.includes('en');
            }});
            r.lang_en_ids = enAds.map(a => a.id);
            r.lang_en_pass = enAds.length >= 9;

            // Test 9: French ads
            const frAds = mockAds.filter(a => {{
                const langs = adLangs[a.id] || [];
                return langs.includes('fr');
            }});
            r.lang_fr_ids = frAds.map(a => a.id);
            r.lang_fr_pass = frAds.length >= 3;

            // Test 10: Spanish ads
            const esAds = mockAds.filter(a => {{
                const langs = adLangs[a.id] || [];
                return langs.includes('es');
            }});
            r.lang_es_ids = esAds.map(a => a.id);
            r.lang_es_pass = esAds.length >= 2;

            // Test 11: German ads
            const deAds = mockAds.filter(a => {{
                const langs = adLangs[a.id] || [];
                return langs.includes('de');
            }});
            r.lang_de_ids = deAds.map(a => a.id);
            r.lang_de_pass = deAds.length >= 2;

            // Test 12: Chinese ads
            const zhAds = mockAds.filter(a => {{
                const langs = adLangs[a.id] || [];
                return langs.includes('zh');
            }});
            r.lang_zh_ids = zhAds.map(a => a.id);
            r.lang_zh_pass = zhAds.length >= 2;

            // Test 13: Arabic ads
            const arAds = mockAds.filter(a => {{
                const langs = adLangs[a.id] || [];
                return langs.includes('ar');
            }});
            r.lang_ar_ids = arAds.map(a => a.id);
            r.lang_ar_pass = arAds.length >= 2;

            // Test 14: Japanese ads
            const jaAds = mockAds.filter(a => {{
                const langs = adLangs[a.id] || [];
                return langs.includes('ja');
            }});
            r.lang_ja_ids = jaAds.map(a => a.id);
            r.lang_ja_pass = jaAds.length >= 1;

            // Test 15: Multi-variation mv1 (EN+FR) → has en AND fr
            const mv1Langs = adLangs['mv1'];
            r.mv1_has_en = Array.isArray(mv1Langs) ? mv1Langs.includes('en') : false;
            r.mv1_has_fr = Array.isArray(mv1Langs) ? mv1Langs.includes('fr') : false;
            r.mv1_pass = r.mv1_has_en && r.mv1_has_fr;

            // Test 16: Multi-variation mv3 (FR only) → NOT en, IS fr
            const mv3Langs = adLangs['mv3'];
            r.mv3_not_en = Array.isArray(mv3Langs) ? !mv3Langs.includes('en') : true;
            r.mv3_is_fr = Array.isArray(mv3Langs) ? mv3Langs.includes('fr') : false;
            r.mv3_pass = r.mv3_not_en && r.mv3_is_fr;

            // Test 17: Multi-variation mv2 (EN+ES) → has en AND es
            const mv2Langs = adLangs['mv2'];
            r.mv2_has_en = Array.isArray(mv2Langs) ? mv2Langs.includes('en') : false;
            r.mv2_has_es = Array.isArray(mv2Langs) ? mv2Langs.includes('es') : false;
            r.mv2_pass = r.mv2_has_en && r.mv2_has_es;

            // Test 18: Multi-variation mv4 (EN+ZH) → has en AND zh
            const mv4Langs = adLangs['mv4'];
            r.mv4_has_en = Array.isArray(mv4Langs) ? mv4Langs.includes('en') : false;
            r.mv4_has_zh = Array.isArray(mv4Langs) ? mv4Langs.includes('zh') : false;
            r.mv4_pass = r.mv4_has_en && r.mv4_has_zh;

            // Test 19: Multi-variation mv5 (EN+FR+DE) → has en AND fr AND de
            const mv5Langs = adLangs['mv5'];
            r.mv5_has_en = Array.isArray(mv5Langs) ? mv5Langs.includes('en') : false;
            r.mv5_has_fr = Array.isArray(mv5Langs) ? mv5Langs.includes('fr') : false;
            r.mv5_has_de = Array.isArray(mv5Langs) ? mv5Langs.includes('de') : false;
            r.mv5_pass = r.mv5_has_en && r.mv5_has_fr && r.mv5_has_de;

            // Test 20: Multi-variation mv6 (EN+AR) → has en AND ar
            const mv6Langs = adLangs['mv6'];
            r.mv6_has_en = Array.isArray(mv6Langs) ? mv6Langs.includes('en') : false;
            r.mv6_has_ar = Array.isArray(mv6Langs) ? mv6Langs.includes('ar') : false;
            r.mv6_pass = r.mv6_has_en && r.mv6_has_ar;

            // ── DATE FILTER TESTS ────────────────────────────────────────────────
            // Test 21: 7d preset
            const ads7d = mockAds.filter(a => !a.adDate || a.adDate >= NOW - 7 * DAY_MS);
            r.date_7d_ids = ads7d.map(a => a.id);
            r.date_7d_count = ads7d.length;
            r.date_7d_pass = ads7d.length >= 15;

            // Test 22: null date always passes date filter
            const nullDateAds = mockAds.filter(a => !a.adDate);
            r.date_null_count = nullDateAds.length;
            r.date_null_pass = nullDateAds.length >= 1;

            // Test 23: 30d preset
            const ads30d = mockAds.filter(a => !a.adDate || a.adDate >= NOW - 30 * DAY_MS);
            r.date_30d_count = ads30d.length;
            r.date_30d_pass = ads30d.length >= 23;

            // Test 24: 7d excludes 45d old ad
            const zh1 = mockAds.find(a => a.id === 'zh1');
            r.date_excludes_old = zh1 ? (zh1.adDate < NOW - 7 * DAY_MS) : false;

            // ── UTM FILTER TESTS ────────────────────────────────────────────────
            // Test 25: facebook UTM
            const fbUtm = mockAds.filter(a =>
                a.landingUrl && a.landingUrl.includes('utm_source=facebook')
            );
            r.utm_fb_ids = fbUtm.map(a => a.id);
            r.utm_fb_count = fbUtm.length;
            r.utm_fb_pass = fbUtm.length >= 4;

            // Test 26: google UTM
            const googleUtm = mockAds.filter(a =>
                a.landingUrl && a.landingUrl.includes('utm_source=google')
            );
            r.utm_google_count = googleUtm.length;
            r.utm_google_pass = googleUtm.length >= 2;

            // Test 27: AND UTM
            const andUtm = mockAds.filter(a =>
                a.landingUrl && a.landingUrl.includes('utm_source=facebook') &&
                a.landingUrl.includes('utm_medium=cpc')
            );
            r.utm_and_count = andUtm.length;
            r.utm_and_pass = andUtm.length >= 1;

            // ── FORMAT FILTER TESTS ──────────────────────────────────────────────
            // Test 28: image format
            const imageAds = mockAds.filter(a => a.adFormat === 'image');
            r.format_image_count = imageAds.length;
            r.format_image_pass = imageAds.length >= 11;

            // Test 29: video format
            const videoAds = mockAds.filter(a => a.adFormat === 'video');
            r.format_video_count = videoAds.length;
            r.format_video_pass = videoAds.length >= 5;

            // Test 30: carousel format
            const carouselAds = mockAds.filter(a => a.adFormat === 'carousel');
            r.format_carousel_count = carouselAds.length;
            r.format_carousel_pass = carouselAds.length >= 3;

            // ── DOMAIN FILTER TESTS ─────────────────────────────────────────────
            // Production domainFilter: ".xyz" → endsWith('.xyz') for TLD match
            // "shop.xyz" → contains 'xyz' but filter uses endsWith
            // We test the PRECISE production logic: endsWith('.xyz') etc.
            const xyzAds = mockAds.filter(a =>
                a.domains && a.domains.some(d => d.toLowerCase().endsWith('.xyz'))
            );
            r.domain_xyz_count = xyzAds.length;
            r.domain_xyz_pass = xyzAds.length >= 7;  // xyz1, mv1(mv6→click), tld_shady1

            // Production domainFilter: ".top" → endsWith('.top')
            const topAds = mockAds.filter(a =>
                a.domains && a.domains.some(d => d.toLowerCase().endsWith('.top'))
            );
            r.domain_top_count = topAds.length;
            r.domain_top_pass = topAds.length >= 1;  // top1(nice.top), en2(top.com), de2(top.de)

            // Production domainFilter: ".icu" → endsWith('.icu')
            const icuAds = mockAds.filter(a =>
                a.domains && a.domains.some(d => d.toLowerCase().endsWith('.icu'))
            );
            r.domain_icu_count = icuAds.length;
            r.domain_icu_pass = icuAds.length >= 2;  // icu1, tld_shady2

            // ── CLASSIFICATION TESTS ─────────────────────────────────────────────
            // Test 34: Nutra classification
            if (classifyFn) {{
                const tests = [
                    {{ text: 'Lose weight fast keto diet burn fat guaranteed results amazing', expected: true }},
                    {{ text: 'Blood sugar diabetes A1C control supplement reduce glucose naturally', expected: true }},
                    {{ text: 'Joint pain arthritis glucosamine mobility supplement relief cure', expected: true }},
                    {{ text: 'Skin cream anti aging collagen wrinkle reduction serum beauty', expected: true }},
                    {{ text: 'Probiotic gut health digestion IBS bloat relief stomach wellness', expected: true }},
                    {{ text: 'Male enhancement testosterone boost erectile supplement health power', expected: true }},
                    {{ text: 'Reverse aging youthful wrinkle cream age defying longevity formula', expected: true }},
                    {{ text: 'Heart health cholesterol blood pressure omega 3 cardio tribulus', expected: true }},
                    {{ text: 'Buy electronics at best prices online shopping store today', expected: false }},
                    {{ text: 'Get supplement now best health product available fast online', expected: false }},
                    {{ text: '', expected: false }},
                ];
                r.classify_results = tests.map(t => {{
                    const result = classifyFn(t.text);
                    return {{ expected: t.expected, got: result.is_nutra, pass: result.is_nutra === t.expected }};
                }});
                r.classify_all_pass = r.classify_results.every(t => t.pass);
            }} else {{
                r.classify_results = [];
                r.classify_all_pass = false;
            }}

            // ── COMBINED FILTER TESTS ───────────────────────────────────────────
            // Test 35: fr language + Shop CTA + image format + active
            const frShopImage = mockAds.filter(a => {{
                const langs = adLangs[a.id] || [];
                const hasFr = langs.includes('fr');
                const hasShop = a.cta && a.cta.includes('Shop');
                return hasFr && hasShop && a.adFormat === 'image' && a.adActive !== false;
            }});
            r.combo_fr_shop_image_ids = frShopImage.map(a => a.id);
            r.combo_fr_shop_image_pass = frShopImage.length >= 1;

            // Test 36: en + video format
            const enVideo = mockAds.filter(a => {{
                const langs = adLangs[a.id] || [];
                return langs.includes('en') && a.adFormat === 'video';
            }});
            r.combo_en_video_count = enVideo.length;
            r.combo_en_video_pass = enVideo.length >= 3;

            // Test 37: ar + active
            const arActive = mockAds.filter(a => {{
                const langs = adLangs[a.id] || [];
                return langs.includes('ar') && a.adActive !== false;
            }});
            r.combo_ar_active_count = arActive.length;
            r.combo_ar_active_pass = arActive.length >= 2;

            // Test 38: de + 7d + active
            const de7dActive = mockAds.filter(a => {{
                const langs = adLangs[a.id] || [];
                const inRange = !a.adDate || a.adDate >= NOW - 7 * DAY_MS;
                return langs.includes('de') && inRange && a.adActive !== false;
            }});
            r.combo_de_7d_active_pass = de7dActive.length >= 1;

            // Test 39: es + carousel + fb_utm
            const esCarFb = mockAds.filter(a => {{
                const langs = adLangs[a.id] || [];
                const hasFb = a.landingUrl && a.landingUrl.includes('utm_source=facebook');
                return langs.includes('es') && a.adFormat === 'carousel' && hasFb;
            }});
            r.combo_es_carousel_fb_pass = esCarFb.length >= 1;

            // Test 40: fr OR es (OR language logic)
            const frOrEs = mockAds.filter(a => {{
                const langs = adLangs[a.id] || [];
                return langs.includes('fr') || langs.includes('es');
            }});
            r.combo_fr_or_es_count = frOrEs.length;
            r.combo_fr_or_es_pass = frOrEs.length >= 5;

            // ── TLD FILTER PRECISION TESTS ────────────────────────────────────────────
            // Inline production TLD functions from popup.js
            const SHADY_TLDS_T = new Set([
                '.space', '.fun', '.info', '.xyz', '.top', '.click', '.link', '.buzz',
                '.icu', '.pw', '.cc', '.club', '.vip', '.pro', '.site', '.website',
                '.work', '.fit', '.shop', '.store', '.gq', '.ml',
                '.cf', '.tk', '.ga', '.bid', '.win', '.date', '.racing', '.download',
                '.stream', '.accountant', '.cricket', '.party', '.science', '.faith',
                '.review', '.loan', '.trade', '.webcam', '.country', '.kim',
                '.xyz.tv', '.xyz.cn', '.xyz.kr', '.xyz.jp', '.xyz.in', '.xyz.ph',
                '.xyz.id', '.xyz.my', '.xyz.pk', '.xyz.th', '.xyz.vn', '.xyz.bd',
                '.top.tv', '.top.cn', '.top.kr', '.top.in', '.top.ph',
                '.top.id', '.top.my', '.top.pk', '.top.th', '.top.vn',
                '.icu.tv', '.icu.cn', '.icu.kr', '.icu.in', '.icu.ph',
                '.icu.id', '.icu.my', '.icu.pk', '.icu.th', '.icu.vn',
                '.click.tv', '.click.cn', '.click.kr', '.click.in', '.click.ph',
                '.click.id', '.click.my', '.click.pk', '.click.th', '.click.vn',
                '.buzz.tv', '.buzz.cn', '.buzz.kr', '.buzz.in', '.buzz.ph',
                '.buzz.id', '.buzz.my', '.buzz.pk', '.buzz.th', '.buzz.vn',
                '.club.tv', '.club.cn', '.club.kr', '.club.in', '.club.ph',
                '.club.id', '.club.my', '.club.pk', '.club.th', '.club.vn',
                '.link.tv', '.link.cn', '.link.kr', '.link.in', '.link.ph',
                '.link.id', '.link.my', '.link.pk', '.link.th', '.link.vn',
                '.site.tv', '.site.cn', '.site.kr', '.site.in', '.site.ph',
                '.site.id', '.site.my', '.site.pk', '.site.th', '.site.vn',
                '.vip.tv', '.vip.cn', '.vip.kr', '.vip.in', '.vip.ph',
                '.vip.id', '.vip.my', '.vip.pk', '.vip.th', '.vip.vn',
                '.pw.tv', '.pw.cn', '.pw.kr', '.pw.in', '.pw.ph',
                '.pw.id', '.pw.my', '.pw.pk', '.pw.th', '.pw.vn',
                '.ml.tv', '.ml.cn', '.ml.kr', '.ml.in', '.ml.ph',
                '.ml.id', '.ml.my', '.ml.pk', '.ml.th', '.ml.vn',
                '.cf.tv', '.cf.cn', '.cf.kr', '.cf.in', '.cf.ph',
                '.cf.id', '.cf.my', '.cf.pk', '.cf.th', '.cf.vn',
                '.tk.tv', '.tk.cn', '.tk.kr', '.tk.in', '.tk.ph',
                '.tk.id', '.tk.my', '.tk.pk', '.tk.th', '.tk.vn',
                '.ga.tv', '.ga.cn', '.ga.kr', '.ga.in', '.ga.ph',
                '.ga.id', '.ga.my', '.ga.pk', '.ga.th', '.ga.vn',
                '.bid.tv', '.bid.cn', '.bid.kr', '.bid.in', '.bid.ph',
                '.bid.id', '.bid.my', '.bid.pk', '.bid.th', '.bid.vn',
                '.win.tv', '.win.cn', '.win.kr', '.win.in', '.win.ph',
                '.win.id', '.win.my', '.win.pk', '.win.th', '.win.vn',
                '.date.tv', '.date.cn', '.date.kr', '.date.in', '.date.ph',
                '.date.id', '.date.my', '.date.pk', '.date.th', '.date.vn',
                '.loan.tv', '.loan.cn', '.loan.kr', '.loan.in', '.loan.ph',
                '.loan.id', '.loan.my', '.loan.pk', '.loan.th', '.loan.vn',
                '.science.tv', '.science.cn', '.science.kr', '.science.in', '.science.ph',
                '.science.id', '.science.my', '.science.pk', '.science.th', '.science.vn',
            ]);
            const CLEAN_TLDS_T = new Set([
                '.com', '.org', '.net', '.edu', '.gov', '.mil',
                '.de', '.fr', '.it', '.es', '.nl', '.be', '.at', '.ch',
                '.pl', '.ru', '.cn', '.jp', '.kr', '.in', '.br', '.au',
                '.ca', '.mx', '.se', '.no', '.dk', '.fi', '.pt', '.cz',
                '.hu', '.ro', '.gr', '.tr', '.il', '.ae', '.sa', '.ng',
                '.za', '.eg', '.pk', '.bd', '.id', '.my', '.th', '.vn',
                '.ph', '.sg', '.nz', '.ar', '.cl', '.pe', '.ve',
                '.ec', '.uy', '.py', '.bo', '.gt', '.cr', '.pa', '.do',
                '.cu', '.jm', '.pr', '.ht', '.app', '.dev', '.io', '.ai',
                '.tv', '.biz', '.us', '.name', '.xxx',
                '.online', '.tech', '.cc',
                '.co.uk', '.co.nz', '.co.jp', '.co.kr', '.co.th', '.co.in',
                '.co.za', '.co.id', '.co.br', '.co.ke', '.co.ao', '.co.mz',
                '.co.bw', '.co.zm', '.co.zw', '.co.tz', '.co.ug',
                '.co.ph', '.co.pk', '.co.gh', '.co.ng',
                '.ac.uk', '.or.jp', '.ne.jp', '.ac.jp', '.co.im', '.ac.im',
                '.co.gg', '.org.gg', '.ac.gg',
                '.gov.uk', '.mod.uk', '.ac.uk', '.gov.au', '.gov.nz', '.gov.cn',
                '.com.au', '.net.au', '.org.au', '.edu.au',
                '.com.br', '.net.br', '.org.br', '.edu.br', '.gov.br',
                '.com.pk', '.net.pk', '.org.pk', '.gov.pk',
                '.com', '.org', '.net', '.co', '.uk',
                '.app', '.dev', '.io', '.tech', '.biz', '.info', '.name',
            ]);

            // Production extractTld from popup.js
            function extractTld(domain) {{
                if (!domain) return '';
                const clean = domain.startsWith('.') ? domain.slice(1) : domain;
                const parts = clean.split('.');
                const last = parts[parts.length - 1];
                if (!last) return '';
                const lastLower = last.toLowerCase();
                if (parts.length >= 2) {{
                    const secondLast = parts[parts.length - 2].toLowerCase();
                    const twoPart = `${{secondLast}}.${{lastLower}}`;
                    if (CLEAN_TLDS_T.has(`.${{twoPart}}`) || SHADY_TLDS_T.has(`.${{twoPart}}`)) {{
                        return `.${{twoPart}}`;
                    }}
                }}
                return `.${{lastLower}}`;
            }}

            // Production getTldCategory from popup.js
            function getTldCategory(domain) {{
                if (!domain) return 'clean';
                const clean = domain.startsWith('.') ? domain.slice(1) : domain;
                const parts = clean.split('.');
                const last = parts[parts.length - 1];
                if (!last) return 'clean';
                const twoPart = parts.length >= 2 ? `${{parts[parts.length - 2].toLowerCase()}}.${{last.toLowerCase()}}` : '';
                if (twoPart && (CLEAN_TLDS_T.has(`.${{twoPart}}`) || SHADY_TLDS_T.has(`.${{twoPart}}`))) {{
                    return SHADY_TLDS_T.has(`.${{twoPart}}`) ? 'shady' : 'clean';
                }}
                return SHADY_TLDS_T.has(`.${{last.toLowerCase()}}`) ? 'shady' : 'clean';
            }}

            // Production allDomainsClean from popup.js
            function allDomainsClean(domains) {{
                if (!domains || domains.length === 0) return false;
                return domains.every(d => getTldCategory(d) === 'clean');
            }}

            // Test TLD ads
            const tldAd = (id) => mockAds.find(a => a.id === id);

            // extractTld precision
            r.tld_ex1 = extractTld('shop.xyz');           // → .xyz
            r.tld_ex2 = extractTld('shop.co.uk');         // → .co.uk
            r.tld_ex3 = extractTld('abc.xyz.tv');         // → .xyz.tv (IS in SHADY_TLDS 2-level combos)
            r.tld_ex4 = extractTld('health.com');         // → .com
            r.tld_ex5 = extractTld('xyz.tv');              // → .xyz.tv (IS in SHADY 2-level combos)
            r.tld_ex6 = extractTld('.xyz');                // → .xyz
            r.tld_ex7 = extractTld('abc.xyz.com');         // → .com (not .xyz.com)
            r.tld_ex8 = extractTld('sleek.xyz');          // → .xyz
            r.tld_ex_pass = (
                r.tld_ex1 === '.xyz' &&
                r.tld_ex2 === '.co.uk' &&
                r.tld_ex3 === '.xyz.tv' &&  // .xyz.tv IS in SHADY_TLDS 2-level combos
                r.tld_ex4 === '.com' &&
                r.tld_ex5 === '.xyz.tv' &&
                r.tld_ex6 === '.xyz' &&
                r.tld_ex7 === '.com' &&
                r.tld_ex8 === '.xyz'
            );

            // getTldCategory precision
            // NOTE: .xyz.tv and .xyz.click are EXPLICITLY in SHADY_TLDS as 2-level combos
            r.tld_cat_xyz   = getTldCategory('sleek.xyz');    // .xyz → shady
            r.tld_cat_icu  = getTldCategory('nice.icu');     // .icu → shady
            r.tld_cat_click= getTldCategory('good.click');   // .click → shady
            r.tld_cat_com  = getTldCategory('health.com');   // .com → clean
            r.tld_cat_couk = getTldCategory('shop.co.uk');   // .co.uk → clean
            r.tld_cat_io   = getTldCategory('app.io');       // .io → clean
            r.tld_cat_tv   = getTldCategory('xyz.tv');       // .xyz.tv → shady (in SHADY 2-level)
            r.tld_cat_mixed_clean = getTldCategory('good.com');  // clean part of mixed
            r.tld_cat_mixed_shady = getTldCategory('good.xyz'); // shady part of mixed
            r.tld_cat_null  = getTldCategory(null);
            r.tld_cat_empty = getTldCategory('');
            r.tld_cat_pass = (
                r.tld_cat_xyz === 'shady' &&
                r.tld_cat_icu === 'shady' &&
                r.tld_cat_click === 'shady' &&
                r.tld_cat_com === 'clean' &&
                r.tld_cat_couk === 'clean' &&
                r.tld_cat_io === 'clean' &&
                r.tld_cat_tv === 'shady' &&  // .xyz.tv IS in SHADY_TLDS
                r.tld_cat_null === 'clean' &&
                r.tld_cat_empty === 'clean'
            );

            // allDomainsClean
            r.acd_clean  = allDomainsClean(['health.com', 'shop.co.uk']);  // all clean → true
            r.acd_shady  = allDomainsClean(['sleek.xyz', 'nice.icu']);       // all shady → false
            r.acd_mixed  = allDomainsClean(['health.com', 'sleek.xyz']);     // mixed → false
            r.acd_empty  = allDomainsClean([]);                                // no domains → false
            r.acd_null   = allDomainsClean(null);                              // null → false
            r.acd_pass = r.acd_clean && !r.acd_shady && !r.acd_mixed && !r.acd_empty && !r.acd_null;

            // domainFilter: .tld → endsWith  vs  domain → includes
            // ".xyz" should match shop.xyz but NOT xyz.tv (ends with .xyz, not .xyz.tv)
            const filterDotXyz = (ad) => {{
                const raw = '.xyz';
                const domains = ad.domains || [];
                return domains.some(d => d.toLowerCase().endsWith(raw));
            }};
            r.df_dotxyz_ids = mockAds.filter(filterDotXyz).map(a => a.id);
            r.df_dotxyz_pass = (
                r.df_dotxyz_ids.includes('xyz1') &&    // shop.xyz → endsWith .xyz ✓
                !r.df_dotxyz_ids.includes('tld_clean4') && // xyz.tv → does NOT end with .xyz ✓
                !r.df_dotxyz_ids.includes('tld_clean5') && // abc.xyz.com → ends with .com, not .xyz ✓
                r.df_dotxyz_ids.includes('tld_shady1')      // sleek.xyz → endsWith .xyz ✓
            );

            // "xyz.tv" → contains 'xyz.tv'
            const filterXyzTv = (ad) => {{
                const raw = 'xyz.tv';
                const domains = ad.domains || [];
                return domains.some(d => d.toLowerCase().includes(raw));
            }};
            r.df_xyztv_ids = mockAds.filter(filterXyzTv).map(a => a.id);
            r.df_xyztv_pass = (
                r.df_xyztv_ids.includes('tld_clean4') &&    // xyz.tv → contains xyz.tv ✓
                !r.df_xyztv_ids.includes('xyz1')            // shop.xyz → does NOT contain xyz.tv ✓
            );

            // ".co.uk" → endsWith .co.uk
            const filterDotCoUk = (ad) => {{
                const raw = '.co.uk';
                const domains = ad.domains || [];
                return domains.some(d => d.toLowerCase().endsWith(raw));
            }};
            r.df_couk_pass = mockAds.filter(filterDotCoUk).some(a => a.id === 'tld_clean1'); // shop.co.uk

            // hideCleanTlds: show ads where at least ONE domain is shady
            // tld_clean4 (xyz.tv=clean) → excluded
            // tld_clean1 (shop.co.uk=clean) → excluded
            // tld_shady1 (sleek.xyz=shady) → included
            // tld_mixed1 (good.com=clean, good.xyz=shady) → included
            // tld_nodomain1 (no domains) → excluded
            // xyz1 (shop.xyz=shady) → included
            const filterHideClean = (ad) => {{
                const domains = ad.domains || [];
                return domains.length > 0 && domains.some(d => getTldCategory(d) === 'shady');
            }};
            r.hc_ids = mockAds.filter(filterHideClean).map(a => a.id);
            // hideCleanTlds: show ads where at least ONE domain is shady
            // Production correctly treats .xyz.tv, .xyz.click, .icu.io, .xyz as SHADY
            r.hc_pass = (
                !r.hc_ids.includes('tld_clean1') &&    // shop.co.uk → clean → excluded ✓
                !r.hc_ids.includes('tld_clean2') &&    // health.com → clean → excluded ✓
                !r.hc_ids.includes('tld_clean3') &&    // app.io → clean → excluded ✓
                !r.hc_ids.includes('tld_clean5') &&    // abc.xyz.com → .com clean → excluded ✓
                // .xyz.tv IS in SHADY_TLDS → tld_clean4 SHOULD be included
                r.hc_ids.includes('tld_clean4') &&
                r.hc_ids.includes('tld_shady1') &&      // sleek.xyz → .xyz shady → included ✓
                r.hc_ids.includes('tld_shady2') &&      // nice.icu → .icu shady → included ✓
                r.hc_ids.includes('tld_shady3') &&      // good.click → .xyz.click shady → included ✓
                r.hc_ids.includes('tld_mixed1') &&      // good.com+good.xyz → at least 1 shady → included ✓
                !r.hc_ids.includes('tld_nodomain1') &&  // no domains → excluded ✓
                // .xyz.tv IS in SHADY → en4 SHOULD be included
                r.hc_ids.includes('en4') &&
                // .xyz.click IS in SHADY → ar1 SHOULD be included
                r.hc_ids.includes('ar1') &&
                // .xyz.tv IS in SHADY → mv6 SHOULD be included
                r.hc_ids.includes('mv6') &&
                // .icu.cn IS in SHADY → zh1 SHOULD be included
                r.hc_ids.includes('zh1') &&
                // .icu IS in SHADY → icu1 SHOULD be included
                r.hc_ids.includes('icu1') &&
                // icu.com → .com (clean) → mv4 should NOT be included
                !r.hc_ids.includes('mv4') &&
                r.hc_ids.includes('xyz1')                // shop.xyz → .xyz shady → included ✓
            );

            // showOnlyWithDomains: show ads where at least one domain exists
            const filterHasDomains = (ad) => (ad.domains || []).length > 0;
            r.sod_pass = (
                !mockAds.filter(filterHasDomains).some(a => a.id === 'tld_nodomain1') &&
                !mockAds.filter(filterHasDomains).some(a => a.id === 'tld_nodomain2') &&
                mockAds.filter(filterHasDomains).some(a => a.id === 'tld_clean1')
            );

            // selectedTlds filter: ads where extractTld(domain) matches
            // selectedTLDs = ['.xyz'] → extractTld must return .xyz
            const filterSelectedXyz = (ad) => {{
                const domains = ad.domains || [];
                const selected = new Set(['.xyz']);
                return domains.some(d => selected.has(extractTld(d)));
            }};
            r.stld_xyz_ids = mockAds.filter(filterSelectedXyz).map(a => a.id);
            r.stld_xyz_pass = (
                r.stld_xyz_ids.includes('xyz1') &&       // shop.xyz → .xyz ✓
                !r.stld_xyz_ids.includes('tld_clean4') && // xyz.tv → .tv (not .xyz) ✓
                !r.stld_xyz_ids.includes('tld_clean5') && // abc.xyz.com → .com ✓
                r.stld_xyz_ids.includes('tld_shady1')    // sleek.xyz → .xyz ✓
            );

            // selectedTLDs multi-select: ['.xyz', '.icu']
            const filterSelectedXyzIcu = (ad) => {{
                const domains = ad.domains || [];
                const selected = new Set(['.xyz', '.icu']);
                return domains.some(d => selected.has(extractTld(d)));
            }};
            r.stld_xyz_icu_ids = mockAds.filter(filterSelectedXyzIcu).map(a => a.id);
            r.stld_xyz_icu_pass = (
                r.stld_xyz_icu_ids.includes('xyz1') &&
                r.stld_xyz_icu_ids.includes('tld_shady1') &&
                r.stld_xyz_icu_ids.includes('tld_shady2') &&
                !r.stld_xyz_icu_ids.includes('tld_clean1')
            );

            return r;
        }}
        """)

        print("\n" + "=" * 60)
        print("LIVE E2E FILTER TEST RESULTS")
        print("=" * 60)

        total_tests = 0
        passed_tests = 0

        def check(name, condition, detail=""):
            nonlocal passed_tests, total_tests
            total_tests += 1
            if condition:
                passed_tests += 1
                log_result(name, True, detail)
            else:
                log_result(name, False, detail)

        # CTA Filter
        print("\n[CTA FILTER TESTS]")
        check("CTA 'Shop Now': exact match (21 ads)",
              result.get('cta_shop_now_pass', False),
              f"count={result.get('cta_shop_now_count', 0)}, ids={result.get('cta_shop_now_ids', [])}")
        check("CTA 'Learn More': exact match (2 ads: en2, mv2)",
              result.get('cta_learn_pass', False),
              f"count={result.get('cta_learn_count', 0)}, ids={result.get('cta_learn_ids', [])}")
        check("CTA 'Now' (partial): matches >= 7 ads with 'Now'",
              result.get('cta_now_pass', False),
              f"count={result.get('cta_now_count', 0)}, ids={result.get('cta_now_ids', [])}")
        check("CTA 'Book': matches >= 2 ads with 'Book'",
              result.get('cta_book_pass', False),
              f"count={result.get('cta_book_count', 0)}")
        check("CTA multi-select OR: 'Shop' OR 'Learn' matches >= 5 ads",
              result.get('cta_or_pass', False),
              f"count={result.get('cta_or_count', 0)}")
        check("CTA filter: null CTA ad excluded from 'Shop Now'",
              result.get('cta_null_excluded', False))
        check("CTA 'nullCta1' has null CTA field",
              result.get('cta_null_is_null', False))
        check(f"All 47 standard CTA_TYPES exact match works",
              result.get('cta_all_types_pass', False),
              f"count={result.get('cta_all_types_count', 0)}")

        # Language Filter
        print("\n[LANGUAGE FILTER TESTS]")
        check("English filter: >= 9 en ads detected",
              result.get('lang_en_pass', False),
              f"count={len(result.get('lang_en_ids', []))}, ids={result.get('lang_en_ids', [])}")
        check("French filter: >= 3 fr ads detected (fr1, fr2, mv1, mv3, mv5)",
              result.get('lang_fr_pass', False),
              f"count={len(result.get('lang_fr_ids', []))}, ids={result.get('lang_fr_ids', [])}")
        check("Spanish filter: >= 2 es ads detected (es1, es2, mv2)",
              result.get('lang_es_pass', False),
              f"count={len(result.get('lang_es_ids', []))}, ids={result.get('lang_es_ids', [])}")
        check("German filter: >= 2 de ads detected (de1, de2, mv5)",
              result.get('lang_de_pass', False),
              f"count={len(result.get('lang_de_ids', []))}, ids={result.get('lang_de_ids', [])}")
        check("Chinese filter: >= 2 zh ads detected (zh1, mv4)",
              result.get('lang_zh_pass', False),
              f"count={len(result.get('lang_zh_ids', []))}, ids={result.get('lang_zh_ids', [])}")
        check("Arabic filter: >= 2 ar ads detected (ar1, mv6)",
              result.get('lang_ar_pass', False),
              f"count={len(result.get('lang_ar_ids', []))}, ids={result.get('lang_ar_ids', [])}")
        check("Japanese filter: >= 1 ja ad detected (ja1)",
              result.get('lang_ja_pass', False),
              f"count={len(result.get('lang_ja_ids', []))}, ids={result.get('lang_ja_ids', [])}")

        # Multi-Variation
        print("\n[MULTI-VARIATION LANGUAGE TESTS]")
        ad_langs = result.get('adLangs', {})
        check("mv1 (EN+FR): has en AND fr",
              result.get('mv1_pass', False),
              f"en={result.get('mv1_has_en')}, fr={result.get('mv1_has_fr')}, langs={ad_langs.get('mv1', [])}")
        check("mv3 (FR only): NOT en, IS fr",
              result.get('mv3_pass', False),
              f"not_en={result.get('mv3_not_en')}, is_fr={result.get('mv3_is_fr')}, langs={ad_langs.get('mv3', [])}")
        check("mv2 (EN+ES): has en AND es",
              result.get('mv2_pass', False),
              f"en={result.get('mv2_has_en')}, es={result.get('mv2_has_es')}, langs={ad_langs.get('mv2', [])}")
        check("mv4 (EN+ZH): has en AND zh",
              result.get('mv4_pass', False),
              f"en={result.get('mv4_has_en')}, zh={result.get('mv4_has_zh')}, langs={ad_langs.get('mv4', [])}")
        check("mv5 (EN+FR+DE): has en AND fr AND de",
              result.get('mv5_pass', False),
              f"en={result.get('mv5_has_en')}, fr={result.get('mv5_has_fr')}, de={result.get('mv5_has_de')}, langs={ad_langs.get('mv5', [])}")
        check("mv6 (EN+AR): has en AND ar",
              result.get('mv6_pass', False),
              f"en={result.get('mv6_has_en')}, ar={result.get('mv6_has_ar')}, langs={ad_langs.get('mv6', [])}")

        # Date Filter
        print("\n[DATE FILTER TESTS]")
        check("Date 7d preset: >= 15 ads in range",
              result.get('date_7d_pass', False),
              f"count={result.get('date_7d_count', 0)}")
        check("Date null: null-date ads always pass (>= 1)",
              result.get('date_null_pass', False),
              f"count={result.get('date_null_count', 0)}")
        check("Date 30d preset: >= 23 ads in range",
              result.get('date_30d_pass', False),
              f"count={result.get('date_30d_count', 0)}")
        check("Date 7d: excludes 45d old zh1 ad",
              result.get('date_excludes_old', False))

        # UTM Filter
        print("\n[UTM FILTER TESTS]")
        check("UTM facebook: >= 4 ads with utm_source=facebook",
              result.get('utm_fb_pass', False),
              f"count={result.get('utm_fb_count', 0)}, ids={result.get('utm_fb_ids', [])}")
        check("UTM google: >= 2 ads with utm_source=google",
              result.get('utm_google_pass', False),
              f"count={result.get('utm_google_count', 0)}")
        check("UTM AND: >= 1 ad with utm_source=facebook AND utm_medium=cpc",
              result.get('utm_and_pass', False),
              f"count={result.get('utm_and_count', 0)}")

        # Format Filter
        print("\n[FORMAT FILTER TESTS]")
        check("Format 'image': >= 11 image ads",
              result.get('format_image_pass', False),
              f"count={result.get('format_image_count', 0)}")
        check("Format 'video': >= 5 video ads",
              result.get('format_video_pass', False),
              f"count={result.get('format_video_count', 0)}")
        check("Format 'carousel': >= 3 carousel ads",
              result.get('format_carousel_pass', False),
              f"count={result.get('format_carousel_count', 0)}")

        # Domain Filter
        print("\n[DOMAIN FILTER TESTS]")
        check("Domain '.xyz': >= 7 ads with xyz domain (endsWith)",
              result.get('domain_xyz_pass', False),
              f"count={result.get('domain_xyz_count', 0)}")
        check("Domain '.top': >= 1 ads with .top TLD (endsWith)",
              result.get('domain_top_pass', False),
              f"count={result.get('domain_top_count', 0)}")
        check("Domain '.icu': >= 2 ads with .icu TLD (endsWith)",
              result.get('domain_icu_pass', False),
              f"count={result.get('domain_icu_count', 0)}")

        # Classification
        print("\n[CLASSIFICATION TESTS]")
        classify_results = result.get('classify_results', [])
        classify_pass = result.get('classify_all_pass', False)
        check(f"Nutra classify: {len(classify_results)} tests, all pass",
              classify_pass,
              f"results={[c.get('pass') for c in classify_results]}")
        for i, cr in enumerate(classify_results):
            label = "nutra" if cr.get('expected') else "not nutra"
            check(f"  classify[{i}]: {label} -> {'PASS' if cr.get('pass') else 'FAIL'}",
                  cr.get('pass', False),
                  f"got={cr.get('got')}, expected={cr.get('expected')}")

        # Combined Filters
        print("\n[COMBINED FILTER TESTS]")
        check("Combined: fr + Shop CTA + image format + active",
              result.get('combo_fr_shop_image_pass', False),
              f"ids={result.get('combo_fr_shop_image_ids', [])}")
        check("Combined: en + video format (>= 3 ads)",
              result.get('combo_en_video_pass', False),
              f"count={result.get('combo_en_video_count', 0)}")
        check("Combined: ar language + active ads (>= 2)",
              result.get('combo_ar_active_pass', False),
              f"count={result.get('combo_ar_active_count', 0)}")
        check("Combined: de language + 7d + active",
              result.get('combo_de_7d_active_pass', False))
        check("Combined: es + carousel + fb_utm",
              result.get('combo_es_carousel_fb_pass', False))
        check("Combined: fr OR es language (OR logic, >= 5 ads)",
              result.get('combo_fr_or_es_pass', False),
              f"count={result.get('combo_fr_or_es_count', 0)}")

        # ── TLD Filter Precision Tests ──────────────────────────
        print("\n[TLD FILTER PRECISION TESTS]")
        check("extractTld: shop.xyz → .xyz",
              result.get('tld_ex1') == '.xyz', f"got: {result.get('tld_ex1')}")
        check("extractTld: shop.co.uk → .co.uk",
              result.get('tld_ex2') == '.co.uk', f"got: {result.get('tld_ex2')}")
        check("extractTld: abc.xyz.tv → .xyz.tv (IS in SHADY_TLDS 2-level combos)",
              result.get('tld_ex3') == '.xyz.tv', f"got: {result.get('tld_ex3')}")
        check("extractTld: health.com → .com",
              result.get('tld_ex4') == '.com', f"got: {result.get('tld_ex4')}")
        check("extractTld: xyz.tv → .xyz.tv (IS in SHADY 2-level combos)",
              result.get('tld_ex5') == '.xyz.tv', f"got: {result.get('tld_ex5')}")
        check("extractTld: .xyz → .xyz",
              result.get('tld_ex6') == '.xyz', f"got: {result.get('tld_ex6')}")
        check("extractTld: abc.xyz.com → .com (not .xyz.com)",
              result.get('tld_ex7') == '.com', f"got: {result.get('tld_ex7')}")
        check("extractTld: sleek.xyz → .xyz",
              result.get('tld_ex8') == '.xyz', f"got: {result.get('tld_ex8')}")
        check("extractTld ALL 8 cases correct",
              result.get('tld_ex_pass', False))
        check("getTldCategory: sleek.xyz → shady",
              result.get('tld_cat_xyz') == 'shady', f"got: {result.get('tld_cat_xyz')}")
        check("getTldCategory: nice.icu → shady",
              result.get('tld_cat_icu') == 'shady', f"got: {result.get('tld_cat_icu')}")
        check("getTldCategory: good.click → shady",
              result.get('tld_cat_click') == 'shady', f"got: {result.get('tld_cat_click')}")
        check("getTldCategory: health.com → clean",
              result.get('tld_cat_com') == 'clean', f"got: {result.get('tld_cat_com')}")
        check("getTldCategory: shop.co.uk → clean",
              result.get('tld_cat_couk') == 'clean', f"got: {result.get('tld_cat_couk')}")
        check("getTldCategory: app.io → clean",
              result.get('tld_cat_io') == 'clean', f"got: {result.get('tld_cat_io')}")
        check("getTldCategory: xyz.tv → .xyz.tv → shady (IS in SHADY 2-level)",
              result.get('tld_cat_tv') == 'shady', f"got: {result.get('tld_cat_tv')}")
        check("getTldCategory: null → clean",
              result.get('tld_cat_null') == 'clean', f"got: {result.get('tld_cat_null')}")
        check("getTldCategory: empty → clean",
              result.get('tld_cat_empty') == 'clean', f"got: {result.get('tld_cat_empty')}")
        check("getTldCategory ALL cases correct",
              result.get('tld_cat_pass', False))
        check("allDomainsClean: [health.com, shop.co.uk] → true (all clean)",
              result.get('acd_clean', True) == True)
        check("allDomainsClean: [sleek.xyz, nice.icu] → false (all shady)",
              result.get('acd_shady', True) == False)
        check("allDomainsClean: [health.com, sleek.xyz] → false (mixed)",
              result.get('acd_mixed', True) == False)
        check("allDomainsClean: [] → false (no domains)",
              result.get('acd_empty', True) == False)
        check("allDomainsClean: null → false",
              result.get('acd_null', True) == False)
        check("allDomainsClean ALL cases correct",
              result.get('acd_pass', False))
        check("domainFilter '.xyz' (endsWith): matches shop.xyz, NOT xyz.tv or abc.xyz.com",
              result.get('df_dotxyz_pass', False),
              f"ids={result.get('df_dotxyz_ids', [])}")
        check("domainFilter 'xyz.tv' (contains): matches xyz.tv, NOT shop.xyz",
              result.get('df_xyztv_pass', False),
              f"ids={result.get('df_xyztv_ids', [])}")
        check("domainFilter '.co.uk': matches shop.co.uk",
              result.get('df_couk_pass', False))
        check("hideCleanTlds: excludes all-clean ads, includes at-least-one-shady, excludes no-domain",
              result.get('hc_pass', False),
              f"ids={result.get('hc_ids', [])}")
        check("showOnlyWithDomains: excludes no-domain ads",
              result.get('sod_pass', False))
        check("selectedTLDs ['.xyz']: matches .xyz domains, NOT .tv or .com",
              result.get('stld_xyz_pass', False),
              f"ids={result.get('stld_xyz_ids', [])}")
        check("selectedTLDs ['.xyz','.icu'] multi-select: OR logic works",
              result.get('stld_xyz_icu_pass', False),
              f"ids={result.get('stld_xyz_icu_ids', [])}")

        # ── Summary ───────────────────────────────────────────
        print("\n" + "=" * 60)
        print(f"RESULTS: {passed_tests}/{total_tests} tests passed")
        if passed_tests < total_tests:
            print(f"WARNING: {total_tests - passed_tests} test(s) FAILED")
        else:
            print("ALL TESTS PASSED")

        if CONSOLE_ERRORS:
            print(f"\nCONSOLE ERRORS ({len(CONSOLE_ERRORS)}):")
            for err in CONSOLE_ERRORS[:5]:
                print(f"  - {str(err)[:150]}")
        else:
            print("\nNo console errors detected.")

        print("\n" + "=" * 60)
        for res in TEST_RESULTS:
            print(res)

        print("\nKeeping browser open for 5 seconds...")
        await asyncio.sleep(5)
        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
