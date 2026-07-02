import asyncio
import json

import pandas as pd
import pytest

from app.main import app
from app.services.expression_service import (
    ExpressionError,
    columns_used,
    evaluate_column,
    evaluate_filter,
    parse,
)


def _sample_df():
    return pd.DataFrame(
        {
            "ppid": ["PPID_A", "PPID_B", "TT_TEST", "PPID_A"],
            "metro_ch_hole_cd": [52.0, 53.5, 50.0, 51.0],
            "metro_thickness": [100.0, 102.0, 90.0, 97.0],
        }
    )


def test_bare_identifier_raises_bracket_error():
    df = _sample_df()
    with pytest.raises(ExpressionError) as exc_info:
        evaluate_filter("PPID != 'TT_TEST'", df)
    assert "대괄호" in exc_info.value.message


def test_sql_style_not_equal_operator_raises_error():
    df = _sample_df()
    with pytest.raises(ExpressionError):
        evaluate_filter("[PPID] <> 'TT_TEST'", df)


def test_and_or_precedence_parentheses_not_in_is_null():
    df = pd.DataFrame(
        {
            "ppid": ["PPID_A", "PPID_B", "PPID_C", "PPID_A"],
            "zone": ["edge", "center", "edge", None],
        }
    )
    # AND binds tighter than OR
    result = evaluate_filter("[zone] = 'edge' AND [ppid] = 'PPID_A' OR [ppid] = 'PPID_C'", df)
    assert list(result) == [True, False, True, False]

    result_paren = evaluate_filter("[zone] = 'edge' AND ([ppid] = 'PPID_A' OR [ppid] = 'PPID_C')", df)
    assert list(result_paren) == [True, False, True, False]

    result_not = evaluate_filter("NOT ([zone] = 'edge')", df)
    assert list(result_not) == [False, True, False, True]

    result_in = evaluate_filter("[ppid] IN ('PPID_A', 'PPID_C')", df)
    assert list(result_in) == [True, False, True, True]

    result_not_in = evaluate_filter("[ppid] NOT IN ('PPID_A', 'PPID_C')", df)
    assert list(result_not_in) == [False, True, False, False]

    result_null = evaluate_filter("[zone] IS NULL", df)
    assert list(result_null) == [False, False, False, True]

    result_not_null = evaluate_filter("[zone] IS NOT NULL", df)
    assert list(result_not_null) == [True, True, True, False]


def test_case_when_produces_object_series():
    df = pd.DataFrame({"metro_ch_hole_cd": [55.0, 52.0, 50.0]})
    result = evaluate_column(
        "case when [metro_ch_hole_cd] >= 53 then 'high' "
        "when [metro_ch_hole_cd] <= 51 then 'low' else 'mid' end",
        df,
    )
    assert pd.api.types.is_string_dtype(result)
    assert list(result) == ["high", "mid", "low"]


def test_arithmetic_expression():
    df = pd.DataFrame({"metro_thickness": [200.0, 180.0], "metro_ch_hole_cd": [100.0, 100.0]})
    result = evaluate_filter("[metro_thickness] / [metro_ch_hole_cd] > 1.9", df)
    assert list(result) == [True, False]


def test_unknown_column_reports_close_match_suggestion():
    df = _sample_df()
    with pytest.raises(ExpressionError) as exc_info:
        evaluate_filter("[PPIDX] = 'PPID_A'", df)
    assert "ppid" in exc_info.value.message


def test_unclosed_parenthesis_raises_error():
    df = _sample_df()
    with pytest.raises(ExpressionError):
        evaluate_filter("([ppid] = 'PPID_A'", df)


def test_non_bool_result_in_filter_mode_raises_error():
    df = _sample_df()
    with pytest.raises(ExpressionError):
        evaluate_filter("[metro_ch_hole_cd]", df)


def test_empty_expression_raises_error():
    with pytest.raises(ExpressionError):
        parse("")


def test_type_mismatch_between_string_and_numeric_raises_error():
    df = _sample_df()
    with pytest.raises(ExpressionError):
        evaluate_filter("[metro_ch_hole_cd] = 'high'", df)


def test_columns_used_extracts_raw_names():
    assert columns_used("[PPID] != \"TT_TEST\" AND [zone] = 'edge'") == ["PPID", "zone"]


# ---------------------------------------------------------------------------
# POST /api/expressions/validate
# ---------------------------------------------------------------------------


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


def test_validate_endpoint_reports_valid_expression_with_resolved_columns():
    status, body = request(
        "POST",
        "/api/expressions/validate",
        {"expression": '[PPID] != "TT_TEST"', "mode": "filter", "context": "fab"},
    )
    assert status == 200
    assert body["valid"] is True
    assert body["columns_used"] == ["ppid"]
    assert body["result_dtype"] == "bool"


def test_validate_endpoint_reports_unknown_column_with_suggestion():
    status, body = request(
        "POST",
        "/api/expressions/validate",
        {"expression": '[PPIDX] != "TT_TEST"', "mode": "filter", "context": "fab"},
    )
    assert status == 200
    assert body["valid"] is False
    assert "ppid" in body["error"]
    assert body["position"] == 0


def test_validate_endpoint_supports_column_mode_in_eds_context():
    status, body = request(
        "POST",
        "/api/expressions/validate",
        {
            "expression": "case when [metro_ch_hole_cd] >= 53 then 'high' else 'low' end",
            "mode": "column",
            "context": "eds",
        },
    )
    assert status == 200
    assert body["valid"] is True
    assert body["result_dtype"] in ("object", "str")
