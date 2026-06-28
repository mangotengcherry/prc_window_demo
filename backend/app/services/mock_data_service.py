from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd

from app.core.config import settings
from app.data.mock_store import store


PRODUCTS = ["DRAM_A", "DRAM_B", "NAND_C"]
LAYERS = ["M1", "M2", "CONTACT"]
STEPS = ["ETCH_CONTACT", "CLEAN_POST_ETCH", "CMP_OXIDE"]
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
        step = str(rng.choice(STEPS, p=[0.60, 0.24, 0.16]))
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

    default_groups = _default_bin_groups()
    default_rules = _default_condition_rules()
    store.wafer_data = df
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
