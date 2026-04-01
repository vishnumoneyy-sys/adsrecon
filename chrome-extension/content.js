/**
 * ADSRECON Chrome Extension — Content Script
 * Extracts ads from Meta Ad Library DOM efficiently.
 * Zero main-thread blocking, uses requestIdleCallback.
 * Optimized for Facebook's React SPA with infinite scroll.
 */

(function () {
  'use strict';

  // ── Shady domain TLDs used by nutra/crypto scams ─────────────────────
  const SHADY_TLDS = new Set([
    '.space', '.fun', '.info', '.xyz', '.top', '.click', '.link', '.buzz',
    '.icu', '.pw', '.cc', '.club', '.vip', '.pro', '.site', '.website',
    '.work', '.fit', '.shop', '.store', '.online', '.tech', '.gq', '.ml',
    '.cf', '.tk', '.ga', '.gaa', '.bid', '.win', '.date', '.racing',
    '.download', '.stream', '.accountant', '.cricket', '.party', '.science',
    '.faith', '.review', '.loan', '.trade', '.webcam', '.city',
  ]);

  // ── State ──────────────────────────────────────────────────
  let ads = [];
  let observer = null;
  let extracted = new Set();
  let lastScrollHeight = 0;
  let scrollTimer = null;
  let initDone = false;

  // ── Helpers ────────────────────────────────────────────────
  function getText(el) { return el ? el.textContent.trim() : ''; }

  function getDomain(url) {
    if (!url) return '';
    try {
      const hostname = new URL(url).hostname.replace(/^www\./, '');
      const parts = hostname.split('.');
      return parts.length >= 2 ? '.' + parts.slice(-2).join('.') : hostname;
    } catch (_) { return ''; }
  }

  function isShadyDomain(url) {
    const domain = getDomain(url);
    if (!domain) return false;
    const tld = '.' + domain.split('.').pop();
    return SHADY_TLDS.has(tld);
  }

  function hashEl(el, len) {
    return btoa(unescape(encodeURIComponent(el.innerHTML.substring(0, 300)))).substring(0, len || 50);
  }

  // ── Extract ALL unique landing URLs from an element ─────────────────
  function extractAllLandingUrls(el) {
    const urls = [];
    const seen = new Set();
    const links = el.querySelectorAll('a[href]');

    for (const link of links) {
      let href = link.href || link.getAttribute('href') || '';
      if (!href || href === '#' || seen.has(href)) continue;
      seen.add(href);

      try {
        const absHref = href.startsWith('/')
          ? 'https://www.facebook.com' + href
          : href;
        const parsed = new URL(absHref);

        // Decode FB redirect params: u, url, l, q, link, goto, redir, destination
        for (const param of ['u', 'url', 'l', 'q', 'link', 'goto', 'redir', 'destination', 'd', 'e', 'href']) {
          const val = parsed.searchParams.get(param);
          if (val) {
            try { href = decodeURIComponent(val); } catch (_) { href = val; }
            break;
          }
        }

        // Skip FB/Meta internal domains
        if (/^(https?:\/\/)?(www\.)?(facebook|fb|instagram|messenger|whatsapp|threads)\.com?(\/|$)/.test(href)) continue;
        if (!href.startsWith('http')) continue;

        urls.push(href);
      } catch (_) {}
    }
    return [...new Set(urls)];
  }

  // ── Extract ad text ───────────────────────────────────────
  function extractAdText(el) {
    // Method 1: data-ad-preview (most reliable)
    const preview = el.querySelector('[data-ad-preview]');
    if (preview) {
      const text = getText(preview);
      if (text.length > 5) return text;
    }

    // Method 2: elements with explicit "Ad" in aria-label
    const adEls = el.querySelectorAll('[aria-label*="Ad"][aria-label*=" "], [aria-label*="ad"][aria-label*=" "], [aria-label*=" "][aria-label*="Ad"]');
    for (const ael of adEls) {
      const text = getText(ael);
      if (text.length > 20 && text.length < 1000) return text;
    }

    // Method 3: text paragraphs inside the ad card
    const ps = el.querySelectorAll('p[dir="auto"]');
    if (ps.length) {
      const texts = Array.from(ps).map(p => getText(p)).filter(t => t.length > 10);
      if (texts.length) return texts.join(' ').substring(0, 500);
    }

    // Method 4: any substantial text content (fallback)
    const allText = getText(el)
      .replace(/\s+/g, ' ')
      .substring(0, 500);
    return allText.length > 10 ? allText : '';
  }

  // ── Extract page/advertiser name ───────────────────────────
  function extractPageName(el) {
    // Priority 1: strong[dir="auto"] — FB's standard name format
    const strong = el.querySelector('strong[dir="auto"]');
    if (strong) {
      const t = getText(strong);
      if (t.length > 1 && t.length < 200 && t.toLowerCase() !== 'facebook') return t;
    }

    // Priority 2: links to Facebook pages
    const pageLinks = el.querySelectorAll('a[href*="/pages/"], a[href*="/profile.php"], a[href*="facebook.com/"][href*="?__cft__"]');
    for (const link of pageLinks) {
      const t = getText(link);
      if (t.length > 1 && t.length < 200) return t;
    }

    // Priority 3: first meaningful span
    const spans = el.querySelectorAll('span[dir="auto"]');
    for (const span of spans) {
      const t = getText(span);
      if (t.length > 2 && t.length < 200) return t;
    }

    // Priority 4: any link text in the card
    const allLinks = el.querySelectorAll('a[role]');
    for (const link of allLinks) {
      const t = getText(link);
      if (t.length > 2 && t.length < 200 && t.toLowerCase() !== 'link') return t;
    }

    return '';
  }

  // ── Extract CTA ────────────────────────────────────────────
  function extractCTA(el) {
    const cta = el.querySelector('a[role="button"], [aria-label*="Call to Action"], [aria-label*="Learn more"], [aria-label*="Shop now"], [aria-label*="Sign up"]');
    if (cta) {
      const label = cta.getAttribute('aria-label');
      if (label && label.length > 1 && label.length < 100) return label;
      const text = getText(cta);
      if (text.length > 1) return text;
    }
    return '';
  }

  // ── Parse a single ad element ─────────────────────────────
  function parseAd(el) {
    const hash = hashEl(el);
    if (extracted.has(hash)) return null;
    extracted.add(hash);

    const text = extractAdText(el);
    if (!text || text.length < 10) return null;

    const pageName = extractPageName(el);
    if (!pageName || pageName.toLowerCase() === 'facebook') return null;

    const landingUrls = extractAllLandingUrls(el);
    const domains = [...new Set(landingUrls.map(getDomain).filter(Boolean))];
    const isShady = landingUrls.some(u => isShadyDomain(u));

    return {
      id: hash,
      pageName,
      adText: text.substring(0, 500),
      landingUrl: landingUrls[0] || '',
      landingUrls,
      domains,
      isShady,
      cta: extractCTA(el),
      timestamp: Date.now(),
    };
  }

  // ── Facebook-specific card discovery ─────────────────────
  // Facebook renders Ad Library ads in several patterns:
  // Pattern A: div[aria-label] containing the whole ad card (main React render)
  // Pattern B: divs with data-pagelet containing FeedUnit or AdCard
  // Pattern C: nested divs within the library's scrollable container
  // Pattern D: elements with specific text patterns like "Active ad"

  function isLikelyAdCard(el) {
    // Filter out FB chrome elements
    const label = el.getAttribute('aria-label') || '';
    const skipLabels = /^(Menu|Search|Log ?in|Close|Back|Next|Share|Remove|Add|Composer|Post|Comment|React|Notification|Chat|Facebook|Messenger|Watch|Stories|Profile|Settings|Home|Bookmarks|News)/i;
    if (skipLabels.test(label)) return false;
    if (!label || label.length < 10 || label.length > 500) return false;
    // Must have children (actual content)
    if (!el.children.length) return false;
    return true;
  }

  function scanForAds() {
    let found = 0;
    const before = ads.length;

    // ── Strategy 1: labelled divs that look like ad cards ─────
    // These are the primary React-rendered ad containers on Ad Library
    const candidates = document.querySelectorAll('div[aria-label]');
    for (const div of candidates) {
      if (!isLikelyAdCard(div)) continue;

      const text = extractAdText(div);
      const pageName = extractPageName(div);
      if (!text || text.length < 10) continue;
      if (!pageName || pageName.toLowerCase() === 'facebook') continue;

      // Additional check: should have external links (ad cards always do)
      const urls = extractAllLandingUrls(div);
      if (urls.length === 0) continue;

      const hash = hashEl(div);
      if (extracted.has(hash)) continue;
      extracted.add(hash);

      const domains = [...new Set(urls.map(getDomain).filter(Boolean))];
      ads.push({
        id: hash,
        pageName,
        adText: text.substring(0, 500),
        landingUrl: urls[0] || '',
        landingUrls: urls,
        domains,
        isShady: urls.some(u => isShadyDomain(u)),
        cta: extractCTA(div),
        timestamp: Date.now(),
      });
      found++;
    }

    // ── Strategy 2: data-pagelet containers (FB's internal IDs) ─
    const pagelets = document.querySelectorAll('[data-pagelet]');
    for (const p of pagelets) {
      const name = p.getAttribute('data-pagelet') || '';
      if (!/(FeedUnit|AdCard|Library|Card|AdUnit|Ad)/i.test(name)) continue;
      const hash = hashEl(p);
      if (extracted.has(hash)) continue;

      const text = extractAdText(p);
      const pageName = extractPageName(p);
      if (!text || text.length < 10) continue;
      if (!pageName || pageName.toLowerCase() === 'facebook') continue;

      extracted.add(hash);
      const urls = extractAllLandingUrls(p);
      const domains = [...new Set(urls.map(getDomain).filter(Boolean))];
      ads.push({
        id: hash, pageName,
        adText: text.substring(0, 500),
        landingUrl: urls[0] || '',
        landingUrls: urls,
        domains,
        isShady: urls.some(u => isShadyDomain(u)),
        cta: extractCTA(p),
        timestamp: Date.now(),
      });
      found++;
    }

    // ── Strategy 3: structured elements with external links ─────
    // These catch ad cards via their external redirect links
    const externalLinks = document.querySelectorAll(
      'a[href*="l.facebook.com"], a[href*="lm.facebook.com"], a[href*="m.facebook.com"], a[href*="l.instagram.com"]'
    );
    for (const link of externalLinks) {
      // Walk up to find the card container (within ~5 levels)
      let card = link;
      for (let i = 0; i < 6; i++) {
        card = card.parentElement;
        if (!card) break;
        const tag = card.tagName;
        if (tag === 'ARTICLE' || tag === 'SECTION' || tag === 'MAIN') break;
      }
      if (!card) card = link.closest('div');

      if (!card || card === document.body) continue;
      const hash = hashEl(card);
      if (extracted.has(hash)) continue;

      const text = extractAdText(card);
      const pageName = extractPageName(card);
      if (!text || text.length < 10) continue;
      if (!pageName || pageName.toLowerCase() === 'facebook') continue;

      extracted.add(hash);
      const urls = extractAllLandingUrls(card);
      const domains = [...new Set(urls.map(getDomain).filter(Boolean))];
      ads.push({
        id: hash, pageName,
        adText: text.substring(0, 500),
        landingUrl: urls[0] || '',
        landingUrls: urls,
        domains,
        isShady: urls.some(u => isShadyDomain(u)),
        cta: extractCTA(card),
        timestamp: Date.now(),
      });
      found++;
    }

    // ── Deduplicate ───────────────────────────────────────────
    const seenKeys = new Set();
    ads = ads.filter(ad => {
      const key = (ad.pageName || '').toLowerCase() + '|' + (ad.adText || '').substring(0, 40);
      if (seenKeys.has(key)) return false;
      seenKeys.add(key);
      return true;
    });

    return ads.length - before;
  }

  // ── Scroll-triggered re-scan ──────────────────────────────
  // Facebook's infinite scroll adds more ads as you scroll down.
  // We detect new content via scrollHeight changes.
  function setupScrollWatch() {
    const checkScroll = () => {
      const sh = document.documentElement.scrollHeight;
      if (sh !== lastScrollHeight) {
        lastScrollHeight = sh;
        const found = scanForAds();
        if (found > 0) broadcastUpdate();
      }
    };
    window.addEventListener('scroll', () => {
      if (scrollTimer) return;
      scrollTimer = setTimeout(() => {
        scrollTimer = null;
        checkScroll();
      }, 500);
    }, { passive: true });
  }

  // ── MutationObserver ──────────────────────────────────────
  function setupObserver() {
    if (observer) observer.disconnect();

    let debounceTimer = null;
    observer = new MutationObserver(() => {
      if (debounceTimer) return;
      debounceTimer = setTimeout(() => {
        debounceTimer = null;
        const found = scanForAds();
        if (found > 0) broadcastUpdate();
      }, 300);
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  }

  // ── Message Bus ────────────────────────────────────────────
  function broadcastUpdate() {
    chrome.runtime.sendMessage({
      type: 'ADS_UPDATED',
      ads: ads.slice(-200),
      count: ads.length,
    }).catch(() => {});
  }

  // ── Nutra Classifier (popup-replicated here for classify) ──
  const NUTRA_PATTERNS = {
    weight_loss:      /\b(weight loss|lose weight|burn fat|shed pounds|detox|belly fat|slim|burner|keto|crash diet|garcinia|forskolin)\b/i,
    blood_sugar:      /\b(blood sugar|diabetes|lower glucose|carb blocker|insulin|sugar balance|A1C)\b/i,
    prostate:         /\b(prostate|enlarged prostate|prostate health|prostate support|bladder|urinary tract men)\b/i,
    skin_beauty:      /\b(skin cream|anti aging|collagen|wrinkle|acne|fairness|glow|beauty|skin serum|retinol|vitamin C serum)\b/i,
    joint_pain:       /\b(joint pain|arthritis|joint health|glucosamine|chondroitin|mobility|pain relief|inflammation)\b/i,
    energy_stamina:   /\b(energy|boost energy|endurance|stamina|vigor|testosterone|sexual performance)\b/i,
    gut_digestion:    /\b(gut health|probiotic|digestion|IBS|bloat|colon cleanse|apple cider vinegar)\b/i,
    male_enhancement: /\b(male enhancement|pennis|erectile|ED treatment|testosterone boost)\b/i,
    anti_aging:       /\b(anti aging|youthful|reverse aging|wrinkle cream|age defying|longevity)\b/i,
    heart_blood:      /\b(heart health|cholesterol|blood pressure|omega 3|cardio|tribulus)\b/i,
  };

  const NUTRA_KEYWORDS = {
    weight_loss: 'Weight Loss', blood_sugar: 'Blood Sugar', prostate: 'Prostate',
    skin_beauty: 'Skin & Beauty', joint_pain: 'Joint Pain', energy_stamina: 'Energy & Stamina',
    gut_digestion: 'Gut & Digestion', male_enhancement: 'Male Enhancement',
    anti_aging: 'Anti-Aging', heart_blood: 'Heart & Blood',
  };

  window.__adsrecon_classify = function (text) {
    const matched = [];
    let score = 0;
    for (const [cat, pattern] of Object.entries(NUTRA_PATTERNS)) {
      const m = (text.match(pattern) || []).length;
      if (m > 0) { matched.push(cat); score += m * 10; }
    }
    return {
      is_nutra: matched.length > 0,
      categories: matched,
      score: Math.min(100, score),
      label: matched.map(c => NUTRA_KEYWORDS[c]).join(', ') || 'None',
    };
  };

  // ── Message Handler ─────────────────────────────────────────
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    switch (msg.type) {
      case 'GET_ADS':
        sendResponse({ ads: ads.slice(-200), count: ads.length });
        break;
      case 'SEARCH': {
        const q = (msg.keyword || '').toLowerCase();
        const results = q
          ? ads.filter(a => a.pageName.toLowerCase().includes(q) || a.adText.toLowerCase().includes(q))
          : ads.slice(-200);
        sendResponse({ ads: results, count: results.length });
        break;
      }
      case 'CLASSIFY':
        sendResponse(window.__adsrecon_classify(msg.text || ''));
        break;
      case 'PING':
        sendResponse({ ok: true, count: ads.length });
        break;
      case 'NAVIGATE':
        // Navigate the Ad Library URL and trigger re-scan
        const url = new URL(window.location.href);
        if (msg.search !== undefined) {
          if (msg.search) {
            url.searchParams.set('q', msg.search);
          } else {
            url.searchParams.delete('q');
          }
        }
        if (msg.country) {
          url.searchParams.set('country', msg.country);
          url.searchParams.set('is_targeted_country', 'false');
        }
        // Clear extracted set on navigation so we re-crawl
        extracted.clear();
        ads = [];
        window.location.href = url.toString();
        sendResponse({ ok: true });
        break;
    }
    return true;
  });

  // ── Init ────────────────────────────────────────────────────
  function init() {
    if (initDone) return;
    initDone = true;

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', onReady);
    } else {
      requestIdleCallback(onReady, { timeout: 2000 });
    }
  }

  function onReady() {
    requestIdleCallback(() => {
      const found = scanForAds();
      if (found > 0) broadcastUpdate();
      setupObserver();
      setupScrollWatch();
      lastScrollHeight = document.documentElement.scrollHeight;
    }, { timeout: 3000 });
  }

  init();
})();
