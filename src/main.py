"""FastAPI application entry."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.health import router as health_router
from api.routes.jobs import router as jobs_router
from config import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _ = get_settings()
    yield


app = FastAPI(
    title="Kadmoo Video Service",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(jobs_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "kadmoo-video-service", "docs": "/docs"}
