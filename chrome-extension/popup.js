/**
 * ADSRECON Chrome Extension — Popup Controller
 * Ultra-fast, non-blocking UI.
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
    domainStats: {}, // {tld: count}
  };

  // ── Nutra config ───────────────────────────────────────────
  // ── Shady TLDs list (comprehensive) ────────────────────────
  const SHADY_TLDS = [
    '.space', '.fun', '.info', '.xyz', '.top', '.click', '.link', '.buzz',
    '.icu', '.pw', '.cc', '.club', '.vip', '.pro', '.site', '.website',
    '.work', '.fit', '.shop', '.store', '.online', '.tech', '.gq', '.ml',
    '.cf', '.tk', '.ga', '.bid', '.win', '.date', '.racing', '.download',
    '.stream', '.accountant', '.cricket', '.party', '.science', '.faith',
    '.review', '.loan', '.trade', '.webcam', '.country', '.kim', '.science',
    '.download', '.bid', '.racing', '.party', '.trade',
  ];

  // ── Nutra config ───────────────────────────────────────────
  const NUTRA_CATS = {
    weight_loss:      { label: 'Weight Loss',     color: '#ffa94d', bg: 'rgba(255,169,77,0.15)' },
    blood_sugar:      { label: 'Blood Sugar',     color: '#ff6b6b', bg: 'rgba(255,107,107,0.15)' },
    prostate:         { label: 'Prostate',        color: '#9775fa', bg: 'rgba(151,117,250,0.15)' },
    skin_beauty:      { label: 'Skin & Beauty',  color: '#ff8cc8', bg: 'rgba(255,140,200,0.15)' },
    joint_pain:       { label: 'Joint Pain',      color: '#74c0fc', bg: 'rgba(116,192,252,0.15)' },
    energy_stamina:   { label: 'Energy',          color: '#ffd43b', bg: 'rgba(255,212,59,0.15)' },
    gut_digestion:    { label: 'Gut Health',      color: '#63e6be', bg: 'rgba(99,230,190,0.15)' },
    male_enhancement: { label: 'Male Enh.',       color: '#ff6b9d', bg: 'rgba(255,107,157,0.15)' },
    anti_aging:       { label: 'Anti-Aging',      color: '#da77f2', bg: 'rgba(218,119,242,0.15)' },
    heart_blood:      { label: 'Heart Health',    color: '#ff5555', bg: 'rgba(255,85,85,0.15)' },
  };

  // ── DOM refs ───────────────────────────────────────────────
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
    updateUI();
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
      $('#countrySelect').value = res.settings.defaultCountry || 'US';
      state.filters.category = res.settings.defaultCategory || '';
    }
  }

  async function checkConnection() {
    // Try content script directly for faster response
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
    // Fallback through background
    const res = await sendBg({ type: 'GET_AD_COUNT' });
    state.connected = res.connected;
    state.adCount = res.count || 0;
    if (!res.connected) {
      $('#loginWarning').style.display = 'flex';
    }
    updateBadge();
  }

  // ── Message helpers ──────────────────────────────────────────
  // Route to background for storage ops, directly to content script for ads
  function sendBg(msg) {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage(msg, (res) => resolve(res || {}));
    });
  }

  async function getAdsFromPage() {
    // Try content script directly first (faster)
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab?.id) {
        const res = await chrome.tabs.sendMessage(tab.id, { type: 'GET_ADS' });
        if (res?.ads) return res;
      }
    } catch (_) {}
    // Fallback: go through background
    return await sendBg({ type: 'GET_ADS' });
  }

  // ── Events ────────────────────────────────────────────────
  function bindEvents() {
    // Tabs
    $$('.tab').forEach(tab => {
      tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    // Search
    $('#doSearch').addEventListener('click', doSearch);
    $('#searchInput').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') doSearch();
    });

    // Country change
    $('#countrySelect').addEventListener('change', () => {
      sendBg({ type: 'SAVE_SETTINGS', settings: { defaultCountry: $('#countrySelect').value } });
    });

    // Ad type
    $('#adTypeSelect').addEventListener('change', doSearch);

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
    $('#clearCatFilter').addEventListener('click', () => {
      state.filters.category = '';
      $$('.chip').forEach(c => c.classList.remove('active'));
      applyFilters();
    });

    // Score slider
    $('#scoreRange').addEventListener('input', (e) => {
      state.filters.scoreMin = parseInt(e.target.value);
      $('#scoreVal').textContent = state.filters.scoreMin;
      applyFilters();
    });

    // Checkboxes
    $('#nutraOnly').addEventListener('change', (e) => {
      state.filters.nutraOnly = e.target.checked;
      applyFilters();
    });
    $('#savedOnly').addEventListener('change', (e) => {
      state.filters.savedOnly = e.target.checked;
      applyFilters();
    });

    // Shady domain filter
    $('#shadyOnly').addEventListener('change', (e) => {
      state.filters.shadyOnly = e.target.checked;
      applyFilters();
    });

    // Clear domain filters
    $('#clearDomainBtn').addEventListener('click', () => {
      state.filters.shadyOnly = false;
      state.filters.selectedTlds.clear();
      $('#shadyOnly').checked = false;
      $$('.tld-chip').forEach(c => c.classList.remove('active'));
      applyFilters();
    });

    // Open Ad Library
    $('#openLibrary').addEventListener('click', () => {
      chrome.tabs.create({ url: 'https://www.facebook.com/ads/library/' });
    });

    // Refresh — pull latest ads from content script
    $('#refreshBtn').addEventListener('click', async () => {
      const res = await getAdsFromPage();
      state.ads = res.ads || [];
      renderDomainStats();
      applyFilters();
      toast(`Found ${state.ads.length} ads`);
    });

    // Track page
    $('#addPageBtn').addEventListener('click', addTrackedPage);
    $('#newPageInput').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') addTrackedPage();
    });

    // Saved actions
    $('#exportSavedBtn').addEventListener('click', exportSaved);
    $('#clearSavedBtn').addEventListener('click', async () => {
      if (!confirm('Clear all saved ads?')) return;
      await sendBg({ type: 'CLEAR_SAVED_ADS' });
      state.savedAds = [];
      renderSavedAds();
      toast('Cleared');
    });

    // Modal close
    $('#closeModal').addEventListener('click', () => $('#adModal').style.display = 'none');
    $('#adModal').addEventListener('click', (e) => {
      if (e.target === $('#adModal')) $('#adModal').style.display = 'none';
    });

    // Export
    $('#exportBtn').addEventListener('click', exportFiltered);
  }

  // ── Tab Switching ───────────────────────────────────────────
  function switchTab(tab) {
    state.activeTab = tab;
    $$('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
    $$('.tab-content').forEach(c => c.classList.toggle('active', c.id === `tab-${tab}`));

    if (tab === 'search' && state.connected) {
      loadAdsFromPage();
    }
  }

  // ── Load ads from content script ───────────────────────────
  async function loadAdsFromPage() {
    const res = await getAdsFromPage();
    state.ads = res.ads || [];
    renderDomainStats();
    applyFilters();
  }

  // ── Search ─────────────────────────────────────────────────
  async function doSearch() {
    const keyword = $('#searchInput').value.trim();
    const country = $('#countrySelect').value;
    const adType = $('#adTypeSelect').value;

    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tabs[0] && tabs[0].url && tabs[0].url.includes('facebook.com/ads/library')) {
      // On Ad Library — send to content script to handle navigation
      try {
        await chrome.tabs.sendMessage(tabs[0].id, {
          type: 'NAVIGATE',
          search: keyword,
          country,
        });
        toast('Refreshing ads...');
      } catch (_) {
        // Content script not responding — navigate directly
        const url = new URL(tabs[0].url);
        url.searchParams.set('q', keyword);
        url.searchParams.set('country', country);
        url.searchParams.set('active_status', 'active');
        if (adType === 'political_and_issue_ads') url.searchParams.set('ad_type', 'political_and_issue_ads');
        chrome.tabs.update(tabs[0].id, { url: url.toString() });
        toast('Navigating...');
      }
    } else {
      chrome.tabs.create({
        url: `https://www.facebook.com/ads/library/?q=${encodeURIComponent(keyword)}&country=${country}&active_status=active${adType === 'political_and_issue_ads' ? '&ad_type=political_and_issue_ads' : ''}`
      });
      toast('Opening Ad Library...');
    }
  }

  // ── Filters ────────────────────────────────────────────────
  function applyFilters() {
    let ads = [...state.ads];

    // Category filter
    if (state.filters.category) {
      ads = ads.filter(ad => {
        const info = window.__popup_classify(ad.adText || '');
        return info.categories?.includes(state.filters.category);
      });
    }

    // Nutra only
    if (state.filters.nutraOnly) {
      ads = ads.filter(ad => {
        const info = window.__popup_classify(ad.adText || '');
        return info.is_nutra;
      });
    }

    // Score
    if (state.filters.scoreMin > 0) {
      ads = ads.filter(ad => {
        const info = window.__popup_classify(ad.adText || '');
        return info.score >= state.filters.scoreMin;
      });
    }

    // Saved only
    if (state.filters.savedOnly) {
      const savedIds = new Set(state.savedAds.map(a => a.id));
      ads = ads.filter(ad => savedIds.has(ad.id));
    }

    // Shady domain filter
    if (state.filters.shadyOnly) {
      ads = ads.filter(ad => ad.isShady);
    }

    // Specific TLD filter
    if (state.filters.selectedTlds.size > 0) {
      ads = ads.filter(ad => {
        const adDomains = ad.domains || [];
        return adDomains.some(d => state.filters.selectedTlds.has(d));
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
    const matched = [];
    let score = 0;
    for (const [cat, pattern] of Object.entries(NUTRA_PATTERNS)) {
      const m = (text.match(pattern) || []).length;
      if (m > 0) { matched.push(cat); score += m * 10; }
    }
    return { is_nutra: matched.length > 0, categories: matched, score: Math.min(100, score) };
  };

  // ── Domain Stats ───────────────────────────────────────────
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
    const stats = getDomainStats();
    const list = $('#domainTldList');
    const shadyEls = Object.entries(stats)
      .filter(([d]) => SHADY_TLDS.some(t => d.endsWith(t)))
      .sort((a, b) => b[1] - a[1])
      .slice(0, 30);

    $('#shadyCount').textContent = `(${(shadyEls.length || '0')})`;

    if (shadyEls.length === 0) {
      list.innerHTML = '<span class="tld-chip" style="opacity:0.4">No shady domains found</span>';
      return;
    }

    list.innerHTML = shadyEls.map(([tld, count]) => {
      const active = state.filters.selectedTlds.has(tld);
      return `<button class="tld-chip${active ? ' active' : ''}" data-tld="${esc(tld)}">${esc(tld)} <span style="opacity:0.6">${count}</span></button>`;
    }).join('');

    list.querySelectorAll('.tld-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const tld = chip.dataset.tld;
        if (state.filters.selectedTlds.has(tld)) {
          state.filters.selectedTlds.delete(tld);
          chip.classList.remove('active');
        } else {
          state.filters.selectedTlds.add(tld);
          chip.classList.add('active');
        }
        applyFilters();
      });
    });
  }

  // ── Render Results ─────────────────────────────────────────
  function renderResults() {
    const list = $('#resultsList');
    const count = $('#resultsCount');
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

    // Bind click events
    list.querySelectorAll('.ad-item').forEach(item => {
      item.addEventListener('click', (e) => {
        if (e.target.closest('.btn-icon')) return;
        const ad = state.filteredAds.find(a => a.id === item.dataset.id);
        if (ad) openAdModal(ad);
      });
    });

    list.querySelectorAll('.save-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const ad = state.filteredAds.find(a => a.id === btn.dataset.id);
        if (ad) toggleSaveAd(ad, btn);
      });
    });
  }

  function renderAdItem(ad) {
    const info = window.__popup_classify(ad.adText || '');
    const saved = state.savedAds.find(a => a.id === ad.id);
    const scoreClass = info.score >= 60 ? 'high' : info.score >= 30 ? 'med' : 'low';
    const catLabels = info.categories.slice(0, 2).map(c => NUTRA_LABELS[c]).join(', ');
    const domains = ad.domains || [];
    const truncatedText = ad.adText ? ad.adText.substring(0, 150) + (ad.adText.length > 150 ? '...' : '') : 'No ad text';

    const domainChips = domains.map(d => {
      const isShady = SHADY_TLDS.some(t => d.endsWith(t));
      return `<span class="ad-chip${isShady ? ' shady' : ''}" title="${esc(d)}">${esc(d)}</span>`;
    }).join('');

    return `
      <div class="ad-item${saved ? ' saved' : ''}${ad.isShady ? ' is-shady' : ''}" data-id="${esc(ad.id)}">
        <div class="ad-item-header">
          <span class="ad-page-name" title="${esc(ad.pageName)}">${esc(ad.pageName)}</span>
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
          ${ad.landingUrl ? `<button class="btn-icon" onclick="window.open('${esc(ad.landingUrl)}', '_blank')" title="Visit">&#128279;</button>` : ''}
        </div>
      </div>`;
  }

  // ── Tracked Pages ─────────────────────────────────────────
  function renderTrackedPages() {
    const list = $('#trackedList');
    if (state.trackedPages.length === 0) {
      list.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">&#128278;</div>
          <div class="empty-text">Track pages to monitor their ads. Enter a Facebook Page name.</div>
        </div>`;
      return;
    }

    list.innerHTML = state.trackedPages.map(p => `
      <div class="tracked-item">
        <span class="tracked-item-name">${esc(p.name)}</span>
        <button class="btn-icon" onclick="window.__removePage(${p.id})" title="Remove">&#10005;</button>
        <button class="btn-sm btn-secondary" onclick="window.__searchPage('${esc(p.name)}')">Search</button>
      </div>`).join('');

    // Global functions for onclick
    window.__removePage = async (id) => {
      await sendBg({ type: 'REMOVE_TRACKED_PAGE', id });
      await loadTrackedPages();
    };

    window.__searchPage = (name) => {
      $('#searchInput').value = name;
      switchTab('search');
      doSearch();
    };
  }

  async function addTrackedPage() {
    const name = $('#newPageInput').value.trim();
    if (!name) return;
    await sendBg({ type: 'ADD_TRACKED_PAGE', name });
    $('#newPageInput').value = '';
    await loadTrackedPages();
    toast(`Tracking: ${name}`);
  }

  // ── Saved Ads ──────────────────────────────────────────────
  function renderSavedAds() {
    const list = $('#savedList');
    if (state.savedAds.length === 0) {
      list.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">&#9734;</div>
          <div class="empty-text">No saved ads yet. Click the star on any ad to save it.</div>
        </div>`;
      return;
    }

    list.innerHTML = state.savedAds.map(ad => renderAdItem(ad)).join('');

    list.querySelectorAll('.ad-item').forEach(item => {
      item.addEventListener('click', (e) => {
        if (e.target.closest('.btn-icon')) return;
        const ad = state.savedAds.find(a => a.id === item.dataset.id);
        if (ad) openAdModal(ad);
      });
    });

    list.querySelectorAll('.save-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const ad = state.savedAds.find(a => a.id === btn.dataset.id);
        if (ad) toggleSaveAd(ad, btn);
      });
    });
  }

  // ── Save/Unsave ────────────────────────────────────────────
  async function toggleSaveAd(ad, btn) {
    const alreadySaved = state.savedAds.find(a => a.id === ad.id);
    if (alreadySaved) {
      await sendBg({ type: 'UNSAVE_AD', adId: ad.id });
      state.savedAds = state.savedAds.filter(a => a.id !== ad.id);
      btn.classList.remove('saved');
      btn.innerHTML = '&#9734;';
      toast('Removed from saved');
    } else {
      await sendBg({ type: 'SAVE_AD', ad });
      state.savedAds.unshift({ ...ad, savedAt: new Date().toISOString() });
      btn.classList.add('saved');
      btn.innerHTML = '&#9733;';
      toast('Ad saved!');
    }
    updateBadge();
  }

  // ── Ad Modal ───────────────────────────────────────────────
  function openAdModal(ad) {
    const info = window.__popup_classify(ad.adText || '');
    const saved = state.savedAds.find(a => a.id === ad.id);
    const domains = ad.domains || [];

    // Build all landing URLs section
    const allUrls = ad.landingUrls || (ad.landingUrl ? [ad.landingUrl] : []);
    const urlsHtml = allUrls.length > 0
      ? allUrls.map(u => {
          const isShady = SHADY_TLDS.some(t => u.includes(t));
          return `<div class="modal-url-item${isShady ? ' shady-url' : ''}">
            <a href="${esc(u)}" target="_blank" class="modal-url-link">${esc(u.length > 80 ? u.substring(0, 80) + '...' : u)}</a>
            ${isShady ? '<span class="shady-badge">SHADY TLD</span>' : ''}
          </div>`;
        }).join('')
      : '<div style="color:var(--text-muted)">No landing URLs found</div>';

    const domainsHtml = domains.length > 0
      ? domains.map(d => {
          const isShady = SHADY_TLDS.some(t => d.endsWith(t));
          return `<span class="ad-chip${isShady ? ' shady' : ''}">${esc(d)}</span>`;
        }).join(' ')
      : '<span style="color:var(--text-muted)">None detected</span>';

    $('#modalTitle').textContent = ad.pageName;
    $('#modalBody').innerHTML = `
      <p><span class="label">Page Name</span><strong style="color:var(--accent-cyan)">${esc(ad.pageName)}</strong></p>
      <p><span class="label">Domains (${domains.length})</span>${domainsHtml}</p>
      <p><span class="label">Landing URLs (${allUrls.length})</span>${urlsHtml}</p>
      <p><span class="label">CTA</span>${esc(ad.cta || 'N/A')}</p>
      <p><span class="label">Classification</span>${info.is_nutra ? esc(info.categories.map(c => NUTRA_LABELS[c]).join(', ')) : 'Not Nutra'}</p>
      <p><span class="label">Aggression Score</span><strong style="color:${info.score >= 60 ? 'var(--accent-red)' : 'var(--accent-cyan)'}">${info.score}/100</strong></p>
      <p><span class="label">Ad Text</span><span style="color:var(--text-secondary);line-height:1.5;word-break:break-word">${esc(ad.adText || 'N/A')}</span></p>
    `;
    $('#visitPageBtn').onclick = () => window.open(`https://www.facebook.com/search/top?q=${encodeURIComponent(ad.pageName)}`, '_blank');
    $('#ripBtn').onclick = () => window.open(ad.landingUrl || allUrls[0] || '', '_blank');
    $('#saveAdBtn').onclick = () => { toggleSaveAd(ad, $('#saveAdBtn')); };
    $('#saveAdBtn').innerHTML = saved ? '&#9733; Saved' : '&#9734; Save';
    $('#adModal').style.display = 'flex';
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
      const urls = (a.landingUrls || [a.landingUrl || '']).join(' | ');
      const domains = (a.domains || []).join(', ');
      return [
        `"${(a.pageName || '').replace(/"/g, '""')}"`,
        `"${(a.adText || '').replace(/"/g, '""')}"`,
        `"${urls.replace(/"/g, '""')}"`,
        `"${domains.replace(/"/g, '""')}"`,
        `"${(a.cta || '').replace(/"/g, '""')}"`,
        info.score,
        `"${info.categories.map(c => NUTRA_LABELS[c]).join(', ')}"`,
        a.isShady ? 'YES' : 'NO',
        a.savedAt || '',
      ].join(',');
    });
    return [headers.join(','), ...rows].join('\n');
  }

  function downloadCSV(csv, filename) {
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  // ── Badge ──────────────────────────────────────────────────
  function updateBadge() {
    const count = state.savedAds.length;
    chrome.runtime.sendMessage({ type: 'UPDATE_BADGE', count }).catch(() => {});
    if (count > 0) {
      chrome.action.setBadgeText({ text: String(count) });
      chrome.action.setBadgeBackgroundColor({ color: '#00d4ff' });
    } else {
      chrome.action.setBadgeText({ text: '' });
    }
  }

  // ── UI Update ─────────────────────────────────────────────
  function updateUI() {
    // Already handled by individual render functions
  }

  // ── Toast ──────────────────────────────────────────────────
  function toast(msg) {
    const el = $('#toast');
    el.textContent = msg;
    el.style.display = 'block';
    clearTimeout(el._timer);
    el._timer = setTimeout(() => { el.style.display = 'none'; }, 2500);
  }

  // ── Helpers ────────────────────────────────────────────────
  function esc(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // ── Start ─────────────────────────────────────────────────
  init();
})();
