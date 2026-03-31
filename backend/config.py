"""ADSRECON Configuration — loads from .env"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # Database
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR}/adsrecon.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # DataImpulse Proxies
    dataimpulse_api_key: str = ""
    proxy_pool_size: int = 5

    # Browser Pool
    browser_pool_size: int = 3
    playwright_browsers_path: str = str(BASE_DIR / ".playwright")

    # Storage
    screenshots_dir: str = str(BASE_DIR / "screenshots")
    html_dumps_dir: str = str(BASE_DIR / "html_dumps")

    # Meta Scraping
    meta_request_delay_ms: int = 2000
    meta_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
    meta_max_retries: int = 3

    # Cloaking Bypass
    cloaking_strategy: str = "fbclid_first"  # fbclid_first | proxy_first
    force_proxy: bool = False

    class Config:
        env_file = BASE_DIR / ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
