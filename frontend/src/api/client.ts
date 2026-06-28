import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

export const exportUrl = (path: string) => `/api${path}`
