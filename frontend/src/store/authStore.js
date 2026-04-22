import { create } from 'zustand'
import { authAPI } from '../services/api'

const useAuthStore = create((set) => ({
  user: null,
  role: localStorage.getItem('role') || null,
  isAuthenticated: !!localStorage.getItem('access_token'),
  isLoading: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null })
    try {
      const { data } = await authAPI.login(email, password)
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      localStorage.setItem('role', data.role)
      localStorage.setItem('user_id', data.user_id)
      set({
        isAuthenticated: true,
        role: data.role,
        user: { id: data.user_id, role: data.role },
        isLoading: false,
      })
      return { success: true, role: data.role }
    } catch (err) {
      const msg = err.response?.data?.detail || 'Login failed'
      set({ isLoading: false, error: msg })
      return { success: false, error: msg }
    }
  },

  logout: () => {
    localStorage.clear()
    set({ isAuthenticated: false, user: null, role: null })
  },
}))

export default useAuthStore
