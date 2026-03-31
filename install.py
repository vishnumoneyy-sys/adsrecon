#!/usr/bin/env python3
"""ADSRECON Installation Script"""
import os
import subprocess
import sys
import shutil
from pathlib import Path

BASE = Path(__file__).parent


def run(cmd, check=True):
    print(f"[INSTALL] {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0 and check:
        print(f"FAILED: {result.stderr[:200]}")
    return result


def main():
    print("=" * 50)
    print("ADSRECON INSTALLER")
    print("=" * 50)

    # Create directories
    dirs = [
        BASE / "screenshots",
        BASE / "html_dumps",
        BASE / "browser_data",
        BASE / ".playwright",
        BASE / "backend" / "models",
        BASE / "backend" / "routers",
        BASE / "backend" / "services",
        BASE / "backend" / "browser",
        BASE / "backend" / "utils",
        BASE / "frontend" / "components",
        BASE / "frontend" / "assets",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"[OK] Created: {d.relative_to(BASE)}")

    # Create __init__.py files
    for d in [
        BASE / "backend",
        BASE / "backend" / "models",
        BASE / "backend" / "routers",
        BASE / "backend" / "services",
        BASE / "backend" / "browser",
        BASE / "backend" / "utils",
    ]:
        init = d / "__init__.py"
        if not init.exists():
            init.write_text("")
            print(f"[OK] Created: {init.relative_to(BASE)}")

    # Install Python dependencies
    print("\n[STEP 1] Installing Python packages...")
    run(f'pip install -r "{BASE}/requirements.txt"', check=False)

    # Install Playwright browsers
    print("\n[STEP 2] Installing Playwright Chromium...")
    run("playwright install chromium --with-deps", check=False)

    # Create .env from .env.example
    env_file = BASE / ".env"
    env_example = BASE / ".env.example"
    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        print(f"\n[OK] Created .env from .env.example")
        print("    ⚠️  Edit C:/AI_STACK/ADSRECON/.env and add your DataImpulse API key")

    print("\n" + "=" * 50)
    print("ADSRECON INSTALLED!")
    print("=" * 50)
    print("\nTo start:")
    print("  python run_backend.py   # Start FastAPI backend")
    print("  python run_frontend.py  # Start frontend server")
    print("  python run.py           # Start both together")
    print("\nThen open: http://localhost:3000")


if __name__ == "__main__":
    main()
