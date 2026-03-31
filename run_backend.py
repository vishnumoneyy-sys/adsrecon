#!/usr/bin/env python3
"""Start ADSRECON FastAPI backend"""
import os
import sys
import uvicorn
from pathlib import Path

BASE = Path(__file__).parent
# Add project root to Python path so 'backend.config' resolves as 'backend/config.py'
# and bare imports like 'from config import' resolve within the backend package
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "backend"))
os.environ.setdefault("BASE_DIR", str(BASE))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=bool(os.environ.get("ADSRECON_ENV", "dev") == "dev"),
    )
