from __future__ import annotations

from app.data.mock_store import store
from app.models.schemas import ExclusionRuleCreate
from app.services.mock_data_service import ensure_mock_data


def create_exclusion_rule(payload: ExclusionRuleCreate) -> dict:
    ensure_mock_data()
    rule_id = store.next_id("exclusion_rule", "EX")
    item = {
        "id": rule_id,
        "name": payload.name,
        "analysis_set_id": payload.analysis_set_id,
        "wafer_ids": payload.wafer_ids,
        "reason": payload.reason,
        "excluded_count": len(payload.wafer_ids),
    }
    store.exclusion_rules[rule_id] = item
    return item


def list_exclusion_rules() -> list[dict]:
    ensure_mock_data()
    return list(store.exclusion_rules.values())


def get_exclusion_rule(rule_id: str | None) -> dict | None:
    ensure_mock_data()
    if not rule_id:
        return None
    return store.exclusion_rules.get(rule_id)
