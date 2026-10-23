import axios from 'axios'

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({ baseURL: `${API_URL}/api/v1` })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Turn FastAPI error payloads (string or validation list) into one readable message.
export function errorMessage(err) {
  const detail = err.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((d) => `${d.loc?.slice(-1)[0]}: ${d.msg}`).join('; ')
  return detail || err.message || 'Something went wrong'
}

export default api
