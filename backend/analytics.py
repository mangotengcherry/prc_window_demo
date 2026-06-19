"""핵심 분석 로직 (M0). 화면/네트워크와 무관한 순수 계산.

규칙(현실성 리뷰 R1): binning·table은 observed-only. 추정값은 M2(시계열 오버레이 전용).
"""
from typing import List, Optional

import numpy as np
import pandas as pd

import data as D


# ---------------- 공통 필터 ----------------
def _filter_rows(df: pd.DataFrame, *, line_id, product, fab_step, date_range) -> pd.DataFrame:
    m = (df["line_id"] == line_id) & (df["product"] == product) & (df["fab_step"] == fab_step)
    if date_range is not None:
        col = date_range.time_column if date_range.time_column in df.columns else "fab_track_out_time"
        start = pd.Timestamp(date_range.start_date)
        end = pd.Timestamp(date_range.end_date) + pd.Timedelta(days=1)
        m &= (df[col] >= start) & (df[col] < end)
    return df[m]


def _within_std(vals) -> Optional[float]:
    """단기(short-term) σ — 이동범위 기반 (I-MR): mean(|Δ|)/1.128. Cpk용."""
    a = np.asarray(vals, dtype=float)
    if a.size < 2:
        return None
    mr = np.abs(np.diff(a)).mean()
    return round(float(mr / 1.128), 4)


def _apply_target_date(sub: pd.DataFrame, tdr) -> pd.DataFrame:
    """y target 확보 시점(eds_tkout_time) 기준 추가 필터."""
    if tdr is None:
        return sub
    start = pd.Timestamp(tdr.start_date)
    end = pd.Timestamp(tdr.end_date) + pd.Timedelta(days=1)
    return sub[(sub["eds_tkout_time"] >= start) & (sub["eds_tkout_time"] < end)]


def _meta_for(feature_key: str) -> dict:
    prc = D.fab_metro_prc()
    hit = prc[prc["feature_key"] == feature_key]
    if hit.empty:
        return {}
    return hit.iloc[0].to_dict()


# ---------------- /api/x-feature-options ----------------
def list_x_features(fab_step: Optional[str], matching: bool,
                    metro_grade: Optional[str], metro_category: Optional[str]) -> List[dict]:
    prc = D.fab_metro_prc().copy()
    if matching and fab_step:
        prc = prc[prc["fab_step"] == fab_step]
    if metro_grade:
        prc = prc[prc["metro_grade"] == metro_grade]
    if metro_category:
        prc = prc[prc["metro_category"] == metro_category]

    df = D.load_dataframe()
    ref_target = D.ALL_TARGETS[0]
    out = []
    for _, r in prc.iterrows():
        key = r["feature_key"]
        score = None
        if r["data_type"] == "numeric" and key in df.columns:
            sub = df[(df["fab_step"] == r["fab_step"]) & df[key].notna() & df[ref_target].notna()]
            if len(sub) > 5:
                c = np.corrcoef(sub[key], sub[ref_target])[0, 1]
                score = None if np.isnan(c) else round(abs(float(c)), 3)
        out.append({
            "name": key,
            "display_name": r["display_name"],
            "data_type": r["data_type"],
            "metro_step": r["metro_step"],
            "metro_item": r["metro_item"],
            "subitem": r["subitem"],
            "metro_grade": r["metro_grade"],
            "metro_category": r["metro_category"],
            "matched_fab_steps": [r["fab_step"]],
            "unit": r["unit"],
            "score": score,
        })
    return out


# ---------------- /api/binned ----------------
def _bin_one(sub: pd.DataFrame, x_feature: str, y_target: str, bins: int) -> List[dict]:
    s = sub[sub[x_feature].notna() & sub[y_target].notna()]
    if len(s) < 2 or x_feature not in s.columns:
        return []
    cats = pd.cut(s[x_feature], bins=bins)
    g = s.groupby(cats, observed=True)[y_target].agg(["mean", "count", "std"])
    out = []
    for interval, row in g.iterrows():
        n = int(row["count"])
        std = None if pd.isna(row["std"]) else round(float(row["std"]), 4)
        sem = None if (std is None or n == 0) else round(float(std / np.sqrt(n)), 4)
        out.append({
            "bin_left": round(float(interval.left), 4),
            "bin_right": round(float(interval.right), 4),
            "bin_center": round(float(interval.mid), 4),
            "y_avg": None if pd.isna(row["mean"]) else round(float(row["mean"]), 4),
            "wafer_count": n,
            "y_std": std,
            "y_sem": sem,
            "n_observed": n,
        })
    return out


def compute_binned(req) -> dict:
    df = D.load_dataframe()
    sub = _filter_rows(df, line_id=req.line_id, product=req.product,
                       fab_step=req.fab_step, date_range=req.date_range)
    # observed-only + y target 확보 시점 필터
    sub = _apply_target_date(sub[sub["observed"]], req.target_date_range)

    cf = req.category_feature
    splits = [(None, None, sub)]
    if cf and cf.name and cf.values and cf.name in sub.columns:
        splits = [(cf.name, v, sub[sub[cf.name] == v]) for v in cf.values]

    combos = []
    truncated = False
    for xf in req.x_features:
        meta = _meta_for(xf)
        if meta.get("data_type") != "numeric":
            continue  # M0: category x feature는 binning 제외
        for yt in req.y_targets:
            for cf_name, cf_val, s in splits:
                if len(combos) >= req_max_combos():
                    truncated = True
                    break
                combos.append({
                    "x_feature": xf,
                    "x_feature_display_name": meta.get("display_name", xf),
                    "y_target": yt,
                    "category": req.category,
                    "eds_step": req.eds_step,
                    "category_feature_name": cf_name,
                    "category_feature_value": cf_val,
                    "bins": _bin_one(s, xf, yt, req.bins),
                })
    return {"fab_step": req.fab_step, "combos": combos, "truncated": truncated}


def req_max_combos() -> int:
    return 24  # 현실성 리뷰 R4: 요청당 combo 하드 캡


# ---------------- /api/timeseries ----------------
def _control_limits(values: pd.Series):
    if len(values) < 2:
        return None
    mu, sigma = float(values.mean()), float(values.std())
    return {"ucl": round(mu + 3 * sigma, 4), "lcl": round(mu - 3 * sigma, 4), "sigma": round(sigma, 4)}


def compute_timeseries(req) -> dict:
    df = D.load_dataframe()
    sub = _filter_rows(df, line_id=req.line_id, product=req.product,
                       fab_step=req.fab_step, date_range=req.date_range).sort_values("fab_track_out_time")

    targets = []
    for yt in req.y_targets:
        obs = _apply_target_date(sub[sub["observed"] & sub[yt].notna()], req.target_date_range)
        observed_points = [{
            "time": t.isoformat(), "value": round(float(v), 4),
            "value_status": "observed", "observed_time": e.isoformat(),
        } for t, v, e in zip(obs["fab_track_out_time"], obs[yt], obs["eds_tkout_time"])]
        targets.append({
            "name": yt, "display_name": yt, "unit": D.TARGET_UNIT.get(yt, ""),
            "observed_points": observed_points,
            "estimated_points": [],  # M0: 추정 미구현 (M2)
            "fit_summary": None,
            "avg": round(float(obs[yt].mean()), 4) if len(obs) else None,
            "control_limits": _control_limits(obs[yt]) if len(obs) else None,
        })

    features = []
    units = D.feature_unit_map()
    for xf in req.x_features:
        if xf not in sub.columns:
            continue
        fs = sub[sub[xf].notna()]
        points = [[t.isoformat(), round(float(v), 4)] for t, v in zip(fs["fab_track_out_time"], fs[xf])]
        features.append({
            "name": xf, "display_name": _meta_for(xf).get("display_name", xf),
            "unit": units.get(xf, ""), "points": points,
            "avg": round(float(fs[xf].mean()), 4) if len(fs) else None,
            "control_limits": _control_limits(fs[xf]) if len(fs) else None,
        })

    return {
        "fab_step": req.fab_step,
        "time_basis": {
            "x_axis": "fab_track_out_time",
            "target_observed_time": "eds_tkout_time",
            "expected_target_lag_days": D.TARGET_LAG_DAYS,
        },
        "sampled": False,
        "n_total": int(len(sub)),
        "targets": targets,
        "features": features,
    }


# ---------------- /api/table ----------------
def compute_table(req) -> dict:
    df = D.load_dataframe()
    sub = _filter_rows(df, line_id=req.line_id, product=req.product,
                       fab_step=req.fab_step, date_range=req.date_range)
    sub = _apply_target_date(sub[sub["observed"]], req.target_date_range)
    dcs = D.dc_spec()

    rows = []
    for xf in req.x_features:
        meta = _meta_for(xf)
        dc = dcs.get(xf, {})
        for yt in req.y_targets:
            s = sub[sub[xf].notna() & sub[yt].notna()] if xf in sub.columns else sub.iloc[0:0]
            n = int(len(s))
            x_within = _within_std(s.sort_values("fab_track_out_time")[xf].values) if n else None
            rows.append({
                "line_id": req.line_id, "product": req.product,
                "category": req.category, "eds_step": req.eds_step, "fab_step": req.fab_step,
                "x_feature": xf, "x_feature_display_name": meta.get("display_name", xf),
                "x_value": round(float(s[xf].mean()), 4) if n else None,
                "x_std": round(float(s[xf].std()), 4) if n > 1 else None,
                "x_std_within": x_within,
                "y_target": yt,
                "y_value": round(float(s[yt].mean()), 4) if n else None,
                "value_status": "observed",
                "metro_step": meta.get("metro_step", ""), "metro_item": meta.get("metro_item", ""),
                "metro_grade": meta.get("metro_grade", ""), "metro_category": meta.get("metro_category", ""),
                "category_feature_name": None, "category_feature_value": None,
                "dc_lower": dc.get("lower"), "dc_upper": dc.get("upper"),
                "n": n,
                "mean": round(float(s[yt].mean()), 4) if n else None,
                "std": round(float(s[yt].std()), 4) if n > 1 else None,
            })
    return {"rows": rows}
