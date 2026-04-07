import logging
from contextlib import asynccontextmanager

from app.api.router import api_router
from app.db import init_db
from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        init_db()
    except SQLAlchemyError:
        logger.warning("Database initialization skipped because PostgreSQL is unavailable.")

    yield


app = FastAPI(
    title="GMF Annotation Platform API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_router)
