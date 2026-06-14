/**
 * AvatarLightbox - 头像放大查看浮层
 * 织梦绮谭 - 点击角色头像后弹出大图预览
 */

import React, { useEffect, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'

interface Props {
  /** 头像 URL */
  src: string
  /** 角色名（用于 alt 文本） */
  alt?: string
  /** 关闭 */
  onClose: () => void
}

export const AvatarLightbox: React.FC<Props> = ({ src, alt = '角色头像', onClose }) => {
  const [imgFailed, setImgFailed] = React.useState(false)

  // src 变化时重置失败状态
  React.useEffect(() => { setImgFailed(false) }, [src])

  // 按 ESC 关闭
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    },
    [onClose],
  )

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  // 阻止背景滚动
  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = prev }
  }, [])

  return createPortal(
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center bg-black/75 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      {/* 图片容器 */}
      <div
        className="relative max-w-[80vw] max-h-[80vh] animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 关闭按钮 */}
        <button
          onClick={onClose}
          className="absolute -top-3 -right-3 w-8 h-8 rounded-full
                     bg-surface-dark/80 border border-white/10
                     flex items-center justify-center
                     hover:bg-red-500/60 transition-colors z-10"
        >
          <X size={14} className="text-white" />
        </button>

        {/* 头像图片 */}
        {imgFailed ? (
          <div className="w-48 h-48 rounded-2xl bg-gradient-to-br from-primary/20 to-accent/10
                          flex items-center justify-center ring-2 ring-primary/30">
            <span className="text-5xl font-display text-primary/40">
              {alt ? alt.charAt(0) : '?'}
            </span>
          </div>
        ) : (
          <img
            src={src}
            alt={alt}
            className="max-w-full max-h-[80vh] rounded-2xl shadow-2xl ring-2 ring-primary/30 object-contain"
            style={{ imageRendering: 'auto' }}
            onError={() => setImgFailed(true)}
          />
        )}

        {/* 角色名标签 */}
        {alt && (
          <div className="absolute bottom-0 left-0 right-0 px-4 py-2.5
                          bg-gradient-to-t from-black/60 to-transparent rounded-b-2xl">
            <span className="text-white/90 text-sm font-medium">{alt}</span>
          </div>
        )}
      </div>
    </div>,
    document.body,
  )
}
