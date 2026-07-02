from __future__ import annotations

import pandas as pd
from fastapi import APIRouter

from app.data.mock_store import store
from app.models.schemas import ExpressionValidateRequest
from app.services.expression_service import ExpressionError, columns_used, evaluate_column, evaluate_filter, resolve_column
from app.services.mock_data_service import ensure_mock_data

router = APIRouter()


def _context_frame(context: str) -> pd.DataFrame:
    ensure_mock_data()
    if context == "fab":
        return store.fab_history
    df = store.wafer_data.copy()
    df["value"] = df["metro_ch_hole_cd"]
    df["part_id"] = "All"
    df["eds_step"] = "M"
    df["test_time"] = df["eds_test_time_m"]
    return df


@router.post("/api/expressions/validate")
def validate_expression(payload: ExpressionValidateRequest):
    df = _context_frame(payload.context)
    try:
        if payload.mode == "filter":
            result = evaluate_filter(payload.expression, df)
        else:
            result = evaluate_column(payload.expression, df)
        resolved: list[str] = []
        for name in columns_used(payload.expression):
            col = resolve_column(name, df)
            if col not in resolved:
                resolved.append(col)
        return {"valid": True, "columns_used": resolved, "result_dtype": str(result.dtype)}
    except ExpressionError as exc:
        return {"valid": False, "error": exc.message, "position": exc.position}
