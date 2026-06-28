from fastapi import APIRouter

from app.models.schemas import ExclusionRuleCreate
from app.services.exclusion_service import create_exclusion_rule, list_exclusion_rules

router = APIRouter()


@router.post("/api/exclusion-rules")
def post_exclusion_rule(payload: ExclusionRuleCreate):
    return create_exclusion_rule(payload)


@router.get("/api/exclusion-rules")
def get_exclusion_rules():
    return list_exclusion_rules()
