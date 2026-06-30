export const guideWorkflowSteps = [
  {
    title: '1. 분석물량 선정',
    menu: '분석물량 선정',
    body: '공유 조건 또는 개인 조건을 불러온 뒤 FAB 기준, EDS 기준, 비교 Legend를 단계적으로 확인합니다.',
  },
  {
    title: '2. 조건 이력 재사용',
    menu: '분석물량 선정',
    body: 'Ch.Hole initial/rev1/rev2 같은 공유 조건은 읽기 전용으로 로드하고, 수정이 필요하면 개인 조건으로 복사합니다.',
  },
  {
    title: '3. EDS 확보 물량만 고정',
    menu: '분석물량 선정',
    body: 'Pending 예측 없이 EDS actual wafer만 FAB Data 추출 대상으로 사용하고, Window Review에 사용할 BIN Group을 선택합니다.',
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
    title: '6. Spotfire/보고용 Export',
    menu: 'Export / Report',
    body: '분석물량 조건, BIN Group, Condition Rule, Exclusion Rule과 요약 문장을 내려받아 후속 분석이나 보고에 사용합니다.',
  },
]

export const guideScenarios = [
  {
    title: '시나리오 A. 단위공정팀의 SPEC 완화 요청 검토',
    trigger: '공정 관리 난이도가 높아 Ch.Hole CD 관리 SPEC 완화 요청이 들어온 상황',
    path: ['분석물량 선정에서 Ch.Hole rev 조건 로드', '필요하면 개인 조건으로 복사해 기간 또는 Tool 조건 수정', 'EDS 기준에서 Hole-to-Hole + Not Open trade-off pair 선택', 'Legend에서 부품 개조 전후 split 적용', 'Window Review에서 safe window 후보와 high-side/low-side risk 비교'],
    outcome: 'SPEC 완화 가능 여부를 단정하지 않고, 완화 검토 후보/추가 검증 필요/조건별 split spec 후보로 정리합니다.',
  },
  {
    title: '시나리오 B. ECO/PPID/Recipe 변경 후 사전 리스크 점검',
    trigger: '공정조건 변경 후 EDS가 확보된 물량 기준으로 revision별 Window를 비교하려는 상황',
    path: ['분석물량 선정의 공유 조건에서 해당 공정 revision 선택', '최근 N일 또는 고정 기간으로 EDS 확보 물량 범위 설정', 'Legend에서 ECO 또는 PPID split 선택', 'Window Review의 Time Trend에서 변경 event 전후 확인', 'Export / Report에서 조건과 결과 저장'],
    outcome: 'EDS actual 기준으로 revision 전후 Window 변화와 조건별 split 차이를 비교합니다.',
  },
  {
    title: '시나리오 C. SPEC 내 관리 중인데 불량이 발생한 경우',
    trigger: 'FAB parameter는 SPEC 안에 있지만 특정 BIN Group 불량률이 상승하는 상황',
    path: ['분석물량 선정에서 abnormal route/rework 제외 조건 확인', 'Window Review의 Condition Split과 Zone View 확인', 'Interaction Heatmap에서 두 FAB parameter 조합 영향 확인', 'Raw Scatter에서 noise wafer 후보를 Exclusion Rule로 저장', '제외 전/후 Window Chart와 summary metric 비교'],
    outcome: '기존 FAB 인자가 원인인지, 다른 공정 noise인지, wafer zone 또는 교호작용 문제인지 검토 경로를 좁힙니다.',
  },
]

export const guideGlossary = [
  { term: '분석물량 선정', meaning: 'FAB/EDS/Legend 조건을 공유 조건 또는 개인 조건으로 불러와 Window Review에 넘기는 단계' },
  { term: '공유 조건', meaning: '프로젝트/공정별 표준 조건. 읽기 전용이며 개인 조건으로 복사해서 수정합니다.' },
  { term: '개인 조건', meaning: '사용자가 복사하거나 새로 만든 수정 가능한 조건' },
  { term: 'Analysis Set', meaning: '분석 대상 물량과 제외 조건을 저장한 재실행 가능한 단위' },
  { term: 'BIN Group', meaning: '하나 이상의 EDS BIN을 합산해 정의한 Failure Mode metric' },
  { term: 'Condition Rule', meaning: '차트 legend와 비교 기준을 만드는 rule, 예: 부품 개조 전/후' },
  { term: 'Exclusion Rule', meaning: '삭제가 아닌 제외 version. 사유와 wafer 목록을 보존합니다.' },
]
