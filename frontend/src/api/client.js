// 모든 백엔드 호출을 이 파일 한 곳에 모음.
import axios from 'axios'

const api = axios.create({ baseURL: '/api' }) // vite proxy가 8000으로 전달

export async function fetchColumns() {
  const res = await api.get('/columns')
  return res.data // { features, targets, fab_steps }
}

export async function fetchBinned(fabStep, xFeatures, yTargets, bins = 10) {
  const res = await api.post('/binned', {
    fab_step: fabStep, x_features: xFeatures, y_targets: yTargets, bins,
  })
  return res.data // { fab_step, combos: [...] }
}

export async function fetchTimeseries(fabStep, xFeatures, yTargets) {
  const res = await api.post('/timeseries', {
    fab_step: fabStep, x_features: xFeatures, y_targets: yTargets,
  })
  return res.data // { fab_step, targets:[...], features:[...] }
}

export async function fetchTable(fabStep, xFeatures, yTargets) {
  const res = await api.post('/table', { fab_step: fabStep, x_features: xFeatures, y_targets: yTargets })
  return res.data // { rows: [...] }
}
