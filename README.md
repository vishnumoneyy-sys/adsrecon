# ADSRECON

**Ad Structure Reconnaissance** — Automated Facebook ad creative analysis and landing page extraction tool.

ADSRECON scrapes Facebook ads via their public ad library, extracts landing page HTML/screenshots, and stores structured data for competitive analysis, creative inspiration, and market research.

---

## What It Does

- Searches the **Facebook Ad Library** by keyword, country, and advertiser
- Extracts **landing page HTML** (full DOM via Playwright) with ad creative metadata
- Captures **full-page screenshots** of landing pages
- Stores everything in a **local SQLite database** with FastAPI CRUD endpoints
- Bypasses **anti-bot cloaking** using fbclid injection (free) and DataImpulse proxy fallback

---

## Key Features

- **Browser Automation** — Playwright-based headless Chromium with persistent browser context, user-agent spoofing, and retry logic
- **Meta Scraping** — Pulls ad creative details (headlines, body text, images, CTA buttons, spend estimates) from the Facebook Ad Library API
- **Landing Page Extraction** — Fetches and stores full HTML + screenshots of ad destination pages, even behind JavaScript walls
- **Cloaking Bypass** — fbclid auto-injection strategy (free) with DataImpulse proxy fallback for aggressive IP-based blocking
- **REST API** — Full CRUD on campaigns, ads, and landing pages via FastAPI with Swagger docs

---

## Architecture

```
Browser (Playwright) → Facebook Ad Library / Landing Pages
                              ↓
                  FastAPI Backend (Python 3.11)
                              ↓
                  SQLite Database (async via SQLAlchemy)
                              ↓
                  Frontend (Static HTML/JS on port 3000)
```

---

## Quick Start

```bash
pip install -r requirements.txt && python install.py && python run.py
```

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | Tested on 3.11 |
| Playwright | 1.41+ | Run `playwright install chromium --with-deps` |
| OS | Windows 10/11, Linux | Uses subprocess + pathlib |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///C:/AI_STACK/ADSRECON/adsrecon.db` | Database connection string |
| `HOST` | `0.0.0.0` | Backend bind host |
| `PORT` | `8000` | Backend port |
| `DEBUG` | `true` | Enable debug mode |
| `DATAIMPULSE_API_KEY` | _(none)_ | DataImpulse proxy API key |
| `BROWSER_POOL_SIZE` | `3` | Number of concurrent browser contexts |
| `PLAYWRIGHT_BROWSERS_PATH` | `C:/AI_STACK/ADSRECON/.playwright` | Playwright browser cache path |
| `SCREENSHOTS_DIR` | `C:/AI_STACK/ADSRECON/screenshots` | Screenshot output directory |
| `HTML_DUMPS_DIR` | `C:/AI_STACK/ADSRECON/html_dumps` | HTML dump output directory |
| `META_REQUEST_DELAY_MS` | `2000` | Delay between Facebook API requests (ms) |
| `META_USER_AGENT` | Chrome 122 | Browser user-agent string |
| `META_MAX_RETRIES` | `3` | Max retries per request |
| `CLOAKING_STRATEGY` | `fbclid_first` | Cloaking bypass strategy |
| `FORCE_PROXY` | `false` | Force proxy usage for all requests |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         ADSRECON                                 │
│                                                                  │
│  ┌──────────────────┐          ┌──────────────────────────────┐ │
│  │   Frontend       │          │      FastAPI Backend         │ │
│  │   (Static JS)    │◄────────►│                              │ │
│  │   Port 3000      │  REST    │  /api/campaigns              │ │
│  └──────────────────┘          │  /api/ads                    │ │
│          │                     │  /api/landing-pages          │ │
│          │                     │  /api/search                  │ │
│          ▼                     └──────────────┬───────────────┘ │
│  ┌──────────────────┐                          │                 │
│  │  Browser Pool    │                          │                 │
│  │  (Playwright)    │◄──────────────────────────┘                 │
│  └───────┬──────────┘                                           │
│          │                                                       │
│          ▼                                                       │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Data Sources                                    │ │
│  │  ┌──────────────────┐  ┌──────────────────────────────────┐  │ │
│  │  │ Facebook         │  │ Landing Pages                    │  │ │
│  │  │ Ad Library API   │  │ (HTML + Screenshots)             │  │ │
│  │  │ (meta.scraper)   │  │ (clicks.auto_scraper)            │  │ │
│  │  └──────────────────┘  └──────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Storage                                          │ │
│  │  SQLite DB (adsrecon.db)  │  Screenshots  │  HTML Dumps     │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/campaigns` | List all campaigns |
| `POST` | `/api/campaigns` | Create a new campaign |
| `GET` | `/api/campaigns/{id}` | Get campaign details |
| `DELETE` | `/api/campaigns/{id}` | Delete a campaign |
| `GET` | `/api/ads` | List ads (filter by campaign_id) |
| `POST` | `/api/ads/search` | Search Facebook Ad Library |
| `GET` | `/api/ads/{id}` | Get ad details |
| `GET` | `/api/ads/{id}/landing-page` | Get landing page data |
| `POST` | `/api/ads/{id}/scrape-landing` | Trigger landing page scrape |
| `GET` | `/api/landing-pages` | List all landing pages |
| `GET` | `/api/landing-pages/{id}` | Get landing page details |
| `GET` | `/api/landing-pages/{id}/screenshot` | Get screenshot file |
| `GET` | `/api/landing-pages/{id}/html` | Get HTML dump file |
| `GET` | `/health` | Health check |

---

## License

MIT
