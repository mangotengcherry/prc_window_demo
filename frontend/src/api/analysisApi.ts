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

// ---------------------------------------------------------------------------
// 조건 라이브러리(Preset) + 물량 선정 미리보기 (§8)
// ---------------------------------------------------------------------------

export async function fetchPresetTree() {
  const { data } = await api.get('/preset-tree')
  return data
}

export async function createPresetFolder(name: string) {
  const { data } = await api.post('/preset-folders', { name })
  return data
}

export async function createPreset(payload: ApiRecord) {
  const { data } = await api.post('/presets', payload)
  return data
}

export async function addPresetRevision(presetId: string, payload: ApiRecord) {
  const { data } = await api.post(`/presets/${presetId}/revisions`, payload)
  return data
}

export async function fetchPresetRevision(presetId: string, rev: number) {
  const { data } = await api.get(`/presets/${presetId}/revisions/${rev}`)
  return data
}

export async function patchPreset(presetId: string, payload: ApiRecord) {
  const { data } = await api.patch(`/presets/${presetId}`, payload)
  return data
}

export async function duplicatePreset(presetId: string, payload: ApiRecord) {
  const { data } = await api.post(`/presets/${presetId}/duplicate`, payload)
  return data
}

export async function deletePreset(presetId: string) {
  const { data } = await api.delete(`/presets/${presetId}`)
  return data
}

export async function validateExpression(payload: ApiRecord) {
  const { data } = await api.post('/expressions/validate', payload)
  return data
}

export async function fetchSelectionPreview(payload: ApiRecord) {
  const { data } = await api.post('/selection/preview', payload)
  return data
}

export async function fetchCustomEdsItems() {
  const { data } = await api.get('/custom-eds-items')
  return data
}

export async function createCustomEdsItem(payload: ApiRecord) {
  const { data } = await api.post('/custom-eds-items', payload)
  return data
}

export async function deleteCustomEdsItem(name: string) {
  const { data } = await api.delete(`/custom-eds-items/${name}`)
  return data
}
