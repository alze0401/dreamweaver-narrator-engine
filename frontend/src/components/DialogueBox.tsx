/**
 * DialogueBox - 对话框组件
 * 织梦绮谭 - 精致二次元风格对话展示
 */

import React, { useEffect, useRef, useState } from 'react'
import { useTypewriter } from '@/hooks/useTypewriter'
import { getCharacterPortrait } from '@/utils/assets'
import { AvatarLightbox } from '@/components/AvatarLightbox'
import type { DisplayMessage } from '@/stores/gameStore'

/** 根据角色名生成稳定的渐变背景色 */
const nameToGradient = (name: string): string => {
  const hash = name.split('').reduce((a, c) => a + c.charCodeAt(0), 0)
  const gradients = [
    'from-purple-500/40 to-pink-500/30',
    'from-blue-500/40 to-cyan-500/30',
    'from-rose-500/40 to-orange-500/30',
    'from-emerald-500/40 to-teal-500/30',
    'from-indigo-500/40 to-violet-500/30',
    'from-amber-500/40 to-yellow-500/30',
  ]
  return gradients[hash % gradients.length]
}

interface Props {
  message: DisplayMessage
  onTypeComplete?: () => void
  isLatest: boolean
  /** 角色头像 URL（从外部传入，优先使用） */
  avatarUrl?: string | null
}

export const DialogueBox: React.FC<Props> = ({ message, onTypeComplete, isLatest, avatarUrl }) => {
  const { displayedText, isComplete, skip } = useTypewriter(
    message.text,
    onTypeComplete,
    isLatest, // 只有最新一条消息才播放打字机动画
  )
  const boxRef = useRef<HTMLDivElement>(null)

  // 立绘检测：hooks 必须在所有条件分支之前调用（React Rules of Hooks）
  const [portrait, setPortrait] = useState<string | null>(null)
  const [lightboxOpen, setLightboxOpen] = useState(false)
  useEffect(() => {
    if (avatarUrl) {
      setPortrait(avatarUrl)
      return
    }
    if (!message.speaker) return
    const url = getCharacterPortrait(message.speaker)
    const img = new Image()
    img.onload = () => setPortrait(url)
    img.onerror = () => setPortrait(null)
    img.src = url
  }, [message.speaker, avatarUrl])

  useEffect(() => {
    boxRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [displayedText])

  // ===== 叙事文本 =====
  if (message.type === 'narration') {
    return (
      <div ref={boxRef} className="mb-5 animate-fade-in cursor-pointer" onClick={skip}>
        <div className="relative pl-4">
          {/* 左侧装饰线 */}
          <div className="absolute left-0 top-1 bottom-1 w-[2px] rounded-full
                          bg-gradient-to-b from-primary/40 via-accent/20 to-transparent" />
          <p className="text-text/90 leading-[1.85] font-serif text-[15px] whitespace-pre-wrap">
            {displayedText}
            {!isComplete && <span className="typewriter-cursor" />}
          </p>
        </div>
      </div>
    )
  }

  // ===== 角色台词 =====
  if (message.type === 'dialogue') {
    return (
      <div ref={boxRef} className="mb-5 animate-fade-in cursor-pointer" onClick={skip}>
        {/* 角色名 + 头像小头像 + 情感 */}
        <div className="flex items-center gap-2.5 mb-2">
          {/* 小头像（始终显示：有头像用头像，无则渐变首字母）圆形 QQ 风格 */}
          {portrait ? (
            <div className="w-8 h-8 rounded-full overflow-hidden shrink-0 ring-1 ring-accent/20 cursor-zoom-in"
                 onClick={(e) => { e.stopPropagation(); setLightboxOpen(true) }}>
              <img
                src={portrait}
                alt={message.speaker}
                className="w-full h-full object-contain"
                onError={() => setPortrait(null)}
              />
            </div>
          ) : message.speaker ? (
            <div className={`w-8 h-8 rounded-full shrink-0 ring-1 ring-accent/20 overflow-hidden
                            bg-gradient-to-br ${nameToGradient(message.speaker)}
                            flex items-center justify-center`}>
              <span className="text-text-bright text-[11px] font-bold drop-shadow-sm">
                {message.speaker.charAt(0)}
              </span>
            </div>
          ) : null}
          {/* 角色名 */}
          <span className="text-accent-light font-bold text-sm tracking-wide">{message.speaker}</span>
          {/* 情感标签 */}
          {message.emotion && (
            <span className="text-[10px] px-2 py-0.5 rounded-full
                             bg-accent/12 text-accent-light/80 border border-accent/15">
              {message.emotion}
            </span>
          )}
        </div>

        {/* 动作描写 */}
        {message.action && (
          <p className="text-text-dim/60 text-sm italic mb-2 whitespace-pre-wrap pl-1">
            {message.action}
          </p>
        )}

        {/* 台词气泡 */}
        <div className="dialogue-glass px-5 py-3.5">
          <p className="text-text-bright leading-[1.85] text-[15px] whitespace-pre-wrap">
            {displayedText}
            {!isComplete && <span className="typewriter-cursor" />}
          </p>
        </div>

        {/* 头像放大浮层 */}
        {lightboxOpen && portrait && (
          <AvatarLightbox
            src={portrait}
            alt={message.speaker || '角色'}
            onClose={() => setLightboxOpen(false)}
          />
        )}
      </div>
    )
  }

  // ===== 玩家消息 =====
  if (message.type === 'player') {
    return (
      <div ref={boxRef} className="mb-5 animate-fade-in flex justify-end">
        <div className="max-w-[80%] px-5 py-3 rounded-2xl rounded-tr-md
                        bg-gradient-to-br from-primary/15 to-primary-dark/10
                        border border-primary/15">
          <p className="text-primary-light text-[15px] leading-relaxed">
            {message.text}
          </p>
        </div>
      </div>
    )
  }

  // ===== 系统消息 =====
  return (
    <div ref={boxRef} className="mb-5 text-center animate-fade-in">
      <span className="text-text-dim/40 text-[11px] px-4 py-1.5 rounded-full
                       bg-surface-light/30 border border-white/[0.03]">
        {message.text}
      </span>
    </div>
  )
}
