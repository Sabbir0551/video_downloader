from fastapi import APIRouter

from app.api.v1.endpoints.downloads import router as downloads_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.info import router as info_router
from app.api.v1.endpoints.takedown import router as takedown_router

api_v1_router = APIRouter()

api_v1_router.include_router(health_router, tags=["System"])
api_v1_router.include_router(info_router, tags=["Extraction"])
api_v1_router.include_router(downloads_router, tags=["Downloads"])
api_v1_router.include_router(takedown_router, tags=["Legal & Compliance"])
