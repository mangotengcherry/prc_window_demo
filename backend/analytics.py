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


def _with_target_groups(df: pd.DataFrame, groups) -> pd.DataFrame:
    """인라인 grouped target → 합성 컬럼 추가. 원본 source가 NaN(미관측)이면 결과도 NaN."""
    if not groups:
        return df
    df = df.copy()
    for g in groups:
        srcs = [s for s in g.sources if s in df.columns]
        if not srcs:
            continue
        df[g.name] = df[srcs].sum(axis=1, min_count=1)  # 현재 sum만
    return df


def _cf_splits(sub: pd.DataFrame, cf):
    """category feature 값별로 (name, value, subdf) 분할. 미선택 시 단일 (None, None, sub)."""
    if cf and getattr(cf, "name", None) and getattr(cf, "values", None) and cf.name in sub.columns:
        return [(cf.name, v, sub[sub[cf.name] == v]) for v in cf.values]
    return [(None, None, sub)]


def _apply_selection(df: pd.DataFrame, sel) -> pd.DataFrame:
    """linked brushing — 선택 시간구간/wafer로 한정."""
    if sel is None:
        return df
    tr = getattr(sel, "time_range", None)
    if tr and len(tr) == 2:
        def _naive(x):
            t = pd.Timestamp(x)
            return t.tz_localize(None) if t.tzinfo is not None else t  # df는 tz-naive
        s, e = _naive(tr[0]), _naive(tr[1])
        if s > e:
            s, e = e, s
        df = df[(df["fab_track_out_time"] >= s) & (df["fab_track_out_time"] <= e)]
    wids = getattr(sel, "wafer_ids", None)
    if wids:
        df = df[df["wafer_id"].isin(wids)]
    return df


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
    df = _with_target_groups(D.load_dataframe(), getattr(req, "y_target_groups", None))
    sub = _filter_rows(df, line_id=req.line_id, product=req.product,
                       fab_step=req.fab_step, date_range=req.date_range)
    sub = _apply_selection(sub, getattr(req, "selection", None))  # linked brushing
    # observed-only + y target 확보 시점 필터
    sub = _apply_target_date(sub[sub["observed"]], req.target_date_range)

    splits = _cf_splits(sub, req.category_feature)

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


MIN_N = 10  # thin 기준 표본수 (columns.min_n과 동일 소스). 추천 window의 "표본 충분" 판정에도 사용.


def req_max_combos() -> int:
    return 24  # 현실성 리뷰 R4: 요청당 combo 하드 캡


# ---------------- /api/timeseries ----------------
def _control_limits(values: pd.Series):
    if len(values) < 2:
        return None
    mu, sigma = float(values.mean()), float(values.std())
    return {"ucl": round(mu + 3 * sigma, 4), "lcl": round(mu - 3 * sigma, 4), "sigma": round(sigma, 4)}


def _drift(points) -> Optional[dict]:
    """인사이트 4: 시계열 최근(마지막 20%) 평균이 기준(앞 80%) 대비 몇 σ 이동했는지 → 추세 감지."""
    n = len(points)
    if n < 20:
        return None
    vals = np.array([p[1] for p in points], dtype=float)
    sd = float(vals.std())
    if sd == 0:
        return None
    k = max(5, n // 5)
    shift = round((float(vals[-k:].mean()) - float(vals[:-k].mean())) / sd, 2)
    return {"shift": shift, "direction": "up" if shift >= 0 else "down", "flagged": bool(abs(shift) >= 1.0)}


def _fit_estimate(obs_rows: pd.DataFrame, sub: pd.DataFrame, xf: str, yt: str):
    """관측 wafer로 y~x 선형회귀 적합 → 미관측 wafer의 x로 y 추정 (사용자 선택: X–Y 회귀)."""
    o = obs_rows[obs_rows[xf].notna()]
    if len(o) < 5:
        return [], None
    x = o[xf].to_numpy(dtype=float)
    y = o[yt].to_numpy(dtype=float)
    sxx = float(((x - x.mean()) ** 2).sum())
    if sxx == 0:
        return [], None
    slope = float(((x - x.mean()) * (y - y.mean())).sum() / sxx)
    intercept = float(y.mean() - slope * x.mean())
    yhat = slope * x + intercept
    ss_res = float(((y - yhat) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = (1 - ss_res / ss_tot) if ss_tot else None
    # 미관측(=y 미확보) wafer를 x로 추정
    un = sub[sub[xf].notna() & (~sub["observed"])].sort_values("fab_track_out_time")
    pts = [[t.isoformat(), round(float(slope * xx + intercept), 4)] for t, xx in zip(un["fab_track_out_time"], un[xf])]
    fit = {"slope": round(slope, 6), "intercept": round(intercept, 4),
           "r2": round(float(r2), 4) if r2 is not None else None, "n": int(len(o))}
    return pts, fit


def compute_timeseries(req) -> dict:
    df = _with_target_groups(D.load_dataframe(), getattr(req, "y_target_groups", None))
    base = _filter_rows(df, line_id=req.line_id, product=req.product,
                        fab_step=req.fab_step, date_range=req.date_range).sort_values("fab_track_out_time")
    splits = _cf_splits(base, getattr(req, "category_feature", None))
    units = D.feature_unit_map()

    targets, features, estimates = [], [], []
    for cf_name, cf_val, sub in splits:
        for yt in req.y_targets:
            obs = _apply_target_date(sub[sub["observed"] & sub[yt].notna()], req.target_date_range)
            observed_points = [{
                "time": t.isoformat(), "value": round(float(v), 4),
                "value_status": "observed", "observed_time": e.isoformat(),
            } for t, v, e in zip(obs["fab_track_out_time"], obs[yt], obs["eds_tkout_time"])]
            targets.append({
                "name": yt, "display_name": yt, "unit": D.TARGET_UNIT.get(yt, ""),
                "category_feature_value": cf_val,
                "observed_points": observed_points,
                "estimated_points": [], "fit_summary": None,
                "avg": round(float(obs[yt].mean()), 4) if len(obs) else None,
                "control_limits": _control_limits(obs[yt]) if len(obs) else None,
            })
            # 조합별 추정 y (미관측 wafer) — y~x 선형회귀
            cl = _control_limits(obs[yt]) if len(obs) else None
            for xf in req.x_features:
                if xf not in sub.columns:
                    continue
                pts, fit = _fit_estimate(obs, sub, xf, yt)
                if pts:
                    # lag 기반 OOS 예측: 추정 y가 target 관리한계(±3σ)를 벗어나는 미확보 wafer 수
                    # + 미확보 batch 추정 평균이 관측 평균 대비 몇 σ 이동했는지(잠복 drift 조기경보)
                    forecast = None
                    if cl:
                        pv = [v for _, v in pts]
                        oos = sum(1 for v in pv if v > cl["ucl"] or v < cl["lcl"])
                        mean_pred = float(np.mean(pv))
                        sig = cl.get("sigma") or 0
                        shift = round((mean_pred - float(obs[yt].mean())) / sig, 2) if sig else 0.0
                        forecast = {"oos": int(oos), "n": len(pts), "ucl": cl["ucl"], "lcl": cl["lcl"],
                                    "shift": shift, "mean_pred": round(mean_pred, 2)}
                    estimates.append({"x_feature": xf, "y_target": yt,
                                      "category_feature_value": cf_val, "points": pts,
                                      "fit_summary": fit, "forecast": forecast})
        for xf in req.x_features:
            if xf not in sub.columns:
                continue
            fs = sub[sub[xf].notna()]
            points = [[t.isoformat(), round(float(v), 4)] for t, v in zip(fs["fab_track_out_time"], fs[xf])]
            features.append({
                "name": xf, "display_name": _meta_for(xf).get("display_name", xf),
                "unit": units.get(xf, ""), "category_feature_value": cf_val, "points": points,
                "avg": round(float(fs[xf].mean()), 4) if len(fs) else None,
                "control_limits": _control_limits(fs[xf]) if len(fs) else None,
                "drift": _drift(points),
            })

    return {
        "fab_step": req.fab_step,
        "time_basis": {
            "x_axis": "fab_track_out_time",
            "target_observed_time": "eds_tkout_time",
            "expected_target_lag_days": D.TARGET_LAG_DAYS,
        },
        "sampled": False,
        "n_total": int(len(base)),
        "targets": targets,
        "features": features,
        "estimates": estimates,
    }


# ---------------- /api/table ----------------
def compute_table(req) -> dict:
    df = _with_target_groups(D.load_dataframe(), getattr(req, "y_target_groups", None))
    base = _filter_rows(df, line_id=req.line_id, product=req.product,
                        fab_step=req.fab_step, date_range=req.date_range)
    base = _apply_selection(base, getattr(req, "selection", None))  # linked brushing
    base = _apply_target_date(base[base["observed"]], req.target_date_range)
    dcs = D.dc_spec()
    splits = _cf_splits(base, getattr(req, "category_feature", None))

    rows = []
    for cf_name, cf_val, sub in splits:
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
                    "category_feature_name": cf_name, "category_feature_value": cf_val,
                    "dc_lower": dc.get("lower"), "dc_upper": dc.get("upper"),
                    "n": n,
                    "mean": round(float(s[yt].mean()), 4) if n else None,
                    "std": round(float(s[yt].std()), 4) if n > 1 else None,
                })
    return {"rows": rows}


# ---------------- /api/drivers (인사이트 2) ----------------
def compute_drivers(req) -> dict:
    """선택 target별로 같은 fab_step의 numeric feature를 |corr|(관측 wafer 기준)로 정렬."""
    df = _with_target_groups(D.load_dataframe(), getattr(req, "y_target_groups", None))
    base = _filter_rows(df, line_id=req.line_id, product=req.product,
                        fab_step=req.fab_step, date_range=req.date_range)
    base = _apply_target_date(base[base["observed"]], req.target_date_range)
    prc = D.fab_metro_prc()
    feats = prc[(prc["fab_step"] == req.fab_step) & (prc["data_type"] == "numeric")]

    out = []
    for yt in req.y_targets:
        drivers = []
        if yt in base.columns:
            for _, fr in feats.iterrows():
                key = fr["feature_key"]
                if key not in base.columns:
                    continue
                s = base[base[key].notna() & base[yt].notna()]
                if len(s) < 5:
                    continue
                c = np.corrcoef(s[key], s[yt])[0, 1]
                if np.isnan(c):
                    continue
                drivers.append({"feature": key, "display_name": fr["display_name"],
                                "corr": round(float(c), 3), "abs": round(abs(float(c)), 3), "n": int(len(s))})
            drivers.sort(key=lambda d: -d["abs"])
        out.append({"target": yt, "drivers": drivers})
    return {"targets": out}


# ---------------- /api/interaction ----------------
SCATTER_CAP = 5000   # scatter 점수 캡. heatmap/rank·binning·범위·outlier 제외는
                     # 프론트가 이 점들로 즉시 계산(서버 재요청 없이 인터랙션 → 자원 효율)


def _empty_interaction(req):
    return {"x_feature": req.x_feature, "y_feature": req.y_feature, "value_field": req.value_field,
            "sampled": False, "n_total": 0, "scatter_points": []}


def compute_interaction(req) -> dict:
    """두 feature(x/y)와 value_field의 wafer 단위 점만 반환."""
    df = _with_target_groups(D.load_dataframe(), getattr(req, "y_target_groups", None))
    sub = _filter_rows(df, line_id=req.line_id, product=req.product,
                       fab_step=req.fab_step, date_range=req.date_range)
    sub = _apply_target_date(sub, req.target_date_range)

    xf, yf, vf = req.x_feature, req.y_feature, req.value_field
    use_count = vf == "__count__"
    need = [xf, yf] + ([] if use_count else [vf])
    if any(c not in sub.columns for c in need):
        return _empty_interaction(req)

    mask = sub[xf].notna() & sub[yf].notna()
    if not use_count:
        mask &= sub[vf].notna()
    s = sub[mask]
    n_total = int(len(s))
    if n_total == 0:
        return _empty_interaction(req)

    sampled = n_total > SCATTER_CAP
    ss = s.sample(SCATTER_CAP, random_state=0) if sampled else s
    scatter = [{"x": round(float(x), 4), "y": round(float(y), 4),
                "value": None if use_count else round(float(v), 4)}
               for x, y, v in zip(ss[xf], ss[yf], (ss[xf] if use_count else ss[vf]))]

    return {"x_feature": xf, "y_feature": yf, "value_field": vf,
            "sampled": sampled, "n_total": n_total, "scatter_points": scatter}
