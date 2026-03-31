"""Playwright Browser Pool — manages headless browser instances for lander ripping.

Manages a pool of headless Chromium browser instances, each with its own isolated
context (cookies, fingerprint). Used for rendering JavaScript-heavy landing pages
that httpx cannot handle.

Lifecycle:
    initialize()  → launch pool → acquire() → use → release() → close_all()

Example:
    pool = BrowserPool(pool_size=3)
    await pool.initialize()
    inst = await pool.acquire()
    page = await inst.context.new_page()
    # ... use page ...
    await page.close()
    await pool.release(inst)
    await pool.close_all()
"""
import asyncio
import logging
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# Windows requires the ProactorEventLoop for asyncio subprocess support (Playwright)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from playwright.async_api import async_playwright, Browser, BrowserContext

logger = logging.getLogger("adsrecon.browser_pool")


@dataclass
class BrowserInstance:
    """A single browser + isolated context pair in the pool."""

    browser: Browser
    context: BrowserContext
    instance_id: str
    in_use: bool = False
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class BrowserPool:
    """Manages a pool of headless Chromium browser instances.

    Each instance has its own isolated BrowserContext so cookies, localStorage,
    and other state are fully isolated between concurrent requests.

    Args:
        pool_size: Number of browser instances to keep alive. Default 3.
    """

    # Chromium launch arguments chosen for stability in container / CI environments
    LAUNCH_ARGS = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",                     # required in headless VMs without GPU
        "--disable-web-security",            # relaxed CORS for scraping
        "--disable-features=IsolateOrigins,site-per-process",
        "--window-size=1920,1080",
    ]

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    def __init__(self, pool_size: int = 3):
        self.pool_size = pool_size
        self.playwright: Optional[object] = None
        self.instances: list[BrowserInstance] = []
        self._lock = asyncio.Lock()
        self._initialized = False

    # ------------------------------------------------------------------ lifecycle

    async def initialize(self) -> None:
        """Launch all browser instances in the pool.

        Idempotent — safe to call multiple times; only initialises once.
        Falls back to graceful degraded mode if Playwright fails on this platform.
        """
        if self._initialized:
            logger.warning("Browser pool already initialised, skipping.")
            return

        logger.info(f"Initialising browser pool with {self.pool_size} instances...")

        try:
            self.playwright = await async_playwright().start()
        except NotImplementedError as exc:
            logger.error(
                f"Playwright subprocess exec not supported on this platform ({exc}). "
                f"Browser pool unavailable. Cloaking bypass will use HTTP-only mode."
            )
            self._initialized = True
            return
        except Exception as exc:
            logger.error(f"Playwright failed to start: {exc}. Browser pool unavailable.")
            self._initialized = True
            return

        launch_errors = []
        for i in range(self.pool_size):
            instance = await self._launch_browser(i)
            if instance is not None:
                self.instances.append(instance)
                logger.info(f"  Browser {i + 1}/{self.pool_size} ready ({instance.instance_id})")
            else:
                launch_errors.append(i)

        self._initialized = True
        logger.info(
            f"Browser pool ready: {len(self.instances)}/{self.pool_size} instances "
            f"({'failed indices: ' + str(launch_errors) if launch_errors else 'no errors'})"
        )

    # ------------------------------------------------------------------ internal

    async def _launch_browser(self, index: int) -> Optional[BrowserInstance]:
        """Launch a single Chromium instance with an isolated context."""
        try:
            browser = await self.playwright.chromium.launch(
                headless=True,
                args=self.LAUNCH_ARGS,
            )

            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=self.USER_AGENT,
                locale="en-US",
                timezone_id="America/New_York",
                permissions=["geolocation"],
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": (
                        "text/html,application/xhtml+xml,application/xml;q=0.9,"
                        "image/avif,image/webp,*/*;q=0.8"
                    ),
                },
            )

            instance = BrowserInstance(
                browser=browser,
                context=context,
                instance_id=f"browser-{index}-{uuid.uuid4().hex[:8]}",
            )

            logger.debug(f"Launched {instance.instance_id}")
            return instance

        except Exception as e:
            logger.error(f"Failed to launch browser {index}: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------------ public API

    async def acquire(self) -> Optional[BrowserInstance]:
        """Return an available BrowserInstance from the pool.

        Marks the instance as in-use so concurrent callers get different instances.
        Returns None if no instances are available (pool exhausted).

        The caller is responsible for:
            1. Creating a page via `instance.context.new_page()`
            2. Using the page
            3. Closing the page when done
            4. Calling `pool.release(instance)` to return it to the pool
        """
        async with self._lock:
            for instance in self.instances:
                if not instance.in_use:
                    instance.in_use = True
                    logger.debug(f"Acquired {instance.instance_id} ({self._in_use_count}/{len(self.instances)} in use)")
                    return instance

            logger.warning("Browser pool exhausted — no free instances available")
            return None

    async def release(self, instance: BrowserInstance) -> None:
        """Return a BrowserInstance back to the pool.

        Also closes any dangling pages left open on that context to prevent
        resource leaks.

        Safe to call even if pages are already closed.
        """
        async with self._lock:
            instance.in_use = False
            try:
                pages = instance.context.pages
                if pages:
                    for page in pages:
                        try:
                            await page.close()
                        except Exception as page_close_err:
                            logger.warning(
                                f"Error closing residual page on {instance.instance_id}: "
                                f"{page_close_err}"
                            )
            except Exception as context_err:
                logger.warning(
                    f"Could not enumerate pages for {instance.instance_id}: {context_err}"
                )
            logger.debug(f"Released {instance.instance_id}")

    async def close_all(self) -> None:
        """Gracefully shut down all browser instances and the Playwright runtime."""
        logger.info("Shutting down browser pool...")
        for instance in self.instances:
            try:
                await instance.browser.close()
                logger.debug(f"Closed {instance.instance_id}")
            except Exception as e:
                logger.error(f"Error closing {instance.instance_id}: {e}", exc_info=True)

        self.instances.clear()

        if self.playwright:
            try:
                await self.playwright.stop()
                logger.debug("Playwright runtime stopped")
            except Exception as e:
                logger.error(f"Error stopping Playwright runtime: {e}", exc_info=True)

        self._initialized = False
        logger.info("Browser pool shut down complete")

    # ------------------------------------------------------------------ utilities

    def get_stats(self) -> dict:
        """Return lightweight pool statistics for health monitoring."""
        total = len(self.instances)
        in_use = self._in_use_count
        return {
            "total": total,
            "in_use": in_use,
            "available": total - in_use,
            "initialized": self._initialized,
        }

    @property
    def _in_use_count(self) -> int:
        return sum(1 for i in self.instances if i.in_use)
