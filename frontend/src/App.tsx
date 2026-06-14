/**
 * 织梦绮谭 - App 根组件
 * 定义路由和全局布局
 */

import React, { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Home } from '@/pages/Home'
import { Login } from '@/pages/Login'
import { TemplateSelect } from '@/pages/TemplateSelect'
import { Game } from '@/pages/Game'
import { SaveLoad } from '@/pages/SaveLoad'
import { TemplateManage } from '@/pages/TemplateManage'
import { Settings } from '@/pages/Settings'
import { Profile } from '@/pages/Profile'
import { LoadingOverlay } from '@/components/LoadingOverlay'
import { AuthModal } from '@/components/AuthModal'
import { GlobalBgm } from '@/components/GlobalBgm'
import { useAuthStore } from '@/stores/authStore'

const App: React.FC = () => {
  const hydrate = useAuthStore((s) => s.hydrate)

  // 应用启动时从 localStorage 恢复认证状态
  useEffect(() => {
    hydrate()
  }, [hydrate])

  // 应用启动时恢复主题
  useEffect(() => {
    try {
      const savedTheme = localStorage.getItem('dw_theme')
      if (savedTheme) {
        document.documentElement.setAttribute('data-theme', savedTheme)
      }
    } catch {}
  }, [])

  return (
    <>
      {/* 全局加载遮罩 */}
      <LoadingOverlay />

      {/* 全局 BGM */}
      <GlobalBgm />

      {/* 懒登录弹窗 */}
      <AuthModal />

      {/* 路由 */}
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Home />} />
        <Route path="/template-select" element={<TemplateSelect />} />
        <Route path="/game" element={<Game />} />

        {/* 存档管理页面 */}
        <Route path="/load-save" element={<SaveLoad />} />
        <Route path="/templates" element={<TemplateManage />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/profile" element={<Profile />} />

        {/* 兜底：未匹配路由 → 首页 */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  )
}

export default App
