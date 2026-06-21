"""데이터 소스 (★ 교체 지점 ★) — 팀원은 보통 이 파일만 바꾼다.

이 파일은 분석/대시보드가 필요로 하는 "원천 데이터 + 메타"를 제공하는 8개 provider
함수로만 구성된다. 회사 DB/CSV 조회로 바꿀 땐 아래 함수들의 **본문만** 채우면 되고,
분석 로직(analytics.py)·API(main.py)·계약 파생(data.py)은 건드릴 필요가 없다.

스키마(필수 컬럼/형식)와 단계별 교체 방법은 DATA_GUIDE.md 참고.
교체 후에는 `python validate_data.py` 로 스키마 적합성을 먼저 검증할 것.

현재 구현 = 계약 동형(contract-isomorphic) 데모 생성기.
"""
from functools import lru_cache

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# 데모 파라미터 (실데이터로 교체하면 대부분 불필요 — 참고용)
# ─────────────────────────────────────────────────────────────────────────────
_NOW = pd.Timestamp("2026-06-19")     # 데모 기준 "현재"(lag 미확보 구간 생성용)
_LAG_MIN, _LAG_MAX = 50, 60           # EDS 확보 지연(일) — wafer마다 50~60일 변동
_LAG_DAYS = _LAG_MAX                  # 명목 lag(provenance "~N일 이전 기준" 표기용)
_N_WAFERS = 1600

_TARGETS_BY_CATEGORY = {
    "BIN": [f"BIN{i:04d}" for i in range(601)],  # BIN0000~BIN0600 (실 구성)
    "MSR": ["MSR0001", "MSR0002"],   # 구성은 실무 적용 시 검토
    "AWACS": ["AWACS01"],            # 구성은 실무 적용 시 검토
}
_EDS_STEPS = ["EDS_M", "EDS_P"]

# 분할(category feature) = wafer 단위 속성. 값은 데모용; 실데이터에선 데이터에서 자동 파생.
_CATEGORY_FEATURE_VALUES = {
    "PPID": ["표준조건", "평가조건1", "평가조건2"],
    "ECO": ["공정평가1", "공정평가2"],
    "EQP_MODEL": ["MODEL_A", "MODEL_B"],
    "EQP": ["EQP01", "EQP02"],
    "EQP_CH": ["CH1", "CH2"],
}

# feature 카탈로그(=fab_metro_prc): (fab_step, metro_step, metro_item, grade, category, data_type, subitem, unit)
_FEATURE_CATALOG_ROWS = [
    ("EQ760200", "MT100001", "CD_MEAN", "A", "VM", "numeric", "avg", "nm"),
    ("EQ760200", "MT100002", "OVL_X", "B", "Metro", "numeric", "avg", "nm"),
    ("EQ760200", "FD200001", "TEMP_SENSOR_01", "A", "FDC", "numeric", "std", "degC"),
    ("AB123456", "MT110001", "THK_MEAN", "A", "VM", "numeric", "avg", "A"),
    ("AB123456", "MT110002", "RS_MEAN", "B", "PC", "numeric", "avg", "ohm"),
    ("CD345678", "MT120001", "CD_MEAN", "A", "VM", "numeric", "avg", "nm"),
    ("CD345678", "FD300001", "PRESSURE_01", "B", "FDC", "numeric", "std", "mTorr"),
]


def feature_key(data_type, fab_step, metro_step, metro_item, subitem) -> str:
    """X feature 식별자(파이프키). fact_table의 feature 컬럼명 == 이 값."""
    return f"{data_type}|{fab_step}|{metro_step}|{metro_item}|{subitem}"


# ═════════════════════════════════════════════════════════════════════════════
# ★ provider 함수 8개 — 실데이터 교체 시 본문만 바꾼다 ★
# ═════════════════════════════════════════════════════════════════════════════

def target_lag_days() -> int:
    """EDS 확보 지연(일). time_basis·provenance 안내에 사용."""
    return _LAG_DAYS


def eds_steps() -> list:
    """EDS step 선택지(드롭다운). 행 필터엔 쓰지 않는 조직 라벨."""
    return list(_EDS_STEPS)


def targets_by_category() -> dict:
    """category → [Y target 컬럼명]. category 선택지·target 후보가 여기서 나온다."""
    return {k: list(v) for k, v in _TARGETS_BY_CATEGORY.items()}


def target_units() -> dict:
    """Y target → 단위 문자열."""
    return {t: ("ea" if t.startswith("BIN") else "a.u.")
            for ts in _TARGETS_BY_CATEGORY.values() for t in ts}


def category_feature_names() -> list:
    """분할 가능한 wafer 단위 컬럼명 목록(fact_table에 동명 컬럼 존재해야 함)."""
    return list(_CATEGORY_FEATURE_VALUES.keys())


@lru_cache(maxsize=1)
def feature_catalog() -> pd.DataFrame:
    """X feature 메타(=fab_metro_prc). 컬럼: fab_step, metro_step, metro_item,
    metro_grade, metro_category, data_type, subitem, unit, feature_key, display_name."""
    rows = []
    for fab, mstep, item, grade, cat, dtype, sub, unit in _FEATURE_CATALOG_ROWS:
        rows.append({
            "fab_step": fab, "metro_step": mstep, "metro_item": item,
            "metro_grade": grade, "metro_category": cat, "data_type": dtype,
            "subitem": sub, "unit": unit,
            "feature_key": feature_key(dtype, fab, mstep, item, sub),
            "display_name": f"{item} / {sub}",
        })
    return pd.DataFrame(rows)


@lru_cache(maxsize=1)
def dc_spec() -> dict:
    """numeric feature_key → {lower, upper} (device-control spec). 실제론 설정/DB 관리."""
    rng = np.random.default_rng(7)
    cat = feature_catalog()
    keys = cat.loc[cat["data_type"] == "numeric", "feature_key"].tolist()
    out = {}
    for key in keys:
        center = 100 + 40 * rng.random()
        half = 8 + 6 * rng.random()
        out[key] = {"lower": round(center - half, 2), "upper": round(center + half, 2)}
    return out


@lru_cache(maxsize=1)
def fact_table() -> pd.DataFrame:
    """wafer × fab_step long-format fact table (핵심). 한 행 = (wafer_id, fab_step).
    그 행의 fab_step에 해당하는 numeric feature 컬럼만 값, 나머지는 NaN.
    target/category_feature는 wafer 단위로 모든 행에 반복. target은 observed일 때만 값.

    필수 컬럼: wafer_id, root_lot_id, line_id, product, fab_step, fab_track_out_time,
    eds_tkout_time, observed, + feature 컬럼(feature_key명) + target 컬럼 + 분할 컬럼.
    """
    rng = np.random.default_rng(42)
    rng_t = np.random.default_rng(123)  # target 노이즈 전용 — feature 실현이 target 개수에 흔들리지 않게 분리
    cat = feature_catalog()
    dcs = dc_spec()
    num_keys = cat.loc[cat["data_type"] == "numeric", "feature_key"].tolist()
    fab_steps = list(dict.fromkeys(cat["fab_step"]))
    all_targets = [t for ts in _TARGETS_BY_CATEGORY.values() for t in ts]
    bin_targets = [t for t in all_targets if t.startswith("BIN")]
    other_targets = [t for t in all_targets if not t.startswith("BIN")]
    nan_targets = {t: np.nan for t in all_targets}  # 미관측 행 target 일괄(601+개 개별 대입 회피)
    lines = ["AAAA", "BBBB", "CCCC", "DDDD"]
    products = ["AAEQ", "BBCR", "CCAK", "DDGQ"]

    def _center(key):
        s = dcs.get(key, {"lower": 90, "upper": 130})
        return (s["lower"] + s["upper"]) / 2, (s["upper"] - s["lower"]) / 4
    # 추정/window 분석이 의미 있도록 BIN target을 첫 fab_step의 한 feature(driver)에 약하게 의존시킴
    driver_key = next((k for k in num_keys if k.split("|")[1] == fab_steps[0]), None)
    driver_c = _center(driver_key)[0] if driver_key else 0.0

    rows = []
    for w in range(_N_WAFERS):
        wid = f"W{w:05d}"
        rlot = f"LOT{w // 25:04d}"  # wafer 25매 = 1 root lot (실데이터에선 원천 lot id 사용)
        line = rng.choice(lines)
        product = rng.choice(products)
        wafer_start = _NOW - pd.Timedelta(days=int(rng.integers(5, 210)))
        # EDS 확보 지연은 wafer마다 변동(먼저 팹아웃→먼저 테스트). 고정 60일 아님.
        lag = int(rng.integers(_LAG_MIN, _LAG_MAX + 1))
        cat_feat_vals = {cf: rng.choice(vals) for cf, vals in _CATEGORY_FEATURE_VALUES.items()}

        # 1) wafer의 모든 numeric feature 값 먼저 생성
        feats = {}
        for key in num_keys:
            c, sd = _center(key)
            feats[key] = float(rng.normal(c, sd))
        # 최근 ~70일 driver feature에 상승 추세 부여 → 잠복 excursion(lag로 target 아직 미확보).
        # 관측 구간엔 거의 안 보이고, 미확보(추정) 구간에서 target이 관리한계로 치닫는 시나리오.
        days_ago = (_NOW - wafer_start).days
        if driver_key and days_ago < 70:
            feats[driver_key] += (70 - days_ago) * 0.5
        # 데모: Cpk/Ppk 진단이 다양한 상태를 보이도록 일부 비-driver feature에 프로파일 부여.
        # 값만 변경(rng 미소비) → driver/forecast 시나리오 불변. OVL=산포↓(과잉), TEMP=시간드리프트(Cpk≫Ppk).
        for key in num_keys:
            if key == driver_key:
                continue
            item = key.split("|")[3]
            if item == "OVL_X":
                c = _center(key)[0]
                feats[key] = c + (feats[key] - c) * 0.30
            elif item == "TEMP_SENSOR_01":
                # 챔버(EQP_CH) 간 대칭 오프셋(±0.8σ) — 중심은 유지하되 군간 차이 큼.
                # → EQP_CH 부분군 Cpk≫Ppk(설비 mismatch)로 드러나지만, time-IMR엔 within에 흡수돼 가려짐.
                c, sd0 = _center(key)
                feats[key] = c + (feats[key] - c) * 0.40
                feats[key] += 0.8 * sd0 if cat_feat_vals.get("EQP_CH") == "CH2" else -0.8 * sd0
        # 2) target — BIN은 driver feature에 약한 선형 의존 + 노이즈, 그 외는 무작위
        dep = 3.0 * (feats[driver_key] - driver_c) if driver_key else 0.0
        bin_noise = rng_t.normal(0, 18, size=len(bin_targets))  # BIN 노이즈 일괄(601회 개별 호출 회피)
        target_vals = {t: float(500 + dep + bin_noise[i]) for i, t in enumerate(bin_targets)}
        target_vals.update({t: float(rng_t.normal(50, 30)) for t in other_targets})

        # 3) row 생성
        for si, fab in enumerate(fab_steps):
            fab_tko = wafer_start + pd.Timedelta(hours=6 * si)
            eds_tko = wafer_start + pd.Timedelta(days=lag) + pd.Timedelta(hours=6 * si)
            observed = eds_tko <= _NOW  # 최근 ~lag일은 미확보(target NaN) → 추정 대상
            row = {
                "wafer_id": wid, "root_lot_id": rlot, "line_id": line, "product": product, "fab_step": fab,
                "fab_track_out_time": fab_tko, "eds_tkout_time": eds_tko, "observed": bool(observed),
            }
            row.update(cat_feat_vals)
            for key in num_keys:
                if key.split("|")[1] == fab:  # 이 fab_step의 feature만 값
                    row[key] = feats[key]
            row.update(target_vals if observed else nan_targets)  # observed-only
            rows.append(row)
    return pd.DataFrame(rows)
