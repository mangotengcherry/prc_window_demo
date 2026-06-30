from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from typing import Any

from fastapi import HTTPException

from app.data.mock_store import store
from app.models.schemas import AnalysisConditionCopy, AnalysisConditionUpdate, AnalysisSetCreate, AnalysisSetFilters
from app.services.analysis_set_service import create_analysis_set
from app.services.mock_data_service import ensure_mock_data


def _condition_or_404(condition_id: str) -> dict[str, Any]:
    ensure_mock_data()
    condition = store.analysis_conditions.get(condition_id)
    if not condition:
        raise HTTPException(status_code=404, detail="analysis condition not found")
    return condition


def list_analysis_conditions() -> dict[str, list[dict[str, Any]]]:
    ensure_mock_data()
    conditions = list(store.analysis_conditions.values())
    return {
        "shared": [condition for condition in conditions if condition["scope"] == "shared"],
        "personal": [condition for condition in conditions if condition["scope"] == "personal"],
    }


def copy_to_personal(condition_id: str, payload: AnalysisConditionCopy) -> dict[str, Any]:
    source = deepcopy(_condition_or_404(condition_id))
    new_id = store.next_id("analysis_condition", "AC")
    source.update(
        {
            "id": new_id,
            "scope": "personal",
            "readonly": False,
            "owner": payload.owner,
            "source_condition_id": condition_id,
            "name": payload.name or f"{source['name']} 개인 복사본",
        }
    )
    store.analysis_conditions[new_id] = source
    return source


def update_analysis_condition(condition_id: str, payload: AnalysisConditionUpdate) -> dict[str, Any]:
    condition = _condition_or_404(condition_id)
    if condition["readonly"]:
        raise HTTPException(status_code=409, detail="shared condition is read-only; copy it to a personal condition before editing")

    data = payload.model_dump(exclude_unset=True)
    for key in ("fab_filters", "eds_filters", "analysis_filters", "legend_config"):
        if key in data:
            condition[key] = {**condition.get(key, {}), **(data.pop(key) or {})}
    for key, value in data.items():
        condition[key] = value
    if "selected_bin_group_ids" in condition:
        condition["eds_filters"]["selected_bin_group_ids"] = condition["selected_bin_group_ids"]
    return condition


def _resolved_analysis_filters(condition: dict[str, Any]) -> AnalysisSetFilters:
    ensure_mock_data()
    filters = dict(condition.get("analysis_filters") or {})
    fab_filters = condition.get("fab_filters") or {}
    filters["eds_status"] = "actual_only"
    if fab_filters.get("date_mode") == "recent_days":
        max_date = store.wafer_data["process_date"].max()
        recent_days = int(fab_filters.get("recent_days") or 30)
        start_date = max_date - timedelta(days=max(recent_days - 1, 0))
        filters["start_date"] = start_date.strftime("%Y-%m-%d")
        filters["end_date"] = max_date.strftime("%Y-%m-%d")
    else:
        filters["start_date"] = fab_filters.get("start_date")
        filters["end_date"] = fab_filters.get("end_date")
    for key in ("product", "layer", "step", "parameter", "tool", "chamber", "ppid", "eco"):
        if key in fab_filters:
            filters[key] = fab_filters[key] or []
    return AnalysisSetFilters(**filters)


def create_analysis_set_from_condition(condition_id: str) -> dict[str, Any]:
    condition = _condition_or_404(condition_id)
    filters = _resolved_analysis_filters(condition)
    return create_analysis_set(AnalysisSetCreate(name=condition["name"], filters=filters))
