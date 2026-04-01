/**
 * ADSRECON Chrome Extension — Background Service Worker
 * Handles cross-tab state, storage, and message routing.
 * Lightweight, non-blocking.
 */

// ── Storage helpers ──────────────────────────────────────────
const STORAGE = {
  trackedPages: [],
  savedAds: [],
  settings: {
    defaultCountry: 'US',
    autoTrack: false,
  }
};

async function loadStorage() {
  const data = await chrome.storage.local.get(['trackedPages', 'savedAds', 'settings']);
  STORAGE.trackedPages = data.trackedPages || [];
  STORAGE.savedAds = data.savedAds || [];
  if (data.settings) STORAGE.settings = { ...STORAGE.settings, ...data.settings };
}

async function saveStorage() {
  await chrome.storage.local.set({
    trackedPages: STORAGE.trackedPages,
    savedAds: STORAGE.savedAds,
    settings: STORAGE.settings,
  });
}

loadStorage();

// ── Message router from popup ───────────────────────────────
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || !msg.type) return true;

  (async () => {
    try {
      switch (msg.type) {
      case 'GET_TRACKED_PAGES':
        sendResponse({ pages: STORAGE.trackedPages });
        break;

      case 'ADD_TRACKED_PAGE': {
        const page = { id: Date.now(), name: msg.name, addedAt: new Date().toISOString() };
        if (!STORAGE.trackedPages.find(p => p.name === page.name)) {
          STORAGE.trackedPages.push(page);
          await saveStorage();
        }
        sendResponse({ pages: STORAGE.trackedPages });
        break;
      }

      case 'REMOVE_TRACKED_PAGE': {
        STORAGE.trackedPages = STORAGE.trackedPages.filter(p => p.id !== msg.id);
        await saveStorage();
        sendResponse({ pages: STORAGE.trackedPages });
        break;
      }

      case 'GET_SAVED_ADS':
        sendResponse({ ads: STORAGE.savedAds });
        break;

      case 'SAVE_AD': {
        const exists = STORAGE.savedAds.find(a => a.id === msg.ad.id);
        if (!exists) {
          STORAGE.savedAds.unshift({ ...msg.ad, savedAt: new Date().toISOString() });
          await saveStorage();
        }
        sendResponse({ saved: true, ads: STORAGE.savedAds });
        break;
      }

      case 'UNSAVE_AD': {
        STORAGE.savedAds = STORAGE.savedAds.filter(a => a.id !== msg.adId);
        await saveStorage();
        sendResponse({ ads: STORAGE.savedAds });
        break;
      }

      case 'CLEAR_SAVED_ADS': {
        STORAGE.savedAds = [];
        await saveStorage();
        sendResponse({ ok: true });
        break;
      }

      case 'GET_SETTINGS':
        sendResponse({ settings: STORAGE.settings });
        break;

      case 'SAVE_SETTINGS': {
        STORAGE.settings = { ...STORAGE.settings, ...msg.settings };
        await saveStorage();
        sendResponse({ settings: STORAGE.settings });
        break;
      }

      case 'GET_AD_COUNT': {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab && tab.url && tab.url.includes('facebook.com/ads/library')) {
          try {
            const result = await chrome.tabs.sendMessage(tab.id, { type: 'PING' });
            sendResponse({ count: result?.count || 0, connected: true });
          } catch {
            sendResponse({ count: 0, connected: false });
          }
        } else {
          sendResponse({ count: 0, connected: false });
        }
        break;
      }

      // ── Bridge: popup ↔ content script ───────────────────────
      case 'GET_ADS': {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab || !tab.url || !tab.url.includes('facebook.com/ads/library')) {
          sendResponse({ ads: [], count: 0 });
          break;
        }
        try {
          const result = await chrome.tabs.sendMessage(tab.id, { type: 'GET_ADS' });
          sendResponse(result || { ads: [], count: 0 });
        } catch {
          sendResponse({ ads: [], count: 0 });
        }
        break;
      }

      case 'SEARCH_ADS': {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab || !tab.url || !tab.url.includes('facebook.com/ads/library')) {
          sendResponse({ ads: [], count: 0 });
          break;
        }
        try {
          const result = await chrome.tabs.sendMessage(tab.id, {
            type: 'SEARCH',
            keyword: msg.keyword || '',
          });
          sendResponse(result || { ads: [], count: 0 });
        } catch {
          sendResponse({ ads: [], count: 0 });
        }
        break;
      }

      case 'NAVIGATE_AND_SCAN': {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab || !tab.url || !tab.url.includes('facebook.com/ads/library')) {
          sendResponse({ ok: false });
          break;
        }
        try {
          const result = await chrome.tabs.sendMessage(tab.id, {
            type: 'NAVIGATE',
            search: msg.search,
            country: msg.country,
          });
          sendResponse(result || { ok: false });
        } catch {
          sendResponse({ ok: false });
        }
        break;
      }

      // ── UPDATE_BADGE — MV3: badge must be set in popup, not service worker ─
      // chrome.action badge APIs are unavailable in MV3 service workers.
      // We store the count and badge state, the popup sets the actual badge.

      case 'UPDATE_BADGE': {
        STORAGE.badgeCount = msg.count || 0;
        // Propagate to popup if it has the badge API available
        // (Badge is managed by popup directly via chrome.action)
        sendResponse({ ok: true });
        break;
      }

      default:
        sendResponse({ error: 'Unknown message type' });
      }
    } catch (err) {
      console.error('[ADSRECON background] error:', err);
      try { sendResponse({ error: String(err) }); } catch (_) {}
    }
  })();
  return true; // Keep channel open for async response
});
