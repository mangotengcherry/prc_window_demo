import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

api.interceptors.request.use((config) => {
  config.headers['X-User'] = localStorage.getItem('workbench_user') || 'me'
  return config
})

export const exportUrl = (path: string) => `/api${path}`
