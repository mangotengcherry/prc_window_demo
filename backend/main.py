"""FastAPI 앱 진입점 (M0). 라우팅 + CORS. 계산은 analytics.py 에 위임."""
import io
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import analytics
import data as D
from schemas import (
    BinnedRequest, BinnedResponse,
    ColumnsResponse,
    DriversRequest, DriversResponse,
    InteractionRequest, InteractionResponse,
    TableRequest, TableResponse,
    TimeseriesRequest, TimeseriesResponse,
    XFeatureOptionsResponse,
)

app = FastAPI(title="Process Window Dashboard API (M0)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MIN_N = analytics.MIN_N
MAX_COMBOS = analytics.req_max_combos()


@app.get("/api/columns", response_model=ColumnsResponse)
def get_columns():
    prc = D.fab_metro_prc()
    units = {**D.feature_unit_map(), **D.TARGET_UNIT}
    df = D.load_dataframe()
    tmin = df["fab_track_out_time"].min().strftime("%Y-%m-%d")
    tmax = df["fab_track_out_time"].max().strftime("%Y-%m-%d")
    obs_eds = df.loc[df["observed"], "eds_tkout_time"]
    emin = obs_eds.min().strftime("%Y-%m-%d")
    emax = obs_eds.max().strftime("%Y-%m-%d")
    return {
        "line_ids": D.LINE_IDS,
        "products": D.PRODUCTS,
        "categories": D.CATEGORIES,
        "eds_steps": D.EDS_STEPS,
        "targets": D.ALL_TARGETS,
        "targets_by_category": D.TARGETS_BY_CATEGORY,
        "fab_steps": D.FAB_STEPS,
        "metro_grades": sorted(prc["metro_grade"].unique().tolist()),
        "metro_categories": sorted(prc["metro_category"].unique().tolist()),
        "category_features": list(D.CATEGORY_FEATURES.keys()),
        "category_feature_values": D.CATEGORY_FEATURES,
        "dc_spec": D.dc_spec(),
        "units": units,
        "min_n": MIN_N,
        "max_combos": MAX_COMBOS,
        "date_default": {"start_date": tmin, "end_date": tmax},
        "target_date_default": {"start_date": emin, "end_date": emax},
    }


@app.get("/api/x-feature-options", response_model=XFeatureOptionsResponse)
def get_x_feature_options(
    fab_step: Optional[str] = Query(None),
    matching: bool = Query(True),
    metro_grade: Optional[str] = Query(None),
    metro_category: Optional[str] = Query(None),
):
    features = analytics.list_x_features(fab_step, matching, metro_grade, metro_category)
    return {"matching": matching, "fab_step": fab_step, "features": features}


@app.post("/api/binned", response_model=BinnedResponse)
def post_binned(req: BinnedRequest):
    return analytics.compute_binned(req)


@app.post("/api/timeseries", response_model=TimeseriesResponse)
def post_timeseries(req: TimeseriesRequest):
    return analytics.compute_timeseries(req)


@app.post("/api/table", response_model=TableResponse)
def post_table(req: TableRequest):
    return analytics.compute_table(req)


@app.post("/api/interaction", response_model=InteractionResponse)
def post_interaction(req: InteractionRequest):
    return analytics.compute_interaction(req)


@app.post("/api/drivers", response_model=DriversResponse)
def post_drivers(req: DriversRequest):
    return analytics.compute_drivers(req)


@app.post("/api/raw")
def post_raw(req: TableRequest):
    """현재 분석 조건의 wafer 원시데이터 CSV (식별자 + 선택 feature/target)."""
    df = analytics.raw_frame(req)
    buf = io.StringIO()
    buf.write("﻿")  # Excel이 UTF-8(한글)로 인식하도록 BOM
    df.to_csv(buf, index=False)
    fname = f"raw_{req.fab_step}_{req.date_range.start_date}_{req.date_range.end_date}.csv"
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="{fname}"'})
