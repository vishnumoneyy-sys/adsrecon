"""ADSRECON Logging Setup"""
import logging
import sys
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent.parent.parent


def setup_logging(debug: bool = True) -> logging.Logger:
    """Configure logging with file and console handlers."""
    level = logging.DEBUG if debug else logging.INFO

    # File handler — daily rotation via filename stamp
    log_dir = BASE / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"adsrecon_{datetime.now().strftime('%Y%m%d')}.log"

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )

    # Console handler — use UTF-8 encoding on Windows to support emoji/log symbols
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    console.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    )
    logging.getLogger().addHandler(console)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("playwright").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return logging.getLogger("adsrecon")


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger for a module."""
    return logging.getLogger(f"adsrecon.{name}")
