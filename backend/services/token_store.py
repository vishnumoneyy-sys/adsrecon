"""Token store — persists Facebook access token to disk (gitignored)."""
import json
import logging
from pathlib import Path

logger = logging.getLogger("adsrecon.token_store")

TOKEN_FILE = Path(__file__).resolve().parent.parent / ".fb_token"


def save_fb_token(token: str) -> None:
    TOKEN_FILE.write_text(json.dumps({"token": token}), encoding="utf-8")
    logger.info("Facebook access token saved")


def load_fb_token() -> str:
    try:
        if TOKEN_FILE.exists():
            data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
            return data.get("token", "")
    except Exception as e:
        logger.warning(f"Failed to load fb token: {e}")
    return ""


def clear_fb_token() -> None:
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        logger.info("Facebook access token cleared")
