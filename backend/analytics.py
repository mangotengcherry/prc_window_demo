"""핵심 분석 로직 — 화면/네트워크와 무관한 순수 계산만 둔다."""
from typing import List

import pandas as pd


def _bin_one(df: pd.DataFrame, x_feature: str, y_target: str, bins: int) -> List[dict]:
    """단일 (feature, target)을 bins개 등간격 구간으로 binning."""
    cats = pd.cut(df[x_feature], bins=bins)
    grouped = df.groupby(cats, observed=True)[y_target].agg(["mean", "count"])
    out = []
    for interval, row in grouped.iterrows():
        out.append({
            "bin_left": round(float(interval.left), 4),
            "bin_right": round(float(interval.right), 4),
            "bin_center": round(float(interval.mid), 4),
            "y_avg": None if pd.isna(row["mean"]) else round(float(row["mean"]), 4),
            "wafer_count": int(row["count"]),
        })
    return out


def compute_binned(df: pd.DataFrame, fab_step: str, x_features: List[str],
                   y_targets: List[str], bins: int = 10) -> dict:
    """선택한 fab_step 안에서 (feature × target) 모든 조합의 binning 결과."""
    sub = df[df["fab_step"] == fab_step]
    combos = []
    for xf in x_features:
        for yt in y_targets:
            combos.append({
                "x_feature": xf,
                "y_target": yt,
                "bins": _bin_one(sub, xf, yt, bins),
            })
    return {"fab_step": fab_step, "combos": combos}


def compute_timeseries(df: pd.DataFrame, fab_step: str, x_features: List[str],
                       y_targets: List[str]) -> dict:
    """선택한 fab_step의 wafer별 시계열. 위(target) / 아래(feature) series로 분리."""
    sub = df[df["fab_step"] == fab_step].sort_values("trackout_time")
    t = [ts.isoformat() for ts in sub["trackout_time"]]

    targets = [
        {"name": yt, "points": [[ti, round(float(v), 4)] for ti, v in zip(t, sub[yt])]}
        for yt in y_targets
    ]
    features = [
        {"name": xf, "points": [[ti, round(float(v), 4)] for ti, v in zip(t, sub[xf])]}
        for xf in x_features
    ]
    return {"fab_step": fab_step, "targets": targets, "features": features}


def compute_table(df: pd.DataFrame, fab_step: str, x_features: List[str],
                  y_targets: List[str], dc_spec: dict) -> dict:
    """선택한 fab_step × 선택 feature × 선택 target 조합의 대표값(평균) 행.

    feature별 DC spec(lower/upper)을 함께 포함. user spec은 사용자 입력이라 프론트에서 채운다.
    """
    g = df[df["fab_step"] == fab_step]
    rows = []
    for xf in x_features:
        dc = dc_spec.get(xf, {})
        for yt in y_targets:
            rows.append({
                "fab_step": fab_step,
                "x_feature": xf,
                "x_value": round(float(g[xf].mean()), 4),
                "y_target": yt,
                "y_value": round(float(g[yt].mean()), 4),
                "dc_lower": dc.get("lower"),
                "dc_upper": dc.get("upper"),
            })
    return {"rows": rows}
