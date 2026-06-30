import { api } from './client.ts'

export type ApiRecord = Record<string, any>

export async function resetMockData() {
  const { data } = await api.post('/mock-data/reset')
  return data
}

export async function fetchMetadata() {
  const { data } = await api.get('/metadata')
  return data
}

export async function createAnalysisSet(payload: ApiRecord) {
  const { data } = await api.post('/analysis-sets', payload)
  return data
}

export async function fetchAnalysisSets() {
  const { data } = await api.get('/analysis-sets')
  return data
}

export async function fetchAnalysisConditions() {
  const { data } = await api.get('/analysis-conditions')
  return data
}

export async function copyAnalysisConditionToPersonal(conditionId: string, payload: ApiRecord) {
  const { data } = await api.post(`/analysis-conditions/${conditionId}/copy-personal`, payload)
  return data
}

export async function updateAnalysisCondition(conditionId: string, payload: ApiRecord) {
  const { data } = await api.patch(`/analysis-conditions/${conditionId}`, payload)
  return data
}

export async function createAnalysisSetFromCondition(conditionId: string) {
  const { data } = await api.post(`/analysis-conditions/${conditionId}/analysis-set`)
  return data
}

export async function createBinGroup(payload: ApiRecord) {
  const { data } = await api.post('/bin-groups', payload)
  return data
}

export async function fetchBinGroups() {
  const { data } = await api.get('/bin-groups')
  return data
}

export async function createConditionRule(payload: ApiRecord) {
  const { data } = await api.post('/condition-rules', payload)
  return data
}

export async function fetchConditionRules() {
  const { data } = await api.get('/condition-rules')
  return data
}

export async function fetchWindowReview(payload: ApiRecord) {
  const { data } = await api.post('/window-review', payload)
  return data
}

export async function createExclusionRule(payload: ApiRecord) {
  const { data } = await api.post('/exclusion-rules', payload)
  return data
}

export async function fetchExclusionRules() {
  const { data } = await api.get('/exclusion-rules')
  return data
}

export async function fetchPendingPrediction(payload: ApiRecord) {
  const { data } = await api.post('/pending-prediction', payload)
  return data
}

export async function fetchReport(runId: string) {
  const { data } = await api.get(`/export/report/${runId}`)
  return data
}
