"""예제 wafer 데이터 (long-format).

각 wafer는 여러 fab_step을 거치며, step마다 feature 값과 trackout_time이 다릅니다.
한 행(row) = (wafer_id, fab_step) 한 쌍.

target(yield, thickness)은 feature 기준값에서 멀어질수록 커지는 'U-shape' 관계로 구성
(=window 차트의 y_avg 선이 양끝에서 올라감).
"""
from functools import lru_cache

import numpy as np
import pandas as pd

FEATURE_COLUMNS = ["etch_time", "temp", "pressure", "gas_flow"]
TARGET_COLUMNS = ["yield", "thickness"]
FAB_STEPS = ["ETCH_01", "ETCH_02", "CVD_01", "PVD_01"]

# step별 feature 기준값(mean)
_STEP_FEATURE_MEAN = {
    "ETCH_01": {"etch_time": 13.0, "temp": 250, "pressure": 120, "gas_flow": 45},
    "ETCH_02": {"etch_time": 14.5, "temp": 255, "pressure": 118, "gas_flow": 48},
    "CVD_01": {"etch_time": 11.5, "temp": 245, "pressure": 125, "gas_flow": 42},
    "PVD_01": {"etch_time": 12.5, "temp": 248, "pressure": 122, "gas_flow": 50},
}
_FEATURE_SD = {"etch_time": 1.5, "temp": 8, "pressure": 10, "gas_flow": 5}

# feature별로 관리 중인 DC spec (device-control 한계). 실제론 설정/DB에서 관리.
DC_SPEC = {
    "etch_time": {"lower": 9.0, "upper": 17.0},
    "temp": {"lower": 230.0, "upper": 270.0},
    "pressure": {"lower": 100.0, "upper": 140.0},
    "gas_flow": {"lower": 35.0, "upper": 55.0},
}


@lru_cache(maxsize=1)
def load_dataframe() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    n_wafers = 300
    rows = []

    for w in range(n_wafers):
        wid = f"W{w:05d}"
        wafer_start = pd.Timestamp("2026-01-01") + pd.Timedelta(hours=w)
        for si, step in enumerate(FAB_STEPS):
            m = _STEP_FEATURE_MEAN[step]
            feats = {f: rng.normal(m[f], _FEATURE_SD[f]) for f in FEATURE_COLUMNS}

            # 표준화 편차의 제곱합 → 기준값에서 멀수록 커짐 (U-shape의 근원)
            z2 = sum(((feats[f] - m[f]) / _FEATURE_SD[f]) ** 2 for f in FEATURE_COLUMNS)
            yld = 0.60 + 0.020 * z2 + rng.normal(0, 0.015)
            thickness = 485 + 2.0 * z2 + rng.normal(0, 6)

            rows.append({
                "wafer_id": wid,
                "fab_step": step,
                "trackout_time": wafer_start + pd.Timedelta(hours=6 * si),
                **feats,
                "yield": float(np.clip(yld, 0, 1)),
                "thickness": thickness,
            })

    return pd.DataFrame(rows)
