/**
 * ADSRECON Chrome Extension — Popup Controller
 * Ultra-fast, non-blocking UI. All bugs fixed.
 */

(function () {
  'use strict';

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
      shadyOnly: false,
      selectedTlds: new Set(),
    },
    connected: false,
    adCount: 0,
  };

  // ── Shady TLDs (deduplicated) ─────────────────────────────
  const SHADY_TLDS = [
    '.space', '.fun', '.info', '.xyz', '.top', '.click', '.link', '.buzz',
    '.icu', '.pw', '.cc', '.club', '.vip', '.pro', '.site', '.website',
    '.work', '.fit', '.shop', '.store', '.online', '.tech', '.gq', '.ml',
    '.cf', '.tk', '.ga', '.bid', '.win', '.date', '.racing', '.download',
    '.stream', '.accountant', '.cricket', '.party', '.science', '.faith',
    '.review', '.loan', '.trade', '.webcam', '.country', '.kim',
  ];

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
    }
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

    // Country change — auto-search when country changes
    const countrySelect = $('#countrySelect');
    if (countrySelect) {
      countrySelect.addEventListener('change', () => {
        const newCountry = countrySelect.value;
        sendBg({ type: 'SAVE_SETTINGS', settings: { defaultCountry: newCountry } });
        doCountrySearch(newCountry);
      });
    }

    // Ad type change — auto-search when ad type changes
    const adTypeSelect = $('#adTypeSelect');
    if (adTypeSelect) {
      adTypeSelect.addEventListener('change', () => {
        const searchType = ($('#searchTypeSelect')?.value) || 'keyword';
        const keyword = ($('#searchInput')?.value || '').trim();
        const country = ($('#countrySelect')?.value) || 'US';
        const adType = ($('#adTypeSelect')?.value) || 'all';
        navigateToSearch(keyword, country, adType, searchType);
      });
    }

    // Search type change — toggle domain input visibility
    const searchTypeSelect = $('#searchTypeSelect');
    if (searchTypeSelect) {
      searchTypeSelect.addEventListener('change', () => {
        const isDomain = searchTypeSelect.value === 'landing_page';
        const landingGroup = $('#landingPageGroup');
        const keywordInput = $('#searchInput');
        if (landingGroup) landingGroup.style.display = isDomain ? 'flex' : 'none';
        if (keywordInput) keywordInput.style.display = isDomain ? 'none' : 'block';
        if (isDomain) {
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
    const shadyOnly = $('#shadyOnly');
    if (shadyOnly) shadyOnly.addEventListener('change', (e) => {
      state.filters.shadyOnly = !!e.target.checked;
      applyFilters();
    });

    // Clear domain filters
    const clearDomainBtn = $('#clearDomainBtn');
    if (clearDomainBtn) {
      clearDomainBtn.addEventListener('click', () => {
        state.filters.shadyOnly = false;
        state.filters.selectedTlds.clear();
        const cb = $('#shadyOnly');
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

    // Refresh
    const refreshBtn = $('#refreshBtn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', async () => {
        refreshBtn.disabled = true;
        try {
          const res = await getAdsFromPage();
          state.ads = res.ads || [];
          state.adCount = state.ads.length;
          renderDomainStats();
          applyFilters();
          toast(`Found ${state.ads.length} ads`);
        } finally {
          refreshBtn.disabled = false;
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

    // TLD chip click
    const tldChip = target.closest('.tld-chip');
    if (tldChip && tldChip.dataset.tld) {
      const tld = tldChip.dataset.tld;
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
  async function navigateToSearch(keyword, country, adType, searchType) {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    const activeTab = tabs[0];

    const targetUrl = new URL('https://www.facebook.com/ads/library/');
    targetUrl.searchParams.set('q', keyword);
    targetUrl.searchParams.set('country', country);
    targetUrl.searchParams.set('active_status', 'active');
    if (adType === 'political_and_issue_ads') {
      targetUrl.searchParams.set('ad_type', 'political_and_issue_ads');
    }
    // search_type: keyword_unordered (default) or landing_page
    if (searchType === 'landing_page') {
      targetUrl.searchParams.set('search_type', 'landing_page');
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
        const timeout = setTimeout(resolve, 5000);
      });
      chrome.tabs.update(tabId, { url: targetUrl.toString() });
      toast('Searching...');
      await loadPromise;
      await delay(1500);
      const res = await getAdsFromPage();
      state.ads = res.ads || [];
      state.adCount = state.ads.length;
      renderDomainStats();
      applyFilters();
      if (state.ads.length > 0) {
        toast(`Found ${state.ads.length} ads`);
      } else {
        toast('Scroll page to load more ads');
      }
    } else {
      chrome.tabs.create({ url: targetUrl.toString() });
      toast('Opening Ad Library...');
    }
  }

  // ── Search ─────────────────────────────────────────────────
  async function doSearch() {
    const searchType = ($('#searchTypeSelect')?.value) || 'keyword';
    const keyword = ($('#searchInput')?.value || '').trim();
    const country = ($('#countrySelect')?.value) || 'US';
    const adType = ($('#adTypeSelect')?.value) || 'all';
    await navigateToSearch(keyword, country, adType, searchType);
  }

  // ── Landing page domain search ────────────────────────────
  async function doLandingSearch() {
    const domain = ($('#landingPageInput')?.value || '').trim();
    if (!domain) { toast('Enter a domain first'); return; }
    const country = ($('#countrySelect')?.value) || 'US';
    const adType = ($('#adTypeSelect')?.value) || 'all';
    // Strip leading dot if user typed ".xyz"
    const cleanDomain = domain.replace(/^\.+/, '');
    await navigateToSearch(cleanDomain, country, adType, 'landing_page');
  }

  // ── Country change (auto-triggered) ───────────────────────
  async function doCountrySearch(newCountry) {
    const searchType = ($('#searchTypeSelect')?.value) || 'keyword';
    const keyword = ($('#searchInput')?.value || '').trim();
    const adType = ($('#adTypeSelect')?.value) || 'all';
    await navigateToSearch(keyword, newCountry, adType, searchType);
  }

  // ── Filters ────────────────────────────────────────────────
  function applyFilters() {
    let ads = [...state.ads];

    if (state.filters.category) {
      ads = ads.filter(ad => {
        const info = window.__popup_classify(ad.adText || '');
        return info.categories?.includes(state.filters.category);
      });
    }

    if (state.filters.nutraOnly) {
      ads = ads.filter(ad => {
        const info = window.__popup_classify(ad.adText || '');
        return info.is_nutra;
      });
    }

    if (state.filters.scoreMin > 0) {
      ads = ads.filter(ad => {
        const info = window.__popup_classify(ad.adText || '');
        return info.score >= state.filters.scoreMin;
      });
    }

    if (state.filters.savedOnly) {
      const savedIds = new Set(state.savedAds.map(a => a.id));
      ads = ads.filter(ad => savedIds.has(ad.id));
    }

    if (state.filters.shadyOnly) {
      ads = ads.filter(ad => !!ad.isShady);
    }

    if (state.filters.selectedTlds.size > 0) {
      ads = ads.filter(ad => {
        const adDomains = ad.domains || [];
        return adDomains.some(d => {
          const cleanDomain = d.startsWith('.') ? d : '.' + d;
          return state.filters.selectedTlds.has(cleanDomain) ||
                 state.filters.selectedTlds.has(d);
        });
      });
    }

    state.filteredAds = ads;
    renderResults();
    renderDomainStats();
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
    const cleanDomain = domain.startsWith('.') ? domain : '.' + domain;
    return SHADY_TLDS.includes(cleanDomain);
  }

  function getDomainStats() {
    const stats = {};
    for (const ad of state.ads) {
      for (const domain of (ad.domains || [])) {
        stats[domain] = (stats[domain] || 0) + 1;
      }
    }
    return stats;
  }

  function renderDomainStats() {
    const list = $('#domainTldList');
    if (!list) return;

    const stats = getDomainStats();
    const shadyEls = Object.entries(stats)
      .filter(([d]) => isShadyDomain(d))
      .sort((a, b) => b[1] - a[1])
      .slice(0, 30);

    const shadyCount = $('#shadyCount');
    if (shadyCount) {
      const count = shadyEls.reduce((sum, [, n]) => sum + n, 0);
      shadyCount.textContent = `(${count})`;
    }

    if (shadyEls.length === 0) {
      list.innerHTML = '<span class="tld-chip" style="opacity:0.4;cursor:default">No shady domains found</span>';
      return;
    }

    list.innerHTML = shadyEls.map(([tld, count]) => {
      const active = state.filters.selectedTlds.has(tld) || state.filters.selectedTlds.has('.' + tld);
      return `<button class="tld-chip${active ? ' active' : ''}" data-tld="${esc(tld)}">${esc(tld)} <span style="opacity:0.6">${count}</span></button>`;
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

    return `
      <div class="ad-item${saved ? ' saved' : ''}${ad.isShady ? ' is-shady' : ''}" data-id="${esc(ad.id)}">
        <div class="ad-item-header">
          <span class="ad-page-name" title="${esc(ad.pageName || '')}">${esc(ad.pageName || 'Unknown')}</span>
          ${info.score > 0 ? `<span class="ad-score-badge ${scoreClass}">${info.score}</span>` : ''}
        </div>
        <div class="ad-text">${esc(truncatedText)}</div>
        <div class="ad-meta">
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
})();
