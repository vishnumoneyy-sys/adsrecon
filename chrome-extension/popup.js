/**
 * ADSRECON Chrome Extension — Popup Controller
 * Ultra-fast, non-blocking UI. All bugs fixed.
 */

(function () {
  'use strict';

  // ── CTA Button Types (from Facebook Ad Library) ─────────────
  const CTA_TYPES = [
    'Book Now', 'Call Now', 'Chat on WhatsApp', 'Check Availability',
    'Contact Us', 'Donate Now', 'Download', 'Enquire Now', 'Explore More',
    'Get Access', 'Get Directions', 'Get Offer', 'Get Promotions', 'Get Quote',
    'Get Showtimes', 'Get Updates', 'Inquire Now', 'Install App', 'Install Now',
    'Interested', 'Join Group', 'Learn More', 'Like Page', 'Listen Now',
    'No Button', 'Open Link', 'Order Now', 'Play Game', 'Register Now',
    'Remind Me', 'Request Time', 'Save', 'See Menu', 'See More', 'Sell Now',
    'Send Message', 'Send Updates', 'Send WhatsApp Message', 'Shop Now',
    'Sign Up', 'Subscribe', 'Try in Camera', 'Use App', 'Visit Instagram Profile',
    'Visit Profile', 'Watch More', 'Watch Video',
  ];

  // ── Language List ──────────────────────────────────────────
  const LANGUAGES = [
    { code: 'all', label: 'All Languages' },
    { code: 'af', label: 'Afrikaans' }, { code: 'sq', label: 'Albanian' },
    { code: 'am', label: 'Amharic' }, { code: 'ar', label: 'Arabic' },
    { code: 'hy', label: 'Armenian' }, { code: 'az', label: 'Azerbaijani' },
    { code: 'eu', label: 'Basque' }, { code: 'be', label: 'Belarusian' },
    { code: 'bn', label: 'Bengali' }, { code: 'bs', label: 'Bosnian' },
    { code: 'bg', label: 'Bulgarian' }, { code: 'my', label: 'Burmese' },
    { code: 'ca', label: 'Catalan' }, { code: 'zh', label: 'Chinese' },
    { code: 'hr', label: 'Croatian' }, { code: 'cs', label: 'Czech' },
    { code: 'da', label: 'Danish' }, { code: 'nl', label: 'Dutch' },
    { code: 'en', label: 'English' }, { code: 'et', label: 'Estonian' },
    { code: 'fil', label: 'Filipino' }, { code: 'fi', label: 'Finnish' },
    { code: 'fr', label: 'French' }, { code: 'ka', label: 'Georgian' },
    { code: 'de', label: 'German' }, { code: 'el', label: 'Greek' },
    { code: 'gu', label: 'Gujarati' }, { code: 'ha', label: 'Hausa' },
    { code: 'he', label: 'Hebrew' }, { code: 'hi', label: 'Hindi' },
    { code: 'hu', label: 'Hungarian' }, { code: 'id', label: 'Indonesian' },
    { code: 'ga', label: 'Irish' }, { code: 'it', label: 'Italian' },
    { code: 'ja', label: 'Japanese' }, { code: 'jv', label: 'Javanese' },
    { code: 'kn', label: 'Kannada' }, { code: 'kk', label: 'Kazakh' },
    { code: 'km', label: 'Khmer' }, { code: 'ko', label: 'Korean' },
    { code: 'lo', label: 'Lao' }, { code: 'lv', label: 'Latvian' },
    { code: 'lt', label: 'Lithuanian' }, { code: 'mk', label: 'Macedonian' },
    { code: 'ms', label: 'Malay' }, { code: 'ml', label: 'Malayalam' },
    { code: 'mr', label: 'Marathi' }, { code: 'mn', label: 'Mongolian' },
    { code: 'ne', label: 'Nepali' }, { code: 'no', label: 'Norwegian' },
    { code: 'ps', label: 'Pashto' }, { code: 'fa', label: 'Persian' },
    { code: 'pl', label: 'Polish' }, { code: 'pt', label: 'Portuguese' },
    { code: 'pa', label: 'Punjabi' }, { code: 'ro', label: 'Romanian' },
    { code: 'ru', label: 'Russian' }, { code: 'sa', label: 'Sanskrit' },
    { code: 'sr', label: 'Serbian' }, { code: 'st', label: 'Sesotho' },
    { code: 'si', label: 'Sinhala' }, { code: 'sk', label: 'Slovak' },
    { code: 'sl', label: 'Slovenian' }, { code: 'so', label: 'Somali' },
    { code: 'es', label: 'Spanish' }, { code: 'sw', label: 'Swahili' },
    { code: 'sv', label: 'Swedish' }, { code: 'ta', label: 'Tamil' },
    { code: 'te', label: 'Telugu' }, { code: 'th', label: 'Thai' },
    { code: 'tr', label: 'Turkish' }, { code: 'uk', label: 'Ukrainian' },
    { code: 'ur', label: 'Urdu' }, { code: 'uz', label: 'Uzbek' },
    { code: 'vi', label: 'Vietnamese' }, { code: 'xh', label: 'Xhosa' },
    { code: 'yi', label: 'Yiddish' }, { code: 'zu', label: 'Zulu' },
  ];

  // ── State ──────────────────────────────────────────────────
  const state = {
    ads: [],
    filteredAds: [],
    trackedPages: [],
    savedAds: [],
    activeTab: 'search',
    filters: {
      category: '',
      scoreMin: 0,
      nutraOnly: false,
      savedOnly: false,
      selectedTlds: new Set(),
      domainFilter: '',
      showOnlyWithDomains: false,  // "All TLD Ads" mode
      hideCleanTlds: false,         // "Hide standard TLDs" — remove ads where ALL domains are clean
      datePreset: 'all',           // 'all', '7', '14', '30', 'custom'
      dateFrom: null,              // Date object or null
      dateTo: null,                // Date object or null
      adFormat: 'all',             // 'all', 'image', 'video', 'carousel'
      activeOnly: true,            // Only show active ads
      selectedCTAs: new Set(),     // Selected CTA button types
      selectedLanguages: new Set(), // Selected language codes
      utmFilter: '',               // UTM parameter filter text
    },
    connected: false,
    adCount: 0,
  };

  // ── Shady TLDs (non-standard, used by nutra/crypto scams) ──
  // Also includes 2-level shady combos (e.g. .xyz.tv, .xyz.cn) for extractTld accuracy
  const SHADY_TLDS = new Set([
    // Standard 1-level shady TLDs
    '.space', '.fun', '.info', '.xyz', '.top', '.click', '.link', '.buzz',
    '.icu', '.pw', '.cc', '.club', '.vip', '.pro', '.site', '.website',
    '.work', '.fit', '.shop', '.store', '.gq', '.ml',
    '.cf', '.tk', '.ga', '.bid', '.win', '.date', '.racing', '.download',
    '.stream', '.accountant', '.cricket', '.party', '.science', '.faith',
    '.review', '.loan', '.trade', '.webcam', '.country', '.kim',
    // Two-level shady combos: .xyz.{cc}, .top.{cc}, .icu.{cc}, etc.
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

  // ── Standard/clean TLDs (should be hidden when "Hide standard TLDs" is on) ──
  // Includes two-level country codes (e.g. .co.uk, .ac.uk, .co.nz) for accurate TLD extraction
  const CLEAN_TLDS = new Set([
    // Standard 1-level TLDs
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
    // Two-level country codes: .co.{cc}
    '.co.uk', '.co.nz', '.co.jp', '.co.kr', '.co.th', '.co.in',
    '.co.za', '.co.id', '.co.br', '.co.ke', '.co.ao', '.co.mz',
    '.co.bw', '.co.zm', '.co.zw', '.co.tz', '.co.ug',
    '.co.ph', '.co.pk', '.co.gh', '.co.ng',
    // Two-level country codes: .ac.{cc}, .or.{cc}, .ne.{cc}
    '.ac.uk', '.or.jp', '.ne.jp', '.ac.jp', '.co.im', '.ac.im',
    '.co.gg', '.org.gg', '.ac.gg',
    // Two-level gov/mil
    '.gov.uk', '.mod.uk', '.ac.uk', '.gov.au', '.gov.nz', '.gov.cn',
    // Other common two-level domains
    '.com.au', '.net.au', '.org.au', '.edu.au',
    '.co.nz', '.net.nz', '.org.nz', '.ac.nz', '.govt.nz',
    '.com.br', '.net.br', '.org.br', '.edu.br', '.gov.br',
    '.co.in', '.net.in', '.org.in', '.ac.in', '.gov.in',
    '.co.uk', '.org.uk', '.ac.uk',
    '.com.pk', '.net.pk', '.org.pk', '.gov.pk',
    '.co.ke', '.or.ke', '.ac.ke',
    // Domain-like clean TLDs
    '.com', '.org', '.net', '.co', '.uk',
    '.app', '.dev', '.io', '.tech', '.biz', '.info', '.name',
  ]);

  // Determine if a domain's TLD is clean (standard) or shady (non-standard)
  // Uses same 2-part lookup as extractTld for consistency
  function getTldCategory(domain) {
    if (!domain) return 'clean';
    const clean = domain.startsWith('.') ? domain.slice(1) : domain;
    const parts = clean.split('.');
    const last = parts[parts.length - 1];
    if (!last) return 'clean';
    if (parts.length >= 2) {
      const secondLast = parts[parts.length - 2];
      const twoPart = `${secondLast}.${last}`;
      if (CLEAN_TLDS.has(`.${twoPart}`) || SHADY_TLDS.has(`.${twoPart}`)) {
        return SHADY_TLDS.has(`.${twoPart}`) ? 'shady' : 'clean';
      }
    }
    return SHADY_TLDS.has(`.${last}`) ? 'shady' : 'clean';
  }

  // Returns true if ALL domains for an ad are clean TLDs (should be hidden)
  function allDomainsClean(domains) {
    if (!domains || domains.length === 0) return false;
    return domains.every(d => getTldCategory(d) === 'clean');
  }

  // ── Nutra config ───────────────────────────────────────────
  const NUTRA_CATS = {
    weight_loss:      { label: 'Weight Loss',     color: '#ffa94d', bg: 'rgba(255,169,77,0.15)' },
    blood_sugar:     { label: 'Blood Sugar',    color: '#ff6b6b', bg: 'rgba(255,107,107,0.15)' },
    prostate:        { label: 'Prostate',        color: '#9775fa', bg: 'rgba(151,117,250,0.15)' },
    skin_beauty:     { label: 'Skin & Beauty', color: '#ff8cc8', bg: 'rgba(255,140,200,0.15)' },
    joint_pain:      { label: 'Joint Pain',      color: '#74c0fc', bg: 'rgba(116,192,252,0.15)' },
    energy_stamina:  { label: 'Energy',          color: '#ffd43b', bg: 'rgba(255,212,59,0.15)' },
    gut_digestion:   { label: 'Gut Health',     color: '#63e6be', bg: 'rgba(99,230,190,0.15)' },
    male_enhancement:{ label: 'Male Enh.',        color: '#ff6b9d', bg: 'rgba(255,107,157,0.15)' },
    anti_aging:      { label: 'Anti-Aging',     color: '#da77f2', bg: 'rgba(218,119,242,0.15)' },
    heart_blood:     { label: 'Heart Health',   color: '#ff5555', bg: 'rgba(255,85,85,0.15)' },
  };

  // ── DOM helpers ────────────────────────────────────────────
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => document.querySelectorAll(s);

  // ── Dropdown helpers ────────────────────────────────────────
  // Initializes a multi-select dropdown panel with chips.
  // type: 'cta' | 'lang', items: string[], onChange(selected Set): void
  function initDropdown(type, items, onChange) {
    const trigger = $(`#${type}DropdownBtn`);
    const panel = $(`#${type}DropdownPanel`);
    const chipList = $(`#${type}ChipList`);
    const searchInput = $(`#${type}SearchInput`);
    if (!trigger || !panel || !chipList) return;

    // Build chips
    function renderChips(filterText = '') {
      const lower = filterText.toLowerCase();
      const filtered = items.filter(item => item.toLowerCase().includes(lower));
      chipList.innerHTML = filtered.map(item => {
        const active = isItemSelected(type, item) ? ' active' : '';
        return `<button class="chip${active}" data-item="${esc(item)}">${esc(item)}</button>`;
      }).join('');
    }

    // Toggle dropdown
    trigger.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = panel.style.display !== 'none';
      closeAllDropdowns();
      if (!isOpen) {
        panel.style.display = 'block';
        trigger.classList.add('active');
        renderChips();
        if (searchInput) { searchInput.value = ''; searchInput.focus(); }
      }
    });

    // Search filter
    if (searchInput) {
      searchInput.addEventListener('input', (e) => renderChips(e.target.value));
    }

    // Chip click (delegated)
    chipList.addEventListener('click', (e) => {
      const chip = e.target.closest('.chip');
      if (!chip) return;
      const item = chip.dataset.item;
      const selected = getSelectedSet(type);
      if (selected.has(item)) {
        selected.delete(item);
        chip.classList.remove('active');
      } else {
        selected.add(item);
        chip.classList.add('active');
      }
      onChange(selected);
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
      if (!panel.contains(e.target) && !trigger.contains(e.target)) {
        panel.style.display = 'none';
        trigger.classList.remove('active');
      }
    });
  }

  function isItemSelected(type, item) {
    if (type === 'cta') return state.filters.selectedCTAs.has(item);
    if (type === 'lang') {
      // Match by label
      const lang = LANGUAGES.find(l => l.label === item);
      if (lang) return state.filters.selectedLanguages.has(lang.code);
    }
    return false;
  }

  function getSelectedSet(type) {
    if (type === 'cta') return state.filters.selectedCTAs;
    if (type === 'lang') {
      // Return a temp set of labels for lang
      return new Set([...state.filters.selectedLanguages].map(c => {
        const lang = LANGUAGES.find(l => l.code === c);
        return lang ? lang.label : '';
      }).filter(Boolean));
    }
    return new Set();
  }

  function updateDropdownLabel(type, selected, items) {
    const label = $(`#${type}DropdownLabel`);
    if (!label) return;
    const count = selected.size;
    if (count === 0 || count === items.length) {
      label.textContent = type === 'cta' ? 'All CTAs' : 'All Languages';
    } else if (count === 1) {
      label.textContent = [...selected][0];
    } else {
      label.textContent = `${count} selected`;
    }
  }

  function closeAllDropdowns() {
    $$('.dropdown-panel').forEach(p => { p.style.display = 'none'; });
    $$('.dropdown-trigger').forEach(t => t.classList.remove('active'));
  }

  // ── Init ───────────────────────────────────────────────────
  async function init() {
    await Promise.all([
      loadTrackedPages(),
      loadSavedAds(),
      loadSettings(),
      checkConnection(),
    ]);
    bindEvents();
    switchTab('search');
    updateBadge();
  }

  // ── Storage ────────────────────────────────────────────────
  async function loadTrackedPages() {
    const res = await sendBg({ type: 'GET_TRACKED_PAGES' });
    state.trackedPages = res.pages || [];
    renderTrackedPages();
  }

  async function loadSavedAds() {
    const res = await sendBg({ type: 'GET_SAVED_ADS' });
    state.savedAds = res.ads || [];
    renderSavedAds();
    updateBadge();
  }

  async function loadSettings() {
    const res = await sendBg({ type: 'GET_SETTINGS' });
    if (res.settings) {
      const countrySelect = $('#countrySelect');
      if (countrySelect) {
        countrySelect.value = res.settings.defaultCountry || 'US';
      }
      state.filters.category = res.settings.defaultCategory || '';
      // Load persisted filter preferences
      if (res.settings.filterPrefs) {
        const fp = res.settings.filterPrefs;
        if (fp.selectedCTAs) state.filters.selectedCTAs = new Set(fp.selectedCTAs);
        if (fp.selectedLanguages) state.filters.selectedLanguages = new Set(fp.selectedLanguages);
        if (fp.utmFilter !== undefined) state.filters.utmFilter = fp.utmFilter;
        if (fp.datePreset) state.filters.datePreset = fp.datePreset;
        if (fp.adFormat) state.filters.adFormat = fp.adFormat;
        if (fp.activeOnly !== undefined) state.filters.activeOnly = fp.activeOnly;
        if (fp.dateFrom) state.filters.dateFrom = new Date(fp.dateFrom);
        if (fp.dateTo) state.filters.dateTo = new Date(fp.dateTo);
      }
    }
  }

  async function saveFilterPrefs() {
    const prefs = {
      selectedCTAs: [...state.filters.selectedCTAs],
      selectedLanguages: [...state.filters.selectedLanguages],
      utmFilter: state.filters.utmFilter,
      datePreset: state.filters.datePreset,
      adFormat: state.filters.adFormat,
      activeOnly: state.filters.activeOnly,
      dateFrom: state.filters.dateFrom ? state.filters.dateFrom.toISOString() : null,
      dateTo: state.filters.dateTo ? state.filters.dateTo.toISOString() : null,
    };
    await sendBg({ type: 'SAVE_FILTER_PREFS', prefs });
  }

  async function checkConnection() {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab?.id && tab?.url?.includes('facebook.com/ads/library')) {
        const res = await chrome.tabs.sendMessage(tab.id, { type: 'PING' });
        state.connected = true;
        state.adCount = res?.count || 0;
        updateBadge();
        return;
      }
    } catch (_) {}
    const res = await sendBg({ type: 'GET_AD_COUNT' });
    state.connected = res.connected || false;
    state.adCount = res.count || 0;
    const loginWarning = $('#loginWarning');
    if (!state.connected && loginWarning) {
      loginWarning.style.display = 'flex';
    }
    updateBadge();
  }

  // ── Message helpers ─────────────────────────────────────────
  function sendBg(msg) {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage(msg, (res) => resolve(res || {}));
    });
  }

  async function getAdsFromPage() {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab?.id) {
        const res = await chrome.tabs.sendMessage(tab.id, { type: 'GET_ADS' });
        if (res?.ads) return res;
      }
    } catch (_) {}
    return await sendBg({ type: 'GET_ADS' });
  }

  // ── Events ────────────────────────────────────────────────
  function bindEvents() {
    // Tabs
    $$('.tab').forEach(tab => {
      tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    // Search
    const doSearchBtn = $('#doSearch');
    if (doSearchBtn) doSearchBtn.addEventListener('click', doSearch);
    const searchInput = $('#searchInput');
    if (searchInput) searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') doSearch();
    });

    // Country change — auto-select default language for country if no languages selected yet
    const countrySelect = $('#countrySelect');
    if (countrySelect) {
      countrySelect.addEventListener('change', () => {
        const newCountry = countrySelect.value;
        sendBg({ type: 'SAVE_SETTINGS', settings: { defaultCountry: newCountry } });
        // Auto-select default language for this country if no languages selected
        if (state.filters.selectedLanguages.size === 0) {
          const defaultLang = GEO_DEFAULT_LANG[newCountry];
          if (defaultLang && defaultLang !== 'en') {
            state.filters.selectedLanguages.add(defaultLang);
            const lang = LANGUAGES.find(l => l.code === defaultLang);
            if (lang) {
              updateDropdownLabel('lang', new Set([lang.label]), LANGUAGES.map(l => l.label));
              $$('#langChipList .chip').forEach(c => {
                if (c.dataset.item === lang.label) c.classList.add('active');
              });
            }
            saveFilterPrefs();
          }
        }
        doCountrySearch(newCountry);
      });
    }

    // Ad type change — auto-search when ad type changes
    const adTypeSelect = $('#adTypeSelect');
    if (adTypeSelect) {
      adTypeSelect.addEventListener('change', () => {
        const keyword = ($('#searchInput')?.value || '').trim();
        const country = ($('#countrySelect')?.value) || 'US';
        const adType = ($('#adTypeSelect')?.value) || 'all';
        navigateToSearch(keyword, country, adType);
      });
    }

    // Search type change — toggle domain input visibility
    const searchTypeSelect = $('#searchTypeSelect');
    if (searchTypeSelect) {
      searchTypeSelect.addEventListener('change', () => {
        const mode = searchTypeSelect.value;
        const landingGroup = $('#landingPageGroup');
        if (landingGroup) {
          landingGroup.style.display = (mode === 'domain' || mode === 'tldonly') ? 'flex' : 'none';
        }
        // Clear domain filter when leaving domain modes
        if (mode === 'keyword' || mode === 'alltld') {
          state.filters.domainFilter = '';
          state.filters.showOnlyWithDomains = false;
          applyFilters();
        }
        if (mode === 'domain' || mode === 'tldonly') {
          const landingInput = $('#landingPageInput');
          if (landingInput) landingInput.focus();
        }
      });
    }

    // Landing page search button
    const doLandingBtn = $('#doLandingSearch');
    if (doLandingBtn) doLandingBtn.addEventListener('click', doLandingSearch);

    // Landing page input Enter key
    const landingInput = $('#landingPageInput');
    if (landingInput) {
      landingInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') doLandingSearch();
      });
    }

    // Category chips
    $$('.chip[data-cat]').forEach(chip => {
      chip.addEventListener('click', () => {
        const cat = chip.dataset.cat;
        if (state.filters.category === cat) {
          state.filters.category = '';
          chip.classList.remove('active');
        } else {
          $$('.chip').forEach(c => c.classList.remove('active'));
          chip.classList.add('active');
          state.filters.category = cat;
        }
        applyFilters();
      });
    });

    // Clear category filter
    const clearCatBtn = $('#clearCatFilter');
    if (clearCatBtn) {
      clearCatBtn.addEventListener('click', () => {
        state.filters.category = '';
        $$('.chip').forEach(c => c.classList.remove('active'));
        applyFilters();
      });
    }

    // Score slider
    const scoreRange = $('#scoreRange');
    const scoreVal = $('#scoreVal');
    if (scoreRange) {
      scoreRange.addEventListener('input', (e) => {
        state.filters.scoreMin = parseInt(e.target.value) || 0;
        if (scoreVal) scoreVal.textContent = state.filters.scoreMin;
        applyFilters();
      });
    }

    // Checkboxes
    const nutraOnly = $('#nutraOnly');
    if (nutraOnly) nutraOnly.addEventListener('change', (e) => {
      state.filters.nutraOnly = !!e.target.checked;
      applyFilters();
    });
    const savedOnly = $('#savedOnly');
    if (savedOnly) savedOnly.addEventListener('change', (e) => {
      state.filters.savedOnly = !!e.target.checked;
      applyFilters();
    });

    // Shady domain filter
    // Hide standard TLDs toggle
    const hideClean = $('#hideClean');
    if (hideClean) hideClean.addEventListener('change', (e) => {
      state.filters.hideCleanTlds = !!e.target.checked;
      applyFilters();
    });

    // Date preset buttons
    $$('.date-preset').forEach(btn => {
      btn.addEventListener('click', () => {
        $$('.date-preset').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const preset = btn.dataset.preset;
        state.filters.datePreset = preset;
        const customRow = $('#dateCustomRow');
        if (customRow) {
          customRow.style.display = preset === 'custom' ? 'flex' : 'none';
        }
        if (preset !== 'custom') {
          state.filters.dateFrom = null;
          state.filters.dateTo = null;
        }
        saveFilterPrefs();
        applyFilters();
      });
    });

    // Custom date inputs
    const dateFrom = $('#dateFrom');
    if (dateFrom) dateFrom.addEventListener('change', (e) => {
      state.filters.dateFrom = e.target.value ? new Date(e.target.value) : null;
      saveFilterPrefs();
      applyFilters();
    });
    const dateTo = $('#dateTo');
    if (dateTo) dateTo.addEventListener('change', (e) => {
      state.filters.dateTo = e.target.value ? new Date(e.target.value + 'T23:59:59') : null;
      saveFilterPrefs();
      applyFilters();
    });

    // Clear date filter
    const clearDateBtn = $('#clearDateBtn');
    if (clearDateBtn) {
      clearDateBtn.addEventListener('click', () => {
        state.filters.datePreset = 'all';
        state.filters.dateFrom = null;
        state.filters.dateTo = null;
        $$('.date-preset').forEach(b => b.classList.remove('active'));
        $$('.date-preset[data-preset="all"]').forEach(b => b.classList.add('active'));
        const customRow = $('#dateCustomRow');
        if (customRow) customRow.style.display = 'none';
        const fromEl = $('#dateFrom');
        const toEl = $('#dateTo');
        if (fromEl) fromEl.value = '';
        if (toEl) toEl.value = '';
        saveFilterPrefs();
        applyFilters();
      });
    }

    // Ad format filter
    const formatSelect = $('#formatSelect');
    if (formatSelect) formatSelect.addEventListener('change', (e) => {
      state.filters.adFormat = e.target.value;
      saveFilterPrefs();
      applyFilters();
    });

    // Active only filter
    const activeOnly = $('#activeOnly');
    if (activeOnly) activeOnly.addEventListener('change', (e) => {
      state.filters.activeOnly = !!e.target.checked;
      saveFilterPrefs();
      applyFilters();
    });

    // ── CTA Dropdown ─────────────────────────────────────────
    initDropdown('cta', CTA_TYPES, (selected) => {
      state.filters.selectedCTAs = selected;
      updateDropdownLabel('cta', selected, CTA_TYPES);
      saveFilterPrefs();
      applyFilters();
    });

    // ── Language Dropdown ──────────────────────────────────
    initDropdown('lang', LANGUAGES.map(l => l.label), (selected) => {
      // Convert labels back to codes
      const selectedCodes = new Set();
      for (const label of selected) {
        const lang = LANGUAGES.find(l => l.label === label);
        if (lang && lang.code !== 'all') selectedCodes.add(lang.code);
      }
      state.filters.selectedLanguages = selectedCodes;
      updateDropdownLabel('lang', selected, LANGUAGES.map(l => l.label));
      saveFilterPrefs();
      applyFilters();
    });

    // Restore dropdown UIs from persisted state
    if (state.filters.selectedCTAs.size > 0) {
      const labels = [...state.filters.selectedCTAs];
      updateDropdownLabel('cta', new Set(labels), CTA_TYPES);
    }
    if (state.filters.selectedLanguages.size > 0) {
      const labels = [...state.filters.selectedLanguages].map(c => {
        const lang = LANGUAGES.find(l => l.code === c);
        return lang ? lang.label : c;
      }).filter(Boolean);
      updateDropdownLabel('lang', new Set(labels), LANGUAGES.map(l => l.label));
    }

    // UTM filter
    const utmInput = $('#utmInput');
    if (utmInput) {
      utmInput.value = state.filters.utmFilter || '';
      utmInput.addEventListener('input', (e) => {
        state.filters.utmFilter = e.target.value.trim();
        saveFilterPrefs();
        applyFilters();
      });
    }

    // Clear UTM
    const clearUtmBtn = $('#clearUtmBtn');
    if (clearUtmBtn) {
      clearUtmBtn.addEventListener('click', () => {
        state.filters.utmFilter = '';
        const el = $('#utmInput');
        if (el) el.value = '';
        saveFilterPrefs();
        applyFilters();
      });
    }

    // Clear CTA
    const clearCtaBtn = $('#clearCtaBtn');
    if (clearCtaBtn) {
      clearCtaBtn.addEventListener('click', () => {
        state.filters.selectedCTAs.clear();
        updateDropdownLabel('cta', new Set(), CTA_TYPES);
        $$('#ctaChipList .chip').forEach(c => c.classList.remove('active'));
        saveFilterPrefs();
        applyFilters();
      });
    }

    // Clear Language
    const clearLangBtn = $('#clearLangBtn');
    if (clearLangBtn) {
      clearLangBtn.addEventListener('click', () => {
        state.filters.selectedLanguages.clear();
        updateDropdownLabel('lang', new Set(), LANGUAGES.map(l => l.label));
        $$('#langChipList .chip').forEach(c => c.classList.remove('active'));
        saveFilterPrefs();
        applyFilters();
      });
    }

    // Restore UI state from persisted prefs
    // Date presets
    const preset = state.filters.datePreset;
    $$('.date-preset').forEach(b => b.classList.remove('active'));
    const presetBtn = $(`.date-preset[data-preset="${preset}"]`);
    if (presetBtn) presetBtn.classList.add('active');
    const customRow = $('#dateCustomRow');
    if (customRow) customRow.style.display = preset === 'custom' ? 'flex' : 'none';
    if (state.filters.dateFrom) {
      const fromEl = $('#dateFrom');
      if (fromEl) fromEl.value = state.filters.dateFrom.toISOString().split('T')[0];
    }
    if (state.filters.dateTo) {
      const toEl = $('#dateTo');
      if (toEl) toEl.value = state.filters.dateTo.toISOString().split('T')[0];
    }
    // Format
    const formatSel = $('#formatSelect');
    if (formatSel) formatSel.value = state.filters.adFormat;
    // Active only
    const activeCb = $('#activeOnly');
    if (activeCb) activeCb.checked = state.filters.activeOnly;

    // Clear domain filters
    const clearDomainBtn = $('#clearDomainBtn');
    if (clearDomainBtn) {
      clearDomainBtn.addEventListener('click', () => {
        state.filters.selectedTlds.clear();
        state.filters.domainFilter = '';
        state.filters.showOnlyWithDomains = false;
        state.filters.hideCleanTlds = false;
        const cb = $('#hideClean');
        if (cb) cb.checked = false;
        $$('.tld-chip').forEach(c => c.classList.remove('active'));
        applyFilters();
      });
    }

    // Open Ad Library
    const openLibrary = $('#openLibrary');
    if (openLibrary) openLibrary.addEventListener('click', () => {
      chrome.tabs.create({ url: 'https://www.facebook.com/ads/library/' });
    });

    // Refresh — force rescan from content script
    const refreshBtn = $('#refreshBtn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', async () => {
        refreshBtn.disabled = true;
        try {
          const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
          if (tab?.id) {
            try { await chrome.tabs.sendMessage(tab.id, { type: 'RESCAN' }); } catch (_) {}
          }
          await delay(1500);
          const res = await getAdsFromPage();
          state.ads = res.ads || [];
          state.adCount = state.ads.length;
          renderDomainStats();
          applyFilters();
          toast(`Scanned: ${state.ads.length} ads`);
        } finally {
          refreshBtn.disabled = false;
        }
      });
    }

    // Manual Scan button — progressive batch scanning to catch infinite-scroll-loaded ads
    const scanBtn = $('#scanBtn');
    if (scanBtn) {
      scanBtn.addEventListener('click', async () => {
        scanBtn.disabled = true;
        scanBtn.textContent = '...';
        try {
          const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
          const maxPasses = 5;
          const batchCounts = [];
          let prevTotal = 0;

          // Progressive scan: rescan multiple times, updating results after each batch
          for (let pass = 1; pass <= maxPasses; pass++) {
            scanBtn.textContent = `Batch ${pass}...`;
            if (tab?.id) {
              try { await chrome.tabs.sendMessage(tab.id, { type: 'RESCAN' }); } catch (_) {}
            }
            await delay(2000);

            // Update after each batch to show live progress
            const res = await getAdsFromPage();
            state.ads = res.ads || [];
            state.adCount = state.ads.length;
            const newAds = state.ads.length - prevTotal;
            prevTotal = state.ads.length;
            batchCounts.push({ pass, total: state.ads.length, new: newAds });

            renderDomainStats();
            applyFilters();

            // Early stop if no new ads found in this batch
            if (newAds === 0 && pass >= 3) break;
          }

          const df = state.filters.domainFilter;
          const withDomains = state.ads.filter(a => (a.domains || []).length > 0).length;
          const batches = batchCounts.length;
          const lastBatch = batchCounts[batches - 1];

          if (df) {
            toast(`${state.filteredAds.length}/${state.ads.length} match "${df}" | ${withDomains} domains | ${batches} batches`);
          } else if (state.filters.showOnlyWithDomains) {
            toast(`${state.filteredAds.length} ads w/ domains | ${withDomains} domains | ${batches} batches`);
          } else {
            toast(`${state.ads.length} ads scanned | ${withDomains} domains | ${batches} batches`);
          }

          // Update debug info with batch breakdown
          const debugInfo = $('#debugInfo');
          if (debugInfo) {
            const batchSummary = batchCounts.map(b =>
              `B${b.pass}:${b.total}${b.new > 0 ? `(+${b.new})` : ''}`
            ).join(' ');
            debugInfo.textContent = `[${df || 'all'}] ${batchSummary}`;
            debugInfo.style.display = 'inline';
          }
        } finally {
          scanBtn.disabled = false;
          scanBtn.textContent = '\u21bb Scan';
        }
      });
    }

    // Settings — show extension info toast
    const settingsBtn = $('#settingsBtn');
    if (settingsBtn) {
      settingsBtn.addEventListener('click', () => {
        toast('ADSRECON v1.0.0 — Meta Ad Intelligence');
      });
    }

    // Track page
    const addPageBtn = $('#addPageBtn');
    if (addPageBtn) addPageBtn.addEventListener('click', addTrackedPage);
    const newPageInput = $('#newPageInput');
    if (newPageInput) newPageInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') addTrackedPage();
    });

    // Saved actions
    const exportSavedBtn = $('#exportSavedBtn');
    if (exportSavedBtn) exportSavedBtn.addEventListener('click', exportSaved);
    const clearSavedBtn = $('#clearSavedBtn');
    if (clearSavedBtn) {
      clearSavedBtn.addEventListener('click', async () => {
        if (!confirm('Clear all saved ads?')) return;
        await sendBg({ type: 'CLEAR_SAVED_ADS' });
        state.savedAds = [];
        renderSavedAds();
        updateBadge();
        toast('Cleared');
      });
    }

    // Modal
    const closeModal = $('#closeModal');
    if (closeModal) closeModal.addEventListener('click', closeAdModal);
    const adModal = $('#adModal');
    if (adModal) {
      adModal.addEventListener('click', (e) => {
        if (e.target === adModal) closeAdModal();
      });
    }

    // Export
    const exportBtn = $('#exportBtn');
    if (exportBtn) exportBtn.addEventListener('click', exportFiltered);

    // Delegated event handling for dynamically rendered content
    // (tracked items, ad items, TLD chips — all created by innerHTML)
    document.addEventListener('click', handleDelegatedClick);
  }

  // ── Delegated click handler for dynamically rendered HTML ─────
  // This avoids the need for innerHTML onclick attributes (XSS safe)
  // Note: visit-link uses onclick="event.stopPropagation()" in the <a> tag itself
  // (inline onclick is acceptable here since URL is pre-escaped by esc())
  function handleDelegatedClick(e) {
    const target = e.target;

    // Tracked page: remove
    const removeBtn = target.closest('[data-action="remove-page"]');
    if (removeBtn) {
      const id = parseInt(removeBtn.dataset.id, 10);
      if (!isNaN(id)) removeTrackedPage(id);
      return;
    }

    // Tracked page: search
    const searchBtn = target.closest('[data-action="search-page"]');
    if (searchBtn) {
      const name = searchBtn.dataset.name || '';
      if (name) searchTrackedPage(name);
      return;
    }

    // TLD chip click — extract the TLD and filter to all ads with that TLD
    const tldChip = target.closest('.tld-chip');
    if (tldChip && tldChip.dataset.tld) {
      const domain = tldChip.dataset.tld;
      // Extract TLD: "shop.xyz" → ".xyz", ".xyz" → ".xyz"
      const tld = domain.startsWith('.')
        ? domain
        : (() => {
            const parts = domain.split('.');
            return parts.length >= 2 ? '.' + parts.slice(-2).join('.') : domain;
          })();
      if (state.filters.selectedTlds.has(tld)) {
        state.filters.selectedTlds.delete(tld);
        tldChip.classList.remove('active');
      } else {
        state.filters.selectedTlds.add(tld);
        tldChip.classList.add('active');
      }
      applyFilters();
      return;
    }

    // Ad item click (but not button clicks)
    const adItem = target.closest('.ad-item');
    if (adItem && !target.closest('button') && !target.closest('a')) {
      const adId = adItem.dataset.id;
      const tab = state.activeTab === 'saved' ? 'saved' : 'search';
      const adList = tab === 'saved' ? state.savedAds : state.filteredAds;
      const ad = adList.find(a => a.id === adId);
      if (ad) openAdModal(ad);
      return;
    }

    // Save button click
    const saveBtn = target.closest('.save-btn');
    if (saveBtn) {
      e.stopPropagation();
      const adId = saveBtn.dataset.id;
      // Find ad in both filtered and saved lists
      let ad = state.filteredAds.find(a => a.id === adId);
      if (!ad) ad = state.savedAds.find(a => a.id === adId);
      if (ad) toggleSaveAd(ad, saveBtn);
      return;
    }
  }

  // ── Tab Switching ───────────────────────────────────────────
  function switchTab(tab) {
    state.activeTab = tab;
    $$('.tab').forEach(t => {
      t.classList.toggle('active', t.dataset.tab === tab);
    });
    $$('.tab-content').forEach(c => {
      c.classList.toggle('active', c.id === `tab-${tab}`);
    });

    if (tab === 'search' && state.connected) {
      loadAdsFromPage();
    }
  }

  // ── Load ads from content script ───────────────────────────
  async function loadAdsFromPage() {
    const res = await getAdsFromPage();
    state.ads = res.ads || [];
    state.adCount = state.ads.length;
    renderDomainStats();
    applyFilters();
  }

  // ── Core navigation helper ──────────────────────────────────
  async function navigateToSearch(keyword, country, adType) {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    const activeTab = tabs[0];

    const targetUrl = new URL('https://www.facebook.com/ads/library/');
    targetUrl.searchParams.set('q', keyword || 'all');
    targetUrl.searchParams.set('country', country);
    targetUrl.searchParams.set('active_status', state.filters.activeOnly ? 'active' : 'all');
    // Date range: use log_time for preset days
    const preset = state.filters.datePreset;
    if (preset !== 'all' && preset !== 'custom') {
      targetUrl.searchParams.set('log_time', preset);
    }
    // Language filter — Facebook supports ?languages=code[,code]
    if (state.filters.selectedLanguages.size > 0) {
      targetUrl.searchParams.set('languages', [...state.filters.selectedLanguages].join(','));
    }
    if (adType === 'political_and_issue_ads') {
      targetUrl.searchParams.set('ad_type', 'political_and_issue_ads');
    }
    // Domain/TLD filtering is done client-side via state.filters.domainFilter
    // Facebook gets the keyword; we filter ads after scanning

    if (activeTab?.url?.includes('facebook.com/ads/library')) {
      const tabId = activeTab.id;
      const loadPromise = new Promise((resolve) => {
        const handler = (updatedTabId, changeInfo) => {
          if (updatedTabId === tabId && changeInfo.status === 'complete') {
            chrome.tabs.onUpdated.removeListener(handler);
            clearTimeout(timeout);
            resolve();
          }
        };
        chrome.tabs.onUpdated.addListener(handler);
        const timeout = setTimeout(resolve, 5000);
      });
      chrome.tabs.update(tabId, { url: targetUrl.toString() });
      toast('Searching...');
      await loadPromise;
      await delay(4000);
      await rescanAndApply();
    } else {
      chrome.tabs.create({ url: targetUrl.toString() });
      toast('Opening Ad Library...');
    }
  }

  // ── Search ─────────────────────────────────────────────────
  async function doSearch() {
    const keyword = ($('#searchInput')?.value || '').trim();
    const country = ($('#countrySelect')?.value) || 'US';
    const adType = ($('#adTypeSelect')?.value) || 'all';
    const mode = ($('#searchTypeSelect')?.value) || 'keyword';
    if (mode === 'keyword') {
      state.filters.domainFilter = '';
      state.filters.showOnlyWithDomains = false;
    }
    await navigateToSearch(keyword, country, adType);
  }

  // ── Landing page domain search ────────────────────────────
  async function doLandingSearch() {
    const domain = ($('#landingPageInput')?.value || '').trim();
    const country = ($('#countrySelect')?.value) || 'US';
    const adType = ($('#adTypeSelect')?.value) || 'all';
    const keyword = ($('#searchInput')?.value || '').trim();

    const mode = ($('#searchTypeSelect')?.value) || 'keyword';

    if (mode === 'alltld') {
      // "All TLD Ads" — show only ads with detected landing page domains
      state.filters.domainFilter = '';
      state.filters.showOnlyWithDomains = true;
      toast(`Searching all ads with landing page domains...`);
      await navigateToSearch(keyword, country, adType);
      return;
    }

    if (mode === 'tldonly') {
      // "Country + TLD Only" — no keyword, filter by TLD only
      if (!domain) { toast('Enter a TLD first (e.g. .xyz)'); return; }
      const hadDot = domain.startsWith('.');
      const cleanDomain = (hadDot ? domain.slice(1) : domain).trim();
      if (!cleanDomain) { toast('Enter a valid TLD'); return; }
      const withDot = '.' + cleanDomain;
      state.filters.domainFilter = withDot;
      state.filters.showOnlyWithDomains = false;
      toast(`Scanning all ads in ${country} for .${cleanDomain} domains...`);
      await navigateToSearch(cleanDomain, country, adType);
      return;
    }

    // mode === 'domain'
    if (!domain) { toast('Enter a domain or TLD first'); return; }

    // Strip leading dot for TLD vs full domain detection
    const hadDot = domain.startsWith('.');
    const cleanDomain = (hadDot ? domain.slice(1) : domain).trim();
    if (!cleanDomain) { toast('Enter a valid domain'); return; }
    const withDot = hadDot ? '.' + cleanDomain : cleanDomain;

    // Store domain filter for client-side filtering
    state.filters.domainFilter = withDot;
    state.filters.showOnlyWithDomains = false;

    if (hadDot) {
      // User typed a TLD like .xyz — search keyword + filter by TLD
      toast(`Searching "${keyword || cleanDomain}" ads with .${cleanDomain} domains...`);
      await navigateToSearch(keyword || cleanDomain, country, adType);
    } else {
      // User typed a full domain like shop.xyz — use Facebook's native
      // search_type=landing_page which returns ads pointing to that domain
      toast(`Finding ads landing on ${cleanDomain}...`);
      await navigateToLandingPageSearch(cleanDomain, country, adType);
    }
  }

  // ── Native landing page search (Facebook's built-in filter) ─────────
  async function navigateToLandingPageSearch(domain, country, adType) {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    const activeTab = tabs[0];

    const targetUrl = new URL('https://www.facebook.com/ads/library/');
    targetUrl.searchParams.set('search_type', 'landing_page');
    targetUrl.searchParams.set('q', domain);
    targetUrl.searchParams.set('country', country);
    targetUrl.searchParams.set('active_status', state.filters.activeOnly ? 'active' : 'all');
    // Date range: use log_time for preset days
    const preset = state.filters.datePreset;
    if (preset !== 'all' && preset !== 'custom') {
      targetUrl.searchParams.set('log_time', preset);
    }
    // Language filter
    if (state.filters.selectedLanguages.size > 0) {
      targetUrl.searchParams.set('languages', [...state.filters.selectedLanguages].join(','));
    }
    if (adType === 'political_and_issue_ads') {
      targetUrl.searchParams.set('ad_type', 'political_and_issue_ads');
    }

    if (activeTab?.url?.includes('facebook.com/ads/library')) {
      const tabId = activeTab.id;
      const loadPromise = new Promise((resolve) => {
        const handler = (updatedTabId, changeInfo) => {
          if (updatedTabId === tabId && changeInfo.status === 'complete') {
            chrome.tabs.onUpdated.removeListener(handler);
            clearTimeout(timeout);
            resolve();
          }
        };
        chrome.tabs.onUpdated.addListener(handler);
        const timeout = setTimeout(resolve, 6000);
      });
      chrome.tabs.update(tabId, { url: targetUrl.toString() });
      toast('Searching...');
      await loadPromise;
      await delay(4000);
      await rescanAndApply();
    } else {
      chrome.tabs.create({ url: targetUrl.toString() });
      toast('Opening Ad Library...');
    }
  }

  // ── Reusable rescan + apply helper ─────────────────────────
  async function rescanAndApply() {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab?.id) {
      try { await chrome.tabs.sendMessage(tab.id, { type: 'RESCAN' }); } catch (_) {}
    }
    await delay(1000);
    const res = await getAdsFromPage();
    state.ads = res.ads || [];
    state.adCount = state.ads.length;
    const withDomains = state.ads.filter(a => (a.domains || []).length > 0).length;
    renderDomainStats();
    applyFilters();
    const df = state.filters.domainFilter;
    const filtered = state.filteredAds.length;
    const debugInfo = $('#debugInfo');
    if (debugInfo) {
      debugInfo.textContent = df
        ? `${filtered} of ${state.ads.length} match "${df}" | ${withDomains} ads have domains`
        : `${state.ads.length} ads | ${withDomains} have domains`;
      debugInfo.style.display = 'inline';
    }
    if (filtered > 0) {
      const mode = $('#searchTypeSelect')?.value;
      if (mode === 'alltld') {
        toast(`Found ${filtered} ads with landing domains`);
      } else {
        toast(`Found ${filtered} ads`);
      }
    } else if (state.ads.length > 0 && withDomains === 0) {
      toast(`Scanned ${state.ads.length} ads — domain extraction failed. Try scrolling the page first.`);
    } else {
      toast(`Scanned ${state.ads.length} ads — none match filter`);
    }
  }

  // ── Country change (auto-triggered) ───────────────────────
  async function doCountrySearch(newCountry) {
    const keyword = ($('#searchInput')?.value || '').trim();
    const adType = ($('#adTypeSelect')?.value) || 'all';
    // Ensure political/issue is never auto-selected — default to 'all'
    const safeAdType = adType === 'political_and_issue_ads' ? 'all' : adType;
    await navigateToSearch(keyword, newCountry, safeAdType);
  }

  // ── Filters ────────────────────────────────────────────────
  function applyFilters() {
    let ads = [...state.ads];

    // 1. Category chip filter
    if (state.filters.category) {
      ads = ads.filter(ad => {
        const info = window.__popup_classify(ad.adText || '');
        return info.categories?.includes(state.filters.category);
      });
    }

    // 2. Nutra only
    if (state.filters.nutraOnly) {
      ads = ads.filter(ad => {
        const info = window.__popup_classify(ad.adText || '');
        return info.is_nutra;
      });
    }

    // 3. Score minimum
    if (state.filters.scoreMin > 0) {
      ads = ads.filter(ad => {
        const info = window.__popup_classify(ad.adText || '');
        return info.score >= state.filters.scoreMin;
      });
    }

    // 4. Saved only
    if (state.filters.savedOnly) {
      const savedIds = new Set(state.savedAds.map(a => a.id));
      ads = ads.filter(ad => savedIds.has(ad.id));
    }

    // 5. Typed TLD/domain filter — e.g. ".xyz" or "shop.xyz"
    if (state.filters.domainFilter) {
      const raw = state.filters.domainFilter.trim().toLowerCase();
      if (raw) {
        const isTld = raw.startsWith('.');
        ads = ads.filter(ad => {
          const domains = ad.domains || [];
          return domains.some(d => {
            const dd = d.toLowerCase();
            if (isTld) {
              // ".xyz" — domain must END with exactly .xyz
              return dd.endsWith(raw);
            } else {
              // "shop.xyz" — domain must CONTAIN the string
              return dd.includes(raw);
            }
          });
        });
      }
    }

    // 6. Selected TLD chips — filter to specific TLD(s)
    if (state.filters.selectedTlds.size > 0) {
      ads = ads.filter(ad => {
        const domains = ad.domains || [];
        return domains.some(d => {
          const tld = extractTld(d);
          return state.filters.selectedTlds.has(tld);
        });
      });
    }

    // 7. Hide standard TLDs — only keep ads that have at least ONE shady TLD domain
    // (removes ads where ALL domains are standard/clean TLDs or have no domains)
    if (state.filters.hideCleanTlds) {
      ads = ads.filter(ad => {
        const domains = ad.domains || [];
        // Must have at least one domain AND that domain must be shady
        return domains.length > 0 && domains.some(d => getTldCategory(d) === 'shady');
      });
    }

    // 8. All TLD Ads mode — only show ads that have at least one detected domain
    if (state.filters.showOnlyWithDomains) {
      ads = ads.filter(ad => (ad.domains || []).length > 0);
    }

    // 9. Active only — filter out deactivated ads
    if (state.filters.activeOnly) {
      ads = ads.filter(ad => ad.adActive !== false);
    }

    // 10. Date range filter
    const preset = state.filters.datePreset;
    if (preset === 'custom' || (preset !== 'all')) {
      const now = Date.now();
      let minTs, maxTs;
      if (preset === 'custom') {
        minTs = state.filters.dateFrom ? state.filters.dateFrom.getTime() : 0;
        maxTs = state.filters.dateTo ? state.filters.dateTo.getTime() : now;
      } else {
        const days = parseInt(preset, 10);
        minTs = now - days * 24 * 60 * 60 * 1000;
        maxTs = now;
      }
      ads = ads.filter(ad => {
        if (!ad.adDate) return true; // keep ads without date info
        const ts = ad.adDate;
        return ts >= minTs && ts <= maxTs;
      });
    }

    // 11. Ad format filter — only show ads matching the selected format
    if (state.filters.adFormat !== 'all') {
      ads = ads.filter(ad => {
        // Ads with unknown/undefined format do not match a specific format filter
        if (!ad.adFormat) return false;
        return ad.adFormat === state.filters.adFormat;
      });
    }

    // 12. CTA button filter — only show ads with matching CTA
    if (state.filters.selectedCTAs.size > 0) {
      ads = ads.filter(ad => {
        if (!ad.cta) return false;
        const cta = ad.cta.toLowerCase();
        // Partial match: "Shop Now" matches filter "Shop"
        for (const filter of state.filters.selectedCTAs) {
          if (cta.includes(filter.toLowerCase())) return true;
        }
        return false;
      });
    }

    // 13. Language filter — only show ads in selected language(s)
    if (state.filters.selectedLanguages.size > 0) {
      ads = ads.filter(ad => {
        const detected = detectLanguage(ad.adText || '');
        return detected && state.filters.selectedLanguages.has(detected);
      });
    }

    // 14. UTM / link filter — match landing URLs containing UTM params
    if (state.filters.utmFilter) {
      const terms = state.filters.utmFilter.split(',').map(t => t.trim().toLowerCase()).filter(Boolean);
      if (terms.length > 0) {
        ads = ads.filter(ad => {
          const urls = [ad.landingUrl, ...(ad.landingUrls || [])];
          for (const url of urls) {
            if (!url) continue;
            const urlLower = url.toLowerCase();
            // Check if URL contains at least one of the UTM terms
            const matches = terms.every(term => {
              // Support both exact param match (utm_source=foo) and partial (utm_source)
              if (term.includes('=')) return urlLower.includes(term);
              return urlLower.includes(term);
            });
            if (matches) return true;
          }
          return false;
        });
      }
    }

    state.filteredAds = ads;
    renderResults();
    renderDomainStats();

    // Update debug info bar with filter summary
    const debugInfo = $('#debugInfo');
    if (debugInfo) {
      const parts = [];
      if (state.filters.domainFilter) parts.push(`"${state.filters.domainFilter}"`);
      if (state.filters.hideCleanTlds) parts.push('hide clean');
      if (state.filters.selectedTlds.size > 0) parts.push(`${state.filters.selectedTlds.size} TLDs`);
      if (state.filters.showOnlyWithDomains) parts.push('all TLD');
      const mode = parts.length > 0 ? `[${parts.join(', ')}] ` : '';
      debugInfo.textContent = `${mode}${ads.length} of ${state.ads.length} ads`;
      debugInfo.style.display = 'inline';
    }
  }

  // ── Language detection (simple character-set based) ─────────
  // Returns ISO language code of the dominant language in text.
  // Falls back to country-based default for geo, or 'en' if unknown.
  const LANG_PATTERNS = {
    en: /[\x00-\x7F]/,         // Basic ASCII (English)
    ar: /[\u0600-\u06FF]/,    // Arabic
    zh: /[\u4E00-\u9FFF]/,     // Chinese
    ja: /[\u3040-\u309F\u30A0-\u30FF]/, // Japanese
    ko: /[\uAC00-\uD7AF\u1100-\u11FF]/, // Korean
    ru: /[\u0400-\u04FF]/,    // Cyrillic
    el: /[\u0370-\u03FF]/,    // Greek
    th: /[\u0E00-\u0E7F]/,    // Thai
    hi: /[\u0900-\u097F]/,    // Hindi
    bn: /[\u0980-\u09FF]/,    // Bengali
    he: /[\u0590-\u05FF]/,    // Hebrew
    vi: /[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]/i, // Vietnamese
    pt: /[ãõñçáéíóúàèìòùâêîôû]/i, // Portuguese (diacritics)
    es: /[áéíóúüñ¿¡àèìòùâêîôûç]/i, // Spanish
    fr: /[àâçéèêëîïôùûüÿœæ]/i, // French
    de: /[äöüß]/i,            // German
    it: /[àèéìíòóù]/i,        // Italian
    nl: /[àèéëïôùü]/i,        // Dutch
    pl: /[ąćęłńóśźż]/i,       // Polish
    tr: /[çğıöşü]/i,          // Turkish
    id: /[aeou]/i,            // Indonesian
    ms: /[aeou]/i,            // Malay
    uk: /[\u0401\u0451\u0404\u0454\u0406\u0456\u0407\u0457\u0408\u0458\u0409\u0459\u040A\u045A\u040B\u045B\u040C\u045C\u040F\u045F]/, // Ukrainian
    ro: /[ăâîșț]/i,           // Romanian
    hu: /[áéíóöőúüű]/i,       // Hungarian
    cs: /[áčďéěíňóřšťůúýž]/i, // Czech
    sv: /[åäö]/i,             // Swedish
    da: /[æøå]/i,             // Danish
    no: /[æøå]/i,             // Norwegian
    fi: /[äöå]/i,             // Finnish
    fa: /[\u0600-\u06FF]/,    // Persian (Arabic script)
    ur: /[\u0600-\u06FF]/,    // Urdu (Arabic script)
    // South Asian
    ta: /[\u0B80-\u0BFF]/,    // Tamil
    te: /[\u0C00-\u0C7F]/,    // Telugu
    kn: /[\u0C80-\u0CFF]/,    // Kannada
    ml: /[\u0D00-\u0D7F]/,   // Malayalam
    mr: /[\u0900-\u097F]/,   // Marathi (Devanagari)
    ne: /[\u0900-\u097F]/,   // Nepali (Devanagari)
    // SE Asian
    km: /[\u1780-\u17FF]/,   // Khmer
    lo: /[\u0E80-\u0EFF]/,   // Lao
    my: /[\u1000-\u109F]/,   // Burmese
    // African
    ha: /[\u0600-\u06FF]/i, // Hausa (Arabic script)
    sw: /[aeiou]/i,         // Swahili
    zu: /[aeiou]/i,          // Zulu
    xh: /[aeiou]/i,          // Xhosa
    // European (non-Latin scripts)
    bg: /[\u0400-\u04FF]/,   // Bulgarian (Cyrillic)
    sr: /[\u0400-\u04FF]/,   // Serbian (Cyrillic)
    mk: /[\u0400-\u04FF]/,   // Macedonian (Cyrillic)
    be: /[\u0400-\u04FF]/,   // Belarusian (Cyrillic)
  };

  // Geo → default language map
  const GEO_DEFAULT_LANG = {
    US: 'en', GB: 'en', AU: 'en', CA: 'en', NZ: 'en', IE: 'en', IN: 'en',
    ZA: 'en', PH: 'en', SG: 'en', MY: 'en',
    FR: 'fr', BE: 'fr', CA: 'fr', CH: 'fr',
    DE: 'de', AT: 'de', CH: 'de',
    ES: 'es', MX: 'es', AR: 'es', CO: 'es', CL: 'es', PE: 'es', VE: 'es', UY: 'es', EC: 'es', PY: 'es', BO: 'es', GT: 'es', CR: 'es', PA: 'es', DO: 'es', CU: 'es', JM: 'es', PR: 'es',
    PT: 'pt', BR: 'pt',
    IT: 'it',
    NL: 'nl',
    PL: 'pl',
    TR: 'tr',
    RU: 'ru', UA: 'uk', BY: 'be', KZ: 'kk',
    JP: 'ja', CN: 'zh', KR: 'ko', TW: 'zh',
    TH: 'th', VN: 'vi', ID: 'id', MY: 'ms', KH: 'km', LA: 'lo', MM: 'my',
    AR: 'ar', EG: 'ar', SA: 'ar', AE: 'ar', IQ: 'ar', JO: 'ar', LB: 'ar', LY: 'ar', MA: 'ar', TN: 'ar', YE: 'ar', SD: 'ar', BH: 'ar', KW: 'ar', QA: 'ar', OM: 'ar', IL: 'he',
    IR: 'fa', AF: 'fa', PK: 'ur', BD: 'bn',
    IN: 'hi', NP: 'ne', MR: 'mr',
    GR: 'el',
    CZ: 'cs', SK: 'cs', HR: 'cs', SI: 'cs', RS: 'sr', BA: 'bs', ME: 'sr', AL: 'sq', MK: 'mk', BG: 'bg',
    SE: 'sv', NO: 'no', DK: 'da', FI: 'fi', IS: 'is',
    HU: 'hu', RO: 'ro', LT: 'lv', EE: 'et', LV: 'lv', UA: 'uk',
    ET: 'et', GE: 'ka', AM: 'hy', AZ: 'az', KG: 'ru', TJ: 'ru', TM: 'ru', UZ: 'uz',
    NG: 'en', GH: 'en', KE: 'en', TZ: 'en', UG: 'en', ET: 'en', SN: 'fr', CM: 'en', ZM: 'en', ZW: 'en', BW: 'en', MZ: 'pt', AO: 'pt', GH: 'en',
  };

  function detectLanguage(text) {
    if (!text) return '';
    // Count distinctive chars for each language pattern
    const counts = {};
    for (const [lang, pattern] of Object.entries(LANG_PATTERNS)) {
      let count = 0;
      for (const char of text) { if (pattern.test(char)) count++; }
      if (count > 0) counts[lang] = count;
    }
    // For non-Latin scripts, English ASCII chars cannot compete with distinct
    // Unicode blocks. Find the best non-Latin script (highest count >= 3).
    // NOTE: Chinese chars also match the Japanese pattern range (CJK Unified).
    // To avoid zh winning over ja, we only apply ja when the ja count is
    // clearly dominant over zh. A simple heuristic: ja count >= zh count + 5.
    const nonLatin = ['ar','zh','ja','ko','ru','el','th','hi','bn','he'];
    let bestNL = { lang: '', count: 0 };
    for (const lang of nonLatin) {
      if (counts[lang] && counts[lang] > bestNL.count) bestNL = { lang, count: counts[lang] };
    }
    if (bestNL.count >= 3) {
      // Japanese detection: only return ja if it dominates Chinese
      // (avoids CJK overlap in mixed text)
      if (bestNL.lang === 'ja' && counts.zh && counts.ja < counts.zh + 5) {
        // ja not clearly dominant; fall through to Latin-script detection
      } else {
        return bestNL.lang;
      }
    }
    // For Latin-script languages: detect by distinctive character classes.
    // English (/[\x00-\x7F]/) always dominates in mixed text, so we only
    // detect Latin-script languages when they have >=3 distinctive accented chars.
    const latinLangChars = {
      fr:  /[àâçéèêëîïôùûüÿœ]/i,
      es:  /[áéíóúüñ¿¡àèìòùâêîôûç]/i,
      de:  /[äöüß]/i,
      it:  /[àèéìíòóù]/i,
      pt:  /[ãõñçáéíóúàèìòùâêîôû]/i,
      pl:  /[ąćęłńóśźż]/i,
      tr:  /[çğıöşü]/i,
    };
    const scores = {};
    for (const [lang, pattern] of Object.entries(latinLangChars)) {
      let count = 0;
      for (const char of text) { if (pattern.test(char)) count++; }
      if (count > 0) scores[lang] = count;
    }
    let best = { lang: '', count: 0 };
    for (const [lang, count] of Object.entries(scores)) {
      if (count > best.count) best = { lang, count };
    }
    if (best.count >= 3) return best.lang;
    return 'en';
  }

  // ── Classify (runs in popup) ───────────────────────────────
  const NUTRA_PATTERNS = {
    weight_loss:      /\b(weight loss|lose weight|burn fat|shed pounds|detox|belly fat|slim|burner|keto|crash diet|garcinia|forskolin)\b/i,
    blood_sugar:      /\b(blood sugar|diabetes|lower glucose|carb blocker|insulin|sugar balance|A1C)\b/i,
    prostate:         /\b(prostate|enlarged prostate|prostate health|prostate support|bladder|urinary tract men)\b/i,
    skin_beauty:      /\b(skin cream|anti aging|collagen|wrinkle|acne|fairness|glow|beauty|vitamin C serum)\b/i,
    joint_pain:       /\b(joint pain|arthritis|joint health|glucosamine|chondroitin|mobility|pain relief|inflammation)\b/i,
    energy_stamina:   /\b(energy|boost energy|endurance|stamina|vigor|testosterone|sexual performance)\b/i,
    gut_digestion:    /\b(gut health|probiotic|digestion|IBS|bloat|colon cleanse|apple cider vinegar)\b/i,
    male_enhancement: /\b(male enhancement|pennis|erectile|ED treatment|testosterone boost)\b/i,
    anti_aging:       /\b(anti aging|youthful|reverse aging|wrinkle cream|age defying|longevity)\b/i,
    heart_blood:      /\b(heart health|cholesterol|blood pressure|omega 3|cardio|tribulus)\b/i,
  };

  const NUTRA_LABELS = {
    weight_loss: 'Weight Loss', blood_sugar: 'Blood Sugar', prostate: 'Prostate',
    skin_beauty: 'Skin & Beauty', joint_pain: 'Joint Pain', energy_stamina: 'Energy',
    gut_digestion: 'Gut Health', male_enhancement: 'Male Enh.', anti_aging: 'Anti-Aging', heart_blood: 'Heart Health',
  };

  window.__popup_classify = function (text) {
    if (!text) return { is_nutra: false, categories: [], score: 0 };
    const matched = [];
    let score = 0;
    for (const [cat, pattern] of Object.entries(NUTRA_PATTERNS)) {
      const m = (text.match(pattern) || []).length;
      if (m > 0) { matched.push(cat); score += m * 10; }
    }
    return { is_nutra: matched.length > 0, categories: matched, score: Math.min(100, score) };
  };

  // ── Domain Stats ───────────────────────────────────────────
  function isShadyDomain(domain) {
    return getTldCategory(domain) === 'shady';
  }

  function getDomainStats() {
    // Aggregate by TLD: "shop.xyz" and "nice.xyz" both count toward ".xyz"
    const tldStats = {};
    for (const ad of state.ads) {
      for (const domain of (ad.domains || [])) {
        const tld = extractTld(domain);
        if (tld) tldStats[tld] = (tldStats[tld] || 0) + 1;
      }
    }
    return tldStats;
  }

  // Extract TLD from a domain string:
  // "shop.xyz" → ".xyz"  (not ".shop.xyz")
  // "google.com" → ".com" (not ".google.com")
  // "mysite.co.uk" → ".co.uk" (2-level country code)
  // ".xyz" → ".xyz"
  function extractTld(domain) {
    if (!domain) return '';
    const clean = domain.startsWith('.') ? domain.slice(1) : domain;
    const parts = clean.split('.');
    const last = parts[parts.length - 1];
    if (!last) return '';
    const lastLower = last.toLowerCase();
    // Check if last part is a known second-level domain (co.uk, co.nz, etc.)
    if (parts.length >= 2) {
      const secondLast = parts[parts.length - 2].toLowerCase();
      const twoPart = `${secondLast}.${lastLower}`;
      if (CLEAN_TLDS.has(`.${twoPart}`) || SHADY_TLDS.has(`.${twoPart}`)) {
        return `.${twoPart}`;
      }
    }
    return `.${lastLower}`;
  }

  function renderDomainStats() {
    const list = $('#domainTldList');
    if (!list) return;

    const stats = getDomainStats();
    // Show all detected TLDs (shady + non-shady), sorted by count
    const allTlds = Object.entries(stats)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 40);

    // shadyCount = number of ads that would be hidden (all domains are clean)
    const shadyCount = $('#shadyCount');
    if (shadyCount) {
      const cleanAdCount = state.ads.filter(ad => allDomainsClean(ad.domains || [])).length;
      shadyCount.textContent = `(${cleanAdCount} clean)`;
    }

    if (allTlds.length === 0) {
      list.innerHTML = '<span class="tld-chip" style="opacity:0.4;cursor:default">No landing domains detected</span>';
      return;
    }

    list.innerHTML = allTlds.map(([tld, count]) => {
      const isShady = isShadyDomain(tld);
      const active = state.filters.selectedTlds.has(tld);
      return `<button class="tld-chip${active ? ' active' : ''}${isShady ? ' shady' : ''}" data-tld="${esc(tld)}">${esc(tld)} <span style="opacity:0.6">${count}</span></button>`;
    }).join('');

    // Event listeners for new TLD chips are handled by delegated handler
  }

  // ── Render Results ─────────────────────────────────────────
  function renderResults() {
    const list = $('#resultsList');
    const count = $('#resultsCount');
    if (!list || !count) return;

    count.textContent = `${state.filteredAds.length} ads`;

    if (state.filteredAds.length === 0) {
      list.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">&#128269;</div>
          <div class="empty-text">No ads found. Try a different search or scroll the Ad Library page to load more ads.</div>
        </div>`;
      return;
    }

    list.innerHTML = state.filteredAds.map(ad => renderAdItem(ad)).join('');
    // Click events are handled by delegated handler
  }

  function renderAdItem(ad) {
    if (!ad || !ad.id) return '';
    const info = window.__popup_classify(ad.adText || '');
    const saved = state.savedAds.find(a => a.id === ad.id);
    const scoreClass = info.score >= 60 ? 'high' : info.score >= 30 ? 'med' : 'low';
    const catLabels = info.categories.slice(0, 2).map(c => NUTRA_LABELS[c]).filter(Boolean).join(', ');
    const domains = ad.domains || [];
    const truncatedText = ad.adText
      ? ad.adText.substring(0, 150) + (ad.adText.length > 150 ? '...' : '')
      : 'No ad text';

    const domainChips = domains.map(d => {
      const shady = isShadyDomain(d);
      return `<span class="ad-chip${shady ? ' shady' : ''}" title="${esc(d)}">${esc(d)}</span>`;
    }).join('');

    // Format indicator
    const fmtIcon = ad.adFormat === 'video' ? '&#9654;' : ad.adFormat === 'carousel' ? '&#8801;' : ad.adFormat === 'image' ? '&#128444;' : '';
    const fmtChip = fmtIcon ? `<span class="ad-chip" title="Format: ${ad.adFormat}">${fmtIcon} ${ad.adFormat}</span>` : '';
    // Active indicator
    const activeChip = ad.adActive === false ? '<span class="ad-chip" style="background:rgba(255,68,102,0.15);border-color:rgba(255,68,102,0.3);color:var(--accent-red)">Inactive</span>' : '';

    return `
      <div class="ad-item${saved ? ' saved' : ''}${ad.isShady ? ' is-shady' : ''}" data-id="${esc(ad.id)}">
        <div class="ad-item-header">
          <span class="ad-page-name" title="${esc(ad.pageName || '')}">${esc(ad.pageName || 'Unknown')}</span>
          ${info.score > 0 ? `<span class="ad-score-badge ${scoreClass}">${info.score}</span>` : ''}
        </div>
        <div class="ad-text">${esc(truncatedText)}</div>
        <div class="ad-meta">
          ${activeChip}
          ${fmtChip}
          ${catLabels ? `<span class="ad-chip nutra">${esc(catLabels)}</span>` : ''}
          ${domainChips}
          ${ad.cta ? `<span class="ad-chip">${esc(ad.cta.substring(0, 30))}</span>` : ''}
        </div>
        <div class="ad-actions">
          <button class="btn-icon save-btn${saved ? ' saved' : ''}" data-id="${esc(ad.id)}" title="${saved ? 'Unsave' : 'Save'}">
            ${saved ? '&#9733;' : '&#9734;'}
          </button>
          ${ad.landingUrl ? `<a href="${esc(ad.landingUrl)}" target="_blank" class="btn-icon" title="Visit" onclick="event.stopPropagation()">&#128279;</a>` : ''}
        </div>
      </div>`;
  }

  // ── Tracked Pages ─────────────────────────────────────────
  function renderTrackedPages() {
    const list = $('#trackedList');
    if (!list) return;

    if (state.trackedPages.length === 0) {
      list.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">&#128278;</div>
          <div class="empty-text">Track pages to monitor their ads. Enter a Facebook Page name.</div>
        </div>`;
      return;
    }

    // Use data attributes for XSS-safe delegation
    list.innerHTML = state.trackedPages.map(p => `
      <div class="tracked-item">
        <span class="tracked-item-name">${esc(p.name || '')}</span>
        <button class="btn-icon" data-action="remove-page" data-id="${p.id}" title="Remove">&#10005;</button>
        <button class="btn-sm btn-secondary" data-action="search-page" data-name="${esc(p.name || '')}">Search</button>
      </div>`).join('');
    // Events handled by delegated handler
  }

  async function addTrackedPage() {
    const input = $('#newPageInput');
    const name = input?.value?.trim();
    if (!name) return;
    await sendBg({ type: 'ADD_TRACKED_PAGE', name });
    if (input) input.value = '';
    await loadTrackedPages();
    toast(`Tracking: ${name}`);
  }

  async function removeTrackedPage(id) {
    await sendBg({ type: 'REMOVE_TRACKED_PAGE', id });
    await loadTrackedPages();
    toast('Page removed');
  }

  function searchTrackedPage(name) {
    const input = $('#searchInput');
    if (input) input.value = name;
    switchTab('search');
    doSearch();
  }

  // ── Saved Ads ──────────────────────────────────────────────
  function renderSavedAds() {
    const list = $('#savedList');
    if (!list) return;

    if (state.savedAds.length === 0) {
      list.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">&#9734;</div>
          <div class="empty-text">No saved ads yet. Click the star on any ad to save it.</div>
        </div>`;
      return;
    }

    list.innerHTML = state.savedAds.map(ad => renderAdItem(ad)).join('');
    // Events handled by delegated handler
  }

  // ── Save/Unsave ────────────────────────────────────────────
  async function toggleSaveAd(ad, btn) {
    const alreadySaved = state.savedAds.find(a => a.id === ad.id);

    if (alreadySaved) {
      await sendBg({ type: 'UNSAVE_AD', adId: ad.id });
      state.savedAds = state.savedAds.filter(a => a.id !== ad.id);
      toast('Removed from saved');
    } else {
      await sendBg({ type: 'SAVE_AD', ad });
      state.savedAds.unshift({ ...ad, savedAt: new Date().toISOString() });
      toast('Ad saved!');
    }

    updateBadge();
    // Re-render the relevant list to reflect the new saved state
    if (state.activeTab === 'saved') {
      renderSavedAds();
    } else {
      // Re-render search results so the star icon updates across all lists
      renderResults();
      // Also update tracked/saved lists if they have this ad
      const savedList = $('#savedList');
      if (savedList && state.savedAds.length > 0) {
        renderSavedAds();
      }
    }

    // Update modal save button if modal is open
    const modalSaveBtn = $('#saveAdBtn');
    if (modalSaveBtn && $('#adModal')?.style.display !== 'none') {
      const isStillSaved = state.savedAds.find(a => a.id === ad.id);
      modalSaveBtn.innerHTML = isStillSaved ? '&#9733; Saved' : '&#9734; Save';
      modalSaveBtn.onclick = () => toggleSaveAd(ad, modalSaveBtn);
    }
  }

  // ── Ad Modal ───────────────────────────────────────────────
  let currentModalAd = null;

  function openAdModal(ad) {
    currentModalAd = ad;
    const info = window.__popup_classify(ad.adText || '');
    const saved = state.savedAds.find(a => a.id === ad.id);
    const domains = ad.domains || [];
    const allUrls = ad.landingUrls || (ad.landingUrl ? [ad.landingUrl] : []);

    // Build URLs list
    const urlsHtml = allUrls.length > 0
      ? allUrls.map(u => {
          const isShady = SHADY_TLDS.some(t => u.includes(t));
          const displayUrl = u.length > 80 ? u.substring(0, 80) + '...' : u;
          return `<div class="modal-url-item${isShady ? ' shady-url' : ''}">
            <a href="${esc(u)}" target="_blank" class="modal-url-link">${esc(displayUrl)}</a>
            ${isShady ? '<span class="shady-badge">SHADY TLD</span>' : ''}
          </div>`;
        }).join('')
      : '<div style="color:var(--text-muted)">No landing URLs found</div>';

    const domainsHtml = domains.length > 0
      ? domains.map(d => {
          const isShady = isShadyDomain(d);
          return `<span class="ad-chip${isShady ? ' shady' : ''}">${esc(d)}</span>`;
        }).join(' ')
      : '<span style="color:var(--text-muted)">None detected</span>';

    const modalTitle = $('#modalTitle');
    const modalBody = $('#modalBody');
    const visitPageBtn = $('#visitPageBtn');
    const ripBtn = $('#ripBtn');
    const saveAdBtn = $('#saveAdBtn');
    const adModal = $('#adModal');

    if (modalTitle) modalTitle.textContent = ad.pageName || 'Ad Details';
    if (modalBody) {
      modalBody.innerHTML = `
        <p><span class="label">Page Name</span><strong style="color:var(--accent-cyan)">${esc(ad.pageName || 'Unknown')}</strong></p>
        <p><span class="label">Domains (${domains.length})</span>${domainsHtml}</p>
        <p><span class="label">Landing URLs (${allUrls.length})</span>${urlsHtml}</p>
        <p><span class="label">CTA</span>${esc(ad.cta || 'N/A')}</p>
        <p><span class="label">Classification</span>${info.is_nutra ? esc(info.categories.map(c => NUTRA_LABELS[c]).filter(Boolean).join(', ')) : 'Not Nutra'}</p>
        <p><span class="label">Aggression Score</span><strong style="color:${info.score >= 60 ? 'var(--accent-red)' : 'var(--accent-cyan)'}">${info.score}/100</strong></p>
        <p><span class="label">Ad Text</span><span style="color:var(--text-secondary);line-height:1.5;word-break:break-word">${esc(ad.adText || 'N/A')}</span></p>
      `;
    }
    if (visitPageBtn) {
      visitPageBtn.onclick = () => window.open(
        `https://www.facebook.com/search/top?q=${encodeURIComponent(ad.pageName || '')}`,
        '_blank'
      );
    }
    if (ripBtn) {
      const targetUrl = ad.landingUrl || allUrls[0] || '';
      ripBtn.onclick = () => {
        if (targetUrl) window.open(targetUrl, '_blank');
        else toast('No landing URL available');
      };
    }
    if (saveAdBtn) {
      saveAdBtn.innerHTML = saved ? '&#9733; Saved' : '&#9734; Save';
      saveAdBtn.onclick = () => {
        if (currentModalAd) toggleSaveAd(currentModalAd, saveAdBtn);
      };
    }
    if (adModal) adModal.style.display = 'flex';
  }

  function closeAdModal() {
    const adModal = $('#adModal');
    if (adModal) adModal.style.display = 'none';
    currentModalAd = null;
  }

  // ── Export ─────────────────────────────────────────────────
  function exportFiltered() {
    if (state.filteredAds.length === 0) { toast('No ads to export'); return; }
    const csv = buildCSV(state.filteredAds);
    downloadCSV(csv, 'adsrecon-export.csv');
    toast(`Exported ${state.filteredAds.length} ads`);
  }

  function exportSaved() {
    if (state.savedAds.length === 0) { toast('No ads to export'); return; }
    const csv = buildCSV(state.savedAds);
    downloadCSV(csv, 'adsrecon-saved.csv');
    toast(`Exported ${state.savedAds.length} ads`);
  }

  function buildCSV(ads) {
    const headers = ['Page Name', 'Ad Text', 'Landing URLs', 'Domains', 'CTA', 'Score', 'Categories', 'Shady', 'Saved At'];
    const rows = ads.map(a => {
      const info = window.__popup_classify(a.adText || '');
      const urls = (a.landingUrls || []).filter(Boolean);
      const urlsStr = urls.length > 0 ? urls.join(' | ') : '';
      const domains = (a.domains || []).join(', ');
      return [
        `"${(a.pageName || '').replace(/"/g, '""')}"`,
        `"${(a.adText || '').replace(/"/g, '""')}"`,
        `"${urlsStr.replace(/"/g, '""')}"`,
        `"${domains.replace(/"/g, '""')}"`,
        `"${(a.cta || '').replace(/"/g, '""')}"`,
        info.score,
        `"${info.categories.map(c => NUTRA_LABELS[c]).filter(Boolean).join(', ')}"`,
        a.isShady ? 'YES' : 'NO',
        a.savedAt || '',
      ].join(',');
    });
    return [headers.join(','), ...rows].join('\n');
  }

  function downloadCSV(csv, filename) {
    try {
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.style.display = 'none';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      toast('Export failed');
    }
  }

  // ── Badge ──────────────────────────────────────────────────
  function updateBadge() {
    const count = state.savedAds.length;
    try {
      if (count > 0) {
        chrome.runtime.sendMessage({ type: 'UPDATE_BADGE', count });
      } else {
        chrome.runtime.sendMessage({ type: 'UPDATE_BADGE', count: 0 });
      }
    } catch (_) {}
  }

  // ── Toast ──────────────────────────────────────────────────
  function toast(msg) {
    const el = $('#toast');
    if (!el) return;
    el.textContent = msg;
    el.style.display = 'block';
    clearTimeout(el._timer);
    el._timer = setTimeout(() => {
      el.style.display = 'none';
    }, 2500);
  }

  // ── Helpers ────────────────────────────────────────────────
  function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

  function esc(str) {
    if (str == null) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // ── Listen for live updates from content script ────────────
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === 'ADS_UPDATED' && msg.ads) {
      state.ads = msg.ads || [];
      state.adCount = msg.count || state.ads.length;
      applyFilters();
    }
  });

  // ── Start ─────────────────────────────────────────────────
  init();

  // ── Expose globals for test harness (used by E2E tests) ─────
  // IIFE const/let don't auto-attach to window, so we do it manually.
  // The test runner's inject_popup_js() strips this block, so it
  // never runs in production — only in the test harness page.
  if (typeof window !== 'undefined') {
    window._adsrecon_exports = [
      'SHADY_TLDS', 'CLEAN_TLDS', 'NUTRA_CATS', 'CTA_TYPES',
      'NUTRA_PATTERNS', 'LANG_PATTERNS',
      'extractTld', 'getTldCategory', 'allDomainsClean', 'isShadyDomain',
      'classify', 'detectLanguage', 'getDomainStats',
      'matchDomainFilter', 'matchTldChip', 'matchHideClean', 'matchHasDomains',
      'matchActive', 'matchDate', 'matchFormat', 'matchCta', 'matchNutra',
      'matchLanguage', 'matchUtm', 'applyAllFilters', 'applyFilters',
    ];
    window._adsrecon_exports.forEach(function (k) {
      if (typeof window[k] === 'undefined') {
        try { window[k] = eval(k); } catch (_) {}
      }
    });
  }
})();
