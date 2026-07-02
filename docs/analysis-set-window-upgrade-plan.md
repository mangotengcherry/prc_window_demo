# 분석 물량 선정 UI 개편 + Window 분석 고도화 — 구현 계획서

> **실행자**: Claude Sonnet (ultra hard). 이 문서만 읽고 구현 가능하도록 작성됨.
> **작성일**: 2026-07-02
> **대상 앱**: 현재 워크벤치 앱 (`frontend/src/main.ts` + `backend/app/`) — 구버전 대시보드가 아님 (아래 §1.3 참고)

---

## 0. 실행자 필수 지침

1. **CLAUDE.md 준수**: 수술적 변경, 요청 외 리팩터 금지, 기존 스타일 유지.
2. **Phase 순서대로 구현**하고, Phase마다 커밋한다. 커밋 전 검증 명령을 반드시 통과시킨다:
   ```bash
   python3 -m pytest backend/tests -q
   cd frontend && npm test && npm run build
   ```
3. **레거시 파일 금지 구역**: 이 저장소에는 구버전 대시보드가 공존한다. 진입점은 `frontend/src/main.ts`와 `backend/app/main.py`다.
   - 수정 금지(구버전 전용): `backend/main.py`, `backend/analytics.py`, `backend/data.py`, `backend/data_source.py`, `backend/schemas.py`, `backend/validate_data.py`, `frontend/src/main.js`, `frontend/src/api/client.js`, `frontend/src/components/Sidebar.vue`, `ComboRow.vue`, `WindowChart.vue`, `ComboTimeSeries.vue`, `DataTable.vue`, `InteractionScatter.vue`, `InteractionPanel.vue`, `TargetGroupingDialog.vue`, `frontend/src/components/InteractionHeatmap.vue`(루트에 있는 것; `components/charts/InteractionHeatmap.vue`는 현행 앱), `frontend/src/echarts.js`, `stats.js`, `share.js`
   - 루트 레벨 src 파일을 수정하기 전에 `main.ts`에서의 import 체인으로 도달 가능한지 확인할 것. (`guideContent.js`, `workbenchSummary.js`, `palette.js`는 확인 후 판단 — `palette.js`는 수정하지 말고 §9의 `palette.ts`를 신규 작성)
4. 모호한 부분이 나오면 §2의 "확정된 가정"을 우선 적용하고, 그래도 불명확하면 구현을 멈추고 질문한다.

---

## 1. 배경

### 1.1 목표

1. **분석대상 물량 선정(Analysis Set) 화면 전면 개편**
   - FAB 진행 이력 기반 + EDS 아이템 기반 2단 선택 구조
   - FAB 조건은 **최대 3개 공정을 join**(교집합) — 한 공정 조건이 완성되면 추가 공정 조건을 이어서 설정 가능
   - **커스텀 EDS 아이템**: 여러 아이템을 +/−로 합성해 직접 타이핑한 이름으로 저장, 전 사용자 공유
   - 선택 조건을 **개인용 Preset으로 저장**하고 **공유용으로 전환** 가능
   - 공정 변경에 따른 **Revision 이력 관리**: 폴더 트리(최상위 = 공정 모듈 `Ch.Hole`, `WLCUT` / 하위 = `Mask Rev1`, `ETCH Rev0`, `ETCH Rev1` 형태의 조건 노드)
   - 선택 완료 시 **시계열 scatter 미리보기**(x축 FAB/EDS 시각 선택, y축 EDS 값) + 인터랙티브 legend/필터/파생 컬럼
2. **Window 분석(Window Review) 메뉴의 탭별 기능 고도화** — YE(수율 향상) 담당자 관점의 인사이트 차트/기법 추가 (§8)

### 1.2 현행 구조 요약 (탐색 완료된 사실)

**Frontend** (Vue 3.5 + Element Plus 2.11 + Plotly.js + Pinia + vue-router, axios `/api` proxy):

| 파일 | 역할 |
|---|---|
| `frontend/src/views/AnalysisSetView.vue` | 현행 물량 선정 화면. 2컬럼: 좌=필터 폼(기간/Product/Layer/Step/Parameter/Tool/PPID/EDS상태/제외토글), 우=저장된 Set 테이블+요약 |
| `frontend/src/stores/analysisSetStore.ts` | `metadata`, `analysisSets[]`, `selectedAnalysisSetId`, `defaultFilters()` |
| `frontend/src/api/analysisApi.ts` | 전 API 함수 집합 (axios) |
| `frontend/src/views/WindowReviewView.vue` | 9개 탭: 요약/Raw Scatter/Binned Response/Trade-off/Time Trend/Condition Split/Zone View/Interaction/제외 Rule |
| `frontend/src/components/charts/*.vue` | `PlotlyChart`(공통 래퍼, `point-click`·`points-selected` emit), `RawScatterChart`, `BinnedResponseChart`, `TradeoffChart`, `TimeTrendChart`, `ZoneViewChart`, `InteractionHeatmap` |
| `frontend/src/components/common/FilterPanel.vue` | `title`/`subtitle` props + default/`#actions` slot |
| `frontend/src/App.vue` | 워크벤치 셸: 좌측 252px 네비 + 74px 톱바 |
| `frontend/src/style.css` | 라이트 테마 (#eef2f6 배경, #2563eb 프라이머리, Inter 폰트) |

**Backend** (FastAPI + pandas, in-memory `MockStore`):

| 파일 | 역할 |
|---|---|
| `backend/app/data/mock_store.py` | dataclass 저장소: `wafer_data`(DataFrame), `analysis_sets`/`bin_groups`/`condition_rules`/`exclusion_rules`/`analysis_runs`(dict), `next_id(kind, prefix)` → "AS001" 형식 |
| `backend/app/services/mock_data_service.py` | 220 lot × 10~22 wafer 생성. 컬럼: `lot_id, wafer_id, product(DRAM_A/B, NAND_C), layer, step(ETCH_CONTACT 등 3종), process_date, expected_eds_date, eds_status(actual/pending), tool_id(T01~06), chamber_id(C1~4), ppid(PPID_A/B/C), eco_number, recipe_version, pm_age, part_modification_flag, zone, metro_ch_hole_cd, metro_thickness, metro_uniformity, fdc_temp_mean, fdc_pressure_mean, fdc_flow_mean, fdc_rf_power_mean, yield, is_rework, is_engineering_lot, is_abnormal_route` + `BIN_001~BIN_600`(fail ratio 0~1) |
| `backend/app/services/analysis_set_service.py` | `apply_filters()`, `summarize_filters()`, `create_analysis_set()` |
| `backend/app/services/window_analysis_service.py` | window-review 번들 계산: scatter(1400 샘플링)/binned(quantile)/tradeoff/trend/zone/interaction(5×5 qcut)/decision candidates/제외 before-after |
| `backend/app/models/schemas.py` | `AnalysisSetFilters`(flat), `AnalysisSetCreate`, `WindowReviewRequest`, `ExclusionRuleCreate` 등 |

**핵심 격차** (이번 작업의 이유):
- 개인/공유 Preset, 폴더/Revision 개념 없음 (Analysis Set 저장은 flat 목록뿐)
- FAB/EDS 2단 선택 구조 없음 — EDS_STEP/EDS_Category/EDS_ITEM/part_id/테스트기간 필드 자체가 없음
- Spotfire/SQL 필터식 없음
- 선정 단계 미리보기 차트 없음 (Window Review로 넘어가야 처음 차트를 봄)
- 데이터가 서버 재시작 시 전부 소실 (Preset은 살아남아야 함)

### 1.3 두 저장 개념의 구분 (설계 핵심)

| 개념 | 의미 | 저장소 | 생존 |
|---|---|---|---|
| **Preset** (조건 라이브러리) | 재사용 가능한 *검색 조건* 묶음. 폴더/Revision/개인·공유 관리 대상 | JSON 파일 (신규 `preset_store.json`) | 서버 재시작에도 유지 |
| **Analysis Set** (물량 스냅샷) | 조건을 *실행*해 확정한 wafer 모집단. Window Review·Pending 예측의 입력 | 기존 in-memory `MockStore` | 세션 한정 (기존 동작 유지) |

Preset을 불러와 → 폼 채움 → 조회/미리보기 → "Analysis Set 저장"으로 스냅샷 생성. 이 구분을 UI 문구에도 반영한다.

---

## 2. 확정된 가정 (구현 전 사용자 재확인 불필요 — 이미 요구사항에서 도출)

| # | 가정 | 근거 |
|---|---|---|
| A1 | Mock 제품명을 `KCAI`, `PPCR`, `QSGB`로, FAB STEP을 `CR380020` 형식 코드로 교체한다 | 사용자가 예시로 제시 (KCAI/PPCR, CR380020/CR860200) |
| A2 | 공정 모듈은 `Ch.Hole`, `WLCUT` 2개로 시작하고 FAB STEP을 모듈에 귀속시킨다 | 사용자 폴더 예시 |
| A3 | 인증이 없으므로 사용자 식별은 프론트 localStorage의 표시 이름(기본 `"me"`)을 `X-User` 헤더로 전달하는 목업으로 처리한다 | 프로토타입 범위. README "인증 미포함" |
| A4 | EDS 값의 long-format 테이블을 통째로 만들지 않는다. wafer-wide BIN/MSR 컬럼에서 **요청된 아이템만 on-demand melt** + part/step 오프셋은 해시 시드 기반 파생으로 계산한다 | 4,000 wafer × 4 step × 640 item × 4 part 사전 생성은 낭비 |
| A5 | BIN 아이템 내부명은 기존 `BIN_001` 형식을 유지한다 (기본 BIN Group·H2H_BINS 등 참조 존재). UI 표기만 `BIN001`로 정규화하지 않는다 | 수술적 변경 원칙 |
| A6 | 필터식은 Spotfire 스타일(`[PPID] != "TT_TEST"`, `case when ... then ... else ... end`)과 SQL 스타일(브래킷 없는 컬럼명, `<>`)을 **하나의 문법**으로 함께 수용한다 | "sql or spotfire 문법" 요구 |
| A7 | 필터식 실행은 자체 파서 → pandas 벡터 연산으로 한다. `eval()`/`df.query()` 직접 호출 금지 (임의 코드 실행 방지, 명확한 에러 메시지) | 안전성 |
| A8 | Revision은 불변(immutable)이다. 같은 Preset에 저장하면 rev+1이 생성되고 과거 rev는 읽기 전용으로 불러오기/복제만 가능 | "이력 관리" 요구의 표준 해석 |
| A9 | 공유 전환은 단방향 토글이 아닌 양방향(`personal ↔ shared`)으로 하되, 공유 Preset은 소유자만 수정(새 rev)·삭제 가능하고 타인은 불러오기/복제만 가능 | 일반적 협업 규칙 |
| A10 | 다공정 join을 위해 **wafer×step long-format `fab_history` 테이블을 신규 생성**한다(모든 wafer가 5개 스텝 전부 통과). 기존 `wafer_data`의 flat 컬럼은 "대표 분석 step" 값으로 유지되어 Window Review 등 기존 화면 호환 | 스텝별 이력 없이 다공정 join 불가 |
| A11 | join 블록 1개 = 공정 1개(단일 선택), 최대 3개, 블록 간 AND(교집합). 블록마다 자체 진행기간·필터식을 가진다 | "2-3개 공정의 진행 조건을 join" 요구 |
| A12 | 커스텀 EDS 아이템은 같은 category끼리만 합성(BIN±BIN, MSR±MSR — 스케일이 달라 혼합 무의미), 생성 즉시 전체 공유, 삭제는 생성자만 | "다른 사람들도 사용" 요구 + 단순화 |

---

## 3. 목표 UX — Analysis Set 화면 (새 레이아웃)

```
┌────────────┬──────────────────────────────────────────┬──────────────────────────┐
│ 조건        │  ① FAB 진행 이력 기반          [접기]     │  선정 물량 요약            │
│ 라이브러리  │  ┌────────────────────────────────────┐  │  Lot 128 · Wafer 2,410   │
│            │  │ 제품명   [KCAI ▾]  [PPCR ▾]        │  │  EDS 매칭 2,180 (90.5%)  │
│ [내 조건]  │  │ 공정 1 [CR380020 ▾]  (기준공정 ●)  │  ├──────────────────────────┤
│ [공유]     │  │ 진행기간 [2026-01-01 ~ 2026-06-19] │  │  시계열 Scatter 미리보기   │
│            │  │ FAB 필터식 (Spotfire)              │  │  x축 (FAB시각|EDS시각)     │
│ ▾ Ch.Hole  │  │ ┌────────────────────────────────┐ │  │  legend [tool_id ▾]      │
│   Mask R1  │  │ │ [PPID] != "TT_TEST"        ✓유효│ │  │  ┌────────────────────┐  │
│   ETCH R0  │  │ └────────────────────────────────┘ │  │  │  · ·· ·   ····  ·  │  │
│   ETCH R1  │  └────────────────────────────────────┘  │  │  ·· scatter (plotly)│  │
│ ▾ WLCUT    │  ② EDS 아이템 기반              [접기]    │  │  └────────────────────┘  │
│   Mask R0  │  ┌────────────────────────────────────┐  │  필터 칩: [zone='edge' ×] │
│            │  │ EDS_STEP [M ▾]  Category [BIN ▾]   │  │  [+ 필터] [+ 파생 컬럼]    │
│ [+ 폴더]   │  │ EDS_ITEM [BIN_014 ▾] (검색)        │  ├──────────────────────────┤
│            │  │ 테스트기간 [ ~ ]   part_id [All ▾] │  │ [Preset으로 저장(Rev)]    │
│            │  │ EDS 필터식 (SQL/Spotfire)          │  │ [Analysis Set 저장]       │
│            │  └────────────────────────────────────┘  │                          │
│            │  [물량 조회 →]                           │                          │
└────────────┴──────────────────────────────────────────┴──────────────────────────┘
```

- **FAB 섹션은 "공정 조건 블록" 카드가 쌓이는 구조** (위 그림은 블록 1개만 그린 것): 블록 = 공정 선택(모듈별 그룹) + 진행기간 + FAB 필터식. 현재 블록이 유효해지면 하단에 `[+ 다른 공정 조건 추가 (join)]` 버튼이 활성화되어 다음 공정 조건을 이어서 설정 — "물어보는" UX를 모달 대신 인라인 버튼으로 구현(흐름 차단 없음). 최대 3개, 블록 간 AND(교집합), 각 블록 우측 `×`로 제거. 첫 블록이 기본 "기준 공정"(미리보기 FAB 시각의 기준)이며 블록 헤더의 라디오로 변경 가능.
- **EDS_ITEM 목록에는 `커스텀` 그룹**이 있고 `[+ 커스텀 아이템]` 버튼으로 여러 아이템을 +/− 합성한 아이템을 생성한다(§8.1).
- 좌측 트리 노드 표기: 폴더 = 공정 모듈(`Ch.Hole`), 자식 = `"{preset명} Rev{n}"` (예: `ETCH Rev1`). 자식 노드 클릭 → 조건 로드. 컨텍스트 메뉴(우클릭 or `⋮`): 불러오기 / 이 조건으로 새 Rev 저장 / 복제 / 공유 전환(소유자만) / 이름 변경 / 삭제(소유자만).
- 로드 시 상단에 배지: `Ch.Hole / ETCH Rev1 불러옴 (2026-06-20, "recipe 변경 반영")`. 폼 수정 시 배지가 `수정됨 *`으로 변함.
- `물량 조회` 버튼: FAB 섹션 필수값(제품/STEP/기간) 없으면 disabled + 사유 tooltip. 클릭 → 미리보기 API 호출.
- 1366px 화면에서는 우측 패널이 하단으로 내려가는 2단 반응 레이아웃 (`grid-template-columns` 미디어쿼리 1개로 처리, 모바일 대응은 비목표).

---

## 4. Phase 0 — Mock 데이터·메타데이터 확장 (backend)

**파일**: `backend/app/services/mock_data_service.py`, `backend/app/core/config.py`(상수 있으면), 관련 테스트

### 4.1 이름 체계 교체

| 항목 | 기존 | 변경 |
|---|---|---|
| products | `DRAM_A`(46%), `DRAM_B`(34%), `NAND_C`(20%) | `KCAI`(46%), `PPCR`(34%), `QSGB`(20%) |
| step | `ETCH_CONTACT`(60%), `CLEAN_POST_ETCH`(24%), `CMP_OXIDE`(16%) | `CR860200`(60%), `CR860400`(24%), `WL560300`(16%) |
| (신규) 공정 모듈 매핑 | 없음 | 아래 `PROCESS_MODULES` 상수 |

```python
PROCESS_MODULES = {
    "Ch.Hole": [
        {"step_id": "CR380020", "label": "Ch.Hole Mask"},
        {"step_id": "CR860200", "label": "Ch.Hole ETCH"},
        {"step_id": "CR860400", "label": "Ch.Hole Clean"},
    ],
    "WLCUT": [
        {"step_id": "WL240100", "label": "WLCUT Mask"},
        {"step_id": "WL560300", "label": "WLCUT ETCH"},
    ],
}
```

wafer의 `step` 분포는 `CR860200` 60% / `CR860400` 16% / `WL560300` 16% / `CR380020` 5% / `WL240100` 3%처럼 5개 스텝 전체에 걸치도록 조정 (합 100%).

`layer` 컬럼은 유지(기존 화면 호환)하되 신규 UI에서는 사용하지 않는다.

### 4.2 신규 컬럼

| 컬럼 | 생성 규칙 |
|---|---|
| `eds_test_time_m` | `eds_status=='actual'`인 wafer만: `expected_eds_date + U(0,2)일`. pending은 NaT |
| `eds_test_time_p` | actual 중 70%: `eds_test_time_m + U(3,6)일`. 나머지 NaT |
| `eds_test_time_ml` / `eds_test_time_pl` | product=='KCAI'의 actual 중 40%만: M/P + 1일. 나머지 NaT |
| `MSR_001` ~ `MSR_040` | 수치형 측정값. 최소 6개는 metro/fdc 인자와 상관 갖게 생성 (예: `MSR_003 = 0.6*zscore(metro_ch_hole_cd) + N(0,0.4)` 스케일 변환), 나머지는 약상관/노이즈 |

**part_id 파생 규칙** (컬럼 사전 생성 금지 — §A4): 요청 시점에 아이템 값 `v`에 대해
```python
def part_value(v, wafer_id, item, part):  # part in {"A","B","C"}
    rng = np.random.default_rng(abs(hash((wafer_id, item, part))) % 2**32)
    return v * (1.0 + {"A": -0.05, "B": 0.0, "C": 0.05}[part]) + rng.normal(0, 0.02 * max(abs(v), 1e-9))
# part_id == "All" → 원본 v 그대로
```
같은 (wafer, item, part) 조합은 항상 같은 값이 나온다(재현성).

**eds_step 파생 규칙**: step `M` = 원본 값, `P` = `v * 0.92`(수리 후 개선 가정) + 동일 방식 노이즈, `ML`/`PL` = `v * 1.03`. 해당 step의 `eds_test_time_*`이 NaT인 wafer는 그 step 데이터 없음으로 처리.

### 4.2b `fab_history` long-format 테이블 (신규 — 다공정 join 기반)

`MockStore`에 `fab_history: pd.DataFrame` 필드를 추가한다. 모든 wafer가 5개 스텝을 공정 순서(`CR380020 → CR860200 → CR860400 → WL240100 → WL560300`)대로 통과한다.

| 컬럼 | 생성 규칙 |
|---|---|
| `wafer_id`, `lot_id`, `product` | wafer_data와 동일 |
| `step_id`, `module` | wafer당 5행 |
| `track_out_time` | lot 시작일부터 스텝당 `+U(1,3)일` 누적. **wafer의 대표 step 행은 `wafer_data.process_date`와 일치**시킴 |
| `tool_id`, `chamber_id`, `ppid`, `eco_number`, `recipe_version`, `pm_age`, `part_modification_flag` | 스텝×lot 단위 재추첨(같은 lot·같은 스텝은 동일 tool 확률 80%). **wafer의 대표 step 행은 wafer_data의 flat 값을 그대로 복사**(일관성 보장) |

행 수 ≈ 4,000 wafer × 5 = 20,000 — 메모리 문제 없음. `wafer_data`의 flat 컬럼(step, tool_id 등)은 "대표 분석 step"의 값으로 계속 유지한다(Window Review 등 기존 화면은 무수정 호환).

### 4.3 metadata 확장 (`GET /api/metadata` 응답에 추가)

```json
{
  "process_modules": [
    {"name": "Ch.Hole", "fab_steps": [{"step_id": "CR380020", "label": "Ch.Hole Mask"}, ...]},
    {"name": "WLCUT",  "fab_steps": [...]}
  ],
  "eds_steps": ["M", "P", "ML", "PL"],
  "eds_categories": ["BIN", "MSR"],
  "eds_items": {"BIN": ["BIN_001", "...", "BIN_600"], "MSR": ["MSR_001", "...", "MSR_040"]},
  "part_ids": ["All", "A", "B", "C"],
  "categorical_columns": ["product", "step", "lot_id", "tool_id", "chamber_id", "ppid",
                          "eco_number", "recipe_version", "zone", "part_modification_flag",
                          "eds_status", "is_rework"],
  "numeric_columns": ["metro_ch_hole_cd", "metro_thickness", "metro_uniformity",
                      "fdc_temp_mean", "fdc_pressure_mean", "fdc_flow_mean",
                      "fdc_rf_power_mean", "pm_age", "yield"]
}
```
기존 키(products/steps/tools/... )는 전부 유지하고 값만 새 이름 체계로 바뀐다.

### 4.4 파급 수정 (이름 교체 sweep)

- `frontend/src/stores/analysisSetStore.ts` `defaultFilters()`: `product: ['KCAI']`, `step: ['CR860200']` 등으로 갱신
- `backend/app/services/analysis_set_service.py`·`window_analysis_service.py`·기본 Condition Rule(T01/C2)·기본 BIN Group: 제품/스텝 문자열 리터럴을 grep으로 전수 확인 (`grep -rn "DRAM_A\|ETCH_CONTACT\|NAND_C\|CLEAN_POST_ETCH\|CMP_OXIDE" backend frontend/src --include='*.py' --include='*.ts' --include='*.vue'`)
- `backend/tests/test_workbench_app.py`의 기대값 갱신

### 4.5 완료 기준

- [ ] `pytest backend/tests -q` 통과 (기존 + 갱신 테스트)
- [ ] `GET /api/metadata`에 4.3의 신규 키 존재, `date_range` 정상
- [ ] 기존 6개 화면이 새 이름 체계로 전부 동작 (Analysis Set 생성 → Window Review 실행까지 수동 확인)

---

## 5. Phase 1 — 필터식(Expression) 엔진 (backend)

**신규 파일**: `backend/app/services/expression_service.py`, `backend/tests/test_expression_service.py`
**수정**: `backend/app/api/routes_metadata.py`(또는 신규 `routes_expressions.py` + `app/main.py` 등록)

### 5.1 문법 (Spotfire/SQL 통합 서브셋)

```
expr        := case_expr | or_expr
or_expr     := and_expr (OR and_expr)*
and_expr    := not_expr (AND not_expr)*
not_expr    := [NOT] comparison
comparison  := additive (( = | == | != | <> | > | >= | < | <= ) additive)?
             | additive [NOT] IN '(' literal (',' literal)* ')'
             | additive IS [NOT] NULL
additive    := term (( + | - ) term)*
term        := factor (( * | / ) factor)*
factor      := literal | column | '(' expr ')' | func '(' expr ')'
column      := '[' 아무 문자 ']'   |   식별자(A-Za-z_][A-Za-z0-9_]*, 예약어 제외)
literal     := 숫자 | '문자열' | "문자열" | TRUE | FALSE
func        := ABS | LOG | LOG10 | SQRT
case_expr   := CASE WHEN expr THEN expr (WHEN expr THEN expr)* [ELSE expr] END
```
- 키워드는 대소문자 무시 (`case when`, `CASE WHEN` 모두 허용)
- `[PPID] != "TT_TEST"`(Spotfire), `PPID <> 'TT_TEST'`(SQL) 모두 동일하게 파싱됨

### 5.2 구현

- 정규식 토크나이저 → 재귀 하강 파서 → AST → `evaluate(ast, df) -> pd.Series` (전부 벡터 연산)
- 컬럼 해석: `df.columns` 화이트리스트. 미존재 컬럼이면 `difflib.get_close_matches`로 유사 컬럼 3개를 포함한 에러 메시지
- 문자열 비교 시 컬럼이 categorical/object가 아니면 astype(str) 비교하지 말고 타입 오류를 명시적으로 반환
- 공개 API:
  ```python
  def parse(expression: str) -> Ast                      # 실패 시 ExpressionError(message, position)
  def evaluate_filter(expression: str, df) -> pd.Series  # bool Series. 비-bool 결과면 오류
  def evaluate_column(expression: str, df) -> pd.Series  # case-when/산술 허용
  def columns_used(expression: str) -> list[str]
  ```

### 5.3 검증 엔드포인트

```
POST /api/expressions/validate
{ "expression": "[PPID] != \"TT_TEST\"", "mode": "filter" | "column", "context": "fab" | "eds" }
→ 200 { "valid": true,  "columns_used": ["ppid"], "result_dtype": "bool" }
→ 200 { "valid": false, "error": "알 수 없는 컬럼 [PPIDX] — 유사: ppid", "position": 0 }
```
`context`는 검증에 쓸 컬럼 화이트리스트 선택용: `fab` = `fab_history` 컬럼(§4.2b: track_out_time, tool_id, chamber_id, ppid, eco_number, recipe_version, pm_age, part_modification_flag 등) + `product`, `eds` = wafer frame + `value`, `part_id`, `eds_step`, `test_time`.

컬럼명 매칭은 대소문자 무시로 한다 (`[PPID]` → `ppid` 컬럼).

### 5.4 테스트 (최소 케이스)

- `[PPID] != "TT_TEST"` / `PPID <> 'TT_TEST'` 동치
- `and`/`or` 우선순위, 괄호, `not`, `in ('A','B')`, `is null`
- `case when [metro_ch_hole_cd] >= 53 then 'high' when [metro_ch_hole_cd] <= 51 then 'low' else 'mid' end` → object Series
- 산술: `[metro_thickness] / [metro_ch_hole_cd] > 1.9`
- 오류: 미존재 컬럼, 닫히지 않은 괄호, filter 모드에 non-bool 식, 빈 문자열

### 5.5 완료 기준

- [ ] 테스트 전부 통과, `eval`/`exec`/`df.query` 미사용 (`grep -n "eval\|exec" backend/app/services/expression_service.py` 확인)

---

## 6. Phase 2 — 조건 라이브러리 (Preset 폴더/Revision/공유) (backend)

**신규 파일**: `backend/app/services/preset_service.py`, `backend/app/api/routes_presets.py`, `backend/tests/test_presets.py`
**수정**: `backend/app/main.py`(라우터 등록), `backend/app/models/schemas.py`

### 6.1 저장 구조 (파일 영속화)

`backend/app/data/preset_store.json` — 서버 기동 시 로드, 변경 시마다 원자적 저장(temp 파일 → `os.replace`). git에는 시드 파일을 커밋한다(아래 6.4).

```json
{
  "folders": [
    {"id": "PF001", "name": "Ch.Hole", "order": 1},
    {"id": "PF002", "name": "WLCUT", "order": 2}
  ],
  "presets": [
    {
      "id": "PS001",
      "folder_id": "PF001",
      "name": "ETCH",
      "scope": "shared",
      "owner": "me",
      "created_at": "2026-07-02T00:00:00",
      "revisions": [
        {"rev": 0, "note": "초기 조건", "created_at": "...", "created_by": "me", "criteria": { ...§7.2의 criteria 객체... }},
        {"rev": 1, "note": "ETCH recipe 변경 반영", "created_at": "...", "created_by": "me", "criteria": {...}}
      ]
    }
  ],
  "counters": {"folder": 2, "preset": 1}
}
```

### 6.2 API

| Method/Path | 요청 | 응답/규칙 |
|---|---|---|
| `GET /api/preset-tree` | header `X-User` | `{folders: [{id, name, presets: [{id, name, scope, owner, latest_rev, revisions: [{rev, note, created_at}]}]}]}`. scope 필터는 프론트에서(전체 반환) |
| `POST /api/preset-folders` | `{name}` | 중복 이름 409 |
| `PATCH /api/preset-folders/{id}` | `{name}` | |
| `DELETE /api/preset-folders/{id}` | | 하위 preset 있으면 409 |
| `POST /api/presets` | `{folder_id, name, scope, note, criteria}` | rev 0 생성. owner = `X-User` |
| `POST /api/presets/{id}/revisions` | `{note, criteria}` | 소유자만. rev = max+1 |
| `GET /api/presets/{id}/revisions/{rev}` | | `{criteria, note, created_at, created_by}` |
| `PATCH /api/presets/{id}` | `{scope}` 또는 `{name}` | 소유자만. scope: `personal`↔`shared` |
| `POST /api/presets/{id}/duplicate` | `{folder_id?, name}` | 최신 rev만 복사해 rev 0으로 새 preset 생성. owner = 요청자 (공유 preset 가져가기 용도) |
| `DELETE /api/presets/{id}` | | 소유자만 |

권한 위반은 403 + 한국어 메시지. `X-User` 헤더 없으면 `"me"`로 간주.

### 6.3 스키마 (schemas.py 추가)

```python
class PresetCriteria(BaseModel):        # §7.2와 동일 구조 — 단일 소스로 재사용
    fab: FabCriteria
    eds: EdsCriteria | None = None
    chart: ChartState | None = None

class PresetCreate(BaseModel):
    folder_id: str
    name: str
    scope: Literal["personal", "shared"] = "personal"
    note: str = ""
    criteria: PresetCriteria
```

### 6.4 시드 데이터

`preset_store.json` 초기 커밋본에 폴더 `Ch.Hole`/`WLCUT` + 예시 preset 3개(`Mask` rev0, `ETCH` rev0·rev1 — rev1은 FAB STEP이나 필터식이 다른 값)를 넣어 트리 UI가 처음부터 채워져 보이게 한다. 예시 소유자는 `"me"`, `ETCH`는 `shared`.

### 6.5 커스텀 EDS 아이템 (같은 JSON 저장소)

여러 EDS 아이템을 +/−로 합성한 아이템을 사용자가 직접 타이핑한 이름으로 저장하고 **모든 사용자가 사용**할 수 있게 한다 (예: `H2H_NET = BIN_014 + BIN_208 − BIN_031`).

`preset_store.json`에 top-level 키 `custom_eds_items` 추가:

```json
{"name": "H2H_NET", "category": "BIN",
 "terms": [{"item": "BIN_014", "sign": 1}, {"item": "BIN_208", "sign": 1}, {"item": "BIN_031", "sign": -1}],
 "owner": "me", "created_at": "2026-07-02T00:00:00"}
```

| Method/Path | 규칙 |
|---|---|
| `GET /api/custom-eds-items` | 전체 목록 (전원 공유 전제) |
| `POST /api/custom-eds-items` | `{name, category, terms}`. name: `^[A-Za-z0-9_]{2,30}$`, 기존 `BIN_*`/`MSR_*`/커스텀명과 중복 시 409. terms ≥ 2, 전부 같은 category, sign ∈ {1, -1} |
| `DELETE /api/custom-eds-items/{name}` | 생성자만(그 외 403). 사용 중 여부는 확인하지 않음(프로토타입) |

값 계산(§7.3에서 사용): 각 term의 원본 값에 part/eds_step 파생(§4.2)을 **먼저** 적용한 뒤 signed sum. 서비스는 `custom_item_service.expand(name) -> list[tuple[str, int]]`를 제공하고 `selection_service`가 이를 사용한다. 구현은 `preset_service`와 동일한 JSON 영속화 헬퍼를 공유한다.

### 6.6 시드·완료 기준

- 시드: `preset_store.json`에 커스텀 아이템 예시 1개(`H2H_SUM = BIN_014 + BIN_208 + BIN_377`, owner `"me"`)를 포함한다.
- [ ] Preset: 생성→rev 추가→공유 전환→타 사용자(`X-User: other`)로 rev 추가 시도 403→복제 성공, 파일 재로드 후에도 유지 — 테스트로 검증
- [ ] 커스텀 아이템: 생성/중복 409/타인 삭제 403/재로드 유지 — 테스트로 검증

---

## 7. Phase 3 — 물량 선정 API: criteria v2 + 미리보기 (backend)

**수정**: `backend/app/models/schemas.py`, `backend/app/services/analysis_set_service.py`
**신규**: `backend/app/services/selection_service.py`, `backend/app/api/routes_selection.py`, `backend/tests/test_selection.py`

### 7.1 스키마

```python
class DateRange(BaseModel):
    start: str | None = None   # "YYYY-MM-DD"
    end: str | None = None

class FabStepCondition(BaseModel):
    fab_step: str                        # 공정 1개 (step_id)
    date_range: DateRange = DateRange()  # 해당 스텝의 track_out_time 기준
    filter_expression: str = ""          # 해당 스텝의 fab_history 행에 적용. 빈 문자열이면 무시

class FabCriteria(BaseModel):
    products: list[str] = []
    step_conditions: list[FabStepCondition] = []  # 1~3개(validator로 강제, 스텝 중복 금지), 블록 간 AND(교집합) join
    primary_step: str | None = None      # 미리보기 "FAB 시각"의 기준 공정. None이면 첫 블록의 공정
    exclude_rework: bool = True          # 기존 제외 토글 3종 이관 (블록 밖 공통)
    exclude_engineering_lot: bool = True
    exclude_abnormal_route: bool = True

class EdsCriteria(BaseModel):
    eds_step: Literal["M", "P", "ML", "PL"] = "M"
    eds_category: Literal["BIN", "MSR"] = "BIN"
    eds_items: list[str] = []            # 1개 이상이면 값은 각 아이템별 시리즈, 미리보기는 첫 항목 기준. 커스텀 아이템 이름 허용(§6.5)
    date_range: DateRange = DateRange()  # eds_test_time_{step} 기준
    part_id: Literal["All", "A", "B", "C"] = "All"
    filter_expression: str = ""

class ComputedColumn(BaseModel):
    name: str                            # 영숫자+_, 기존 컬럼과 충돌 금지
    expression: str

class ChartState(BaseModel):
    x_axis: Literal["fab_time", "eds_time"] = "fab_time"
    legend_by: str | None = None         # categorical 컬럼명 or computed column명
    adhoc_filters: list[str] = []        # filter 식 목록 (AND 결합)
    computed_columns: list[ComputedColumn] = []
```

`AnalysisSetCreate`에 `criteria: PresetCriteria | None = None` 추가. `filters`(기존 flat)는 유지 — 기존 화면·테스트 호환. `apply_filters()`는 `criteria`가 있으면 신규 경로(아래 7.3), 없으면 기존 경로.

### 7.2 미리보기 엔드포인트

```
POST /api/selection/preview
{
  "fab":  { FabCriteria },
  "eds":  { EdsCriteria },        // null이면 FAB만으로 wafer 수 요약 (points는 빈 배열)
  "chart": { ChartState },
  "sample_limit": 2000
}
→ 200
{
  "summary": {
    "lot_count": 128, "wafer_count": 2410,
    "fab_step_matches": [
      {"fab_step": "CR380020", "matched": 3100},
      {"fab_step": "CR860200", "matched": 2600}
    ],
    "eds_matched_count": 2180, "eds_match_ratio": 0.905,
    "excluded_by_fab_filter": 55, "excluded_by_eds_filter": 12,
    "excluded_by_adhoc": 30
  },
  "columns": { "categorical": ["product", ..., "cd_band"], "numeric": [...] },
  "points": [
    { "wafer_id": "W00001", "lot_id": "L0001",
      "x": "2026-03-02T04:00:00",        // x_axis 선택에 따라 process_date 또는 eds_test_time
      "y": 0.034,                        // 첫 eds_item 값 (part/step 파생 적용)
      "legend": "T01",                   // legend_by 없으면 "전체"
      "meta": { "tool_id": "T01", "chamber_id": "C2", "ppid": "PPID_A",
                "zone": "edge", "eds_item": "BIN_014", "part_id": "All" } }
  ],
  "sampled": true, "n_total": 2180
}
```

오류 계약: 필터식 오류는 400이 아니라 200 + `{"error": {"stage": "fab_filter:<step_id>"|"eds_items"|"eds_filter"|"adhoc"|"computed:<name>", "message": "..."}}` — 프론트가 해당 입력창(블록) 옆에 표시할 수 있게 한다. 삭제된 커스텀 아이템 참조는 `stage: "eds_items"` + `"삭제된 커스텀 아이템: H2H_NET"`.

### 7.3 `selection_service.py` 파이프라인

```
1. FAB join: product 마스크(wafer 단위) → step_conditions 블록별로 fab_history에서
     (step_id == block.fab_step) & track_out_time 기간 & evaluate_filter(block.filter_expression)
   을 만족하는 wafer_id 집합을 구하고 전체 교집합(AND) → 제외 토글 3종 적용.
   블록별 매칭 수를 summary.fab_step_matches로 보고(어느 join에서 물량이 줄었는지 확인용)
2. EDS: eds_step의 test_time 컬럼 NaT 제거 → date_range 마스크
   → 요청 아이템만 melt: value = part_value(step_value(원본)) (§4.2)
   → 커스텀 아이템은 custom_item_service.expand()로 전개해 각 term에 파생 적용 후 signed sum (§6.5)
   → eds filter_expression 평가 (value/part_id/eds_step/test_time + wafer 컬럼 사용 가능)
3. computed_columns 순차 평가(evaluate_column) → frame에 추가 (이후 필터·legend에서 사용 가능)
4. adhoc_filters AND 결합
5. summary 집계 → x/y/legend 추출 → n_total 기록 → 초과 시 균등 샘플링(sample_limit)
   fab_time(x축)은 primary_step(없으면 첫 블록 공정)의 track_out_time
```
샘플링은 시간순 정렬 후 `np.linspace` 인덱스 선택(시계열 모양 보존).

### 7.4 완료 기준

- [ ] 테스트: FAB만/FAB+EDS/필터식 포함/computed column을 legend로/오류 스테이지 보고 — 각 1개 이상
- [ ] 테스트: 2개 공정 join 시 단일 공정 대비 물량이 줄고, 블록별 매칭 수가 `fab_step_matches`로 보고됨
- [ ] 테스트: 커스텀 아이템을 `eds_items`로 지정하면 미리보기 y값 = 구성 아이템의 signed sum과 일치
- [ ] `POST /api/analysis-sets`에 criteria를 넣어 만든 Set으로 기존 `POST /api/window-review`가 정상 동작

---

## 8. Phase 4 — Analysis Set 화면 개편 (frontend)

**재작성**: `frontend/src/views/AnalysisSetView.vue`
**신규 컴포넌트** (`frontend/src/components/analysisSet/`):

| 컴포넌트 | props / emits | 내용 |
|---|---|---|
| `PresetTree.vue` | props: 없음(presetStore 직결) / emits: `load(criteria, presetLabel)` | 상단 `el-segmented` [내 조건 | 공유 | 전체] + `el-tree`(폴더/preset-rev 노드) + 노드 `⋮` 드롭다운(불러오기/새 Rev 저장/복제/공유 전환/이름 변경/삭제) + `[+ 폴더]` 버튼. 삭제는 `ElMessageBox.confirm` |
| `FabHistoryForm.vue` | `v-model:criteria` (FabCriteria) | 상단 공통: 제품 multi-select + 제외 토글 3종. 그 아래 **공정 조건 블록 카드 목록**(`FabStepConditionCard.vue` 반복) + `[+ 다른 공정 조건 추가 (join)]` 버튼: 마지막 블록이 유효(공정+기간 채움, 필터식 유효 또는 공백)할 때만 활성, 3개 도달 시 숨김 |
| `FabStepConditionCard.vue` | `v-model:condition` (FabStepCondition), `index`, `is-primary`, `removable` / emits: `remove`, `set-primary` | 카드 헤더 `공정 {n}` + 기준공정 라디오 + `×` 버튼. 본문: 공정 select(**공정 모듈별 `el-option-group`**, 다른 블록이 쓴 스텝은 disabled), 진행기간 date-picker, `ExpressionEditor`(context=fab) |
| `EdsItemForm.vue` | `v-model:criteria` (EdsCriteria) | EDS_STEP segmented(M/P/ML/PL), Category segmented(BIN/MSR), EDS_ITEM multi-select(검색·가상 스크롤: 600개 → element-plus `el-select-v2`, **`커스텀` `el-option-group` 최상단 고정** — hover tooltip에 수식·생성자 표시, 본인 것은 우측 휴지통), `[+ 커스텀 아이템]` 버튼 → `CustomEdsItemDialog`, 테스트 기간, part_id select, `ExpressionEditor`(context=eds) |
| `CustomEdsItemDialog.vue` | `visible`, `category`, `items`(해당 category 아이템 목록) / emits: `save({name, category, terms})` | 이름 입력(영숫자+`_`, 실시간 형식 검사), "더할 아이템" multi-select / "뺄 아이템" multi-select, 하단에 수식 미리보기(`H2H_NET = BIN_014 + BIN_208 − BIN_031`), 서버 409(이름 중복) 시 입력창 옆 표시 |
| `ExpressionEditor.vue` | `v-model`(string), `context`, `placeholder` / emits: `valid-change(bool)` | textarea + 컬럼 팔레트 popover(클릭 시 커서 위치에 `[컬럼]` 삽입) + 500ms 디바운스 자동 검증(`POST /api/expressions/validate`) + 상태 아이콘(✓/✗+메시지). placeholder 예시: `case when [PPID] != "TT_TEST" then ...` |
| `SelectionPreview.vue` | `preview`(응답 객체), `loading` / emits: `update:chart`(ChartState 변경) | 요약 밴드(SummaryCard 재사용) + x축 segmented + legend-by select(columns.categorical) + `PlotlyChart` scattergl + 필터 칩 목록 + `[+ 필터]`/`[+ 파생 컬럼]` 버튼 + `sampled` 안내 문구("2,180개 중 2,000개 표시") |
| `ComputedColumnDialog.vue` | `visible`, `existing-names` / emits: `save({name, expression})` | 이름 입력 + ExpressionEditor(mode=column) + 미리보기 문구 |
| `SavePresetDialog.vue` | `visible`, `folders`, `currentPreset?` / emits: `save({mode: 'new'|'new-rev', folder_id, name, note, scope})` | "새 Preset" vs "기존 Preset에 새 Rev" 라디오 |

**신규 스토어** `frontend/src/stores/presetStore.ts`: `tree`, `scopeFilter`, `loadedPreset {id, name, rev, folderName} | null`, `dirty: bool`, actions `loadTree/create/addRevision/duplicate/setScope/rename/remove/createFolder`.

**`analysisSetStore.ts` 확장**: `criteria`(reactive PresetCriteria), `preview`, `previewLoading`, actions `runPreview()`, `createFromCriteria(name)`.

**API 함수 추가** (`frontend/src/api/analysisApi.ts`): `fetchPresetTree`, `createPreset`, `addPresetRevision`, `duplicatePreset`, `patchPreset`, `deletePreset`, `createPresetFolder`, `validateExpression`, `fetchSelectionPreview`, `fetchCustomEdsItems`, `createCustomEdsItem`, `deleteCustomEdsItem`. axios 인스턴스(`client.ts`)에 `X-User` 기본 헤더 추가: `localStorage.getItem('workbench_user') || 'me'`.

### 8.1 인터랙션 세부

- **scatter legend**: `RawScatterChart`처럼 legend 값별 trace 분리. 색상은 §9의 `CATEGORICAL_PALETTE` 순환. legend 항목 클릭 시 Plotly 기본 토글(추가 구현 불필요).
- **필터 칩**: 각 칩 = adhoc_filters의 식 1개. `×` 클릭 → 제거 → 미리보기 자동 재조회. 칩 추가는 `[+ 필터]` → ExpressionEditor 다이얼로그.
- **파생 컬럼**: 저장 시 chart.computed_columns에 추가 → 재조회 → legend-by 목록에 신규 컬럼 표시(문자열 결과면 categorical로).
- **미리보기 자동 재조회 조건**: x축/legend/칩/파생 변경 시(차트 상태만 바뀜) — criteria(FAB/EDS 폼) 변경 시에는 자동 조회하지 않고 `물량 조회` 버튼 활성화만(대량 조회 남발 방지).
- **공정 조건 추가 흐름**: 블록이 유효해지는 순간 `[+ 다른 공정 조건 추가 (join)]`이 비활성→활성으로 바뀌며 "CR380020 조건 완료 — 다른 공정을 join 하시겠습니까?" 보조 문구 표시(모달 아님). 블록 추가 시 이전 블록은 요약 한 줄(`공정 1 · CR380020 · 1/1~6/19 · 필터 1건`)로 접히고 새 블록이 펼쳐진다. 요약 클릭으로 재펼침.
- **join 결과 가시화**: 미리보기 요약 밴드에 블록별 매칭 수를 화살표로 표기 — `CR380020 3,100 → ∩ CR860200 2,600 → 제외 2,410`. 최종 0건이면 어느 블록에서 소멸했는지 강조.
- **커스텀 아이템**: 생성 성공 시 목록 갱신 + 방금 만든 아이템 자동 선택. 삭제는 본인 것만(타인 것은 휴지통 미노출).
- **상태**: initial(안내 문구 "조건을 선택하고 물량 조회를 누르세요") / loading(스켈레톤) / loaded / empty("조건에 해당하는 물량 없음 — 기간을 넓혀보세요") / error(스테이지별 메시지를 해당 입력창 근처에).
- **Analysis Set 저장**: 이름 입력 + 저장 → `createFromCriteria` → 성공 시 기존처럼 우측(또는 요약 밴드 아래) 저장 목록 갱신. 기존 "저장된 Analysis Set" 테이블은 우측 패널 하단에 접이식으로 유지 (Window Review 연계 유지가 목적이므로 제거 금지).

### 8.2 완료 기준

- [ ] Preset 트리에서 `ETCH Rev1` 클릭 → 폼 채워지고 배지 표시 → 폼 수정 → "새 Rev 저장" → 트리에 `ETCH Rev2` 등장
- [ ] 공유 탭에서 타인 preset 복제 가능, 수정 버튼은 비활성
- [ ] `[PPID] != "TT_TEST"` 입력 시 유효 표시, 오타 컬럼 입력 시 유사 컬럼 제안 메시지
- [ ] FAB+EDS 선택 → 물량 조회 → scatter 표시 → legend를 `tool_id`→파생 컬럼으로 전환 → 색상 재배치
- [ ] x축 FAB시각↔EDS시각 전환 시 점 위치 변경
- [ ] 공정 1 조건 완성 → `+ 다른 공정 조건 추가` 활성 → 공정 2 추가 → 조회 시 요약 밴드에 블록별 매칭 수(∩ 흐름) 표시, 기준공정 변경 시 x축 시각이 해당 공정 track-out으로 변경
- [ ] `[+ 커스텀 아이템]`으로 `H2H_NET` 생성 → EDS_ITEM 커스텀 그룹에 표시·자동 선택 → 조회 성공 → `X-User`를 `other`로 바꿔도 목록에 보이고 휴지통은 미노출
- [ ] `npm test && npm run build` 통과

---

## 9. 디자인/테마 가이드 (전 Phase 공통)

- **기조 유지**: 현행 라이트 테마(#eef2f6 배경 / 흰 패널 / #2563eb 프라이머리 / Inter). 대규모 디자인 시스템 도입 금지.
- **신규 파일** `frontend/src/palette.ts`:
  ```ts
  // Okabe-Ito 색맹 안전 팔레트 — categorical legend 전용
  export const CATEGORICAL_PALETTE = ['#0072B2', '#E69F00', '#009E73', '#CC79A7',
                                      '#56B4E9', '#D55E00', '#F0E442', '#999999']
  export const HEAT_RAMP = [[0, '#e2e8f0'], [0.5, '#f59e0b'], [1, '#dc2626']]  // 낮음=회색, 높음=빨강
  ```
  `SelectionPreview` scatter, `RawScatterChart`, `ZoneViewChart`, Commonality boxplot(§10)에서 사용. 기존 차트 색을 일괄 교체하지는 말고 legend 다중 series가 있는 차트만 적용.
- **style.css 추가 토큰**: `--radius-panel: 12px; --gap-page: 16px; --shadow-soft: 0 1px 3px rgb(15 23 42 / 0.08);` — 신규 컴포넌트는 이 토큰 사용.
- 트리 패널: 배경 `#f8fafc`(네비와 동일 계열), 선택 노드 `#eff6ff` + 좌측 3px `#2563eb` 바.
- 카드 제목은 14px/600, 과한 장식·이모지 금지. 모든 신규 문구는 한국어(기존 관례).

---

## 10. Phase 5·6 — Window 분석 메뉴 고도화

### 10.1 기존 탭 진단 및 개선 (YE 담당자 관점)

| 탭 | 현재 | 진단 | 개선 (이번 범위) |
|---|---|---|---|
| 요약 | decision candidates + evidence + KPI 카드 | 방향성 좋음. window 여유도·최근 추세가 없음 | KPI 카드 2개 추가: **Safe window 점유율**(x_parameter가 safe_window 안에 있는 wafer %) + **최근 30일 fail 추세**(직전 30일 vs 이전 30일 delta, ▲▼ 표시) |
| Raw Scatter | x=관리인자, y=BIN Group fail, lasso 제외 | y축이 BIN Group 고정. spec 기준선 없음 | y축 선택(선택된 BIN Group들 + `yield`), safe_window 세로 band 오버레이(연한 초록 `rgba(22,163,74,0.08)` + 경계 점선) |
| Binned Response | 분위 binning + stderr | 표본 적은 bin이 동급으로 보임 | `wafer_count < 15`인 bin은 marker 회색·점선 연결로 디엠퍼시스 + 하단에 wafer_count bar(y2축) |
| Trade-off | H2H vs Not Open 2선 | `combined_fail_rate`가 응답에 있는데 미표시. 균형점 판단을 눈대중에 의존 | combined 라인(회색 굵은 선) 추가 + 최소 combined bin에 `★ 균형점` annotation |
| Time Trend | actual fail + pending 수 | **관리도 부재** — 드리프트/이상 조기 감지 불가 | SPC 추가: 중심선·±3σ(UCL/LCL) 점선, 한계 초과점 빨간 강조, 연속 7점 편측(run rule) 구간 주황 배경 band, 위반 건수 배지 |
| Condition Split | scatter를 legend 색으로만 | "어느 인자 기인인가"의 **정량 근거 없음** | 신규 Commonality 탭으로 대체·확장 (아래). Split scatter는 유지 + palette.ts 적용 |
| Zone View | zone별 binned 라인 | 존별 차이의 유의성 불명 | zone별 boxplot(Plotly box trace) 병기 + Kruskal-Wallis p-value 표기 |
| Interaction | 5×5 heatmap, 두 번째 인자 서버 고정 | 인자 조합을 사용자가 못 바꿈. 저표본 셀 왜곡 | x/y 인자 select 2개 추가(`view_options.interaction_x/y`) + `count < 5` 셀 반투명 + hover에 count 표기 |
| 제외 Rule | rule 목록 + before/after corr | 충분 | 변경 없음 (correlation delta에 ▲▼ 색만) |

### 10.2 신규 탭 3종 (YE 인사이트 핵심)

**① BIN Pareto (수율 손실 파레토)** — *"어떤 불량 모드부터 잡을까"*
- 전체 BIN 중 평균 fail rate × wafer 수 기여 상위 30개 bar + 누적 % 라인 (이중축)
- 기본 BIN Group에 속한 bin은 bar 색 강조, 나머지는 회색
- bar 클릭 → 해당 bin 1개짜리 임시 BIN Group으로 즉시 review 재실행(확인 다이얼로그)

**② Driver Ranking (관리 인자 영향도)** — *"x_parameter를 데이터가 제안"*
- 선택된 BIN Group fail rate에 대해 metadata.numeric_columns 전체의 |Pearson r| 수평 bar (부호는 bar 색: 양=빨강, 음=파랑), n 표기
- bar 클릭 → 그 인자를 `xParameter`로 설정하고 review 재실행
- 상단 안내: "상관은 인과가 아님 — 후보 선별용" 캡션

**③ Commonality (설비/조건 기인성 분석)** — *"4M 변경점 추적의 기본기"*
- 대상 factor: `tool_id, chamber_id, ppid, eco_number, recipe_version, part_modification_flag`
- factor별로 그룹 분해 → **Kruskal-Wallis H 검정** p-value + epsilon² 효과크기 → p 오름차순 랭킹 테이블 (컬럼: 인자 / 그룹 수 / p-value / 효과크기 / 최악 그룹(중앙값 최대) / n)
- 행 클릭 → 우측에 해당 factor의 그룹별 boxplot (Plotly box, palette.ts 적용) + 그룹별 n/중앙값 표
- `part_modification_flag` 행에는 개조 전후 두 그룹 비교 = 사실상 Before/After 검정이 포함됨을 캡션으로 명시
- p-value < 0.05 행에 주황 배지 "유의"

### 10.3 Backend 확장 (Phase 5)

**수정**: `backend/app/services/window_analysis_service.py`, `backend/app/models/schemas.py`, `backend/requirements.txt`(`scipy` 명시 — scikit-learn 의존성으로 이미 존재할 가능성이 높지만 명시한다)

`WindowReviewRequest.view_options`에 허용 키 추가: `bins`(기존), `interaction_x`, `interaction_y`, `y_axis_metric`.

응답 필드 추가 (기존 필드는 전부 유지):

```json
{
  "summary_metrics": { "...기존...": "",
    "safe_window_occupancy": 0.83,
    "recent_trend": {"recent_30d_fail": 0.041, "prior_30d_fail": 0.036, "delta": 0.005}
  },
  "trend_data": { "...기존 actual/pending...": "",
    "spc": {"center": 0.038, "ucl": 0.052, "lcl": 0.024, "sigma": 0.0047,
            "violations": [{"date": "2026-05-02", "type": "beyond_3sigma"},
                            {"date": "2026-04-11", "type": "run_of_7"}]}
  },
  "pareto_data": [
    {"bin_id": "BIN_014", "mean_fail_rate": 0.021, "loss_contribution": 0.18,
     "cum_pct": 0.18, "in_selected_group": true}
  ],
  "driver_ranking": [
    {"parameter": "metro_ch_hole_cd", "corr": 0.68, "abs_corr": 0.68, "n": 2180}
  ],
  "commonality_data": [
    {"factor": "chamber_id", "p_value": 0.0012, "effect_size": 0.09, "group_count": 4,
     "worst_group": "C2",
     "groups": [{"value": "C1", "n": 540, "median": 0.031, "q1": 0.021, "q3": 0.044,
                 "mean": 0.034, "min": 0.002, "max": 0.11}]}
  ]
}
```

계산 규칙:
- SPC: actual 일별 fail rate 시계열로 center=mean, sigma=std(전 구간), run rule = 연속 7점이 center의 같은 쪽. (일별 점수가 20 미만이면 spc를 null로 반환하고 프론트는 안내 문구)
- Pareto: `loss_contribution = mean_fail_rate / Σ(전체 BIN mean_fail_rate)` 상위 30개. 600개 컬럼 mean은 `frame[bin_cols].mean()` 한 번으로 계산(루프 금지)
- Kruskal-Wallis: `scipy.stats.kruskal`, 그룹당 n<5인 그룹은 제외하고 그룹 2개 미만이 되면 해당 factor 생략. `epsilon² = (H - k + 1) / (n - k)`
- Driver: pending 제외(actual만), NaN pairwise 제거 후 r. n<30이면 목록에서 제외

### 10.4 Frontend (Phase 6)

**신규**: `frontend/src/components/charts/ParetoChart.vue`, `DriverRankingChart.vue`, `frontend/src/components/window/CommonalityPanel.vue`(랭킹 테이블 + boxplot 복합 — `el-table` + `PlotlyChart`)
**수정**: `WindowReviewView.vue`(탭 3개 추가 + 기존 탭 개선 §10.1), `TimeTrendChart.vue`(SPC 오버레이 — `spc` prop 추가, 없으면 기존 렌더 그대로), `BinnedResponseChart.vue`, `TradeoffChart.vue`, `RawScatterChart.vue`(safe window band는 `layout.shapes`로), `InteractionHeatmap.vue`, `windowReviewStore.ts`(view_options 확장)

탭 순서(왼→오): 요약 / **BIN Pareto** / **Driver Ranking** / Raw Scatter / Binned Response / Trade-off / Time Trend / **Commonality** / Zone View / Interaction / 제외 Rule
(분석 흐름: 무엇이 아픈가(Pareto) → 무엇이 원인 후보인가(Driver) → 관계 확인(Scatter/Binned) → 조건 기인성(Commonality) 순)

### 10.5 완료 기준

- [ ] backend: pareto/driver/commonality/spc 필드 단위 테스트 (형태 + 경계: 그룹 부족 시 생략, 일별 점수 부족 시 spc null)
- [ ] Pareto bar 클릭 → review 재실행되어 요약 KPI 변화 확인
- [ ] Driver bar 클릭 → xParameter 변경 반영
- [ ] Commonality에서 chamber_id가 유의(mock 물리: C2 개조·chamber tail 내장됨 → p<0.05 기대) 확인
- [ ] Time Trend에 UCL/LCL 점선 + 위반점 강조 렌더
- [ ] 기존 9개 탭 회귀 없음, `npm test && npm run build` 통과

---

## 11. Phase 7 — 마무리 (문서/회귀)

1. `README.md`: Screens 섹션에 개편된 Analysis Set(트리/FAB·EDS/미리보기)과 신규 3탭 반영, API 목록에 신규 엔드포인트 추가
2. 전체 회귀: 가이드 화면의 7-step 문구가 새 흐름과 어긋나면 `guideContent.js`의 해당 문구만 최소 수정
3. 최종 검증:
   ```bash
   python3 -m pytest backend/tests -q
   cd frontend && npm test && npm run build
   ```
   + 수동 시나리오: Preset 로드 → 물량 조회 → 파생 컬럼 legend → Analysis Set 저장 → Window Review 실행 → 신규 3탭 확인 → Export CSV

---

## 12. 실행 순서 요약

| Phase | 내용 | 의존성 | 규모 |
|---|---|---|---|
| 0 | Mock 데이터·metadata 확장 + 이름 체계 sweep | - | 중 |
| 1 | Expression 엔진 + validate API | - | 중 |
| 2 | Preset 폴더/Rev/공유 + 커스텀 EDS 아이템 backend (파일 영속) | - | 중 |
| 3 | criteria v2 + selection preview backend | 0, 1 | 중 |
| 4 | Analysis Set 화면 개편 (트리/폼/미리보기) | 1, 2, 3 | **대** |
| 5 | Window review backend 확장 (pareto/driver/commonality/spc) | 0 | 중 |
| 6 | Window review frontend (신규 3탭 + 기존 탭 개선) | 5 | 대 |
| 7 | 문서·회귀 | 전부 | 소 |

Phase 0→1→2→3→4 순서 고정. Phase 5·6은 Phase 0 이후라면 4와 병행 가능.

---

## 13. 비목표

- 인증/권한 시스템 (X-User 목업으로 대체)
- DB 도입 (Preset만 JSON 파일, 나머지 in-memory 유지)
- 구버전 대시보드(§0.3 금지 구역) 수정
- `wafer_data` flat 구조의 재구조화 — 대표 step 1개 모델 유지 (다공정 join은 신규 `fab_history` 테이블(§4.2b)이 담당, 기존 화면은 flat 컬럼 그대로 사용)
- FAB join 블록 4개 이상, 블록 간 OR 결합 (AND 교집합만)
- 모바일 반응형, 다크모드
- Spotfire 문법 전체 구현 (§5.1 서브셋만 — OVER/Intersect 등 미지원, 미지원 문법은 명확한 에러 메시지)
- 추천 spec/window 자동 산출 (과거 정합성 우려로 롤백된 이력 있음 — MEMORY.md)

## 14. 리스크와 완화

| 리스크 | 완화 |
|---|---|
| 이름 체계 교체(Phase 0)가 숨은 문자열 참조를 깨뜨림 | §4.4의 grep sweep 명령 실행 + 전체 화면 수동 확인을 완료 기준에 포함 |
| 필터식 파서 엣지 케이스 | §5.4 테스트 최소 세트 강제, 미지원 문법은 "지원하지 않는 문법: ..." 에러로 명시 |
| 600개 EDS_ITEM select 렌더 성능 | `el-select-v2`(가상 스크롤) 사용 |
| preview 재조회 남발 | criteria 변경은 수동 조회 버튼, 차트 상태 변경만 자동 재조회 (§8.1) |
| scipy 부재 | requirements.txt에 명시. import 실패 시 commonality_data를 빈 배열 + 경고 로그로 degrade |
| AnalysisSetView 재작성으로 Window Review 연계 회귀 | 기존 "저장된 Analysis Set" 테이블·선택 로직 유지 (§8.1 마지막 항목), Phase 4 완료 기준에 Window Review 실행 포함 |
| 다공정 join으로 물량이 0에 수렴 | `summary.fab_step_matches`로 블록별 감소를 항상 노출, 0건이면 소멸 지점 블록을 강조 + 안내 문구 |
| 커스텀 아이템 이름 충돌·삭제 후 참조 | 생성 시 전체 네임스페이스(BIN/MSR/커스텀) 중복 검사(409). Preset이 삭제된 커스텀 아이템을 참조하면 preview가 `error.stage="eds_items"`로 "삭제된 커스텀 아이템: {name}" 반환 — 화면이 깨지지 않음 |
