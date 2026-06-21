"""analytics 핵심 로직 단위/통합 테스트.

순수 헬퍼(통계)는 합성 입력으로, compute_* 는 데모 데이터(data.load_dataframe)로 검증한다.
실데이터 교체 후에도 계약(필드/형식)이 깨지지 않는지 회귀 보호하는 목적.
실행: `cd backend && pytest -q`
"""
from types import SimpleNamespace as NS

import numpy as np
import pandas as pd
import pytest

import analytics
import data as D
from analytics import (
    _within_std, _control_limits, _drift, _fit_estimate,
    _with_target_groups, _apply_selection, _apply_target_date, _pooled_within_std,
    _corr_pvalue, _bh_fdr,
)

# 데모에서 파생(하드코딩 회피) — 첫 fab_step의 numeric feature들
FAB = D.FAB_STEPS[0]
NUM_FEATS = [k for k in D.numeric_feature_keys() if k.split("|")[1] == FAB]
DRIVER = NUM_FEATS[0]          # target 의존 driver(CD_MEAN)
NOISE = NUM_FEATS[1] if len(NUM_FEATS) > 1 else NUM_FEATS[0]  # 저상관 feature
TEMP = next((k for k in NUM_FEATS if "TEMP" in k), NUM_FEATS[-1])  # 챔버 mismatch feature
TGT = D.TARGETS_BY_CATEGORY["BIN"][0]  # BIN0000


def base_req(**over):
    dr = NS(start_date=D._FACT["fab_track_out_time"].min().strftime("%Y-%m-%d"),
            end_date=D._FACT["fab_track_out_time"].max().strftime("%Y-%m-%d"),
            time_column="fab_track_out_time")
    d = dict(line_id=D.LINE_IDS[0], product=D.PRODUCTS[0], category="BIN",
             eds_step=D.EDS_STEPS[0], date_range=dr, target_date_range=None,
             fab_step=FAB, x_features=[DRIVER], y_targets=[TGT],
             y_target_groups=[], category_feature=None, selection=None, bins=10, cpk_subgroup=None)
    d.update(over)
    return NS(**d)


# ───────────────────────── 순수 통계 헬퍼 ─────────────────────────
def test_within_std():
    # 이동범위 |Δ| = [1,1,1] → mean=1 → /1.128
    assert _within_std([1, 2, 3, 4]) == pytest.approx(1 / 1.128, rel=1e-3)
    assert _within_std([5]) is None          # n<2
    assert _within_std([]) is None


def test_control_limits_within_imr():
    # 관리한계 σ는 단기(군내 I-MR) = MR̄/1.128. [1..5]의 MR̄=1 → within=1/1.128.
    s = pd.Series([1, 2, 3, 4, 5])
    cl = _control_limits(s)
    within = 1.0 / 1.128
    assert cl["method"] == "within(I-MR)"
    assert cl["sigma"] == pytest.approx(within, abs=1e-3)             # 단기 σ
    assert cl["sigma_overall"] == pytest.approx(float(s.std()), abs=1e-3)  # 전체 σ도 노출
    assert cl["ucl"] == pytest.approx(3 + 3 * within, abs=1e-3)
    assert cl["lcl"] == pytest.approx(3 - 3 * within, abs=1e-3)
    # 상수열 → MR̄=0 → 전체 std로 fallback(둘 다 0이라 한계=평균)
    cf = _control_limits(pd.Series([7.0, 7.0, 7.0]))
    assert cf["method"] == "overall" and cf["sigma"] == 0
    assert _control_limits(pd.Series([1])) is None   # n<2


def test_drift_flagged_and_none():
    assert _drift([[i, 100.0] for i in range(10)]) is None      # n<20
    assert _drift([[i, 100.0] for i in range(25)]) is None      # sd=0
    jump = [[i, 100.0] for i in range(20)] + [[i, 110.0] for i in range(20, 25)]
    d = _drift(jump)
    assert d["flagged"] is True and d["direction"] == "up" and d["shift"] >= 1.0
    # 완만 — flag 안 됨
    flat = [[i, 100.0 + (i % 2) * 0.1] for i in range(25)]
    assert _drift(flat)["flagged"] is False


def test_corr_pvalue():
    # r=0.8, n=5 → 양측 p≈0.104 (비유의), r=0.5·n=400 → 매우 유의
    assert _corr_pvalue(0.8, 5) == pytest.approx(0.1041, abs=2e-3)
    assert _corr_pvalue(0.5, 400) < 1e-10
    assert _corr_pvalue(0.0, 50) == pytest.approx(1.0, abs=1e-6)   # 무상관 → p=1
    assert _corr_pvalue(0.9, 2) is None                            # df<1


def test_bh_fdr_monotone_and_order():
    # 입력 순서 보존 + 단조성. p 큰 값은 q≥p, 작은 값은 보정
    q = _bh_fdr([0.01, 0.04, 0.03, 0.005, None])
    assert q[4] is None                       # None은 유지
    present = [q[i] for i in (3, 0, 2, 1)]     # p 오름차순 인덱스
    assert present == sorted(present)          # q 단조 증가
    assert all(qi <= 1.0 for qi in present)
    assert _bh_fdr([None, None]) == [None, None]


def test_with_target_groups_min_count_requires_all():
    df = pd.DataFrame({"A": [1.0, 2.0, np.nan], "B": [10.0, np.nan, np.nan]})
    g = NS(name="G", sources=["A", "B"], agg="sum")
    out = _with_target_groups(df, [g])
    # 모든 source 있어야 합산: [11, NaN, NaN] (부분합 방지)
    assert out["G"].tolist()[0] == pytest.approx(11.0)
    assert pd.isna(out["G"].iloc[1]) and pd.isna(out["G"].iloc[2])


def test_with_target_groups_noop_without_groups():
    df = pd.DataFrame({"A": [1.0]})
    assert _with_target_groups(df, None) is df          # 그룹 없으면 원본 그대로


def test_fit_estimate_linear_and_extrap():
    obs = pd.DataFrame({"x": np.arange(1, 11, dtype=float),
                        "y": 2.0 * np.arange(1, 11) + 1.0})  # y=2x+1 정확
    un_x = [12.0, 13.0, 5.0]   # 2개는 관측범위[1,10] 밖 → 외삽 2/3
    sub = pd.DataFrame({
        "x": list(np.arange(1, 11, dtype=float)) + un_x,
        "observed": [True] * 10 + [False] * 3,
        "fab_track_out_time": pd.date_range("2026-01-01", periods=13, freq="D"),
        "wafer_id": [f"W{i}" for i in range(13)],
        "root_lot_id": [f"L{i}" for i in range(13)],
    })
    pts, fit, ids = _fit_estimate(obs, sub, "x", "y")
    assert fit["slope"] == pytest.approx(2.0, rel=1e-6)
    assert fit["intercept"] == pytest.approx(1.0, abs=1e-6)
    assert fit["r2"] == pytest.approx(1.0, rel=1e-6)
    assert fit["extrap"] == pytest.approx(2 / 3, rel=1e-3)   # 2/3 외삽
    assert len(pts) == 3 and len(ids) == 3
    assert ids[0] == ["L10", "W10"]   # [root_lot_id, wafer_id] 순서·정렬 일치


def test_fit_estimate_guards():
    small = pd.DataFrame({"x": [1.0, 2, 3], "y": [1.0, 2, 3]})
    sub = pd.DataFrame({"x": [1.0], "observed": [False],
                        "fab_track_out_time": pd.to_datetime(["2026-01-01"]),
                        "wafer_id": ["W"], "root_lot_id": ["L"]})
    assert _fit_estimate(small, sub, "x", "y") == ([], None, [])      # n<5
    const = pd.DataFrame({"x": [5.0] * 6, "y": [1.0, 2, 3, 4, 5, 6]})
    assert _fit_estimate(const, sub, "x", "y") == ([], None, [])      # sxx=0


def test_apply_selection_time_and_wafers():
    df = pd.DataFrame({
        "fab_track_out_time": pd.to_datetime(["2026-01-01", "2026-01-05", "2026-01-10"]),
        "wafer_id": ["A", "B", "C"],
    })
    # tz-aware 경계도 처리(내부에서 tz_localize None)
    sel = NS(time_range=["2026-01-04T00:00:00Z", "2026-01-11T00:00:00Z"], wafer_ids=None)
    assert _apply_selection(df, sel)["wafer_id"].tolist() == ["B", "C"]
    assert _apply_selection(df, NS(time_range=None, wafer_ids=["C"]))["wafer_id"].tolist() == ["C"]
    assert _apply_selection(df, None) is df


def test_apply_target_date_end_inclusive():
    sub = pd.DataFrame({"eds_tkout_time": pd.to_datetime(["2026-01-01", "2026-01-31", "2026-02-01"])})
    tdr = NS(start_date="2026-01-01", end_date="2026-01-31")   # end 당일 포함(+1일 처리)
    out = _apply_target_date(sub, tdr)
    assert len(out) == 2 and out["eds_tkout_time"].max().day == 31


# ───────────────────────── compute_* (데모 데이터) ─────────────────────────
def test_compute_binned_observed_only_and_truncate():
    resp = analytics.compute_binned(base_req())
    assert resp["fab_step"] == FAB and len(resp["combos"]) == 1
    assert all(b["n_observed"] == b["wafer_count"] for b in resp["combos"][0]["bins"])
    # 조합 폭증 → 24 cap truncate
    many = base_req(y_targets=D.TARGETS_BY_CATEGORY["BIN"][:25])
    r2 = analytics.compute_binned(many)
    assert r2["truncated"] is True and len(r2["combos"]) == analytics.req_max_combos()


def test_compute_timeseries_contract_and_identity():
    ts = analytics.compute_timeseries(base_req())
    assert ts["time_basis"]["expected_target_lag_days"] == D.TARGET_LAG_DAYS
    t = ts["targets"][0]
    assert t["observed_points"] and "wid" in t["observed_points"][0] and "rlot" in t["observed_points"][0]
    f = ts["features"][0]
    assert len(f["point_ids"]) == len(f["points"])      # 식별자 동행 정렬
    e = ts["estimates"][0]
    assert len(e["point_ids"]) == len(e["points"])
    fc = e["forecast"]
    for k in ("oos", "n", "ucl", "lcl", "shift", "mean_pred", "r2", "extrap", "low_conf"):
        assert k in fc


def test_forecast_confidence_guard():
    # driver(높은 R²) → 신뢰 / 노이즈 feature(낮은 R²) → 참고용
    drv = analytics.compute_timeseries(base_req(x_features=[DRIVER]))["estimates"][0]["forecast"]
    assert drv["low_conf"] is False and drv["r2"] >= 0.2
    noi = analytics.compute_timeseries(base_req(x_features=[NOISE]))["estimates"][0]["forecast"]
    assert noi["low_conf"] is True       # R²<0.2 또는 외삽≥0.5


def test_compute_table_structure():
    rows = analytics.compute_table(base_req())["rows"]
    assert len(rows) == 1
    r = rows[0]
    assert r["x_feature"] == DRIVER and r["y_target"] == TGT and r["n"] > 0
    assert r["mean"] is not None and r["dc_lower"] is not None


def test_compute_drivers_ranked():
    out = analytics.compute_drivers(base_req(x_features=NUM_FEATS))["targets"]
    drivers = out[0]["drivers"]
    assert drivers and drivers[0]["abs"] >= drivers[-1]["abs"]   # |corr| 내림차순
    assert drivers[0]["feature"] == DRIVER                       # driver가 최상위
    top = drivers[0]
    assert top["n"] >= analytics.MIN_N                           # 소표본 컷
    assert top["p_value"] is not None and top["q_value"] is not None
    assert 0.0 <= top["q_value"] <= 1.0
    assert top["q_value"] < 0.1                                  # 진짜 driver는 FDR 후에도 유의


def test_compute_interaction_identity():
    req = base_req()
    ireq = NS(line_id=req.line_id, product=req.product, category=req.category,
              eds_step=req.eds_step, date_range=req.date_range, target_date_range=None,
              fab_step=FAB, x_feature=DRIVER, y_feature=NOISE, value_field=TGT, y_target_groups=[])
    res = analytics.compute_interaction(ireq)
    assert res["n_total"] > 0 and res["scatter_points"]
    p = res["scatter_points"][0]
    assert "wid" in p and "rlot" in p and "t" in p


def test_raw_frame_has_identity_columns():
    df = analytics.raw_frame(base_req())
    for c in ("root_lot_id", "wafer_id", "observed", DRIVER, TGT):
        assert c in df.columns
    assert len(df) > 0


def test_pooled_within_std():
    # 두 군 [1,2,3]·[11,12,13] — 군내는 작고(σ_within=1) 군간은 큼
    sw = _pooled_within_std([1, 2, 3, 11, 12, 13], ['a', 'a', 'a', 'b', 'b', 'b'])
    assert sw == pytest.approx(1.0, abs=1e-3)
    assert sw < float(pd.Series([1, 2, 3, 11, 12, 13]).std())   # within << overall(군간차)
    assert _pooled_within_std([1, 2, 3], ['a', 'b', 'c']) is None  # 전부 singleton → 분리 불가


def test_compute_table_cpk_subgroup():
    # EQP_CH 부분군 vs time I-MR — method 라벨 + within ≤ overall + 챔버 mismatch가 부분군에서 드러남
    eqp = analytics.compute_table(base_req(x_features=[TEMP], cpk_subgroup="EQP_CH"))["rows"][0]
    imr = analytics.compute_table(base_req(x_features=[TEMP], cpk_subgroup=None))["rows"][0]
    assert eqp["x_within_method"] == "EQP_CH" and imr["x_within_method"] == "time(I-MR)"
    assert eqp["x_std_within"] <= eqp["x_std"] + 1e-9            # 풀드 within ≤ overall(분산분해)
    # 챔버 간 차이가 EQP_CH within에선 빠지므로 time-IMR보다 작음 (mismatch 드러남)
    assert eqp["x_std_within"] < imr["x_std_within"]


def test_validate_source_clean():
    assert D.validate_source() == []     # 데모 데이터는 계약 충족
