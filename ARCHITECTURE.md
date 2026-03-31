# ADSRECON Architecture

**Version:** 1.0.0
**Date:** 2026-03-31
**Type:** Full-Stack SaaS Application
**Target:** Facebook Ads Library spy tool for Nutra affiliate marketers

---

## 1. SYSTEM OVERVIEW

ADSRECON is a VPS-hosted SaaS tool that enables Nutra affiliate marketers to:

1. **Search** competitor Facebook pages and retrieve all active ads
2. **Classify** ads as REAL (legitimate offer) or DECOY (cloaking dummy)
3. **Rip** landing pages with cloaking bypass to extract real offers
4. **Analyze** video creatives and copy patterns
5. **Track** campaigns over time for trend analysis

### Core Technical Insight

```
Meta's "View Ad" redirect URL format:
https://l.facebook.com/l.php?u=https%3A%2F%2FREAL-LANDER.TOP%2Fpath&fbclid=IwZXh0bgNhZW0CMTAA...

The fbclid parameter is Meta's own tracking click ID.
Cloaking services use fbclid as PRIMARY cloaking signal (not IP).

KEY INSIGHT: Visiting a lander WITH fbclid appended bypasses 90%+ of cloaking.
Proxies only needed as fallback for IP-quality checks.
```

### Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (SPA)                            │
│                     React + Tailwind + Vite                        │
└─────────────────────────────┬───────────────────────────────────────┘
                              │ HTTP/REST
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI)                           │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌───────────┐ │
│  │ Meta Scraper│  │ Cloak Bypass │  │ Browser Pool│  │ Lander    │ │
│  │ Service     │  │ Service      │  │ (Playwright)│  │ Ripper    │ │
│  └─────────────┘  └──────────────┘  └─────────────┘  └───────────┘ │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐                 │
│  │ Nutra       │  │ Video        │  │ Ad          │                 │
│  │ Classifier  │  │ Extractor    │  │ Tracker     │                 │
│  └─────────────┘  └──────────────┘  └─────────────┘                 │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         ┌─────────┐    ┌──────────┐   ┌───────────┐
         │ SQLite  │    │  File    │   │  Config   │
         │ DB      │    │  Storage │   │  (.env)   │
         └─────────┘    └──────────┘   └───────────┘
```

---

## 2. COMPONENT DIAGRAM

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                               ADSRECON SYSTEM                                    │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────────────────┐         ┌───────────────────────────────────┐  │
│  │        FRONTEND             │         │            BACKEND                │  │
│  │        (React SPA)          │         │           (FastAPI)                │  │
│  │                              │         │                                   │  │
│  │  ┌─────────────────────┐    │         │  ┌─────────────────────────────┐  │  │
│  │  │  Search Component   │    │         │  │      META SCRAPER SERVICE   │  │  │
│  │  │  - Page URL input   │────┼────────▶│  │  - Search ads by page        │  │  │
│  │  │  - Geo selector     │    │   REST  │  │  - Extract ad cards          │  │  │
│  │  └─────────────────────┘    │         │  │  - Parse video URLs          │  │  │
│  │                              │         │  │  - Get fbclid redirects      │  │  │
│  │  ┌─────────────────────┐    │         │  └─────────────────────────────┘  │  │
│  │  │  Ad Cards Grid      │◀───┼─────────│                                   │  │
│  │  │  - Thumbnails       │    │         │  ┌─────────────────────────────┐  │  │
│  │  │  - CTA buttons      │    │         │  │    CLOAKING BYPASS SERVICE  │  │  │
│  │  │  - Domain badges    │    │         │  │                             │  │  │
│  │  └─────────────────────┘    │         │  │  1. Extract fbclid          │  │  │
│  │                              │         │  │  2. Visit WITH fbclid        │  │  │
│  │  ┌─────────────────────┐    │         │  │  3. Fallback to proxy        │  │  │
│  │  │  Rip Panel          │────┼────────▶│  │  4. Compare expected/actual   │  │  │
│  │  │  - Preview iframe   │    │         │  │  5. Return REAL/DECOY/UNKNOWN│  │  │
│  │  │  - HTML download    │    │         │  └─────────────────────────────┘  │  │
│  │  └─────────────────────┘    │         │                                   │  │
│  │                              │         │  ┌─────────────────────────────┐  │  │
│  │  ┌─────────────────────┐    │         │  │      BROWSER POOL           │  │  │
│  │  │  Analytics View     │◀───┼─────────│  │  (Playwright Instances)     │  │  │
│  │  │  - Trend charts     │    │         │  │                             │  │  │
│  │  │  - Competitor matrix│    │         │  │  ┌─────┐ ┌─────┐ ┌─────┐    │  │  │
│  │  └─────────────────────┘    │         │  │  │ B1  │ │ B2  │ │ B3  │    │  │  │
│  │                              │         │  │  └─────┘ └─────┘ └─────┘    │  │  │
│  │                              │         │  │  Pool size: 3 (configurable)│  │  │
│  │                              │         │  └─────────────────────────────┘  │  │
│  │                              │         │                                   │  │
│  │                              │         │  ┌─────────────────────────────┐  │  │
│  │                              │         │  │      LANDER RIPPER SERVICE │  │  │
│  │                              │         │  │                             │  │  │
│  │                              │         │  │  - Full page screenshot     │  │  │
│  │                              │         │  │  - HTML dump (sanitized)    │  │  │
│  │                              │         │  │  - CSS extraction           │  │  │
│  │                              │         │  │  - Form field detection     │  │  │
│  │                              │         │  └─────────────────────────────┘  │  │
│  │                              │         │                                   │  │
│  │                              │         │  ┌─────────────────────────────┐  │  │
│  │                              │         │  │      NUTRA CLASSIFIER       │  │  │
│  │                              │         │  │                             │  │  │
│  │                              │         │  │  Categories:                │  │  │
│  │                              │         │  │  - Weight Loss              │  │  │
│  │                              │         │  │  - Male Enhancement         │  │  │
│  │                              │         │  │  - Skin Care                │  │  │
│  │                              │         │  │  - Blood Sugar              │  │  │
│  │                              │         │  │  - Joint Pain               │  │  │
│  │                              │         │  │  - Memory/Focus            │  │  │
│  │                              │         │  │  - Sleep/Stress             │  │  │
│  │                              │         │  │  - Eye Health              │  │  │
│  │                              │         │  │  - Heart Health            │  │  │
│  │                              │         │  │  - Prostate                │  │  │
│  │                              │         │  │  - Teeth Whitening         │  │  │
│  │                              │         │  │  - Anti-Aging              │  │  │
│  │                              │         │  └─────────────────────────────┘  │  │
│  │                              │         │                                   │  │
│  │                              │         │  ┌─────────────────────────────┐  │  │
│  │                              │         │  │      VIDEO EXTRACTOR        │  │  │
│  │                              │         │  │                             │  │  │
│  │                              │         │  │  - Download video files     │  │  │
│  │                              │         │  │  - Extract thumbnails       │  │  │
│  │                              │         │  │  - Detect video dimensions  │  │  │
│  │                              │         │  │  - Format detection         │  │  │
│  │                              │         │  └─────────────────────────────┘  │  │
│  └──────────────────────────────┘         └───────────────────────────────────┘  │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                              DATA LAYER                                     │  │
│  │                                                                             │  │
│  │   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   │  │
│  │   │    ads      │   │ variations  │   │  landers    │   │ campaigns   │   │  │
│  │   │   table     │   │   table     │   │   table     │   │   table     │   │  │
│  │   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘   │  │
│  │                                                                             │  │
│  │   ┌─────────────────────────────────────────────────────────────────┐      │  │
│  │   │                    FILE STORAGE                                │      │  │
│  │   │  /screenshots/{ad_id}/{timestamp}.png                          │      │  │
│  │   │  /landers/{lander_id}/full.html                                │      │  │
│  │   │  /videos/{ad_id}/{timestamp}.mp4                                │      │  │
│  │   └─────────────────────────────────────────────────────────────────┘      │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. DATA FLOW DIAGRAMS

### 3A. User Searches a Competitor Page

```
┌─────────────┐     ┌──────────────┐     ┌───────────────────┐     ┌──────────────┐     ┌─────────────┐
│   User      │     │   Frontend   │     │   Meta Scraper    │     │   SQLite     │     │  Frontend   │
│   Pastes    │────▶│   Sends      │────▶│   Service         │────▶│   Stores     │────▶│   Shows     │
│   Page URL  │     │   /scrape    │     │   Fetches ads     │     │   ads + vars │     │   Ad Cards  │
└─────────────┘     └──────────────┘     └───────────────────┘     └──────────────┘     └─────────────┘
                                                                                                   │
                    ┌───────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────────────────────────────────────────────────────┐
    │                         STEP-BY-STEP FLOW                                     │
    │                                                                               │
    │  1. Frontend: POST /api/scrape { page_url, geo }                           │
    │                                                                               │
    │  2. Backend extracts PAGE_ID from URL                                        │
    │     Input:  https://www.facebook.com/ExampleBrand/                            │
    │     Output: PAGE_ID = "123456789"                                             │
    │                                                                               │
    │  3. Meta Scraper Service:                                                     │
    │     - Constructs API URL:                                                     │
    │       https://www.facebook.com/ads/library/?view_all_page_id={PAGE_ID}       │
    │     - Fetches via httpx with browser-like headers                            │
    │     - Parses response for ad cards                                           │
    │                                                                               │
    │  4. For each ad found:                                                        │
    │     - Extract: ad_id, page_name, page_id, creative_ids                       │
    │     - Extract: thumbnail_url, video_urls[]                                   │
    │     - Extract: cta_text, page_title                                          │
    │     - Extract: direct_url (from "View Ad" click link)                        │
    │     - Store in DB with timestamp                                              │
    │                                                                               │
    │  5. Return: { success: true, ads: [...], total: N }                          │
    │                                                                               │
    └───────────────────────────────────────────────────────────────────────────────┘
```

### 3B. User Classifies an Ad (Cloaking Check)

```
┌─────────────┐     ┌──────────────┐     ┌───────────────────┐     ┌──────────────┐
│   User      │     │   Frontend   │     │   Cloaking        │     │   Browser    │
│   Clicks    │────▶│   POST       │────▶│   Bypass          │────▶│   Pool       │
│   "Check"   │     │   /classify  │     │   Service         │     │   (Playwright)│
└─────────────┘     └──────────────┘     └───────────────────┘     └──────────────┘
                                                                 │
                    ┌──────────────────────────────────────────┐│
                    │                                          ▼
                    │   ┌───────────────────────────────────────────────┐
                    │   │            DECISION TREE                       │
                    │   │                                                │
                    │   │   Step 1: EXTRACT fbclid                       │
                    │   │   - From stored direct_url                     │
                    │   │   - Format: &fbclid=IwZXh0bgNhZW0CMTAA...     │
                    │   │                                                │
                    │   │   Step 2: TRY WITHOUT PROXY                    │
                    │   │   - Visit: https://REAL-LANDER.TOP/?fbclid=...│
                    │   │   - Playwright with clean browser context      │
                    │   │   - Wait for redirect completion               │
                    │   │                                                │
                    │   │   ┌─────────────┐  ┌─────────────────────────┐ │
                    │   │   │   SUCCESS   │  │       FAILURE            │ │
                    │   │   │             │  │                          │ │
                    │   │   │ → Compare   │  │ Step 3: TRY WITH PROXY   │ │
                    │   │   │   expected  │  │                          │ │
                    │   │   │   vs actual │  │ DataImpulse rotation:   │ │
                    │   │   │   URL       │  │ - residential proxies    │ │
                    │   │   │             │  │ - geo-targeted (US/UK/CA)│ │
                    │   │   └─────────────┘  └─────────────────────────┘ │
                    │   │                                                │
                    │   │   Step 4: CLASSIFY RESULT                       │
                    │   │   ┌─────────┬─────────┬─────────┐              │
                    │   │   │  REAL   │  DECOY  │ UNKNOWN │              │
                    │   │   │ expected│ expected│  timeout│              │
                    │   │   │ = actual| != actual│  error  │              │
                    │   │   └─────────┴─────────┴─────────┘              │
                    │   │                                                │
                    │   └─────────────────────────────────────────────────┘
                    │
                    └──────────────────────────────────────────────────────────┘
                                                 │
                                                 ▼
┌─────────────┐     ┌──────────────┐     ┌───────────────────┐
│   Frontend  │◀────│   Backend    │◀────│   Return Result   │
│   Updates   │     │   Saves to    │     │   + lander data  │
│   Ad Card   │     │   DB          │     │                   │
└─────────────┘     └──────────────┘     └───────────────────┘
```

### 3C. User Rips a Landing Page

```
┌─────────────┐     ┌──────────────┐     ┌───────────────────┐     ┌──────────────┐
│   User      │     │   Frontend   │     │   Lander          │     │   Browser    │
│   Clicks    │────▶│   POST       │────▶│   Ripper          │────▶│   Pool       │
│   "Rip"     │     │   /rip        │     │   Service         │     │              │
└─────────────┘     └──────────────┘     └───────────────────┘     └──────────────┘
                                                                 │
                    ┌──────────────────────────────────────────┐│
                    │                                          ▼
                    │   ┌───────────────────────────────────────────────┐
                    │   │            RIP WORKFLOW                        │
                    │   │                                                │
                    │   │   1. Get browser from pool                     │
                    │   │   2. Create new browser context                 │
                    │   │   3. Set proxy if needed (DataImpulse)         │
                    │   │   4. Navigate to lander URL WITH fbclid        │
                    │   │   5. Wait for networkidle (timeout: 15s)       │
                    │   │   6. Extract DOM content                        │
                    │   │   7. Sanitize HTML (remove scripts, iframes)   │
                    │   │   8. Take full-page screenshot                  │
                    │   │   9. Extract meta tags, forms, links           │
                    │   │   10. Release browser back to pool             │
                    │   │   11. Store files in /landers/{id}/            │
                    │   │   12. Update DB record                          │
                    │   │   13. Return preview data                       │
                    │   │                                                │
                    │   └─────────────────────────────────────────────────┘
                    │
                    └──────────────────────────────────────────────────────────┘
                                                 │
                                                 ▼
┌─────────────┐     ┌──────────────┐     ┌───────────────────┐
│   Frontend  │◀────│   Backend    │◀────│   Preview +       │
│   Shows     │     │   Returns:   │     │   download links  │
│   Screenshot│     │   - preview  │     │                   │
│   + Preview │     │   - html_url │     │                   │
└─────────────┘     └──────────────┘     └───────────────────┘
```

### 3D. Video Extraction Flow

```
┌─────────────┐     ┌──────────────┐     ┌───────────────────┐     ┌──────────────┐
│   User      │     │   Frontend   │     │   Video           │     │   File       │
│   Clicks    │────▶│   POST       │────▶│   Extractor       │────▶│   Storage    │
│   "Save"    │     │   /video     │     │   Service         │     │   /videos/   │
└─────────────┘     └──────────────┘     └───────────────────┘     └──────────────┘
                                                 │
                    ┌────────────────────────────┘
                    │
                    ▼
    ┌─────────────────────────────────────────────────────────────┐
    │  1. Download video via httpx (stream=True)                 │
    │  2. Save to /videos/{ad_id}/{timestamp}.mp4                │
    │  3. Generate thumbnail frame at 2s mark                    │
    │  4. Extract metadata (duration, resolution, codec)         │
    │  5. Update DB: video_url, thumbnail_url, video_meta       │
    │  6. Return: { video_url, thumbnail_url, duration }         │
    └─────────────────────────────────────────────────────────────┘
```

---

## 4. DATABASE SCHEMA

### 4.1 ads Table

```sql
CREATE TABLE ads (
    -- Primary identifiers
    id                  TEXT PRIMARY KEY,           -- UUID: uuid4()
    library_id          TEXT UNIQUE NOT NULL,        -- Meta's ad library ID
    page_id             TEXT NOT NULL,               -- Facebook page ID
    page_name           TEXT NOT NULL,               -- Brand name

    -- Creative data
    creative_ids        TEXT,                        -- JSON array: ["cid1", "cid2"]
    thumbnail_url       TEXT,                        -- Main image URL
    video_urls          TEXT,                        -- JSON array: ["url1", "url2"]

    -- Ad content
    cta_text            TEXT,                        -- "Shop Now", "Learn More", etc.
    page_title          TEXT,                        -- Ad headline/title
    ad_body             TEXT,                        -- Full ad copy text

    -- Tracking data
    direct_url          TEXT,                        -- From "View Ad" click (includes fbclid)
    fbclid              TEXT,                       -- Extracted fbclid parameter

    -- Classification results
    status              TEXT DEFAULT 'pending',      -- pending | real | decoy | unknown | error
    status_checked_at   TIMESTAMP,                   -- When classification was run
    classification_method TEXT,                     -- 'fbclid_only' | 'proxy_used'

    -- Geo targeting
    geo_targeting       TEXT,                        -- JSON array: ["US", "UK"]

    -- Nutra vertical
    vertical            TEXT,                        -- Weight Loss, Male Enhancement, etc.
    vertical_confidence REAL DEFAULT 0.0,            -- 0.0 to 1.0

    -- Timestamps
    first_seen_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Raw data storage
    raw_data            TEXT                         -- Full JSON from Meta
);

CREATE INDEX idx_ads_page_id ON ads(page_id);
CREATE INDEX idx_ads_status ON ads(status);
CREATE INDEX idx_ads_vertical ON ads(vertical);
CREATE INDEX idx_ads_first_seen ON ads(first_seen_at);
CREATE INDEX idx_ads_direct_url ON ads(direct_url);
```

### 4.2 variations Table

```sql
CREATE TABLE variations (
    -- Primary identifiers
    id                  TEXT PRIMARY KEY,           -- UUID
    ad_id               TEXT NOT NULL,              -- FK to ads.id

    -- Variation data
    variation_type      TEXT NOT NULL,              -- 'image' | 'video' | 'headline' | 'copy' | 'cta'
    position            INTEGER DEFAULT 0,          -- Order in rotation

    -- Content
    content_url         TEXT,                        -- Image/video URL
    content_hash        TEXT,                        -- SHA256 of downloaded content
    thumbnail_url       TEXT,                        -- Preview thumbnail
    headline_text       TEXT,                        -- For headline/copy variations
    copy_text           TEXT,

    -- Metadata
    width               INTEGER,
    height              INTEGER,
    file_size           INTEGER,
    mime_type           TEXT,

    -- Timestamps
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Relations
    FOREIGN KEY (ad_id) REFERENCES ads(id) ON DELETE CASCADE
);

CREATE INDEX idx_variations_ad_id ON variations(ad_id);
CREATE INDEX idx_variations_type ON variations(variation_type);
```

### 4.3 landers Table

```sql
CREATE TABLE landers (
    -- Primary identifiers
    id                  TEXT PRIMARY KEY,           -- UUID
    ad_id               TEXT,                        -- FK to ads.id (nullable for standalone rips)

    -- URL data
    original_url        TEXT NOT NULL,              -- URL as entered/stored
    final_url           TEXT,                        -- Actual URL after all redirects
    url_domain          TEXT,                        -- Extracted domain

    -- Classification
    cloak_status        TEXT DEFAULT 'pending',     -- pending | clean | cloaked | unknown | error
    expected_domain     TEXT,                        -- What we expected to see
    actual_domain       TEXT,                        -- What we actually got
    classification_reason TEXT,                     -- Why it was classified

    -- Content
    html_content        TEXT,                        -- Sanitized HTML (stored in DB or file?)
    html_path           TEXT,                        -- Path to full HTML file: /landers/{id}/index.html
    screenshot_path     TEXT,                        -- Path: /landers/{id}/screenshot.png
    thumbnail_path      TEXT,                        -- Path: /landers/{id}/thumb.png

    -- Page analysis
    meta_title          TEXT,
    meta_description    TEXT,
    forms_detected      INTEGER DEFAULT 0,
    forms_html          TEXT,                        -- JSON: [{name, action, fields[]}]
    links_external      INTEGER DEFAULT 0,
    links_internal      INTEGER DEFAULT 0,

    -- Nutra signals
    nutra_signals       TEXT,                        -- JSON: [{type, value, confidence}]

    -- Browser/rip metadata
    browser_used        TEXT,                        -- 'chrome' | 'firefox' | etc.
    proxy_used          TEXT,                        -- Proxy host (no credentials)
    proxy_geo           TEXT,                        -- Proxy location
    rip_duration_ms     INTEGER,                     -- How long rip took
    rip_method          TEXT,                        -- 'fbclid' | 'proxy' | 'direct'

    -- Error tracking
    error_message       TEXT,
    error_count         INTEGER DEFAULT 0,

    -- Timestamps
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    first_rip_at        TIMESTAMP,
    last_rip_at         TIMESTAMP,
    rip_count           INTEGER DEFAULT 0,

    -- Relations
    FOREIGN KEY (ad_id) REFERENCES ads(id) ON DELETE SET NULL
);

CREATE INDEX idx_landers_ad_id ON landers(ad_id);
CREATE INDEX idx_landers_domain ON landers(url_domain);
CREATE INDEX idx_landers_cloak_status ON landers(cloak_status);
CREATE INDEX idx_landers_created ON landers(created_at);
CREATE INDEX idx_landers_original_url ON landers(original_url);
```

### 4.4 campaigns Table

```sql
CREATE TABLE campaigns (
    -- Primary identifiers
    id                  TEXT PRIMARY KEY,           -- UUID
    name                TEXT NOT NULL,              -- User-defined name

    -- Campaign tracking
    competitor_page_id  TEXT,                        -- Facebook page being tracked
    competitor_name     TEXT,

    -- Settings
    geo_targets         TEXT,                        -- JSON array: ["US", "UK"]
    verticals           TEXT,                        -- JSON array: targeted verticals

    -- Status
    status              TEXT DEFAULT 'active',      -- active | paused | completed
    is_auto_scrape      INTEGER DEFAULT 0,          -- 1 = run on schedule

    -- Schedule (for auto-scrape)
    scrape_interval_hours INTEGER DEFAULT 24,
    last_scrape_at      TIMESTAMP,
    next_scrape_at      TIMESTAMP,

    -- Statistics (denormalized for performance)
    total_ads_found     INTEGER DEFAULT 0,
    total_real_ads      INTEGER DEFAULT 0,
    total_decoy_ads     INTEGER DEFAULT 0,
    total_landers_ripped INTEGER DEFAULT 0,

    -- Timestamps
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_campaigns_competitor ON campaigns(competitor_page_id);
CREATE INDEX idx_campaigns_status ON campaigns(status);
```

### 4.5 API Keys Table (for multi-user SaaS)

```sql
CREATE TABLE api_keys (
    id                  TEXT PRIMARY KEY,
    user_id             TEXT NOT NULL,
    key_hash            TEXT UNIQUE NOT NULL,       -- SHA256 of actual key
    name                TEXT,                        -- User-defined label
    rate_limit_rpm       INTEGER DEFAULT 60,        -- Requests per minute
    is_active           INTEGER DEFAULT 1,
    last_used_at        TIMESTAMP,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at          TIMESTAMP
);

CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
```

---

## 5. API DESIGN

### Base URL
```
http://localhost:8000/api/v1
```

### Authentication
```http
Authorization: Bearer <api_key>
```

### 5.1 Ad Scraping Endpoints

#### POST /scrape/page
Scrape all ads from a Facebook page.

```http
POST /api/v1/scrape/page
Content-Type: application/json
Authorization: Bearer <key>

{
    "page_url": "https://www.facebook.com/ExampleBrand",
    "geo": "US",
    "include_inactive": false
}
```

**Response 200:**
```json
{
    "success": true,
    "job_id": "uuid-1234",
    "status": "completed",
    "data": {
        "page_id": "123456789",
        "page_name": "Example Brand",
        "ads_found": 47,
        "ads": [
            {
                "id": "ad-uuid-1",
                "library_id": "2345678",
                "cta_text": "Shop Now",
                "page_title": "Amazing Weight Loss Solution",
                "thumbnail_url": "https://...",
                "video_urls": [],
                "direct_url": "https://l.facebook.com/l.php?u=https%3A%2F%2Freal-lander.top%2Foffer&fbclid=...",
                "geo_targeting": ["US", "UK"],
                "status": "pending"
            }
        ]
    },
    "timing_ms": 4521
}
```

#### GET /scrape/status/{job_id}
Check scraping job status.

```http
GET /api/v1/scrape/status/{job_id}
Authorization: Bearer <key>
```

**Response 200:**
```json
{
    "job_id": "uuid-1234",
    "status": "completed",  // queued | running | completed | failed
    "progress": 100,
    "ads_found": 47,
    "errors": []
}
```

### 5.2 Classification Endpoints

#### POST /classify/{ad_id}
Classify an ad as REAL or DECOY.

```http
POST /api/v1/classify/{ad_id}
Authorization: Bearer <key>

{
    "force_recheck": false,  // Re-run even if already classified
    "method": "auto"         // auto | fbclid_only | proxy_required
}
```

**Response 200:**
```json
{
    "success": true,
    "ad_id": "ad-uuid-1",
    "classification": {
        "status": "real",
        "method": "fbclid_only",
        "expected_domain": "real-lander.top",
        "actual_domain": "real-lander.top",
        "redirect_chain": [
            "https://l.facebook.com/l.php?u=...",
            "https://real-lander.top/offer"
        ],
        "cloaking_score": 0.0,
        "verified_at": "2026-03-31T12:00:00Z"
    },
    "lander": {
        "id": "lander-uuid-1",
        "url": "https://real-lander.top/offer",
        "final_url": "https://real-lander.top/offer"
    },
    "timing_ms": 3241
}
```

**Response (decoy detected):**
```json
{
    "success": true,
    "ad_id": "ad-uuid-1",
    "classification": {
        "status": "decoy",
        "method": "fbclid_only",
        "expected_domain": "real-lander.top",
        "actual_domain": "decoy-site.com",
        "redirect_chain": [
            "https://l.facebook.com/l.php?u=...",
            "https://decoy-site.com"
        ],
        "cloaking_score": 1.0,
        "verified_at": "2026-03-31T12:00:00Z"
    }
}
```

#### POST /classify/batch
Classify multiple ads in bulk.

```http
POST /api/v1/classify/batch
Authorization: Bearer <key>

{
    "ad_ids": ["uuid-1", "uuid-2", "uuid-3"],
    "parallel": true,
    "max_concurrent": 3
}
```

### 5.3 Lander Rip Endpoints

#### POST /rip
Rip a landing page.

```http
POST /api/v1/rip
Authorization: Bearer <key>

{
    "url": "https://real-lander.top/offer",
    "ad_id": "ad-uuid-1",          // Optional
    "include_fbclid": true,         // Append fbclid if available
    "fbclid": "IwZXh0bgNhZW0CMTAA...",  // Optional
    "use_proxy": "auto",            // auto | always | never
    "screenshot": true,
    "extract_forms": true,
    "sanitize_html": true
}
```

**Response 200:**
```json
{
    "success": true,
    "lander": {
        "id": "lander-uuid-1",
        "original_url": "https://real-lander.top/offer",
        "final_url": "https://real-lander.top/offer",
        "cloak_status": "clean",
        "meta_title": "Amazing Weight Loss Product",
        "meta_description": "Lose 10 lbs in 10 days...",
        "forms_detected": 1,
        "links_external": 5,
        "nutra_signals": [
            {"type": "headline", "value": "Lose Weight Fast", "confidence": 0.95},
            {"type": "claim", "value": "FDA approved", "confidence": 0.88}
        ]
    },
    "files": {
        "screenshot": "/files/landers/lander-uuid-1/screenshot.png",
        "html": "/files/landers/lander-uuid-1/index.html",
        "thumbnail": "/files/landers/lander-uuid-1/thumb.png"
    },
    "timing_ms": 8234
}
```

#### GET /rip/{lander_id}
Get rip results.

```http
GET /api/v1/rip/{lander_id}
Authorization: Bearer <key>
```

#### GET /rip/{lander_id}/preview
Get HTML preview (sandboxed iframe data).

```http
GET /api/v1/rip/{lander_id}/preview
Authorization: Bearer <key>
```

**Response 200:**
```html
<!-- Sanitized HTML content -->
<div class="landing-page">
    ...
</div>
```

### 5.4 Video Endpoints

#### POST /video/extract
Extract video from ad.

```http
POST /api/v1/video/extract
Authorization: Bearer <key>

{
    "ad_id": "ad-uuid-1",
    "video_url": "https://video.fb.com/...",
    "download": true,
    "generate_thumbnail": true
}
```

**Response 200:**
```json
{
    "success": true,
    "video": {
        "id": "video-uuid-1",
        "url": "https://...",
        "local_path": "/files/videos/video-uuid-1.mp4",
        "thumbnail_path": "/files/videos/video-uuid-1/thumb.jpg",
        "duration_seconds": 15.5,
        "width": 1080,
        "height": 1920,
        "codec": "h264",
        "file_size_bytes": 2456789
    }
}
```

### 5.5 Analytics Endpoints

#### GET /analytics/ads
Get ad analytics.

```http
GET /api/v1/analytics/ads?page_id=123&from=2026-03-01&to=2026-03-31&vertical=weight_loss
Authorization: Bearer <key>
```

**Response 200:**
```json
{
    "total_ads": 156,
    "by_status": {
        "real": 89,
        "decoy": 34,
        "pending": 28,
        "error": 5
    },
    "by_vertical": {
        "weight_loss": 45,
        "male_enhancement": 32,
        "skin_care": 28,
        "other": 51
    },
    "by_geo": {
        "US": 98,
        "UK": 42,
        "CA": 16
    },
    "trends": [
        {"date": "2026-03-01", "ads_found": 12, "real_ratio": 0.65},
        {"date": "2026-03-02", "ads_found": 18, "real_ratio": 0.72}
    ]
}
```

#### GET /analytics/competitors
Get competitor comparison.

```http
GET /api/v1/analytics/competitors
Authorization: Bearer <key>
```

### 5.6 Campaign Endpoints

#### POST /campaigns
Create tracking campaign.

```http
POST /api/v1/campaigns
Authorization: Bearer <key>

{
    "name": "Competitor X Tracking",
    "competitor_page_url": "https://www.facebook.com/CompetitorX",
    "geo_targets": ["US", "UK"],
    "verticals": ["weight_loss", "male_enhancement"],
    "auto_scrape": true,
    "scrape_interval_hours": 24
}
```

#### GET /campaigns
List all campaigns.

#### GET /campaigns/{id}
Get campaign details.

#### PUT /campaigns/{id}
Update campaign.

#### DELETE /campaigns/{id}
Delete campaign.

### 5.7 Error Responses

```json
{
    "success": false,
    "error": {
        "code": "SCRAPE_FAILED",
        "message": "Facebook blocked the request. Try again later.",
        "details": {
            "fb_error_code": 190,
            "retry_after_seconds": 60
        }
    }
}
```

**Standard Error Codes:**
| Code | HTTP Status | Description |
|------|-------------|-------------|
| INVALID_URL | 400 | Invalid page URL format |
| SCRAPE_FAILED | 502 | Facebook scraping failed |
| RATE_LIMITED | 429 | Too many requests |
| BROWSER_ERROR | 503 | Browser pool exhausted |
| RIP_TIMEOUT | 504 | Lander rip timed out |
| INVALID_API_KEY | 401 | Invalid or expired API key |
| NOT_FOUND | 404 | Resource not found |

---

## 6. BROWSER POOL DESIGN

### 6.1 Pool Architecture

```python
# backend/services/browser_pool.py

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Optional, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger("browser_pool")


@dataclass
class BrowserConfig:
    """Configuration for browser pool."""
    pool_size: int = 3                    # Number of browser instances
    headless: bool = True                  # Run headless on VPS
    viewport_width: int = 1920
    viewport_height: int = 1080
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    timeout_ms: int = 30000               # Page load timeout
    navigation_timeout_ms: int = 45000    # Navigation timeout


@dataclass
class BrowserInstance:
    """Represents a browser instance in the pool."""
    id: str
    browser: Browser
    context: BrowserContext
    in_use: bool = False
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    use_count: int = 0


class BrowserPool:
    """
    Manages a pool of Playwright browser instances.

    Design decisions:
    - Pool size of 3 is optimal for VPS with 4GB+ RAM
    - Each instance gets a fresh context for isolation
    - Lazy initialization - browsers created on first request
    - Health checks every 5 minutes
    """

    def __init__(self, config: BrowserConfig = None):
        self.config = config or BrowserConfig()
        self._playwright = None
        self._browsers: List[BrowserInstance] = []
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self):
        """Initialize the browser pool."""
        async with self._lock:
            if self._initialized:
                return

            logger.info(f"Initializing browser pool with {self.config.pool_size} instances")
            self._playwright = await async_playwright().start()

            for i in range(self.config.pool_size):
                instance = await self._create_instance(i)
                self._browsers.append(instance)

            self._initialized = True
            logger.info("Browser pool initialized successfully")

    async def _create_instance(self, index: int) -> BrowserInstance:
        """Create a new browser instance."""
        browser = await self._playwright.chromium.launch(
            headless=self.config.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )

        context = await browser.new_context(
            viewport={'width': self.config.viewport_width, 'height': self.config.viewport_height},
            user_agent=self.config.user_agent,
            ignore_https_errors=True
        )

        # Set extra headers to look like real browser
        await context.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        })

        instance_id = f"browser-{index}-{uuid.uuid4().hex[:8]}"
        return BrowserInstance(
            id=instance_id,
            browser=browser,
            context=context
        )

    @asynccontextmanager
    async def acquire(self, timeout: float = 30.0):
        """
        Acquire a browser from the pool.

        Usage:
            async with browser_pool.acquire() as ctx:
                page = await ctx.new_page()
                await page.goto("...")
        """
        async with self._lock:
            # Find available browser
            for instance in self._browsers:
                if not instance.in_use:
                    instance.in_use = True
                    instance.last_used_at = time.time()
                    instance.use_count += 1
                    logger.debug(f"Acquired browser {instance.id}")
                    break
            else:
                # All browsers in use - wait or raise
                raise BrowserPoolExhausted(
                    f"All {self.config.pool_size} browsers are in use"
                )

        try:
            yield instance
        finally:
            async with self._lock:
                instance.in_use = False
                # Create new context for next use (fresh state)
                await instance.context.close()
                instance.context = await instance.browser.new_context(
                    viewport={'width': self.config.viewport_width, 'height': self.config.viewport_height},
                    user_agent=self.config.user_agent,
                    ignore_https_errors=True
                )
            logger.debug(f"Released browser {instance.id}")

    async def health_check(self):
        """Perform health check on all browsers."""
        async with self._lock:
            for i, instance in enumerate(self._browsers):
                try:
                    async with asyncio.timeout(5.0):
                        test_page = await instance.context.new_page()
                        await test_page.goto("about:blank")
                        await test_page.close()
                        logger.debug(f"Browser {instance.id} health check OK")
                except Exception as e:
                    logger.warning(f"Browser {instance.id} health check failed: {e}")
                    # Replace unhealthy browser
                    await instance.browser.close()
                    self._browsers[i] = await self._create_instance(i)

    async def shutdown(self):
        """Shutdown all browsers."""
        async with self._lock:
            for instance in self._browsers:
                await instance.browser.close()
            if self._playwright:
                await self._playwright.stop()
            self._browsers.clear()
            self._initialized = False
            logger.info("Browser pool shutdown complete")


class BrowserPoolExhausted(Exception):
    """Raised when all browsers in pool are in use."""
    pass
```

### 6.2 Proxy Rotation

```python
# backend/services/proxy_manager.py

import random
import httpx
from dataclasses import dataclass
from typing import Optional, List
import asyncio


@dataclass
class ProxyConfig:
    """Single proxy configuration."""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    geo: str = "US"
    protocol: str = "http"  # http, socks5

    @property
    def url(self) -> str:
        """Get proxy URL for httpx/playwright."""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"


class ProxyManager:
    """
    Manages DataImpulse proxy rotation.

    Strategy:
    1. Primary: Use fbclid bypass (no proxy needed)
    2. Fallback: Rotate through DataImpulse residential proxies
    3. Geo-targeting: Prefer proxies matching ad target geo
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._proxies: List[ProxyConfig] = []
        self._geo_pools: dict[str, List[ProxyConfig]] = {}
        self._current_index = 0

    async def load_proxies(self):
        """Load proxies from DataImpulse API."""
        # DataImpulse API endpoint for proxy list
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.dataimpulse.com/proxies",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            data = response.json()

            for proxy_data in data.get("proxies", []):
                proxy = ProxyConfig(
                    host=proxy_data["host"],
                    port=proxy_data["port"],
                    username=proxy_data.get("username"),
                    password=proxy_data.get("password"),
                    geo=proxy_data.get("geo", "US"),
                    protocol=proxy_data.get("protocol", "http")
                )
                self._proxies.append(proxy)

                if proxy.geo not in self._geo_pools:
                    self._geo_pools[proxy.geo] = []
                self._geo_pools[proxy.geo].append(proxy)

        # Also add backup static proxies
        self._proxies.extend([
            ProxyConfig(host="gw.dataimpulse.com", port=80, geo="US", protocol="http"),
            ProxyConfig(host="gw.dataimpulse.com", port=443, geo="UK", protocol="http"),
        ])

    def get_proxy(self, geo: Optional[str] = None) -> Optional[ProxyConfig]:
        """
        Get next proxy, optionally geo-matched.

        Args:
            geo: Target geo code (US, UK, CA, etc.)

        Returns:
            ProxyConfig or None if no proxies available
        """
        if geo and geo in self._geo_pools:
            pool = self._geo_pools[geo]
            if pool:
                return random.choice(pool)

        # Fallback to any available proxy
        if self._proxies:
            proxy = self._proxies[self._current_index]
            self._current_index = (self._current_index + 1) % len(self._proxies)
            return proxy

        return None

    def get_playwright_proxy(self, geo: Optional[str] = None) -> Optional[dict]:
        """Get proxy config formatted for Playwright."""
        proxy = self.get_proxy(geo)
        if not proxy:
            return None

        return {
            "server": f"{proxy.protocol}://{proxy.host}:{proxy.port}",
            "username": proxy.username,
            "password": proxy.password
        }
```

### 6.3 Browser Pool Integration with Cloaking Bypass

```python
# backend/services/cloaking_bypass.py

import asyncio
import re
import httpx
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import Optional, Tuple
import logging

logger = logging.getLogger("cloaking_bypass")


class CloakingBypassService:
    """
    Implements the fbclid-first cloaking bypass strategy.

    Decision tree:
    1. Extract fbclid from Meta's redirect URL
    2. Visit lander WITH fbclid (no proxy)
    3. If fails, try with DataImpulse proxy
    4. Compare expected vs actual URL
    5. Return classification
    """

    def __init__(
        self,
        browser_pool,
        proxy_manager,
        config
    ):
        self.browser_pool = browser_pool
        self.proxy_manager = proxy_manager
        self.config = config

    def extract_fbclid(self, url: str) -> Optional[str]:
        """
        Extract fbclid from Meta redirect URL.

        Input:  https://l.facebook.com/l.php?u=https%3A%2F%2Freal-lander.top%2Foffer&fbclid=IwZXh0bgNhZW0CMTAA...
        Output: IwZXh0bgNhZW0CMTAA...
        """
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            return params.get("fbclid", [None])[0]
        except Exception as e:
            logger.warning(f"Failed to extract fbclid from {url}: {e}")
            return None

    def extract_lander_url(self, fbclid_url: str) -> Optional[str]:
        """
        Extract the actual lander URL from Meta's redirect URL.

        Input:  https://l.facebook.com/l.php?u=https%3A%2F%2Freal-lander.top%2Foffer&fbclid=...
        Output: https://real-lander.top/offer
        """
        try:
            parsed = urlparse(fbclid_url)
            params = parse_qs(parsed.query)
            encoded_url = params.get("u", [None])[0]
            if encoded_url:
                from urllib.parse import unquote
                return unquote(encoded_url)
            return None
        except Exception as e:
            logger.warning(f"Failed to extract lander URL: {e}")
            return None

    def append_fbclid(self, url: str, fbclid: str) -> str:
        """
        Append fbclid to URL preserving existing params.

        Input:  https://real-lander.top/offer?id=123, fbclid=abc
        Output: https://real-lander.top/offer?id=123&fbclid=abc
        """
        parsed = urlparse(url)
        params = dict(parse_qs(parsed.query))
        params["fbclid"] = fbclid

        new_query = urlencode(params, safe="")
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))

    async def classify(
        self,
        ad_id: str,
        direct_url: str,
        expected_domain: str,
        use_proxy: str = "auto"
    ) -> dict:
        """
        Classify ad as REAL or DECOY.

        Args:
            ad_id: Ad UUID
            direct_url: Meta's redirect URL (from "View Ad")
            expected_domain: Domain we expect to see
            use_proxy: 'auto', 'always', or 'never'

        Returns:
            Classification result dict
        """
        result = {
            "ad_id": ad_id,
            "status": "unknown",
            "expected_domain": expected_domain,
            "actual_domain": None,
            "final_url": None,
            "redirect_chain": [],
            "method": None,
            "proxy_used": None,
            "cloaking_score": 0.5,
            "error": None
        }

        # Step 1: Extract fbclid and lander URL
        fbclid = self.extract_fbclid(direct_url)
        lander_url = self.extract_lander_url(direct_url)

        if not lander_url:
            result["error"] = "Failed to extract lander URL"
            result["status"] = "error"
            return result

        result["redirect_chain"].append(lander_url)

        expected_domain = expected_domain or urlparse(lander_url).netloc

        # Step 2: Try WITHOUT proxy first (fbclid method)
        if use_proxy in ("auto", "never"):
            try:
                visit_url = self.append_fbclid(lander_url, fbclid) if fbclid else lander_url

                final_url, actual_domain = await self._visit_with_browser(
                    visit_url,
                    use_proxy=False
                )

                result["final_url"] = final_url
                result["actual_domain"] = actual_domain
                result["method"] = "fbclid_only"

                # Step 4: Compare
                if actual_domain == expected_domain:
                    result["status"] = "real"
                    result["cloaking_score"] = 0.0
                else:
                    result["status"] = "decoy"
                    result["cloaking_score"] = 1.0

                return result

            except Exception as e:
                logger.warning(f"fbclid-only visit failed: {e}")
                if use_proxy == "never":
                    result["error"] = str(e)
                    result["status"] = "error"
                    return result

        # Step 3: Fallback to proxy
        if use_proxy in ("auto", "always"):
            try:
                geo = self._extract_geo_from_domain(expected_domain)
                proxy = self.proxy_manager.get_proxy(geo)

                final_url, actual_domain = await self._visit_with_browser(
                    lander_url,
                    use_proxy=True,
                    proxy=proxy
                )

                result["final_url"] = final_url
                result["actual_domain"] = actual_domain
                result["method"] = "proxy_used"
                result["proxy_used"] = proxy.host if proxy else None

                if actual_domain == expected_domain:
                    result["status"] = "real"
                    result["cloaking_score"] = 0.0
                else:
                    result["status"] = "decoy"
                    result["cloaking_score"] = 1.0

                return result

            except Exception as e:
                logger.error(f"Proxy visit failed: {e}")
                result["error"] = str(e)
                result["status"] = "error"
                return result

        return result

    async def _visit_with_browser(
        self,
        url: str,
        use_proxy: bool = False,
        proxy: ProxyConfig = None
    ) -> Tuple[str, str]:
        """
        Visit URL with Playwright browser.

        Returns:
            Tuple of (final_url, final_domain)
        """
        async with self.browser_pool.acquire() as instance:
            context_config = {}

            if use_proxy and proxy:
                playwright_proxy = self.proxy_manager.get_playwright_proxy()
                if playwright_proxy:
                    context_config["proxy"] = playwright_proxy

            page = await instance.context.new_page()

            try:
                # Track final URL after all redirects
                final_urls = []

                page.on("framenavigated", lambda frame: final_urls.append(frame.url))

                response = await page.goto(url, wait_until="networkidle")

                # Give extra time for JS redirects
                await asyncio.sleep(2)

                # Get final URL
                final_url = page.url
                final_domain = urlparse(final_url).netloc

                return final_url, final_domain

            finally:
                await page.close()

    def _extract_geo_from_domain(self, domain: str) -> Optional[str]:
        """Extract geo hint from domain (e.g., .co.uk -> UK)."""
        geo_map = {
            ".com.br": "BR",
            ".co.uk": "UK",
            ".ca": "CA",
            ".com.au": "AU",
            ".de": "DE",
            ".fr": "FR",
            ".es": "ES",
            ".mx": "MX"
        }

        for tld, geo in geo_map.items():
            if domain.endswith(tld):
                return geo

        return "US"  # Default
```

---

## 7. CLOAKING BYPASS STRATEGY

### Decision Tree (Pseudocode)

```
FUNCTION classify_ad(ad):
    fbclid = extract_fbclid(ad.direct_url)
    lander_url = extract_lander_url(ad.direct_url)
    expected_domain = extract_domain(lander_url)

    # ATTEMPT 1: Visit with fbclid, no proxy
    try:
        visit_url = lander_url + "?fbclid=" + fbclid
        final_url, actual_domain = browser.visit(visit_url)

        IF actual_domain == expected_domain:
            RETURN { status: "REAL", score: 0.0, method: "fbclid_only" }
        ELSE:
            # Reached decoy - cloaking is working
            RETURN { status: "DECOY", score: 1.0, method: "fbclid_only",
                     expected: expected_domain, actual: actual_domain }
    EXCEPT timeout/error:
        PASS  # Fall through to proxy attempt

    # ATTEMPT 2: Visit with proxy
    geo = get_geo_for_domain(expected_domain)
    proxy = proxy_manager.get_proxy(geo)

    try:
        final_url, actual_domain = browser.visit(lander_url, proxy=proxy)

        IF actual_domain == expected_domain:
            RETURN { status: "REAL", score: 0.0, method: "proxy_used" }
        ELSE:
            RETURN { status: "DECOY", score: 1.0, method: "proxy_used",
                     expected: expected_domain, actual: actual_domain }
    EXCEPT timeout/error:
        RETURN { status: "UNKNOWN", score: 0.5, error: "Connection failed" }
```

### Cloaking Score Calculation

```python
def calculate_cloaking_score(classification: dict) -> float:
    """
    Calculate a 0.0-1.0 cloaking score.

    0.0 = Clean (no cloaking detected)
    0.5 = Unknown (couldn't verify)
    1.0 = Fully cloaked (decoy detected)
    """

    status = classification.get("status")
    method = classification.get("method")
    expected = classification.get("expected_domain", "")
    actual = classification.get("actual_domain", "")

    if status == "real":
        # Clean visit - either no cloaking or we passed it
        if method == "fbclid_only":
            return 0.0  # Clean with fbclid = no cloaking detected
        else:
            return 0.2  # Had to use proxy - possible IP check

    elif status == "decoy":
        # Decoy detected - definitely cloaked
        if expected and actual:
            # Calculate how different (subdomain spoofing vs different domain)
            if expected.split(".")[-1] != actual.split(".")[-1]:
                return 1.0  # Completely different domain
            else:
                return 0.8  # Similar domain, subdomain spoofing

    else:  # unknown, error
        return 0.5  # Couldn't determine
```

---

## 8. SHARED SYSTEM INTEGRATION

### 8.1 Logging System

**Location:** `C:/AI_STACK/AI_PRODUCT_FACTORY/SHARED_SYSTEMS/logging_system/`

**Integration:**

```python
# backend/main.py

import sys
sys.path.insert(0, "C:/AI_STACK/AI_PRODUCT_FACTORY/SHARED_SYSTEMS/logging_system")

from logging_core import get_logger

# Initialize root logger
logger = get_logger(
    "adsrecon",
    level="INFO",
    log_file="C:/AI_STACK/ADSRECON/logs/adsrecon.log"
)

# Create module loggers
scraper_logger = get_logger("adsrecon.scraper", log_file="C:/AI_STACK/ADSRECON/logs/scraper.log")
browser_logger = get_logger("adsrecon.browser", log_file="C:/AI_STACK/ADSRECON/logs/browser.log")
classifier_logger = get_logger("adsrecon.classifier", log_file="C:/AI_STACK/ADSRECON/logs/classifier.log")
```

**What to log:**

| Event | Level | Data |
|-------|-------|------|
| API request received | INFO | endpoint, method, api_key (masked) |
| Scrape job started | INFO | page_id, geo |
| Scrape job completed | INFO | page_id, ads_found, duration_ms |
| Ad classification | INFO | ad_id, status, method, score |
| Browser acquired | DEBUG | browser_id, pool_size |
| Browser error | ERROR | browser_id, error_message |
| Proxy rotation | DEBUG | proxy_host, geo |
| Rate limit hit | WARNING | endpoint, retry_after |
| Lander rip completed | INFO | lander_id, status, duration_ms |

### 8.2 Config System

**Location:** `C:/AI_STACK/AI_PRODUCT_FACTORY/SHARED_SYSTEMS/config_system/`

**Environment Variables (.env):**

```bash
# ADSRECON Configuration

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Database
DATABASE_URL=sqlite:///C:/AI_STACK/ADSRECON/data/adsrecon.db

# Browser Pool
BROWSER_POOL_SIZE=3
BROWSER_HEADLESS=true
BROWSER_TIMEOUT_MS=30000

# DataImpulse Proxies
DATAIMPULSE_API_KEY=your_api_key_here
PROXY_ENABLED=true
PROXY_ROTATION_STRATEGY=random

# Meta Scraper
META_SCRAPE_DELAY_MS=2000
META_RATE_LIMIT_PER_MINUTE=30
META_USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36

# File Storage
STORAGE_PATH=C:/AI_STACK/ADSRECON/storage
SCREENSHOT_FORMAT=png
HTML_SANITIZE=true

# Security
API_KEY_HEADER=X-API-Key
CORS_ORIGINS=http://localhost:5173,https://app.adsrecon.com
RATE_LIMIT_PER_MINUTE=60

# Logging
LOG_LEVEL=INFO
LOG_PATH=C:/AI_STACK/ADSRECON/logs
```

**Config Loading:**

```python
# backend/config.py

from pathlib import Path
from dataclasses import dataclass
import os

@dataclass
class Config:
    """Application configuration."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Paths
    base_dir: Path = Path(__file__).parent.parent
    data_dir: Path = base_dir / "data"
    storage_dir: Path = base_dir / "storage"
    log_dir: Path = base_dir / "logs"

    # Browser
    browser_pool_size: int = 3
    browser_headless: bool = True
    browser_timeout_ms: int = 30000

    # Proxies
    proxy_enabled: bool = True
    dataimpulse_api_key: str = ""

    # Meta
    meta_scrape_delay_ms: int = 2000
    meta_rate_limit_per_minute: int = 30

    # Storage
    screenshot_format: str = "png"
    html_sanitize: bool = True

    @classmethod
    def from_env(cls):
        """Load config from environment variables."""
        return cls(
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            proxy_enabled=os.getenv("PROXY_ENABLED", "true").lower() == "true",
            dataimpulse_api_key=os.getenv("DATAIMPULSE_API_KEY", ""),
            browser_pool_size=int(os.getenv("BROWSER_POOL_SIZE", "3")),
            # ... etc
        )


# Singleton config instance
config = Config.from_env()

# Ensure directories exist
config.data_dir.mkdir(parents=True, exist_ok=True)
config.storage_dir.mkdir(parents=True, exist_ok=True)
config.log_dir.mkdir(parents=True, exist_ok=True)
```

### 8.3 Agent Framework

**Location:** `C:/AI_STACK/AI_PRODUCT_FACTORY/SHARED_SYSTEMS/agent_framework/`

**Usage:** The agent framework is primarily for the APFMS pipeline. For ADSRECON, autonomous agents would be useful for:

1. **Scheduled Campaign Scraper Agent** - Runs on cron to scrape competitor pages
2. **Trend Analysis Agent** - Identifies patterns in competitor ads over time
3. **Alert Agent** - Notifies when new competitors enter the market

```python
# backend/agents/campaign_monitor.py

"""
Campaign Monitor Agent
Periodically scrapes competitor pages and alerts on changes.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List
import logging

logger = logging.getLogger("adsrecon.agent.campaign_monitor")


class CampaignMonitorAgent:
    """
    Autonomous agent that monitors competitor campaigns.

    Runs every N hours:
    1. Fetch active campaigns from DB
    2. For each campaign, scrape competitor page
    3. Compare new ads to previous scrape
    4. Alert on new ads (especially REAL ones)
    5. Update last_scrape_at timestamp
    """

    def __init__(
        self,
        scraper_service,
        classifier_service,
        db,
        alert_service
    ):
        self.scraper = scraper_service
        self.classifier = classifier_service
        self.db = db
        self.alerts = alert_service

    async def run(self):
        """Main agent loop."""
        logger.info("Campaign monitor agent starting")

        campaigns = await self.db.get_active_campaigns()

        for campaign in campaigns:
            if not self._should_scrape(campaign):
                continue

            logger.info(f"Scraping campaign: {campaign.name}")

            try:
                # Scrape ads
                result = await self.scraper.scrape_page(
                    campaign.competitor_page_id,
                    campaign.geo_targets
                )

                # Find new ads
                new_ads = self._find_new_ads(result.ads, campaign)

                if new_ads:
                    logger.info(f"Found {len(new_ads)} new ads")

                    # Classify new ads
                    for ad in new_ads:
                        if ad.status == "real":
                            await self.alerts.send_alert(
                                type="new_real_ad",
                                campaign=campaign.name,
                                ad=ad
                            )

                # Update campaign
                await self.db.update_campaign(
                    campaign.id,
                    last_scrape_at=datetime.utcnow(),
                    total_ads_found=result.total
                )

            except Exception as e:
                logger.error(f"Campaign scrape failed: {e}")

        logger.info("Campaign monitor agent completed")

    def _should_scrape(self, campaign) -> bool:
        """Check if campaign should be scraped now."""
        if not campaign.is_auto_scrape:
            return False

        if not campaign.last_scrape_at:
            return True

        interval = timedelta(hours=campaign.scrape_interval_hours)
        return datetime.utcnow() - campaign.last_scrape_at >= interval

    def _find_new_ads(self, current_ads: List, campaign) -> List:
        """Find ads that are new since last scrape."""
        previous_ids = campaign.last_ad_ids  # From DB
        return [ad for ad in current_ads if ad.library_id not in previous_ids]
```

---

## 9. FILE STRUCTURE

```
C:/AI_STACK/ADSRECON/
│
├── ARCHITECTURE.md                    # This file
├── README.md                          # Quick start guide
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment template
├── pyproject.toml                    # Project metadata
│
├── backend/
│   ├── main.py                        # FastAPI app entry point
│   ├── config.py                      # Configuration loader
│   │
│   ├── __init__.py
│   │
│   ├── api/                           # API route handlers
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py              # Main API router
│   │   │   ├── scrape.py              # Scraping endpoints
│   │   │   ├── classify.py             # Classification endpoints
│   │   │   ├── rip.py                  # Lander ripping endpoints
│   │   │   ├── video.py                # Video extraction endpoints
│   │   │   ├── analytics.py            # Analytics endpoints
│   │   │   └── campaigns.py             # Campaign management
│   │   └── deps.py                     # Dependency injection
│   │
│   ├── services/                      # Business logic
│   │   ├── __init__.py
│   │   ├── meta_scraper.py            # Facebook Ads Library scraper
│   │   ├── cloaking_bypass.py          # Cloaking detection logic
│   │   ├── browser_pool.py            # Playwright browser management
│   │   ├── proxy_manager.py            # DataImpulse proxy rotation
│   │   ├── lander_ripper.py            # Landing page ripping
│   │   ├── video_extractor.py          # Video download/extraction
│   │   ├── nutra_classifier.py         # Nutra vertical classification
│   │   └── html_sanitizer.py           # HTML sanitization
│   │
│   ├── models/                        # Pydantic data models
│   │   ├── __init__.py
│   │   ├── ad.py                      # Ad model
│   │   ├── variation.py                # Variation model
│   │   ├── lander.py                  # Lander model
│   │   ├── campaign.py                # Campaign model
│   │   └── api.py                     # API request/response models
│   │
│   ├── db/                            # Database layer
│   │   ├── __init__.py
│   │   ├── database.py                # SQLite connection
│   │   ├── schema.py                  # Table definitions
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── ad_repository.py
│   │   │   ├── lander_repository.py
│   │   │   └── campaign_repository.py
│   │   └── migrations/
│   │       └── 001_initial.sql
│   │
│   ├── agents/                        # Autonomous agents
│   │   ├── __init__.py
│   │   ├── campaign_monitor.py        # Scheduled competitor monitoring
│   │   └── trend_analyzer.py           # Pattern detection
│   │
│   └── utils/                         # Utilities
│       ├── __init__.py
│       ├── url_utils.py               # URL parsing/manipulation
│       ├── domain_utils.py            # Domain extraction
│       └── hash_utils.py              # Content hashing
│
├── frontend/
│   ├── index.html                     # SPA entry point
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   │
│   ├── src/
│   │   ├── main.js                    # React entry
│   │   ├── App.jsx                    # Root component
│   │   ├── index.css                  # Tailwind imports
│   │   │
│   │   ├── api/                       # API client
│   │   │   └── client.js              # Fetch wrapper
│   │   │
│   │   ├── components/                # UI components
│   │   │   ├── SearchBar.jsx
│   │   │   ├── AdCard.jsx
│   │   │   ├── AdGrid.jsx
│   │   │   ├── RipPanel.jsx
│   │   │   ├── PreviewFrame.jsx
│   │   │   ├── GeoSelector.jsx
│   │   │   ├── StatusBadge.jsx
│   │   │   └── VideoPlayer.jsx
│   │   │
│   │   ├── pages/                    # Route pages
│   │   │   ├── Dashboard.jsx
│   │   │   ├── AdSearch.jsx
│   │   │   ├── CampaignDetail.jsx
│   │   │   └── Analytics.jsx
│   │   │
│   │   └── hooks/                    # Custom React hooks
│   │       ├── useApi.js
│   │       └── usePolling.js
│   │
│   └── public/
│       └── favicon.ico
│
├── storage/                           # File storage (created at runtime)
│   ├── screenshots/
│   │   └── {ad_id}/
│   │       └── {timestamp}.png
│   │
│   ├── landers/
│   │   └── {lander_id}/
│   │       ├── index.html
│   │       ├── screenshot.png
│   │       └── thumb.png
│   │
│   └── videos/
│       └── {ad_id}/
│           ├── video.mp4
│           └── thumb.jpg
│
├── data/                              # SQLite database (created at runtime)
│   └── adsrecon.db
│
├── logs/                              # Application logs (created at runtime)
│   ├── adsrecon.log
│   ├── scraper.log
│   ├── browser.log
│   └── classifier.log
│
└── tests/
    ├── __init__.py
    ├── conftest.py                    # Pytest fixtures
    ├── test_scraper.py
    ├── test_classifier.py
    ├── test_browser_pool.py
    ├── test_api.py
    └── fixtures/
        ├── sample_ads_response.html
        └── sample_lander_page.html
```

---

## 10. TECHNOLOGY CHOICES

| Component | Choice | Reason |
|-----------|--------|--------|
| **Backend Framework** | FastAPI | Async support for concurrent browser operations; auto-generated OpenAPI docs; Pydantic for validation; easy dependency injection |
| **Database** | SQLite | Zero setup; perfect for single-VPS deployment; ACID compliant; sufficient for <100K records |
| **Browser Automation** | Playwright | Better than Selenium for headless; async support; strong iframe/redirect handling; mobile emulation built-in |
| **HTTP Client** | httpx | Async support; automatic retry; connection pooling; proxy support; browser-like headers |
| **HTML Parsing** | BeautifulSoup4 + lxml | Mature; fast parsing; easy CSS selectors; good for extraction |
| **Frontend Framework** | React + Vite | Component-based; fast HMR for development; large ecosystem; React Query for API state |
| **Styling** | Tailwind CSS | Utility-first; no context switching; small bundle size; easy responsive design |
| **API State** | TanStack Query (React Query) | Automatic caching; background refetch; loading/error states |
| **Video Processing** | FFmpeg (subprocess) | Best quality; widely supported; Python bindings |
| **HTML Sanitization** | bleach | Whitelist-based; strips all JS/events; safe defaults |
| **URL Analysis** | tldextract | Correct TLD parsing; handles country TLDs (.co.uk, .com.br) |
| **Content Hashing** | hashlib (SHA256) | Duplicate detection; integrity verification |

### Why NOT Alternatives

| Rejected | Reason |
|----------|--------|
| **PostgreSQL** | Overkill for single-VPS; adds deployment complexity |
| **Selenium** | Slower; less async-native; larger footprint |
| **Scrapy** | Overkill; not needed for single-page scraping |
| **Vue/Svelte** | Less familiar; smaller ecosystem |
| **Django** | Too heavy; not needed for API-only backend |
| **Next.js** | Would need separate backend; unnecessary complexity |

---

## 11. SECURITY CONSIDERATIONS

### 11.1 HTML Sanitization

**Critical**: Ripped HTML must be sanitized before serving to prevent XSS.

```python
# backend/services/html_sanitizer.py

import bleach
from bleach.css_sanitizer import CSSSanitizer

# Allowed tags (whitelist approach)
ALLOWED_TAGS = [
    'html', 'head', 'body', 'title', 'meta', 'link',
    'div', 'span', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'a', 'img', 'video', 'audio', 'source',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'form', 'input', 'select', 'option', 'textarea', 'button', 'label',
    'section', 'article', 'header', 'footer', 'nav', 'aside', 'main',
    'br', 'hr', 'strong', 'em', 'b', 'i', 'u', 's',
    'blockquote', 'pre', 'code',
    'svg', 'path', 'rect', 'circle', 'g', 'use'
]

# Allowed attributes per tag
ALLOWED_ATTRIBUTES = {
    '*': ['class', 'id', 'style'],
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'width', 'height', 'loading'],
    'video': ['src', 'controls', 'autoplay', 'loop', 'muted', 'poster', 'width', 'height'],
    'audio': ['src', 'controls', 'autoplay', 'loop', 'muted'],
    'source': ['src', 'type'],
    'input': ['type', 'name', 'value', 'placeholder', 'required', 'disabled'],
    'select': ['name', 'required', 'disabled'],
    'option': ['value', 'selected', 'disabled'],
    'textarea': ['name', 'placeholder', 'required', 'rows', 'cols'],
    'button': ['type', 'name', 'value', 'disabled'],
    'form': ['action', 'method', 'target'],
    'meta': ['name', 'content', 'property'],
    'link': ['rel', 'href', 'type', 'media', 'integrity'],
    'style': [],  # Inline styles stripped unless whitelisted
    # SVG attributes
    'svg': ['xmlns', 'viewBox', 'width', 'height', 'fill', 'stroke'],
    'path': ['d', 'fill', 'stroke', 'stroke-width', 'transform'],
    'rect': ['x', 'y', 'width', 'height', 'fill', 'rx', 'ry'],
    'circle': ['cx', 'cy', 'r', 'fill'],
    'g': ['transform', 'fill', 'stroke'],
    'use': ['href', 'xlink:href'],
}

# CSS properties to allow
ALLOWED_CSS_PROPERTIES = [
    'color', 'background-color', 'font-family', 'font-size', 'font-weight',
    'text-align', 'margin', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
    'padding', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
    'border', 'border-radius', 'width', 'height', 'max-width', 'min-height',
    'display', 'flex', 'flex-direction', 'justify-content', 'align-items',
    'position', 'top', 'left', 'right', 'bottom', 'z-index',
    'opacity', 'visibility', 'overflow', 'line-height'
]


class HTMLSanitizer:
    """Sanitize ripped HTML to prevent XSS attacks."""

    def __init__(self):
        self.css_sanitizer = CSSSanitizer(
            css_properties_allowlist=ALLOWED_CSS_PROPERTIES
        )

    def sanitize(self, html: str) -> str:
        """
        Remove dangerous content from HTML.

        Strips:
        - All <script> tags
        - All event handlers (onclick, onerror, etc.)
        - javascript: URLs
        - <iframe>, <object>, <embed> tags
        - External resource loading (unless safe)
        """
        if not html:
            return ""

        # Step 1: Strip dangerous tags completely
        html = bleach.clean(
            html,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            css_sanitizer=self.css_sanitizer,
            strip=True,
            strip_comments=True
        )

        # Step 2: Rewrite URLs to be safe
        html = self._rewrite_urls(html)

        # Step 3: Remove data: URLs (potential XSS vector)
        html = self._remove_data_urls(html)

        # Step 4: Add sandbox attribute to iframe if we allow it
        # (Currently iframes are not allowed)

        return html

    def _rewrite_urls(self, html: str) -> str:
        """Ensure URLs don't use javascript: protocol."""
        import re

        # Remove javascript: from href attributes
        html = re.sub(
            r'href=["\']javascript:[^"\']*["\']',
            'href="#"',
            html,
            flags=re.IGNORECASE
        )

        # Remove javascript: from src attributes
        html = re.sub(
            r'src=["\']javascript:[^"\']*["\']',
            'src=""',
            html,
            flags=re.IGNORECASE
        )

        return html

    def _remove_data_urls(self, html: str) -> str:
        """Remove data: URLs which can contain executable content."""
        import re

        # Remove data: URLs from src
        html = re.sub(
            r'src=["\']data:[^"\']*["\']',
            'src=""',
            html
        )

        return html
```

### 11.2 Proxy Credential Storage

```python
# Proxy credentials are NEVER stored in code or DB

# .env file (gitignored)
DATAIMPULSE_API_KEY=di_live_xxxxxxxxxxxxxxxx

# Proxy rotation uses the API key to fetch session credentials
# No hardcoded credentials anywhere
```

### 11.3 Rate Limiting

```python
# backend/api/deps.py

from fastapi import Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
import time

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


async def rate_limit_check(request: Request):
    """Check rate limit for API key or IP."""
    # Get identifier (API key if present, else IP)
    api_key = request.headers.get("X-API-Key")
    identifier = api_key or get_remote_address(request)

    # Check against limiter
    # Implementation depends on chosen rate limiting library

    return True


@router.post("/scrape/page")
@limiter.limit("30/minute")  # Meta rate limit
async def scrape_page(request: Request, body: ScrapeRequest):
    await rate_limit_check(request)
    # ...
```

### 11.4 Screenshot Storage

```python
# Screenshots stored with random UUIDs to prevent enumeration
import uuid
from pathlib import Path

def save_screenshot(browser_page, lander_id: str) -> str:
    """Save screenshot with secure random filename."""
    filename = f"{uuid.uuid4().hex}.png"
    path = Path(config.storage_dir) / "screenshots" / lander_id
    path.mkdir(parents=True, exist_ok=True)

    full_path = path / filename
    await browser_page.screenshot(path=full_path, full_page=True)

    # Return relative path (no lander_id enumeration for non-owners)
    return f"/files/screenshots/{lander_id}/{filename}"
```

---

## 12. SCALABILITY NOTES

### 12.1 At 1,000 Ads

| Concern | Solution |
|---------|----------|
| **Database size** | SQLite handles 1M rows easily. Add indexes on frequently queried columns. |
| **Screenshot storage** | ~10MB per screenshot = 10GB for 1000. Use compression or WebP format. |
| **API response time** | Add pagination to `/ads` endpoint. Default page size: 50. |
| **Memory** | SQLite is RAM-mapped; ensure adequate RAM for hot data. |

### 12.2 At 10 Concurrent Users

| Concern | Solution |
|---------|----------|
| **Browser pool exhaustion** | Pool size of 3 handles 10 users with queuing. Average rip: 8s, so throughput: ~22/hr/pool. |
| **Meta rate limiting** | Implement per-user rate limiting. 30 requests/min/user = 300 total. |
| **Database contention** | SQLite WAL mode handles concurrent reads. Writes are serialized. |
| **Memory pressure** | Browser pool uses ~1GB RAM. With 3 browsers + OS: ~4GB total. |
| **CPU** | Meta scraping is I/O-bound. Ripper is CPU-bound (HTML parsing). |

### 12.3 Bottlenecks

```
Bottleneck Analysis:

1. Meta Scraper (HIGH)
   - Facebook blocks aggressive scraping
   - Solution: Add delays, rotate user agents, use cached data

2. Browser Pool (MEDIUM)
   - 3 browsers = 3 concurrent rips
   - Solution: Scale pool to 5-10 on larger VPS

3. Video Download (LOW-MEDIUM)
   - Large files, slow downloads
   - Solution: Async download queue, download only on demand

4. HTML Sanitization (LOW)
   - Fast with lxml backend
   - Solution: N/A

5. Database (LOW)
   - SQLite handles thousands of writes/second
   - Solution: Batch inserts, add indexes
```

### 12.4 Horizontal Scaling Considerations

If/when moving to multi-server:

```python
# Current architecture (single VPS):
# User → FastAPI → Browser Pool (local) → Meta/Facebook

# Future architecture (multi-server):
# User → Load Balancer → API Servers (stateless)
#                           ↓
#                    Celery Workers (separate VMs)
#                           ↓
#                    Browser Pool (per worker)
#                           ↓
#                    Shared Storage (S3) + Shared DB (PostgreSQL)
```

**Migration path:**
1. Add Redis for job queue
2. Move DB to PostgreSQL
3. Deploy workers on separate machines
4. Move storage to S3-compatible storage
5. API servers become stateless

---

## 13. REUSE FROM EXISTING CODE

### From ADSPY_ELITE Chrome Extension

| Component | Reuse Strategy |
|-----------|----------------|
| `domain.js` | Convert to `backend/utils/domain_utils.py` using tldextract |
| `affiliate.js` | Convert to `backend/services/affiliate_detector.py` |
| `video.js` | Convert to `backend/services/video_extractor.py` (adapt selectors) |
| `exporter.js` | Keep as frontend feature (client-side CSV/JSON export) |

### From Shared Systems

| System | Integration |
|--------|-------------|
| `logging_system` | Import `get_logger` in each backend module |
| `config_system` | Use `.env` loading pattern from shared config |

---

## 14. IMPLEMENTATION PRIORITY

### Phase 1: Core MVP (Week 1)
1. Backend setup with FastAPI
2. Database schema and repositories
3. Meta scraper service
4. Basic ad API endpoints
5. Frontend ad search UI

### Phase 2: Cloaking Detection (Week 2)
1. Browser pool implementation
2. Cloaking bypass service (fbclid-first)
3. Proxy integration
4. Classification endpoints
5. Status badges in UI

### Phase 3: Lander Ripping (Week 3)
1. Lander ripper service
2. HTML sanitization
3. Screenshot capture
4. Preview panel in UI
5. HTML download

### Phase 4: Polish (Week 4)
1. Video extraction
2. Nutra classifier
3. Analytics dashboard
4. Campaign monitoring agent
5. Rate limiting and security

---

## 15. CRITICAL CODE SNIPPETS

### 15.1 Meta URL Extraction

```python
# backend/services/meta_scraper.py

import re
from urllib.parse import urlparse, parse_qs

def extract_page_id(url: str) -> Optional[str]:
    """
    Extract Facebook page ID from various URL formats.

    Handles:
    - https://www.facebook.com/ExampleBrand
    - https://www.facebook.com/ExampleBrand/
    - https://www.facebook.com/ExampleBrand/?__xts__[0]=...
    - https://www.facebook.com/pages/ExampleBrand/123456789
    - https://m.facebook.com/ExampleBrand
    """
    # Remove m. prefix for consistency
    url = url.replace("m.facebook.com", "www.facebook.com")

    # Try username format: /PageName or /PageName/
    match = re.match(r'facebook\.com/([^/?]+)/?', url)
    if match:
        username = match.group(1)
        if username.lower() != "pages":
            return username  # This is the page name/username

    # Try page ID format: /pages/name/id or /pages/id
    match = re.search(r'facebook\.com/pages/[^/]+/(\d+)', url)
    if match:
        return match.group(1)

    # Try query param: ?page_id=123
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    if 'page_id' in params:
        return params['page_id'][0]

    return None
```

### 15.2 fbclid Extraction (Complete)

```python
# backend/services/fbclid_utils.py

from urllib.parse import urlparse, parse_qs, unquote
import re

def extract_from_meta_redirect(url: str) -> tuple[Optional[str], Optional[str]]:
    """
    Extract fbclid and lander URL from Meta's redirect URL.

    Input:  https://l.facebook.com/l.php?u=https%3A%2F%2Freal-lander.top%2Foffer%3Futm%3Dtest&fbclid=IwZXh0bgNhZW0CMTAA...

    Returns:
        (fbclid, lander_url)
        ("IwZXh0bgNhZW0CMTAA...", "https://real-lander.top/offer?utm=test")
    """
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        fbclid = params.get("fbclid", [None])[0]

        # The 'u' param contains the redirect URL, URL-encoded
        encoded_url = params.get("u", [None])[0]
        if encoded_url:
            lander_url = unquote(unquote(encoded_url))  # Double-encoded sometimes
        else:
            lander_url = None

        return fbclid, lander_url

    except Exception:
        return None, None


def append_fbclid_to_url(url: str, fbclid: str) -> str:
    """
    Safely append fbclid to a URL.

    Handles:
    - URL without query params: lander.com → lander.com?fbclid=xxx
    - URL with query params: lander.com/?utm=x → lander.com/?utm=x&fbclid=xxx
    - URL with fragments: lander.com#section → lander.com?fbclid=xxx#section
    """
    from urllib.parse import urlparse, urlencode, urlunparse, parse_qs

    parsed = urlparse(url)

    # Parse existing query params
    existing_params = parse_qs(parsed.query)
    existing_params["fbclid"] = [fbclid]

    # Re-encode
    new_query = urlencode(existing_params, safe="")

    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment  # Keep fragment
    ))
```

### 15.3 Nutra Vertical Classification

```python
# backend/services/nutra_classifier.py

from dataclasses import dataclass
from typing import List, Tuple
import re


@dataclass
class NutraCategory:
    name: str
    keywords: List[str]
    weight: float  # Higher = more important


NUTRA_VERTICALS = {
    "weight_loss": NutraCategory(
        name="Weight Loss",
        keywords=[
            "weight loss", "lose weight", "fat burner", "slim", "keto",
            "belly fat", "burn fat", "weight reduction", "detox", "cleanse",
            "lose inches", "thinner", "skinny", "fitness", "appetite suppressant",
            " Garcinia", "Apple Cider Vinegar", "Raspberry Ketone"
        ],
        weight=1.0
    ),
    "male_enhancement": NutraCategory(
        name="Male Enhancement",
        keywords=[
            "male enhancement", "penis enlargement", "erectile dysfunction",
            "ED treatment", "bigger penis", "male performance", "libido booster",
            "testosterone booster", "stamina", "sexual performance"
        ],
        weight=1.0
    ),
    "skin_care": NutraCategory(
        name="Skin Care",
        keywords=[
            "skin clearing", "acne", "wrinkle", "anti aging", "younger looking",
            "skin cream", "glow", "fairness", "skin tone", "melasma",
            "dermatologist", "complexion", "radiant skin"
        ],
        weight=1.0
    ),
    "blood_sugar": NutraCategory(
        name="Blood Sugar",
        keywords=[
            "blood sugar", "diabetes", "A1C", "glucose", "insulin",
            "sugar control", "diabetic", "blood glucose", "prediabetic"
        ],
        weight=1.0
    ),
    "joint_pain": NutraCategory(
        name="Joint Pain",
        keywords=[
            "joint pain", "arthritis", "joint health", "flexibility",
            "mobility", "glucosamine", "chondroitin", "MSM", "creaky joints",
            "stiff joints", "bone health"
        ],
        weight=1.0
    ),
    "memory_focus": NutraCategory(
        name="Memory & Focus",
        keywords=[
            "memory", "focus", "concentration", "brain health", "cognitive",
            "mental clarity", "alertness", "nootropic", "brain fog",
            "mind sharp", "learning", "study"
        ],
        weight=1.0
    ),
    "sleep_stress": NutraCategory(
        name="Sleep & Stress",
        keywords=[
            "sleep", "insomnia", "melatonin", "relaxation", "stress",
            "anxiety", "calm", "rest", "sleep aid", "natural sleep",
            "deep sleep", "sleeping"
        ],
        weight=1.0
    ),
    "eye_health": NutraCategory(
        name="Eye Health",
        keywords=[
            "eye health", "vision", " eyesight", "macular degeneration",
            "cataract", "glaucoma", "retina", "eye formula", "lutein",
            "zeaxanthin", "blue light", "visual acuity"
        ],
        weight=1.0
    ),
    "heart_health": NutraCategory(
        name="Heart Health",
        keywords=[
            "heart health", "cholesterol", "blood pressure", "cardiovascular",
            "arterial plaque", "heart attack", "stroke", "circulation",
            "omega 3", "coq10", "hawthorn"
        ],
        weight=1.0
    ),
    "prostate": NutraCategory(
        name="Prostate",
        keywords=[
            "prostate", "BPH", "urinary", "bladder", "prostate health",
            "night time urination", "saw palmetto"
        ],
        weight=1.0
    ),
    "teeth_whitening": NutraCategory(
        name="Teeth Whitening",
        keywords=[
            "teeth whitening", "whiter teeth", "smile", "dental",
            "stain removal", "enamel", "crowns", " veneers"
        ],
        weight=0.8  # Lower because it's common outside Nutra
    ),
    "anti_aging": NutraCategory(
        name="Anti-Aging",
        keywords=[
            "anti aging", "youth", "reverse aging", " longevity",
            "NMN", "resveratrol", "telomere", "younger", "agen"
        ],
        weight=0.9
    )
}


class NutraClassifier:
    """Classify ad content into Nutra verticals."""

    def __init__(self):
        self.categories = NUTRA_VERTICALS

    def classify(self, text: str) -> Tuple[str, float]:
        """
        Classify text into Nutra vertical.

        Args:
            text: Ad headline, body, or combined text

        Returns:
            (vertical_name, confidence_score)
            e.g., ("weight_loss", 0.85)
        """
        text_lower = text.lower()

        scores = {}
        for vertical_id, category in self.categories.items():
            score = 0.0
            for keyword in category.keywords:
                # Count occurrences
                count = text_lower.count(keyword.lower())
                if count > 0:
                    score += count * category.weight

            if score > 0:
                scores[vertical_id] = score

        if not scores:
            return ("uncategorized", 0.0)

        # Get best match
        best_vertical = max(scores, key=scores.get)
        best_score = scores[best_vertical]

        # Normalize to 0-1 confidence
        max_possible = len(self.categories[best_vertical].keywords)
        confidence = min(best_score / 3.0, 1.0)  # Cap at 1.0

        return (best_vertical, confidence)

    def classify_ad(self, ad: dict) -> Tuple[str, float]:
        """
        Classify full ad into Nutra vertical.

        Combines: headline + body + page_title + CTA
        """
        combined = " ".join(filter(None, [
            ad.get("page_title", ""),
            ad.get("ad_body", ""),
            ad.get("cta_text", "")
        ]))

        return self.classify(combined)
```

---

## 16. DEPLOYMENT CHECKLIST

Before production deployment:

- [ ] Install Playwright browsers: `playwright install chromium`
- [ ] Set up DataImpulse account and get API key
- [ ] Configure .env with production values
- [ ] Set up reverse proxy (nginx/Caddy) for HTTPS
- [ ] Configure firewall (only allow 80/443 for web, SSH for management)
- [ ] Set up automated backups of SQLite database
- [ ] Configure log rotation (weekly)
- [ ] Set up monitoring (CPU, RAM, disk alerts)
- [ ] Test rate limiting works correctly
- [ ] Verify HTML sanitization strips all JS
- [ ] Set up CDN for static assets (optional)

---

**END OF ARCHITECTURE DOCUMENT**
