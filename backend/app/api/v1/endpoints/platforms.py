from typing import Dict, List, Optional
from fastapi import APIRouter, Query, Response

from app.platforms.registry import PlatformMetadata, get_platform_registry

router = APIRouter(prefix="/platforms", tags=["Platforms"])


@router.get("", response_model=Dict[str, Any] if False else None)
async def list_platforms(
    response: Response,
    tier: Optional[str] = Query(None, description="Filter by tier: supported, best_effort, unsupported_no_video, login_or_paid, defunct"),
    category: Optional[str] = Query(None, description="Filter by category: social, video_audio, messaging, community_forum, photo_art, etc."),
):
    """
    Returns the comprehensive list of 100 platforms supported or classified by AnyStream.
    Public and cached with Cache-Control headers.
    """
    # Cache for 1 hour on clients and CDN
    response.headers["Cache-Control"] = "public, max-age=3600, s-maxage=86400"

    registry = get_platform_registry()
    platforms = registry.get_all(tier=tier)
    if category:
        platforms = [p for p in platforms if p.category == category]

    return {
        "version": registry.data.version,
        "last_verified": registry.data.last_verified,
        "ytdlp_version": registry.data.ytdlp_version,
        "total": len(platforms),
        "tiers_summary": registry.data.tiers_summary,
        "platforms": [p.model_dump() for p in platforms],
    }


@router.get("/detect")
async def detect_platform(url: str = Query(..., description="URL to detect platform for")):
    """
    Detects platform metadata, tier, and policy permissions for a given URL.
    Used by frontend for instantaneous client-side feedback before initiating extraction.
    """
    registry = get_platform_registry()
    platform = registry.find_by_url(url)
    if not platform:
        return {
            "detected": False,
            "platform": None,
            "tier": "unknown",
            "allowed": True,
            "message": "URL not matched to a recognized platform. Attempting generic extraction.",
        }

    is_allowed = platform.tier in ["supported", "best_effort"]
    return {
        "detected": True,
        "platform": platform.model_dump(),
        "tier": platform.tier,
        "allowed": is_allowed,
        "requires_login": platform.requires_login,
        "has_public_video": platform.has_public_video,
    }

