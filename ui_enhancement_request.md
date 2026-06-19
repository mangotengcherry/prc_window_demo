# UI Enhancement Request for Claude Code

이 문서는 현재 `Process Window 분석 대시보드`를 단순 데모가 아니라 회사 백엔드 데이터만 연결하면 실무에서 사용할 수 있는 UI로 고도화하기 위해 Claude Code에 전달할 요청서 양식이다.

## 작성 전제

- 현재 프로젝트는 `Vue 3 + Vite + ECharts` 프론트엔드와 `FastAPI` 백엔드로 구성되어 있다.
- 프론트엔드 API 호출은 `frontend/src/api/client.js`에 모여 있다.
- 백엔드 응답 계약은 `backend/schemas.py`에 정의되어 있다.
- 현재 화면은 `feature × target` 조합별 process window chart, matching time series chart, summary table을 제공한다.
- 목표는 화면만 보기 좋은 데모가 아니라, 회사 backend data를 연결했을 때 분석 업무자가 반복적으로 사용할 수 있는 UI로 만드는 것이다.

## 현재 프로젝트 구조 요약

```text
backend/
  main.py          # FastAPI route
  schemas.py       # request/response schema
  analytics.py     # binning, timeseries, table 계산
  data.py          # demo data source, columns, DC spec

frontend/
  src/
    App.vue
    api/client.js
    components/
      Sidebar.vue
      ComboRow.vue
      WindowChart.vue
      ComboTimeSeries.vue
      DataTable.vue
    style.css
```

## 현재 UI 기능

- 좌측 사이드바에서 `Y target`, `X feature`, `fab_step`을 선택한다.
- `차트 작성` 버튼을 누르면 백엔드에서 binned chart, time series, table data를 가져온다.
- 각 `feature × target` 조합별로 한 행이 생성된다.
- 각 행은 `Window chart`와 `시계열 chart`를 함께 보여준다.
- 사용자 입력 spec lower/upper가 chart와 table에 반영된다.
- DC spec은 백엔드에서 받아 window chart와 table에 표시된다.

## 추가 업무 요구사항 요약

이번 고도화에서는 기존 `fab_step + x_feature + y_target` 중심 UI를 회사 데이터 구조에 맞게 확장한다.

- 최상단 분석 조건에 `Line_ID`, `제품`, `Category`, `EDS_STEP`, `Y_Target 추출 기간`을 추가한다.
- `Y_Target`은 category와 EDS step 기준으로 필터링하고, 여러 Y target을 합산한 사용자 정의 grouped target을 만들 수 있게 한다.
- `X_Feature`는 기본적으로 `fab_metro_prc` 매칭 정보를 기준으로 선택된 `FAB_STEP`과 연관된 metro item만 보여준다.
- `X_Feature` 목록은 `Metro_Grade`, `Metro_Category`, matching on/off로 필터링할 수 있어야 한다.
- Window chart와 time series chart는 `Category Feature` 기준으로 multi-line 또는 split chart 모드를 지원한다.
- 시계열 차트는 `fab_step track_out_time`을 x축으로 사용하되, EDS Test 지연으로 최근 y target 실측값이 없는 구간은 간단한 통계식 기반 추정값을 실제값과 분리해 표시한다.
- 요약 테이블에는 category, category feature, metro metadata를 추가한다.
- 별도 교호작용 분석 영역에서 선택된 X features와 Y target 중 2개 feature를 골라 scatter/heatmap과 ranking table을 만든다.

## Claude Code에 전달할 기본 요청문

```text
현재 프로젝트의 UI를 실무 사용 가능한 수준으로 고도화해줘.

목표:
- 단순 데모 화면이 아니라 회사 backend data만 연결하면 분석 업무에 바로 사용할 수 있는 대시보드 UI로 만든다.
- 현재 Vue 3 + Vite + ECharts 구조는 유지한다.
- API 호출은 frontend/src/api/client.js에 모으고, 백엔드 데이터 계약은 backend/schemas.py 기준으로 맞춘다.
- 불필요한 대규모 리팩터링은 하지 말고, 현재 구조를 유지하면서 필요한 UI/UX, 상태 처리, 데이터 연결 준비를 보강한다.
- 기존 FAB_STEP, X_FEATURE, Y_TARGET 선택 구조를 회사 데이터 구조에 맞게 Line_ID, 제품, Category, EDS_STEP, 기간, metro item matching, category feature 분석까지 확장한다.

먼저 현재 프로젝트 구조와 주요 컴포넌트를 읽고, 구현 계획을 제안한 뒤 진행해줘.
```

## 고도화 요구사항

### 1. 데이터 연결 준비

목표:

- 회사 백엔드로 교체할 때 프론트엔드 수정 범위를 최소화한다.
- API 응답이 비어 있거나 일부 필드가 누락되어도 화면이 깨지지 않게 한다.

요구사항:

- `frontend/src/api/client.js`에 API base URL 설정 방식을 명확히 둔다.
- 개발용 proxy와 운영용 backend URL을 구분할 수 있게 한다.
- API 실패, timeout, 빈 응답, 잘못된 응답 형식에 대한 UI 상태를 추가한다.
- 현재 필요한 API 계약을 문서화한다.

확인 기준:

- 백엔드가 꺼져 있을 때 사용자가 무엇을 해야 하는지 알 수 있다.
- 특정 chart data가 비어 있어도 전체 화면이 무너지지 않는다.
- API endpoint 변경 시 수정 위치가 `client.js` 중심으로 제한된다.

### 2. 선택 UI 개선

목표:

- Line, 제품, category, EDS step, Y target, FAB step, X feature 수가 많아져도 빠르게 분석 조건을 구성할 수 있게 한다.

요구사항:

- Tab 또는 좌측 조건 영역 최상단에 `Line_ID` 선택 섹션을 추가한다.
  - 예: `AAAA`, `BBBB`, `CCCC`, `DDDD`
- `Line_ID` 아래에 `제품` 선택 섹션을 추가한다.
  - 예: `AAEQ`, `BBCR`, `CCAK`, `DDGQ`
- `Y_Target` 선택 창 위에 `Category` 선택 섹션을 추가한다.
  - 예: `BIN`, `MSR`, `AWACS`
- `Category` 아래에 `EDS_STEP` 선택 섹션을 추가한다.
  - 예: `EDS_M`, `EDS_P`
- `Y_Target` 선택 창은 `EDS_STEP` 아래에 배치한다.
  - 예: `BIN0131`, `BIN0132`, ..., `BIN0600`
- 분석 기간 선택 기능을 추가한다.
  - 시계열 x축과 window 분석의 기본 시간 기준은 `fab_step track_out_time`이다.
  - Y target의 실제 측정/확보 시점은 `eds_tkout_time`으로 별도 관리한다.
  - 최근 `fab_step track_out_time` 구간은 아직 EDS Test가 끝나지 않아 y target 값이 없을 수 있으므로, 실제값과 추정값을 UI에서 명확히 구분한다.
  - `start_date`, `end_date`를 달력 UI로 선택한다.
  - 실제 backend 컬럼명은 회사 schema에 맞춰 확정하되, 문서에서는 예시로 `fab_track_out_time`, `eds_tkout_time`을 사용한다.
- 모든 선택 목록은 검색, 선택 개수, 검색 결과 개수, 전체 선택, 전체 해제를 지원한다.
- `차트 작성` 버튼은 필수 선택값이 없을 때 disabled 상태로 보여준다.
- 선택 조건을 현재 분석 조건으로 요약 표시한다.

확인 기준:

- 사용자는 어떤 line, 제품, category, EDS step, 기간, fab step, feature, target으로 분석 중인지 한눈에 알 수 있다.
- 선택값이 없는 상태에서 의미 없는 API 요청이 발생하지 않는다.

### 2-1. Y Target Grouping

목표:

- 여러 Y target을 합산해 별도의 분석 target으로 사용할 수 있게 한다.

요구사항:

- 사용자가 `Y_Target`을 단일 또는 여러 개 체크할 수 있다.
- 여러 Y target을 체크한 뒤 `Grouping` 버튼을 누르면 합산 target을 만들 수 있다.
- grouping 시 사용자가 새 target 이름을 입력한다.
- grouped target은 기존 `Y_Target` 목록에 추가되어 일반 target처럼 선택할 수 있다.
- grouped target은 원본 target 목록과 계산 방식이 추적 가능해야 한다.
  - 예: `BIN0131 + BIN0153`, aggregation: `sum`
- 같은 이름의 grouped target이 있을 때 overwrite, rename, cancel 중 하나를 선택하게 한다.

확인 기준:

- `BIN0131`, `BIN0153`을 선택해 `BIN0131_0153_SUM` 같은 target을 만들 수 있다.
- grouped target을 선택해 window chart, time series, summary table에 사용할 수 있다.
- grouped target의 원본 구성이 UI에서 확인된다.

### 2-2. FAB STEP 및 X Feature Matching

목표:

- `fab_metro_prc` 데이터 테이블의 매칭 정보를 사용해 FAB step과 관련 있는 metro item을 우선적으로 보여준다.

업무 데이터 전제:

- `FAB_STEP` 형식은 알파벳 2개 + 숫자 6자리다.
  - 예: `EQ760200`
- `fab_metro_prc`에는 아래 매칭 정보가 있다.
  - `FAB_STEP`
  - `METRO_STEP`
  - `METRO_ITEM`
  - `METRO_GRADE`
  - `METRO_CATEGORY`
- `METRO_CATEGORY` 예시는 `VM`, `Metro`, `PC`, `FDC` 등이다.

X feature 이름 생성 기준:

- X feature key는 backend와 frontend가 동일하게 해석할 수 있도록 `|` delimiter를 사용한다.
- 기본 형식은 아래와 같다.

```text
data_type|fab_step|metro_step_or_fdc_step|metro_item_or_fdc_sensor_item|subitem
```

- `data_type`
  - `numeric`: 연속형 수치 feature
  - `category`: 범주형 feature
- `fab_step`
  - 예: `EQ760200`
- `metro_step_or_fdc_step`
  - metro data인 경우 `METRO_STEP`
  - FDC data인 경우 `FDC_STEP`
- `metro_item_or_fdc_sensor_item`
  - metro data인 경우 `METRO_ITEM`
  - FDC data인 경우 sensor item
- `subitem`
  - 예: `avg`, `std`, `min`, `max`, `median`

예시:

```text
numeric|EQ760200|MT123456|CD_MEAN|avg
numeric|EQ760200|FD123456|TEMP_SENSOR_01|std
category|EQ760200|FD123456|EQP_CH|value
```

UI 표시 기준:

- 내부 key는 전체 문자열을 유지한다.
- 화면 목록에서는 너무 길어지지 않도록 주요 정보를 분리해서 보여준다.
  - 예: `CD_MEAN / avg`
  - 보조 정보: `numeric · FAB EQ760200 · STEP MT123456`
- tooltip 또는 detail 영역에서 full key를 복사할 수 있게 한다.
- `data_type=category`인 feature는 heatmap/scatter나 aggregation에서 사용할 수 있는 방식이 numeric feature와 다를 수 있으므로, 선택 UI에서 category feature임을 명확히 표시한다.

요구사항:

- `X_FEATURE` 선택 창은 기본적으로 선택된 `FAB_STEP`과 연관된 metro item만 보여준다.
- `Matching Off` 토글을 제공해 FAB step 기반 필터링을 끌 수 있게 한다.
- Matching on/off를 전환해도 사용자가 이미 체크한 X feature는 reset되지 않아야 한다.
- X feature 목록은 아래 조건으로 추가 필터링할 수 있어야 한다.
  - `Metro_Grade`
  - `Metro_Category`
- reset 기능은 명시적 버튼으로 제공한다.
  - 추천: `선택 초기화`, `현재 필터 결과만 선택 해제`, `전체 선택 해제`를 구분한다.

확인 기준:

- Matching On 상태에서 FAB step과 연관된 metro item만 기본 노출된다.
- Matching Off 상태에서는 전체 X feature 후보를 검색할 수 있다.
- Matching 토글을 바꿔도 기존 체크 항목이 유지된다.
- 사용자는 현재 선택된 X feature가 필터 결과 밖에 있더라도 선택 상태를 확인할 수 있다.

### 3. Chart UX 개선

목표:

- 분석자가 chart를 해석하고 비교하기 쉽게 한다.

요구사항:

- user spec과 DC spec의 범례를 명확히 보여준다.
- chart tooltip에 bin range, wafer count, y average를 읽기 쉽게 표시한다.
- time series chart에서 target과 feature의 단위/이름이 잘 보이게 한다.
- loading 중 chart 영역에 skeleton 또는 명확한 loading state를 보여준다.
- 데이터가 없는 조합은 빈 chart 대신 원인 메시지를 보여준다.
- `Category Feature` 기준 chart 표시 방식을 추가한다.

확인 기준:

- chart 색상과 선의 의미를 처음 보는 사용자도 이해할 수 있다.
- 데이터가 적거나 없는 경우에도 사용자가 상황을 알 수 있다.

### 3-1. Category Feature Chart Mode

목표:

- `Category Feature`별 차이를 window chart와 time series chart에서 비교할 수 있게 한다.

Category Feature 예시:

- `ECO`
  - 예: `공정평가1`, `공정평가2`
- `PPID`
  - 예: `표준조건`, `평가조건1`, `평가조건2`
- `EQP_MODEL`
- `EQP`
- `EQP_CH`

요구사항:

- 사용자가 Category Feature를 선택할 수 있게 한다.
- Category Feature 표시 방식은 두 가지 모드를 제공한다.
  - 옵션 1: 하나의 chart 안에 Category Feature별 `y_avg` line을 여러 개 표시하고 legend 색상으로 구분한다.
  - 옵션 2: Category Feature 값별로 chart를 나누어 표시한다.
- 옵션 1과 옵션 2를 UI에서 선택할 수 있어야 한다.
- 모든 Category Feature 값이 표시되면 chart가 복잡해지므로, legend 또는 별도 선택 UI로 표시할 Category Feature 값을 일부만 선택할 수 있어야 한다.
- 선택된 Category Feature 값은 window chart와 time series chart 모두에 일관되게 적용한다.

확인 기준:

- 사용자는 ECO, PPID, EQP 등 category feature별 y_avg 차이를 비교할 수 있다.
- multi-line 모드와 split-chart 모드를 전환할 수 있다.
- legend에서 일부 category feature 값을 숨기거나 다시 표시할 수 있다.

### 3-2. 시계열 Y Target 지연 및 추정값 표시

목표:

- `fab_step track_out_time` 기준으로 최근 구간을 볼 때, 아직 EDS Test가 완료되지 않아 y target 실측값이 없는 기간도 현업 판단에 필요한 수준으로 보조 추정한다.

업무 배경:

- FAB step 진행 후 y target 값은 EDS Test를 통해 뒤늦게 확보된다.
- 예: `EQ760200` 진행 시점으로부터 약 2개월 뒤에 `BIN0131` 같은 y target 값이 확보될 수 있다.
- 따라서 최근 `fab_step track_out_time` 구간에는 x feature 값은 존재하지만 y target 실측값은 결측일 수 있다.
- 현업 담당자는 과거의 x feature와 y target 관계, window 수준, fitting 수준을 참고해 해당 시점의 불량률을 대략 추정해 판단한다.

요구사항:

- 시계열 차트의 x축은 `fab_step track_out_time` 기준으로 유지한다.
- y target series는 `observed`와 `estimated`를 분리한다.
  - `observed`: EDS Test가 완료되어 실제 y target 값이 확보된 점
  - `estimated`: 아직 y target이 확보되지 않은 최근 구간에 대해 통계식으로 산출한 점
- 최근 결측 구간은 하루에 1 point만 표시한다.
  - 같은 날짜에 여러 wafer/lot이 있으면 backend에서 일 단위로 집계한 추정값을 내려준다.
- 추정 방식은 v1에서 고비용 모델이 아니라 단순하고 설명 가능한 통계식으로 제한한다.
  - 후보 1: window bin별 과거 평균 기반 추정
  - 후보 2: 선택된 x feature와 y target의 단순 선형 fitting
  - 후보 3: backend가 제공하는 `fit_method` 중 하나를 UI에서 표시만 한다.
- 추정값은 실제 scatter point와 명확히 다르게 표현한다.
  - 더 낮은 opacity
  - hollow marker 또는 dashed border
  - tooltip에 `estimated` 표시
  - legend에 `Y target observed`, `Y target estimated`를 분리 표시
- 추정값은 의사결정 보조값이며 실제 EDS Test 결과와 동일하게 취급하지 않는다.
- 추정값이 생성된 기간, 사용한 fitting 방식, reference 기간, 표본수는 tooltip 또는 metadata 영역에서 확인 가능해야 한다.

확인 기준:

- 최근 2개월처럼 y target 실측값이 없는 구간도 날짜별 1 point 추정값으로 흐름을 볼 수 있다.
- 사용자는 실제 y target point와 추정 point를 색상, border, 투명도, legend로 구분할 수 있다.
- 추정값이 summary table, export, KPI에 섞일 때는 `value_status=estimated`처럼 명시적으로 표시된다.
- 추정값만 있는 구간을 실제 품질 결과로 오해하지 않도록 경고 또는 보조 라벨이 표시된다.

### 4. Summary Table 개선

목표:

- chart를 보고 끝나는 화면이 아니라, 결과를 비교하고 판단할 수 있는 표를 만든다.

요구사항:

- 컬럼 의미를 명확히 표시한다.
- user/DC range가 100%를 초과하거나 비정상 값일 때 시각적으로 강조한다.
- table이 길어질 때 header sticky와 가로 스크롤을 안정적으로 유지한다.
- 필요한 경우 CSV export 버튼을 추가한다.
- 정렬 또는 필터가 필요하면 최소 기능으로 추가한다.
- `Category`, `Category Feature`, `Metro` 관련 metadata 컬럼을 추가한다.

확인 기준:

- 사용자는 여러 조합의 spec range 상태를 빠르게 비교할 수 있다.
- table data가 많아져도 읽기 어렵지 않다.
- 사용자는 summary table에서 각 row가 어떤 category, category feature, metro item 조건에 해당하는지 확인할 수 있다.

추가 컬럼 후보:

- `line_id`
- `product`
- `category`
- `eds_step`
- `fab_step`
- `metro_step`
- `metro_item`
- `metro_grade`
- `metro_category`
- `category_feature_name`
- `category_feature_value`
- `y_target`
- `x_feature`
- `user_spec_lower`
- `user_spec_upper`
- `dc_spec_lower`
- `dc_spec_upper`
- `n` (표본수)
- `mean`, `std`
- `cpk` (또는 ppk)
- `in_spec_pct`, `oos_count`

### 5. Layout 및 정보 구조 개선

목표:

- 데모처럼 보이는 화면을 실무용 분석 도구처럼 정리한다.

요구사항:

- 상단에 현재 분석 조건, 상태, 마지막 조회 시간을 표시한다.
- 좌측 사이드바, chart 영역, table 영역의 역할을 명확히 분리한다.
- chart row가 많아졌을 때 스크롤과 섹션 구분이 안정적이어야 한다.
- 모바일 최적화보다 desktop 분석 환경을 우선한다.
- 카드 내부에 불필요하게 큰 제목이나 장식 요소를 추가하지 않는다.

확인 기준:

- 1920px desktop 화면에서 여러 chart를 비교하기 편하다.
- 1366px laptop 화면에서도 주요 컨트롤과 chart가 겹치지 않는다.

### 6. 상태 관리

목표:

- 사용자가 현재 화면 상태를 예측할 수 있게 한다.

요구사항:

- initial, loading, loaded, empty, error 상태를 분리한다.
- (신규) `thin` 상태: 데이터는 있으나 표본이 부족(`n < min_n`)해 신뢰도가 낮은 경우를 empty와 별도로 구분한다. (`6-2 (A)` 참고)
- API 요청 중 중복 클릭을 막는다.
- 마지막 성공 결과와 현재 요청 실패 상태를 구분한다.
- spec 입력값이 조합별로 유지되는지 확인한다.

확인 기준:

- loading 중 같은 요청이 반복 실행되지 않는다.
- 실패 상태에서도 이전 결과를 유지할지 지울지 정책이 코드에 명확하다.

### 6-1. 교호작용 분석 영역

목표:

- 차트 작성에 사용된 X features와 Y target을 바탕으로 두 feature 간 교호작용을 scatter/heatmap으로 분석한다.

요구사항:

- 별도 `교호작용 분석` 영역을 추가한다.
- 차트 작성에 사용된 X features 및 Y target 중 교호작용 분석 대상 feature 2개를 선택할 수 있어야 한다.
- value 값으로 사용할 인자를 선택할 수 있어야 한다.
  - 예: wafer count, y average, grouped target value, 특정 metric 등
- 선택된 두 feature를 x/y축으로 하는 scatter chart를 제공한다.
- 선택된 두 feature를 x/y축으로 하는 heatmap chart를 제공한다.
- heatmap은 아래 값을 interactive하게 조정할 수 있어야 한다.
  - x축 bin 개수
  - y축 bin 개수
  - x축 scale/range
  - y축 scale/range
- heatmap cell 값은 사용자가 선택한 value 인자의 aggregation 결과로 표시한다.
  - aggregation 옵션: `average`, `median`
- 교호작용 분석에 사용한 두 feature 조합으로 발생하는 경우의 수를 aggregation 값 기준 rank table로 보여준다.

확인 기준:

- 사용자는 선택된 feature 2개에 대해 scatter와 heatmap을 모두 볼 수 있다.
- bin 개수와 scale 조정이 chart에 즉시 반영된다.
- rank table에서 어떤 feature 조합이 value 값이 높은지 낮은지 확인할 수 있다.
- average와 median aggregation을 전환할 수 있다.

### 6-2. 분석·의사결정 레이어 (DS/UX 검토 반영, 신규 — Chart/Table/State/계약 횡단)

목표:

- 현재 스펙이 정의한 "회사 데이터를 연결하면 동작하는" 도구를, 분석가가 "신뢰하고 판단하는" 도구로 끌어올린다.
- 핵심 원칙: 아래 항목 다수는 프론트 기능이 아니라 `7-1`의 응답 계약 필드다. 계약 필드는 회사 backend 동결 *전*에 확정한다(나중에 추가하면 조직 경계를 넘는 재집계·재배포·재검증이 든다). 전부 경량 통계이며 딥러닝/고비용 알고리즘은 사용하지 않는다.

#### (A) 불확실성·표본 신뢰도

요구사항:

- binned `bins[]`, summary table row, heatmap cell에 표본수(`n`/`wafer_count`)와 산포(`y_std` 또는 `y_sem`)를 포함한다.
- window chart의 `y_avg` line에 신뢰구간 band(±1.96·SE) 또는 error bar를 표시하고, 표본이 적은 bin은 흐리게/점선으로 디엠퍼시스한다.
- grouping(합산) × category split × binning이 겹치면 셀당 표본이 곱셈적으로 줄어든다. `min_n` 미만 셀은 `thin`(신뢰 낮음) 상태로 빈 셀과 별도 구분한다.

확인 기준:

- 사용자는 각 bin/row/cell의 평균이 몇 개 wafer에 기반하고 얼마나 흔들리는지 알 수 있다.
- 표본이 적은 구간이 시각적으로 구분된다.

#### (B) 공정능력·적합성 지표

요구사항:

- summary table에 `n`, `mean`, `std`, `cpk`(또는 ppk), `in_spec_pct`(user spec 기준), `oos_count`를 추가한다.
- 계산은 backend에서 한다: `Cpk = min(USL−μ, μ−LSL) / (3σ)`.
- 기존 user/DC range %와 함께 의사결정 핵심 지표로 강조한다.

확인 기준:

- 사용자는 각 조합이 spec 대비 얼마나 안정적인지(Cpk)와 이탈 비율(OOS)을 표에서 바로 본다.

#### (C) 시계열 이상·드리프트 (관리도)

요구사항:

- time series에 관리한계(평균 ±3σ)와 연속 N점 한쪽 치우침 같은 단순 관리도 규칙을 표시한다.
- user/DC spec을 벗어난 점은 빨강으로 강조하고 위반 개수를 배지로 표시한다.
- ★ 다운샘플(아래 D)을 적용하면 클라이언트가 계산한 평균/σ/이동평균/관리한계는 편향된다. 따라서 avg·control limit는 backend가 풀데이터로 계산해 응답에 포함한다.

확인 기준:

- 분석가는 spec 이탈·드리프트를 색과 배지로 즉시 인지한다.

#### (D) 스케일·다운샘플

요구사항:

- timeseries 응답에 `sampled`(bool), `n_total`(int)을 포함하고 서버에서 LTTB 등으로 점 수를 줄인다.
- 프론트는 ECharts `sampling: 'lttb'`를 병행하고, 다운샘플 여부를 사용자에게 표시한다.

확인 기준:

- 기간이 넓어 wafer가 수십만~수백만이어도 차트가 멈추지 않는다.
- 사용자는 화면이 원본인지 다운샘플인지 안다.

#### (E) Feature 영향도 정렬

요구사항:

- `x-feature-options` 응답의 `features[]`에 `score`(예: |상관계수| 또는 단변량 설명력)를 포함한다.
- X feature 목록을 "영향도순"으로 정렬할 수 있게 한다. matching이 후보를 대량 생성하므로 분석가가 어디부터 볼지 빠르게 고르게 한다.

확인 기준:

- 후보가 수백 개여도 영향이 큰 feature가 상단에 온다.

#### (F) 최적 process window 추천

요구사항:

- binned 응답 combo에 `recommended_window { lower, upper, score }`(옵션)를 포함한다. target을 최적화하면서 표본이 충분한 feature 구간을 backend가 탐색해 제안한다.
- window chart에 추천 구간을 band로 오버레이한다(사용자 spec 입력과 별도의 보조 가이드).

확인 기준:

- 사용자는 spec을 처음부터 수기로 찾지 않고 추천 구간을 출발점으로 조정한다.

#### (G) 색맹 안전 시각 인코딩

요구사항:

- `frontend/src/style.css` 색 토큰을 Okabe-Ito 같은 색맹 안전 팔레트로 정리한다.
- user spec/DC spec 선은 색(빨강/검정)에만 의존하지 말고 dash 패턴·라벨을 병행한다.
- category feature 다중 series는 빨강·초록 조합을 피한다(spec·feature 의미색과 충돌 방지).

확인 기준:

- 적록색약 사용자도 spec 선과 series를 구분할 수 있다.

#### (H) KPI 요약 밴드 (overview → detail)

요구사항:

- 상단 분석 조건 영역에 핵심 KPI 카드를 둔다: 총 wafer 수, in-spec %, OOS 개수, Cpk가 가장 낮은 조합/스텝.
- 상세(combo row)로 내려가기 전에 전체 상태를 한눈에 파악하게 한다.

확인 기준:

- 사용자는 스크롤 전에 전체 공정 상태를 빠르게 파악한다.

#### (I) Linked Brushing (서버 필터 기반)

요구사항:

- time series에서 시간 구간을 brush 선택하면 해당 구간 wafer만으로 window chart·table을 다시 집계한다.
- 단, 비목표("전체 raw data를 프론트로 내려받아 무거운 aggregation 금지")를 지키기 위해 클라이언트 집계가 아니라 backend round-trip으로 구현한다: `/api/binned`·`/api/table`에 `selection`(time_range 또는 wafer_filter) 파라미터를 추가한다.
- scatter brush → 선택 wafer drill-down table(옵션)도 같은 방식.

확인 기준:

- 한 구간을 선택하면 다른 차트·표가 그 구간 기준으로 갱신된다.
- 대용량에서도 프론트가 무거워지지 않는다.

#### (J) Provenance·재현성

요구사항:

- 상단에 데이터 출처, 분석 기간(`fab_track_out_time` 기준), y target 확보 범위(`eds_tkout_time` 기준), 표본수, 쿼리 식별자를 한 줄로 표시한다.
- 현재 분석 조건을 URL 쿼리로 직렬화해 공유 가능한 링크를 만든다(P2의 localStorage/preset과 연계).

확인 기준:

- 다른 사람이 같은 링크로 같은 화면을 재현할 수 있다.

### 7. Backend Data 연결 계약

회사 백엔드와 연결할 때 아래 계약을 우선 확인한다.

#### GET `/api/columns`

필요 응답:

```json
{
  "line_ids": ["AAAA", "BBBB", "CCCC", "DDDD"],
  "products": ["AAEQ", "BBCR", "CCAK", "DDGQ"],
  "categories": ["BIN", "MSR", "AWACS"],
  "eds_steps": ["EDS_M", "EDS_P"],
  "features": [
    "numeric|EQ760200|MT123456|METRO_ITEM_A|avg",
    "numeric|EQ760200|FD123456|TEMP_SENSOR_01|std"
  ],
  "targets": ["BIN0131", "BIN0132"],
  "fab_steps": ["EQ760200", "AB123456"],
  "metro_grades": ["A", "B"],
  "metro_categories": ["VM", "Metro", "PC", "FDC"],
  "category_features": ["ECO", "PPID", "EQP_MODEL", "EQP", "EQP_CH"],
  "dc_spec": {
    "numeric|EQ760200|MT123456|METRO_ITEM_A|avg": { "lower": 1.0, "upper": 5.0 }
  }
}
```

#### GET `/api/x-feature-options`

목적:

- 선택된 FAB step과 metro metadata 조건을 기준으로 X feature 후보를 가져온다.

요청 query 예시:

```text
fab_step=EQ760200&matching=true&metro_grade=A&metro_category=VM
```

필요 응답:

```json
{
  "matching": true,
  "fab_step": "EQ760200",
  "features": [
    {
      "name": "numeric|EQ760200|MT123456|METRO_ITEM_A|avg",
      "display_name": "METRO_ITEM_A / avg",
      "data_type": "numeric",
      "metro_step": "MT123456",
      "metro_item": "METRO_ITEM_A",
      "subitem": "avg",
      "metro_grade": "A",
      "metro_category": "VM",
      "matched_fab_steps": ["EQ760200"]
    }
  ]
}
```

#### POST `/api/y-target-groups`

목적:

- 여러 Y target을 합산한 grouped target을 생성한다.

요청:

```json
{
  "name": "BIN0131_0153_SUM",
  "source_targets": ["BIN0131", "BIN0153"],
  "aggregation": "sum"
}
```

필요 응답:

```json
{
  "name": "BIN0131_0153_SUM",
  "source_targets": ["BIN0131", "BIN0153"],
  "aggregation": "sum",
  "created": true
}
```

#### POST `/api/binned`

요청:

```json
{
  "line_id": "AAAA",
  "product": "AAEQ",
  "category": "BIN",
  "eds_step": "EDS_M",
  "date_range": {
    "start_date": "2026-06-01",
    "end_date": "2026-06-19",
    "time_column": "fab_track_out_time"
  },
  "target_time_column": "eds_tkout_time",
  "target_lag": {
    "expected_days": 60,
    "estimate_missing_recent": true
  },
  "fab_step": "EQ760200",
  "x_features": ["numeric|EQ760200|MT123456|METRO_ITEM_A|avg"],
  "y_targets": ["BIN0131"],
  "bins": 10,
  "category_feature": {
    "name": "PPID",
    "values": ["표준조건", "평가조건1"],
    "chart_mode": "multi_line"
  }
}
```

필요 응답:

```json
{
  "fab_step": "EQ760200",
  "combos": [
    {
      "x_feature": "numeric|EQ760200|MT123456|METRO_ITEM_A|avg",
      "x_feature_display_name": "METRO_ITEM_A / avg",
      "y_target": "BIN0131",
      "category": "BIN",
      "eds_step": "EDS_M",
      "category_feature_name": "PPID",
      "category_feature_value": "표준조건",
      "bins": [
        {
          "bin_left": 0.0,
          "bin_right": 1.0,
          "bin_center": 0.5,
          "y_avg": 10.2,
          "wafer_count": 12
        }
      ]
    }
  ]
}
```

#### POST `/api/timeseries`

요청:

```json
{
  "line_id": "AAAA",
  "product": "AAEQ",
  "category": "BIN",
  "eds_step": "EDS_M",
  "fab_step": "EQ760200",
  "date_range": {
    "start_date": "2026-06-01",
    "end_date": "2026-06-19",
    "time_column": "fab_track_out_time"
  },
  "target_time_column": "eds_tkout_time",
  "target_lag": {
    "expected_days": 60,
    "estimate_missing_recent": true,
    "estimate_frequency": "daily",
    "fit_method": "window_bin_avg"
  },
  "x_features": ["numeric|EQ760200|MT123456|METRO_ITEM_A|avg"],
  "y_targets": ["BIN0131"]
}
```

필요 응답:

```json
{
  "fab_step": "EQ760200",
  "time_basis": {
    "x_axis": "fab_track_out_time",
    "target_observed_time": "eds_tkout_time",
    "expected_target_lag_days": 60
  },
  "targets": [
    {
      "name": "BIN0131",
      "display_name": "BIN0131",
      "observed_points": [
        {
          "time": "2026-04-19T00:00:00",
          "value": 10.2,
          "value_status": "observed",
          "observed_time": "2026-06-18T00:00:00"
        }
      ],
      "estimated_points": [
        {
          "time": "2026-06-19T00:00:00",
          "value": 12.7,
          "value_status": "estimated",
          "fit_method": "window_bin_avg",
          "reference_range": ["2026-02-01", "2026-04-30"],
          "n_reference": 184
        }
      ],
      "fit_summary": {
        "method": "window_bin_avg",
        "formula_label": "historical window bin average",
        "reference_range": ["2026-02-01", "2026-04-30"],
        "n_reference": 184
      }
    }
  ],
  "features": [
    { "name": "numeric|EQ760200|MT123456|METRO_ITEM_A|avg", "display_name": "METRO_ITEM_A / avg", "points": [["2026-06-19T00:00:00", 1.5]] }
  ]
}
```

#### POST `/api/table`

필요 응답:

```json
{
  "rows": [
    {
      "fab_step": "EQ760200",
      "line_id": "AAAA",
      "product": "AAEQ",
      "category": "BIN",
      "eds_step": "EDS_M",
      "x_feature": "numeric|EQ760200|MT123456|METRO_ITEM_A|avg",
      "x_feature_display_name": "METRO_ITEM_A / avg",
      "x_value": 1.5,
      "y_target": "BIN0131",
      "y_value": 10.2,
      "value_status": "observed",
      "estimated_y_value": null,
      "fit_method": null,
      "metro_step": "MT123456",
      "metro_item": "METRO_ITEM_A",
      "metro_grade": "A",
      "metro_category": "VM",
      "category_feature_name": "PPID",
      "category_feature_value": "표준조건",
      "dc_lower": 1.0,
      "dc_upper": 5.0
    }
  ]
}
```

#### POST `/api/interaction`

목적:

- 선택된 feature 2개와 value 인자 기준으로 scatter, heatmap, ranking table 데이터를 생성한다.

요청:

```json
{
  "line_id": "AAAA",
  "product": "AAEQ",
  "category": "BIN",
  "eds_step": "EDS_M",
  "fab_step": "EQ760200",
  "date_range": {
    "start_date": "2026-06-01",
    "end_date": "2026-06-19",
    "time_column": "fab_track_out_time"
  },
  "target_time_column": "eds_tkout_time",
  "x_feature": "numeric|EQ760200|MT123456|METRO_ITEM_A|avg",
  "y_feature": "numeric|EQ760200|FD123456|TEMP_SENSOR_01|std",
  "value_field": "BIN0131",
  "aggregation": "average",
  "x_bins": 10,
  "y_bins": 10,
  "x_range": [0.0, 10.0],
  "y_range": [0.0, 5.0]
}
```

필요 응답:

```json
{
  "scatter_points": [
    { "x": 1.2, "y": 3.4, "value": 10.2 }
  ],
  "heatmap_cells": [
    {
      "x_bin": 0,
      "y_bin": 0,
      "x_bin_label": "0.0 - 1.0",
      "y_bin_label": "0.0 - 0.5",
      "value": 10.2,
      "count": 15
    }
  ],
  "rank_rows": [
    {
      "rank": 1,
      "x_bin_label": "0.0 - 1.0",
      "y_bin_label": "0.0 - 0.5",
      "aggregation": 10.2,
      "count": 15
    }
  ]
}
```

#### 7-1. 분석 레이어 계약 확장 (DS/UX 검토 반영, 신규)

`6-2`를 지원하기 위해 기존 응답에 아래 필드를 *추가형*으로 더한다(기존 필드·계산 로직은 유지). 회사 backend 동결 전에 함께 확정한다.

```text
GET /api/columns
  + units: { "<feature|target>": "<unit>" }            # 3장의 단위 표시 지원
  + min_n                                              # thin(신뢰 낮음) 판정 기준

GET /api/x-feature-options → features[]
  + score                                              # 영향도 정렬용 (예: |corr|)
  + unit

POST /api/binned → combos[].bins[]
  + y_std, y_sem                                       # 또는 y_ci_low / y_ci_high
POST /api/binned → combos[]
  + recommended_window { lower, upper, score }          # 최적 공정창 (옵션)
  + y_unit
POST /api/binned  (request)
  + selection { time_range?, wafer_ids? }              # linked brushing (옵션)

POST /api/timeseries
  + sampled (bool), n_total (int)                      # 다운샘플 메타
  + targets[].unit / features[].unit
  + targets[].avg / features[].avg                     # ★풀데이터 기준 서버 계산
  + targets[].control_limits { ucl, lcl, sigma }       # ★풀데이터 기준 서버 계산
  + time_basis { x_axis, target_observed_time, expected_target_lag_days }
  + targets[].observed_points[]                        # 실제 EDS Test 확보값
  + targets[].estimated_points[]                       # 최근 결측 구간의 일 단위 추정값
  + targets[].fit_summary { method, formula_label, reference_range, n_reference }

POST /api/table → rows[]
  + n, mean, std
  + cpk                                                # 또는 ppk
  + in_spec_pct, oos_count
  + value_status                                       # observed | estimated
  + estimated_y_value, fit_method                      # 추정값이 table/export에 섞일 때 명시
POST /api/table  (request)
  + selection { time_range?, wafer_ids? }              # linked brushing (옵션)

POST /api/interaction
  + heatmap_cells[].count(기존) → min_count 임계로 저카운트 셀 디엠퍼시스
  + rank_rows[].count(기존) + ci (옵션)
```

주의:

- 다운샘플 ↔ 통계 충돌: 시계열을 줄이면 클라이언트 계산 통계(avg·σ·이동평균·관리한계)가 편향되므로, 해당 값은 backend가 풀데이터로 계산해 내려준다.
- `min_n`은 `/api/columns`(또는 설정)에서 내려 UI `thin` 상태 기준으로 공유한다.
- 위 필드는 모두 *추가형*이라 비목표 "백엔드 계산 로직 전면 재작성"에 해당하지 않는다(동일 집계 패스에서 산출).

## 우선순위

### P0: 회사 데이터 연결 전 필수

- API base URL 설정 정리
- loading, empty, error 상태 분리
- Line_ID, 제품, Category, EDS_STEP, 기간, FAB_STEP, X_FEATURE, Y_TARGET 선택 UI disabled/validation 처리
- chart/table empty state 처리
- 현재 API 계약 문서화 및 확장 API 계약 초안 정리
- `fab_metro_prc` 기반 X feature matching 데이터 계약 정리
- (신규) 분석 레이어 계약 필드 동결: bins `y_std/y_sem`, table `n/cpk/in_spec_pct/oos_count`, timeseries `sampled/avg/control_limits`, columns `units/min_n`, x-feature `score` (`7-1` 참고)
- (신규) 시계열 y target 지연 대응 계약 동결: `time_basis`, `observed_points`, `estimated_points`, `fit_summary`, `value_status`
- (신규) `thin`(표본 부족·신뢰 낮음) 상태 정의 및 `min_n` 기준 확정

### P1: 실무 사용성 개선

- 전체 선택/해제
- 선택 조건 요약
- Y Target grouping
- Matching On/Off 및 Metro_Grade, Metro_Category 필터
- Category Feature chart mode
- chart tooltip 개선
- user spec / DC spec 범례
- table metadata 컬럼, 강조 표시와 CSV export
- (신규) 불확실성 band·표본 적은 bin 디엠퍼시스 (`6-2 A`)
- (신규) Cpk·in-spec%·OOS 표시 + 상단 KPI 밴드 (`6-2 B,H`)
- (신규) 색맹 안전 팔레트 + spec 선 dash/라벨 (`6-2 G`)
- (신규) 시계열 관리도·OOS 강조 (`6-2 C`)
- (신규) 최근 y target 결측 구간 추정 point 표시 (`3-2`)
- (신규) X feature 영향도순 정렬 (`6-2 E`)
- (신규) 시계열 다운샘플(LTTB) 표시 (`6-2 D`)

### P2: 추가 개선

- chart row 접기/펼치기
- 사용자가 선택한 조건 localStorage 저장
- 최근 조회 조건 불러오기
- 컬럼 단위 또는 설명 metadata 표시
- 분석 조건 preset 저장
- 교호작용 분석 scatter/heatmap/ranking table
- (신규) 교호작용 heatmap min-count 임계·저카운트 셀 디엠퍼시스 (`6-2 A`)
- (신규) 최적 process window 추천 band 오버레이 (`6-2 F`)
- (신규) Linked brushing: 시간구간 brush → 서버 필터 재집계 (`6-2 I`)
- (신규) provenance 줄 + URL 직렬화 공유 링크 (`6-2 J`)

## 비목표

이번 요청에서 하지 않을 일:

- 프론트엔드 프레임워크 변경
- 대규모 디자인 시스템 도입
- 인증/권한 구현
- 백엔드 계산 로직 전면 재작성
- 모바일 중심 반응형 재설계
- 복잡한 상태 관리 라이브러리 도입
- `fab_metro_prc` 원천 테이블 자체의 정합성 보정
- 회사 DB 접속 정보나 credential을 코드에 하드코딩

## 구현 시 주의사항

- 현재 컴포넌트 경계를 최대한 유지한다.
- API 호출은 `frontend/src/api/client.js` 밖으로 흩어지지 않게 한다.
- chart option은 각 chart 컴포넌트 내부에서 관리하되, 반복되는 포맷 함수는 필요할 때만 분리한다.
- CSS는 기존 `frontend/src/style.css`의 변수 체계를 우선 사용한다.
- 화면을 예쁘게 만드는 것보다 분석자가 데이터 상태를 정확히 이해하는 것을 우선한다.
- mock data에만 맞춘 하드코딩을 추가하지 않는다.
- 회사 backend schema가 확정되지 않은 항목은 UI mock과 API contract draft를 분리해서 작성한다.
- 선택 조건이 많아지므로 컴포넌트가 과도하게 커지면 `FilterPanel`, `TargetGroupingDialog`, `InteractionPanel`처럼 기능 단위로 분리한다.

## 크로스체크 메모

- `6-2 분석·의사결정 레이어`는 방향은 타당하지만 한 번에 구현하면 범위가 커진다.
- P0에서는 backend 계약 필드와 UI 상태 정의를 확정하는 데 집중한다.
- P1/P2에서 chart 표시, KPI, brushing, 추천 window 같은 실제 기능을 단계적으로 구현한다.
- 시계열 관련 시간 기준은 혼동되기 쉬우므로 다음처럼 분리한다.
  - `fab_track_out_time`: 시계열 x축 및 분석 기간의 기본 기준
  - `eds_tkout_time`: y target이 실제로 확보된 EDS Test 시점
- 최근 구간의 y target 추정값은 실제값이 아니라 의사결정 보조값이다. 모든 chart/table/export에서 `observed`와 `estimated`를 구분해야 한다.

## 현실성·효율성 리뷰 & 단계 실행 (M0–M2)

> 계획 전체를 현실성·효율성 관점에서 압박 테스트한 결과와 그에 따른 실행 단위. 위 우선순위(P0/P1/P2)를 *실행 단위*로 다시 자른 것이며, 충돌 시 이 절을 우선한다.

### 유지할 강점

- 추가형 계약 원칙, mock/contract 분리, 시간기준 분리(`fab_track_out_time` vs `eds_tkout_time`), `thin` 상태, 비목표 명시 — 그대로 유지.

### 현실성 리스크

- **R1. 추정 y-target(`3-2`)은 UI가 아니라 통계 방법론 결정이며 집계 오염 위험이 있다.**
  - `/api/binned` 요청의 estimate 플래그 + `bins[]`에 `value_status` 부재 → 추정 wafer가 binning·Cpk·in_spec·window에 섞일 수 있다.
  - 규칙: **binning·Cpk·window·KPI는 observed-only.** 추정은 시계열 오버레이 전용. 추정 생성 자체는 플래그 뒤 옵션(M2). M0에선 계약 슬롯만 둔다.
- **R2. 계약 "동결"의 주체는 회사 backend팀이다.** Claude Code 산출물은 "계약 draft + 동형 demo backend + 소비 frontend" = 제안서다. Cpk·control_limits는 demo에선 싸지만 회사 스케일에선 캐싱/사전집계가 필요 → 프론트는 "있으면 그리고 없으면 graceful".
- **R3. "차트 작성" 한 번의 combo fan-out이 스케일 절벽.** 5 feature × 3 target × (category 4분할) = 60 combo를 단일 동기 POST로 받으면 전부 블로킹. → combo 단위 progressive 로딩 + loading/thin을 combo별로.
- **R4. category split × 다중 조합 = 무제한 폭발.** 요청당 max combo·렌더 category 값 하드 캡 + 초과 안내.
- **R5. lag 때문에 "최근 구간" window 분석은 구조적으로 빈다.** observed-only이므로 최근 N일은 window/Cpk가 비어 보임 → "window는 ~N일 이전 기준"을 `time_basis`/provenance로 명시.

### 효율성 / 스코프

- **E1. "제공 필드 렌더(싼 것)"와 "신규 인터랙션(비싼 것)"을 분리.** 싼 것(Cpk/CI band/범례/tooltip/영향도 정렬/units)은 앞에서 빠르게, 비싼 것(brushing/interaction/추정/grouped 영속화/window 추천)은 뒤로.
- **E2. 색맹 팔레트/토큰을 맨 먼저** — 모든 series가 상속하므로 나중에 하면 전 차트 재작업.
- **E3. 차트 컴포넌트 편집은 1패스로 배칭**(legend·tooltip·CI band·spec dash·empty/thin).
- **E4. `/api/y-target-groups`(stateful)는 v1 과설계 → 인라인(stateless)로.** 그룹 정의는 요청에 동봉, 보유는 클라(P2 localStorage).
- **E5. 계약 동형 demo 데이터 생성기는 숨은 작업량** → 명시적 산출물로 잡는다.

### 계약 잔손질

- `/api/binned`는 observed-only(estimate 플래그 제거, 필요시 `n_observed`만).
- `units`(columns) vs `unit`(x-feature/timeseries) → feature/target별 `unit` 하나로 통일.
- interaction `value`(heatmap) vs `aggregation`(rank) 네이밍 정합.
- `scatter_points`도 샘플링/최대 점수 캡(timeseries와 동일 원칙).
- combo/category 하드 캡을 columns(또는 설정)로 노출해 프론트·백 공유.

### 단계 실행 (M0–M2)

| 단계 | 내용 | 목적 |
|---|---|---|
| **M0** (≈ 진짜 P0) | env/baseURL · 상태머신(loading/empty/error/`thin` + 중복요청 방지) · 신규 조건필터(line/product/category/eds_step/기간)+validation/disabled · 계약 draft 확정(분석·추정 슬롯 포함) · 계약 동형 demo backend · 빈/에러 state. 차트 렌더는 안 깨지게만 | 백엔드 핸드셰이크 de-risk |
| **M1** (싼 P1) | 팔레트 먼저 → 차트 1패스(legend·tooltip·CI band·spec dash·empty/thin) · 테이블 Cpk/in-spec/OOS/n · KPI 밴드 · 영향도 정렬 · 다운샘플 표시 | 제공 필드 렌더로 즉시 가치 |
| **M2** (비싼 P1+P2) | matching 풀세트 · category mode(캡) · grouped target(인라인) · interaction panel · 추정값(플래그) · linked brushing · recommended window · provenance/URL | 인터랙션·방법론은 마지막 |

핵심 재배치: 추정값 렌더 → M2, 색맹 팔레트 → M1 맨 앞, 차트 편집 배칭, grouped target 인라인.

## Claude Code 작업 요청 양식

아래 양식을 복사해서 작업 단위별로 채워 넣는다.

```markdown
# UI 개선 요청

## 목표
- 

## 현재 문제
- 

## 원하는 동작
- 

## 관련 파일
- `frontend/src/App.vue`
- `frontend/src/components/...`
- `frontend/src/api/client.js`

## 백엔드 데이터 전제
- endpoint:
- request:
- response:
- 빈 데이터일 때:
- 에러일 때:

## UI 요구사항
- 

## 완료 조건
- 

## 하지 말아야 할 것
- 

## 검증 방법
- `cd frontend && npm run build`
- 브라우저에서 주요 상태 확인:
  - 초기 상태
  - loading 상태
  - 정상 데이터 상태
  - 빈 데이터 상태
  - 에러 상태
```

## 예시 요청 1: API 연결 준비

```markdown
# UI 개선 요청

## 목표
회사 백엔드로 API를 교체해도 프론트엔드 수정 범위가 작도록 API client와 화면 상태 처리를 정리한다.

## 현재 문제
- API base URL이 `/api`로 고정되어 있다.
- 백엔드 연결 실패 메시지가 단일 문자열로만 처리된다.
- 빈 응답과 에러 응답의 UI가 구분되지 않는다.

## 원하는 동작
- 개발 환경에서는 Vite proxy를 사용한다.
- 운영 환경에서는 환경변수로 API base URL을 바꿀 수 있다.
- API 실패, 빈 데이터, 잘못된 응답을 구분해 사용자에게 보여준다.

## 관련 파일
- `frontend/src/api/client.js`
- `frontend/src/App.vue`
- 필요한 경우 chart/table 컴포넌트

## 백엔드 데이터 전제
- 기존 `backend/schemas.py`의 응답 구조를 유지한다.

## 완료 조건
- API base URL 설정 위치가 명확하다.
- 백엔드가 꺼져 있을 때 안내 메시지가 보인다.
- 빈 chart/table 데이터가 와도 화면이 깨지지 않는다.

## 하지 말아야 할 것
- 백엔드 계산 로직을 바꾸지 않는다.
- 새로운 상태 관리 라이브러리를 추가하지 않는다.

## 검증 방법
- `cd frontend && npm run build`
- 백엔드를 켠 상태와 끈 상태를 각각 확인한다.
```

## 예시 요청 2: 분석 조건 선택 UI 개선

```markdown
# UI 개선 요청

## 목표
Line_ID, 제품, Category, EDS_STEP, 기간, FAB_STEP, X_FEATURE, Y_TARGET을 업무 순서에 맞게 선택할 수 있는 조건 패널을 만든다.

## 현재 문제
- 현재 선택 UI는 Y target, X feature, fab_step 중심이다.
- 회사 데이터에서는 Line_ID, 제품, Category, EDS_STEP, 기간 조건이 먼저 필요하다.
- X feature는 fab_metro_prc 기준 matching 필터가 필요하다.

## 원하는 동작
- 최상단에 Line_ID와 제품 선택 섹션을 추가한다.
- Y_Target 위에 Category, EDS_STEP, 기간 선택 섹션을 추가한다.
- X_FEATURE는 선택된 FAB_STEP과 fab_metro_prc 매칭된 metro item을 기본 표시한다.
- Matching Off 토글, Metro_Grade 필터, Metro_Category 필터를 제공한다.
- Matching on/off 전환 시 기존 체크 항목은 유지한다.
- 필수 선택값이 없으면 `차트 작성` 버튼을 disabled 처리한다.

## 관련 파일
- `frontend/src/components/Sidebar.vue`
- `frontend/src/App.vue`
- `frontend/src/api/client.js`

## 완료 조건
- 사용자가 현재 line, 제품, category, EDS step, 기간, fab step, feature, target 조건을 확인할 수 있다.
- 선택값이 없거나 불완전할 때 API 요청이 발생하지 않는다.
- Matching Off를 켰다가 꺼도 기존 선택 X feature가 reset되지 않는다.

## 하지 말아야 할 것
- 라우팅을 추가하지 않는다.
- 화면 전체 레이아웃을 크게 바꾸지 않는다.

## 검증 방법
- `cd frontend && npm run build`
- 필수 선택 없음, 일부 선택, 전체 선택, matching on/off 전환 상태를 확인한다.
```

## 예시 요청 3: Chart 해석성 개선

```markdown
# UI 개선 요청

## 목표
분석자가 chart의 선, 색상, 값의 의미를 빠르게 이해할 수 있게 한다.

## 현재 문제
- user spec과 DC spec 선의 의미가 chart 내부에서 충분히 설명되지 않는다.
- tooltip이 분석 업무에 필요한 값 중심으로 정리되어 있지 않다.
- 데이터가 없는 조합의 표시 정책이 약하다.

## 원하는 동작
- user spec과 DC spec 범례를 표시한다.
- window chart tooltip에 bin range, wafer count, y average를 표시한다.
- time series chart tooltip에 시간, target 값, feature 값을 읽기 쉽게 표시한다.
- 데이터가 없는 경우 chart 대신 empty state를 보여준다.

## 관련 파일
- `frontend/src/components/WindowChart.vue`
- `frontend/src/components/ComboTimeSeries.vue`
- `frontend/src/components/ComboRow.vue`

## 완료 조건
- 처음 보는 사용자도 chart 선의 의미를 알 수 있다.
- 빈 데이터에서도 chart가 깨지지 않는다.

## 하지 말아야 할 것
- ECharts 외의 chart library를 추가하지 않는다.

## 검증 방법
- `cd frontend && npm run build`
- 정상 데이터, 빈 bins, 빈 timeseries를 각각 확인한다.
```

## 예시 요청 4: Y Target Grouping

```markdown
# UI 개선 요청

## 목표
여러 Y target을 선택해 합산 target을 만들고, 이를 일반 Y target처럼 분석에 사용할 수 있게 한다.

## 현재 문제
- Y target은 원본 컬럼만 선택할 수 있다.
- BIN0131, BIN0153처럼 여러 target을 합산해 보고 싶은 경우 별도 target으로 다룰 수 없다.

## 원하는 동작
- Y_Target 목록에서 여러 항목을 체크한다.
- `Grouping` 버튼을 누르면 새 target 이름을 입력하는 modal/dialog를 연다.
- aggregation 방식은 우선 `sum`으로 한다.
- 생성된 grouped target은 Y_Target 목록에 추가된다.
- grouped target의 원본 source targets를 UI에서 확인할 수 있다.
- 같은 이름이 있을 때 overwrite, rename, cancel 중 하나를 선택하게 한다.

## 관련 파일
- `frontend/src/components/Sidebar.vue`
- `frontend/src/App.vue`
- `frontend/src/api/client.js`
- 필요하면 `TargetGroupingDialog.vue` 신규 생성

## 백엔드 데이터 전제
- `POST /api/y-target-groups`
- request: `{ name, source_targets, aggregation }`
- response: `{ name, source_targets, aggregation, created }`

## 완료 조건
- BIN0131, BIN0153을 선택해 `BIN0131_0153_SUM` target을 만들 수 있다.
- grouped target을 선택해 chart/table 요청에 포함할 수 있다.
- grouped target과 원본 target을 시각적으로 구분할 수 있다.

## 하지 말아야 할 것
- 프론트엔드에서 실제 대용량 target 값을 직접 계산하지 않는다.
- grouping 정보를 local mock에만 저장해 회사 backend 연결이 어렵게 만들지 않는다.

## 검증 방법
- `cd frontend && npm run build`
- target 1개 선택, 여러 개 선택, 중복 이름 입력, grouping 취소 상태를 확인한다.
```

## 예시 요청 5: Category Feature Chart Mode

```markdown
# UI 개선 요청

## 목표
ECO, PPID, EQP_MODEL, EQP, EQP_CH 같은 Category Feature 기준으로 chart를 비교할 수 있게 한다.

## 현재 문제
- Window chart의 y_avg line은 단일 series 중심이다.
- Category Feature별 차이를 하나의 chart에서 비교하거나, feature 값별 chart로 나누어 볼 수 없다.

## 원하는 동작
- Category Feature 선택 UI를 추가한다.
- chart mode를 `multi-line`과 `split-chart` 중 선택할 수 있게 한다.
- multi-line 모드에서는 Category Feature 값별 y_avg line을 한 chart에 표시하고 legend로 구분한다.
- split-chart 모드에서는 Category Feature 값별로 chart를 나누어 표시한다.
- 표시할 Category Feature 값은 legend 또는 별도 선택 UI로 일부만 선택 가능해야 한다.

## 관련 파일
- `frontend/src/components/WindowChart.vue`
- `frontend/src/components/ComboTimeSeries.vue`
- `frontend/src/components/ComboRow.vue`
- `frontend/src/App.vue`

## 백엔드 데이터 전제
- `/api/binned`와 `/api/timeseries` 응답에 `category_feature_name`, `category_feature_value` 또는 category series 구분자가 포함된다.

## 완료 조건
- PPID 기준으로 `표준조건`, `평가조건1`, `평가조건2`를 legend로 구분해 볼 수 있다.
- multi-line과 split-chart 모드를 전환할 수 있다.
- 표시하지 않을 Category Feature 값을 숨길 수 있다.

## 하지 말아야 할 것
- chart library를 바꾸지 않는다.
- 모든 category value를 강제로 표시해 chart를 읽기 어렵게 만들지 않는다.

## 검증 방법
- `cd frontend && npm run build`
- category value 1개, 여러 개, 빈 category value 상태를 확인한다.
```

## 예시 요청 6: 교호작용 분석 영역

```markdown
# UI 개선 요청

## 목표
차트 작성에 사용된 X features와 Y target 중 2개 feature를 선택해 scatter/heatmap/ranking table로 교호작용을 분석한다.

## 현재 문제
- 현재 화면은 feature와 target 각각의 window/time series 분석 중심이다.
- 두 feature 조합이 target 또는 value에 미치는 영향을 보기 어렵다.

## 원하는 동작
- 별도 `교호작용 분석` 영역을 추가한다.
- 분석 대상 feature 2개와 value field를 선택한다.
- aggregation은 average와 median을 선택할 수 있게 한다.
- scatter chart와 heatmap chart를 제공한다.
- heatmap의 x/y bin 개수와 x/y scale range를 조정할 수 있게 한다.
- feature 조합별 aggregation 결과를 rank table로 보여준다.

## 관련 파일
- `frontend/src/App.vue`
- `frontend/src/api/client.js`
- 신규 컴포넌트 후보:
  - `InteractionPanel.vue`
  - `InteractionScatter.vue`
  - `InteractionHeatmap.vue`
  - `InteractionRankTable.vue`

## 백엔드 데이터 전제
- `POST /api/interaction`
- request: `{ x_feature, y_feature, value_field, aggregation, x_bins, y_bins, x_range, y_range, ...filters }`
- response: `{ scatter_points, heatmap_cells, rank_rows }`

## 완료 조건
- feature 2개를 선택하면 scatter와 heatmap이 표시된다.
- x/y bin 개수 변경이 heatmap에 반영된다.
- average/median 전환이 rank table과 heatmap에 반영된다.

## 하지 말아야 할 것
- 전체 raw data를 프론트엔드로 내려받아 무거운 aggregation을 브라우저에서 수행하지 않는다.
- 기존 window chart 영역과 과도하게 섞어 정보 구조를 흐리지 않는다.

## 검증 방법
- `cd frontend && npm run build`
- feature 미선택, feature 1개 선택, feature 2개 선택, 빈 interaction 결과 상태를 확인한다.
```

## 예시 요청 7: 시계열 Y Target 지연 구간 추정 표시

```markdown
# UI 개선 요청

## 목표
FAB step track_out_time 기준 최근 구간에서 y target 실측값이 아직 확보되지 않은 경우, 간단한 통계식 기반 추정값을 실제값과 구분해 시계열 차트에 표시한다.

## 현재 문제
- 시계열 x축은 fab_step의 track_out_time 기준이다.
- y target은 EDS Test를 통해 약 2개월 뒤 확보되는 경우가 많다.
- 최근 기간에는 x feature 값은 있지만 y target 값이 없어 시계열이 끊기거나 현업 판단 보조 정보가 부족하다.

## 원하는 동작
- `/api/timeseries` 응답에서 y target을 `observed_points`와 `estimated_points`로 분리한다.
- 추정값은 최근 결측 구간에 대해 날짜별 1 point만 표시한다.
- 추정 방식은 backend가 제공하는 단순 통계식으로 한다.
  - 예: `window_bin_avg`, `linear_fit`
- estimated point는 실제 scatter point와 다르게 표현한다.
  - 낮은 opacity
  - hollow marker 또는 dashed border
  - tooltip에 `estimated` 표시
  - legend에서 observed/estimated 분리
- 추정값은 table/export/KPI에 포함될 경우 `value_status=estimated`를 표시한다.

## 관련 파일
- `frontend/src/components/ComboTimeSeries.vue`
- `frontend/src/components/DataTable.vue`
- `frontend/src/api/client.js`
- 필요하면 `frontend/src/App.vue`

## 백엔드 데이터 전제
- `POST /api/timeseries`
- request: `{ date_range.time_column="fab_track_out_time", target_time_column="eds_tkout_time", target_lag, x_features, y_targets }`
- response: `{ time_basis, targets[].observed_points, targets[].estimated_points, targets[].fit_summary }`

## 완료 조건
- 최근 y target 결측 구간에 estimated point가 날짜별 1개씩 표시된다.
- observed point와 estimated point가 시각적으로 명확히 구분된다.
- tooltip에서 fit method, reference range, n_reference를 확인할 수 있다.
- estimated point를 실제 EDS 결과로 오해하지 않도록 보조 라벨이 표시된다.

## 하지 말아야 할 것
- 추정값을 실제 y target 값과 같은 series로 섞지 않는다.
- 복잡한 ML 모델이나 설명하기 어려운 fitting을 v1에 넣지 않는다.
- 프론트엔드에서 대용량 raw data를 직접 받아 fitting하지 않는다.

## 검증 방법
- `cd frontend && npm run build`
- observed만 있는 기간, observed+estimated가 섞인 기간, estimated만 있는 최근 기간을 확인한다.
```

## Claude Code에 맡기기 전 체크리스트

- [ ] 이번 요청의 목표가 한 문장으로 명확한가?
- [ ] 현재 문제가 실제 화면 기준으로 설명되어 있는가?
- [ ] 관련 파일을 지정했는가?
- [ ] 백엔드 데이터 전제가 적혀 있는가?
- [ ] 회사 데이터 컬럼명과 예시 값이 들어 있는가?
- [ ] filter 조건과 chart/table 응답 계약이 분리되어 있는가?
- [ ] 완료 조건이 검증 가능하게 적혀 있는가?
- [ ] 하지 말아야 할 범위가 적혀 있는가?
- [ ] `npm run build` 같은 검증 방법이 포함되어 있는가?

## 추천 작업 순서

1. API 연결 준비와 상태 처리 (+ `7-1` 분석 레이어 계약 필드 동결, `thin` 상태 추가)
2. Line_ID, 제품, Category, EDS_STEP, 기간 선택 UI
3. FAB_STEP 기반 X feature matching과 metro metadata 필터
4. Y Target grouping
5. Category Feature chart mode
6. 시계열 y target 지연 구간 추정 표시
7. summary table metadata 컬럼
8. chart tooltip, legend, empty state 마감
9. 교호작용 분석 scatter/heatmap/ranking table
10. CSV export, preset 저장 같은 편의 기능

이 순서로 진행하면 회사 백엔드 연결 시 가장 위험한 부분부터 줄일 수 있다.
