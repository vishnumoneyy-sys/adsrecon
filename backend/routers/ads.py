"""ADSRECON Ads Router — scraping, listing, and managing ads"""
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Optional
import logging
import asyncio

from services.meta_scraper import MetaScraper, MetaAd
from services.meta_browser_scraper import MetaBrowserScraper
from services.meta_graph_api_scraper import MetaGraphApiScraper, GraphApiAd
from services.nutra_classifier import NutraClassifier
from services.token_store import save_fb_token, load_fb_token, clear_fb_token
from models.ad import Ad
from database import async_session_maker
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("adsrecon.ads")
router = APIRouter()

# Singleton classifier
nutra_classifier = NutraClassifier()


# ─── Keyword mappings per nutra category ───────────────────────────────────────
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "weight_loss": ["weight loss supplement", "lose weight", "burn fat"],
    "blood_sugar": ["blood sugar support", "diabetes supplement", "lower blood sugar"],
    "prostate": ["prostate health", "prostate support", "enlarged prostate"],
    "skin_beauty": ["skin cream", "anti aging skin", "collagen supplement"],
    "joint_pain": ["joint pain relief", "arthritis supplement", "joint health"],
    "energy_stamina": ["energy supplement", "boost energy", "stamina supplement"],
    "gut_digestion": ["gut health", "digestion supplement", "probiotic"],
    "male_enhancement": ["male enhancement", "male performance", "sexual health supplement"],
    "female_health": ["women health supplement", "menopause relief", "female libido"],
    "anti_aging": ["anti aging", "youthful skin", "age reversal supplement"],
    "eyes_vision": ["eye health", "vision support", "improve eyesight"],
    "heart_blood": ["heart health supplement", "lower cholesterol", "blood pressure supplement"],
}

# Supported countries for multi-country scraping
SUPPORTED_COUNTRIES = ["US", "GB", "CA", "AU", "DE", "FR", "BR", "MX", "IN", "JP"]


# Request/Response models
class ScrapeRequest(BaseModel):
    page_url: str
    country: str = "US"
    category: str = ""


class SearchRequest(BaseModel):
    keyword: str
    country: str = "US"
    media_type: str = "all"
    category: str = ""


class ScrapeMultiRequest(BaseModel):
    countries: list[str]
    categories: list[str]
    max_per_country: int = 5


class AdResponse(BaseModel):
    id: int
    library_id: str
    page_name: str
    ad_text: str
    landing_url_clean: str
    landing_url_actual: Optional[str]
    platforms: list
    status: str
    days_running: int
    category: Optional[str]
    is_real_nutra: bool
    nutra_score: int
    cloak_status: str
    saved: bool
    created_at: str


# ─── Helpers ───────────────────────────────────────────────────────────────────
def _graph_ad_to_meta_ad(graph_ad: GraphApiAd) -> MetaAd:
    """Convert a GraphApiAd to MetaAd for uniform DB storage."""
    return MetaAd(
        library_id=graph_ad.library_id,
        page_id=graph_ad.page_id,
        page_name=graph_ad.page_name,
        ad_text=graph_ad.ad_text,
        primary_image_url="",
        video_url="",
        landing_url=graph_ad.landing_url,
        fbclid=graph_ad.fbclid,
        platforms=graph_ad.platforms,
        days_running=0,
        impressions=graph_ad.impressions,
        is_active=graph_ad.is_active,
    )


async def _classify_and_store_graph_ads(
    graph_ads: list[GraphApiAd], db: AsyncSession, override_category: str = ""
) -> list[dict]:
    """Store GraphApiAd objects in DB and return summaries."""
    stored = []
    for graph_ad in graph_ads:
        meta_ad = _graph_ad_to_meta_ad(graph_ad)
        existing = await db.execute(
            select(Ad).where(Ad.library_id == meta_ad.library_id)
        )
        db_ad = existing.scalar_one_or_none()

        if not db_ad:
            classification = nutra_classifier.classify(meta_ad.ad_text or "")
            top_category = override_category if override_category else classification.top_category

            db_ad = Ad(
                library_id=meta_ad.library_id,
                page_id=meta_ad.page_id,
                page_name=meta_ad.page_name,
                ad_text=meta_ad.ad_text,
                primary_image_url=meta_ad.primary_image_url,
                video_urls=[],
                landing_url_clean=meta_ad.landing_url,
                fbclid=meta_ad.fbclid,
                platforms=meta_ad.platforms,
                days_running=0,
                impressions_estimate=meta_ad.impressions,
                spend_estimate=meta_ad.spend,
                countries=graph_ad.countries,
                status="active" if meta_ad.is_active else "inactive",
                category=top_category,
                is_real_nutra=classification.is_nutra,
                nutra_score=classification.aggression_score,
                cloak_status="pending",
                saved=False
            )
            db.add(db_ad)
            await db.commit()
            await db.refresh(db_ad)

        stored.append({
            "id": db_ad.id,
            "library_id": db_ad.library_id,
            "page_name": db_ad.page_name,
            "ad_text": (db_ad.ad_text[:100] + "...") if db_ad.ad_text and len(db_ad.ad_text) > 100 else db_ad.ad_text,
            "landing_url": db_ad.landing_url_clean,
            "category": db_ad.category,
            "is_nutra": db_ad.is_real_nutra,
            "impressions": graph_ad.impressions if graph_ad.impressions else "",
            "spend": graph_ad.spend if graph_ad.spend else "",
            "countries": graph_ad.countries,
        })
    return stored


async def _classify_and_store_ads(meta_ads: list[MetaAd], db: AsyncSession, override_category: str = "") -> list[dict]:
    """
    Classify each MetaAd with the nutra classifier and store in the DB.
    Returns a list of stored ad summaries.
    """
    stored_ads = []
    for meta_ad in meta_ads:
        existing = await db.execute(
            select(Ad).where(Ad.library_id == meta_ad.library_id)
        )
        db_ad = existing.scalar_one_or_none()

        if not db_ad:
            # Use nutra classifier to auto-classify
            classification = nutra_classifier.classify(meta_ad.ad_text or "")

            # Override with provided category if set
            top_category = override_category if override_category else classification.top_category

            db_ad = Ad(
                library_id=meta_ad.library_id,
                page_id=meta_ad.page_id,
                page_name=meta_ad.page_name,
                ad_text=meta_ad.ad_text,
                primary_image_url=meta_ad.primary_image_url,
                video_urls=meta_ad.video_url.split(",") if meta_ad.video_url else [],
                landing_url_clean=meta_ad.landing_url,
                fbclid=meta_ad.fbclid,
                platforms=meta_ad.platforms,
                days_running=meta_ad.days_running,
                impressions_estimate=meta_ad.impressions,
                status="active" if meta_ad.is_active else "inactive",
                category=top_category,
                is_real_nutra=classification.is_nutra,
                nutra_score=classification.aggression_score,
                cloak_status="pending",
                saved=False
            )
            db.add(db_ad)
            await db.commit()
            await db.refresh(db_ad)

        stored_ads.append({
            "id": db_ad.id,
            "library_id": db_ad.library_id,
            "page_name": db_ad.page_name,
            "ad_text": (db_ad.ad_text[:100] + "...") if db_ad.ad_text and len(db_ad.ad_text) > 100 else db_ad.ad_text,
            "landing_url": db_ad.landing_url_clean,
            "category": db_ad.category,
            "is_nutra": db_ad.is_real_nutra
        })

    return stored_ads


# GET /api/ads — List ads with filters
@router.get("")
async def list_ads(
    request: Request,
    category: Optional[str] = None,
    status: Optional[str] = None,
    page_id: Optional[str] = None,
    saved_only: bool = False,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0)
):
    """List ads from the database with optional filters"""
    async with async_session_maker() as db:
        query = select(Ad)

        if category:
            query = query.where(Ad.category == category)
        if status:
            query = query.where(Ad.status == status)
        if page_id:
            query = query.where(Ad.page_id == page_id)
        if saved_only:
            query = query.where(Ad.saved == True)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.order_by(Ad.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        db_ads = result.scalars().all()

        ads_response = []
        for ad in db_ads:
            ads_response.append(AdResponse(
                id=ad.id,
                library_id=ad.library_id or "",
                page_name=ad.page_name or "",
                ad_text=ad.ad_text or "",
                landing_url_clean=ad.landing_url_clean or "",
                landing_url_actual=ad.landing_url_actual,
                platforms=ad.platforms or [],
                status=ad.status or "active",
                days_running=ad.days_running or 0,
                category=ad.category,
                is_real_nutra=ad.is_real_nutra or False,
                nutra_score=ad.nutra_score or 0,
                cloak_status=ad.cloak_status or "pending",
                saved=ad.saved or False,
                created_at=ad.created_at.isoformat() if ad.created_at else ""
            ))

        return {"ads": ads_response, "total": total, "limit": limit, "offset": offset, "source": "list"}


# POST /api/ads/scrape — Scrape ads from a Facebook page
@router.post("/scrape")
async def scrape_ads(request: Request, body: ScrapeRequest):
    """
    Scrape all ads from a Facebook Ads Library transparency page.
    Uses Playwright browser (primary) with httpx fallback.
    Auto-classifies each ad using the nutra classifier.
    """
    logger.info(f"Scraping page: {body.page_url[:100]}  country={body.country}  category={body.category}")

    meta_ads = []
    method_used = "none"
    browser_pool = request.app.state.browser_pool

    # Try browser-based scraping first
    if browser_pool and browser_pool.instances:
        try:
            async with MetaBrowserScraper(browser_pool) as browser_scraper:
                meta_ads = await browser_scraper.scrape_page(body.page_url)
                method_used = "browser"
        except Exception as browser_err:
            logger.warning(f"Browser scrape failed for {body.page_url[:60]}: {browser_err}")

    # Fall back to httpx if browser returned nothing
    if not meta_ads:
        try:
            async with MetaScraper() as scraper:
                meta_ads = await scraper.scrape_page(body.page_url)
                method_used = "http"
        except Exception as e:
            logger.error(f"Scraping failed (both methods): {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Meta blocked or unavailable: {str(e)}"
            )

    if not meta_ads:
        return {
            "ads": [],
            "total": 0,
            "message": f"No ads found (method={method_used}). Meta may be blocking requests.",
            "source": "scrape"
        }

    # Store in database with auto-classification
    async with async_session_maker() as db:
        stored_ads = await _classify_and_store_ads(meta_ads, db, override_category=body.category)

    logger.info(f"Scraped {len(stored_ads)} ads (method={method_used})")
    return {
        "ads": stored_ads,
        "total": len(stored_ads),
        "message": f"Scraped {len(stored_ads)} ads (method={method_used})",
        "source": "scrape"
    }


# GET /api/ads/search — Search ads by keyword
@router.get("/search")
async def search_ads(
    request: Request,
    q: str = Query(..., min_length=2),
    country: str = Query(default="US"),
    media_type: str = Query(default="all"),
    category: str = Query(default="")
):
    """
    Search Meta Ads Library by keyword.
    Priority: Graph API (free, fast, no proxies) → Browser → httpx fallback.
    """
    logger.info(f"Searching keyword: {q}  country={country}  media_type={media_type}  category={category}")

    # ── 1. Try Graph API (FREE — no proxies, no browser needed) ─────────────────
    graph_ads: list[dict] = []
    fbclid_saved = False

    token = load_fb_token()
    if token:
        try:
            scraper = MetaGraphApiScraper(access_token=token)
            raw_ads, err = await scraper.search_ads(query=q, country=country, limit=100)
            await scraper.close()

            if raw_ads and not err:
                async with async_session_maker() as db:
                    stored = await _classify_and_store_graph_ads(raw_ads, db)
                    for ad in stored:
                        ad["country"] = country
                        graph_ads.append(ad)
                fbclid_saved = True
                logger.info(f"Graph API: found {len(graph_ads)} ads for '{q}' in {country}")
        except Exception as graph_err:
            logger.warning(f"Graph API failed for '{q}': {graph_err}")

    # ── 2. Browser fallback (if Graph API returned nothing) ─────────────────────
    meta_ads = []
    method_used = "none"

    if not graph_ads:
        browser_pool = request.app.state.browser_pool

        if browser_pool and browser_pool.instances:
            try:
                async with MetaBrowserScraper(browser_pool) as browser_scraper:
                    meta_ads = await browser_scraper.search_keyword(q, country)
                    method_used = "browser"
            except Exception as browser_err:
                logger.warning(f"Browser search failed for '{q}' in {country}: {browser_err}")

        # httpx fallback
        if not meta_ads:
            try:
                async with MetaScraper() as scraper:
                    meta_ads = await scraper.search_keyword(q, country)
                    method_used = "http"
            except Exception as e:
                logger.error(f"Search failed (both methods): {e}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Meta blocked the search: {str(e)}. Try the Auto Scrape feature."
                )

        if not meta_ads:
            return {
                "ads": [],
                "total": 0,
                "keyword": q,
                "country": country,
                "message": f"No ads found (method={method_used}). Meta may be blocking this search.",
                "source": "search"
            }

        # Store browser/httpx results
        async with async_session_maker() as db:
            stored = await _classify_and_store_ads(meta_ads, db)
            for ad in stored:
                ad["country"] = country
            graph_ads = stored
            method_used = method_used

    return {
        "ads": graph_ads,
        "total": len(graph_ads),
        "keyword": q,
        "country": country,
        "method": "graph_api" if fbclid_saved else method_used,
        "message": f"Found {len(graph_ads)} ads (method={method_used if not fbclid_saved else 'graph_api'})",
        "source": "search",
        "fb_token_configured": bool(token)
    }


# GET /api/ads/countries — Return ad counts per country
@router.get("/countries")
async def get_countries(request: Request):
    """
    Return the list of supported countries with ad counts.
    Counts ads in the DB grouped by the 'country' field (stored in page_id or as metadata).
    """
    # The Ad model does not have a dedicated country field, so we derive it
    # from the page_id prefix or count all ads as "unknown" for now.
    # A full implementation would add a country column to the Ad model.
    async with async_session_maker() as db:
        total_result = await db.execute(select(func.count()).select_from(Ad))
        total = total_result.scalar() or 0

        # Count by category as a proxy for country-level distribution
        cat_result = await db.execute(
            select(Ad.category, func.count(Ad.id))
            .group_by(Ad.category)
            .order_by(func.count(Ad.id).desc())
        )
        cat_rows = cat_result.all()

        # Return supported countries with counts (DB stores country in page metadata; default all to 0)
        country_counts = []
        for country in SUPPORTED_COUNTRIES:
            country_counts.append({
                "country": country,
                "count": 0,  # Would require a country column in Ad model to populate accurately
                "supported": True
            })

        return {
            "countries": country_counts,
            "total_ads": total,
            "by_category": [{"category": r[0] or "unknown", "count": r[1]} for r in cat_rows],
            "source": "search"
        }


# POST /api/ads/scrape-multi — Scrape ads for multiple countries and categories
@router.post("/scrape-multi")
async def scrape_multi(request: Request, body: ScrapeMultiRequest):
    """
    Scrape ads across multiple countries and nutra categories.
    For each country+category combo, searches with the category's keyword terms
    and stores all results with country and category fields set.
    """
    logger.info(f"Multi-country scrape: countries={body.countries}  categories={body.categories}  max={body.max_per_country}")

    # Validate countries
    invalid_countries = [c for c in body.countries if c not in SUPPORTED_COUNTRIES]
    if invalid_countries:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported countries: {invalid_countries}. Supported: {SUPPORTED_COUNTRIES}"
        )

    # Validate categories
    valid_cats = list(CATEGORY_KEYWORDS.keys())
    invalid_cats = [c for c in body.categories if c not in valid_cats]
    if invalid_cats:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown categories: {invalid_cats}. Valid: {valid_cats}"
        )

    all_ads = []
    total_scrape_errors = 0
    progress = []
    browser_pool = request.app.state.browser_pool

    async with async_session_maker() as db:
        for country in body.countries:
            country_progress = {"country": country, "categories": []}

            for cat in body.categories:
                keywords = CATEGORY_KEYWORDS.get(cat, [])
                cat_progress = {"category": cat, "keywords_searched": 0, "ads_found": 0, "errors": 0}

                for keyword in keywords:
                    meta_ads = []
                    try:
                        # Try browser-based first
                        if browser_pool and browser_pool.instances:
                            async with MetaBrowserScraper(browser_pool) as browser_scraper:
                                meta_ads = await browser_scraper.search_keyword(keyword, country)
                        # Fall back to httpx
                        if not meta_ads:
                            async with MetaScraper() as scraper:
                                meta_ads = await scraper.search_keyword(keyword, country)
                    except Exception as e:
                        logger.warning(f"Multi-country keyword search failed: keyword={keyword} country={country}: {e}")
                        cat_progress["errors"] += 1
                        cat_progress["keywords_searched"] += 1
                        total_scrape_errors += 1
                        await asyncio.sleep(0.5)
                        continue

                    cat_progress["keywords_searched"] += 1
                    cat_progress["ads_found"] += len(meta_ads)

                    if meta_ads:
                        stored = await _classify_and_store_ads(meta_ads, db, override_category=cat)
                        for ad in stored:
                            ad["country"] = country
                            ad["category"] = cat
                            all_ads.append(ad)

                    # Respectful throttle between keyword searches
                    await asyncio.sleep(1.0)

                country_progress["categories"].append(cat_progress)

                # Respectful throttle between category switches
                await asyncio.sleep(1.5)

            progress.append(country_progress)

    return {
        "ads": all_ads[: body.max_per_country * len(body.countries) * len(body.categories)],
        "total_ads_found": len(all_ads),
        "scrape_errors": total_scrape_errors,
        "progress": progress,
        "countries": body.countries,
        "categories": body.categories,
        "message": f"Multi-country scrape complete: {len(all_ads)} ads found",
        "source": "multi_country"
    }


# POST /api/ads/scrape-countries — Scrape all 10 supported countries with rate limiting
@router.post("/scrape-countries")
async def scrape_countries(request: Request, keyword: str = Query(default="nutra supplement")):
    """
    Scrape Meta Ads Library across all 10 supported countries using a single keyword.
    Uses Playwright browser-based scraping (primary) with httpx fallback.
    Adds 2-second rate limiting between country requests.
    Returns aggregated results with country-level summaries.
    """
    logger.info(f"Scraping all countries with keyword: {keyword}")

    all_ads = []
    country_results = {}
    total_errors = 0
    browser_pool = request.app.state.browser_pool

    async with async_session_maker() as db:
        for country in SUPPORTED_COUNTRIES:
            meta_ads = []
            used_browser = False

            # Try browser-based scraping first (more reliable, bypasses bot detection)
            if browser_pool and browser_pool.instances:
                try:
                    async with MetaBrowserScraper(browser_pool) as browser_scraper:
                        meta_ads = await browser_scraper.search_keyword(keyword, country)
                        used_browser = True
                except Exception as browser_err:
                    logger.warning(f"Browser scrape failed for {country}: {browser_err}")

            # Fall back to httpx-based scraper if browser returned nothing
            if not meta_ads:
                try:
                    async with MetaScraper() as scraper:
                        meta_ads = await scraper.search_keyword(keyword, country)
                except Exception as e:
                    logger.warning(f"Country scrape blocked: country={country}: {e}")
                    country_results[country] = {
                        "ads": [],
                        "count": 0,
                        "error": str(e),
                        "blocked": True
                    }
                    total_errors += 1
                    await asyncio.sleep(2.0)
                    continue

            stored = await _classify_and_store_ads(meta_ads, db)
            for ad in stored:
                ad["country"] = country
            all_ads.extend(stored)
            country_results[country] = {
                "ads": stored,
                "count": len(stored),
                "blocked": False,
                "method": "browser" if used_browser else "http"
            }
            logger.info(f"Country {country}: {len(stored)} ads stored (method={country_results[country]['method']})")

            # 2-second rate limit between country requests
            await asyncio.sleep(2.0)

    total_stored = sum(r["count"] for r in country_results.values())
    blocked_countries = [c for c, r in country_results.items() if r.get("blocked")]

    return {
        "ads": all_ads,
        "total_ads": len(all_ads),
        "total_stored": total_stored,
        "scrape_errors": total_errors,
        "countries": country_results,
        "blocked_countries": blocked_countries,
        "keyword": keyword,
        "message": f"Scraped {len(all_ads)} ads across {len(SUPPORTED_COUNTRIES)} countries",
        "source": "multi_country"
    }


# GET /api/ads/settings — Check token status
@router.get("/settings")
async def get_settings():
    """Returns the current Facebook API token status (masked)."""
    token = load_fb_token()
    return {
        "fb_token_configured": bool(token),
        "fb_token_masked": ("*" * 20 + token[-6:]) if token else "",
        "scraping_methods": ["graph_api", "browser", "http"],
        "primary_method": "graph_api" if token else "browser",
        "token_help_url": "https://developers.facebook.com/tools/explorer/",
    }


# POST /api/ads/settings — Save Facebook access token
@router.post("/settings")
async def save_settings(token: str = Query(...)):
    """Save a Facebook Graph API access token (stored in .fb_token)."""
    if len(token) < 20:
        raise HTTPException(status_code=400, detail="Invalid token — too short")
    try:
        scraper = MetaGraphApiScraper(access_token=token)
        valid, msg = await scraper.test_connection()
        await scraper.close()
        if not valid:
            raise HTTPException(
                status_code=400,
                detail=f"Token invalid: {msg}. Get a new one at https://developers.facebook.com/tools/explorer/"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token validation failed: {str(e)}")
    save_fb_token(token)
    logger.info("Facebook access token saved successfully")
    return {
        "success": True,
        "message": "Token saved. Graph API scraping is now active (free, no proxies needed).",
        "token_masked": ("*" * 20 + token[-6:]),
    }


# DELETE /api/ads/settings — Clear the stored token
@router.delete("/settings")
async def clear_settings():
    """Remove the stored Facebook access token."""
    clear_fb_token()
    return {"success": True, "message": "Token cleared."}


# GET /api/ads/test-graph-api — Test the Graph API with current token
@router.get("/test-graph-api")
async def test_graph_api():
    """Test if the stored Graph API token works. Returns sample ads."""
    token = load_fb_token()
    if not token:
        raise HTTPException(
            status_code=400,
            detail="No token configured. Set it via POST /api/ads/settings?token=YOUR_TOKEN"
        )
    scraper = MetaGraphApiScraper(access_token=token, request_delay=0.5)
    valid, msg = await scraper.test_connection()
    await scraper.close()
    if not valid:
        raise HTTPException(status_code=400, detail=f"Token invalid: {msg}")
    try:
        raw_ads, err = await scraper.search_ads(query="supplement", country="US", limit=3)
        await scraper.close()
    except Exception as test_err:
        return {
            "token_valid": True,
            "test_search": "failed",
            "error": str(test_err),
            "message": "Token valid but test search failed."
        }
    if err:
        raise HTTPException(status_code=400, detail=f"Test search failed: {err}")
    return {
        "token_valid": True,
        "test_search": "success",
        "ads_found": len(raw_ads),
        "sample": [{"id": a.library_id, "page": a.page_name, "text": a.ad_text[:60]} for a in raw_ads[:2]],
        "message": f"Graph API is working! Found {len(raw_ads)} test ads."
    }


# GET /api/ads/{id} — Get single ad with variations
@router.get("/{ad_id}")
async def get_ad(ad_id: int, request: Request):
    """Get a single ad by ID with all its variations"""
    async with async_session_maker() as db:
        result = await db.execute(select(Ad).where(Ad.id == ad_id))
        ad = result.scalar_one_or_none()

        if not ad:
            raise HTTPException(status_code=404, detail="Ad not found")

        # Get variations
        from models.variation import Variation
        vars_result = await db.execute(
            select(Variation).where(Variation.ad_id == ad_id)
        )
        variations = vars_result.scalars().all()

        return {
            "ad": {
                "id": ad.id,
                "library_id": ad.library_id,
                "page_name": ad.page_name,
                "page_id": ad.page_id,
                "ad_text": ad.ad_text,
                "primary_image_url": ad.primary_image_url,
                "video_urls": ad.video_urls or [],
                "landing_url_clean": ad.landing_url_clean,
                "landing_url_actual": ad.landing_url_actual,
                "fbclid": ad.fbclid,
                "platforms": ad.platforms or [],
                "days_running": ad.days_running,
                "impressions": ad.impressions_estimate,
                "status": ad.status,
                "category": ad.category,
                "is_real_nutra": ad.is_real_nutra,
                "nutra_score": ad.nutra_score,
                "cloak_status": ad.cloak_status,
                "cloak_service_guess": ad.cloak_service_guess,
                "saved": ad.saved,
                "created_at": ad.created_at.isoformat() if ad.created_at else ""
            },
            "variations": [
                {
                    "id": v.id,
                    "creative_text": v.creative_text,
                    "landing_url": v.landing_url,
                    "platform_target": v.platform_target,
                    "device_target": v.device_target,
                    "is_decoy": v.is_decoy,
                    "is_real": v.is_real
                }
                for v in variations
            ],
            "source": "list"
        }


# POST /api/ads/{id}/save — Toggle saved status
@router.post("/{ad_id}/save")
async def toggle_save(ad_id: int, request: Request):
    """Toggle the saved status of an ad"""
    async with async_session_maker() as db:
        result = await db.execute(select(Ad).where(Ad.id == ad_id))
        ad = result.scalar_one_or_none()

        if not ad:
            raise HTTPException(status_code=404, detail="Ad not found")

        ad.saved = not ad.saved
        await db.commit()

        return {"id": ad.id, "saved": ad.saved, "source": "list"}


# --------------------------------------------------------------------------- demo data

DEMO_ADS = [
    {
        "library_id": "demo_001",
        "page_name": "Pure Health Labs",
        "ad_text": "LOSE 30 POUNDS IN 30 DAYS — All Natural Formula! Doctor approved blood sugar support. No diet, no exercise. 87% saw results in week 2. Order now, limited supply!",
        "landing_url": "https://purehealth-labs.com/weight-loss formula/?fbclid=demo001",
        "primary_image_url": "https://picsum.photos/seed/nutra1/600/400",
        "platforms": ["facebook", "instagram"],
        "days_running": 14,
        "status": "active",
        "country": "US",
    },
    {
        "library_id": "demo_002",
        "page_name": "VitaBoost Supplements",
        "ad_text": "OZEMPIC ALTERNATIVE THAT ACTUALLY WORKS! Boost your energy & metabolism. Real customers, real results. Click to see before/after photos. 60-day money-back guarantee!",
        "landing_url": "https://vitaboost-shop.com/metabolism-boost/?utm_source=facebook",
        "primary_image_url": "https://picsum.photos/seed/nutra2/600/400",
        "platforms": ["facebook", "instagram", "messenger"],
        "days_running": 7,
        "status": "active",
        "country": "US",
    },
    {
        "library_id": "demo_003",
        "page_name": "Prostate Relief Co",
        "ad_text": "Doctor Recommended Prostate Support Formula — 9 in 10 men saw improvement in just 4 weeks! Reduce nighttime bathroom trips. All-natural ingredients. Ships worldwide.",
        "landing_url": "https://prostate-relief.com/buy-now?camp=fb_ads",
        "primary_image_url": "https://picsum.photos/seed/nutra3/600/400",
        "platforms": ["facebook"],
        "days_running": 21,
        "status": "active",
        "country": "GB",
    },
    {
        "library_id": "demo_004",
        "page_name": "GlowSkin Beauty",
        "ad_text": "REVERSE YOUR AGE IN 30 DAYS — dermatologist tested & approved. Reduce wrinkles, dark spots & fine lines with this breakthrough collagen formula. 500K+ happy customers worldwide.",
        "landing_url": "https://glowskin-pro.com/anti-aging-cream/?fbclid=demo004",
        "primary_image_url": "https://picsum.photos/seed/nutra4/600/400",
        "platforms": ["facebook", "instagram"],
        "days_running": 30,
        "status": "active",
        "country": "AU",
    },
    {
        "library_id": "demo_005",
        "page_name": "JointFlex Pro",
        "ad_text": "WALK WITHOUT PAIN IN 7 DAYS — clinically proven joint support supplement. Reduce stiffness, inflammation & joint pain. Made in USA. 90-day satisfaction guarantee. Order now!",
        "landing_url": "https://jointflexpro.com/joint-relief/?utm_medium=social",
        "primary_image_url": "https://picsum.photos/seed/nutra5/600/400",
        "platforms": ["facebook", "audience_network"],
        "days_running": 18,
        "status": "active",
        "country": "CA",
    },
    {
        "library_id": "demo_006",
        "page_name": "GutWell Probiotics",
        "ad_text": "HEAL YOUR GUT IN 2 WEEKS — 50 billion CFU probiotic blend. Bloating, gas, constipation? All gone in days. 30-day money-back guarantee. Doctors recommend this!",
        "landing_url": "https://gutwellpro.com/digestive-health/?fbclid=demo006",
        "primary_image_url": "https://picsum.photos/seed/nutra6/600/400",
        "platforms": ["facebook", "instagram"],
        "days_running": 12,
        "status": "active",
        "country": "DE",
    },
    {
        "library_id": "demo_007",
        "page_name": "MaleEdge Performance",
        "ad_text": "RESTORE YOUR CONFIDENCE IN BED — male enhancement formula. Longer lasting, harder performance. All-natural ingredients. Discreet shipping. 73% saw results in 2 weeks!",
        "landing_url": "https://maleedge-plus.com/order-now?camp=fb",
        "primary_image_url": "https://picsum.photos/seed/nutra7/600/400",
        "platforms": ["facebook"],
        "days_running": 9,
        "status": "active",
        "country": "FR",
    },
    {
        "library_id": "demo_008",
        "page_name": "ClearView Eye Health",
        "ad_text": "IMPROVE YOUR VISION NATURALLY — protect your eyes from blue light & aging. Lutein & zeaxanthin formula. 20/20 vision support. Try risk-free today!",
        "landing_url": "https://clearview-eyes.com/vision-support/?fbclid=demo008",
        "primary_image_url": "https://picsum.photos/seed/nutra8/600/400",
        "platforms": ["facebook"],
        "days_running": 6,
        "status": "active",
        "country": "BR",
    },
    {
        "library_id": "demo_009",
        "page_name": "HeartGuard Plus",
        "ad_text": "LOWER YOUR BLOOD PRESSURE IN 30 DAYS — cardiologist recommended cardiovascular support. Natural ingredients, no side effects. Take control of your heart health NOW!",
        "landing_url": "https://heartguard-plus.com/cardio-health/?utm_source=meta",
        "primary_image_url": "https://picsum.photos/seed/nutra9/600/400",
        "platforms": ["facebook", "instagram"],
        "days_running": 15,
        "status": "active",
        "country": "MX",
    },
    {
        "library_id": "demo_010",
        "page_name": "Femina Wellness",
        "ad_text": "HOT FLASHES END TODAY — menopause relief that actually works! Reduce night sweats, mood swings & weight gain. 100% natural. Join 200K+ women feeling great again!",
        "landing_url": "https://femina-wellness.com/menopause-relief/?fbclid=demo010",
        "primary_image_url": "https://picsum.photos/seed/nutra10/600/400",
        "platforms": ["facebook", "instagram"],
        "days_running": 22,
        "status": "active",
        "country": "IN",
    },
    {
        "library_id": "demo_011",
        "page_name": "DecoyClean Brands",
        "ad_text": "Try our premium organic green tea — only $9.99! Fresh from Japan, rich in antioxidants. Limited time offer. Free shipping on first order.",
        "landing_url": "https://decoy-clean.com/green-tea",
        "primary_image_url": "https://picsum.photos/seed/decoy1/600/400",
        "platforms": ["facebook"],
        "days_running": 45,
        "status": "active",
        "country": "US",
        "is_decoy": True,
    },
    {
        "library_id": "demo_012",
        "page_name": "CleanLife Organics",
        "ad_text": "Organic multivitamins for the whole family. Made with farm-fresh ingredients. No artificial colors. Your path to better health starts here.",
        "landing_url": "https://cleanlife-organics.com/multivitamins",
        "primary_image_url": "https://picsum.photos/seed/decoy2/600/400",
        "platforms": ["facebook", "instagram"],
        "days_running": 60,
        "status": "active",
        "country": "US",
        "is_decoy": True,
    },
]


# POST /api/ads/demo — Seed database with demo ads
@router.post("/demo")
async def seed_demo_ads(request: Request, clear_first: bool = Query(default=True)):
    """
    Populate the database with realistic demo nutra ads so the full UI can be tested.
    Each ad is auto-classified with the nutra classifier.
    """
    logger.info(f"Seeding demo ads (clear_first={clear_first})")

    async with async_session_maker() as db:
        if clear_first:
            # Remove existing demo ads
            result = await db.execute(
                select(Ad).where(Ad.library_id.like("demo_%"))
            )
            existing = result.scalars().all()
            for ad in existing:
                await db.delete(ad)
            await db.commit()

        stored = []
        for demo in DEMO_ADS:
            # Classify the ad
            classification = nutra_classifier.classify(demo["ad_text"])

            ad = Ad(
                library_id=demo["library_id"],
                page_id=demo["library_id"],
                page_name=demo["page_name"],
                ad_text=demo["ad_text"],
                primary_image_url=demo.get("primary_image_url", ""),
                landing_url_clean=demo["landing_url"],
                fbclid=extract_fbclid_from_url(demo["landing_url"]),
                platforms=demo.get("platforms", []),
                days_running=demo.get("days_running", 0),
                status=demo.get("status", "active"),
                category=classification.top_category or "",
                is_real_nutra=not demo.get("is_decoy", False),
                nutra_score=classification.aggression_score,
                cloak_status="pending",
                saved=False,
            )
            db.add(ad)
            await db.commit()
            await db.refresh(ad)

            stored.append({
                "id": ad.id,
                "library_id": ad.library_id,
                "page_name": ad.page_name,
                "ad_text": ad.ad_text[:80] + "..." if ad.ad_text and len(ad.ad_text) > 80 else ad.ad_text,
                "landing_url": ad.landing_url_clean,
                "category": ad.category,
                "is_nutra": ad.is_real_nutra,
                "country": demo.get("country", "US"),
            })

        logger.info(f"Seeded {len(stored)} demo ads")

    return {
        "ads": stored,
        "total": len(stored),
        "message": f"Loaded {len(stored)} demo ads across {len(set(d['country'] for d in DEMO_ADS))} countries",
        "source": "demo"
    }


def extract_fbclid_from_url(url: str) -> str:
    """Extract fbclid from a URL for the demo."""
    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        fbclids = params.get("fbclid", [])
        return fbclids[0] if fbclids else ""
    except Exception:
        return ""


# DELETE /api/ads/{id} — Delete an ad
@router.delete("/{ad_id}")
async def delete_ad(ad_id: int, request: Request):
    """Delete an ad and all its variations"""
    async with async_session_maker() as db:
        result = await db.execute(select(Ad).where(Ad.id == ad_id))
        ad = result.scalar_one_or_none()

        if not ad:
            raise HTTPException(status_code=404, detail="Ad not found")

        await db.delete(ad)
        await db.commit()

        return {"deleted": True, "id": ad_id, "source": "list"}


# GET /api/ads/settings — Check current API token status
