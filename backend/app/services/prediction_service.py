from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import HuberRegressor, LinearRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, PolynomialFeatures, StandardScaler

from app.models.schemas import PendingPredictionRequest
from app.services.analysis_set_service import frame_for_analysis_set
from app.services.bin_group_service import attach_group_metric, get_bin_group
from app.services.condition_rule_service import get_condition_rule, legend_for
from app.services.mock_data_service import ensure_mock_data


BASE_NUMERIC = [
    "metro_ch_hole_cd",
    "metro_thickness",
    "metro_uniformity",
    "fdc_temp_mean",
    "fdc_pressure_mean",
    "fdc_rf_power_mean",
    "pm_age",
]
CATEGORICAL = ["chamber_id", "ppid", "eco_number"]


def _model(model_type: str):
    if model_type == "linear":
        return LinearRegression()
    if model_type == "huber":
        return HuberRegressor(max_iter=300)
    return Ridge(alpha=1.8)


def _features(requested: list[str]) -> list[str]:
    out = []
    for item in [*requested, *BASE_NUMERIC]:
        if item not in out:
            out.append(item)
    return out


def _confidence(width: float, rate: float) -> str:
    if width < max(0.006, rate * 0.35):
        return "High"
    if width < max(0.014, rate * 0.8):
        return "Medium"
    return "Low"


def _risk_kr(value: str) -> str:
    return {"High": "높음", "Medium": "중간", "Low": "낮음"}.get(value, value)


def _confidence_kr(value: str) -> str:
    return {"High": "높음", "Medium": "중간", "Low": "낮음"}.get(value, value)


def compute_pending_prediction(payload: PendingPredictionRequest) -> dict[str, Any]:
    ensure_mock_data()
    frame = frame_for_analysis_set(payload.analysis_set_id)
    group = get_bin_group(payload.bin_group_ids[0] if payload.bin_group_ids else "BG001")
    metric_col = "_selected_metric"
    frame[metric_col] = attach_group_metric(frame, group)
    numeric = [col for col in _features(payload.x_parameters) if col in frame.columns]
    feature_cols = numeric + CATEGORICAL + ["part_modification_flag"]

    actual = frame[frame["eds_status"] == "actual"].dropna(subset=[metric_col]).copy()
    pending = frame[frame["eds_status"] == "pending"].copy()
    if len(actual) < 20 or pending.empty:
        return {
            "pending_predictions": [],
            "trend": {"actual": [], "predicted": []},
            "model_performance": {"mae": 0, "rmse": 0, "bias": 0, "high_risk_hit_rate": 0, "prediction_interval_coverage": 0},
            "backtest": [],
        }

    actual = actual.sort_values("process_date")
    split = max(12, int(len(actual) * 0.78))
    train = actual.iloc[:split]
    test = actual.iloc[split:] if len(actual) > split + 5 else actual.sample(min(80, len(actual)), random_state=12)

    numeric_transformer = Pipeline([("scale", StandardScaler())])
    if payload.model_type == "polynomial2":
        numeric_transformer = Pipeline([("scale", StandardScaler()), ("poly", PolynomialFeatures(degree=2, include_bias=False))])
    transformer = ColumnTransformer(
        [
            ("numeric", numeric_transformer, numeric),
            ("category", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL + ["part_modification_flag"]),
        ]
    )
    model = Pipeline([("prep", transformer), ("regressor", _model(payload.model_type))])
    model.fit(train[feature_cols], train[metric_col])

    test_pred = np.clip(model.predict(test[feature_cols]), 0, 1)
    residual = test[metric_col].to_numpy() - test_pred
    lower_q = float(np.quantile(residual, 0.10))
    upper_q = float(np.quantile(residual, 0.90))
    mae = float(np.mean(np.abs(residual)))
    rmse = float(np.sqrt(np.mean(residual**2)))
    bias = float(np.mean(residual))
    coverage = float(np.mean((test[metric_col].to_numpy() >= test_pred + lower_q) & (test[metric_col].to_numpy() <= test_pred + upper_q)))
    high_threshold = float(train[metric_col].quantile(0.84))
    actual_high = test[metric_col].to_numpy() >= high_threshold
    predicted_high = test_pred >= high_threshold
    hit_rate = float((actual_high & predicted_high).sum() / max(1, actual_high.sum()))

    pending_pred = np.clip(model.predict(pending[feature_cols]), 0, 1)
    rule = get_condition_rule(payload.condition_rule_id)
    prediction_rows = []
    for (_, row), pred in zip(pending.iterrows(), pending_pred, strict=False):
        lower = max(0.0, float(pred + lower_q))
        upper = min(1.0, float(pred + upper_q))
        width = upper - lower
        risk = "High" if pred >= high_threshold else "Medium" if pred >= train[metric_col].quantile(0.65) else "Low"
        confidence = _confidence(width, float(pred))
        prediction_rows.append(
            {
                "lot_id": row["lot_id"],
                "wafer_id": row["wafer_id"],
                "expected_eds_date": row["expected_eds_date"].strftime("%Y-%m-%d"),
                "selected_fab_x_value": round(float(row[payload.x_parameters[0]]), 4) if payload.x_parameters else None,
                "predicted_bin_group_fail_rate": round(float(pred), 5),
                "prediction_lower": round(lower, 5),
                "prediction_upper": round(upper, 5),
                "risk_level": risk,
                "confidence": confidence,
                "chamber": f"{row['tool_id']}/{row['chamber_id']}",
                "ppid": row["ppid"],
                "eco": row["eco_number"],
                "part_modification": bool(row["part_modification_flag"]),
                "legend": legend_for(row, rule),
                "explanation": f"{group['name']} Pending 예측은 risk {_risk_kr(risk)}, confidence {_confidence_kr(confidence)}입니다.",
            }
        )

    actual_trend = (
        actual.assign(day=actual["process_date"].dt.strftime("%Y-%m-%d"))
        .groupby("day", observed=True)[metric_col]
        .mean()
        .reset_index()
        .rename(columns={"day": "date", metric_col: "actual_fail_rate"})
    )
    predicted_frame = pending.copy()
    predicted_frame["_pred"] = pending_pred
    predicted_trend = (
        predicted_frame.assign(day=predicted_frame["expected_eds_date"].dt.strftime("%Y-%m-%d"))
        .groupby("day", observed=True)["_pred"]
        .agg(["mean", "count"])
        .reset_index()
        .rename(columns={"day": "date", "mean": "predicted_fail_rate", "count": "pending_count"})
    )

    backtest = []
    for (_, row), pred in zip(test.iterrows(), test_pred, strict=False):
        backtest.append(
            {
                "wafer_id": row["wafer_id"],
                "actual": round(float(row[metric_col]), 5),
                "predicted": round(float(pred), 5),
                "chamber": f"{row['tool_id']}/{row['chamber_id']}",
                "ppid": row["ppid"],
                "zone": row["zone"],
            }
        )
    return {
        "bin_group": group,
        "pending_predictions": sorted(prediction_rows, key=lambda item: item["predicted_bin_group_fail_rate"], reverse=True)[:300],
        "trend": {
            "actual": actual_trend.round(5).to_dict(orient="records"),
            "predicted": predicted_trend.round(5).to_dict(orient="records"),
            "prediction_interval": {"residual_q10": round(lower_q, 5), "residual_q90": round(upper_q, 5)},
        },
        "model_performance": {
            "mae": round(mae, 5),
            "rmse": round(rmse, 5),
            "bias": round(bias, 5),
            "high_risk_hit_rate": round(hit_rate, 4),
            "prediction_interval_coverage": round(coverage, 4),
        },
        "backtest": backtest[:300],
    }
