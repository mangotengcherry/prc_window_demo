"""주고받는 데이터의 '모양'(계약서). pydantic 모델."""
from typing import List, Optional

from pydantic import BaseModel


# ---- 요청 ----
class BinnedRequest(BaseModel):
    fab_step: str
    x_features: List[str]
    y_targets: List[str]
    bins: int = 10


class TimeseriesRequest(BaseModel):
    fab_step: str
    x_features: List[str]
    y_targets: List[str]


class TableRequest(BaseModel):
    fab_step: str
    x_features: List[str]
    y_targets: List[str]


# ---- 응답 ----
class ColumnsResponse(BaseModel):
    features: List[str]
    targets: List[str]
    fab_steps: List[str]
    dc_spec: dict  # { feature: { lower, upper } }


class Bin(BaseModel):
    bin_left: float
    bin_right: float
    bin_center: float
    y_avg: Optional[float]
    wafer_count: int


class Combo(BaseModel):
    x_feature: str
    y_target: str
    bins: List[Bin]


class BinnedResponse(BaseModel):
    fab_step: str
    combos: List[Combo]


class Series(BaseModel):
    name: str
    points: list  # [[iso_time, value], ...]


class TimeseriesResponse(BaseModel):
    fab_step: str
    targets: List[Series]
    features: List[Series]


class TableRow(BaseModel):
    fab_step: str
    x_feature: str
    x_value: float
    y_target: str
    y_value: float
    dc_lower: Optional[float]
    dc_upper: Optional[float]


class TableResponse(BaseModel):
    rows: List[TableRow]
