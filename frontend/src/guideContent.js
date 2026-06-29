export const guideWorkflowSteps = [
  {
    title: '1. 분석 물량 정의',
    menu: 'Analysis Set',
    body: '기간, Product, Layer, Step, FAB parameter, EDS 완료 여부와 제외 조건을 정해 검토할 Lot/Wafer 모집단을 고정합니다.',
  },
  {
    title: '2. BIN Group 정의',
    menu: 'BIN Group',
    body: '단일 EDS BIN 또는 여러 BIN의 sum으로 Failure Mode를 만듭니다. Hole-to-Hole과 Ch.Hole Not Open처럼 trade-off 관계인 그룹을 함께 선택합니다.',
  },
  {
    title: '3. 조건 Legend 정의',
    menu: 'Condition Rule',
    body: 'ECO, PPID, Tool/Chamber, Recipe, PM age, 부품 개조 전후 같은 비교 기준을 정합니다.',
  },
  {
    title: '4. Window 관계 확인',
    menu: 'Window Review',
    body: 'Raw Scatter, Binned Response, Trade-off, Time Trend, Zone View, Interaction을 보며 SPEC 변경 후보인지 판단합니다.',
  },
  {
    title: '5. Noise 후보는 Rule로 제외',
    menu: 'Window Review',
    body: '이상 wafer를 삭제하지 않고 Exclusion Rule version으로 저장한 뒤 제외 전/후 correlation, slope, fail rate 변화를 비교합니다.',
  },
  {
    title: '6. Pending 물량 리스크 확인',
    menu: 'Pending Prediction',
    body: 'FAB/FDC는 확보됐지만 EDS가 미완료인 wafer의 BIN Group fail rate를 예측 범위와 confidence와 함께 확인합니다.',
  },
  {
    title: '7. Spotfire/보고용 Export',
    menu: 'Export / Report',
    body: '필터링 데이터, Analysis Set, BIN Group, Condition Rule, Exclusion Rule과 요약 문장을 내려받아 후속 분석이나 보고에 사용합니다.',
  },
]

export const guideScenarios = [
  {
    title: '시나리오 A. 단위공정팀의 SPEC 완화 요청 검토',
    trigger: '공정 관리 난이도가 높아 Ch.Hole CD 관리 SPEC 완화 요청이 들어온 상황',
    path: ['Analysis Set에서 해당 Product/Layer/Step 물량 고정', 'BIN Group에서 Hole-to-Hole + Not Open trade-off pair 선택', 'Condition Rule에서 Tool/Chamber와 부품 개조 전후 split 적용', 'Window Review에서 safe window 후보와 high-side/low-side risk 비교', 'Export / Report에서 검토 후보 문장과 CSV 저장'],
    outcome: 'SPEC 완화 가능 여부를 단정하지 않고, 완화 검토 후보/추가 검증 필요/조건별 split spec 후보로 정리합니다.',
  },
  {
    title: '시나리오 B. ECO/PPID/Recipe 변경 후 사전 리스크 점검',
    trigger: '공정조건 변경 후 아직 EDS가 완료되지 않은 물량이 누적되는 상황',
    path: ['Analysis Set에서 Include pending 선택', 'Condition Rule에서 ECO 또는 PPID split 선택', 'Window Review의 Time Trend에서 변경 event 전후 확인', 'Pending Prediction에서 pending wafer risk table 확인', 'EDS 완료 후 backtest metric으로 예측 품질 확인'],
    outcome: 'Actual EDS와 Predicted Pending EDS를 분리해서 보고, confidence가 낮은 조건은 추적 대상으로 남깁니다.',
  },
  {
    title: '시나리오 C. SPEC 내 관리 중인데 불량이 발생한 경우',
    trigger: 'FAB parameter는 SPEC 안에 있지만 특정 BIN Group 불량률이 상승하는 상황',
    path: ['Analysis Set에서 abnormal route/rework 제외 조건 확인', 'Window Review의 Condition Split과 Zone View 확인', 'Interaction Heatmap에서 두 FAB parameter 조합 영향 확인', 'Raw Scatter에서 noise wafer 후보를 Exclusion Rule로 저장', '제외 전/후 Window Chart와 summary metric 비교'],
    outcome: '기존 FAB 인자가 원인인지, 다른 공정 noise인지, wafer zone 또는 교호작용 문제인지 검토 경로를 좁힙니다.',
  },
]

export const guideGlossary = [
  { term: 'Analysis Set', meaning: '분석 대상 물량과 제외 조건을 저장한 재실행 가능한 단위' },
  { term: 'BIN Group', meaning: '하나 이상의 EDS BIN을 합산해 정의한 Failure Mode metric' },
  { term: 'Condition Rule', meaning: '차트 legend와 비교 기준을 만드는 rule, 예: 부품 개조 전/후' },
  { term: 'Exclusion Rule', meaning: '삭제가 아닌 제외 version. 사유와 wafer 목록을 보존합니다.' },
  { term: 'Pending Prediction', meaning: 'EDS 미완료 물량의 BIN Group fail rate 참고 예측' },
]
