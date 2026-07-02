from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd

from app.core.config import settings
from app.data.mock_store import store


PRODUCTS = ["KCAI", "PPCR", "QSGB"]
LAYERS = ["M1", "M2", "CONTACT"]
STEPS = ["CR860200", "CR860400", "WL560300", "CR380020", "WL240100"]
STEP_PROBS = [0.60, 0.16, 0.16, 0.05, 0.03]
PROCESS_MODULES = {
    "Ch.Hole": [
        {"step_id": "CR380020", "label": "Ch.Hole Mask"},
        {"step_id": "CR860200", "label": "Ch.Hole ETCH"},
        {"step_id": "CR860400", "label": "Ch.Hole Clean"},
    ],
    "WLCUT": [
        {"step_id": "WL240100", "label": "WLCUT Mask"},
        {"step_id": "WL560300", "label": "WLCUT ETCH"},
    ],
}
STEP_ORDER = ["CR380020", "CR860200", "CR860400", "WL240100", "WL560300"]
STEP_MODULE = {step["step_id"]: module for module, steps in PROCESS_MODULES.items() for step in steps}
TOOLS = ["T01", "T02", "T03", "T04", "T05", "T06"]
CHAMBERS = ["C1", "C2", "C3", "C4"]
PPIDS = ["PPID_A", "PPID_B", "PPID_C"]
ECOS = ["ECO_26_011", "ECO_26_017", "ECO_26_023"]
RECIPES = ["RCP_1.0", "RCP_1.1", "RCP_2.0"]
ZONES = ["center", "middle", "ring", "edge"]
PARAMETERS = [
    "metro_ch_hole_cd",
    "metro_thickness",
    "metro_uniformity",
    "fdc_temp_mean",
    "fdc_pressure_mean",
    "fdc_flow_mean",
    "fdc_rf_power_mean",
]
H2H_BINS = ["BIN_014", "BIN_208", "BIN_377"]
NOT_OPEN_BINS = ["BIN_031", "BIN_122", "BIN_450"]
EDGE_BINS = ["BIN_066", "BIN_188", "BIN_501"]
CENTER_BINS = ["BIN_072", "BIN_155", "BIN_410"]


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-x))


def _bin_name(index: int) -> str:
    return f"BIN_{index:03d}"


def part_value(v: float, wafer_id: str, item: str, part: str) -> float:
    """Deterministic per-part offset for an EDS value (§4.2)."""
    if part == "All":
        return v
    rng = np.random.default_rng(abs(hash((wafer_id, item, part))) % 2**32)
    shift = {"A": -0.05, "B": 0.0, "C": 0.05}[part]
    return v * (1.0 + shift) + rng.normal(0, 0.02 * max(abs(v), 1e-9))


def step_value(v: float, wafer_id: str, item: str, step: str) -> float:
    """Deterministic per eds_step offset for an EDS value (§4.2)."""
    if step == "M":
        return v
    rng = np.random.default_rng(abs(hash((wafer_id, item, step))) % 2**32)
    factor = 0.92 if step == "P" else 1.03  # ML/PL
    return v * factor + rng.normal(0, 0.02 * max(abs(v), 1e-9))


def _zscore(series: pd.Series) -> pd.Series:
    std = series.std(ddof=0)
    return (series - series.mean()) / (std if std else 1.0)


def _add_eds_test_times(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    n = len(df)
    actual_mask = (df["eds_status"] == "actual").to_numpy()

    eds_test_time_m = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    eds_test_time_m.loc[actual_mask] = df.loc[actual_mask, "expected_eds_date"] + pd.to_timedelta(
        rng.uniform(0, 2, int(actual_mask.sum())), unit="D"
    )

    p_eligible = actual_mask & (rng.random(n) < 0.70)
    eds_test_time_p = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    eds_test_time_p.loc[p_eligible] = eds_test_time_m.loc[p_eligible] + pd.to_timedelta(
        rng.uniform(3, 6, int(p_eligible.sum())), unit="D"
    )

    kcai_actual = actual_mask & (df["product"] == "KCAI").to_numpy()
    ml_pl_eligible = kcai_actual & (rng.random(n) < 0.40)
    eds_test_time_ml = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    eds_test_time_pl = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    eds_test_time_ml.loc[ml_pl_eligible] = eds_test_time_m.loc[ml_pl_eligible] + pd.Timedelta(days=1)
    eds_test_time_pl.loc[ml_pl_eligible] = eds_test_time_p.loc[ml_pl_eligible] + pd.Timedelta(days=1)

    df["eds_test_time_m"] = eds_test_time_m
    df["eds_test_time_p"] = eds_test_time_p
    df["eds_test_time_ml"] = eds_test_time_ml
    df["eds_test_time_pl"] = eds_test_time_pl
    return df


def _add_msr_columns(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    n = len(df)
    correlated_specs = [
        ("MSR_001", "metro_ch_hole_cd", 0.65, 120.0, 15.0),
        ("MSR_002", "metro_thickness", 0.55, 80.0, 10.0),
        ("MSR_003", "metro_uniformity", 0.60, 45.0, 6.0),
        ("MSR_004", "fdc_temp_mean", 0.50, 200.0, 25.0),
        ("MSR_005", "fdc_pressure_mean", 0.45, 60.0, 8.0),
        ("MSR_006", "fdc_rf_power_mean", 0.58, 300.0, 40.0),
    ]
    for name, source, weight, base, scale in correlated_specs:
        z = _zscore(df[source])
        df[name] = base + scale * (weight * z + rng.normal(0, 0.4, n))

    for i in range(7, 41):
        name = f"MSR_{i:03d}"
        source = PARAMETERS[i % len(PARAMETERS)]
        z = _zscore(df[source])
        df[name] = 100.0 + 12.0 * (0.15 * z + rng.normal(0, 1.0, n))
    return df


def _build_fab_history(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for lot_id, lot_df in df.groupby("lot_id", sort=False):
        rep_step = str(lot_df["step"].iloc[0])
        rep_index = STEP_ORDER.index(rep_step)
        product = str(lot_df["product"].iloc[0])

        lot_step_refs = [
            {
                "tool_id": str(rng.choice(TOOLS)),
                "chamber_id": str(rng.choice(CHAMBERS)),
                "ppid": str(rng.choice(PPIDS, p=[0.55, 0.32, 0.13])),
                "eco_number": str(rng.choice(ECOS, p=[0.45, 0.36, 0.19])),
                "recipe_version": str(rng.choice(RECIPES, p=[0.50, 0.32, 0.18])),
            }
            for _ in STEP_ORDER
        ]

        for _, wafer in lot_df.iterrows():
            offsets = np.cumsum(rng.uniform(1, 3, len(STEP_ORDER)))
            anchor = offsets[rep_index]
            for step_index, step_id in enumerate(STEP_ORDER):
                track_out_time = wafer["process_date"] + pd.Timedelta(days=float(offsets[step_index] - anchor))
                if step_index == rep_index:
                    tool_id = wafer["tool_id"]
                    chamber_id = wafer["chamber_id"]
                    ppid = wafer["ppid"]
                    eco_number = wafer["eco_number"]
                    recipe_version = wafer["recipe_version"]
                    pm_age = wafer["pm_age"]
                    part_modification_flag = wafer["part_modification_flag"]
                else:
                    if rng.random() < 0.80:
                        ref = lot_step_refs[step_index]
                        tool_id = ref["tool_id"]
                        chamber_id = ref["chamber_id"]
                        ppid = ref["ppid"]
                        eco_number = ref["eco_number"]
                        recipe_version = ref["recipe_version"]
                    else:
                        tool_id = str(rng.choice(TOOLS))
                        chamber_id = str(rng.choice(CHAMBERS))
                        ppid = str(rng.choice(PPIDS, p=[0.55, 0.32, 0.13]))
                        eco_number = str(rng.choice(ECOS, p=[0.45, 0.36, 0.19]))
                        recipe_version = str(rng.choice(RECIPES, p=[0.50, 0.32, 0.18]))
                    pm_age = round(float(np.clip(rng.gamma(3.4, 22), 1, 220)), 2)
                    part_modification_flag = bool(
                        tool_id == "T01" and chamber_id == "C2" and track_out_time.date() >= date(2026, 3, 15)
                    )

                rows.append(
                    {
                        "wafer_id": wafer["wafer_id"],
                        "lot_id": lot_id,
                        "product": product,
                        "step_id": step_id,
                        "module": STEP_MODULE[step_id],
                        "track_out_time": track_out_time,
                        "tool_id": tool_id,
                        "chamber_id": chamber_id,
                        "ppid": ppid,
                        "eco_number": eco_number,
                        "recipe_version": recipe_version,
                        "pm_age": pm_age,
                        "part_modification_flag": part_modification_flag,
                    }
                )

    return pd.DataFrame(rows)


def _default_bin_groups() -> list[dict[str, Any]]:
    return [
        {
            "id": "BG001",
            "name": "Hole-to-Hole",
            "description": "High-side Ch.Hole CD sensitive bridge-like failure mode.",
            "failure_mode": "Hole-to-Hole",
            "bin_ids": H2H_BINS,
            "zone": None,
            "tradeoff_pair_id": "BG002",
        },
        {
            "id": "BG002",
            "name": "Ch.Hole Not Open",
            "description": "Low-side Ch.Hole CD sensitive open failure mode.",
            "failure_mode": "Ch.Hole Not Open",
            "bin_ids": NOT_OPEN_BINS,
            "zone": None,
            "tradeoff_pair_id": "BG001",
        },
        {
            "id": "BG003",
            "name": "Edge Hole-to-Hole",
            "description": "Edge-zone sensitive Hole-to-Hole group.",
            "failure_mode": "Hole-to-Hole",
            "bin_ids": H2H_BINS + EDGE_BINS,
            "zone": "edge",
            "tradeoff_pair_id": "BG004",
        },
        {
            "id": "BG004",
            "name": "Center Not Open",
            "description": "Center-zone sensitive Not Open group.",
            "failure_mode": "Ch.Hole Not Open",
            "bin_ids": NOT_OPEN_BINS + CENTER_BINS,
            "zone": "center",
            "tradeoff_pair_id": "BG003",
        },
    ]


def _default_condition_rules() -> list[dict[str, Any]]:
    return [
        {
            "id": "CR001",
            "name": "T01 C2 modification split",
            "legend_basis": "Part modification",
            "manual_rules": [
                {
                    "tool_id": "T01",
                    "chamber_id": "C2",
                    "applied_from": "2026-03-15",
                    "label_before": "Before modification",
                    "label_after": "After modification",
                }
            ],
        }
    ]


def reset_mock_data(seed: int | None = None) -> dict[str, Any]:
    rng = np.random.default_rng(settings.random_seed if seed is None else seed)
    start = date(2026, 1, 3)
    rows: list[dict[str, Any]] = []
    wafer_seq = 0

    for lot_index in range(settings.lot_count):
        lot_id = f"L{lot_index + 1:04d}"
        lot_date = start + timedelta(days=int(rng.integers(0, 150)))
        product = str(rng.choice(PRODUCTS, p=[0.46, 0.34, 0.20]))
        layer = str(rng.choice(LAYERS, p=[0.48, 0.30, 0.22]))
        step = str(rng.choice(STEPS, p=STEP_PROBS))
        tool = str(rng.choice(TOOLS))
        chamber = str(rng.choice(CHAMBERS))
        ppid = str(rng.choice(PPIDS, p=[0.55, 0.32, 0.13]))
        eco = str(rng.choice(ECOS, p=[0.45, 0.36, 0.19]))
        recipe = str(rng.choice(RECIPES, p=[0.50, 0.32, 0.18]))
        lot_shift = float(rng.normal(0, 0.24))
        wafers = int(rng.integers(settings.min_wafers, settings.max_wafers + 1))

        for wafer_in_lot in range(wafers):
            wafer_seq += 1
            process_date = lot_date + timedelta(days=int(rng.integers(0, 4)))
            expected_eds_date = process_date + timedelta(days=int(rng.integers(5, 16)))
            zone = str(rng.choice(ZONES, p=[0.26, 0.32, 0.21, 0.21]))
            pm_age = float(np.clip(rng.gamma(3.4, 22), 1, 220))

            modified = tool == "T01" and chamber == "C2" and process_date >= date(2026, 3, 15)
            eco_shift = 0.52 if eco == "ECO_26_017" and process_date >= date(2026, 2, 18) else 0.0
            ppid_shift = 0.34 if ppid == "PPID_B" else 0.0
            chamber_tail = max(0.0, rng.normal(0.72, 0.38)) if tool == "T03" and chamber == "C4" else 0.0
            mod_shift = -0.34 if modified else 0.0
            mod_sigma = 0.42 if modified else 0.72

            cd = 52.0 + lot_shift + eco_shift + ppid_shift + chamber_tail + mod_shift + rng.normal(0, mod_sigma)
            thickness = 100.0 + 0.38 * (cd - 52) + rng.normal(0, 2.4)
            uniformity = 1.52 + 0.09 * abs(cd - 52) + (0.18 if zone == "edge" else 0.0) + rng.normal(0, 0.16)
            temp = 405 + 1.9 * (cd - 52) + rng.normal(0, 5.2)
            pressure = 55 - 0.75 * (cd - 52) + rng.normal(0, 2.4)
            flow = 120 + 1.25 * (thickness - 100) + rng.normal(0, 5.8)
            rf_power = 860 + 12.0 * (cd - 52) + rng.normal(0, 28)

            h2h = 0.002 + 0.044 * _sigmoid(np.array([(cd - 53.2) * 2.0]))[0]
            not_open = 0.002 + 0.043 * _sigmoid(np.array([(50.9 - cd) * 2.15]))[0]
            if zone == "edge":
                h2h += 0.010 + max(0, cd - 52.8) * 0.007
            if zone == "center":
                not_open += 0.006 + max(0, 51.2 - cd) * 0.007
            if modified:
                h2h *= 0.76
                not_open *= 0.82

            other_noise = float(np.clip(rng.normal(0.004, 0.002), 0, 0.018))
            outlier = rng.random() < 0.025
            if outlier:
                h2h += float(rng.uniform(0.02, 0.06))
                not_open += float(rng.uniform(0.01, 0.04))
            h2h = float(np.clip(h2h, 0, 0.20))
            not_open = float(np.clip(not_open, 0, 0.20))
            yield_value = float(np.clip(0.985 - h2h - not_open - other_noise + rng.normal(0, 0.004), 0.72, 0.998))
            eds_status = "pending" if expected_eds_date > date(2026, 5, 24) or rng.random() < 0.13 else "actual"

            rows.append(
                {
                    "lot_id": lot_id,
                    "wafer_id": f"W{wafer_seq:05d}",
                    "wafer_in_lot": wafer_in_lot + 1,
                    "product": product,
                    "layer": layer,
                    "step": step,
                    "process_date": pd.Timestamp(process_date),
                    "expected_eds_date": pd.Timestamp(expected_eds_date),
                    "eds_status": eds_status,
                    "tool_id": tool,
                    "chamber_id": chamber,
                    "ppid": ppid,
                    "eco_number": eco,
                    "recipe_version": recipe,
                    "pm_age": round(pm_age, 2),
                    "part_modification_flag": bool(modified),
                    "zone": zone,
                    "metro_ch_hole_cd": round(float(cd), 4),
                    "metro_thickness": round(float(thickness), 4),
                    "metro_uniformity": round(float(uniformity), 4),
                    "fdc_temp_mean": round(float(temp), 4),
                    "fdc_pressure_mean": round(float(pressure), 4),
                    "fdc_flow_mean": round(float(flow), 4),
                    "fdc_rf_power_mean": round(float(rf_power), 4),
                    "yield": round(yield_value, 5),
                    "is_rework": bool(rng.random() < 0.045),
                    "is_engineering_lot": bool(rng.random() < 0.035),
                    "is_abnormal_route": bool(rng.random() < 0.025 or outlier),
                    "synthetic_note": "synthetic/mock only",
                    "_h2h_true": h2h,
                    "_not_open_true": not_open,
                }
            )

    df = pd.DataFrame(rows)
    bin_names = [_bin_name(i) for i in range(1, settings.bin_count + 1)]
    sparse = rng.beta(0.35, 55, size=(len(df), settings.bin_count)) * 0.010
    bin_df = pd.DataFrame(sparse, columns=bin_names)

    h2h_weights = np.array([0.45, 0.33, 0.22])
    not_open_weights = np.array([0.40, 0.36, 0.24])
    edge_weights = np.array([0.44, 0.31, 0.25])
    center_weights = np.array([0.38, 0.34, 0.28])
    h2h_values = df["_h2h_true"].to_numpy()
    not_open_values = df["_not_open_true"].to_numpy()

    for name, weight in zip(H2H_BINS, h2h_weights, strict=False):
        bin_df[name] = np.clip(h2h_values * weight + rng.normal(0, 0.0008, len(df)), 0, 1)
    for name, weight in zip(NOT_OPEN_BINS, not_open_weights, strict=False):
        bin_df[name] = np.clip(not_open_values * weight + rng.normal(0, 0.0008, len(df)), 0, 1)

    edge_mask = (df["zone"] == "edge").to_numpy()
    center_mask = (df["zone"] == "center").to_numpy()
    for name, weight in zip(EDGE_BINS, edge_weights, strict=False):
        bin_df[name] = np.where(edge_mask, np.clip(h2h_values * weight * 0.55, 0, 1), bin_df[name])
    for name, weight in zip(CENTER_BINS, center_weights, strict=False):
        bin_df[name] = np.where(center_mask, np.clip(not_open_values * weight * 0.52, 0, 1), bin_df[name])

    meaningful_bins = set(H2H_BINS + NOT_OPEN_BINS + EDGE_BINS + CENTER_BINS)
    extra_pattern_bins = [name for name in bin_names if name not in meaningful_bins][:22]
    for idx, name in enumerate(extra_pattern_bins):
        driver = h2h_values if idx % 2 == 0 else not_open_values
        sensitivity = 0.10 + 0.03 * (idx % 4)
        bin_df[name] = np.clip(driver * sensitivity + rng.beta(0.7, 80, len(df)) * 0.01, 0, 1)

    df = pd.concat([df.drop(columns=["_h2h_true", "_not_open_true"]), bin_df], axis=1)
    df = _add_eds_test_times(df, rng)
    df = _add_msr_columns(df, rng)
    fab_history = _build_fab_history(df, rng)
    msr_names = [f"MSR_{i:03d}" for i in range(1, 41)]

    default_groups = _default_bin_groups()
    default_rules = _default_condition_rules()
    store.wafer_data = df
    store.fab_history = fab_history
    store.metadata = {
        "products": PRODUCTS,
        "layers": LAYERS,
        "steps": STEPS,
        "tools": TOOLS,
        "chambers": CHAMBERS,
        "ppids": PPIDS,
        "ecos": ECOS,
        "recipes": RECIPES,
        "zones": ZONES,
        "parameters": PARAMETERS,
        "bin_list": bin_names,
        "default_bin_groups": default_groups,
        "process_modules": [{"name": module, "fab_steps": steps} for module, steps in PROCESS_MODULES.items()],
        "eds_steps": ["M", "P", "ML", "PL"],
        "eds_categories": ["BIN", "MSR"],
        "eds_items": {"BIN": bin_names, "MSR": msr_names},
        "part_ids": ["All", "A", "B", "C"],
        "categorical_columns": [
            "product",
            "step",
            "lot_id",
            "tool_id",
            "chamber_id",
            "ppid",
            "eco_number",
            "recipe_version",
            "zone",
            "part_modification_flag",
            "eds_status",
            "is_rework",
        ],
        "numeric_columns": [
            "metro_ch_hole_cd",
            "metro_thickness",
            "metro_uniformity",
            "fdc_temp_mean",
            "fdc_pressure_mean",
            "fdc_flow_mean",
            "fdc_rf_power_mean",
            "pm_age",
            "yield",
        ],
        "date_range": {
            "start_date": df["process_date"].min().strftime("%Y-%m-%d"),
            "end_date": df["process_date"].max().strftime("%Y-%m-%d"),
        },
        "synthetic_data_notice": "All wafer, FAB, FDC, and EDS BIN data are synthetic mock data.",
    }
    store.analysis_sets.clear()
    store.bin_groups = {group["id"]: group for group in default_groups}
    store.condition_rules = {rule["id"]: rule for rule in default_rules}
    store.exclusion_rules.clear()
    store.analysis_runs.clear()
    store.counters = {
        "analysis_set": 0,
        "bin_group": len(default_groups),
        "condition_rule": len(default_rules),
        "exclusion_rule": 0,
        "analysis_run": 0,
    }
    return {"lot_count": int(df["lot_id"].nunique()), "wafer_count": int(len(df)), "bin_count": settings.bin_count}


def ensure_mock_data() -> None:
    if store.wafer_data.empty:
        reset_mock_data()


def metadata() -> dict[str, Any]:
    ensure_mock_data()
    return store.metadata
