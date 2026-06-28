from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.data.mock_store import store
from app.models.schemas import WindowReviewRequest
from app.services.analysis_set_service import frame_for_analysis_set, get_analysis_set
from app.services.bin_group_service import attach_group_metric, get_bin_group
from app.services.condition_rule_service import get_condition_rule, legend_for
from app.services.exclusion_service import get_exclusion_rule
from app.services.mock_data_service import H2H_BINS, NOT_OPEN_BINS, ensure_mock_data


def _round(value: Any, digits: int = 5) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


def _linear_stats(df: pd.DataFrame, x: str, y: str) -> dict[str, Any]:
    s = df[[x, y]].dropna()
    if len(s) < 3:
        return {"correlation": None, "slope": None}
    corr = float(np.corrcoef(s[x], s[y])[0, 1])
    slope = float(np.polyfit(s[x], s[y], 1)[0])
    return {"correlation": round(corr, 4), "slope": round(slope, 5)}


def _candidate_copy(stats: dict[str, Any], low_rate: float, high_rate: float) -> list[dict[str, str]]:
    candidates = []
    corr = stats.get("correlation") or 0
    slope = stats.get("slope") or 0
    if high_rate > low_rate * 1.25 and slope > 0:
        candidates.append({"type": "SPEC 완화 검토 후보", "basis": "High-side fail rate가 low-side risk보다 빠르게 상승합니다."})
        candidates.append({"type": "Target centering 후보", "basis": "FAB 관리 인자를 중심값에 가깝게 맞추면 high-side 노출을 줄일 수 있습니다."})
    if low_rate > high_rate * 1.25 and slope < 0:
        candidates.append({"type": "SPEC 강화 검토 후보", "basis": "선택 Window에서 low-side Not Open risk가 우세합니다."})
    if abs(corr) < 0.12:
        candidates.append({"type": "추가 검증 필요 후보", "basis": "전체 X-Y 관계가 약하므로 condition split 또는 interaction 확인이 필요합니다."})
    candidates.append({"type": "Split spec 후보", "basis": "공통 SPEC 변경 전 chamber, PPID, 부품 개조 전후 split을 검토해야 합니다."})
    return candidates


def _safe_window(df: pd.DataFrame, x: str, y: str) -> dict[str, Any]:
    s = df[[x, y]].dropna()
    if len(s) < 10:
        return {"lower": None, "upper": None}
    threshold = s[y].quantile(0.45)
    safe = s[s[y] <= threshold]
    return {"lower": _round(safe[x].quantile(0.15), 4), "upper": _round(safe[x].quantile(0.85), 4)}


def _binned(df: pd.DataFrame, x: str, y: str, bins: int, group_name: str) -> list[dict[str, Any]]:
    s = df[[x, y]].dropna().copy()
    if s.empty:
        return []
    s["bin"] = pd.cut(s[x], bins=bins, duplicates="drop")
    rows = []
    for interval, part in s.groupby("bin", observed=True):
        rows.append(
            {
                "bin_left": _round(interval.left, 4),
                "bin_right": _round(interval.right, 4),
                "bin_center": _round(interval.mid, 4),
                "metric": group_name,
                "fail_rate": _round(part[y].mean()),
                "median_fail_rate": _round(part[y].median()),
                "wafer_count": int(len(part)),
                "stderr": _round(part[y].std() / np.sqrt(len(part))) if len(part) > 1 else 0,
            }
        )
    return rows


def _trend(df: pd.DataFrame, x: str, y: str) -> dict[str, list[dict[str, Any]]]:
    actual = df[df["eds_status"] == "actual"].copy()
    pending = df[df["eds_status"] == "pending"].copy()
    actual["day"] = actual["process_date"].dt.strftime("%Y-%m-%d")
    pending["day"] = pending["expected_eds_date"].dt.strftime("%Y-%m-%d")
    actual_rows = [
        {"date": day, "actual_fail_rate": _round(part[y].mean()), "fab_mean": _round(part[x].mean()), "wafer_count": int(len(part))}
        for day, part in actual.groupby("day", observed=True)
    ]
    pending_rows = [
        {"date": day, "pending_wafer_count": int(len(part)), "fab_mean": _round(part[x].mean())}
        for day, part in pending.groupby("day", observed=True)
    ]
    return {"actual": actual_rows, "pending": pending_rows}


def _tradeoff(df: pd.DataFrame, x: str, bins: int) -> list[dict[str, Any]]:
    work = df[[x, "_h2h", "_not_open"]].dropna().copy()
    if work.empty:
        return []
    work["bin"] = pd.cut(work[x], bins=bins, duplicates="drop")
    rows = []
    for interval, part in work.groupby("bin", observed=True):
        rows.append(
            {
                "bin_center": _round(interval.mid, 4),
                "hole_to_hole_fail_rate": _round(part["_h2h"].mean()),
                "not_open_fail_rate": _round(part["_not_open"].mean()),
                "combined_fail_rate": _round(part["_h2h"].mean() + part["_not_open"].mean()),
                "wafer_count": int(len(part)),
            }
        )
    return rows


def _zone(df: pd.DataFrame, x: str, y: str, bins: int) -> list[dict[str, Any]]:
    rows = []
    for zone, part in df.groupby("zone", observed=True):
        for row in _binned(part, x, y, bins, str(zone)):
            row["zone"] = zone
            rows.append(row)
    return rows


def _interaction(df: pd.DataFrame, x: str, y: str) -> list[dict[str, Any]]:
    second = "metro_thickness" if x != "metro_thickness" else "fdc_temp_mean"
    work = df[[x, second, y]].dropna().copy()
    if work.empty:
        return []
    work["x_bin"] = pd.qcut(work[x], q=5, duplicates="drop")
    work["y_bin"] = pd.qcut(work[second], q=5, duplicates="drop")
    rows = []
    for (xb, yb), part in work.groupby(["x_bin", "y_bin"], observed=True):
        rows.append(
            {
                "x_parameter": x,
                "y_parameter": second,
                "x_bin": f"{xb.left:.2f}~{xb.right:.2f}",
                "y_bin": f"{yb.left:.2f}~{yb.right:.2f}",
                "fail_rate": _round(part[y].mean()),
                "wafer_count": int(len(part)),
            }
        )
    return rows


def _point(row: pd.Series, x: str, y: str, legend: str) -> dict[str, Any]:
    spec_target = 52.0
    return {
        "lot_id": row["lot_id"],
        "wafer_id": row["wafer_id"],
        "product": row["product"],
        "layer": row["layer"],
        "step": row["step"],
        "tool_id": row["tool_id"],
        "chamber_id": row["chamber_id"],
        "ppid": row["ppid"],
        "eco_number": row["eco_number"],
        "recipe_version": row["recipe_version"],
        "pm_age": _round(row["pm_age"], 2),
        "zone": row["zone"],
        "process_date": row["process_date"].strftime("%Y-%m-%d"),
        "expected_eds_date": row["expected_eds_date"].strftime("%Y-%m-%d"),
        "eds_status": row["eds_status"],
        "legend": legend,
        "x_value": _round(row[x], 4),
        "selected_bin_group_fail_rate": _round(row[y]),
        "eds_yield": _round(row["yield"]),
        "yield_loss": _round(1 - row["yield"]),
        "target_offset": _round(row[x] - spec_target, 4),
        "spec_margin": _round(min(row[x] - 50.8, 53.4 - row[x]), 4),
        "part_modification_flag": bool(row["part_modification_flag"]),
        "exclusion_status": "included",
    }


def compute_window_review(payload: WindowReviewRequest) -> dict[str, Any]:
    ensure_mock_data()
    analysis_set = get_analysis_set(payload.analysis_set_id)
    original_frame = frame_for_analysis_set(payload.analysis_set_id)
    exclusion = get_exclusion_rule(payload.exclusion_rule_id)
    frame = original_frame.copy()
    if exclusion:
        frame = frame[~frame["wafer_id"].isin(exclusion["wafer_ids"])].copy()

    group_ids = payload.bin_group_ids or ["BG001"]
    groups = [get_bin_group(group_id) for group_id in group_ids]
    primary_group = groups[0]
    metric_col = "_selected_metric"
    frame[metric_col] = attach_group_metric(frame, primary_group)
    original_frame[metric_col] = attach_group_metric(original_frame, primary_group)
    frame["_h2h"] = frame[[bin_id for bin_id in H2H_BINS if bin_id in frame.columns]].sum(axis=1)
    frame["_not_open"] = frame[[bin_id for bin_id in NOT_OPEN_BINS if bin_id in frame.columns]].sum(axis=1)

    x = payload.x_parameter
    bins = int(payload.view_options.get("bins", 8))
    actual = frame[frame["eds_status"] == "actual"].copy()
    rule = get_condition_rule(payload.condition_rule_id)
    if len(actual) > 1400:
        actual_scatter = actual.sample(1400, random_state=7)
    else:
        actual_scatter = actual
    scatter = [_point(row, x, metric_col, legend_for(row, rule)) for _, row in actual_scatter.iterrows()]

    stats = _linear_stats(actual, x, metric_col)
    low_cut = actual[x].quantile(0.25) if len(actual) else 0
    high_cut = actual[x].quantile(0.75) if len(actual) else 0
    low_rate = float(actual.loc[actual[x] <= low_cut, metric_col].mean()) if len(actual) else 0
    high_rate = float(actual.loc[actual[x] >= high_cut, metric_col].mean()) if len(actual) else 0
    safe_window = _safe_window(actual, x, metric_col)
    before_stats = _linear_stats(original_frame[original_frame["eds_status"] == "actual"], x, metric_col)
    after_stats = stats

    run_id = store.next_id("analysis_run", "RUN")
    response = {
        "analysis_run_id": run_id,
        "analysis_set": analysis_set,
        "synthetic_data_notice": store.metadata["synthetic_data_notice"],
        "context": {
            "x_parameter": x,
            "bin_groups": [{"id": group["id"], "name": group["name"], "bin_ids": group["bin_ids"], "zone": group.get("zone")} for group in groups],
            "condition_rule_id": payload.condition_rule_id,
            "exclusion_rule_id": payload.exclusion_rule_id,
        },
        "summary_metrics": {
            "wafer_count": int(len(frame)),
            "actual_wafer_count": int((frame["eds_status"] == "actual").sum()),
            "pending_wafer_count": int((frame["eds_status"] == "pending").sum()),
            "correlation": stats["correlation"],
            "slope": stats["slope"],
            "high_side_fail_rate": _round(high_rate),
            "low_side_fail_rate": _round(low_rate),
            "safe_window": safe_window,
        },
        "decision_candidates": _candidate_copy(stats, low_rate, high_rate),
        "evidence": [
            f"{primary_group['name']}을(를) {x} 기준으로 검토했습니다.",
            "High-side와 low-side trade-off BIN Group을 함께 비교합니다.",
            "Outlier 후보는 삭제하지 않고 Exclusion Rule version으로 저장할 때만 제외됩니다.",
        ],
        "scatter_data": scatter,
        "binned_response_data": _binned(actual, x, metric_col, bins, primary_group["name"]),
        "trend_data": _trend(frame, x, metric_col),
        "tradeoff_data": _tradeoff(actual, x, bins),
        "zone_data": _zone(actual, x, metric_col, max(4, bins // 2)),
        "interaction_heatmap_data": _interaction(actual, x, metric_col),
        "excluded_point_summary": {
            "exclusion_rule_id": payload.exclusion_rule_id,
            "excluded_count": int(len(original_frame) - len(frame)),
            "before": before_stats,
            "after": after_stats,
        },
    }
    store.analysis_runs[run_id] = response
    return response
