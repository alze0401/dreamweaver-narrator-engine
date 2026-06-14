/**
 * 织梦绮谭 - 登录/注册弹窗组件
 * 当用户未登录但尝试需要认证的操作时弹出
 */

import React, { useState, useEffect, useCallback } from 'react'
import { X, LogIn, UserPlus, Sparkles } from 'lucide-react'
import { authApi } from '@/services/api'
import { useAuthStore } from '@/stores/authStore'

export const AuthModal: React.FC = () => {
  const setAuth = useAuthStore((s) => s.setAuth)

  const [isOpen, setIsOpen] = useState(false)
  const [isLogin, setIsLogin] = useState(true)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // 监听 auth-required 事件
  useEffect(() => {
    const handleAuthRequired = () => {
      setIsOpen(true)
      setError('')
    }
    window.addEventListener('auth-required', handleAuthRequired)
    return () => window.removeEventListener('auth-required', handleAuthRequired)
  }, [])

  const handleClose = useCallback(() => {
    setIsOpen(false)
    setError('')
    setUsername('')
    setPassword('')
    setDisplayName('')
  }, [])

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
      handleClose()
    } catch (err) {
      // 如果是 NEED_LOGIN 错误（来自 401 拦截），不要再次触发弹窗
      if ((err as Error).message === 'NEED_LOGIN') {
        setError('认证失败，请重试')
      } else {
        setError((err as Error).message)
      }
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
      {/* 背景遮罩 */}
      <div
        className="absolute inset-0 bg-surface-dark/90 backdrop-blur-xl"
        onClick={handleClose}
      />

      {/* 主卡片 */}
      <div className="w-full max-w-md relative z-10">
        {/* Logo + 标题 */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/15 mb-3">
            <Sparkles size={24} className="text-primary-light" />
          </div>
          <h2 className="text-xl font-bold text-text-bright tracking-wide">织梦绮谭</h2>
          <p className="text-text-dim/50 text-sm mt-1">登录以继续你的冒险</p>
        </div>

        {/* 表单卡片 */}
        <div className="glass-panel-strong p-6" style={{ borderRadius: '20px' }}>
          {/* 关闭按钮 */}
          <button
            onClick={handleClose}
            className="absolute top-4 right-4 w-8 h-8 rounded-lg flex items-center justify-center
                       bg-surface-light/30 hover:bg-surface-light/50 transition-colors"
          >
            <X size={14} className="text-text-dim" />
          </button>

          {/* 切换 Tab */}
          <div className="flex gap-1 mb-5 bg-surface-dark/40 rounded-xl p-1">
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

            {/* 显示名称（仅注册） */}
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
        <p className="text-center text-text-dim/30 text-[11px] mt-4">
          登录后即可保存进度和管理模板
        </p>
      </div>
    </div>
  )
}
