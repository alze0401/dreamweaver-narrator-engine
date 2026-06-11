/**
 * LoadingOverlay - 全局加载遮罩
 * 织梦绮谭 - 毛玻璃风格加载画面
 */

import React from 'react'
import { useUIStore } from '@/stores/uiStore'

export const LoadingOverlay: React.FC = () => {
  const loading = useUIStore((s) => s.loading)
  const text = useUIStore((s) => s.loadingText)

  if (!loading) return null

  return (
    <div className="fixed inset-0 bg-surface-dark/80 backdrop-blur-md z-[100] flex flex-col
                    items-center justify-center gap-5 animate-fade-in">
      {/* 旋转光环 */}
      <div className="relative w-14 h-14">
        <div className="absolute inset-0 rounded-full border-2 border-primary/10" />
        <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-primary-light
                        animate-spin" />
        <div className="absolute inset-2 rounded-full border border-transparent border-b-accent/40
                        animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }} />
      </div>
      <p className="text-text-bright text-base font-light tracking-wide">{text || '加载中...'}</p>
    </div>
  )
}
