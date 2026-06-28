from fastapi import APIRouter

from app.services.export_service import analysis_set_csv, report_json

router = APIRouter()


@router.get("/api/export/analysis-set/{analysis_set_id}")
def get_analysis_set_export(analysis_set_id: str):
    return analysis_set_csv(analysis_set_id)


@router.get("/api/export/report/{analysis_run_id}")
def get_report_export(analysis_run_id: str):
    return report_json(analysis_run_id)
