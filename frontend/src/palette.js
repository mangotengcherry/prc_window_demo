// 색맹 안전(Okabe-Ito 기반) 차트 색 — 차트 컴포넌트의 단일 색 출처.
// spec 선은 색 + dash + 라벨로 이중 인코딩하여 적록색약에서도 구분되게 한다.
export const PALETTE = {
  specUser: '#D55E00', // vermillion — user spec
  specDc: '#111111', //   black     — DC spec
  count: '#cfe3f5', //    window bar (wafer count)
  avg: '#0072B2', //      window y avg line (blue)
  ciFill: 'rgba(0, 114, 178, 0.16)', // 신뢰구간 band
  tsTarget: '#56B4E9', // 시계열 target scatter (sky)
  tsTargetMa: '#E69F00', // target 이동평균 (orange)
  tsFeature: '#009E73', // 시계열 feature scatter (green)
  tsFeatureMa: '#CC79A7', // feature 이동평균 (purple)
  faint: 'rgba(17, 17, 26, 0.28)',
}
