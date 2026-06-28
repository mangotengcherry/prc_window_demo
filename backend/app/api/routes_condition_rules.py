from fastapi import APIRouter

from app.models.schemas import ConditionRuleCreate
from app.services.condition_rule_service import create_condition_rule, list_condition_rules

router = APIRouter()


@router.post("/api/condition-rules")
def post_condition_rule(payload: ConditionRuleCreate):
    return create_condition_rule(payload)


@router.get("/api/condition-rules")
def get_condition_rules():
    return list_condition_rules()
