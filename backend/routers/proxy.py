"""ADSRECON Proxy Router — proxy health and testing"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import logging

from services.proxy_manager import ProxyManager

logger = logging.getLogger("adsrecon.proxy")
router = APIRouter()


# GET /api/proxy/health — Check proxy pool health
@router.get("/health")
async def proxy_health(request: Request):
    """Get status of the proxy pool"""
    proxy_manager: ProxyManager = request.app.state.proxy_manager
    if not proxy_manager:
        return {"working": False, "message": "No proxy configured"}

    health = await proxy_manager.health_check_all()
    working_count = sum(1 for v in health.values() if v)

    return {
        "total": len(health),
        "working": working_count,
        "status": health
    }


# POST /api/proxy/test — Test a specific proxy URL
@router.post("/test")
async def test_proxy(request: Request, body: dict):
    """Test if a proxy URL is working"""
    proxy_manager: ProxyManager = request.app.state.proxy_manager
    proxy_url = body.get("proxy_url")

    if not proxy_url:
        raise HTTPException(status_code=400, detail="proxy_url required")

    working = await proxy_manager.check_proxy(proxy_url)

    return {
        "proxy_url": proxy_url,
        "working": working,
        "checked_at": "now"
    }


# GET /api/proxy/next — Get next proxy from pool
@router.get("/next")
async def get_next_proxy(request: Request, geo: str = "us"):
    """Get the next available proxy from the pool"""
    proxy_manager: ProxyManager = request.app.state.proxy_manager
    if not proxy_manager:
        return {"proxy_url": None, "message": "No proxy manager"}

    proxy_url = await proxy_manager.get_proxy(geo)

    return {
        "proxy_url": proxy_url,
        "geo": geo,
        "working": proxy_url is not None
    }
