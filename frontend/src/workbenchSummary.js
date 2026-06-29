const pct = (value) => (value == null ? '-' : `${(Number(value) * 100).toFixed(2)}%`)
const count = (value) => Number(value || 0).toLocaleString()
const windowText = (safeWindow) => {
  if (!safeWindow || safeWindow.lower == null || safeWindow.upper == null) return '-'
  return `${Number(safeWindow.lower).toFixed(2)} ~ ${Number(safeWindow.upper).toFixed(2)}`
}

const basisMap = new Map([
  ['High-side fail rate rises.', 'High-side 불량률 상승이 확인되어 SPEC 완화 전 추가 검토가 필요합니다.'],
])

function cautiousCandidate(firstCandidate) {
  if (!firstCandidate) return '추가 검증 필요 후보: 조건 분리와 교호작용을 확인해야 합니다.'
  const basis = basisMap.get(firstCandidate.basis) || firstCandidate.basis || '근거 확인 필요'
  return `${firstCandidate.type}: ${basis}`
}

export function summarizeWindowReview(review) {
  const metrics = review?.summary_metrics || {}
  const firstCandidate = review?.decision_candidates?.[0]
  const primaryCandidate = cautiousCandidate(firstCandidate)

  return {
    waferText: `${count(metrics.wafer_count)}매`,
    actualText: `Actual ${count(metrics.actual_wafer_count)}매`,
    pendingText: `Pending ${count(metrics.pending_wafer_count)}매`,
    failRateText: pct(metrics.high_side_fail_rate),
    lowFailRateText: pct(metrics.low_side_fail_rate),
    correlationText: metrics.correlation == null ? '-' : Number(metrics.correlation).toFixed(2),
    safeWindowText: windowText(metrics.safe_window),
    primaryCandidate,
    xParameter: review?.context?.x_parameter || '-',
    yMetric: review?.context?.bin_groups?.[0]?.name || '-',
  }
}
