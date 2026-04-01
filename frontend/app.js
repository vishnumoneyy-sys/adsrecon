/**
 * ADSRECON — app.js
 * Complete vanilla JS SPA for Meta Ads Library spy tool
 * Backend: localhost:8000
 */

(function () {
  'use strict';

  /* ============================================================
     CONFIG & CONSTANTS
  ============================================================ */

  const API_BASE = 'http://localhost:8000';
  const NUTRA_CATEGORIES = {
    blood_sugar:      { label: 'Blood Sugar',      color: '#ff6b6b', bg: 'rgba(255,107,107,0.15)' },
    weight_loss:      { label: 'Weight Loss',      color: '#ffa94d', bg: 'rgba(255,169,77,0.15)' },
    prostate:         { label: 'Prostate',          color: '#9775fa', bg: 'rgba(151,117,250,0.15)' },
    skin_beauty:      { label: 'Skin & Beauty',    color: '#ff8cc8', bg: 'rgba(255,140,200,0.15)' },
    joint_pain:       { label: 'Joint Pain',        color: '#74c0fc', bg: 'rgba(116,192,252,0.15)' },
    energy_stamina:   { label: 'Energy & Stamina', color: '#ffd43b', bg: 'rgba(255,212,59,0.15)' },
    gut_digestion:    { label: 'Gut & Digestion', color: '#63e6be', bg: 'rgba(99,230,190,0.15)' },
    male_enhancement:  { label: 'Male Enhancement',  color: '#ff6b9d', bg: 'rgba(255,107,157,0.15)' },
    female_health:    { label: 'Female Health',    color: '#f783ac', bg: 'rgba(247,131,172,0.15)' },
    anti_aging:       { label: 'Anti-Aging',        color: '#da77f2', bg: 'rgba(218,119,242,0.15)' },
    eyes_vision:      { label: 'Eyes & Vision',     color: '#66d9e8', bg: 'rgba(102,217,232,0.15)' },
    heart_blood:      { label: 'Heart & Blood',    color: '#ff5555', bg: 'rgba(255,85,85,0.15)' },
  };

  const COUNTRY_LIST = ['US', 'GB', 'CA', 'AU', 'DE', 'FR', 'BR', 'MX', 'JP', 'IN'];

  const COUNTRY_NAMES = {
    US: 'United States', GB: 'United Kingdom', CA: 'Canada', AU: 'Australia',
    DE: 'Germany', FR: 'France', BR: 'Brazil', MX: 'Mexico', JP: 'Japan', IN: 'India',
  };

  // Major markets pre-selected in Multi-Country tab
  const MAJOR_MARKETS = ['US', 'GB', 'CA', 'AU'];

  /* ============================================================
     STATE
  ============================================================ */

  const state = {
    ads: [],
    filteredAds: [],
    selectedAd: null,
    selectedAdDetail: null,
    ripStatus: null,
    classifyStatus: null,
    ripList: [],
    previewMode: 'iframe',
    ripDevice: 'desktop',
    activeTab: 'search',
    activeDetailTab: 'info',
    filters: {
      category: '',
      status: '',
      savedOnly: false,
      sort: 'newest',
    },
    searchQuery: '',
    isLoading: false,
    loadError: null,
    backendOk: false,
    browserPool: { total: 0, available: 0 },
    notifications: [],
    // Multi-country state
    scrapeTab: 'single',        // 'single' | 'multi' | 'auto'
    selectedCountries: new Set(MAJOR_MARKETS),
    selectedCategories: new Set(),
    scrapeInProgress: false,
  };

  /* ============================================================
     DOM REFS
  ============================================================ */

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  function getEl(id) { return document.getElementById(id); }

  const els = {
    mainLayout:         getEl('mainLayout'),
    adGrid:             getEl('adGrid'),
    detailPanel:        getEl('detailPanel'),
    detailCloseBtn:     getEl('detailCloseBtn'),
    searchInput:         getEl('searchInput'),
    scrapeBtn:          getEl('scrapeBtn'),
    autoScrapeBtn:      getEl('autoScrapeBtn'),
    tabSearch:          getEl('tabSearch'),
    tabScraped:         getEl('tabScraped'),
    tabDemo:            getEl('tabDemo'),
    categoryList:       getEl('categoryList'),
    statusOptions:      getEl('statusOptions'),
    savedOnlyToggle:    getEl('savedOnlyToggle'),
    sortSelect:         getEl('sortSelect'),
    exportCsvBtn:       getEl('exportCsvBtn'),
    exportJsonBtn:      getEl('exportJsonBtn'),
    clearFiltersBtn:    getEl('clearFiltersBtn'),
    resultCountNum:      getEl('resultCountNum'),
    resultFiltered:     getEl('resultFiltered'),
    statTotal:          getEl('statTotal'),
    statActive:         getEl('statActive'),
    statSaved:          getEl('statSaved'),
    statCloaked:        getEl('statCloaked'),
    backendDot:         getEl('backendDot'),
    browserDot:         getEl('browserDot'),
    browserCount:       getEl('browserCount'),
    browserPoolStatus:  getEl('browserPoolStatus'),
    // Detail
    detailPageName:     getEl('detailPageName'),
    detailTabs:         getEl('detailTabs'),
    detailText:         getEl('detailText'),
    detailUrls:         getEl('detailUrls'),
    detailNutraChips:   getEl('detailNutraChips'),
    detailBadgeRow:     getEl('detailBadgeRow'),
    detailAggression:   getEl('detailAggression'),
    detailHook:         getEl('detailHook'),
    detailHookType:     getEl('detailHookType'),
    detailKeywords:     getEl('detailKeywords'),
    detailMatchedKeywords: getEl('detailMatchedKeywords'),
    detailThumbs:       getEl('detailThumbs'),
    detailThumbGallery: getEl('detailThumbGallery'),
    detailVideo:        getEl('detailVideo'),
    detailVideoContainer: getEl('detailVideoContainer'),
    detailVideoPlaceholder: getEl('detailVideoPlaceholder'),
    // Preview tab
    deviceToggle:       getEl('deviceToggle'),
    ripLanderBtn:       getEl('ripLanderBtn'),
    ripSpinner:         getEl('ripSpinner'),
    previewContainer:   getEl('previewContainer'),
    previewToolbar:     getEl('previewToolbar'),
    previewUrl:         getEl('previewUrl'),
    previewLoading:     getEl('previewLoading'),
    previewEmpty:       getEl('previewEmpty'),
    previewIframe:      getEl('previewIframe'),
    previewImage:       getEl('previewImage'),
    classifyBtn:        getEl('classifyBtn'),
    classifySpinner:     getEl('classifySpinner'),
    classifyResults:     getEl('classifyResults'),
    classifyResultsBody: getEl('classifyResultsBody'),
    // Detail actions
    detailSaveBtn:      getEl('detailSaveBtn'),
    detailOpenBtn:      getEl('detailOpenBtn'),
    detailDeleteBtn:    getEl('detailDeleteBtn'),
    // Rips tab
    ripsList:           getEl('ripsList'),
    ripsEmpty:          getEl('ripsEmpty'),
    // Modal
    scrapeModal:        getEl('scrapeModal'),
    scrapeModalOverlay: getEl('scrapeModalOverlay'),
    scrapeModalBox:     getEl('scrapeModalBox'),
    scrapeModalTitle:   getEl('scrapeModalTitle'),
    modalPageUrl:       getEl('modalPageUrl'),
    modalCountry:       getEl('modalCountry'),
    scrapeModalCancel:   getEl('scrapeModalCancel'),
    scrapeModalRun:     getEl('scrapeModalRun'),
    scrapeModalRunLabel: getEl('scrapeModalRunLabel'),
    scrapeSpinner:      getEl('scrapeSpinner'),
    scrapeProgressArea: getEl('scrapeProgressArea'),
    scrapeProgressLabel: getEl('scrapeProgressLabel'),
    loadDemoBtn:      getEl('loadDemoBtn'),
    scrapeProgressBar:  getEl('scrapeProgressBar'),
    tabInfo:            getEl('tabInfo'),
    tabPreview:         getEl('tabPreview'),
    tabRips:            getEl('tabRips'),
    // Multi-country
    countryCheckboxGrid: getEl('countryCheckboxGrid'),
    selectAllCountries: getEl('selectAllCountries'),
    clearAllCountries:  getEl('clearAllCountries'),
    modalMultiKeyword:   getEl('modalMultiKeyword'),
    modalMultiPageUrl:   getEl('modalMultiPageUrl'),
    // Auto-category
    categoryCheckboxGrid: getEl('categoryCheckboxGrid'),
    selectAllCategories:  getEl('selectAllCategories'),
    clearAllCategories:  getEl('clearAllCategories'),
    autoCountryCheckboxGrid: getEl('autoCountryCheckboxGrid'),
    selectAllCountriesAuto: getEl('selectAllCountriesAuto'),
    clearAllCountriesAuto: getEl('clearAllCountriesAuto'),
  };

  /* ============================================================
     API TOKEN (Facebook Graph API)
  ============================================================ */

  async function checkTokenStatus() {
    try {
      const data = await apiGet('/api/ads/settings');
      const badge = document.getElementById('apiTokenBadge');
      const noToken = document.getElementById('apiNoToken');
      const hasToken = document.getElementById('apiHasToken');
      const dot = document.getElementById('apiStatusDot');
      const text = document.getElementById('apiStatusText');
      const masked = document.getElementById('tokenMasked');

      if (data.fb_token_configured) {
        dot.style.background = '#4CAF50';
        text.textContent = 'Graph API: Active (free)';
        badge.textContent = 'FREE';
        badge.style.background = '#4CAF50';
        badge.style.display = 'inline';
        noToken.style.display = 'none';
        hasToken.style.display = 'block';
        masked.textContent = data.fb_token_masked || '';
      } else {
        dot.style.background = '#ff9800';
        text.textContent = 'Graph API: Not configured';
        badge.style.display = 'none';
        noToken.style.display = 'block';
        hasToken.style.display = 'none';
      }
    } catch {
      // Settings endpoint not available yet — ignore
    }
  }

  async function saveToken() {
    const input = document.getElementById('apiTokenInput');
    const result = document.getElementById('apiResult');
    const token = input.value.trim();
    if (!token) return;

    result.style.display = 'block';
    result.textContent = 'Validating token...';
    result.style.color = 'var(--text-muted)';

    try {
      const data = await apiPost('/api/ads/settings?' + new URLSearchParams({ token }));
      result.style.color = '#4CAF50';
      result.textContent = data.message;
      input.value = '';
      document.getElementById('apiTokenForm').style.display = 'none';
      document.getElementById('showTokenFormBtn').style.display = 'block';
      await checkTokenStatus();
      await loadAds();
    } catch (err) {
      result.style.color = '#f44336';
      result.textContent = 'Error: ' + err.message;
    }
  }

  async function testToken() {
    const result = document.getElementById('apiResult');
    const btn = document.getElementById('testTokenBtn');
    result.style.display = 'block';
    result.style.color = 'var(--text-muted)';
    result.textContent = 'Testing...';
    btn.disabled = true;

    try {
      const data = await apiGet('/api/ads/test-graph-api');
      result.style.color = '#4CAF50';
      const sample = data.sample && data.sample[0]
        ? `Sample ad: "${data.sample[0].text}" from ${data.sample[0].page}`
        : '';
      result.textContent = `SUCCESS! ${data.ads_found} test ads found. ${sample}`;
    } catch (err) {
      result.style.color = '#f44336';
      result.textContent = 'Failed: ' + err.message;
    } finally {
      btn.disabled = false;
    }
  }

  async function clearToken() {
    if (!confirm('Remove the Facebook access token?')) return;
    try {
      const data = await apiDelete('/api/ads/settings');
      showNotification('Token removed', 'success');
      await checkTokenStatus();
    } catch (err) {
      showNotification('Failed to remove token: ' + err.message, 'error');
    }
  }

  function showTokenForm() {
    document.getElementById('apiTokenForm').style.display = 'block';
    document.getElementById('showTokenFormBtn').style.display = 'none';
    document.getElementById('apiResult').style.display = 'none';
    document.getElementById('apiTokenInput').focus();
  }

  function cancelTokenForm() {
    document.getElementById('apiTokenForm').style.display = 'none';
    document.getElementById('showTokenFormBtn').style.display = 'block';
    document.getElementById('apiTokenInput').value = '';
  }

  /* ============================================================
     UTILITIES
  ============================================================ */

  function debounce(fn, delay) {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), delay);
    };
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function truncate(str, len) {
    if (!str) return '';
    return str.length > len ? str.slice(0, len) + '...' : str;
  }

  function getDomain(url) {
    try {
      return new URL(url).hostname;
    } catch {
      return url;
    }
  }

  function domainsDiffer(url1, url2) {
    try {
      return new URL(url1).hostname !== new URL(url2).hostname;
    } catch {
      return false;
    }
  }

  function formatDate(iso) {
    if (!iso) return '';
    try {
      return new Date(iso).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
      });
    } catch {
      return iso;
    }
  }

  function showNotification(text, type = 'info', duration = 3500) {
    const id = Date.now() + Math.random();
    const colors = {
      success: '#00ff88', error: '#ff3366', info: '#00d4ff', warning: '#ffaa00',
    };
    const icons = {
      success: '&#10003;', error: '&#10007;', info: '&#8505;', warning: '&#9888;',
    };

    const el = document.createElement('div');
    el.className = `notification is-${type}`;
    el.id = `notif-${id}`;
    el.innerHTML = `
      <span class="notification-icon" style="color:${colors[type] || colors.info}">${icons[type] || icons.info}</span>
      <span class="notification-text">${escapeHtml(text)}</span>
      <button class="notification-close" onclick="this.parentElement.remove()">&#10005;</button>
    `;
    document.body.appendChild(el);

    setTimeout(() => {
      const n = document.getElementById(`notif-${id}`);
      if (n) n.remove();
    }, duration);
  }

  function getNutraCategories(ad) {
    if (!ad) return [];
    if (ad.nutra_categories) {
      if (typeof ad.nutra_categories === 'object') {
        return Object.entries(ad.nutra_categories)
          .filter(([, v]) => v === true)
          .map(([k]) => k);
      }
      return Array.isArray(ad.nutra_categories) ? ad.nutra_categories : [];
    }
    if (ad.categories) return Array.isArray(ad.categories) ? ad.categories : [];
    return [];
  }

  function getAggressionLevel(score) {
    if (score === null || score === undefined) return null;
    if (score >= 7) return 'high';
    if (score >= 4) return 'medium';
    return 'low';
  }

  function getAggressionLabel(score) {
    const level = getAggressionLevel(score);
    if (level === 'high') return 'High Pressure';
    if (level === 'medium') return 'Medium Pressure';
    if (level === 'low') return 'Low Pressure';
    return 'Unknown';
  }

  function getAdStatus(ad) {
    if (ad.is_decoy) return 'decoy';
    if (ad.cloak_detected) return 'cloaked';
    if (ad.is_real_nutra) return 'real';
    if (ad.status === 'active') return 'active';
    if (ad.status === 'inactive') return 'inactive';
    return 'unknown';
  }

  function getStatusLabel(status) {
    const map = {
      active: 'Active', inactive: 'Inactive', cloaked: 'Cloaked',
      decoy: 'Decoy Page', real: 'Real Nutra', unknown: 'Unknown',
    };
    return map[status] || status;
  }

  function getStatusBadgeClass(status) {
    const map = {
      active: 'badge-active', inactive: 'badge-inactive',
      cloaked: 'badge-cloaked', decoy: 'badge-decoy',
      real: 'badge-real', unknown: 'badge-unknown',
    };
    return map[status] || 'badge-unknown';
  }

  /* ============================================================
     API CLIENT
  ============================================================ */

  async function apiGet(path, params) {
    let url = `${API_BASE}${path}`;
    if (params) {
      const q = new URLSearchParams(
        Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined)
      ).toString();
      if (q) url += '?' + q;
    }
    const res = await fetch(url);
    if (!res.ok) {
      const err = await res.text().catch(() => 'Unknown error');
      throw new Error(`API ${res.status}: ${err}`);
    }
    return res.json();
  }

  async function apiPost(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    });
    if (!res.ok) {
      const err = await res.text().catch(() => 'Unknown error');
      throw new Error(`API ${res.status}: ${err}`);
    }
    return res.json();
  }

  async function apiDelete(path) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) {
      const err = await res.text().catch(() => 'Unknown error');
      throw new Error(`API ${res.status}: ${err}`);
    }
    return res.json();
  }

  async function checkBackendHealth() {
    try {
      const data = await apiGet('/health');
      state.backendOk = true;
      if (data.browser_pool) {
        state.browserPool = data.browser_pool;
      }
      updateBackendStatus(true, data.browser_pool);
      return data;
    } catch {
      state.backendOk = false;
      updateBackendStatus(false);
      return null;
    }
  }

  function updateBackendStatus(ok, pool) {
    const dot = els.backendDot;
    if (dot) {
      dot.className = `dot ${ok ? 'ok' : 'err'}`;
    }
    if (pool) {
      if (els.browserDot) {
        els.browserDot.className = `dot ${pool.available > 0 ? 'ok' : 'warn'}`;
      }
      if (els.browserCount) {
        els.browserCount.textContent = `${pool.available}/${pool.total} browsers`;
      }
      if (els.browserPoolStatus) {
        els.browserPoolStatus.textContent = `Pool: ${pool.available}/${pool.total} available`;
      }
    }
  }

  /* ============================================================
     DATA LOADING
  ============================================================ */

  async function loadAds() {
    state.isLoading = true;
    state.loadError = null;
    renderAdGrid();

    try {
      let data;
      if (state.activeTab === 'scraped') {
        data = await apiGet('/api/ads', {
          saved_only: state.filters.savedOnly ? '1' : '',
          limit: 200,
          offset: 0,
        });
      } else {
        const q = state.searchQuery.trim();
        if (q) {
          data = await apiGet('/api/ads/search', {
            q: q,
            country: 'US',
          });

          // Friendly error when Meta blocks the search
          if ((!data.ads || data.ads.length === 0) && state.ads.length === 0) {
            state.loadError = null; // suppress generic error
            state.isLoading = false;
            renderAdGrid();
            // Show a friendly message via notification
            showNotification(
              'Meta blocked the search request. Try scraping a specific page URL instead, or use the Auto Scrape feature.',
              'warning',
              6000
            );
            return;
          }
        } else {
          data = await apiGet('/api/ads', {
            category: state.filters.category,
            status: state.filters.status,
            saved_only: state.filters.savedOnly ? '1' : '',
            limit: 200,
            offset: 0,
          });
        }
      }

      state.ads = data.ads || [];
      applyFilters();
      updateStats();
    } catch (err) {
      // Check if this looks like a Meta block
      const isMetaBlock = err.message.includes('503') ||
        err.message.toLowerCase().includes('blocked') ||
        err.message.toLowerCase().includes('forbidden');

      if (isMetaBlock && state.activeTab === 'search' && state.searchQuery.trim()) {
        showNotification(
          'Meta blocked the search request. Try scraping a specific page URL instead, or use the Auto Scrape feature.',
          'warning',
          6000
        );
      }
      state.loadError = err.message;
      state.isLoading = false;
      renderAdGrid();
    }
  }

  async function fetchAdDetail(id) {
    try {
      const data = await apiGet(`/api/ads/${id}`);
      state.selectedAdDetail = data.ad || data;
      return state.selectedAdDetail;
    } catch {
      return null;
    }
  }

  async function fetchRipList(adId) {
    try {
      const data = await apiGet(`/api/rip/ad/${adId}`);
      if (data && data.id) {
        state.ripList = [data];
      } else {
        state.ripList = [];
      }
    } catch {
      state.ripList = [];
    }
  }

  async function saveAd(adId) {
    try {
      await apiPost(`/api/ads/${adId}/save`, {});
      const ad = state.ads.find(a => String(a.id) === String(adId));
      if (ad) {
        ad.saved = !ad.saved;
      }
      if (state.selectedAd && String(state.selectedAd.id) === String(adId)) {
        state.selectedAd.saved = !state.selectedAd.saved;
        renderDetailSaveBtn();
      }
      applyFilters();
      updateStats();
      const adCard = document.querySelector(`.ad-card[data-id="${adId}"]`);
      if (adCard) {
        adCard.classList.toggle('is-saved', ad?.saved);
        const saveBtn = adCard.querySelector('.save-btn');
        if (saveBtn) {
          saveBtn.classList.toggle('is-saved', ad?.saved);
          saveBtn.innerHTML = ad?.saved
            ? '&#9733; Saved'
            : '&#9734; Save';
        }
      }
      showNotification(`Ad ${ad?.saved ? 'saved' : 'unsaved'}`, 'success');
    } catch (err) {
      showNotification(`Save failed: ${err.message}`, 'error');
    }
  }

  async function deleteAd(adId) {
    if (!confirm('Delete this ad from the database?')) return;
    try {
      await apiDelete(`/api/ads/${adId}`);
      state.ads = state.ads.filter(a => String(a.id) !== String(adId));
      if (state.selectedAd && String(state.selectedAd.id) === String(adId)) {
        closeDetail();
      }
      applyFilters();
      updateStats();
      showNotification('Ad deleted', 'success');
    } catch (err) {
      showNotification(`Delete failed: ${err.message}`, 'error');
    }
  }

  async function ripLander(adId, url, fbclid, device, proxy) {
    state.ripStatus = { loading: true, error: null, data: null };
    renderRipStatus();

    try {
      const data = await apiPost('/api/rip', {
        ad_id: adId,
        url: url,
        fbclid: fbclid || '',
        device: device,
        proxy: proxy || '',
      });

      state.ripStatus = { loading: false, error: null, data };
      renderRipResult(data);
      showNotification(
        data.success
          ? `Lander ripped successfully${data.cloak_detected ? ' — CLOAKED' : ''}`
          : `Rip failed: ${data.error || 'Unknown error'}`,
        data.success ? 'success' : 'error'
      );
    } catch (err) {
      state.ripStatus = { loading: false, error: err.message, data: null };
      renderRipStatus();
      showNotification(`Rip failed: ${err.message}`, 'error');
    }
  }

  async function classifyAd(adId) {
    state.classifyStatus = { loading: true, error: null, data: null };
    renderClassifyStatus();

    try {
      const data = await apiPost(`/api/classify/${adId}`, {});

      // Update ad record with classification
      const ad = state.ads.find(a => String(a.id) === String(adId));
      if (ad) {
        Object.assign(ad, {
          is_decoy: data.is_decoy,
          is_real_nutra: data.is_real_nutra,
          cloak_status: data.cloak_status,
          landing_url_clean: data.landing_url_clean,
          landing_url_actual: data.landing_url_actual,
          cloak_type: data.cloak_type,
          domains_differ: data.domains_differ,
          expected_domain: data.expected_domain,
          actual_domain: data.actual_domain,
          nutra_categories: data.nutra_categories,
          top_category: data.top_category,
          aggression_score: data.aggression_score,
          hook_type: data.hook_type,
          matched_keywords: data.matched_keywords,
          fbclid_used: data.fbclid_used,
          proxy_used: data.proxy_used,
          classification_done: true,
        });
      }

      state.classifyStatus = { loading: false, error: null, data };
      renderClassifyStatus();
      renderDetailInfo();
      applyFilters();
      showNotification(
        `${data.is_decoy ? 'DECOY PAGE' : data.is_real_nutra ? 'REAL NUTRA' : 'Unknown'} — ${data.top_category || 'Uncategorized'}`,
        data.is_decoy ? 'error' : data.is_real_nutra ? 'success' : 'info'
      );
    } catch (err) {
      state.classifyStatus = { loading: false, error: err.message, data: null };
      renderClassifyStatus();
      showNotification(`Classification failed: ${err.message}`, 'error');
    }
  }

  /* ============================================================
     DEMO DATA
  ============================================================ */

  async function loadDemoData() {
    if (!els.loadDemoBtn) return;
    els.loadDemoBtn.disabled = true;
    els.loadDemoBtn.textContent = 'Loading...';
    try {
      const data = await apiPost('/api/ads/demo', {});
      state.ads = data.ads || [];
      state.activeTab = 'scraped';
      els.tabScraped.classList.add('is-active');
      els.tabSearch.classList.remove('is-active');
      applyFilters();
      updateStats();
      showNotification(
        `Loaded ${data.total} demo ads from ${data.message.split(' ')[1]} countries`,
        'success'
      );
    } catch (err) {
      showNotification(`Failed to load demo: ${err.message}`, 'error');
    } finally {
      if (els.loadDemoBtn) {
        els.loadDemoBtn.disabled = false;
        els.loadDemoBtn.textContent = 'LOAD DEMO';
      }
    }
  }

  /* ============================================================
     SCRAPE FUNCTIONS
  ============================================================ */

  async function scrapePage(url, country) {
    const btn = els.scrapeModalRun;
    const spinner = els.scrapeSpinner;
    btn.disabled = true;
    spinner.style.display = 'inline-block';

    try {
      const data = await apiPost('/api/ads/scrape', { page_url: url, country });
      state.ads = data.ads || [];
      state.activeTab = 'scraped';
      els.tabScraped.classList.add('is-active');
      els.tabSearch.classList.remove('is-active');
      closeScrapeModal();
      applyFilters();
      updateStats();
      showNotification(
        `Scraped ${data.total || 0} ads from ${COUNTRY_NAMES[country] || country}`,
        'success'
      );
    } catch (err) {
      showNotification(`Scrape failed: ${err.message}`, 'error');
    } finally {
      btn.disabled = false;
      spinner.style.display = 'none';
    }
  }

  /**
   * Scrape ads across multiple countries.
   * Shows progress updates as each country completes.
   */
  async function scrapeMultiCountries(countries, options = {}) {
    const { keyword = '', baseUrl = '' } = options;
    if (countries.length === 0) {
      showNotification('Please select at least one country', 'warning');
      return;
    }

    state.scrapeInProgress = true;
    setScrapeButtonsDisabled(true);
    showScrapeProgressUI(0, countries.length, countries[0]);

    let totalAds = 0;
    const failedCountries = [];

    for (let i = 0; i < countries.length; i++) {
      const country = countries[i];
      const current = i + 1;
      showScrapeProgressUI(current, countries.length, country);

      try {
        const params = { country };
        if (keyword.trim()) {
          params.keyword = keyword.trim();
        }
        if (baseUrl.trim()) {
          params.page_url = baseUrl.trim();
        }

        const data = await apiPost('/api/ads/scrape', params);
        const count = data.ads ? data.ads.length : (data.total || 0);
        totalAds += count;

        // Merge scraped ads into state
        if (data.ads && data.ads.length > 0) {
          const existingIds = new Set(state.ads.map(a => String(a.id)));
          const newAds = data.ads.filter(a => !existingIds.has(String(a.id)));
          state.ads = [...state.ads, ...newAds];
        }
      } catch (err) {
        failedCountries.push(`${COUNTRY_NAMES[country] || country} (${err.message})`);
      }
    }

    state.scrapeInProgress = false;
    hideScrapeProgressUI();
    setScrapeButtonsDisabled(false);

    state.activeTab = 'scraped';
    els.tabScraped.classList.add('is-active');
    els.tabSearch.classList.remove('is-active');
    closeScrapeModal();
    applyFilters();
    updateStats();

    if (failedCountries.length > 0) {
      showNotification(
        `Scraped ${totalAds} ads across ${countries.length - failedCountries.length}/${countries.length} countries. Failed: ${failedCountries.join(', ')}`,
        'warning',
        8000
      );
    } else {
      showNotification(
        `Scraped ${totalAds} ads across ${countries.length} countries`,
        'success'
      );
    }
  }

  /**
   * Scrape ads across multiple categories (Auto-Category mode).
   * Calls the /api/ads/scrape-multi endpoint.
   */
  async function scrapeAutoCategory(categories, countries) {
    if (categories.length === 0) {
      showNotification('Please select at least one category', 'warning');
      return;
    }
    if (countries.length === 0) {
      showNotification('Please select at least one country', 'warning');
      return;
    }

    state.scrapeInProgress = true;
    setScrapeButtonsDisabled(true);
    showScrapeProgressUI(0, countries.length, 'Building keyword list...');

    try {
      const data = await apiPost('/api/ads/scrape-multi', {
        categories: categories,
        countries: countries,
      });

      const totalAds = data.total || data.ads?.length || 0;

      if (data.ads && data.ads.length > 0) {
        const existingIds = new Set(state.ads.map(a => String(a.id)));
        const newAds = data.ads.filter(a => !existingIds.has(String(a.id)));
        state.ads = [...state.ads, ...newAds];
      }

      state.scrapeInProgress = false;
      hideScrapeProgressUI();
      setScrapeButtonsDisabled(false);
      state.activeTab = 'scraped';
      els.tabScraped.classList.add('is-active');
      els.tabSearch.classList.remove('is-active');
      closeScrapeModal();
      applyFilters();
      updateStats();

      showNotification(
        `Auto-scrape complete: ${totalAds} ads across ${categories.length} categories and ${countries.length} countries`,
        'success'
      );
    } catch (err) {
      state.scrapeInProgress = false;
      hideScrapeProgressUI();
      setScrapeButtonsDisabled(false);
      showNotification(`Auto-scrape failed: ${err.message}`, 'error');
    }
  }

  /* ============================================================
     SCRAPE PROGRESS UI
  ============================================================ */

  function showScrapeProgressUI(current, total, country) {
    els.scrapeProgressArea.style.display = 'block';
    const label = `Scraping ${COUNTRY_NAMES[country] || country} (${current}/${total})...`;
    els.scrapeProgressLabel.textContent = label;
    const pct = total > 0 ? Math.round((current / total) * 100) : 0;
    els.scrapeProgressBar.style.width = pct + '%';
  }

  function hideScrapeProgressUI() {
    els.scrapeProgressArea.style.display = 'none';
    els.scrapeProgressBar.style.width = '0%';
  }

  function setScrapeButtonsDisabled(disabled) {
    els.scrapeModalRun.disabled = disabled;
    if (els.selectAllCountries) els.selectAllCountries.disabled = disabled;
    if (els.clearAllCountries) els.clearAllCountries.disabled = disabled;
    if (els.selectAllCategories) els.selectAllCategories.disabled = disabled;
    if (els.clearAllCategories) els.clearAllCategories.disabled = disabled;
    if (els.selectAllCountriesAuto) els.selectAllCountriesAuto.disabled = disabled;
    if (els.clearAllCountriesAuto) els.clearAllCountriesAuto.disabled = disabled;
  }

  /* ============================================================
     FILTERING & SORTING
  ============================================================ */

  function applyFilters() {
    let ads = [...state.ads];

    // Category filter
    if (state.filters.category) {
      ads = ads.filter(ad => {
        const cats = getNutraCategories(ad);
        return cats.includes(state.filters.category);
      });
    }

    // Status filter
    if (state.filters.status) {
      ads = ads.filter(ad => {
        const s = getAdStatus(ad);
        return s === state.filters.status;
      });
    }

    // Saved only
    if (state.filters.savedOnly) {
      ads = ads.filter(ad => ad.saved);
    }

    // Search (text filter on scraped tab)
    const q = state.searchQuery.trim().toLowerCase();
    if (q && state.activeTab === 'scraped') {
      ads = ads.filter(ad => {
        const page = (ad.page_name || ad.pageName || '').toLowerCase();
        const text = (ad.ad_text || ad.text || ad.adCreativeBody || '').toLowerCase();
        const domain = getDomain(ad.page_url || ad.pageUrl || '').toLowerCase();
        const url = (ad.ad_creative_link_caption || '').toLowerCase();
        return page.includes(q) || text.includes(q) || domain.includes(q) || url.includes(q);
      });
    }

    // Sort
    ads.sort((a, b) => {
      switch (state.filters.sort) {
        case 'newest':
          return (b.created_at || b.createdAt || 0) - (a.created_at || a.createdAt || 0);
        case 'oldest':
          return (a.created_at || a.createdAt || 0) - (b.created_at || b.createdAt || 0);
        case 'score_high':
          return (b.aggression_score || b.aggressionScore || 0) - (a.aggression_score || a.aggressionScore || 0);
        case 'score_low':
          return (a.aggression_score || a.aggressionScore || 0) - (b.aggression_score || b.aggressionScore || 0);
        case 'saved':
          return (b.saved ? 1 : 0) - (a.saved ? 1 : 0);
        default:
          return 0;
      }
    });

    state.filteredAds = ads;
    state.isLoading = false;
    renderAdGrid();
    updateStats();
  }

  function updateStats() {
    const total = state.ads.length;
    const filtered = state.filteredAds.length;
    const saved = state.ads.filter(a => a.saved).length;
    const cloaked = state.ads.filter(a => getAdStatus(a) === 'cloaked').length;
    const active = state.ads.filter(a => getAdStatus(a) === 'active').length;

    els.statTotal.textContent = total;
    els.statActive.textContent = active;
    els.statSaved.textContent = saved;
    els.statCloaked.textContent = cloaked;
    els.resultCountNum.textContent = filtered;

    if (filtered < total && total > 0) {
      els.resultFiltered.style.display = 'inline';
    } else {
      els.resultFiltered.style.display = 'none';
    }
  }

  /* ============================================================
     RENDER: AD GRID
  ============================================================ */

  function renderAdGrid() {
    const grid = els.adGrid;
    grid.classList.remove('loading', 'empty', 'error');

    if (state.isLoading) {
      grid.classList.add('loading');
      grid.innerHTML = `
        <div class="loading-center">
          <div class="spinner"></div>
          <span>Loading ads...</span>
        </div>
      `;
      return;
    }

    if (state.loadError) {
      grid.classList.add('error');
      grid.innerHTML = `
        <div class="error-state">
          <div class="error-title">Failed to load ads</div>
          <div class="error-sub">${escapeHtml(state.loadError)}</div>
          <button class="btn btn-ghost btn-sm" onclick="window._adsrecon.loadAds()">Retry</button>
        </div>
      `;
      return;
    }

    if (state.filteredAds.length === 0) {
      grid.classList.add('empty');
      const msg = state.activeTab === 'scraped'
        ? 'Paste a Meta Ads Library URL and click SCRAPE to fetch ads'
        : 'No ads match the current filters';
      grid.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">&#128269;</div>
          <div class="empty-title">${state.ads.length === 0 ? 'No ads scraped yet' : 'No matches'}</div>
          <div class="empty-sub">${msg}</div>
          ${state.ads.length === 0 ? '<button class="btn btn-primary btn-sm" onclick="document.getElementById(\'scrapeBtn\').click()">Scrape Now</button>' : ''}
        </div>
      `;
      return;
    }

    grid.innerHTML = state.filteredAds.map(ad => renderAdCard(ad)).join('');

    // Bind card events
    grid.querySelectorAll('.ad-card').forEach(card => {
      card.addEventListener('click', (e) => {
        if (e.target.closest('.save-btn')) {
          e.stopPropagation();
          saveAd(card.dataset.id);
          return;
        }
        if (e.target.closest('.rip-mini-btn')) {
          e.stopPropagation();
          const url = card.dataset.url || card.dataset.pageUrl || '';
          selectAd(card.dataset.id, url);
          return;
        }
        const url = card.dataset.url || card.dataset.pageUrl || '';
        selectAd(card.dataset.id, url);
      });
    });
  }

  function renderAdCard(ad) {
    const id = ad.id;
    const pageName = escapeHtml(ad.page_name || ad.pageName || 'Unknown Page');
    const adText = escapeHtml(truncate(ad.ad_text || ad.text || ad.adCreativeBody || '', 120));
    const thumb = ad.thumbnail_url || ad.thumbnailUrl || ad.image_url || ad.imageUrl || '';
    const hasVideo = !!(ad.video_url || ad.videoUrl || ad.video_url_list);
    const saved = !!ad.saved;
    const status = getAdStatus(ad);
    const statusLabel = getStatusLabel(status);
    const statusClass = getStatusBadgeClass(status);
    const categories = getNutraCategories(ad);
    const ctaText = escapeHtml(ad.ad_creative_link_caption || ad.cta_text || ad.call_to_action || '');
    const url = ad.page_url || ad.pageUrl || '';
    const selected = state.selectedAd && String(state.selectedAd.id) === String(id);

    let thumbHtml;
    if (thumb) {
      thumbHtml = `<img src="${escapeHtml(thumb)}" alt="Ad thumbnail" loading="lazy" onerror="this.parentElement.innerHTML='<div class=\\'thumb-placeholder\\'>No Image</div>'" />`;
    } else {
      thumbHtml = `<div class="thumb-placeholder">No Thumbnail</div>`;
    }

    let catChips = '';
    if (categories.length > 0) {
      const displayCats = categories.slice(0, 2);
      catChips = displayCats.map(c => {
        const cat = NUTRA_CATEGORIES[c];
        if (!cat) return '';
        return `<span class="nutra-chip" style="color:${cat.color};border-color:${cat.color}40;background:${cat.bg}">${escapeHtml(cat.label)}</span>`;
      }).join('');
    }

    return `
      <article class="ad-card${saved ? ' is-saved' : ''}${selected ? ' is-selected' : ''}"
        data-id="${id}"
        data-url="${escapeHtml(url)}"
        data-page-url="${escapeHtml(url)}">
        <div class="ad-card-thumb">
          ${thumbHtml}
          ${hasVideo ? '<div class="video-badge">&#9654; Video</div>' : ''}
        </div>
        <div class="ad-card-body">
          <div class="ad-card-page" title="${pageName}">${pageName}</div>
          <div class="ad-card-text">${adText || '<em style="color:var(--text-muted)">No ad text</em>'}</div>
          <div class="ad-card-footer">
            ${ctaText ? `<span class="badge badge-cta">${escapeHtml(ctaText)}</span>` : ''}
            <span class="badge ${statusClass}">${escapeHtml(statusLabel)}</span>
            ${catChips}
          </div>
        </div>
        <div class="ad-card-actions">
          <button class="save-btn${saved ? ' is-saved' : ''}" data-id="${id}" title="${saved ? 'Unsave' : 'Save'}">
            ${saved ? '&#9733; Saved' : '&#9734; Save'}
          </button>
          <button class="rip-mini-btn" data-id="${id}">&#128247; Rip</button>
        </div>
      </article>
    `;
  }

  /* ============================================================
     RENDER: DETAIL PANEL
  ============================================================ */

  function renderDetailSaveBtn() {
    if (!state.selectedAd) return;
    const btn = els.detailSaveBtn;
    const saved = !!state.selectedAd.saved;
    btn.innerHTML = `${saved ? '&#9733;' : '&#9734;'} ${saved ? 'Saved' : 'Save'}`;
  }

  function selectAd(id, url) {
    const ad = state.ads.find(a => String(a.id) === String(id));
    if (!ad) return;

    state.selectedAd = ad;
    state.ripStatus = null;
    state.classifyStatus = null;
    state.previewMode = 'iframe';

    $$('.ad-card').forEach(c => c.classList.remove('is-selected'));
    const card = document.querySelector(`.ad-card[data-id="${id}"]`);
    if (card) card.classList.add('is-selected');

    els.mainLayout.classList.remove('detail-closed');
    els.mainLayout.classList.add('detail-open');
    els.detailPanel.classList.add('is-open');

    hidePreview();
    els.previewEmpty.style.display = 'flex';
    els.previewLoading.style.display = 'none';

    renderDetailInfo();

    fetchAdDetail(id);
    fetchRipList(id);

    els.detailPageName.textContent = ad.page_name || ad.pageName || 'Ad Detail';

    fetchAdDetail(id).then(detail => {
      if (detail && state.selectedAd && String(state.selectedAd.id) === String(id)) {
        state.selectedAdDetail = detail;
        renderDetailInfo();
      }
    });

    fetchRipList(id).then(() => {
      if (state.selectedAd) {
        renderRips();
      }
    });
  }

  function closeDetail() {
    els.mainLayout.classList.add('detail-closed');
    els.mainLayout.classList.remove('detail-open');
    els.detailPanel.classList.remove('is-open');
    state.selectedAd = null;
    state.selectedAdDetail = null;
    state.ripStatus = null;
    state.classifyStatus = null;
    $$('.ad-card').forEach(c => c.classList.remove('is-selected'));
  }

  function renderDetailInfo() {
    const ad = state.selectedAd;
    if (!ad) return;

    els.detailPageName.textContent = ad.page_name || ad.pageName || 'Ad Detail';
    els.detailText.textContent = ad.ad_text || ad.text || ad.adCreativeBody || 'No ad text available.';

    renderDetailUrls(ad);
    renderDetailThumbs(ad);
    renderDetailVideo(ad);
    renderDetailClassification(ad);

    if (ad.hook_type) {
      els.detailHook.style.display = 'flex';
      els.detailHookType.textContent = ad.hook_type;
    } else {
      els.detailHook.style.display = 'none';
    }

    if (ad.matched_keywords && ad.matched_keywords.length > 0) {
      els.detailKeywords.style.display = 'flex';
      els.detailMatchedKeywords.innerHTML = ad.matched_keywords.map(k =>
        `<span class="nutra-chip" style="color:var(--accent-yellow);border-color:rgba(255,170,0,0.4);background:rgba(255,170,0,0.1)">${escapeHtml(k)}</span>`
      ).join('');
    } else {
      els.detailKeywords.style.display = 'none';
    }

    renderDetailSaveBtn();
  }

  function renderDetailUrls(ad) {
    const cleanUrl = ad.landing_url_clean || ad.clean_url || ad.ad_creative_link || ad.page_url || ad.pageUrl || '';
    const actualUrl = ad.landing_url_actual || ad.actual_url || ad.url || '';
    const differ = ad.domains_differ || (cleanUrl && actualUrl && domainsDiffer(cleanUrl, actualUrl));
    const cloakDetected = ad.cloak_detected || ad.cloak_status === 'cloaked' || differ;

    let html = '';

    if (cleanUrl) {
      html += `
        <div class="cloak-diff ${cloakDetected && differ ? 'clean' : 'neutral'}">
          <div class="cloak-diff-label">Clean URL (shown to Meta)</div>
          <div class="cloak-diff-url">${escapeHtml(cleanUrl)}</div>
        </div>
      `;
    }

    if (actualUrl && actualUrl !== cleanUrl) {
      html += `
        <div class="cloak-diff ${differ ? 'actual' : 'neutral'}">
          <div class="cloak-diff-label">Actual URL (after redirect)</div>
          <div class="cloak-diff-url">${escapeHtml(actualUrl)}</div>
        </div>
      `;
    }

    if (!html) {
      const pageUrl = ad.page_url || ad.pageUrl || '';
      if (pageUrl) {
        html = `
          <div class="url-block">
            <div class="url-label">Page URL</div>
            <div class="url-value"><a href="${escapeHtml(pageUrl)}" target="_blank" rel="noopener">${escapeHtml(truncate(pageUrl, 80))}</a></div>
          </div>
        `;
      }
    }

    els.detailUrls.innerHTML = html;
  }

  function renderDetailThumbs(ad) {
    const thumbs = ad.thumbnail_url || ad.thumbnailUrl || ad.image_url || ad.imageUrl || '';

    if (!thumbs) {
      els.detailThumbs.style.display = 'none';
      return;
    }

    els.detailThumbs.style.display = 'flex';
    const thumbArr = Array.isArray(thumbs) ? thumbs : [thumbs];
    els.detailThumbGallery.innerHTML = thumbArr.map(t =>
      `<img src="${escapeHtml(t)}" alt="Thumbnail" style="width:80px;height:60px;object-fit:cover;border-radius:6px;border:1px solid var(--border-subtle);cursor:pointer;" onclick="window._adsrecon.previewImage('${escapeHtml(t)}')" />`
    ).join('');
  }

  function renderDetailVideo(ad) {
    const videoUrl = ad.video_url || ad.videoUrl ||
      (Array.isArray(ad.video_urls) ? ad.video_urls[0] : null) ||
      (Array.isArray(ad.video_url_list) ? ad.video_url_list[0] : null);

    if (!videoUrl) {
      els.detailVideo.style.display = 'none';
      return;
    }

    els.detailVideo.style.display = 'flex';
    els.detailVideoPlaceholder.innerHTML = `
      <video controls style="width:100%;height:100%;border:none;" preload="metadata">
        <source src="${escapeHtml(videoUrl)}" />
        Your browser does not support video.
      </video>
    `;
  }

  function renderDetailClassification(ad) {
    const cats = getNutraCategories(ad);
    const topCat = ad.top_category || (cats.length > 0 ? cats[0] : '');
    const score = ad.aggression_score || ad.aggressionScore;
    const level = getAggressionLevel(score);

    if (cats.length > 0) {
      els.detailNutraChips.innerHTML = cats.map(c => {
        const cat = NUTRA_CATEGORIES[c];
        if (!cat) return `<span class="nutra-chip">${escapeHtml(c)}</span>`;
        return `<span class="nutra-chip" style="color:${cat.color};border-color:${cat.color}40;background:${cat.bg}">${escapeHtml(cat.label)}</span>`;
      }).join('');
      els.detailNutraChips.parentElement.querySelector('.detail-section-title').textContent = 'Nutra Categories';
    } else {
      els.detailNutraChips.innerHTML = '<span style="font-size:12px;color:var(--text-muted)">No categories detected</span>';
      els.detailNutraChips.parentElement.querySelector('.detail-section-title').textContent = 'Classification';
    }

    const status = getAdStatus(ad);
    const badges = [];

    if (ad.cloak_detected || ad.cloak_status === 'cloaked') {
      badges.push(`<span class="badge badge-cloaked">&#128274; Cloaked</span>`);
    }
    if (ad.is_decoy) {
      badges.push(`<span class="badge badge-decoy">&#128127; Decoy</span>`);
    }
    if (ad.is_real_nutra) {
      badges.push(`<span class="badge badge-real">&#9989; Real Nutra</span>`);
    }
    badges.push(`<span class="badge ${getStatusBadgeClass(status)}">${escapeHtml(getStatusLabel(status))}</span>`);

    els.detailBadgeRow.innerHTML = badges.join('');

    if (score !== null && score !== undefined) {
      els.detailAggression.innerHTML = `
        <div class="aggression-meter">
          <div class="detail-section-title" style="margin-bottom:4px;">Aggression Score</div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="class-stat-value ${level || ''}" style="font-size:28px;">${score}</span>
            <span style="font-size:11px;color:var(--text-secondary)">/ 10</span>
            <span class="badge ${level === 'high' ? 'badge-cloaked' : level === 'medium' ? 'badge-decoy' : 'badge-active'}">${escapeHtml(getAggressionLabel(score))}</span>
          </div>
          <div class="aggression-bar-wrap" style="margin-top:6px;">
            <div class="aggression-bar ${level || ''}" style="width:${Math.min(100, score * 10)}%"></div>
          </div>
          ${ad.hook_type ? `<div style="font-size:11px;color:var(--text-muted);margin-top:4px;">Hook: ${escapeHtml(ad.hook_type)}</div>` : ''}
        </div>
      `;
    } else {
      els.detailAggression.innerHTML = `
        <div class="aggression-meter">
          <div class="detail-section-title">Aggression Score</div>
          <div style="font-size:12px;color:var(--text-muted);">Not yet classified — click "Classify Ad"</div>
        </div>
      `;
    }
  }

  /* ============================================================
     RENDER: PREVIEW & RIP
  ============================================================ */

  function hidePreview() {
    els.previewIframe.style.display = 'none';
    els.previewImage.style.display = 'none';
    els.previewLoading.style.display = 'none';
    els.previewToolbar.style.display = 'none';
    els.previewEmpty.style.display = 'none';
  }

  function showPreviewIframe(url) {
    hidePreview();
    els.previewToolbar.style.display = 'flex';
    els.previewUrl.textContent = truncate(url, 60);
    els.previewIframe.style.display = 'block';
    els.previewIframe.src = url;
  }

  function showPreviewImage(src) {
    hidePreview();
    els.previewImage.style.display = 'block';
    els.previewImage.src = src;
    els.previewImage.onerror = () => {
      els.previewImage.style.display = 'none';
      els.previewEmpty.style.display = 'flex';
      els.previewEmpty.innerHTML = `<span>Image failed to load</span>`;
    };
  }

  window._adsrecon = window._adsrecon || {};
  window._adsrecon.previewImage = showPreviewImage;

  function renderRipStatus() {
    if (state.ripStatus?.loading) {
      els.ripSpinner.style.display = 'inline-block';
      els.ripLanderBtn.disabled = true;
      hidePreview();
      els.previewLoading.style.display = 'flex';
      els.previewLoading.innerHTML = `<div class="spinner"></div><span>Ripping lander (${state.ripDevice})...</span>`;
      return;
    }

    els.ripSpinner.style.display = 'none';
    els.ripLanderBtn.disabled = false;

    if (state.ripStatus?.error) {
      hidePreview();
      els.previewEmpty.style.display = 'flex';
      els.previewEmpty.innerHTML = `<span style="color:var(--accent-red)">Error: ${escapeHtml(state.ripStatus.error)}</span>`;
    }
  }

  function renderRipResult(data) {
    els.ripSpinner.style.display = 'none';
    els.ripLanderBtn.disabled = false;

    if (!data) {
      hidePreview();
      els.previewEmpty.style.display = 'flex';
      return;
    }

    if (data.screenshot_path) {
      const screenshotUrl = data.screenshot_path.startsWith('http')
        ? data.screenshot_path
        : `${API_BASE}/${data.screenshot_path}`;
      showPreviewImage(screenshotUrl);
    } else if (data.html_path) {
      const htmlUrl = data.html_path.startsWith('http')
        ? data.html_path
        : `${API_BASE}/${data.html_path}`;
      showPreviewIframe(htmlUrl);
    } else {
      hidePreview();
      els.previewEmpty.style.display = 'flex';
    }

    if (data.cloak_detected) {
      showNotification(`Cloak detected — ${data.cloak_type || 'Unknown type'}`, 'error', 6000);
    }
  }

  function renderClassifyStatus() {
    if (state.classifyStatus?.loading) {
      els.classifySpinner.style.display = 'inline-block';
      els.classifyBtn.disabled = true;
      els.classifyResults.style.display = 'none';
      return;
    }

    els.classifySpinner.style.display = 'none';
    els.classifyBtn.disabled = false;

    if (!state.classifyStatus?.data) {
      els.classifyResults.style.display = 'none';
      return;
    }

    const d = state.classifyStatus.data;
    els.classifyResults.style.display = 'flex';

    let html = `
      <div class="cloak-diff ${d.is_decoy ? 'actual' : 'clean'}">
        <div class="cloak-diff-label">${d.is_decoy ? 'DECOY PAGE' : d.is_real_nutra ? 'REAL NUTRA' : 'UNKNOWN'}</div>
      </div>
      <div class="classification-grid">
        <div class="class-stat">
          <div class="class-stat-label">Cloak Status</div>
          <div class="class-stat-value" style="font-size:14px;color:${d.cloak_detected ? 'var(--accent-red)' : 'var(--accent-green)'}">${escapeHtml(d.cloak_status || 'None')}</div>
        </div>
        <div class="class-stat">
          <div class="class-stat-label">Aggression</div>
          <div class="class-stat-value ${getAggressionLevel(d.aggression_score) || ''}" style="font-size:22px;">${d.aggression_score ?? '?'}</div>
        </div>
        <div class="class-stat">
          <div class="class-stat-label">Top Category</div>
          <div class="class-stat-value" style="font-size:12px;">${escapeHtml(d.top_category || 'N/A')}</div>
        </div>
        <div class="class-stat">
          <div class="class-stat-label">Hook Type</div>
          <div class="class-stat-value" style="font-size:12px;">${escapeHtml(d.hook_type || 'N/A')}</div>
        </div>
      </div>
    `;

    if (d.domains_differ) {
      html += `
        <div class="cloak-diff actual" style="margin-top:6px;">
          <div class="cloak-diff-label">URL Mismatch Detected</div>
          <div style="font-size:11px;color:var(--text-muted);margin-top:3px;">
            Expected: ${escapeHtml(d.expected_domain || 'N/A')} &rarr; Actual: ${escapeHtml(d.actual_domain || 'N/A')}
          </div>
        </div>
      `;
    }

    els.classifyResultsBody.innerHTML = html;
  }

  function renderRips() {
    if (state.ripList.length === 0) {
      els.ripsList.innerHTML = '';
      els.ripsEmpty.style.display = 'flex';
      return;
    }

    els.ripsEmpty.style.display = 'none';
    els.ripsList.innerHTML = state.ripList.map(rip => `
      <div class="cloak-diff ${rip.cloak_detected ? 'actual' : 'clean'}" style="margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
          <div class="cloak-diff-label" style="margin:0;">
            ${rip.cloak_detected ? '&#128274; Cloaked' : '&#9989; Clean'} — ${escapeHtml(rip.device_used || 'Unknown')}
          </div>
          <div style="font-size:10px;color:var(--text-muted);">${formatDate(rip.accessed_at)}</div>
        </div>
        ${rip.final_url ? `<div class="cloak-diff-url" style="margin-bottom:4px;">${escapeHtml(rip.final_url)}</div>` : ''}
        ${rip.video_urls && rip.video_urls.length > 0 ? `<div style="margin-top:4px;"><span style="font-size:10px;color:var(--text-muted)">Videos: </span>${rip.video_urls.length}</div>` : ''}
        <div style="display:flex;gap:5px;margin-top:6px;">
          ${rip.screenshot_path ? `<button class="btn btn-ghost btn-sm" onclick="window._adsrecon.showRipImage('${escapeHtml(rip.screenshot_path.startsWith('http') ? rip.screenshot_path : API_BASE + '/' + rip.screenshot_path)}')">Screenshot</button>` : ''}
          ${rip.html_path ? `<button class="btn btn-ghost btn-sm" onclick="window._adsrecon.showRipHtml('${escapeHtml(rip.html_path.startsWith('http') ? rip.html_path : API_BASE + '/' + rip.html_path)}')">HTML</button>` : ''}
        </div>
      </div>
    `).join('');
  }

  window._adsrecon.showRipImage = (url) => {
    switchDetailTab('preview');
    showPreviewImage(url);
  };

  window._adsrecon.showRipHtml = (url) => {
    switchDetailTab('preview');
    showPreviewIframe(url);
  };

  /* ============================================================
     RENDER: FILTERS
  ============================================================ */

  function renderFilters() {
    els.categoryList.innerHTML = `
      <label class="category-item${!state.filters.category ? ' is-active' : ''}" data-category="">
        <input type="radio" name="categoryFilter" value="" ${!state.filters.category ? 'checked' : ''} style="display:none" />
        <span class="category-dot" style="background:var(--text-muted)"></span>
        <span>All Categories</span>
      </label>
      ${Object.entries(NUTRA_CATEGORIES).map(([key, cat]) => {
        const count = state.ads.filter(ad => getNutraCategories(ad).includes(key)).length;
        return `
          <label class="category-item${state.filters.category === key ? ' is-active' : ''}" data-category="${key}">
            <input type="radio" name="categoryFilter" value="${key}" ${state.filters.category === key ? 'checked' : ''} style="display:none" />
            <span class="category-dot" style="background:${cat.color}"></span>
            <span>${escapeHtml(cat.label)}</span>
            ${count > 0 ? `<span class="category-count">${count}</span>` : ''}
          </label>
        `;
      }).join('')}
    `;

    els.categoryList.querySelectorAll('.category-item').forEach(item => {
      item.addEventListener('click', () => {
        els.categoryList.querySelectorAll('.category-item').forEach(i => i.classList.remove('is-active'));
        item.classList.add('is-active');
        state.filters.category = item.dataset.category;
        applyFilters();
      });
    });
  }

  function renderStatusFilters() {
    els.statusOptions.querySelectorAll('.status-option').forEach(opt => {
      opt.addEventListener('click', () => {
        els.statusOptions.querySelectorAll('.status-option').forEach(o => o.classList.remove('is-active'));
        opt.classList.add('is-active');
        state.filters.status = opt.dataset.status;
        applyFilters();
      });
    });
  }

  /* ============================================================
     EXPORT
  ============================================================ */

  function exportCsv() {
    const ads = state.filteredAds;
    if (ads.length === 0) {
      showNotification('No ads to export', 'info');
      return;
    }

    const headers = ['ID', 'Page Name', 'Ad Text', 'Page URL', 'CTA', 'Status', 'Saved', 'Aggression Score', 'Top Category', 'Hook Type', 'Cloak Detected', 'Is Decoy', 'Is Real Nutra', 'Created'];
    const rows = ads.map(ad => [
      ad.id,
      (ad.page_name || ad.pageName || '').replace(/"/g, '""'),
      (ad.ad_text || ad.text || '').replace(/"/g, '""'),
      ad.page_url || ad.pageUrl || '',
      ad.ad_creative_link_caption || ad.cta_text || '',
      getAdStatus(ad),
      ad.saved ? 'Yes' : 'No',
      ad.aggression_score || ad.aggressionScore || '',
      ad.top_category || '',
      ad.hook_type || '',
      ad.cloak_detected ? 'Yes' : 'No',
      ad.is_decoy ? 'Yes' : 'No',
      ad.is_real_nutra ? 'Yes' : 'No',
      ad.created_at || ad.createdAt || '',
    ]);

    const csv = [headers.join(','), ...rows.map(r => r.map(v => `"${v}"`).join(','))].join('\n');
    downloadFile('adsrecon_export.csv', csv, 'text/csv');
    showNotification(`Exported ${ads.length} rows to CSV`, 'success');
  }

  function exportJson() {
    const ads = state.filteredAds;
    if (ads.length === 0) {
      showNotification('No ads to export', 'info');
      return;
    }

    const json = JSON.stringify(ads, null, 2);
    downloadFile('adsrecon_export.json', json, 'application/json');
    showNotification(`Exported ${ads.length} ads to JSON`, 'success');
  }

  function downloadFile(filename, content, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  /* ============================================================
     SCRAPE MODAL
  ============================================================ */

  function openScrapeModal(tab = 'single') {
    els.scrapeModal.style.display = 'block';
    els.scrapeModalOverlay.style.display = 'flex';
    els.modalPageUrl.value = '';
    els.modalCountry.value = 'US';
    els.modalMultiKeyword.value = '';
    els.modalMultiPageUrl.value = '';
    els.scrapeSpinner.style.display = 'none';
    els.scrapeModalRun.disabled = false;
    els.scrapeModalRunLabel.textContent = 'Start Scrape';
    hideScrapeProgressUI();

    // Reset category selection
    state.selectedCategories.clear();
    renderCategoryCheckboxGrid();
    renderAutoCountryCheckboxGrid();
    renderCountryCheckboxGrid();

    switchScrapeTab(tab);
    setTimeout(() => els.modalPageUrl.focus(), 50);
  }

  function closeScrapeModal() {
    els.scrapeModal.style.display = 'none';
    els.scrapeModalOverlay.style.display = 'none';
  }

  function switchScrapeTab(tab) {
    state.scrapeTab = tab;

    // Update tab buttons
    els.scrapeModalBox.querySelectorAll('.modal-tab').forEach(t => {
      t.classList.toggle('is-active', t.dataset.scrapeTab === tab);
    });

    // Show/hide tab content
    const tabMap = { single: 'scrapeTabSingle', multi: 'scrapeTabMulti', auto: 'scrapeTabAuto' };
    Object.entries(tabMap).forEach(([key, id]) => {
      const el = getEl(id);
      if (el) el.style.display = key === tab ? 'block' : 'none';
    });

    // Update title and button label
    const titleMap = {
      single: 'Scrape Meta Ads Library',
      multi: 'Multi-Country Scrape',
      auto: 'Auto Scrape by Category',
    };
    const btnMap = {
      single: 'Start Scrape',
      multi: 'Start Multi-Country Scrape',
      auto: 'Scrape All',
    };
    if (els.scrapeModalTitle) els.scrapeModalTitle.textContent = titleMap[tab] || 'Scrape';
    if (els.scrapeModalRunLabel) els.scrapeModalRunLabel.textContent = btnMap[tab] || 'Start Scrape';
  }

  /* ============================================================
     CHECKBOX GRIDS (rendered by JS)
  ============================================================ */

  function renderCountryCheckboxGrid() {
    if (!els.countryCheckboxGrid) return;
    els.countryCheckboxGrid.innerHTML = COUNTRY_LIST.map(code => {
      const checked = state.selectedCountries.has(code) ? 'checked' : '';
      return `
        <label class="checkbox-item">
          <input type="checkbox" value="${code}" ${checked} />
          <span class="checkbox-label">${escapeHtml(COUNTRY_NAMES[code])}</span>
        </label>
      `;
    }).join('');

    els.countryCheckboxGrid.querySelectorAll('input[type="checkbox"]').forEach(cb => {
      cb.addEventListener('change', () => {
        if (cb.checked) {
          state.selectedCountries.add(cb.value);
        } else {
          state.selectedCountries.delete(cb.value);
        }
      });
    });
  }

  function renderAutoCountryCheckboxGrid() {
    if (!els.autoCountryCheckboxGrid) return;
    els.autoCountryCheckboxGrid.innerHTML = COUNTRY_LIST.map(code => {
      const checked = state.selectedCountries.has(code) ? 'checked' : '';
      return `
        <label class="checkbox-item">
          <input type="checkbox" value="${code}" ${checked} />
          <span class="checkbox-label">${escapeHtml(COUNTRY_NAMES[code])}</span>
        </label>
      `;
    }).join('');

    els.autoCountryCheckboxGrid.querySelectorAll('input[type="checkbox"]').forEach(cb => {
      cb.addEventListener('change', () => {
        if (cb.checked) {
          state.selectedCountries.add(cb.value);
        } else {
          state.selectedCountries.delete(cb.value);
        }
      });
    });
  }

  function renderCategoryCheckboxGrid() {
    if (!els.categoryCheckboxGrid) return;
    els.categoryCheckboxGrid.innerHTML = Object.entries(NUTRA_CATEGORIES).map(([key, cat]) => {
      const checked = state.selectedCategories.has(key) ? 'checked' : '';
      return `
        <label class="checkbox-item cat-checkbox">
          <input type="checkbox" value="${key}" ${checked} />
          <span class="cat-dot" style="background:${cat.color}"></span>
          <span class="checkbox-label">${escapeHtml(cat.label)}</span>
        </label>
      `;
    }).join('');

    els.categoryCheckboxGrid.querySelectorAll('input[type="checkbox"]').forEach(cb => {
      cb.addEventListener('change', () => {
        if (cb.checked) {
          state.selectedCategories.add(cb.value);
        } else {
          state.selectedCategories.delete(cb.value);
        }
      });
    });
  }

  /* ============================================================
     TAB SWITCHING
  ============================================================ */

  function switchMainTab(tab) {
    state.activeTab = tab;
    els.tabSearch.classList.remove('is-active');
    els.tabScraped.classList.remove('is-active');
    els.tabDemo && els.tabDemo.classList.remove('is-active');

    if (tab === 'search') {
      els.tabSearch.classList.add('is-active');
      state.searchQuery = '';
      els.searchInput.value = '';
      loadAds();
    } else if (tab === 'scraped') {
      els.tabScraped.classList.add('is-active');
      state.searchQuery = '';
      els.searchInput.value = '';
      loadAds();
    } else if (tab === 'demo') {
      els.tabDemo && els.tabDemo.classList.add('is-active');
      state.searchQuery = '';
      els.searchInput.value = '';
      // Load demo data into the scraped tab
      loadDemoData();
    }
  }

  function switchDetailTab(tab) {
    state.activeDetailTab = tab;
    els.tabInfo.style.display = tab === 'info' ? 'flex' : 'none';
    els.tabPreview.style.display = tab === 'preview' ? 'flex' : 'none';
    els.tabRips.style.display = tab === 'rips' ? 'flex' : 'none';
    els.detailTabs.querySelectorAll('.detail-tab').forEach(t => {
      t.classList.toggle('is-active', t.dataset.tab === tab);
    });

    if (tab === 'rips') {
      renderRips();
    }
  }

  /* ============================================================
     RIP HANDLER
  ============================================================ */

  async function handleRip() {
    if (!state.selectedAd) {
      showNotification('No ad selected', 'error');
      return;
    }

    const ad = state.selectedAd;
    const url = ad.landing_url_actual || ad.landing_url_clean || ad.page_url || ad.pageUrl || ad.ad_creative_link || '';
    const fbclid = extractFbclid(url);
    const proxy = '';

    if (!url) {
      showNotification('No landing URL available for this ad', 'error');
      return;
    }

    await ripLander(ad.id, url, fbclid, state.ripDevice, proxy);
  }

  function extractFbclid(url) {
    try {
      const u = new URL(url);
      return u.searchParams.get('fbclid') || '';
    } catch {
      return '';
    }
  }

  /* ============================================================
     EVENT BINDINGS
  ============================================================ */

  function bindEvents() {
    // Search
    const debouncedSearch = debounce(() => {
      state.searchQuery = els.searchInput.value;
      applyFilters();
    }, 400);

    els.searchInput.addEventListener('input', debouncedSearch);
    els.searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        state.searchQuery = els.searchInput.value;
        if (state.searchQuery.trim()) {
          state.activeTab = 'search';
          els.tabSearch.classList.add('is-active');
          els.tabScraped.classList.remove('is-active');
        }
        loadAds();
      }
    });

    // Scrape buttons
    els.scrapeBtn.addEventListener('click', () => openScrapeModal('single'));
    els.autoScrapeBtn.addEventListener('click', () => openScrapeModal('auto'));

    // Load Demo button
    els.loadDemoBtn.addEventListener('click', loadDemoData);

    // Tab toggle
    els.tabSearch.addEventListener('click', () => switchMainTab('search'));
    els.tabScraped.addEventListener('click', () => switchMainTab('scraped'));
    els.tabDemo.addEventListener('click', () => switchMainTab('demo'));

    // API Token
    document.getElementById('showTokenFormBtn').addEventListener('click', showTokenForm);
    document.getElementById('cancelTokenBtn').addEventListener('click', cancelTokenForm);
    document.getElementById('saveTokenBtn').addEventListener('click', saveToken);
    document.getElementById('testTokenBtn').addEventListener('click', testToken);
    document.getElementById('clearTokenBtn').addEventListener('click', clearToken);
    document.getElementById('apiTokenInput').addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.key === 'Enter') saveToken();
      if (e.key === 'Escape') cancelTokenForm();
    });

    // Detail close
    els.detailCloseBtn.addEventListener('click', closeDetail);

    // Detail tabs
    els.detailTabs.querySelectorAll('.detail-tab').forEach(tab => {
      tab.addEventListener('click', () => switchDetailTab(tab.dataset.tab));
    });

    // Save button
    els.detailSaveBtn.addEventListener('click', () => {
      if (state.selectedAd) saveAd(state.selectedAd.id);
    });

    // Open landing
    els.detailOpenBtn.addEventListener('click', () => {
      if (!state.selectedAd) return;
      const url = state.selectedAd.landing_url_actual || state.selectedAd.landing_url_clean ||
        state.selectedAd.page_url || state.selectedAd.pageUrl || '';
      if (url) {
        window.open(url, '_blank', 'noopener,noreferrer');
      } else {
        showNotification('No URL available', 'info');
      }
    });

    // Delete button
    els.detailDeleteBtn.addEventListener('click', () => {
      if (state.selectedAd) deleteAd(state.selectedAd.id);
    });

    // Rip lander
    els.ripLanderBtn.addEventListener('click', handleRip);

    // Classify
    els.classifyBtn.addEventListener('click', () => {
      if (state.selectedAd) classifyAd(state.selectedAd.id);
    });

    // Device toggle
    els.deviceToggle.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', () => {
        els.deviceToggle.querySelectorAll('button').forEach(b => b.classList.remove('is-active'));
        btn.classList.add('is-active');
        state.ripDevice = btn.dataset.device;
      });
    });

    // Saved only toggle
    els.savedOnlyToggle.addEventListener('click', () => {
      state.filters.savedOnly = !state.filters.savedOnly;
      els.savedOnlyToggle.classList.toggle('is-active', state.filters.savedOnly);
      applyFilters();
    });

    // Sort
    els.sortSelect.addEventListener('change', () => {
      state.filters.sort = els.sortSelect.value;
      applyFilters();
    });

    // Export
    els.exportCsvBtn.addEventListener('click', exportCsv);
    els.exportJsonBtn.addEventListener('click', exportJson);

    // Clear filters
    els.clearFiltersBtn.addEventListener('click', () => {
      state.filters.category = '';
      state.filters.status = '';
      state.filters.savedOnly = false;
      state.searchQuery = '';
      els.searchInput.value = '';
      els.savedOnlyToggle.classList.remove('is-active');
      els.sortSelect.value = 'newest';

      els.categoryList.querySelectorAll('.category-item').forEach(i => {
        i.classList.toggle('is-active', !i.dataset.category);
      });
      els.statusOptions.querySelectorAll('.status-option').forEach(o => {
        o.classList.toggle('is-active', !o.dataset.status);
      });

      applyFilters();
      renderFilters();
    });

    // Scrape modal: modal tab switcher
    els.scrapeModalBox.querySelectorAll('.modal-tab').forEach(tab => {
      tab.addEventListener('click', () => switchScrapeTab(tab.dataset.scrapeTab));
    });

    // Scrape modal: Multi-Country select/clear all
    els.selectAllCountries.addEventListener('click', () => {
      COUNTRY_LIST.forEach(c => state.selectedCountries.add(c));
      renderCountryCheckboxGrid();
    });
    els.clearAllCountries.addEventListener('click', () => {
      state.selectedCountries.clear();
      renderCountryCheckboxGrid();
    });

    // Scrape modal: Auto-Category select/clear all categories
    els.selectAllCategories.addEventListener('click', () => {
      Object.keys(NUTRA_CATEGORIES).forEach(c => state.selectedCategories.add(c));
      renderCategoryCheckboxGrid();
    });
    els.clearAllCategories.addEventListener('click', () => {
      state.selectedCategories.clear();
      renderCategoryCheckboxGrid();
    });

    // Scrape modal: Auto-Country preset (major markets)
    els.selectAllCountriesAuto.addEventListener('click', () => {
      MAJOR_MARKETS.forEach(c => state.selectedCountries.add(c));
      renderAutoCountryCheckboxGrid();
    });
    els.clearAllCountriesAuto.addEventListener('click', () => {
      state.selectedCountries.clear();
      renderAutoCountryCheckboxGrid();
    });

    // Scrape modal: Cancel
    els.scrapeModalCancel.addEventListener('click', () => {
      if (state.scrapeInProgress) {
        if (!confirm('Scrape in progress. Are you sure you want to cancel?')) return;
      }
      closeScrapeModal();
    });

    // Scrape modal: Overlay click to close
    els.scrapeModalOverlay.addEventListener('click', (e) => {
      if (e.target === els.scrapeModalOverlay) {
        if (!state.scrapeInProgress) closeScrapeModal();
      }
    });

    // Scrape modal: Run button — dispatches based on active tab
    els.scrapeModalRun.addEventListener('click', () => {
      if (state.scrapeInProgress) return;

      switch (state.scrapeTab) {
        case 'single': {
          const url = els.modalPageUrl.value.trim();
          const country = els.modalCountry.value;
          if (!url) {
            showNotification('Please enter a page URL', 'error');
            return;
          }
          scrapePage(url, country);
          break;
        }
        case 'multi': {
          const countries = Array.from(state.selectedCountries);
          const keyword = els.modalMultiKeyword ? els.modalMultiKeyword.value : '';
          const baseUrl = els.modalMultiPageUrl ? els.modalMultiPageUrl.value : '';
          scrapeMultiCountries(countries, { keyword, baseUrl });
          break;
        }
        case 'auto': {
          const categories = Array.from(state.selectedCategories);
          const countries = Array.from(state.selectedCountries);
          scrapeAutoCategory(categories, countries);
          break;
        }
      }
    });

    // Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        if (els.scrapeModal.style.display !== 'none') {
          if (!state.scrapeInProgress) closeScrapeModal();
        } else {
          closeDetail();
        }
      }
    });

    // Expose globally
    window._adsrecon = window._adsrecon || {};
    window._adsrecon.loadAds = loadAds;
    window._adsrecon.scrapeMulti = (countries, options) => scrapeMultiCountries(countries, options);
    window._adsrecon.scrapeAuto = (categories, countries) => scrapeAutoCategory(categories, countries);
    window._adsrecon.openScrapeModal = openScrapeModal;
  }

  /* ============================================================
     INIT
  ============================================================ */

  async function init() {
    bindEvents();
    renderFilters();
    renderStatusFilters();
    renderAdGrid();
    renderCountryCheckboxGrid();
    renderAutoCountryCheckboxGrid();
    renderCategoryCheckboxGrid();

    await checkBackendHealth();
    await loadAds();
    await checkTokenStatus();

    setInterval(checkBackendHealth, 30000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
