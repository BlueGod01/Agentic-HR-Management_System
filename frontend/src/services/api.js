import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

// Attach access token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-refresh on 401
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        try {
          const { data } = await axios.post(`${API_BASE}/auth/refresh`, { refresh_token: refresh })
          localStorage.setItem('access_token', data.access_token)
          localStorage.setItem('refresh_token', data.refresh_token)
          original.headers.Authorization = `Bearer ${data.access_token}`
          return api(original)
        } catch {
          localStorage.clear()
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

export default api

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authAPI = {
  login: (email, password) => api.post('/auth/login', { email, password }),
}

// ── Chat ──────────────────────────────────────────────────────────────────────
export const chatAPI = {
  sendMessage: (message, session_id) => api.post('/chat/message', { message, session_id }),
  getHistory: (session_id) => api.get(`/chat/history/${session_id}`),
  getSessions: () => api.get('/chat/sessions'),
}

// ── Employee ──────────────────────────────────────────────────────────────────
export const employeeAPI = {
  getProfile: () => api.get('/employee/profile'),
  getSalary: () => api.get('/employee/salary'),
  getLeaveBalance: () => api.get('/employee/leave/balance'),
  getLeaveRequests: () => api.get('/employee/leave/requests'),
  requestLeave: (data) => api.post('/employee/leave/request', data),
}

// ── Employer ──────────────────────────────────────────────────────────────────
export const employerAPI = {
  getAlerts: (params) => api.get('/employer/alerts', { params }),
  getAlertSummary: (hours) => api.get('/employer/alerts/summary', { params: { hours } }),
  generateEmail: (data) => api.post('/employer/email/generate', data),
  listDrafts: () => api.get('/employer/email/drafts'),
  approveEmail: (data) => api.post('/employer/email/approve', data),
  sendWhatsApp: (message) => api.post('/employer/whatsapp/send', { message }),
  listEmployees: (params) => api.get('/employer/employees', { params }),
  createEmployee: (data) => api.post('/employer/users/create', data),
  reviewLeave: (id, action) => api.patch(`/employer/leave/${id}/review?action=${action}`),
}
