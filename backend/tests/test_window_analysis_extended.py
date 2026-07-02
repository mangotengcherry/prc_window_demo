import asyncio
import json

import numpy as np
import pandas as pd

from app.main import app
from app.services import window_analysis_service as was


def request(method, path, json_body=None):
    body = b"" if json_body is None else json.dumps(json_body).encode("utf-8")
    messages = []

    async def run_app():
        sent_request = False
        response_done = asyncio.Event()

        async def receive():
            nonlocal sent_request
            if not sent_request:
                sent_request = True
                return {"type": "http.request", "body": body, "more_body": False}
            await response_done.wait()
            return {"type": "http.disconnect"}

        async def send(message):
            messages.append(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                response_done.set()

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("utf-8"),
            "query_string": b"",
            "headers": [(b"content-type", b"application/json")],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        }
        await app(scope, receive, send)

    asyncio.run(run_app())

    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    payload = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    return status, json.loads(payload.decode("utf-8"))


def json_request(method, path, json_body=None):
    return request(method, path, json_body)


# ---------------------------------------------------------------------------
# safe_window_occupancy / recent_trend
# ---------------------------------------------------------------------------

def test_safe_window_occupancy_fraction_inside_bounds():
    df = pd.DataFrame({"x": list(range(1, 11))})
    occupancy = was._safe_window_occupancy(df, "x", {"lower": 3, "upper": 7})
    assert occupancy == 0.5


def test_safe_window_occupancy_none_when_bounds_missing():
    df = pd.DataFrame({"x": list(range(1, 11))})
    assert was._safe_window_occupancy(df, "x", {"lower": None, "upper": None}) is None


def test_recent_trend_delta_between_two_30day_windows():
    dates = pd.date_range("2026-01-01", periods=60, freq="D")
    y = [0.02] * 30 + [0.05] * 30
    df = pd.DataFrame({"process_date": dates, "y": y})
    result = was._recent_trend(df, "y")
    assert result == {"recent_30d_fail": 0.05, "prior_30d_fail": 0.02, "delta": 0.03}


def test_recent_trend_none_when_actual_empty():
    df = pd.DataFrame({"process_date": pd.Series(dtype="datetime64[ns]"), "y": pd.Series(dtype="float64")})
    assert was._recent_trend(df, "y") is None


# ---------------------------------------------------------------------------
# SPC
# ---------------------------------------------------------------------------

def test_spc_null_when_fewer_than_20_daily_points():
    rows = [{"date": f"2026-01-{i + 1:02d}", "actual_fail_rate": 0.03} for i in range(19)]
    assert was._spc(rows) is None


def test_spc_detects_beyond_3sigma_and_run_of_7():
    base = [0.030, 0.029, 0.031, 0.028, 0.032, 0.029, 0.031, 0.030, 0.028, 0.032, 0.029, 0.031, 0.030]
    run = [0.034, 0.035, 0.034, 0.036, 0.035, 0.034, 0.036]
    outlier_block = [0.030, 0.500]
    values = base + run + outlier_block
    rows = [{"date": f"2026-01-{i + 1:02d}", "actual_fail_rate": v} for i, v in enumerate(values)]
    result = was._spc(rows)
    assert result is not None
    assert set(result.keys()) == {"center", "ucl", "lcl", "sigma", "violations"}
    types = {violation["type"] for violation in result["violations"]}
    assert "beyond_3sigma" in types
    assert "run_of_7" in types
    outlier_violation = next(v for v in result["violations"] if v["type"] == "beyond_3sigma")
    assert outlier_violation["date"] == "2026-01-22"


# ---------------------------------------------------------------------------
# Pareto
# ---------------------------------------------------------------------------

def test_pareto_ranks_desc_and_marks_selected_group():
    df = pd.DataFrame({"BIN_001": [0.01] * 5, "BIN_002": [0.05] * 5, "BIN_003": [0.0] * 5})
    rows = was._pareto(df, ["BIN_001", "BIN_002", "BIN_003"], {"BIN_002"})
    assert [row["bin_id"] for row in rows] == ["BIN_002", "BIN_001", "BIN_003"]
    assert rows[0]["in_selected_group"] is True
    assert rows[1]["in_selected_group"] is False
    assert rows[0]["loss_contribution"] == 0.8333
    assert rows[-1]["cum_pct"] == 1.0


def test_pareto_caps_at_top_30():
    many = pd.DataFrame({f"BIN_{i:03d}": [0.001 * i] * 5 for i in range(1, 36)})
    rows = was._pareto(many, [f"BIN_{i:03d}" for i in range(1, 36)], set())
    assert len(rows) == 30


def test_pareto_empty_when_no_actual_rows():
    df = pd.DataFrame({"BIN_001": pd.Series(dtype="float64")})
    assert was._pareto(df, ["BIN_001"], set()) == []


# ---------------------------------------------------------------------------
# Driver ranking
# ---------------------------------------------------------------------------

def test_driver_ranking_excludes_n_below_30_and_self():
    rng = np.random.default_rng(0)
    n = 40
    y = rng.normal(0, 1, n)
    param_strong = y * 2 + rng.normal(0, 0.1, n)
    param_weak_lown = np.concatenate([rng.normal(0, 1, 15), [np.nan] * 25])
    df = pd.DataFrame({"param_strong": param_strong, "param_weak_lown": param_weak_lown, "y": y})

    rows = was._driver_ranking(df, "y", ["param_strong", "param_weak_lown", "y"])

    parameters = [row["parameter"] for row in rows]
    assert "param_strong" in parameters
    assert "param_weak_lown" not in parameters  # n=15 < 30
    assert "y" not in parameters  # self excluded
    strong = next(row for row in rows if row["parameter"] == "param_strong")
    assert strong["n"] == 40
    assert strong["corr"] > 0.9
    assert strong["abs_corr"] == abs(strong["corr"])


# ---------------------------------------------------------------------------
# Commonality
# ---------------------------------------------------------------------------

def test_commonality_ranks_significant_factor():
    df = pd.DataFrame(
        {
            "factor": ["A"] * 10 + ["B"] * 10 + ["C"] * 3,  # C has n=3 < 5, dropped
            "y": list(np.linspace(0.01, 0.02, 10)) + list(np.linspace(0.05, 0.06, 10)) + [0.9, 0.91, 0.92],
        }
    )
    rows = was._commonality(df, "y", ["factor"])
    assert len(rows) == 1
    row = rows[0]
    assert row["factor"] == "factor"
    assert row["group_count"] == 2
    assert {g["value"] for g in row["groups"]} == {"A", "B"}
    assert row["p_value"] < 0.05
    assert row["effect_size"] is not None
    assert row["worst_group"] == "B"


def test_commonality_skips_factor_with_fewer_than_2_groups_after_filter():
    df = pd.DataFrame(
        {
            "factor": ["A"] * 10 + ["B"] * 3,  # B has n=3 < 5, dropped -> only 1 group left
            "y": list(np.linspace(0.01, 0.02, 10)) + [0.9, 0.91, 0.92],
        }
    )
    assert was._commonality(df, "y", ["factor"]) == []


def test_commonality_degrades_to_empty_list_when_scipy_missing(monkeypatch):
    monkeypatch.setattr(was, "scipy_stats", None)
    df = pd.DataFrame({"factor": ["A"] * 10 + ["B"] * 10, "y": list(range(20))})
    assert was._commonality(df, "y", ["factor"]) == []


# ---------------------------------------------------------------------------
# End-to-end wiring through /api/window-review
# ---------------------------------------------------------------------------

def test_window_review_response_includes_new_phase5_fields():
    _, analysis_set = json_request(
        "POST",
        "/api/analysis-sets",
        {
            "name": "Phase5 extended fields check",
            "filters": {
                "product": ["KCAI"],
                "layer": ["M1"],
                "step": ["CR860200"],
                "parameter": ["metro_ch_hole_cd"],
                "eds_status": "actual_only",
            },
        },
    )
    _, groups = json_request("GET", "/api/bin-groups")
    default_group = groups[0]
    _, condition_rules = json_request("GET", "/api/condition-rules")
    condition_rule = condition_rules[0]

    status, review = json_request(
        "POST",
        "/api/window-review",
        {
            "analysis_set_id": analysis_set["id"],
            "x_parameter": "metro_ch_hole_cd",
            "bin_group_ids": [default_group["id"]],
            "condition_rule_id": condition_rule["id"],
            "view_options": {"bins": 8, "interaction_x": "metro_ch_hole_cd", "interaction_y": "fdc_pressure_mean"},
        },
    )
    assert status == 200

    # existing fields still present (backward compatibility)
    assert review["scatter_data"]
    assert review["binned_response_data"]
    assert review["trend_data"]["actual"]

    # new fields
    assert "safe_window_occupancy" in review["summary_metrics"]
    assert "recent_trend" in review["summary_metrics"]
    assert "spc" in review["trend_data"]
    assert isinstance(review["pareto_data"], list)
    assert len(review["pareto_data"]) <= 30
    assert isinstance(review["driver_ranking"], list)
    for driver in review["driver_ranking"]:
        assert driver["n"] >= 30
    assert isinstance(review["commonality_data"], list)
    for row in review["commonality_data"]:
        assert set(row.keys()) == {"factor", "p_value", "effect_size", "group_count", "worst_group", "groups"}

    interaction_parameters = {(row["x_parameter"], row["y_parameter"]) for row in review["interaction_heatmap_data"]}
    assert interaction_parameters == {("metro_ch_hole_cd", "fdc_pressure_mean")}


def test_window_review_y_axis_metric_yield_switches_scatter_y():
    _, analysis_set = json_request(
        "POST",
        "/api/analysis-sets",
        {
            "name": "Phase5 y_axis_metric check",
            "filters": {
                "product": ["KCAI"],
                "layer": ["M1"],
                "step": ["CR860200"],
                "parameter": ["metro_ch_hole_cd"],
                "eds_status": "actual_only",
            },
        },
    )
    _, groups = json_request("GET", "/api/bin-groups")
    default_group = groups[0]

    _, review = json_request(
        "POST",
        "/api/window-review",
        {
            "analysis_set_id": analysis_set["id"],
            "x_parameter": "metro_ch_hole_cd",
            "bin_group_ids": [default_group["id"]],
            "view_options": {"bins": 8, "y_axis_metric": "yield"},
        },
    )
    point = review["scatter_data"][0]
    assert point["selected_bin_group_fail_rate"] == point["eds_yield"]
