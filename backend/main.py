"""FastAPI 앱 진입점 — 라우팅 + CORS. 계산은 analytics.py 에 위임."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import analytics
from data import DC_SPEC, FAB_STEPS, FEATURE_COLUMNS, TARGET_COLUMNS, load_dataframe
from schemas import (
    BinnedRequest,
    BinnedResponse,
    ColumnsResponse,
    TableRequest,
    TableResponse,
    TimeseriesRequest,
    TimeseriesResponse,
)

app = FastAPI(title="Process Window Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _check_columns(cols) -> None:
    valid = set(FEATURE_COLUMNS) | set(TARGET_COLUMNS)
    for c in cols:
        if c not in valid:
            raise HTTPException(status_code=400, detail=f"unknown column: {c}")


def _check_step(step: str) -> None:
    if step not in FAB_STEPS:
        raise HTTPException(status_code=400, detail=f"unknown fab_step: {step}")


@app.get("/api/columns", response_model=ColumnsResponse)
def get_columns():
    return {"features": FEATURE_COLUMNS, "targets": TARGET_COLUMNS,
            "fab_steps": FAB_STEPS, "dc_spec": DC_SPEC}


@app.post("/api/binned", response_model=BinnedResponse)
def post_binned(req: BinnedRequest):
    _check_step(req.fab_step)
    _check_columns(req.x_features + req.y_targets)
    df = load_dataframe()
    return analytics.compute_binned(df, req.fab_step, req.x_features, req.y_targets, req.bins)


@app.post("/api/timeseries", response_model=TimeseriesResponse)
def post_timeseries(req: TimeseriesRequest):
    _check_step(req.fab_step)
    _check_columns(req.x_features + req.y_targets)
    df = load_dataframe()
    return analytics.compute_timeseries(df, req.fab_step, req.x_features, req.y_targets)


@app.post("/api/table", response_model=TableResponse)
def post_table(req: TableRequest):
    _check_step(req.fab_step)
    _check_columns(req.x_features + req.y_targets)
    df = load_dataframe()
    return analytics.compute_table(df, req.fab_step, req.x_features, req.y_targets, DC_SPEC)
