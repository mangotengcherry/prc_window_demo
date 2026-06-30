from fastapi import APIRouter

from app.models.schemas import AnalysisConditionCopy, AnalysisConditionUpdate
from app.services.analysis_condition_service import (
    copy_to_personal,
    create_analysis_set_from_condition,
    list_analysis_conditions,
    update_analysis_condition,
)

router = APIRouter()


@router.get("/api/analysis-conditions")
def get_analysis_conditions():
    return list_analysis_conditions()


@router.post("/api/analysis-conditions/{condition_id}/copy-personal")
def post_copy_personal(condition_id: str, payload: AnalysisConditionCopy):
    return copy_to_personal(condition_id, payload)


@router.patch("/api/analysis-conditions/{condition_id}")
def patch_analysis_condition(condition_id: str, payload: AnalysisConditionUpdate):
    return update_analysis_condition(condition_id, payload)


@router.post("/api/analysis-conditions/{condition_id}/analysis-set")
def post_condition_analysis_set(condition_id: str):
    return create_analysis_set_from_condition(condition_id)
