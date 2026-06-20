// 모든 백엔드 호출을 이 파일 한 곳에 모은다.
// dev: Vite proxy(/api) 사용. 운영: VITE_API_BASE_URL 환경변수로 교체.
import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'

const api = axios.create({ baseURL, timeout: 20000 })

// 실패를 종류별로 구분해 던진다(네트워크/타임아웃/HTTP/형식).
function toAppError(e) {
  if (e.code === 'ECONNABORTED') return { kind: 'timeout', message: '요청 시간이 초과되었습니다.' }
  if (e.response) return { kind: 'http', status: e.response.status, message: `서버 오류(${e.response.status})` }
  if (e.request) return { kind: 'network', message: '백엔드에 연결할 수 없습니다. (uvicorn 8000 실행 여부 확인)' }
  return { kind: 'unknown', message: e.message || '알 수 없는 오류' }
}

async function call(fn) {
  try {
    return await fn()
  } catch (e) {
    throw toAppError(e)
  }
}

export function fetchColumns() {
  return call(async () => (await api.get('/columns')).data)
}

export function fetchXFeatureOptions(fabStep, { matching = true, metroGrade = null, metroCategory = null } = {}) {
  return call(async () => {
    const params = { fab_step: fabStep, matching }
    if (metroGrade) params.metro_grade = metroGrade
    if (metroCategory) params.metro_category = metroCategory
    return (await api.get('/x-feature-options', { params })).data
  })
}

export function fetchBinned(cond) {
  return call(async () => (await api.post('/binned', cond)).data)
}

export function fetchTimeseries(cond) {
  return call(async () => (await api.post('/timeseries', cond)).data)
}

export function fetchTable(cond) {
  return call(async () => (await api.post('/table', cond)).data)
}

export function fetchInteraction(req) {
  return call(async () => (await api.post('/interaction', req)).data)
}

export function fetchDrivers(cond) {
  return call(async () => (await api.post('/drivers', cond)).data)
}
