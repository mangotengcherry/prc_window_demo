// 색맹 안전(Okabe-Ito 기반) 차트 색 — 차트 컴포넌트의 단일 색 출처.
// spec 선은 색 + dash + 라벨로 이중 인코딩하여 적록색약에서도 구분되게 한다.
export const PALETTE = {
  specUser: '#D55E00', // vermillion — user spec
  specDc: '#3f3f46', //   zinc-700  — DC spec (순흑 대신 살짝 완화: pastel 데이터 위에서 과하지 않게)
  count: '#cfe3f5', //    window bar (wafer count)
  avg: '#0072B2', //      window y avg line (blue)
  ciFill: 'rgba(0, 114, 178, 0.16)', // 신뢰구간 band
  tsTarget: '#56B4E9', // 시계열 target scatter (sky)
  tsTargetMa: '#E69F00', // target 이동평균 (orange)
  tsFeature: '#009E73', // 시계열 feature scatter (green)
  tsFeatureMa: '#CC79A7', // feature 이동평균 (purple)
  faint: 'rgba(17, 17, 26, 0.28)',
  estimate: '#CC79A7', // 추정 y (속이 빈 다이아몬드로 관측값과 구분)
}

// 분할값(category feature) 오버레이용 범주 색 — multi-line 모드에서 값별 라인 구분.
// spec 색(vermillion/black)과 충돌하지 않는 Okabe-Ito 계열 순서.
export const SERIES = ['#0072B2', '#E69F00', '#009E73', '#CC79A7', '#56B4E9']

// 교호작용 scatter/heatmap value 색 — 팀 컨벤션: 높을수록 빨강, 낮을수록 회색.
export const HEAT_RAMP = ['#d9d9d9', '#fcae91', '#fb6a4a', '#de2d26', '#a50f15']
