import asyncio
import json

from app.main import app


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
    headers = {
        k.decode("latin1").lower(): v.decode("latin1")
        for m in messages
        if m["type"] == "http.response.start"
        for k, v in m.get("headers", [])
    }
    payload = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    return status, headers, payload


def json_request(method, path, json_body=None):
    status, headers, payload = request(method, path, json_body)
    return status, headers, json.loads(payload.decode("utf-8"))


def test_metadata_and_mock_reset_expose_semiconductor_workbench_context():
    reset_status, _, reset_body = json_request("POST", "/api/mock-data/reset")
    assert reset_status == 200
    assert reset_body["wafer_count"] >= 2000

    status, _, metadata = json_request("GET", "/api/metadata")
    assert status == 200

    assert "metro_ch_hole_cd" in metadata["parameters"]
    assert "BIN_014" in metadata["bin_list"]
    assert metadata["default_bin_groups"][0]["name"] == "Hole-to-Hole"
    assert {"center", "edge", "middle", "ring"}.issubset(set(metadata["zones"]))


def test_analysis_set_bin_group_condition_rule_and_window_review_roundtrip():
    analysis_status, _, analysis_set = json_request(
        "POST",
        "/api/analysis-sets",
        {
            "name": "Ch.Hole CD relaxation check",
            "filters": {
                "product": ["DRAM_A"],
                "layer": ["M1"],
                "step": ["ETCH_CONTACT"],
                "parameter": ["metro_ch_hole_cd"],
                "eds_status": "actual_only",
                "exclude_rework": True,
                "exclude_engineering_lot": True,
                "exclude_abnormal_route": True,
            },
        },
    )
    assert analysis_status == 200
    assert analysis_set["metrics"]["wafer_count"] > 0
    assert analysis_set["metrics"]["eds_actual_coverage"] > 0.8

    group_status, _, bin_group = json_request(
        "POST",
        "/api/bin-groups",
        {
            "name": "Regression Hole-to-Hole",
            "description": "High-side Ch.Hole CD sensitive group",
            "failure_mode": "Hole-to-Hole",
            "bin_ids": ["BIN_014", "BIN_208", "BIN_377"],
            "zone": None,
        },
    )
    assert group_status == 200
    assert bin_group["bin_ids"] == ["BIN_014", "BIN_208", "BIN_377"]

    rule_status, _, condition_rule = json_request(
        "POST",
        "/api/condition-rules",
        {
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
        },
    )
    assert rule_status == 200

    review_status, _, review = json_request(
        "POST",
        "/api/window-review",
        {
            "analysis_set_id": analysis_set["id"],
            "x_parameter": "metro_ch_hole_cd",
            "bin_group_ids": [bin_group["id"]],
            "condition_rule_id": condition_rule["id"],
            "view_options": {"bins": 8},
        },
    )
    assert review_status == 200
    assert review["summary_metrics"]["wafer_count"] > 0
    assert len(review["scatter_data"]) > 0
    assert len(review["binned_response_data"]) > 0
    assert len(review["trend_data"]["actual"]) > 0
    assert len(review["tradeoff_data"]) > 0
    assert len(review["zone_data"]) > 0
    assert len(review["interaction_heatmap_data"]) > 0
    assert review["decision_candidates"]


def test_analysis_condition_library_separates_shared_readonly_and_personal_editable_conditions():
    reset_status, _, _ = json_request("POST", "/api/mock-data/reset")
    assert reset_status == 200

    list_status, _, library = json_request("GET", "/api/analysis-conditions")
    assert list_status == 200
    assert library["shared"]
    assert library["personal"]

    ch_hole = next(item for item in library["shared"] if item["process_key"] == "Ch.Hole" and item["revision"] == "rev1")
    assert ch_hole["scope"] == "shared"
    assert ch_hole["readonly"] is True
    assert ch_hole["fab_filters"]["date_mode"] == "fixed"
    assert ch_hole["analysis_filters"]["eds_status"] == "actual_only"

    shared_update_status, _, shared_update = json_request(
        "PATCH",
        f"/api/analysis-conditions/{ch_hole['id']}",
        {"name": "Should not edit shared condition"},
    )
    assert shared_update_status == 409
    assert "read-only" in shared_update["detail"]

    copy_status, _, personal_copy = json_request(
        "POST",
        f"/api/analysis-conditions/{ch_hole['id']}/copy-personal",
        {"owner": "jimin", "name": "Ch.Hole rev1 최근 30일 quick check"},
    )
    assert copy_status == 200
    assert personal_copy["scope"] == "personal"
    assert personal_copy["readonly"] is False
    assert personal_copy["source_condition_id"] == ch_hole["id"]

    update_status, _, updated = json_request(
        "PATCH",
        f"/api/analysis-conditions/{personal_copy['id']}",
        {
            "fab_filters": {
                "date_mode": "recent_days",
                "recent_days": 30,
                "start_date": None,
                "end_date": None,
            }
        },
    )
    assert update_status == 200
    assert updated["fab_filters"]["date_mode"] == "recent_days"
    assert updated["fab_filters"]["recent_days"] == 30

    create_status, _, analysis_set = json_request(
        "POST",
        f"/api/analysis-conditions/{updated['id']}/analysis-set",
    )
    assert create_status == 200
    assert analysis_set["filters"]["eds_status"] == "actual_only"
    assert analysis_set["metrics"]["eds_pending_count"] == 0


def test_exclusion_prediction_and_exports_are_available():
    _, _, analysis_set = json_request(
        "POST",
        "/api/analysis-sets",
        {
            "name": "Pending risk check",
            "filters": {
                "product": ["DRAM_A"],
                "layer": ["M1"],
                "step": ["ETCH_CONTACT"],
                "parameter": ["metro_ch_hole_cd"],
                "eds_status": "include_pending",
            },
        },
    )
    _, _, groups = json_request("GET", "/api/bin-groups")
    default_group = groups[0]
    _, _, condition_rules = json_request("GET", "/api/condition-rules")
    condition_rule = condition_rules[0]

    _, _, review = json_request(
        "POST",
        "/api/window-review",
        {
            "analysis_set_id": analysis_set["id"],
            "x_parameter": "metro_ch_hole_cd",
            "bin_group_ids": [default_group["id"]],
            "condition_rule_id": condition_rule["id"],
            "view_options": {"bins": 6},
        },
    )
    wafer_ids = [point["wafer_id"] for point in review["scatter_data"][:3]]

    exclusion_status, _, exclusion = json_request(
        "POST",
        "/api/exclusion-rules",
        {
            "name": "Other process noise candidates",
            "analysis_set_id": analysis_set["id"],
            "wafer_ids": wafer_ids,
            "reason": "Abnormal downstream signature",
        },
    )
    assert exclusion_status == 200
    assert exclusion["excluded_count"] == len(wafer_ids)

    prediction_status, _, prediction = json_request(
        "POST",
        "/api/pending-prediction",
        {
            "analysis_set_id": analysis_set["id"],
            "x_parameters": ["metro_ch_hole_cd", "metro_thickness", "metro_uniformity"],
            "bin_group_ids": [default_group["id"]],
            "condition_rule_id": condition_rule["id"],
            "model_type": "ridge",
        },
    )
    assert prediction_status == 200
    assert len(prediction["pending_predictions"]) > 0
    assert prediction["model_performance"]["mae"] >= 0
    assert prediction["model_performance"]["prediction_interval_coverage"] > 0

    csv_status, csv_headers, csv_payload = request("GET", f"/api/export/analysis-set/{analysis_set['id']}")
    assert csv_status == 200
    assert "text/csv" in csv_headers["content-type"]
    assert "wafer_id" in csv_payload.decode("utf-8")

    report_status, _, report = json_request("GET", f"/api/export/report/{review['analysis_run_id']}")
    assert report_status == 200
    assert report["analysis_run_id"] == review["analysis_run_id"]
