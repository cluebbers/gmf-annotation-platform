from fastapi import APIRouter

from app.api.routes.gold_annotations import router as gold_annotations_router
from app.api.routes.health import router as health_router
from app.api.routes.incidents import router as incidents_router
from app.api.routes.snippets import router as snippets_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(incidents_router)
api_router.include_router(gold_annotations_router)
api_router.include_router(snippets_router)
