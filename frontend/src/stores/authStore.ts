import { create } from 'zustand'
import * as authApi from '../api/auth'
import type { User } from '../types'

const TOKEN_KEY = 'access_token'
const REFRESH_KEY = 'refresh_token'

interface AuthState {
  user: User | null
  loading: boolean
  initialized: boolean

  init: () => Promise<void>
  login: (username: string, password: string) => Promise<void>
  register: (username: string, password: string, passwordConfirm: string) => Promise<void>
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: false,
  initialized: false,

  init: async () => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      set({ initialized: true })
      return
    }
    try {
      const user = await authApi.getMe()
      set({ user, initialized: true })
    } catch {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(REFRESH_KEY)
      set({ user: null, initialized: true })
    }
  },

  login: async (username, password) => {
    set({ loading: true })
    try {
      const tokens = await authApi.login({ username, password })
      localStorage.setItem(TOKEN_KEY, tokens.access)
      localStorage.setItem(REFRESH_KEY, tokens.refresh)
      const user = await authApi.getMe()
      set({ user, loading: false })
    } catch (e) {
      set({ loading: false })
      throw e
    }
  },

  register: async (username, password, passwordConfirm) => {
    set({ loading: true })
    try {
      await authApi.register({
        username,
        password,
        password_confirm: passwordConfirm,
      })
      const tokens = await authApi.login({ username, password })
      localStorage.setItem(TOKEN_KEY, tokens.access)
      localStorage.setItem(REFRESH_KEY, tokens.refresh)
      const user = await authApi.getMe()
      set({ user, loading: false })
    } catch (e) {
      set({ loading: false })
      throw e
    }
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
    set({ user: null })
  },
}))
