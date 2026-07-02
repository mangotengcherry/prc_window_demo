from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)

try:
    from scipy import stats as scipy_stats
except ImportError:  # pragma: no cover - scipy is a declared dependency
    scipy_stats = None
    logger.warning("scipy를 불러오지 못해 commonality_data 계산을 건너뜁니다.")

COMMONALITY_FACTORS = ["tool_id", "chamber_id", "ppid", "eco_number", "recipe_version", "part_modification_flag"]


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
        candidates.insert(0, {"type": "추가 검증 필요 후보", "basis": "전체 X-Y 관계가 약하므로 condition split 또는 interaction 확인이 필요합니다."})
    candidates.append({"type": "Split spec 후보", "basis": "공통 SPEC 변경 전 chamber, PPID, 부품 개조 전후 split을 검토해야 합니다."})
    return candidates


def _safe_window(df: pd.DataFrame, x: str, y: str) -> dict[str, Any]:
    s = df[[x, y]].dropna()
    if len(s) < 10:
        return {"lower": None, "upper": None}
    threshold = s[y].quantile(0.45)
    safe = s[s[y] <= threshold]
    return {"lower": _round(safe[x].quantile(0.15), 4), "upper": _round(safe[x].quantile(0.85), 4)}


def _safe_window_occupancy(df: pd.DataFrame, x: str, safe_window: dict[str, Any]) -> float | None:
    lower = safe_window.get("lower")
    upper = safe_window.get("upper")
    if lower is None or upper is None:
        return None
    s = df[x].dropna()
    if s.empty:
        return None
    return _round(((s >= lower) & (s <= upper)).mean(), 4)


def _recent_trend(actual: pd.DataFrame, y: str) -> dict[str, Any] | None:
    s = actual[["process_date", y]].dropna()
    if s.empty:
        return None
    last_date = s["process_date"].max()
    recent_start = last_date - pd.Timedelta(days=29)
    prior_start = recent_start - pd.Timedelta(days=30)
    prior_end = recent_start - pd.Timedelta(days=1)
    recent = s[(s["process_date"] >= recent_start) & (s["process_date"] <= last_date)]
    prior = s[(s["process_date"] >= prior_start) & (s["process_date"] <= prior_end)]
    recent_fail = recent[y].mean() if len(recent) else None
    prior_fail = prior[y].mean() if len(prior) else None
    delta = (recent_fail - prior_fail) if recent_fail is not None and prior_fail is not None and not pd.isna(recent_fail) and not pd.isna(prior_fail) else None
    return {
        "recent_30d_fail": _round(recent_fail),
        "prior_30d_fail": _round(prior_fail),
        "delta": _round(delta),
    }


def _spc(actual_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    values = [(row["date"], row["actual_fail_rate"]) for row in actual_rows if row["actual_fail_rate"] is not None]
    if len(values) < 20:
        return None
    dates = [v[0] for v in values]
    series = np.array([v[1] for v in values], dtype=float)
    center = float(series.mean())
    sigma = float(series.std(ddof=1))
    ucl = center + 3 * sigma
    lcl = center - 3 * sigma
    violations: list[dict[str, str]] = []
    for date, value in zip(dates, series, strict=False):
        if value > ucl or value < lcl:
            violations.append({"date": date, "type": "beyond_3sigma"})
    run_side = 0  # +1 above center, -1 below center, 0 undefined
    run_length = 0
    for date, value in zip(dates, series, strict=False):
        side = 1 if value > center else (-1 if value < center else 0)
        if side != 0 and side == run_side:
            run_length += 1
        else:
            run_side = side
            run_length = 1 if side != 0 else 0
        if side != 0 and run_length == 7:
            violations.append({"date": date, "type": "run_of_7"})
    return {
        "center": _round(center),
        "ucl": _round(ucl),
        "lcl": _round(lcl),
        "sigma": _round(sigma),
        "violations": violations,
    }


def _pareto(actual: pd.DataFrame, bin_cols: list[str], selected_bin_ids: set[str]) -> list[dict[str, Any]]:
    if not bin_cols or actual.empty:
        return []
    means = actual[bin_cols].mean()
    total = means.sum()
    if total <= 0:
        return []
    top = means.sort_values(ascending=False).head(30)
    rows = []
    cum = 0.0
    for bin_id, mean_fail_rate in top.items():
        contribution = float(mean_fail_rate) / float(total)
        cum += contribution
        rows.append(
            {
                "bin_id": bin_id,
                "mean_fail_rate": _round(mean_fail_rate),
                "loss_contribution": _round(contribution, 4),
                "cum_pct": _round(cum, 4),
                "in_selected_group": bin_id in selected_bin_ids,
            }
        )
    return rows


def _driver_ranking(actual: pd.DataFrame, y: str, numeric_columns: list[str]) -> list[dict[str, Any]]:
    rows = []
    for column in numeric_columns:
        if column not in actual.columns or column == y:
            continue
        s = actual[[column, y]].dropna()
        n = len(s)
        if n < 30 or s[column].std(ddof=0) == 0 or s[y].std(ddof=0) == 0:
            continue
        corr = float(np.corrcoef(s[column], s[y])[0, 1])
        rows.append({"parameter": column, "corr": _round(corr, 4), "abs_corr": _round(abs(corr), 4), "n": n})
    rows.sort(key=lambda row: row["abs_corr"], reverse=True)
    return rows


def _commonality(actual: pd.DataFrame, y: str, factors: list[str]) -> list[dict[str, Any]]:
    if scipy_stats is None:
        return []
    rows = []
    for factor in factors:
        if factor not in actual.columns:
            continue
        s = actual[[factor, y]].dropna()
        group_frames = [part[y].to_numpy() for _, part in s.groupby(factor, observed=True) if len(part) >= 5]
        if len(group_frames) < 2:
            continue
        h_stat, p_value = scipy_stats.kruskal(*group_frames)
        k = len(group_frames)
        n = sum(len(g) for g in group_frames)
        epsilon_sq = (h_stat - k + 1) / (n - k) if n > k else None
        groups = []
        worst_value = None
        worst_median = None
        for value, part in s.groupby(factor, observed=True):
            if len(part) < 5:
                continue
            median = float(part[y].median())
            groups.append(
                {
                    "value": value,
                    "n": int(len(part)),
                    "median": _round(median),
                    "q1": _round(part[y].quantile(0.25)),
                    "q3": _round(part[y].quantile(0.75)),
                    "mean": _round(part[y].mean()),
                    "min": _round(part[y].min()),
                    "max": _round(part[y].max()),
                }
            )
            if worst_median is None or median > worst_median:
                worst_median = median
                worst_value = value
        rows.append(
            {
                "factor": factor,
                "p_value": _round(p_value, 6),
                "effect_size": _round(epsilon_sq, 4) if epsilon_sq is not None else None,
                "group_count": k,
                "worst_group": worst_value,
                "groups": groups,
            }
        )
    rows.sort(key=lambda row: row["p_value"] if row["p_value"] is not None else 1.0)
    return rows


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


def _interaction(df: pd.DataFrame, x: str, y: str, second: str | None = None) -> list[dict[str, Any]]:
    if not second:
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
    metric_columns: dict[str, str] = {}
    for group in groups:
        col_name = f"_metric_{group['id']}"
        frame[col_name] = attach_group_metric(frame, group)
        original_frame[col_name] = attach_group_metric(original_frame, group)
        metric_columns[group["id"]] = col_name
    metric_col = metric_columns[primary_group["id"]]
    y_axis_option = payload.view_options.get("y_axis_metric")
    if y_axis_option == "yield":
        metric_col = "yield"
    elif y_axis_option in metric_columns:
        metric_col = metric_columns[y_axis_option]
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

    safe_window_occupancy = _safe_window_occupancy(frame, x, safe_window)
    recent_trend = _recent_trend(actual, metric_col)
    trend_data = _trend(frame, x, metric_col)
    trend_data["spc"] = _spc(trend_data["actual"])

    bin_cols = [c for c in actual.columns if c.startswith("BIN_")]
    selected_bin_ids = {bin_id for group in groups for bin_id in group["bin_ids"]}
    pareto_data = _pareto(actual, bin_cols, selected_bin_ids)
    driver_ranking = _driver_ranking(actual, metric_col, store.metadata.get("numeric_columns", []))
    commonality_data = _commonality(actual, metric_col, COMMONALITY_FACTORS)

    interaction_x = payload.view_options.get("interaction_x") or x
    if interaction_x not in actual.columns:
        interaction_x = x
    interaction_y = payload.view_options.get("interaction_y")
    if interaction_y and interaction_y not in actual.columns:
        interaction_y = None

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
            "safe_window_occupancy": safe_window_occupancy,
            "recent_trend": recent_trend,
        },
        "decision_candidates": _candidate_copy(stats, low_rate, high_rate),
        "evidence": [
            f"{primary_group['name']}을(를) {x} 기준으로 검토했습니다.",
            "High-side와 low-side trade-off BIN Group을 함께 비교합니다.",
            "Outlier 후보는 삭제하지 않고 Exclusion Rule version으로 저장할 때만 제외됩니다.",
        ],
        "scatter_data": scatter,
        "binned_response_data": _binned(actual, x, metric_col, bins, primary_group["name"]),
        "trend_data": trend_data,
        "tradeoff_data": _tradeoff(actual, x, bins),
        "zone_data": _zone(actual, x, metric_col, max(4, bins // 2)),
        "interaction_heatmap_data": _interaction(actual, interaction_x, metric_col, interaction_y),
        "pareto_data": pareto_data,
        "driver_ranking": driver_ranking,
        "commonality_data": commonality_data,
        "excluded_point_summary": {
            "exclusion_rule_id": payload.exclusion_rule_id,
            "excluded_count": int(len(original_frame) - len(frame)),
            "before": before_stats,
            "after": after_stats,
        },
    }
    store.analysis_runs[run_id] = response
    return response
