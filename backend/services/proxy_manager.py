"""Proxy Manager — re-export from utils for service layer consistency.

The actual implementation lives in utils/proxy_manager.py.
This module re-exports it for service-layer imports.
"""
from utils.proxy_manager import ProxyManager, Proxy

__all__ = ["ProxyManager", "Proxy"]
