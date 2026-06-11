/**
 * 织梦绮谭 - App 根组件
 * 定义路由和全局布局
 */

import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Home } from '@/pages/Home'
import { TemplateSelect } from '@/pages/TemplateSelect'
import { Game } from '@/pages/Game'
import { SaveLoad } from '@/pages/SaveLoad'
import { LoadingOverlay } from '@/components/LoadingOverlay'

const App: React.FC = () => {
  return (
    <>
      {/* 全局加载遮罩 */}
      <LoadingOverlay />

      {/* 路由 */}
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/template-select" element={<TemplateSelect />} />
        <Route path="/game" element={<Game />} />

        {/* 存档管理页面 */}
        <Route path="/load-save" element={<SaveLoad />} />
        <Route path="/templates" element={<Home />} />

        {/* 兜底：未匹配路由 → 首页 */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  )
}

export default App
