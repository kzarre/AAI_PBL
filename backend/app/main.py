from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import dashboard, health, messages, users
from app.config import settings
from app.database import create_db_and_tables

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    create_db_and_tables()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

for module in (health, messages, users):
    app.include_router(module.router, prefix=API_PREFIX)
app.include_router(dashboard.router)
