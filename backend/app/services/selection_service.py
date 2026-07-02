"""물량 선정 criteria(FAB join + EDS melt) 파이프라인 (§7).

FAB 진행 이력(join, 최대 3블록 AND)과 EDS 아이템(melt·파생·커스텀 합성)을 조합해
미리보기(scatter)를 만들고, Analysis Set 스냅샷(§1.3)의 wafer 모집단도 같은 FAB/EDS
경로로 계산한다.
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd
from fastapi import HTTPException

from app.data.mock_store import store
from app.models.schemas import ChartState, EdsCriteria, FabCriteria, PresetCriteria, SelectionPreviewRequest
from app.services import preset_service
from app.services.expression_service import ExpressionError, evaluate_column, evaluate_filter
from app.services.mock_data_service import ensure_mock_data, part_value, step_value

_TEST_TIME_COL = {
    "M": "eds_test_time_m",
    "P": "eds_test_time_p",
    "ML": "eds_test_time_ml",
    "PL": "eds_test_time_pl",
}
_ITEM_PREFIXES = ("BIN_", "MSR_")
_COMPUTED_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")


class SelectionStageError(Exception):
    def __init__(self, stage: str, message: str):
        super().__init__(message)
        self.stage = stage
        self.message = message


def _list_filter(df: pd.DataFrame, column: str, values: list[str]) -> pd.Series:
    return pd.Series(True, index=df.index) if not values else df[column].isin(values)


def _fab_join(fab: FabCriteria) -> tuple[set[str], list[dict[str, Any]], int]:
    """product 마스크 + 블록별 (step & 진행기간 & 필터식) → 전체 교집합(AND)."""
    history = store.fab_history
    product_mask = _list_filter(history, "product", fab.products)
    matched_sets: list[set[str]] = []
    fab_step_matches: list[dict[str, Any]] = []
    excluded_by_fab_filter = 0
    for block in fab.step_conditions:
        subset = history.loc[product_mask & (history["step_id"] == block.fab_step)]
        if block.date_range.start:
            subset = subset.loc[subset["track_out_time"] >= pd.Timestamp(block.date_range.start)]
        if block.date_range.end:
            subset = subset.loc[subset["track_out_time"] <= pd.Timestamp(block.date_range.end)]
        base_count = len(subset)
        if block.filter_expression.strip():
            try:
                mask = evaluate_filter(block.filter_expression, subset)
            except ExpressionError as exc:
                raise SelectionStageError(f"fab_filter:{block.fab_step}", exc.message) from exc
            subset = subset.loc[mask]
        matched = len(subset)
        excluded_by_fab_filter += base_count - matched
        fab_step_matches.append({"fab_step": block.fab_step, "matched": matched})
        matched_sets.append(set(subset["wafer_id"]))
    wafer_ids = set.intersection(*matched_sets) if matched_sets else set()
    return wafer_ids, fab_step_matches, excluded_by_fab_filter


def _apply_fab_excludes(wafer_ids: set[str], fab: FabCriteria) -> pd.DataFrame:
    df = store.wafer_data
    subset = df.loc[df["wafer_id"].isin(wafer_ids)]
    mask = pd.Series(True, index=subset.index)
    if fab.exclude_rework:
        mask &= ~subset["is_rework"]
    if fab.exclude_engineering_lot:
        mask &= ~subset["is_engineering_lot"]
    if fab.exclude_abnormal_route:
        mask &= ~subset["is_abnormal_route"]
    return subset.loc[mask].copy()


def _drop_item_columns(frame: pd.DataFrame) -> pd.DataFrame:
    drop_cols = [c for c in frame.columns if c.startswith(_ITEM_PREFIXES)]
    return frame.drop(columns=drop_cols) if drop_cols else frame


def _derived_value_series(item: str, eds_step: str, part_id: str, wafer_ids: list[str]) -> pd.Series:
    base = store.wafer_data.set_index("wafer_id")[item].reindex(wafer_ids)
    step_applied = pd.Series(
        {wafer_id: step_value(float(v), wafer_id, item, eds_step) for wafer_id, v in base.items()}
    )
    return pd.Series(
        {wafer_id: part_value(v, wafer_id, item, part_id) for wafer_id, v in step_applied.items()}
    ).reindex(wafer_ids)


def _item_value_series(item_name: str, category: str, eds_step: str, part_id: str, wafer_ids: list[str]) -> pd.Series:
    base_items = set(store.metadata["eds_items"][category])
    if item_name in base_items:
        return _derived_value_series(item_name, eds_step, part_id, wafer_ids)
    try:
        terms = preset_service.expand_custom_item(item_name)
    except HTTPException as exc:
        raise SelectionStageError("eds_items", str(exc.detail)) from exc
    total = pd.Series(0.0, index=wafer_ids)
    for term_item, sign in terms:
        total = total + sign * _derived_value_series(term_item, eds_step, part_id, wafer_ids)
    return total


def _build_eds_frame(fab_frame: pd.DataFrame, eds: EdsCriteria) -> pd.DataFrame:
    test_time_col = _TEST_TIME_COL[eds.eds_step]
    base = fab_frame.dropna(subset=[test_time_col]).copy()
    if eds.date_range.start:
        base = base.loc[base[test_time_col] >= pd.Timestamp(eds.date_range.start)]
    if eds.date_range.end:
        base = base.loc[base[test_time_col] <= pd.Timestamp(eds.date_range.end)]
    base = _drop_item_columns(base)
    if base.empty or not eds.eds_items:
        return base.assign(value=pd.Series(dtype=float), eds_item=pd.Series(dtype=object), part_id=eds.part_id,
                            eds_step=eds.eds_step, test_time=base[test_time_col])
    wafer_ids = base["wafer_id"].tolist()
    rows = []
    for item in eds.eds_items:
        values = _item_value_series(item, eds.eds_category, eds.eds_step, eds.part_id, wafer_ids)
        item_frame = base.copy()
        item_frame["value"] = item_frame["wafer_id"].map(values)
        item_frame["eds_item"] = item
        item_frame["part_id"] = eds.part_id
        item_frame["eds_step"] = eds.eds_step
        item_frame["test_time"] = item_frame[test_time_col]
        rows.append(item_frame)
    return pd.concat(rows, ignore_index=True)


def _apply_eds_filter(long_frame: pd.DataFrame, eds: EdsCriteria) -> tuple[pd.DataFrame, int]:
    base_count = len(long_frame)
    if eds.filter_expression.strip() and base_count:
        try:
            mask = evaluate_filter(eds.filter_expression, long_frame)
        except ExpressionError as exc:
            raise SelectionStageError("eds_filter", exc.message) from exc
        long_frame = long_frame.loc[mask]
    return long_frame, base_count - len(long_frame)


def _apply_computed_columns(frame: pd.DataFrame, chart: ChartState) -> pd.DataFrame:
    for column in chart.computed_columns:
        if not _COMPUTED_NAME_RE.match(column.name):
            raise SelectionStageError(f"computed:{column.name}", "파생 컬럼 이름은 영숫자와 밑줄만 사용할 수 있습니다")
        if column.name in frame.columns:
            raise SelectionStageError(f"computed:{column.name}", f"이미 존재하는 컬럼과 이름이 충돌합니다: {column.name}")
        try:
            frame[column.name] = evaluate_column(column.expression, frame)
        except ExpressionError as exc:
            raise SelectionStageError(f"computed:{column.name}", exc.message) from exc
    return frame


def _apply_adhoc_filters(frame: pd.DataFrame, chart: ChartState) -> tuple[pd.DataFrame, int]:
    base_count = len(frame)
    for expression in chart.adhoc_filters:
        try:
            mask = evaluate_filter(expression, frame)
        except ExpressionError as exc:
            raise SelectionStageError("adhoc", exc.message) from exc
        frame = frame.loc[mask]
    return frame, base_count - len(frame)


def resolve_population(criteria: PresetCriteria) -> pd.DataFrame:
    """criteria(FAB+EDS)로 정의된 wafer 모집단을 wafer_data wide 포맷으로 반환한다 (§1.3 Analysis Set 스냅샷)."""
    ensure_mock_data()
    wafer_ids, _fab_step_matches, _excluded = _fab_join(criteria.fab)
    fab_frame = _apply_fab_excludes(wafer_ids, criteria.fab)
    if criteria.eds is None:
        return fab_frame
    long_frame = _build_eds_frame(fab_frame, criteria.eds)
    long_frame, _excluded_eds = _apply_eds_filter(long_frame, criteria.eds)
    keep_ids = set(long_frame["wafer_id"].unique()) if not long_frame.empty else set()
    return fab_frame.loc[fab_frame["wafer_id"].isin(keep_ids)].copy()


def _fab_time_map(wafer_ids: list[str], primary_step: str) -> pd.Series:
    history = store.fab_history
    rows = history.loc[history["step_id"] == primary_step]
    rows = rows.loc[rows["wafer_id"].isin(wafer_ids)]
    return rows.set_index("wafer_id")["track_out_time"]


def _columns_summary(chart: ChartState, frame: pd.DataFrame) -> dict[str, list[str]]:
    categorical = list(store.metadata["categorical_columns"])
    numeric = list(store.metadata["numeric_columns"])
    for column in chart.computed_columns:
        if column.name not in frame.columns:
            continue
        if pd.api.types.is_numeric_dtype(frame[column.name]) and not pd.api.types.is_bool_dtype(frame[column.name]):
            numeric.append(column.name)
        else:
            categorical.append(column.name)
    return {"categorical": categorical, "numeric": numeric}


def _isoformat(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).isoformat()


def _build_points(
    frame: pd.DataFrame, chart: ChartState, fab_time_map: pd.Series, sample_limit: int
) -> tuple[list[dict[str, Any]], bool, int]:
    n_total = len(frame)
    if n_total == 0:
        return [], False, 0

    if chart.x_axis == "eds_time":
        frame = frame.sort_values("test_time")
    else:
        frame = frame.assign(_fab_time=frame["wafer_id"].map(fab_time_map)).sort_values("_fab_time")

    sampled = False
    if sample_limit > 0 and n_total > sample_limit:
        idx = np.unique(np.linspace(0, n_total - 1, sample_limit).round().astype(int))
        frame = frame.iloc[idx]
        sampled = True

    legend_col = chart.legend_by if chart.legend_by in frame.columns else None
    points = []
    for row in frame.itertuples():
        x_value = fab_time_map.get(row.wafer_id) if chart.x_axis == "fab_time" else row.test_time
        legend = str(getattr(row, legend_col)) if legend_col else "전체"
        points.append(
            {
                "wafer_id": row.wafer_id,
                "lot_id": row.lot_id,
                "x": _isoformat(x_value),
                "y": round(float(row.value), 5) if pd.notna(row.value) else None,
                "legend": legend,
                "meta": {
                    "tool_id": row.tool_id,
                    "chamber_id": row.chamber_id,
                    "ppid": row.ppid,
                    "zone": row.zone,
                    "eds_item": row.eds_item,
                    "part_id": row.part_id,
                },
            }
        )
    return points, sampled, n_total


def preview(payload: SelectionPreviewRequest) -> dict[str, Any]:
    ensure_mock_data()
    try:
        wafer_ids, fab_step_matches, excluded_by_fab_filter = _fab_join(payload.fab)
        fab_frame = _apply_fab_excludes(wafer_ids, payload.fab)
        primary_step = payload.fab.primary_step or payload.fab.step_conditions[0].fab_step
        fab_time_map = _fab_time_map(fab_frame["wafer_id"].tolist(), primary_step)

        excluded_by_eds_filter = 0
        eds_matched_count = 0
        eds_match_ratio = 0.0
        points: list[dict[str, Any]] = []
        sampled = False
        n_total = 0

        if payload.eds is not None:
            long_frame = _build_eds_frame(fab_frame, payload.eds)
            long_frame, excluded_by_eds_filter = _apply_eds_filter(long_frame, payload.eds)
            long_frame = _apply_computed_columns(long_frame, payload.chart)
            long_frame, excluded_by_adhoc = _apply_adhoc_filters(long_frame, payload.chart)

            first_item = payload.eds.eds_items[0] if payload.eds.eds_items else None
            preview_frame = long_frame.loc[long_frame["eds_item"] == first_item] if first_item else long_frame.iloc[0:0]
            wafer_count = int(len(fab_frame))
            eds_matched_count = int(preview_frame["wafer_id"].nunique())
            eds_match_ratio = round(eds_matched_count / wafer_count, 4) if wafer_count else 0.0
            columns = _columns_summary(payload.chart, long_frame)
            points, sampled, n_total = _build_points(preview_frame, payload.chart, fab_time_map, payload.sample_limit)
        else:
            frame = _apply_computed_columns(fab_frame.copy(), payload.chart)
            frame, excluded_by_adhoc = _apply_adhoc_filters(frame, payload.chart)
            wafer_count = int(len(fab_frame))
            columns = _columns_summary(payload.chart, frame)

        summary = {
            "lot_count": int(fab_frame["lot_id"].nunique()),
            "wafer_count": wafer_count,
            "fab_step_matches": fab_step_matches,
            "eds_matched_count": eds_matched_count,
            "eds_match_ratio": eds_match_ratio,
            "excluded_by_fab_filter": excluded_by_fab_filter,
            "excluded_by_eds_filter": excluded_by_eds_filter,
            "excluded_by_adhoc": excluded_by_adhoc,
        }
        return {
            "summary": summary,
            "columns": columns,
            "points": points,
            "sampled": sampled,
            "n_total": n_total,
        }
    except SelectionStageError as exc:
        return {"error": {"stage": exc.stage, "message": exc.message}}
