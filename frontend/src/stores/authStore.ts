/**
 * 织梦绮谭 - 认证状态 Store
 * 管理用户登录状态、Token、用户信息
 */

import { create } from 'zustand'
import type { AuthUser } from '@/types'

interface AuthState {
  token: string | null
  user: AuthUser | null
  isAuthenticated: boolean

  /** 登录成功后设置 */
  setAuth: (token: string, user: AuthUser) => void

  /** 退出登录 */
  logout: () => void

  /** 从 localStorage 恢复（应用启动时调用） */
  hydrate: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  isAuthenticated: false,

  setAuth: (token, user) => {
    try { localStorage.setItem('dw_token', token) } catch {}
    try { localStorage.setItem('dw_user', JSON.stringify(user)) } catch {}
    set({ token, user, isAuthenticated: true })
  },

  logout: () => {
    try { localStorage.removeItem('dw_token') } catch {}
    try { localStorage.removeItem('dw_user') } catch {}
    set({ token: null, user: null, isAuthenticated: false })
  },

  hydrate: () => {
    try {
      const token = localStorage.getItem('dw_token')
      const userStr = localStorage.getItem('dw_user')
      if (token && userStr) {
        const parsed = JSON.parse(userStr)
        // 校验必要字段，防止旧版脏数据导致 UI 显示异常
        if (
          parsed &&
          typeof parsed.id === 'string' &&
          typeof parsed.username === 'string' &&
          parsed.username.length > 0
        ) {
          const user = parsed as AuthUser
          set({ token, user, isAuthenticated: true })
        } else {
          // 脏数据：清除并拒绝恢复登录态
          localStorage.removeItem('dw_token')
          localStorage.removeItem('dw_user')
        }
      }
    } catch {
      // JSON 解析失败等异常，清除脏数据
      try { localStorage.removeItem('dw_token') } catch {}
      try { localStorage.removeItem('dw_user') } catch {}
    }
  },
}))
