"""요청/응답 계약 (M0 — 회사 계약 §7과 동형).

분석 레이어(7-1)·시간기준·추정 슬롯을 포함하되, M0에서 채우지 않는 값은 Optional로 둔다.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ---------- 공통 ----------
class DateRange(BaseModel):
    start_date: str
    end_date: str
    time_column: str = "fab_track_out_time"


class CategoryFeatureSel(BaseModel):
    name: Optional[str] = None
    values: List[str] = []
    chart_mode: str = "multi_line"  # multi_line | split


class TargetGroup(BaseModel):
    """인라인(stateless) grouped target — 원본 target들을 합산한 합성 target.
    정의는 요청에 동봉(E4), 보유는 클라이언트(localStorage). y_targets에 name으로 참조."""
    name: str
    sources: List[str]
    agg: str = "sum"  # 현재 sum만 지원


# ---------- /api/columns ----------
class ColumnsResponse(BaseModel):
    line_ids: List[str]
    products: List[str]
    categories: List[str]
    eds_steps: List[str]
    targets: List[str]
    targets_by_category: Dict[str, List[str]]
    fab_steps: List[str]
    metro_grades: List[str]
    metro_categories: List[str]
    category_features: List[str]
    category_feature_values: Dict[str, List[str]]
    dc_spec: Dict[str, Dict[str, float]]
    units: Dict[str, str]
    min_n: int
    max_combos: int
    date_default: Dict[str, str]         # fab_track_out_time 범위 기반
    target_date_default: Dict[str, str]  # eds_tkout_time(observed) 범위 기반


# ---------- /api/x-feature-options ----------
class XFeature(BaseModel):
    name: str
    display_name: str
    data_type: str
    metro_step: str
    metro_item: str
    subitem: str
    metro_grade: str
    metro_category: str
    matched_fab_steps: List[str]
    unit: str = ""
    score: Optional[float] = None


class XFeatureOptionsResponse(BaseModel):
    matching: bool
    fab_step: Optional[str]
    features: List[XFeature]


# ---------- /api/binned ----------
class BinnedRequest(BaseModel):
    line_id: str
    product: str
    category: str
    eds_step: str
    date_range: DateRange                       # fab_track_out_time 기준
    target_date_range: Optional[DateRange] = None  # eds_tkout_time 기준 (y target 확보 시점)
    fab_step: str
    x_features: List[str]
    y_targets: List[str]
    bins: int = 10
    y_target_groups: List[TargetGroup] = []
    category_feature: Optional[CategoryFeatureSel] = None


class Bin(BaseModel):
    bin_left: float
    bin_right: float
    bin_center: float
    y_avg: Optional[float]
    wafer_count: int
    # 분석 레이어 (7-1)
    y_std: Optional[float] = None
    y_sem: Optional[float] = None
    n_observed: Optional[int] = None


class Combo(BaseModel):
    x_feature: str
    x_feature_display_name: str
    y_target: str
    category: str
    eds_step: str
    category_feature_name: Optional[str] = None
    category_feature_value: Optional[str] = None
    bins: List[Bin]


class BinnedResponse(BaseModel):
    fab_step: str
    combos: List[Combo]
    truncated: bool = False  # max_combos 초과 시


# ---------- /api/timeseries ----------
class TimeseriesRequest(BaseModel):
    line_id: str
    product: str
    category: str
    eds_step: str
    date_range: DateRange
    target_date_range: Optional[DateRange] = None
    fab_step: str
    x_features: List[str]
    y_targets: List[str]
    y_target_groups: List[TargetGroup] = []
    category_feature: Optional[CategoryFeatureSel] = None


class TimeBasis(BaseModel):
    x_axis: str
    target_observed_time: str
    expected_target_lag_days: int


class TimePoint(BaseModel):
    time: str
    value: float
    value_status: str  # observed | estimated
    observed_time: Optional[str] = None


class TargetSeries(BaseModel):
    name: str
    display_name: str
    unit: str = ""
    category_feature_value: Optional[str] = None
    observed_points: List[TimePoint]
    estimated_points: List[TimePoint] = []
    fit_summary: Optional[Dict[str, Any]] = None
    avg: Optional[float] = None
    control_limits: Optional[Dict[str, float]] = None


class FeatureSeries(BaseModel):
    name: str
    display_name: str
    unit: str = ""
    category_feature_value: Optional[str] = None
    points: list  # [[iso, value], ...]
    avg: Optional[float] = None
    control_limits: Optional[Dict[str, float]] = None


class EstimateSeries(BaseModel):
    """조합(x_feature × y_target × 분할값)별 추정 y. 미관측 wafer를 y~x 선형회귀로 추정."""
    x_feature: str
    y_target: str
    category_feature_value: Optional[str] = None
    points: list  # [[iso, value], ...] — 미관측 wafer의 추정 y
    fit_summary: Optional[Dict[str, Any]] = None  # {slope, intercept, r2, n}


class TimeseriesResponse(BaseModel):
    fab_step: str
    time_basis: TimeBasis
    sampled: bool = False
    n_total: Optional[int] = None
    targets: List[TargetSeries]
    features: List[FeatureSeries]
    estimates: List[EstimateSeries] = []


# ---------- /api/table ----------
class TableRequest(BaseModel):
    line_id: str
    product: str
    category: str
    eds_step: str
    date_range: DateRange
    target_date_range: Optional[DateRange] = None
    fab_step: str
    x_features: List[str]
    y_targets: List[str]
    y_target_groups: List[TargetGroup] = []
    category_feature: Optional[CategoryFeatureSel] = None


class TableRow(BaseModel):
    line_id: str
    product: str
    category: str
    eds_step: str
    fab_step: str
    x_feature: str
    x_feature_display_name: str
    x_value: Optional[float]
    x_std: Optional[float] = None         # 전체(long-term) σ → Ppk
    x_std_within: Optional[float] = None  # 단기(short-term) σ → Cpk
    y_target: str
    y_value: Optional[float]
    value_status: str = "observed"
    metro_step: str = ""
    metro_item: str = ""
    metro_grade: str = ""
    metro_category: str = ""
    category_feature_name: Optional[str] = None
    category_feature_value: Optional[str] = None
    dc_lower: Optional[float] = None
    dc_upper: Optional[float] = None
    # 분석 레이어
    n: Optional[int] = None
    mean: Optional[float] = None
    std: Optional[float] = None


class TableResponse(BaseModel):
    rows: List[TableRow]


# ---------- /api/interaction ----------
class InteractionRequest(BaseModel):
    line_id: str
    product: str
    category: str
    eds_step: str
    date_range: DateRange
    target_date_range: Optional[DateRange] = None
    fab_step: str
    x_feature: str
    y_feature: str
    value_field: str                  # 집계 대상 컬럼. "__count__" = wafer 수
    aggregation: str = "average"      # average | median
    x_bins: int = 10
    y_bins: int = 10
    x_range: Optional[List[float]] = None
    y_range: Optional[List[float]] = None
    y_target_groups: List[TargetGroup] = []  # value_field가 grouped target일 수 있음


class ScatterPoint(BaseModel):
    x: float
    y: float
    value: Optional[float] = None


class HeatmapCell(BaseModel):
    x_bin: int
    y_bin: int
    x_bin_label: str
    y_bin_label: str
    value: Optional[float]
    count: int


class RankRow(BaseModel):
    rank: int
    x_bin_label: str
    y_bin_label: str
    aggregation: Optional[float]
    count: int


class InteractionResponse(BaseModel):
    x_feature: str
    y_feature: str
    value_field: str
    aggregation: str
    sampled: bool = False
    n_total: int = 0
    scatter_points: List[ScatterPoint]
    heatmap_cells: List[HeatmapCell]
    rank_rows: List[RankRow]
