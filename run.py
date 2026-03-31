#!/usr/bin/env python3
"""Start both ADSRECON backend and frontend"""
import subprocess
import sys
import time
import os
import webbrowser
from pathlib import Path

BASE = Path(__file__).parent


def main():
    print("=" * 50)
    print("ADSRECON LAUNCHER")
    print("=" * 50)

    # Start backend
    print("\nStarting FastAPI backend on port 8000...")
    backend = subprocess.Popen(
        [sys.executable, str(BASE / "run_backend.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(3)

    # Start frontend
    print("Starting frontend on port 3000...")
    frontend = subprocess.Popen(
        [sys.executable, str(BASE / "run_frontend.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    print("\nADSRECON running!")
    print("   Frontend: http://localhost:3000")
    print("   Backend:  http://localhost:8000")
    print("   API docs: http://localhost:8000/docs")
    webbrowser.open("http://localhost:3000")

    try:
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        backend.terminate()
        frontend.terminate()


if __name__ == "__main__":
    main()
