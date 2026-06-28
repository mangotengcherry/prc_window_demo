from __future__ import annotations

import io

from fastapi.responses import JSONResponse, StreamingResponse

from app.data.mock_store import store
from app.services.analysis_set_service import frame_for_analysis_set, get_analysis_set
from app.services.mock_data_service import ensure_mock_data


def analysis_set_csv(analysis_set_id: str) -> StreamingResponse:
    ensure_mock_data()
    frame = frame_for_analysis_set(analysis_set_id)
    buffer = io.StringIO()
    export_cols = [
        "lot_id",
        "wafer_id",
        "product",
        "layer",
        "step",
        "process_date",
        "expected_eds_date",
        "eds_status",
        "tool_id",
        "chamber_id",
        "ppid",
        "eco_number",
        "recipe_version",
        "pm_age",
        "part_modification_flag",
        "zone",
        "metro_ch_hole_cd",
        "metro_thickness",
        "metro_uniformity",
        "fdc_temp_mean",
        "fdc_pressure_mean",
        "fdc_flow_mean",
        "fdc_rf_power_mean",
        "yield",
        "BIN_014",
        "BIN_208",
        "BIN_377",
        "BIN_031",
        "BIN_122",
        "BIN_450",
    ]
    frame[export_cols].to_csv(buffer, index=False)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="analysis_set_{analysis_set_id}.csv"'},
    )


def report_json(analysis_run_id: str) -> JSONResponse:
    ensure_mock_data()
    run = store.analysis_runs[analysis_run_id]
    analysis_set = get_analysis_set(run["analysis_set"]["id"])
    summary = run["summary_metrics"]
    text = (
        f"현재 synthetic Analysis Set '{analysis_set['name']}' 기준으로 {run['context']['x_parameter']}와 "
        f"{run['context']['bin_groups'][0]['name']}의 Window 관계를 검토했습니다. "
        f"Correlation은 {summary['correlation']}, high-side fail rate는 {summary['high_side_fail_rate']}이며, "
        f"safe-window 후보 범위는 {summary['safe_window']}입니다. "
        "이는 자동 판정이 아니라 검토 후보이며, condition split, Exclusion Rule 전/후 비교, EDS 완료 후 재검증이 필요합니다."
    )
    return JSONResponse(
        {
            "analysis_run_id": analysis_run_id,
            "analysis_set_id": analysis_set["id"],
            "summary_text": text,
            "summary_metrics": summary,
            "decision_candidates": run["decision_candidates"],
            "synthetic_data_notice": run["synthetic_data_notice"],
        }
    )
