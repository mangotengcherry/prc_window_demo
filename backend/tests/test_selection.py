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
    payload = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    body_json = json.loads(payload.decode("utf-8")) if payload else None
    return status, body_json


def json_request(method, path, json_body=None):
    return request(method, path, json_body)


def _fab(step_conditions, products=None):
    return {
        "products": products if products is not None else ["KCAI"],
        "step_conditions": step_conditions,
        "primary_step": step_conditions[0]["fab_step"] if step_conditions else None,
    }


def _step(fab_step, start=None, end=None, filter_expression=""):
    return {
        "fab_step": fab_step,
        "date_range": {"start": start, "end": end},
        "filter_expression": filter_expression,
    }


def _eds(items, filter_expression="", eds_step="M", category="BIN"):
    return {
        "eds_step": eds_step,
        "eds_category": category,
        "eds_items": items,
        "date_range": {},
        "part_id": "All",
        "filter_expression": filter_expression,
    }


# ---------------------------------------------------------------------------
# FAB만 / FAB+EDS
# ---------------------------------------------------------------------------


def test_preview_fab_only_returns_summary_without_points():
    status, body = json_request(
        "POST", "/api/selection/preview", {"fab": _fab([_step("CR860200")]), "eds": None}
    )
    assert status == 200
    assert body["points"] == []
    assert body["summary"]["wafer_count"] > 0
    assert len(body["summary"]["fab_step_matches"]) == 1
    assert body["summary"]["fab_step_matches"][0]["fab_step"] == "CR860200"
    assert body["summary"]["fab_step_matches"][0]["matched"] > 0


def test_preview_fab_and_eds_returns_points_and_matched_ratio():
    status, body = json_request(
        "POST",
        "/api/selection/preview",
        {"fab": _fab([_step("CR860200")]), "eds": _eds(["BIN_014"]), "sample_limit": 200},
    )
    assert status == 200
    assert body["summary"]["eds_matched_count"] > 0
    assert 0 < body["summary"]["eds_match_ratio"] <= 1
    assert len(body["points"]) > 0
    point = body["points"][0]
    assert point["meta"]["eds_item"] == "BIN_014"
    assert point["y"] is not None
    assert point["x"] is not None


# ---------------------------------------------------------------------------
# 필터식 포함
# ---------------------------------------------------------------------------


def test_preview_fab_filter_expression_reduces_matched_and_reports_excluded():
    status, without_filter = json_request(
        "POST", "/api/selection/preview", {"fab": _fab([_step("CR860200")]), "eds": None}
    )
    assert status == 200

    status, with_filter = json_request(
        "POST",
        "/api/selection/preview",
        {"fab": _fab([_step("CR860200", filter_expression='[tool_id] == "T01"')]), "eds": None},
    )
    assert status == 200
    assert with_filter["summary"]["wafer_count"] < without_filter["summary"]["wafer_count"]
    assert with_filter["summary"]["excluded_by_fab_filter"] > 0


def test_preview_eds_filter_expression_reduces_matched_and_reports_excluded():
    status, without_filter = json_request(
        "POST",
        "/api/selection/preview",
        {"fab": _fab([_step("CR860200")]), "eds": _eds(["BIN_014"]), "sample_limit": 5000},
    )
    assert status == 200

    status, with_filter = json_request(
        "POST",
        "/api/selection/preview",
        {
            "fab": _fab([_step("CR860200")]),
            "eds": _eds(["BIN_014"], filter_expression="[value] > 0.01"),
            "sample_limit": 5000,
        },
    )
    assert status == 200
    assert with_filter["summary"]["eds_matched_count"] < without_filter["summary"]["eds_matched_count"]
    assert with_filter["summary"]["excluded_by_eds_filter"] > 0


# ---------------------------------------------------------------------------
# computed column을 legend로
# ---------------------------------------------------------------------------


def test_preview_computed_column_used_as_legend():
    status, body = json_request(
        "POST",
        "/api/selection/preview",
        {
            "fab": _fab([_step("CR860200")]),
            "eds": _eds(["BIN_014"]),
            "chart": {
                "legend_by": "cd_band",
                "computed_columns": [
                    {
                        "name": "cd_band",
                        "expression": "case when [metro_ch_hole_cd] >= 52 then 'high' else 'low' end",
                    }
                ],
            },
            "sample_limit": 500,
        },
    )
    assert status == 200
    assert "cd_band" in body["columns"]["categorical"]
    legends = {p["legend"] for p in body["points"]}
    assert legends <= {"high", "low"}
    assert legends


# ---------------------------------------------------------------------------
# 오류 스테이지 보고
# ---------------------------------------------------------------------------


def test_preview_reports_fab_filter_stage_error():
    status, body = json_request(
        "POST",
        "/api/selection/preview",
        {"fab": _fab([_step("CR860200", filter_expression="[NO_SUCH_COLUMN] == 1")]), "eds": None},
    )
    assert status == 200
    assert body["error"]["stage"] == "fab_filter:CR860200"


def test_preview_reports_eds_filter_stage_error():
    status, body = json_request(
        "POST",
        "/api/selection/preview",
        {
            "fab": _fab([_step("CR860200")]),
            "eds": _eds(["BIN_014"], filter_expression="[NO_SUCH_COLUMN] == 1"),
        },
    )
    assert status == 200
    assert body["error"]["stage"] == "eds_filter"


def test_preview_reports_deleted_custom_item_error_at_eds_items_stage():
    status, body = json_request(
        "POST",
        "/api/selection/preview",
        {"fab": _fab([_step("CR860200")]), "eds": _eds(["GHOST_ITEM_NOT_FOUND"])},
    )
    assert status == 200
    assert body["error"]["stage"] == "eds_items"
    assert "GHOST_ITEM_NOT_FOUND" in body["error"]["message"]


def test_preview_reports_adhoc_filter_stage_error():
    status, body = json_request(
        "POST",
        "/api/selection/preview",
        {
            "fab": _fab([_step("CR860200")]),
            "eds": None,
            "chart": {"adhoc_filters": ["[NO_SUCH_COLUMN] == 1"]},
        },
    )
    assert status == 200
    assert body["error"]["stage"] == "adhoc"


def test_preview_reports_computed_column_stage_error():
    status, body = json_request(
        "POST",
        "/api/selection/preview",
        {
            "fab": _fab([_step("CR860200")]),
            "eds": None,
            "chart": {"computed_columns": [{"name": "bad_col", "expression": "[NO_SUCH_COLUMN] + 1"}]},
        },
    )
    assert status == 200
    assert body["error"]["stage"] == "computed:bad_col"


# ---------------------------------------------------------------------------
# 2개 공정 join -> 물량 감소 + 블록별 매칭 수 보고
# ---------------------------------------------------------------------------


def test_preview_two_step_join_reduces_wafer_count_and_reports_block_matches():
    status, single = json_request(
        "POST", "/api/selection/preview", {"fab": _fab([_step("CR860200")]), "eds": None}
    )
    assert status == 200

    status, joined = json_request(
        "POST",
        "/api/selection/preview",
        {
            "fab": _fab(
                [
                    _step("CR860200"),
                    _step("CR860400", filter_expression='[tool_id] == "T01"'),
                ]
            ),
            "eds": None,
        },
    )
    assert status == 200
    assert joined["summary"]["wafer_count"] < single["summary"]["wafer_count"]
    matches = joined["summary"]["fab_step_matches"]
    assert [m["fab_step"] for m in matches] == ["CR860200", "CR860400"]
    assert all(m["matched"] > 0 for m in matches)


# ---------------------------------------------------------------------------
# 커스텀 아이템 y값 = signed sum
# ---------------------------------------------------------------------------


def test_preview_custom_eds_item_value_matches_signed_sum_of_components():
    from app.services import selection_service

    wafer_ids = ["W00001", "W00002", "W00003"]
    custom = selection_service._item_value_series("H2H_SUM", "BIN", "M", "All", wafer_ids)
    manual = (
        selection_service._derived_value_series("BIN_014", "M", "All", wafer_ids)
        + selection_service._derived_value_series("BIN_208", "M", "All", wafer_ids)
        + selection_service._derived_value_series("BIN_377", "M", "All", wafer_ids)
    )
    assert (custom - manual).abs().max() < 1e-9

    status, body = json_request(
        "POST",
        "/api/selection/preview",
        {"fab": _fab([_step("CR860200")]), "eds": _eds(["H2H_SUM"]), "sample_limit": 5},
    )
    assert status == 200
    assert body["points"]
    assert body["points"][0]["meta"]["eds_item"] == "H2H_SUM"


# ---------------------------------------------------------------------------
# criteria로 만든 Analysis Set이 기존 window-review와 호환
# ---------------------------------------------------------------------------


def test_analysis_set_created_from_criteria_works_with_window_review():
    status, analysis_set = json_request(
        "POST",
        "/api/analysis-sets",
        {
            "name": "criteria based set",
            "criteria": {
                "fab": _fab([_step("CR860200", start="2026-01-01", end="2026-06-19")]),
                "eds": None,
                "chart": None,
            },
        },
    )
    assert status == 200
    assert analysis_set["metrics"]["wafer_count"] > 0

    status, review = json_request(
        "POST",
        "/api/window-review",
        {
            "analysis_set_id": analysis_set["id"],
            "x_parameter": "metro_ch_hole_cd",
            "bin_group_ids": ["BG001"],
            "view_options": {"bins": 6},
        },
    )
    assert status == 200
    assert review["summary_metrics"]["wafer_count"] == analysis_set["metrics"]["wafer_count"]
    assert len(review["scatter_data"]) > 0
