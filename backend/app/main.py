from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_analysis_sets,
    routes_bin_groups,
    routes_condition_rules,
    routes_exclusions,
    routes_expressions,
    routes_export,
    routes_metadata,
    routes_prediction,
    routes_window_review,
)
from app.core.config import settings
from app.services.mock_data_service import ensure_mock_data


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_mock_data()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    ensure_mock_data()
    return {"status": "ok", "app": settings.app_name}


app.include_router(routes_metadata.router)
app.include_router(routes_expressions.router)
app.include_router(routes_analysis_sets.router)
app.include_router(routes_bin_groups.router)
app.include_router(routes_condition_rules.router)
app.include_router(routes_window_review.router)
app.include_router(routes_exclusions.router)
app.include_router(routes_prediction.router)
app.include_router(routes_export.router)
