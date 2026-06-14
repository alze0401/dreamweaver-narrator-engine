/**
 * AffectionToast - 好感度变化飘出提示
 * 织梦绮谭 - 从右侧飘入、停留、再飘出的轻量通知（非弹窗）
 */

import React, { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { Heart, ArrowDown } from 'lucide-react'
import type { AffectionChange } from '@/types'

/** 维度中文名称映射 */
const DIMENSION_LABELS: Record<string, string> = {
  intimacy: '亲密',
  trust: '信任',
  respect: '尊重',
  curiosity: '好奇',
  fear: '畏惧',
}

interface ToastItem {
  id: number
  character: string
  dimension: string
  delta: number
  positive: boolean
}

interface Props {
  changes: AffectionChange[]
}

export const AffectionToast: React.FC<Props> = ({ changes }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const processedCount = React.useRef(0)

  // 当新的变化出现时，生成 toast 并设定自动消失
  useEffect(() => {
    if (changes.length <= processedCount.current) return

    const newChanges = changes.slice(processedCount.current)
    processedCount.current = changes.length

    const newToasts: ToastItem[] = newChanges.map((c, i) => ({
      id: Date.now() + i,
      character: c.character,
      dimension: DIMENSION_LABELS[c.dimension] || c.dimension,
      delta: c.delta,
      positive: c.delta > 0,
    }))

    setToasts((prev) => [...prev, ...newToasts])

    // 3.5 秒后自动移除（CSS 动画总时长 3s + 0.5s 缓冲）
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => !newToasts.find((n) => n.id === t.id)))
    }, 3500)
  }, [changes])

  // 会话切换时重置
  useEffect(() => {
    processedCount.current = 0
    setToasts([])
  }, [])

  if (toasts.length === 0) return null

  return createPortal(
    <div className="fixed top-20 right-5 z-[60] flex flex-col gap-2.5 pointer-events-none">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className="glass-panel px-4 py-2.5 flex items-center gap-2.5 min-w-[170px]"
          style={{
            animation: 'toastFloat 3s cubic-bezier(0.16, 1, 0.3, 1) forwards',
            borderRadius: '14px',
          }}
        >
          {toast.positive ? (
            <Heart size={14} className="text-pink-400 shrink-0 fill-pink-400/30" />
          ) : (
            <ArrowDown size={14} className="text-blue-400 shrink-0" />
          )}
          <div className="flex flex-col">
            <span className="text-text-bright text-xs font-medium leading-tight">
              {toast.character}
            </span>
            <span
              className={`text-[11px] leading-tight mt-0.5 ${
                toast.positive ? 'text-pink-400' : 'text-blue-400'
              }`}
            >
              {toast.dimension} {toast.positive ? '+' : ''}
              {toast.delta}
            </span>
          </div>
        </div>
      ))}
    </div>,
    document.body,
  )
}
