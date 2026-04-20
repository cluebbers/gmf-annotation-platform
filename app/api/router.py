from fastapi import APIRouter

from app.api.routes.chat import router as chat_router
from app.api.routes.compare import router as compare_router
from app.api.routes.incidents import router as incidents_router
from app.api.routes.prediction import router as prediction_router

api_router = APIRouter()
api_router.include_router(incidents_router)
api_router.include_router(prediction_router)
api_router.include_router(chat_router)
api_router.include_router(compare_router)
