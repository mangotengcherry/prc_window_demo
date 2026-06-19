"""계약 동형(contract-isomorphic) 데모 데이터 생성기 (M0).

회사 backend를 연결하기 전, ui_enhancement_request.md의 계약(§7)과 같은 모양의
mock을 제공한다. 실제 적용 시 이 파일만 회사 DB 조회로 교체한다.

핵심 차원:
  - line_id / product / category / eds_step / fab_step
  - X feature = pipe-key:  data_type|fab_step|metro_step|metro_item|subitem
  - Y target = BIN/MSR/AWACS 계열
  - fab_metro_prc 매칭 테이블 (FAB_STEP ↔ METRO_*)
  - 시간기준 분리: fab_track_out_time(공정 trackout) vs eds_tkout_time(EDS 확보)
    → lag(약 60일) 때문에 최근 구간은 y target 미확보(observed=False)
"""
from functools import lru_cache

import numpy as np
import pandas as pd

# 데모 기준 "현재" 시각 (lag로 인한 미확보 구간을 만들기 위해 고정)
NOW = pd.Timestamp("2026-06-19")
TARGET_LAG_DAYS = 60

LINE_IDS = ["AAAA", "BBBB", "CCCC", "DDDD"]
PRODUCTS = ["AAEQ", "BBCR", "CCAK", "DDGQ"]
CATEGORIES = ["BIN", "MSR", "AWACS"]
EDS_STEPS = ["EDS_M", "EDS_P"]
FAB_STEPS = ["EQ760200", "AB123456", "CD345678"]

# 카테고리별 Y target (이름은 category 접두 규칙) — 단위 포함
TARGETS_BY_CATEGORY = {
    "BIN": ["BIN0131", "BIN0132", "BIN0133"],
    "MSR": ["MSR0001", "MSR0002"],
    "AWACS": ["AWACS01"],
}
ALL_TARGETS = [t for ts in TARGETS_BY_CATEGORY.values() for t in ts]
TARGET_UNIT = {t: ("ea" if t.startswith("BIN") else "a.u.") for t in ALL_TARGETS}

# category feature (wafer 단위 속성)
CATEGORY_FEATURES = {
    "PPID": ["표준조건", "평가조건1", "평가조건2"],
    "ECO": ["공정평가1", "공정평가2"],
    "EQP_MODEL": ["MODEL_A", "MODEL_B"],
    "EQP": ["EQP01", "EQP02"],
    "EQP_CH": ["CH1", "CH2"],
}

# fab_metro_prc 매칭 테이블: (fab_step, metro_step, metro_item, grade, category, data_type, subitem, unit)
_FAB_METRO_PRC = [
    ("EQ760200", "MT100001", "CD_MEAN", "A", "VM", "numeric", "avg", "nm"),
    ("EQ760200", "MT100002", "OVL_X", "B", "Metro", "numeric", "avg", "nm"),
    ("EQ760200", "FD200001", "TEMP_SENSOR_01", "A", "FDC", "numeric", "std", "degC"),
    ("AB123456", "MT110001", "THK_MEAN", "A", "VM", "numeric", "avg", "A"),
    ("AB123456", "MT110002", "RS_MEAN", "B", "PC", "numeric", "avg", "ohm"),
    ("CD345678", "MT120001", "CD_MEAN", "A", "VM", "numeric", "avg", "nm"),
    ("CD345678", "FD300001", "PRESSURE_01", "B", "FDC", "numeric", "std", "mTorr"),
]


def feature_key(data_type, fab_step, metro_step, metro_item, subitem):
    return f"{data_type}|{fab_step}|{metro_step}|{metro_item}|{subitem}"


def display_name(metro_item, subitem):
    return f"{metro_item} / {subitem}"


@lru_cache(maxsize=1)
def fab_metro_prc() -> pd.DataFrame:
    """매칭 테이블 + 파생 feature key/메타."""
    rows = []
    for fab, mstep, item, grade, cat, dtype, sub, unit in _FAB_METRO_PRC:
        rows.append({
            "fab_step": fab,
            "metro_step": mstep,
            "metro_item": item,
            "metro_grade": grade,
            "metro_category": cat,
            "data_type": dtype,
            "subitem": sub,
            "unit": unit,
            "feature_key": feature_key(dtype, fab, mstep, item, sub),
            "display_name": display_name(item, sub),
        })
    return pd.DataFrame(rows)


def numeric_feature_keys():
    df = fab_metro_prc()
    return df.loc[df["data_type"] == "numeric", "feature_key"].tolist()


def feature_unit_map():
    df = fab_metro_prc()
    return dict(zip(df["feature_key"], df["unit"]))


# feature별 DC spec (numeric만). 실제론 설정/DB 관리.
@lru_cache(maxsize=1)
def dc_spec() -> dict:
    rng = np.random.default_rng(7)
    out = {}
    for key in numeric_feature_keys():
        center = 100 + 40 * rng.random()
        half = 8 + 6 * rng.random()
        out[key] = {"lower": round(center - half, 2), "upper": round(center + half, 2)}
    return out


@lru_cache(maxsize=1)
def load_dataframe() -> pd.DataFrame:
    """wafer × fab_step long-format fact table.

    한 행 = (wafer_id, fab_step). 그 행의 fab_step에 해당하는 feature 컬럼만 채워지고,
    나머지 feature 컬럼은 NaN. target/category_feature는 wafer 단위로 모든 행에 반복.
    """
    rng = np.random.default_rng(42)
    n_wafers = 1600
    metro = fab_metro_prc()
    dcs = dc_spec()
    num_keys = numeric_feature_keys()
    cat_keys = metro.loc[metro["data_type"] == "category", "feature_key"].tolist()

    rows = []
    for w in range(n_wafers):
        wid = f"W{w:05d}"
        line = rng.choice(LINE_IDS)
        product = rng.choice(PRODUCTS)
        # wafer 투입 시점: 최근 ~7개월에 분포 (일부는 lag로 EDS 미확보)
        wafer_start = NOW - pd.Timedelta(days=int(rng.integers(5, 210)))
        cat_feat_vals = {cf: rng.choice(vals) for cf, vals in CATEGORY_FEATURES.items()}

        # wafer-level target (numeric). 일부 feature와 약한 관계 부여(시각화용)
        target_vals = {t: float(rng.normal(500 if t.startswith("BIN") else 50, 30)) for t in ALL_TARGETS}

        for si, fab in enumerate(FAB_STEPS):
            fab_tko = wafer_start + pd.Timedelta(hours=6 * si)
            eds_tko = wafer_start + pd.Timedelta(days=TARGET_LAG_DAYS) + pd.Timedelta(hours=6 * si)
            observed = eds_tko <= NOW

            row = {
                "wafer_id": wid,
                "line_id": line,
                "product": product,
                "fab_step": fab,
                "fab_track_out_time": fab_tko,
                "eds_tkout_time": eds_tko,
                "observed": bool(observed),
            }
            row.update(cat_feat_vals)
            # 이 fab_step에 해당하는 numeric/category feature 값 채우기
            for key in num_keys:
                if key.split("|")[1] == fab:
                    spec = dcs.get(key, {"lower": 90, "upper": 130})
                    center = (spec["lower"] + spec["upper"]) / 2
                    row[key] = float(rng.normal(center, (spec["upper"] - spec["lower"]) / 4))
            for key in cat_keys:
                if key.split("|")[1] == fab:
                    row[key] = rng.choice(CATEGORY_FEATURES["EQP_CH"])
            # target은 observed일 때만 값, 아니면 NaN (M0: observed-only)
            for t in ALL_TARGETS:
                row[t] = target_vals[t] if observed else np.nan
            rows.append(row)

    return pd.DataFrame(rows)
