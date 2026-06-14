/**
 * 织梦绮谭 - 登录/注册页面
 * Galgame 风格毛玻璃 UI
 */

import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogIn, UserPlus, Sparkles } from 'lucide-react'
import { authApi } from '@/services/api'
import { useAuthStore } from '@/stores/authStore'

export const Login: React.FC = () => {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)

  const [isLogin, setIsLogin] = useState(true)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password.trim()) {
      setError('请输入用户名和密码')
      return
    }
    setError('')
    setLoading(true)

    try {
      const res = isLogin
        ? await authApi.login(username.trim(), password)
        : await authApi.register(username.trim(), password, displayName.trim() || undefined)

      setAuth(res.access_token, res.user)
      navigate('/')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-surface-dark flex items-center justify-center p-4 relative overflow-hidden">
      {/* 背景装饰 */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full bg-primary/5 blur-[120px]" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 rounded-full bg-pink-500/5 blur-[100px]" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-indigo-500/[0.03] blur-[150px]" />
      </div>

      {/* 主卡片 */}
      <div className="w-full max-w-md relative z-10">
        {/* Logo + 标题 */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/15 mb-4">
            <Sparkles size={28} className="text-primary-light" />
          </div>
          <h1 className="text-2xl font-bold text-text-bright tracking-wide">织梦绮谭</h1>
          <p className="text-text-dim/50 text-sm mt-1">AI 驱动的 Galgame 叙事引擎</p>
        </div>

        {/* 表单卡片 */}
        <div className="glass-panel-strong p-8" style={{ borderRadius: '20px' }}>
          {/* 切换 Tab */}
          <div className="flex gap-1 mb-6 bg-surface-dark/40 rounded-xl p-1">
            <button
              onClick={() => { setIsLogin(true); setError('') }}
              className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all duration-300
                ${isLogin
                  ? 'bg-primary/20 text-primary-light'
                  : 'text-text-dim/50 hover:text-text-dim'
                }`}
            >
              登录
            </button>
            <button
              onClick={() => { setIsLogin(false); setError('') }}
              className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all duration-300
                ${!isLogin
                  ? 'bg-primary/20 text-primary-light'
                  : 'text-text-dim/50 hover:text-text-dim'
                }`}
            >
              注册
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* 用户名 */}
            <div>
              <label className="text-text-dim/60 text-xs block mb-1.5 tracking-wide">用户名</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="请输入用户名"
                className="w-full bg-surface-dark/60 text-text-bright border border-white/[0.06]
                           focus:border-primary/40 rounded-xl px-4 py-3 outline-none transition-colors
                           placeholder:text-text-dim/25 text-sm"
                autoComplete="username"
              />
            </div>

            {/* 密码 */}
            <div>
              <label className="text-text-dim/60 text-xs block mb-1.5 tracking-wide">密码</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={isLogin ? '请输入密码' : '至少 6 位密码'}
                className="w-full bg-surface-dark/60 text-text-bright border border-white/[0.06]
                           focus:border-primary/40 rounded-xl px-4 py-3 outline-none transition-colors
                           placeholder:text-text-dim/25 text-sm"
                autoComplete={isLogin ? 'current-password' : 'new-password'}
              />
            </div>

            {/* 显示名（仅注册） */}
            {!isLogin && (
              <div className="animate-fade-in">
                <label className="text-text-dim/60 text-xs block mb-1.5 tracking-wide">显示名称（可选）</label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="你在游戏中的称呼"
                  className="w-full bg-surface-dark/60 text-text-bright border border-white/[0.06]
                             focus:border-primary/40 rounded-xl px-4 py-3 outline-none transition-colors
                             placeholder:text-text-dim/25 text-sm"
                />
              </div>
            )}

            {/* 错误提示 */}
            {error && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-2.5 text-red-300 text-xs animate-fade-in">
                {error}
              </div>
            )}

            {/* 提交按钮 */}
            <button
              type="submit"
              disabled={loading}
              className="w-full btn-gradient flex items-center justify-center gap-2 px-6 py-3
                         text-white rounded-xl font-medium text-sm transition-all duration-300
                         disabled:opacity-50 disabled:cursor-not-allowed
                         shadow-[0_4px_16px_rgba(168,130,255,0.25)]"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  {isLogin ? '登录中...' : '注册中...'}
                </span>
              ) : (
                <>
                  {isLogin ? <LogIn size={15} /> : <UserPlus size={15} />}
                  {isLogin ? '登录' : '注册'}
                </>
              )}
            </button>
          </form>
        </div>

        {/* 底部提示 */}
        <p className="text-center text-text-dim/30 text-[11px] mt-6">
          管理员账号: admin / zxz.18730988025
        </p>
      </div>
    </div>
  )
}
