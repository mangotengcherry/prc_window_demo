"""계약/파생 레이어 — 분석(analytics)·API(main)가 import하는 공개 심볼을 제공한다.

원천 데이터/메타는 모두 data_source.py(교체 지점)에서 가져오고, 차원 목록·파생 메타는
여기서 데이터로부터 자동 계산한다. **보통 이 파일은 수정하지 않는다.**
(실데이터 적용은 data_source.py만 바꾸면 됨 — DATA_GUIDE.md 참고.)
"""
from functools import lru_cache

import pandas as pd

import data_source as src

# ── 원천 (data_source 위임) ──────────────────────────────────────────────────
load_dataframe = src.fact_table        # wafer×fab_step long fact table


def fab_metro_prc() -> pd.DataFrame:
    """X feature 카탈로그(메타)."""
    return src.feature_catalog()


def dc_spec() -> dict:
    """numeric feature_key → {lower, upper}."""
    return src.dc_spec()


# ── 파생 헬퍼 ────────────────────────────────────────────────────────────────
def numeric_feature_keys() -> list:
    cat = fab_metro_prc()
    return cat.loc[cat["data_type"] == "numeric", "feature_key"].tolist()


def feature_unit_map() -> dict:
    cat = fab_metro_prc()
    return dict(zip(cat["feature_key"], cat["unit"]))


# ── 차원 목록/상수 (데이터에서 파생 — import 시 1회 계산) ─────────────────────
TARGET_LAG_DAYS = src.target_lag_days()
EDS_STEPS = src.eds_steps()
TARGETS_BY_CATEGORY = src.targets_by_category()
CATEGORIES = list(TARGETS_BY_CATEGORY.keys())
ALL_TARGETS = [t for ts in TARGETS_BY_CATEGORY.values() for t in ts]
TARGET_UNIT = src.target_units()

def _uniq(series) -> list:
    """정렬된 고유값(plain str). numpy 스칼라가 새어나가지 않게 캐스팅."""
    return sorted({str(x) for x in series.dropna()})


_FACT = load_dataframe()
LINE_IDS = _uniq(_FACT["line_id"])
PRODUCTS = _uniq(_FACT["product"])
FAB_STEPS = list(dict.fromkeys(str(x) for x in fab_metro_prc()["fab_step"]))  # 카탈로그상 공정 순서 유지
# 분할(category feature) 값은 데이터에서 자동 파생 (정의는 data_source가 컬럼명만 제공)
CATEGORY_FEATURES = {
    name: _uniq(_FACT[name])
    for name in src.category_feature_names() if name in _FACT.columns
}


# ── 검증 (validate_data.py / 가이드에서 사용) ────────────────────────────────
def validate_source() -> list:
    """data_source가 계약 스키마를 만족하는지 점검. 문제 메시지 리스트 반환(빈 리스트=정상)."""
    problems = []
    fact = load_dataframe()
    cat = fab_metro_prc()

    required_cols = ["wafer_id", "line_id", "product", "fab_step",
                     "fab_track_out_time", "eds_tkout_time", "observed"]
    for c in required_cols:
        if c not in fact.columns:
            problems.append(f"fact_table에 필수 컬럼 누락: '{c}'")

    for c in ["fab_track_out_time", "eds_tkout_time"]:
        if c in fact.columns and not pd.api.types.is_datetime64_any_dtype(fact[c]):
            problems.append(f"fact_table['{c}']는 datetime 형이어야 함 (현재 {fact[c].dtype})")

    cat_required = ["fab_step", "data_type", "feature_key", "display_name", "unit",
                    "metro_step", "metro_grade", "metro_category"]
    for c in cat_required:
        if c not in cat.columns:
            problems.append(f"feature_catalog에 필수 컬럼 누락: '{c}'")

    # numeric feature_key는 fact_table에 동명 컬럼이 있어야 함
    if "feature_key" in cat.columns and "data_type" in cat.columns:
        for key in cat.loc[cat["data_type"] == "numeric", "feature_key"]:
            if key not in fact.columns:
                problems.append(f"numeric feature_key '{key}' 에 해당하는 fact_table 컬럼 없음")

    # 모든 target 컬럼 존재 확인
    for t in ALL_TARGETS:
        if t not in fact.columns:
            problems.append(f"target '{t}' 컬럼이 fact_table에 없음")

    # 분할 컬럼 존재
    for name in src.category_feature_names():
        if name not in fact.columns:
            problems.append(f"category feature '{name}' 컬럼이 fact_table에 없음")

    # dc_spec 키는 numeric feature_key여야 함
    nkeys = set(numeric_feature_keys())
    for k in dc_spec():
        if k not in nkeys:
            problems.append(f"dc_spec 키 '{k}' 가 numeric feature_key 목록에 없음")

    return problems


@lru_cache(maxsize=1)
def _warn_if_invalid():
    probs = validate_source()
    if probs:
        import sys
        print("⚠ data_source 스키마 경고:\n  - " + "\n  - ".join(probs), file=sys.stderr)
    return probs


_warn_if_invalid()
