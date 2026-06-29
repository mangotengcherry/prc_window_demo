from __future__ import annotations

from typing import Any

import pandas as pd

from app.data.mock_store import store
from app.models.schemas import AnalysisSetCreate, AnalysisSetFilters
from app.services.mock_data_service import ensure_mock_data


def _list_filter(df: pd.DataFrame, column: str, values: list[str]) -> pd.Series:
    return pd.Series(True, index=df.index) if not values else df[column].isin(values)


def apply_filters(filters: AnalysisSetFilters | dict[str, Any]) -> pd.DataFrame:
    ensure_mock_data()
    if isinstance(filters, dict):
        filters = AnalysisSetFilters(**filters)
    df = store.wafer_data
    mask = pd.Series(True, index=df.index)
    mask &= _list_filter(df, "product", filters.product)
    mask &= _list_filter(df, "layer", filters.layer)
    mask &= _list_filter(df, "step", filters.step)
    mask &= _list_filter(df, "tool_id", filters.tool)
    mask &= _list_filter(df, "chamber_id", filters.chamber)
    mask &= _list_filter(df, "ppid", filters.ppid)
    mask &= _list_filter(df, "eco_number", filters.eco)
    if filters.start_date:
        mask &= df["process_date"] >= pd.Timestamp(filters.start_date)
    if filters.end_date:
        mask &= df["process_date"] <= pd.Timestamp(filters.end_date)
    if filters.pm_age_min is not None:
        mask &= df["pm_age"] >= filters.pm_age_min
    if filters.pm_age_max is not None:
        mask &= df["pm_age"] <= filters.pm_age_max
    if filters.eds_status == "actual_only":
        mask &= df["eds_status"] == "actual"
    if filters.exclude_rework:
        mask &= ~df["is_rework"]
    if filters.exclude_engineering_lot:
        mask &= ~df["is_engineering_lot"]
    if filters.exclude_abnormal_route:
        mask &= ~df["is_abnormal_route"]
    return df.loc[mask].copy()


def summarize_filters(filters: AnalysisSetFilters | dict[str, Any], frame: pd.DataFrame) -> dict[str, Any]:
    if isinstance(filters, dict):
        filters = AnalysisSetFilters(**filters)
    parameter = filters.parameter[0] if filters.parameter else "metro_ch_hole_cd"
    excluded_reasons = {
        "rework": int(store.wafer_data["is_rework"].sum()) if filters.exclude_rework else 0,
        "engineering_lot": int(store.wafer_data["is_engineering_lot"].sum()) if filters.exclude_engineering_lot else 0,
        "abnormal_route": int(store.wafer_data["is_abnormal_route"].sum()) if filters.exclude_abnormal_route else 0,
    }
    wafer_count = int(len(frame))
    actual_count = int((frame["eds_status"] == "actual").sum()) if wafer_count else 0
    return {
        "lot_count": int(frame["lot_id"].nunique()) if wafer_count else 0,
        "wafer_count": wafer_count,
        "fab_coverage": round(float(frame[parameter].notna().mean()), 4) if wafer_count and parameter in frame else 0,
        "eds_actual_coverage": round(float(actual_count / wafer_count), 4) if wafer_count else 0,
        "eds_pending_count": int((frame["eds_status"] == "pending").sum()) if wafer_count else 0,
        "excluded_wafer_count": int(sum(excluded_reasons.values())),
        "excluded_reasons": excluded_reasons,
        "selected_condition_summary": {
            "product": filters.product or ["All"],
            "layer": filters.layer or ["All"],
            "step": filters.step or ["All"],
            "parameter": filters.parameter or [parameter],
            "eds_status": filters.eds_status,
        },
    }


def create_analysis_set(payload: AnalysisSetCreate) -> dict[str, Any]:
    frame = apply_filters(payload.filters)
    analysis_set_id = store.next_id("analysis_set", "AS")
    item = {
        "id": analysis_set_id,
        "name": payload.name,
        "filters": payload.filters.model_dump(),
        "metrics": summarize_filters(payload.filters, frame),
    }
    store.analysis_sets[analysis_set_id] = item
    return item


def list_analysis_sets() -> list[dict[str, Any]]:
    ensure_mock_data()
    return list(store.analysis_sets.values())


def get_analysis_set(analysis_set_id: str) -> dict[str, Any]:
    return store.analysis_sets[analysis_set_id]


def frame_for_analysis_set(analysis_set_id: str) -> pd.DataFrame:
    item = get_analysis_set(analysis_set_id)
    return apply_filters(item["filters"])
