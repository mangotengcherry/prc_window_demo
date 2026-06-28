from fastapi import APIRouter

from app.models.schemas import AnalysisSetCreate
from app.services.analysis_set_service import create_analysis_set, get_analysis_set, list_analysis_sets

router = APIRouter()


@router.post("/api/analysis-sets")
def post_analysis_set(payload: AnalysisSetCreate):
    return create_analysis_set(payload)


@router.get("/api/analysis-sets")
def get_analysis_sets():
    return list_analysis_sets()


@router.get("/api/analysis-sets/{analysis_set_id}")
def get_one_analysis_set(analysis_set_id: str):
    return get_analysis_set(analysis_set_id)
