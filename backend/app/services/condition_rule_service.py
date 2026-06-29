from __future__ import annotations

from typing import Any

import pandas as pd

from app.data.mock_store import store
from app.models.schemas import ConditionRuleCreate
from app.services.mock_data_service import ensure_mock_data


def create_condition_rule(payload: ConditionRuleCreate) -> dict[str, Any]:
    ensure_mock_data()
    rule_id = store.next_id("condition_rule", "CR")
    item = {"id": rule_id, **payload.model_dump()}
    store.condition_rules[rule_id] = item
    return item


def list_condition_rules() -> list[dict[str, Any]]:
    ensure_mock_data()
    return list(store.condition_rules.values())


def get_condition_rule(rule_id: str | None) -> dict[str, Any] | None:
    ensure_mock_data()
    if not rule_id:
        return None
    return store.condition_rules.get(rule_id)


def legend_for(row: pd.Series, rule: dict[str, Any] | None) -> str:
    if not rule:
        return "All wafers"
    basis = rule.get("legend_basis", "")
    if basis == "Part modification":
        for manual in rule.get("manual_rules", []):
            if row["tool_id"] == manual["tool_id"] and row["chamber_id"] == manual["chamber_id"]:
                applied = pd.Timestamp(manual["applied_from"])
                return manual["label_after"] if row["process_date"] >= applied else manual["label_before"]
        return "Modification applied" if row["part_modification_flag"] else "No modification rule"
    if basis == "ECO":
        return str(row["eco_number"])
    if basis == "PPID":
        return str(row["ppid"])
    if basis == "Tool":
        return str(row["tool_id"])
    if basis == "Chamber":
        return f"{row['tool_id']}/{row['chamber_id']}"
    if basis == "Recipe":
        return str(row["recipe_version"])
    if basis == "PM age":
        if row["pm_age"] < 60:
            return "PM age <60"
        if row["pm_age"] < 120:
            return "PM age 60-119"
        return "PM age >=120"
    return "All wafers"
