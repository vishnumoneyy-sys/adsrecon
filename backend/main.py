"""ADSRECON FastAPI Backend — main application entry point"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from config import get_settings, BASE_DIR
from database import init_db
from browser.playwright_pool import BrowserPool
from services.cloaking_bypass import CloakingBypassService
from services.lander_ripper import LanderRipper
from services.proxy_manager import ProxyManager
from utils.logging import setup_logging
from routers import ads, rip, classify, proxy

settings = get_settings()
logger = setup_logging(settings.debug)

# Global services (initialized on startup)
browser_pool: BrowserPool | None = None
cloaking_service: CloakingBypassService | None = None
lander_ripper: LanderRipper | None = None
proxy_manager: ProxyManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle"""
    global browser_pool, cloaking_service, lander_ripper, proxy_manager

    logger.info("=" * 50)
    logger.info("ADSRECON STARTING UP")
    logger.info("=" * 50)

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Create storage directories
    Path(settings.screenshots_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.html_dumps_dir).mkdir(parents=True, exist_ok=True)

    # Initialize browser pool
    browser_pool = BrowserPool(pool_size=settings.browser_pool_size)
    await browser_pool.initialize()
    logger.info("Browser pool initialized")

    # Initialize services
    cloaking_service = CloakingBypassService()
    proxy_manager = ProxyManager(api_key=settings.dataimpulse_api_key)
    lander_ripper = LanderRipper(
        browser_pool=browser_pool,
        cloaking_service=cloaking_service,
        screenshots_dir=settings.screenshots_dir,
        html_dumps_dir=settings.html_dumps_dir
    )
    logger.info("Services initialized")

    # Inject services into app state
    app.state.browser_pool = browser_pool
    app.state.cloaking_service = cloaking_service
    app.state.lander_ripper = lander_ripper
    app.state.proxy_manager = proxy_manager

    # Inject browser_pool for MetaBrowserScraper
    app.state.meta_browser_scraper = None  # initialized lazily per-request

    logger.info("=" * 50)
    logger.info("ADSRECON READY")
    logger.info("=" * 50)

    yield  # App runs here

    # Shutdown
    logger.info("Shutting down ADSRECON...")
    if browser_pool:
        await browser_pool.close_all()
    logger.info("ADSRECON stopped")


# Create FastAPI app
app = FastAPI(
    title="ADSRECON API",
    description="Facebook Ads Library Spy Tool for Nutra Affiliate Marketers",
    version="1.0.0",
    lifespan=lifespan
)

# CORS — allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for screenshots
app.mount("/screenshots", StaticFiles(directory=settings.screenshots_dir), name="screenshots")

# Mount static files for HTML dumps (used by iframe preview)
app.mount("/html_dumps", StaticFiles(directory=settings.html_dumps_dir), name="html_dumps")

# Mount frontend as static SPA — only if it exists
_frontend_path = BASE_DIR.parent / "frontend"
if _frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_path), html=True), name="frontend")

# Include routers FIRST so /api/* routes are registered before static catch-all
app.include_router(ads.router, prefix="/api/ads", tags=["ads"])
app.include_router(rip.router, prefix="/api/rip", tags=["rip"])
app.include_router(classify.router, prefix="/api/classify", tags=["classify"])
app.include_router(proxy.router, prefix="/api/proxy", tags=["proxy"])


@app.get("/health")
async def health():
    """Health check endpoint"""
    stats = browser_pool.get_stats() if browser_pool else {}
    return {
        "status": "ok",
        "browser_pool": stats,
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
