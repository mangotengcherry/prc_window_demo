"""요청/응답 계약 (M0 — 회사 계약 §7과 동형).

분석 레이어(7-1)·시간기준·추정 슬롯을 포함하되, M0에서 채우지 않는 값은 Optional로 둔다.
"""
from typing import Dict, List, Optional

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


class Selection(BaseModel):
    """linked brushing — 선택 wafer로만 재집계 (window·table)."""
    time_range: Optional[List[str]] = None  # [start_iso, end_iso], fab_track_out_time 기준
    wafer_ids: Optional[List[str]] = None


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
    selection: Optional[Selection] = None


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


# 분석 레이어 계약 — 명시적 서브모델(이전 Dict[str, Any] → 타입·docstring drift 방지, /docs 노출)
class ControlLimits(BaseModel):
    ucl: float
    lcl: float
    sigma: float            # 관리한계 산출 σ — 단기(군내 I-MR) 우선
    sigma_overall: float    # 전체(long-term) σ — 참고
    method: str             # "within(I-MR)" | "overall"


class FitSummary(BaseModel):
    slope: float
    intercept: float
    r2: Optional[float] = None
    n: int
    extrap: float = 0.0     # 추정 X가 관측 범위 밖 비율


class Forecast(BaseModel):
    oos: int                # 추정 y가 관리한계 초과한 미확보 wafer 수
    n: int
    ucl: float
    lcl: float
    shift: float            # 추정 평균이 관측 평균 대비 σ 이동
    mean_pred: float
    r2: Optional[float] = None
    extrap: float = 0.0
    low_conf: bool          # 저R²/외삽 → 참고용 강등


class Drift(BaseModel):
    shift: float            # 최근(마지막 20%) 평균이 기준 대비 단기 σ 이동
    direction: str
    flagged: bool


class TimePoint(BaseModel):
    time: str
    value: float
    value_status: str  # observed | estimated
    observed_time: Optional[str] = None
    wid: Optional[str] = None    # wafer_id (점 = wafer 1매, 툴팁용)
    rlot: Optional[str] = None   # root_lot_id


class TargetSeries(BaseModel):
    name: str
    display_name: str
    unit: str = ""
    category_feature_value: Optional[str] = None
    observed_points: List[TimePoint]
    estimated_points: List[TimePoint] = []
    fit_summary: Optional[FitSummary] = None
    avg: Optional[float] = None
    control_limits: Optional[ControlLimits] = None


class FeatureSeries(BaseModel):
    name: str
    display_name: str
    unit: str = ""
    category_feature_value: Optional[str] = None
    points: list  # [[iso, value], ...]
    point_ids: list = []  # [[root_lot_id, wafer_id], ...] points와 동일 순서 (툴팁용)
    avg: Optional[float] = None
    control_limits: Optional[ControlLimits] = None
    drift: Optional[Drift] = None  # 추세 감지


class EstimateSeries(BaseModel):
    """조합(x_feature × y_target × 분할값)별 추정 y. 미관측 wafer를 y~x 선형회귀로 추정."""
    x_feature: str
    y_target: str
    category_feature_value: Optional[str] = None
    points: list  # [[iso, value], ...] — 미관측 wafer의 추정 y
    point_ids: list = []  # [[root_lot_id, wafer_id], ...] points와 동일 순서 (툴팁용)
    fit_summary: Optional[FitSummary] = None
    forecast: Optional[Forecast] = None     # 관리한계 초과 예측 수 + 신뢰가드


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
    selection: Optional[Selection] = None
    cpk_subgroup: Optional[str] = None  # Cpk within σ 부분군 컬럼(EQP/EQP_CH/root_lot 등). None=time I-MR


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
    x_std_within: Optional[float] = None  # 군내(within-subgroup) σ → Cpk
    x_within_method: Optional[str] = None # within σ 산출 부분군(EQP/EQP_CH/lot) 또는 "time(I-MR)"
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


# ---------- /api/drivers ----------  (인사이트 2: 영향 요인 랭킹)
class DriversRequest(BaseModel):
    line_id: str
    product: str
    category: str
    eds_step: str
    date_range: DateRange
    target_date_range: Optional[DateRange] = None
    fab_step: str
    y_targets: List[str]
    y_target_groups: List[TargetGroup] = []


class DriverItem(BaseModel):
    feature: str
    display_name: str
    corr: float      # 부호 포함 상관
    abs: float       # |corr| (정렬 기준)
    n: int
    p_value: Optional[float] = None   # 상관 유의성(양측)
    q_value: Optional[float] = None   # BH FDR 보정 — q<0.1이면 다중비교 후에도 유의


class TargetDrivers(BaseModel):
    target: str
    drivers: List[DriverItem]


class DriversResponse(BaseModel):
    targets: List[TargetDrivers]


# ---------- /api/interaction ----------
# binning/aggregation/range/outlier 제외는 프론트가 scatter_points로 즉시 계산.
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
    y_target_groups: List[TargetGroup] = []  # value_field가 grouped target일 수 있음


class ScatterPoint(BaseModel):
    x: float
    y: float
    value: Optional[float] = None
    wid: Optional[str] = None    # wafer_id (점 = wafer 1매, 툴팁용)
    rlot: Optional[str] = None   # root_lot_id
    t: Optional[str] = None      # fab_track_out_time(iso)


class InteractionResponse(BaseModel):
    x_feature: str
    y_feature: str
    value_field: str
    sampled: bool = False
    n_total: int = 0
    scatter_points: List[ScatterPoint]
