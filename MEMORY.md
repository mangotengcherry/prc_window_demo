# MEMORY — Process Window 분석 대시보드 (핸드오프 문서)

다른 에이전트가 이 작업을 이어받기 위한 컨텍스트 요약. 코드에서 자명한 내용보다 "왜 이렇게 했는가"와 현재 상태에 집중.

## 1. 목적 / 사용자
- 반도체 **process window 분석 대시보드**. 사용자는 데이터 분석가이며 **웹 개발 입문자** → 학습하며 구축 중.
- 의사소통 언어: **한국어**. 사용자 이메일 jimin032@gmail.com.
- Python은 **3.10 기준**으로 작성(시스템엔 3.14가 깔려 있어도 코드/의존성은 3.10 호환 유지).

## 2. 기술 스택
- **Frontend**: Vue 3 (`<script setup>`, Composition API) + Vite + ECharts(`vue-echarts`) + axios
- **Backend**: FastAPI + pandas + uvicorn (예제 데이터 생성)
- 차트 라이브러리로 ECharts 선택(혼합차트·markLine·grid 연동·dataZoom 모두 필요해서)

## 3. 파일 구조
```
prc_window/
├── process_window_dashboard_guide.ipynb   # 학습용 노트북(개념+코드 설명)
├── README.md / MEMORY.md
├── backend/
│   ├── main.py        # FastAPI 라우팅 + CORS. 계산은 analytics에 위임
│   ├── analytics.py   # 순수 계산: compute_binned / compute_timeseries / compute_table
│   ├── data.py        # 예제 데이터(long-format) + FEATURE/TARGET/FAB_STEPS + DC_SPEC
│   ├── schemas.py     # pydantic 요청/응답 모델
│   └── requirements.txt  # fastapi/uvicorn/pandas/numpy/pydantic (3.10 호환 핀)
└── frontend/
    ├── vite.config.js  # /api → localhost:8000 proxy
    ├── src/
    │   ├── App.vue          # 레이아웃 + 상태 보유(부모). 조합별 ComboRow 렌더 + 테이블
    │   ├── api/client.js    # fetchColumns/Binned/Timeseries/Table
    │   ├── echarts.js       # 필요한 ECharts 모듈만 use() 등록
    │   └── components/
    │       ├── Sidebar.vue          # 좌측 탭: 체크박스 listbox(검색) + fab_step 드롭다운 + 차트작성
    │       ├── ComboRow.vue         # 조합 1행: spec 헤더 + [WindowChart | ComboTimeSeries]
    │       ├── WindowChart.vue       # binned 혼합차트(bar=count, line=y_avg U-shape) + 수직선
    │       ├── ComboTimeSeries.vue   # 시계열 dual scatter + 이동평균 추세선 + Y슬라이더
    │       └── DataTable.vue         # 요약 테이블
    └── style.css        # 전역 테마(Apple/인디고 톤)
```

## 4. 데이터 모델 (backend/data.py)
- **long-format**: 한 행 = (wafer_id, fab_step). 각 wafer가 4개 fab_step을 거치며 step마다 feature값/trackout_time이 다름.
- 컬럼: wafer_id, fab_step, trackout_time, etch_time/temp/pressure/gas_flow(feature), yield/thickness(target)
- `FEATURE_COLUMNS`, `TARGET_COLUMNS`, `FAB_STEPS=["ETCH_01","ETCH_02","CVD_01","PVD_01"]`
- `DC_SPEC`: **feature별** device-control spec {lower, upper}. (예: etch_time 9~17)
- target은 feature 기준값에서 멀어질수록 커지는 관계 → **window 차트 y_avg가 U-shape**(양끝 상승)으로 보이도록 의도적으로 구성.
- 실제 적용 시 `load_dataframe()`를 DB/CSV 조회로 교체하면 됨.

## 5. API (backend/main.py)
- `GET  /api/columns` → {features, targets, fab_steps, **dc_spec**}
- `POST /api/binned` {fab_step, x_features[], y_targets[], bins=10} → {combos:[{x_feature,y_target,bins[]}]}
- `POST /api/timeseries` {fab_step, x_features[], y_targets[]} → {targets:[{name,points}], features:[{name,points}]}
- `POST /api/table` {**fab_step**, x_features[], y_targets[]} → {rows:[{fab_step,x_feature,x_value,y_target,y_value,dc_lower,dc_upper}]}

## 6. UI 동작 / 핵심 결정사항 (요청 이력 반영)
- **다중 선택**: x_feature, y_target은 **체크박스 listbox**(키워드 검색 가능, 약 4개 표시 후 스크롤). fab_step은 단일 드롭다운.
- **조합(feature×target)마다 한 행(ComboRow)**: 왼쪽 Window 차트 + 오른쪽 매칭 시계열(위=target, 아래=feature). 시계열은 한 차트에 한 feature/target만(스케일 겹침 방지).
- **spec은 조합별**: ComboRow 상단 헤더에 user spec lower/upper 입력 → Window 차트 **빨간 수직선** + 시계열 feature 차트 **빨간 수평선**에 동시 반영.
- **DC spec**: Window 차트에 **검은 수직선**으로 표시. spec 수직선은 두께 2(약 1.5배).
- **시계열 이동평균 추세선**: centered moving average(윈도우≈n/15). 색상 주황(target)/보라(feature), scatter는 반투명. (예전 평탄 avg line은 제거됨)
- **Y축 슬라이더**: Window(우측 1개, count·avg 함께) / 시계열(상·하 grid 각 1개). 시계열 X축은 inside 확대 유지, 하단 X 슬라이더는 제거됨.
- **요약 테이블**: 행 = **선택한 fab_step** × feature × target (※ 최근 수정: 이전엔 모든 fab_step이 나왔으나 선택 step만 나오도록 변경). x_feature/y_target은 **이름만** 표시(값 X). 컬럼 헤더 약어 **USL/USU/DSL/DSU**(title 툴팁 full name). 마지막 컬럼 **user/DC range %** = (user_upper−user_lower)/(dc_upper−dc_lower)×100, 100% 초과 시 빨간 pill.
- **테마**: Apple/인디고(#4f46e5) 톤. 글래스 사이드바, 그라데이션 버튼/브랜드, soft shadow, 카드 hover lift. 토큰은 `src/style.css`의 `:root`.

## 7. 실행 방법
```bash
# 백엔드
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && uvicorn main:app --reload --port 8000   # docs: :8000/docs
# 프론트
cd frontend && npm install && npm run dev   # http://localhost:5173
```

## 8. 현재 상태 / 미해결
- 위 모든 기능 구현·동작 검증 완료(헤드리스 Chrome 스크린샷으로 확인).
- 알려진 함정: 헤드리스 `fullPage` 스크린샷은 ECharts canvas 합성을 누락함 → **viewport 캡처 또는 element.screenshot 사용**할 것. 실제 앱 렌더는 정상.
- `frontend`에 `puppeteer-core`가 `--no-save`로 설치돼 있음(스크린샷 검증용, package.json엔 미포함).

## 9. 다음 단계 후보
- data.py 예제 → 실제 wafer 데이터(CSV/DB) 연결
- 이동평균 윈도우 사용자 조절, fab_step 컬럼을 배지로 빼기, 로딩/에러 UX, 다크모드
- 배포: 프론트 `npm run build` 정적 호스팅 + 백엔드 uvicorn/gunicorn

## 10. 작업 관례
- 변경은 최소·수술적으로(요청 외 리팩터 금지), 기존 스타일 유지, 모호하면 먼저 질문.
- 변경 후 헤드리스 캡처로 시각 검증하고 사용자에게 이미지로 보고하는 흐름을 유지해 왔음.
