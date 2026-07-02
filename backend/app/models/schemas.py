from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


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


# ---------------------------------------------------------------------------
# 조건 라이브러리(Preset) criteria — Analysis Set 선정(Phase 3)과 공유하는 단일 소스
# ---------------------------------------------------------------------------


class DateRange(BaseModel):
    start: str | None = None
    end: str | None = None


class FabStepCondition(BaseModel):
    fab_step: str
    date_range: DateRange = DateRange()
    filter_expression: str = ""


class FabCriteria(BaseModel):
    products: list[str] = Field(default_factory=list)
    step_conditions: list[FabStepCondition] = Field(default_factory=list)
    primary_step: str | None = None
    exclude_rework: bool = True
    exclude_engineering_lot: bool = True
    exclude_abnormal_route: bool = True

    @field_validator("step_conditions")
    @classmethod
    def _validate_step_conditions(cls, value: list[FabStepCondition]) -> list[FabStepCondition]:
        if len(value) > 3:
            raise ValueError("공정 조건은 최대 3개까지 설정할 수 있습니다")
        steps = [condition.fab_step for condition in value]
        if len(steps) != len(set(steps)):
            raise ValueError("공정 조건에 중복된 공정이 있습니다")
        return value


class EdsCriteria(BaseModel):
    eds_step: Literal["M", "P", "ML", "PL"] = "M"
    eds_category: Literal["BIN", "MSR"] = "BIN"
    eds_items: list[str] = Field(default_factory=list)
    date_range: DateRange = DateRange()
    part_id: Literal["All", "A", "B", "C"] = "All"
    filter_expression: str = ""


class ComputedColumn(BaseModel):
    name: str
    expression: str


class ChartState(BaseModel):
    x_axis: Literal["fab_time", "eds_time"] = "fab_time"
    legend_by: str | None = None
    adhoc_filters: list[str] = Field(default_factory=list)
    computed_columns: list[ComputedColumn] = Field(default_factory=list)


class PresetCriteria(BaseModel):
    fab: FabCriteria
    eds: EdsCriteria | None = None
    chart: ChartState | None = None


# ---------------------------------------------------------------------------
# Preset 폴더/Revision/공유 (Phase 2)
# ---------------------------------------------------------------------------


class PresetFolderCreate(BaseModel):
    name: str


class PresetFolderUpdate(BaseModel):
    name: str


class PresetCreate(BaseModel):
    folder_id: str
    name: str
    scope: Literal["personal", "shared"] = "personal"
    note: str = ""
    criteria: PresetCriteria


class PresetRevisionCreate(BaseModel):
    note: str = ""
    criteria: PresetCriteria


class PresetPatch(BaseModel):
    scope: Literal["personal", "shared"] | None = None
    name: str | None = None


class PresetDuplicate(BaseModel):
    folder_id: str | None = None
    name: str


class CustomEdsItemTerm(BaseModel):
    item: str
    sign: Literal[1, -1]


class CustomEdsItemCreate(BaseModel):
    name: str = Field(pattern=r"^[A-Za-z0-9_]{2,30}$")
    category: Literal["BIN", "MSR"]
    terms: list[CustomEdsItemTerm]

    @field_validator("terms")
    @classmethod
    def _validate_terms(cls, value: list[CustomEdsItemTerm]) -> list[CustomEdsItemTerm]:
        if len(value) < 2:
            raise ValueError("커스텀 아이템은 2개 이상의 아이템으로 구성해야 합니다")
        return value
