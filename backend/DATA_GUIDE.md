# 데이터 교체 가이드 — 회사 데이터 꽂기

> 데모 데이터를 **우리 팀 실데이터로 갈아끼우는** 방법. 분석 로직·API·프론트는 손대지 않고
> **`data_source.py` 한 파일만** 회사 DB/CSV 조회로 바꾸면 된다.

---

## 1. 구조 (왜 한 파일만 바꾸면 되나)

```
data_source.py   ← ★ 여기만 바꾼다 (원천 데이터 + 메타 제공)
      │  provider 함수 8개
      ▼
data.py          ← 계약/파생 레이어 (차원 목록·파생 메타 자동 계산) — 수정 불필요
      │
      ▼
analytics.py     ← 분석 로직 (binning·Cpk·시계열·교호작용·추정·brush) — 수정 불필요
main.py          ← FastAPI 라우팅 — 수정 불필요
```

- `data.py`는 `data_source`가 주는 원천에서 **line/product/fab_step/category 목록, 분할 값, 단위, target 목록**을
  자동으로 파생한다. 즉 차원 목록을 따로 관리할 필요가 없다 — **데이터에 있는 그대로** 잡힌다.
- 그래서 교체 작업 = `data_source.py`의 **provider 함수 8개 본문만** 채우기.

---

## 2. 빠른 시작

0. (최초 1회) 의존성 설치: `pip install -r requirements.txt`
   — pandas·numpy·**scipy**(driver 상관 유의성·FDR) + fastapi·uvicorn 포함.
1. `data_source.py`의 provider 함수들을 회사 데이터 조회로 교체 (아래 §4).
2. 검증: `python validate_data.py` → **✓ 전부 통과** 확인 (스키마·표본·분석 smoke).
3. 실행: `uvicorn main:app --reload`. 프론트 실행·팀원 LAN 공유는 루트 `README.md` 참고.

문제가 있으면 `validate_data.py`가 **무엇이 틀렸는지** 콕 집어준다.

---

## 3. 필수 스키마 (계약)

`data_source.py`가 제공해야 하는 8개:

| provider | 반환 | 설명 |
|---|---|---|
| `fact_table()` | `pd.DataFrame` | **핵심.** wafer×fab_step long 테이블 (아래 컬럼 표) |
| `feature_catalog()` | `pd.DataFrame` | X feature 메타 (fab_metro_prc) |
| `dc_spec()` | `dict` | `feature_key → {"lower", "upper"}` |
| `targets_by_category()` | `dict` | `category → [Y target 컬럼명]` |
| `target_units()` | `dict` | `target → 단위 문자열` |
| `category_feature_names()` | `list[str]` | 분할 가능한 wafer 단위 컬럼명 |
| `eds_steps()` | `list[str]` | EDS step 선택지(라벨, 필터 아님) |
| `target_lag_days()` | `int` | EDS 확보 지연(일) |

### 3-1. `fact_table()` 컬럼 (한 행 = wafer × fab_step)

| 컬럼 | 형식 | 필수 | 의미 |
|---|---|:--:|---|
| `wafer_id` | str | ✅ | wafer 식별자 (scatter 점 hover 툴팁·raw CSV에 표시) |
| `root_lot_id` | str | ✅ | root lot 식별자 (wafer 묶음. 툴팁·raw CSV에 표시) |
| `line_id` | str | ✅ | 라인 (필터 차원 → 목록 자동 파생) |
| `product` | str | ✅ | 제품 (필터 차원) |
| `fab_step` | str | ✅ | 공정 step (필터 차원) |
| `fab_track_out_time` | datetime | ✅ | 공정 trackout 시각 → **x축·분석 기간 기준** |
| `eds_tkout_time` | datetime | ✅ | EDS(=y target) 확보 시각 |
| `observed` | bool | ✅ | y target 확보 여부 (False면 target=NaN, 추정 대상) |
| `<feature_key>` | float | ✅* | numeric X feature 값. **컬럼명 = `feature_key`** (§3-2). 해당 fab_step 행에만 값, 나머지 NaN |
| `<target>` | float | ✅ | Y target 값. observed=False면 NaN |
| `<category_feature>` | str | ✅ | 분할 컬럼 (PPID/ECO/EQP…). wafer 단위로 모든 행에 반복 |

\* numeric feature 컬럼은 `feature_catalog`의 numeric 행 수만큼 있어야 하고, 컬럼명이 `feature_key`와 일치해야 한다.

**중요한 규약**
- **observed-only**: window·표·Cpk는 `observed=True` 행만 집계. 최근 `target_lag_days`일 wafer는 보통 미확보(추정 y 대상).
- **NaN 의미**: feature는 "그 fab_step이 아니라서" NaN, target은 "아직 미확보라서" NaN. 둘 다 자연스럽게 빠진다.
- 한 wafer가 여러 fab_step을 거치면 그 수만큼 행이 생기고, target/분할 값은 행마다 반복된다.

### 3-2. `feature_key` (X feature 식별자)

파이프키 형식: `data_type|fab_step|metro_step|metro_item|subitem`
예: `numeric|EQ760200|MT100001|CD_MEAN|avg`

`fact_table`의 feature 컬럼명 == 이 값. `data_source.feature_key(...)` 헬퍼로 생성.

### 3-3. `feature_catalog()` 컬럼

| 컬럼 | 의미 |
|---|---|
| `fab_step` | 이 feature가 측정되는 공정 step |
| `metro_step` / `metro_item` / `subitem` | 계측 step / 항목 / 하위항목 |
| `metro_grade` / `metro_category` | 계측 등급(A/B…) / 분류(VM/FDC…) — X feature 필터에 사용 |
| `data_type` | `"numeric"` (현재 numeric만 분석). category형은 분할(category_feature)로 |
| `unit` | 단위 |
| `feature_key` | §3-2 |
| `display_name` | 화면 표시명 (예: `CD_MEAN / avg`) |

---

## 4. 교체 예시

### 4-1. CSV에서 읽기

```python
# data_source.py
import pandas as pd
from functools import lru_cache

@lru_cache(maxsize=1)
def fact_table() -> pd.DataFrame:
    df = pd.read_parquet("/data/prc_fact.parquet")     # 또는 read_csv
    for c in ["fab_track_out_time", "eds_tkout_time"]:  # 문자열이면 datetime 변환
        df[c] = pd.to_datetime(df[c])
    return df

@lru_cache(maxsize=1)
def feature_catalog() -> pd.DataFrame:
    return pd.read_csv("/data/feature_catalog.csv")     # §3-3 컬럼 포함

def dc_spec() -> dict:
    s = pd.read_csv("/data/dc_spec.csv")                # feature_key, lower, upper
    return {r.feature_key: {"lower": r.lower, "upper": r.upper} for r in s.itertuples()}

def targets_by_category() -> dict:
    return {"BIN": ["BIN0131", ...], "MSR": [...]}      # 설정/메타에서
def target_units() -> dict: ...
def category_feature_names() -> list: return ["PPID", "ECO", "EQP_MODEL", "EQP"]
def eds_steps() -> list: return ["EDS_M", "EDS_P"]
def target_lag_days() -> int: return 60
```

### 4-2. DB에서 읽기

```python
@lru_cache(maxsize=1)
def fact_table() -> pd.DataFrame:
    import sqlalchemy as sa
    eng = sa.create_engine(os.environ["PRC_DB_URL"])
    # wafer×fab_step long 형태로 가공한 뷰/쿼리 권장 (feature를 컬럼으로 pivot)
    return pd.read_sql("SELECT * FROM v_prc_fact", eng, parse_dates=["fab_track_out_time", "eds_tkout_time"])
```

> 사내 데이터가 wafer×feature **wide**라면, feature를 `feature_key` 컬럼명으로 pivot하고
> fab_step별 행으로 펼쳐 long 형태로 만들면 된다. (검증 스크립트가 형태를 잡아준다.)

### 4-3. `observed`가 데이터에 없을 때

EDS 확보 여부 플래그가 없으면 시각으로 만들면 된다:
```python
NOW = pd.Timestamp.now()
df["observed"] = df["eds_tkout_time"].notna() & (df["eds_tkout_time"] <= NOW)
```

---

## 5. 검증

```bash
python validate_data.py
```
- **스키마**: 필수 컬럼/형식/feature_key↔컬럼 일치/ dc_spec 키 등 점검 → 문제를 한 줄씩 출력
- **파생 차원**: line/product/fab_step/category/분할값/단위가 데이터에서 어떻게 잡혔는지 확인
- **표본 점검**: feature별 비결측 수가 너무 적으면 경고(bin이 비거나 thin)
- **분석 smoke**: binned/timeseries/table을 실제로 한 번 돌려 0건/에러를 사전 차단

초록불(`✓ 전부 통과`)이면 대시보드에 바로 쓸 수 있다.

### 단위 테스트 (analytics 회귀 보호)
```bash
pip install -r requirements-dev.txt   # pytest
pytest -q                              # backend/ 에서
```
- `tests/test_analytics.py` — 통계 헬퍼(Cpk σ·관리한계·drift·회귀추정·외삽)와 compute_* 계약(필드/식별자/forecast 신뢰가드)을 검증.
- 데이터 소스를 교체했다면 `validate_data.py` 통과 후 `pytest`도 돌려 분석 계약이 안 깨졌는지 확인할 것.

---

## 6. 자주 막히는 곳

| 증상 | 원인 / 해결 |
|---|---|
| `numeric feature_key '…' 에 해당하는 fact_table 컬럼 없음` | feature 컬럼명이 `feature_key`(파이프키)와 다름 → 컬럼명을 맞추거나 catalog의 키를 맞춤 |
| window/표가 비어 보임 | `observed=True` 행이 없음(전부 최근=미확보) → `target_lag_days`·기간·`observed` 확인 |
| `'fab_track_out_time'는 datetime 형이어야 함` | `pd.to_datetime(...)`으로 변환 |
| 분할 드롭다운에 인자가 안 보임 | `category_feature_names()`가 반환하는 컬럼명이 fact_table에 있어야 함 |
| Cpk가 다 비어 있음 | feature 표본 < 2이거나 dc_spec에 해당 feature 없음 |
| 최근 구간 window가 항상 비는 게 정상? | ✅ lag(`target_lag_days`) 때문. 최근 wafer는 EDS 미확보(추정 y 대상)라 window·표·Cpk에서 빠진다 |

---

## 7. 참고 — 최근 분석 업데이트 (데이터 계약에는 영향 없음)

아래는 분석 산출물 해석에 참고할 변경점이다. **`data_source.py` 계약과 무관**하므로,
데이터만 갈아끼우면 그대로 동작한다(별도 작업 불필요).

- **driver 랭킹에 유의성**: 상관마다 p-value + 다중비교 보정 q-value(Benjamini-Hochberg FDR)를 함께 반환.
  화면에선 **q ≥ 0.1(우연 가능)** 항목을 흐리게 + `ns` 표시 → 우연 상관을 공정 윈도우 결정에서 배제.
  (계산에 `scipy` 필요 — §2의 requirements에 포함)
- **관리한계·drift σ 일관화**: 시계열 UCL/LCL과 drift 판정의 σ를 **단기(군내 I-MR) = MR̄/1.128** 기준으로 통일
  (Cpk의 within σ와 동일 정신). 응답 `control_limits`에 `sigma`(단기)·`sigma_overall`(전체)·`method` 동시 노출.
- 위 변경은 **표본/데이터에 따라 자동 산출**되므로 실데이터에서도 추가 설정이 없다.

문의: 구조는 `data.py`(파생 규칙)·`analytics.py`(분석식) 주석 참고. 분석식(Cpk/Ppk/추정/FDR/관리한계 σ 등)은
프로젝트 `MEMORY.md` 참고.
