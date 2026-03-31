# ADSRECON -- Product Requirements Document

**Version:** 1.0
**Date:** 2026-03-31
**Product:** ADSRECON -- Facebook Ads Intelligence for Nutra Affiliate Marketers
**Status:** Draft for Architect & Coder Handoff

---

## 1. PRODUCT VISION

ADSRECON is a self-hosted intelligence platform that pierces the veil of Facebook ad cloaking to expose what nutra affiliate marketers are actually running. While Meta's Ads Library shows clean decoy ads, ADSRECON uses the `fbclid` parameter (Meta's own tracking token embedded in every Facebook click redirect) as the key to unlock the real, cloaked landing pages -- without expensive residential proxies. ADSRECON crawls competitor pages, extracts all ad variations (decoy vs. real), rips the actual landing pages behind the cloak, classifies every ad by nutra vertical (blood sugar, weight loss, prostate, skin, joint, energy, gut, male, female, anti-aging, eyes, heart), and delivers downloadable creatives in a searchable, project-organized interface. The result: affiliate marketers stop guessing which ads are live offers and start building campaigns backed by real intelligence.

---

## 2. USER STORIES

### US-01: Search by Competitor Page URL
**As a** nutra affiliate marketer **I want to** enter a competitor's Facebook Page URL **so that** I can see all ads that page has run across supported countries.

**Acceptance Criteria:**
- Input field accepts URL in formats: `https://facebook.com/pagename`, `https://www.facebook.com/pagename`, or bare `pagename`
- System resolves page to Meta Ads Library format and fetches all active + historical ads
- Results display in a table with columns: Ad Preview thumbnail, Ad Text (truncated), Status (Active/Inactive), Start Date, End Date, Impressions estimate, Number of Variations
- User can paginate through results (50 ads per page)
- Error handling: page not found, page has no ads, rate limited

**Priority:** MUST HAVE (MVP)

---

### US-02: Search Meta Ads Library by Keyword
**As a** nutra affiliate marketer **I want to** search ads by keyword across all of Meta's supported countries **so that** I can discover which offers are trending in my vertical.

**Acceptance Criteria:**
- Text input for keyword search (e.g., "blood sugar support", "prostate health", "weight loss")
- Country selector: US, UK, CA, AU, DE, FR, ES, BR, MX (multi-select)
- Date range filter: Last 7 days, 30 days, 90 days, 180 days, 1 year, Custom
- Results show matching ads from all pages, sorted by recency or impressions
- Each result links back to the source page
- Optional: filter by presence of video creatives
- Rate limiting: queue keyword searches, max 10 concurrent

**Priority:** MUST HAVE (MVP)

---

### US-03: View Ad Variations (Decoy vs Real)
**As a** nutra affiliate marketer **I want to** see all variations of a single ad **so that** I can identify which variation is the decoy and which is the real offer.

**Acceptance Criteria:**
- For any ad in the library, click "View Variations" to expand all registered ad creatives
- Each variation shows: preview thumbnail, headline, primary text, CTA button, destination URL (from Meta)
- System marks variations that have known cloaking signatures (e.g., URL contains redirect parameters typical of Keitaro, Bemob, RedTrack)
- Variations are labeled: "Potential Decoy" or "Likely Real Offer" based on URL analysis
- User can compare variations side-by-side
- Total variation count displayed per ad

**Priority:** MUST HAVE (MVP)

---

### US-04: Rip Landing Pages (Cloaking Bypass + Content Extraction)
**As a** nutra affiliate marketer **I want to** click a button and see the actual landing page behind a cloaked ad **so that** I can analyze the VSL, copy, offer structure, and funnel.

**Acceptance Criteria:**
- "Rip Lander" button on every ad variation and ad detail view
- System constructs a click URL using the ad's Facebook redirect URL (with fbclid parameter intact)
- Playwright navigates to the click URL, waits for full page load (5s minimum, 30s max with JS polling)
- System captures: full-page screenshot (desktop 1920x1080), mobile screenshot (390x844), full HTML source, extracted text content, detected tech stack (CMS, tracking pixels, forms)
- For multi-step funnels: detect "Step 1 of 3" patterns, attempt to fill and proceed (optional, off by default)
- Captured data stored in project with timestamp
- Storage: screenshots saved as PNG, HTML as .html file, metadata as JSON
- Fallback: if fbclid bypass fails, attempt with DataImpulse proxy rotation

**Priority:** MUST HAVE (MVP)

---

### US-05: Classify Ads by Nutra Vertical
**As a** nutra affiliate marketer **I want to** see automatic classification of every ad by its nutra category **so that** I can filter and organize intelligence by vertical.

**Acceptance Criteria:**
- System automatically classifies each scraped ad into one of 12 verticals:
  1. Blood Sugar
  2. Weight Loss
  3. Prostate
  4. Skin
  5. Joint
  6. Energy
  7. Gut Health
  8. Male Enhancement
  9. Female Health
  10. Anti-Aging
  11. Eye Health
  12. Heart Health
- Classification based on: ad text keywords, landing page text/content, creative imagery labels
- Confidence score displayed (High / Medium / Low)
- User can override classification and the override is saved
- Bulk re-classification tool for imported ad sets
- Classifier is retrainable from user feedback

**Priority:** MUST HAVE (MVP)

---

### US-06: Filter by Category, Geo, Status
**As a** nutra affiliate marketer **I want to** filter my intelligence view by vertical, country, and ad status **so that** I can focus on the most relevant campaigns.

**Acceptance Criteria:**
- Filter bar with: Vertical (multi-select), Geo (multi-select), Status (Active, Inactive, Any), Date Range, Has Video (yes/no), Has Cloaking (yes/no/unknown), Page Name
- Filters are combinable with AND logic
- Filter state persists in URL for sharing
- Result count updates live as filters change
- "Save Filter" option to name and store filter presets

**Priority:** SHOULD HAVE

---

### US-07: Save Ads to Projects
**As a** nutra affiliate marketer **I want to** organize discovered ads into named projects **so that** I can keep intelligence organized by competitor, vertical, or campaign wave.

**Acceptance Criteria:**
- Create, rename, delete projects
- Add individual ads or entire search results to a project
- Projects display: name, creation date, ad count, last updated
- Within a project: sortable ad list, notes field per ad, tag field per ad
- Project-level stats: total ads, active ads, verticals breakdown, geo breakdown
- Projects stored in local SQLite database (self-hosted)
- Export project as ZIP (screenshots + data)

**Priority:** SHOULD HAVE

---

### US-08: Export Data (CSV / JSON)
**As a** nutra affiliate marketer **I want to** export intelligence data to CSV or JSON **so that** I can import it into my own analytics or分享 it with my team.

**Acceptance Criteria:**
- Export options: All results, Current filter, Selected ads, Single project
- CSV format: ad_id, page_name, vertical, geo, status, start_date, end_date, impressions, variations_count, has_video, has_cloaking, cloaking_service, lander_url, created_at
- JSON format: full structured export including all variation data, lander metadata, screenshots paths
- Download as ZIP for mixed media exports
- Scheduled export: optional daily email/webhook delivery (nice to have)

**Priority:** SHOULD HAVE

---

## 3. FEATURE PRIORITIZATION (MoSCoW)

### MUST HAVE (MVP -- Ship in v1.0)

| # | Feature | Description |
|---|---------|-------------|
| M01 | Meta Ads Library Scraper | No-auth scraping of Meta's public Ads Library API and HTML pages. Fetch ad listings by page URL and keyword search. Parse JSON responses and HTML to extract ad metadata (text, images, links, dates, impressions). Handle pagination. |
| M02 | Variation Extractor | For each ad, fetch and display all registered creative variations. Show variation count, each variation's preview and destination URL. |
| M03 | fbclid Cloaking Bypass | Take the ad's Facebook redirect URL (contains `fbclid` param), feed it to Playwright, and navigate to the cloaked destination. The `fbclid` parameter tells the cloaking service this is a real Facebook visitor -- it serves the real lander. This is the core innovation: no residential proxies needed for the primary flow. |
| M04 | Landing Page Ripper (Playwright) | Headless browser (Playwright with Chromium) navigates to the resolved lander URL, waits for full render, captures screenshot (desktop + mobile), extracts HTML, and pulls text content. Stores results locally. |
| M05 | Nutra Vertical Classifier | Rule-based + keyword-matching classifier that categorizes each ad into one of 12 verticals. Uses ad text, landing page content, and image alt-text for classification. Outputs confidence score. |
| M06 | Multi-Geo Targeting | Support for all 9 countries: US, UK, CA, AU, DE, FR, ES, BR, MX. Pass country parameter to Meta Ads Library requests. Store geo metadata per ad. |
| M07 | Basic Search & Filter UI | Web interface with search bar (page URL + keyword), filter panel (vertical, geo, status), results table with pagination. |
| M08 | SQLite Database Storage | Local SQLite database to store all scraped ads, landing pages, projects, and metadata. Schema defined for scalability. |

### SHOULD HAVE (v1.x -- After MVP)

| # | Feature | Description |
|---|---------|-------------|
| S01 | Desktop vs Mobile Detection | When ripping landers, detect and capture both desktop and mobile variants. Some cloaking services serve different content based on device type. Store both screenshots and note differences. |
| S02 | Video Creative Extraction | For ads with video creatives, extract the video URL from Meta's asset data. Download video to local storage. Fallback: use yt-dlp if URL is a YouTube-hosted video. |
| S03 | Ad Creative Downloader | Download ad images (single and multi-image carousels) to local storage. Organize by ad ID and project. Support batch download. |
| S04 | Project / Campaign Management | Create named projects, add ads to projects, add notes/tags per ad, view project-level analytics. |
| S05 | CSV / JSON Export | Export ad data and project data to CSV and JSON formats. Include full metadata. |
| S06 | Decoy vs Real Classifier | Analyze variation URLs for cloaking service signatures (redirect domains, path patterns). Label each variation as "Potential Decoy" or "Likely Real Offer." Use heuristics: presence of redirect URLs from known cloaking services (Keitaro CPV Lab, Bemob, RedTrack, AppsFlyer, Hyros, Voluum). |
| S07 | Proxy Support (DataImpulse Fallback) | If fbclid bypass fails or Meta rate-limits, rotate through DataImpulse proxies. Config page for proxy key entry, proxy health check, automatic failover. |
| S08 | Trend Tracking (Days Running) | Calculate and display how long each ad has been active. Show "First Seen" and "Last Seen" dates. Track trend: ads gaining impressions vs. declining. |
| S09 | Cloaking Service Detection | Based on URL analysis and response headers, guess which cloaking service an advertiser is using. Show confidence level. Database of known cloaking service signatures. |

### COULD HAVE (v2.0 -- Future)

| # | Feature | Description |
|---|---------|-------------|
| C01 | Alert System | Configure email or webhook alerts when a tracked competitor page starts running new ads. Poll Meta Ads Library on schedule, diff against stored data, trigger alert on new ads detected. |
| C02 | Landing Page Comparison Tool | Side-by-side comparison of two or more landing pages. Highlight differences in copy, CTA, offer structure, price points. |
| C03 | Proxy Health Monitoring | Dashboard showing proxy pool status: response times, success rates, geo coverage. Auto-remove dead proxies. |
| C04 | Multi-Step Funnel Traversal | Auto-detect multi-step funnels (quiz, survey, order form wizard). Auto-fill Step 1 using plausible data and proceed to Step 2+. Store each step's screenshot. |
| C05 | Campaign Cloning Intelligence | Given a competitor's ad, suggest a campaign structure: recommended offer type, lander template, funnel steps, based on detected patterns. |

### WON'T HAVE (This Cycle)

| # | Feature | Reason |
|---|---------|--------|
| W01 | Facebook Auth Integration | Out of scope. ADSRECON works exclusively with the public Meta Ads Library. No login, no token-based API. |
| W02 | Real-Time Ad Monitoring | Streaming/polling of live ad changes is too resource-intensive for v1. Use scheduled batch polls instead. |
| W03 | Built-in Landing Page Builder | This is a spy tool, not a creation tool. Users export data to use in their own tools. |
| W04 | Social Proof Overlay | Detecting fake engagement (comments, shares) is outside the scope. We report what Meta shows. |
| W05 | Mobile App | Web-only for v1. Self-hosted VPS serves the UI. |

---

## 4. SUCCESS METRICS

### SM-01: Landers Uncloaked Rate
**Metric:** Percentage of "Rip Lander" attempts that successfully return a real landing page (non-decoy content).
**Target:** > 75% success rate on first attempt using fbclid method alone. > 90% with DataImpulse proxy fallback.
**Measurement:** Track `rip_attempted`, `rip_success`, `rip_failed` counters per ad in the database. Report: `rip_success / rip_attempted * 100`.
**Why it matters:** If we cannot pierce the cloak reliably, the product has no value. This is the core differentiator.

### SM-02: Ad Intelligence Coverage
**Metric:** Number of unique ads scraped and stored per week, per country.
**Target:** > 500 ads scraped per week across all supported countries for initial seed data.
**Measurement:** `SELECT COUNT(DISTINCT ad_id) FROM ads WHERE scraped_at > NOW() - INTERVAL 7 DAYS GROUP BY geo`.
**Why it matters:** The product only has value if there is a rich dataset to explore. Coverage drives utility.

### SM-03: Classification Accuracy
**Metric:** Percentage of ads correctly classified by the nutra vertical classifier (based on user corrections).
**Target:** > 85% accuracy before user correction.
**Measurement:** After users correct classifications, compute `correct / (correct + incorrect)` and track over time. Aim for > 90% accuracy after 100+ corrections with retraining.
**Why it matters:** Users trust the product more when vertical filters work reliably. Poor classification undermines the core workflow.

### SM-04: Time to First Insight
**Metric:** Elapsed time from user entering a competitor page URL to seeing the first ripped landing page.
**Target:** < 3 minutes from URL input to first lander screenshot available in the UI.
**Measurement:** Log timestamps: `page_submitted_at`, `scrape_complete_at`, `rip_complete_at`. Report percentiles (p50, p95).
**Why it matters:** Slow tools get abandoned. Fast turnaround keeps users engaged and iterating.

### SM-05: Project Retention Rate
**Metric:** Percentage of users who return within 7 days and add more than 5 ads to at least one project.
**Target:** > 60% retention week-over-week for active users.
**Measurement:** Track `user_id`, `project_created_at`, `ads_added` in the database. Weekly cohort analysis.
**Why it matters:** Spy tools are only useful if users build a habit of competitive intelligence. Retention measures whether ADSRECON becomes part of the daily workflow.

---

## 5. MVP DEFINITION (v1.0)

The MVP delivers a working, end-to-end flow: enter a competitor page URL, see all their ads, click to uncloak and rip the real landing page, classify by vertical. Everything below must work.

### Core Flow (Must Work End-to-End)
1. **Input:** User enters a Facebook Page URL in the search bar.
2. **Scrape:** System fetches all ads from Meta Ads Library for that page (no auth required). Displays results: ad preview, text, status, variation count.
3. **Expand Variations:** User clicks an ad to see all registered creative variations.
4. **Rip Lander:** User clicks "Rip" on a variation. System uses the ad's fbclid-bearing URL, launches Playwright, navigates to the real (cloaked) destination, waits for render, captures desktop screenshot + HTML + text content.
5. **Classify:** System auto-classifies the ad into one of 12 nutra verticals based on ad text and lander content. Displays confidence level.
6. **Store:** All data (ad metadata, screenshots, HTML, text) is stored in the local SQLite database.
7. **Search & Filter:** User can filter results by vertical and geo. Keyword search across Meta.

### MVP Scope (What Ships)
- **Web UI:** Single-page application with search bar, results table, ad detail panel, lander viewer (screenshot + text).
- **Meta Scraper:** No-auth fetcher for Meta Ads Library. Supports page URL lookup and keyword search. Handles 9 countries.
- **Variation Extractor:** Fetches all creative variations per ad from Meta.
- **fbclid Ripper:** Constructs click URL, navigates via Playwright, captures screenshot + HTML + text.
- **Nutra Classifier:** 12-category keyword-based classifier with confidence scoring.
- **SQLite Storage:** All data persisted locally.
- **Basic Export:** JSON export of single ad data.

### MVP Scope (What Does NOT Ship)
- Project management (v1.x)
- CSV export (v1.x)
- Proxy integration (v1.x, fbclid primary flow is sufficient)
- Video extraction (v1.x)
- Alert system (v2.0)
- Desktop vs Mobile differentiation (v1.x)
- Trend tracking dashboard (v1.x)
- Landing page comparison (v2.0)

### MVP Success Criteria
- A user can enter any public nutra advertiser's Facebook page and see their ads within 60 seconds.
- A user can rip a landing page and see the real (cloaked) content within 3 minutes.
- The nutra vertical classifier correctly categorizes > 80% of ads without user correction.
- The system handles at least 5 concurrent scraping tasks without crashing.
- All data survives a server restart (SQLite persistence).

---

## 6. OPEN QUESTIONS

### Technical

**Q1: Does Meta's Ads Library expose all ad variations through their public API, or is HTML scraping required?**
Meta has a public Graph API (`graph.facebook.com/v18.0/ads_archive`) that accepts `access_token` -- but without an auth token it returns nothing useful. However, the Meta Ads Library website (https://www.facebook.com/ads/library/) has a public-facing UI that loads data via internal AJAX calls. We need to determine if those calls can be replicated without auth, or if we need to reverse-engineer the library's internal token exchange. This is the primary technical risk. Resolution path: inspect network traffic on the Ads Library page, extract AJAX endpoints, test without auth, fall back to HTML parsing of the rendered page if AJAX requires auth.
**Owner:** Architect Agent

**Q2: How stable is the cloaking bypass using fbclid alone?**
The core assumption is that cloaking services check for the presence of `fbclid` and treat the request as a legitimate Facebook visitor. This works for most but not all cloaking setups. Some services may check additional signals: IP geolocation matching the claimed country, IP reputation (residential vs datacenter), device fingerprinting, or cookie/session state. We need to empirically test this across 20-50 real nutra ads before declaring the approach production-ready. Resolution path: build a test harness, run against known cloaked ads, measure success rate, document failure modes.
**Owner:** Coder Agent / QA Agent

**Q3: How does Meta handle rate limiting for the Ads Library?**
When scraping at scale (multiple pages, multiple countries), Meta may throttle or temporarily block requests from the same IP. We need to know the exact limits: requests per minute, requests per hour, whether cookies/sessions affect the limit, and whether DataImpulse proxies are sufficient for bypassing rate limits. Resolution path: load test with increasing concurrency, measure rate limit responses, document thresholds.
**Owner:** Coder Agent

**Q4: What is the expected storage footprint per ripped landing page?**
A desktop screenshot at 1920x1080 PNG is ~500KB-2MB depending on complexity. HTML source is typically 50KB-500KB. Text extraction is negligible. If a user rips 1,000 landing pages, storage could be 1-2.5 GB. We need to define a retention policy: auto-delete screenshots older than X days, compress older screenshots, allow user-defined limits. Resolution path: profile storage per lander for 50 sample pages, define compression strategy, implement cleanup job.
**Owner:** Architect Agent

**Q5: Can Playwright run headless on the VPS without a display server?**
The target deployment is a self-hosted VPS (likely Ubuntu or Debian). Playwright's headless Chromium works in headless Linux environments, but GPU acceleration may be needed for pages that require WebGL. We need to confirm the VPS specs can handle headless browser workloads, or whether we need to use a service like Browserless.io as an alternative. Resolution path: set up test VPS, install Playwright headless, benchmark page load times, measure memory/CPU usage.
**Owner:** Coder Agent / DevOps Agent

### Business / Product

**Q6: What is the target pricing model?**
Self-hosted VPS accessible as a personal SaaS. Is this a one-time purchase (buy the script + setup guide), a subscription (monthly fee for updates + proxy credits), or a freemium model (core free, premium features paid)? The pricing model affects feature prioritization and the MVP scope significantly. Owner: User

**Q7: Who is the primary persona -- solo affiliate or agency/team?**
Solo affiliates care about speed and simplicity. Agencies care about multi-user access, team sharing, white-label reports, and user management. These drive different UI and backend requirements (auth, multi-tenancy, roles). If both, we need to design for multi-user from the start. Owner: User

**Q8: What is the target scale for v1.0?**
Is ADSRECON designed for one person spying on 10 competitors (small scale), or for an agency tracking 500+ competitors across all geos (large scale)? Scale affects the database design (SQLite vs PostgreSQL), the scraping concurrency model, and the UI's ability to handle large result sets. Owner: User

**Q9: Should ADSRECON support non-nutra verticals (sweepstakes, lead gen, e-commerce)?**
The MVP classifier is nutra-specific. But the scraper and ripper are vertical-agnostic. If we expect users to want to spy on non-nutra advertisers (sweepstakes, crypto, SaaS, dropshipping), the classifier and UI need to be extensible. This affects the data model and the classifier architecture (add vertical as a tag/label rather than an enum). Owner: User

**Q10: What is the competitor landscape -- are there existing tools ADSRECON must differentiate from?**
Known competitors: AdSpy, Social Ad Scout, Power Ad Spy, AdEspresso, SpyFu. Most require subscriptions and some use browser extensions. ADSRECON's differentiator is the fbclid cloaking bypass (others use proxies), the nutra-specific classification, and the self-hosted model. We need to validate these differentiators with real users before over-investing. Owner: Research Agent / User

---

## 7. TECHNICAL CONSTRAINTS

### TC-01: No Facebook Authentication
ADSRECON must operate using only the public Meta Ads Library. No Facebook login, no user access token, no OAuth flow. This constraint drives the entire scraping approach -- we are limited to what Meta exposes to unauthenticated visitors. If Meta's public API requires auth (which the Graph API does), we must fall back to HTML scraping or AJAX endpoint reverse-engineering. The scraper must gracefully degrade if public endpoints become unavailable.

### TC-02: fbclid Primary, Proxies Secondary
The core innovation is using Meta's own `fbclid` parameter to bypass cloaking without expensive residential proxies. Proxies (DataImpulse integration) are a fallback mechanism, not the primary path. This keeps costs low (~$30/month for DataImpulse vs. $300+/month for residential proxies) and simplifies deployment. The architecture must implement the fbclid flow as the happy path and only invoke proxy rotation on explicit failure.

### TC-03: Storage Management for Screenshots
Ripped landing pages generate screenshots that consume disk space rapidly. The system must implement:
- **Compression:** Convert screenshots to WebP format (50-70% smaller than PNG) after initial capture.
- **Retention policy:** Auto-delete screenshots older than 90 days (configurable), or delete screenshots for ads marked "inactive" after 30 days.
- **Storage tiering:** Keep full-resolution PNG for 7 days, then compress to WebP for long-term storage.
- **Quota system:** Warn at 80% disk usage, block new captures at 95%.
- **Storage location:** All media stored in `C:/AI_STACK/ADSRECON/storage/` with subdirectories: `screenshots/`, `html/`, `videos/`, `images/`.

### TC-04: Meta HTML Parser Fragility
Meta's Ads Library UI changes frequently (CSS class names, DOM structure, AJAX endpoints). A hardcoded HTML parser will break regularly. The scraper must use a resilient approach:
- **Primary:** Target stable data attributes (e.g., `data-testid`, `data-ad-id`) over CSS classes.
- **Fallback:** Use keyword-based text extraction when DOM paths fail.
- **Alerting:** If scraper fails for > 20% of requests in a batch, trigger an alert and pause scraping.
- **Version tracking:** Store the parser version with each scraped record. When parser changes, trigger a re-scrape of recent ads.
- **Update mechanism:** Parser configuration (CSS selectors, XPath expressions) stored in a config file, not hardcoded. Coder can update selectors without deploying new code.

### TC-05: VPS Deployment as SaaS
ADSRECON is deployed on a self-hosted VPS (Ubuntu 22.04 LTS recommended) and accessed via browser from any location. This creates these constraints:
- **Web server:** FastAPI (Python) serving the React/Vue SPA frontend and API backend on the same VPS.
- **Process management:** Systemd service for the FastAPI app. Auto-restart on crash.
- **Health monitoring:** Simple health endpoint (`/health`) that checks DB connectivity, Playwright availability, and disk space.
- **Reverse proxy:** Nginx as reverse proxy for HTTPS termination and static file serving.
- **Database:** SQLite for v1.0 (supports up to ~100,000 records comfortably). Must be backup-able via `sqlite3 .backup`.
- **No external cloud dependencies:** All processing happens on the VPS. No S3, no external databases, no third-party APIs (except DataImpulse proxy API for fallback).

### TC-07: Playwright Resource Constraints
The headless browser is the most resource-intensive component. Constraints:
- **Memory:** Each Playwright instance uses ~200-500MB RAM. Limit concurrent instances to 2-3 on a VPS with 8GB RAM.
- **Timeout:** Landing page load timeout: 30 seconds. If page does not load in 30s, mark as failed and log the URL.
- **Stealth:** Use Playwright-stealth or similar to minimize detection by anti-bot systems (hide webdriver property, fake navigator properties).
- **PDF export (optional):** Generate a PDF version of the lander as an alternative to screenshot for text-heavy pages.

### TC-08: Self-Healing Architecture
The system must not lose jobs or data on crash:
- **Job queue persistence:** Scraping and ripping tasks are stored in the SQLite queue with status (pending, running, complete, failed).
- **Retry logic:** Failed tasks retry up to 3 times with exponential backoff (30s, 60s, 120s).
- **Dead letter queue:** Tasks that fail 3 times are moved to a dead letter table with the error message, for manual review.
- **Crash recovery:** On startup, scan the queue for "running" tasks and reset them to "pending" (they were interrupted by the crash).
- **Checkpointing:** For longrips (pages with multiple steps), save state after each step so interrupted rips can resume.

---

## APPENDIX: Data MODEL (High-Level)

```
ads
  - ad_id (TEXT, PK)
  - page_id (TEXT)
  - page_name (TEXT)
  - ad_text (TEXT)
  - primary_text (TEXT)
  - headline (TEXT)
  - creative_type (TEXT: image, video, carousel, collection)
  - status (TEXT: active, inactive)
  - start_date (DATETIME)
  - end_date (DATETIME)
  - impressions (TEXT, Meta's string format)
  - geo (TEXT)
  - vertical (TEXT)
  - vertical_confidence (REAL)
  - has_cloaking (BOOLEAN)
  - cloaking_service (TEXT)
  - scraped_at (DATETIME)
  - project_id (TEXT, FK)

ad_variations
  - variation_id (TEXT, PK)
  - ad_id (TEXT, FK)
  - variation_index (INTEGER)
  - preview_url (TEXT)
  - destination_url (TEXT)
  - is_decoy (BOOLEAN)
  - is_real (BOOLEAN)

landing_pages
  - lander_id (TEXT, PK)
  - ad_id (TEXT, FK)
  - variation_id (TEXT, FK)
  - screenshot_desktop_path (TEXT)
  - screenshot_mobile_path (TEXT)
  - html_path (TEXT)
  - text_content (TEXT)
  - cms_detected (TEXT)
  - trackers_detected (TEXT)
  - ripped_at (DATETIME)
  - rip_status (TEXT: pending, running, complete, failed)
  - rip_error (TEXT)

projects
  - project_id (TEXT, PK)
  - name (TEXT)
  - description (TEXT)
  - created_at (DATETIME)
  - updated_at (DATETIME)

scrape_queue
  - task_id (TEXT, PK)
  - task_type (TEXT: page_scrape, keyword_scrape, lander_rip)
  - target (TEXT: URL or keyword)
  - geo (TEXT)
  - status (TEXT: pending, running, complete, failed)
  - priority (INTEGER)
  - attempts (INTEGER)
  - error_message (TEXT)
  - created_at (DATETIME)
  - started_at (DATETIME)
  - completed_at (DATETIME)
```

---

## APPENDIX: API ENDPOINTS (MVP)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check: DB, Playwright, disk space |
| GET | `/api/ads` | List ads with filters (vertical, geo, status, page) |
| GET | `/api/ads/:ad_id` | Get single ad detail |
| POST | `/api/scrape/page` | Start scrape by page URL |
| POST | `/api/scrape/keyword` | Start scrape by keyword |
| GET | `/api/scrape/status/:task_id` | Get scrape task status |
| POST | `/api/rip` | Start lander rip for an ad variation |
| GET | `/api/rip/status/:task_id` | Get rip task status |
| GET | `/api/rip/:rip_id/screenshot` | Serve screenshot file |
| GET | `/api/rip/:rip_id/html` | Serve HTML file |
| POST | `/api/classify/:ad_id` | Trigger re-classification |
| PUT | `/api/ads/:ad_id/vertical` | Update vertical classification |
| GET | `/api/projects` | List projects |
| POST | `/api/projects` | Create project |
| GET | `/api/projects/:id/ads` | Get ads in project |
| POST | `/api/projects/:id/ads` | Add ads to project |
| GET | `/api/export/:ad_id` | Export single ad as JSON |

---

*PRD ends. Architect Agent: proceed to system design. Coder Agent: proceed to implementation from MVP scope.*
