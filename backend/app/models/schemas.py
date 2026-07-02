from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AnalysisSetFilters(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    product: list[str] = Field(default_factory=list)
    layer: list[str] = Field(default_factory=list)
    step: list[str] = Field(default_factory=list)
    parameter: list[str] = Field(default_factory=list)
    tool: list[str] = Field(default_factory=list)
    chamber: list[str] = Field(default_factory=list)
    ppid: list[str] = Field(default_factory=list)
    eco: list[str] = Field(default_factory=list)
    pm_age_min: float | None = None
    pm_age_max: float | None = None
    eds_status: Literal["actual_only", "include_pending"] = "actual_only"
    exclude_rework: bool = True
    exclude_engineering_lot: bool = True
    exclude_abnormal_route: bool = True


class AnalysisSetCreate(BaseModel):
    name: str
    filters: AnalysisSetFilters


class BinGroupCreate(BaseModel):
    name: str
    description: str = ""
    failure_mode: str = ""
    bin_ids: list[str]
    zone: str | None = None
    tradeoff_pair_id: str | None = None


class ManualModificationRule(BaseModel):
    tool_id: str
    chamber_id: str
    applied_from: str
    label_before: str = "Before modification"
    label_after: str = "After modification"


class ConditionRuleCreate(BaseModel):
    name: str
    legend_basis: str = "Part modification"
    manual_rules: list[ManualModificationRule] = Field(default_factory=list)


class WindowReviewRequest(BaseModel):
    analysis_set_id: str
    x_parameter: str
    y_metric: str | None = None
    bin_group_ids: list[str] = Field(default_factory=list)
    condition_rule_id: str | None = None
    exclusion_rule_id: str | None = None
    view_options: dict[str, Any] = Field(default_factory=dict)


class ExclusionRuleCreate(BaseModel):
    name: str
    analysis_set_id: str
    wafer_ids: list[str]
    reason: str


class ExpressionValidateRequest(BaseModel):
    expression: str
    mode: Literal["filter", "column"] = "filter"
    context: Literal["fab", "eds"] = "fab"


class PendingPredictionRequest(BaseModel):
    analysis_set_id: str
    x_parameters: list[str]
    bin_group_ids: list[str]
    condition_rule_id: str | None = None
    model_type: Literal["linear", "ridge", "huber", "polynomial2"] = "ridge"
