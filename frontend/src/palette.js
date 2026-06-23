// 차트 색상 — UI의 teal accent와 조화되도록 정리한 색맹 안전 팔레트.
// spec 선은 색 + dash + 라벨로 이중 인코딩해 적록색각 이상에서도 구분한다.
export const PALETTE = {
  specUser: '#C2410C', // user spec: burnt orange
  specDc: '#334155', // DC spec: slate
  count: '#D8E8E5', // window bar: muted teal
  avg: '#0F766E', // window y average
  ciFill: 'rgba(15, 118, 110, 0.15)',
  tsTarget: '#3B82F6',
  tsTargetMa: '#0F766E',
  tsFeature: '#64748B',
  tsFeatureMa: '#7C3AED',
  faint: 'rgba(23, 33, 43, 0.28)',
  estimate: '#C026D3',
}

// 분할값(category feature) overlay. spec 색과 충돌하지 않는 순서.
export const SERIES = ['#0F766E', '#2563EB', '#D97706', '#7C3AED', '#DB2777', '#475569']

// 교호작용 scatter/heatmap: 낮음은 중립, 높음은 위험 신호에 가까운 red.
export const HEAT_RAMP = ['#E5E7EB', '#CBD5E1', '#FDBA74', '#F97316', '#B91C1C']
