export const ANALYSIS_SELECTION_STEPS = [
  { key: 'fab', title: 'FAB 기준 검색 조건 설정' },
  { key: 'eds', title: 'EDS 기준 검색 조건 설정' },
  { key: 'legend', title: '비교 대상 Legend 설정' },
]

const stepOrder = ANALYSIS_SELECTION_STEPS.map((step) => step.key)

export function conditionScopeLabel(condition) {
  return condition?.scope === 'shared' ? '공유 조건' : '개인 조건'
}

export function isEditableCondition(condition) {
  return Boolean(condition && condition.scope === 'personal' && condition.readonly === false)
}

export function describePeriod(fabFilters = {}) {
  if (fabFilters.date_mode === 'recent_days') {
    return `최근 ${fabFilters.recent_days || 30}일`
  }
  if (fabFilters.start_date && fabFilters.end_date) {
    return `${fabFilters.start_date} ~ ${fabFilters.end_date}`
  }
  return '기간 미설정'
}

export function nextStepKey(currentKey) {
  const index = stepOrder.indexOf(currentKey)
  return stepOrder[Math.min(index + 1, stepOrder.length - 1)] || stepOrder[0]
}

export function previousStepKey(currentKey) {
  const index = stepOrder.indexOf(currentKey)
  return stepOrder[Math.max(index - 1, 0)] || stepOrder[0]
}

export function summarizeCondition(condition = {}) {
  const analysisFilters = condition.analysis_filters || {}
  const legendConfig = condition.legend_config || {}
  return {
    title: `${condition.process_key || '공정'} / ${condition.revision || 'revision'}`,
    name: condition.name || '-',
    scopeLabel: conditionScopeLabel(condition),
    editable: isEditableCondition(condition),
    period: describePeriod(condition.fab_filters),
    product: (analysisFilters.product || ['All']).join(', '),
    step: (analysisFilters.step || ['All']).join(', '),
    edsStatus: analysisFilters.eds_status === 'actual_only' ? 'EDS 확보 물량만' : 'Pending 포함',
    binGroups: (condition.selected_bin_group_ids || []).join(', ') || '-',
    legendBasis: legendConfig.basis || '-',
  }
}
