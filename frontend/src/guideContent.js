export const guideWorkflowSteps = [
  {
    title: '1. 분석 물량 정의',
    menu: 'Analysis Set',
    body: 'Preset 조건 라이브러리를 불러오거나 FAB 진행 이력(최대 3공정 join)과 EDS 아이템 조건을 새로 구성하고, 시계열 scatter 미리보기로 확인한 뒤 검토할 Lot/Wafer 모집단을 고정합니다.',
  },
  {
    title: '2. BIN Group·조건 Legend 활용',
    menu: '분석대상 선정 / Window Review',
    body: 'BIN Group(Failure Mode)은 Window Review의 BIN Pareto 탭에서 막대를 클릭해 단일 BIN 임시 그룹으로 생성할 수 있습니다. 조건 Rule은 사전 시드된 목록 중에서 선택해 적용하며, ECO·PPID·Tool/Chamber·부품 개조 전후 같은 조건 legend와 before/after 비교는 Window Review의 Commonality 탭(자동 유의성 분석)이나 차트 legend 선택에서 확인합니다.',
  },
  {
    title: '3. Window 관계 확인',
    menu: 'Window Review',
    body: 'BIN Pareto, Driver Ranking으로 원인 후보를 좁히고 Raw Scatter, Binned Response, Trade-off, Time Trend, Commonality, Zone View, Interaction을 보며 SPEC 변경 후보인지 판단합니다.',
  },
  {
    title: '4. Noise 후보는 Rule로 제외',
    menu: 'Window Review',
    body: '이상 wafer를 삭제하지 않고 Exclusion Rule version으로 저장한 뒤 제외 전/후 correlation, slope, fail rate 변화를 비교합니다.',
  },
  {
    title: '5. Spotfire/보고용 Export',
    menu: 'Export / Report',
    body: '필터링 데이터, Analysis Set, BIN Group, Condition Rule, Exclusion Rule과 요약 문장을 내려받아 후속 분석이나 보고에 사용합니다.',
  },
]

export const guideScenarios = [
  {
    title: '시나리오 A. 단위공정팀의 SPEC 완화 요청 검토',
    trigger: '공정 관리 난이도가 높아 Ch.Hole CD 관리 SPEC 완화 요청이 들어온 상황',
    path: ['분석대상 선정에서 해당 Product/Layer/Step 물량 고정 및 Hole-to-Hole + Not Open trade-off pair EDS 아이템 구성', 'Window Review에서 Tool/Chamber와 부품 개조 전후 조건 Rule을 선택해 split 적용', 'Window Review에서 safe window 후보와 high-side/low-side risk 비교', 'Export / Report에서 검토 후보 문장과 CSV 저장'],
    outcome: 'SPEC 완화 가능 여부를 단정하지 않고, 완화 검토 후보/추가 검증 필요/조건별 split spec 후보로 정리합니다.',
  },
  {
    title: '시나리오 B. SPEC 내 관리 중인데 불량이 발생한 경우',
    trigger: 'FAB parameter는 SPEC 안에 있지만 특정 BIN Group 불량률이 상승하는 상황',
    path: ['분석대상 선정에서 abnormal route/rework 제외 조건 확인', 'Window Review의 Condition Split과 Zone View 확인', 'Interaction Heatmap에서 두 FAB parameter 조합 영향 확인', 'Raw Scatter에서 noise wafer 후보를 Exclusion Rule로 저장', '제외 전/후 Window Chart와 summary metric 비교'],
    outcome: '기존 FAB 인자가 원인인지, 다른 공정 noise인지, wafer zone 또는 교호작용 문제인지 검토 경로를 좁힙니다.',
  },
]

export const guideGlossary = [
  { term: 'Analysis Set', meaning: '분석 대상 물량과 제외 조건을 저장한 재실행 가능한 단위' },
  { term: 'BIN Group', meaning: '하나 이상의 EDS BIN을 합산해 만든 Failure Mode metric. 현재는 Window Review의 BIN Pareto 탭에서 막대를 클릭해 단일 BIN짜리 임시 그룹만 만들 수 있습니다.' },
  { term: 'Condition Rule', meaning: '차트 legend와 비교 기준이 되는 rule, 예: 부품 개조 전/후. Window Review에서 사전 시드된 목록 중 선택해 적용합니다(직접 생성 UI는 없음).' },
  { term: 'Exclusion Rule', meaning: '삭제가 아닌 제외 version. 사유와 wafer 목록을 보존합니다.' },
  { term: 'Pending Prediction', meaning: 'EDS 미완료 물량의 BIN Group fail rate 참고 예측' },
]
