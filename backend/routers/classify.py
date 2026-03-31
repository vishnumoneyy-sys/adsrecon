"""ADSRECON Classify Router — decoy vs real ad classification"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func
import logging

from services.cloaking_bypass import CloakingBypassService
from services.nutra_classifier import NutraClassifier
from models.ad import Ad
from database import async_session_maker
from sqlalchemy import select

logger = logging.getLogger("adsrecon.classify")
router = APIRouter()

# Singleton classifier
nutra_classifier = NutraClassifier()


class TextClassifyRequest(BaseModel):
    text: str
    landing_url: str = ""


# POST /api/classify/text — Direct text classification (no ad_id needed)
@router.post("/text")
async def classify_text(body: TextClassifyRequest):
    """
    Classify ad text directly without needing an existing ad in the DB.
    Returns nutra categories, aggression score, decoy detection, and signals.
    """
    classification = nutra_classifier.classify(body.text)
    is_decoy = nutra_classifier.is_decoy(body.text, body.landing_url)

    return {
        "is_decoy": is_decoy,
        "is_nutra": classification.is_nutra,
        "nutra_categories": classification.categories,
        "top_category": classification.top_category,
        "aggression_score": classification.aggression_score,
        "hook_type": classification.hook_type,
        "matched_keywords": classification.matched_keywords,
        "is_ghs": classification.is_ghs,
        "is_prescription_claim": classification.is_prescription_claim,
        "cta_language": classification.cta_language,
        "target_demo": classification.target_demo,
        "red_flags": classification.red_flags,
    }


# POST /api/classify/{ad_id} — Classify an ad (decoy vs real)
@router.post("/{ad_id}")
async def classify_ad(ad_id: int, request: Request):
    """
    Classify an ad: Is it a decoy or a real cloaked nutra ad?

    Steps:
    1. Get the ad from DB
    2. Visit the landing URL with fbclid
    3. Compare clean URL vs actual URL
    4. Classify as decoy/real/nutra
    5. Update DB
    """
    cloaking_service: CloakingBypassService = request.app.state.cloaking_service
    if not cloaking_service:
        raise HTTPException(status_code=500, detail="Cloaking service not initialized")

    async with async_session_maker() as db:
        result = await db.execute(select(Ad).where(Ad.id == ad_id))
        ad = result.scalar_one_or_none()

        if not ad:
            raise HTTPException(status_code=404, detail="Ad not found")

        # Classify ad text with nutra classifier
        ad_text = ad.ad_text or ""
        landing_url = ad.landing_url_clean or ""
        classification = nutra_classifier.classify(ad_text)
        is_decoy = nutra_classifier.is_decoy(ad_text, landing_url)

        # Attempt cloaking bypass
        cloak_result = await cloaking_service.bypass(
            landing_url=landing_url,
            fbclid=ad.fbclid
        )

        # Update ad
        ad.landing_url_actual = cloak_result.actual_url
        ad.is_real_nutra = cloak_result.is_cloaked or classification.is_nutra
        ad.category = classification.top_category or ad.category
        ad.nutra_score = classification.aggression_score
        ad.cloak_status = "cloaked" if cloak_result.is_cloaked else ("passed" if cloak_result.success else "failed")
        ad.updated_at = func.now()

        await db.commit()

        return {
            "ad_id": ad_id,
            "is_decoy": is_decoy,
            "is_real_nutra": ad.is_real_nutra,
            "cloak_status": ad.cloak_status,
            "landing_url_clean": landing_url,
            "landing_url_actual": cloak_result.actual_url,
            "cloak_type": cloak_result.cloak_type,
            "domains_differ": cloak_result.is_cloaked,
            "expected_domain": cloak_result.expected_domain,
            "actual_domain": cloak_result.actual_domain,
            "nutra_categories": classification.categories,
            "top_category": classification.top_category,
            "aggression_score": classification.aggression_score,
            "hook_type": classification.hook_type,
            "matched_keywords": classification.matched_keywords,
            "fbclid_used": bool(cloak_result.fbclid_used),
            "proxy_used": bool(cloak_result.proxy_used)
        }
