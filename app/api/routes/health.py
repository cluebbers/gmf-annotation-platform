from fastapi import APIRouter, Response, status

from app.db import database_is_available

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(response: Response) -> dict[str, str]:
    if database_is_available():
        return {"status": "ok", "database": "ok"}

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "error", "database": "unavailable"}
