"""ADSRECON Rip Router — landing page ripping endpoints"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import logging
import posixpath

from models.lander import Lander
from models.ad import Ad
from database import async_session_maker
from sqlalchemy import select

logger = logging.getLogger("adsrecon.rip")
router = APIRouter()


def _web_path(full_path: str, mount_point: str = "/screenshots") -> str:
    """
    Convert a full filesystem path to a web-accessible URL path.

    E.g. C:/AI_STACK/ADSRECON/screenshots/abc123.png → /screenshots/abc123.png
    Handles both forward slashes and Windows backslashes.
    """
    if not full_path:
        return ""
    # Replace Windows backslashes with forward slashes, then extract basename
    normalized = full_path.replace("\\", "/")
    filename = posixpath.basename(normalized)
    return f"{mount_point}/{filename}"


class RipRequest(BaseModel):
    ad_id: Optional[int] = None
    url: str
    fbclid: Optional[str] = None
    device: str = "desktop"  # desktop or mobile
    proxy: Optional[str] = None


# POST /api/rip — Rip a landing page
@router.post("")
async def rip_lander(request: Request, body: RipRequest):
    """
    Rip a landing page using Playwright.
    Returns screenshot path and extracted data.
    """
    ripper = request.app.state.lander_ripper
    if not ripper:
        raise HTTPException(status_code=500, detail="Ripper not initialized")

    logger.info(f"Ripping: {body.url[:60]} (device={body.device})")

    result = await ripper.rip(
        landing_url=body.url,
        fbclid=body.fbclid,
        device=body.device,
        proxy=body.proxy
    )

    # Store result in database
    lander_id = None
    # Web-accessible paths (for the API response)
    web_screenshot = _web_path(result.screenshot_path) if result.screenshot_path else ""
    web_html = _web_path(result.html_path, "/html_dumps") if result.html_path else ""

    async with async_session_maker() as db:
        lander = Lander(
            ad_id=body.ad_id,
            screenshot_path=result.screenshot_path,  # Store full path for DB
            html_dump_path=result.html_path,
            video_urls=result.video_urls,
            phone_numbers=result.phone_numbers,
            email_addresses=result.emails,
            cloak_detected=result.cloak_result.is_cloaked if result.cloak_result else False,
            cloak_service_guess=result.cloak_result.cloak_type if result.cloak_result else None,
            device_used=result.device_used,
            proxy_used=body.proxy,
            final_url=result.final_url,
            title=result.title,
        )
        db.add(lander)
        await db.commit()
        await db.refresh(lander)
        lander_id = lander.id

        # Update ad with actual URL and cloak status
        if body.ad_id:
            ad_result = await db.execute(select(Ad).where(Ad.id == body.ad_id))
            ad = ad_result.scalar_one_or_none()
            if ad:
                ad.landing_url_actual = result.final_url
                if result.cloak_result:
                    ad.cloak_status = "cloaked" if result.cloak_result.is_cloaked else "passed"
                await db.commit()

    return {
        "id": lander_id,
        "success": result.success,
        "screenshot_path": web_screenshot,
        "html_path": web_html,
        "title": result.title,
        "final_url": result.final_url,
        "video_urls": result.video_urls,
        "phone_numbers": result.phone_numbers,
        "emails": result.emails,
        "cloak_detected": result.cloak_result.is_cloaked if result.cloak_result else False,
        "cloak_type": result.cloak_result.cloak_type if result.cloak_result else None,
        "device_used": result.device_used,
        "error": result.error
    }


# GET /api/rip/{id}/screenshot — Serve screenshot image
@router.get("/{lander_id}/screenshot")
async def get_screenshot(lander_id: int, request: Request):
    """Serve the screenshot image for a lander rip"""
    from pathlib import Path
    from fastapi.responses import FileResponse

    async with async_session_maker() as db:
        result = await db.execute(select(Lander).where(Lander.id == lander_id))
        lander = result.scalar_one_or_none()

        if not lander or not lander.screenshot_path:
            raise HTTPException(status_code=404, detail="Screenshot not found")

        path = Path(lander.screenshot_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Screenshot file not found")

        return FileResponse(str(path), media_type="image/png")


# GET /api/rip/{ad_id} — Get rip for an ad
@router.get("/ad/{ad_id}")
async def get_rip_for_ad(ad_id: int, request: Request):
    """Get the latest rip for an ad"""
    async with async_session_maker() as db:
        result = await db.execute(
            select(Lander)
            .where(Lander.ad_id == ad_id)
            .order_by(Lander.accessed_at.desc())
            .limit(1)
        )
        lander = result.scalar_one_or_none()

        if not lander:
            return {"found": False, "message": "No rip found for this ad"}

        return {
            "found": True,
            "id": lander.id,
            "screenshot_path": _web_path(lander.screenshot_path),
            "html_path": _web_path(lander.html_dump_path, "/html_dumps"),
            "final_url": lander.final_url,
            "title": lander.title,
            "video_urls": lander.video_urls or [],
            "cloak_detected": lander.cloak_detected,
            "cloak_type": lander.cloak_service_guess,
            "device_used": lander.device_used,
            "accessed_at": lander.accessed_at.isoformat() if lander.accessed_at else None
        }
