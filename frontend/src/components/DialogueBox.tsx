/**
 * DialogueBox - 对话框组件
 * 织梦绮谭 - 精致二次元风格对话展示
 */

import React, { useEffect, useRef, useState } from 'react'
import { useTypewriter } from '@/hooks/useTypewriter'
import { getCharacterPortrait } from '@/utils/assets'
import type { DisplayMessage } from '@/stores/gameStore'

interface Props {
  message: DisplayMessage
  onTypeComplete?: () => void
  isLatest: boolean
}

export const DialogueBox: React.FC<Props> = ({ message, onTypeComplete, isLatest }) => {
  const { displayedText, isComplete, skip } = useTypewriter(
    isLatest ? message.text : message.text,
    onTypeComplete,
  )
  const boxRef = useRef<HTMLDivElement>(null)

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
    // 立绘检测
    const [portrait, setPortrait] = useState<string | null>(null)
    useEffect(() => {
      if (!message.speaker) return
      const url = getCharacterPortrait(message.speaker)
      const img = new Image()
      img.onload = () => setPortrait(url)
      img.onerror = () => setPortrait(null)
      img.src = url
    }, [message.speaker])

    return (
      <div ref={boxRef} className="mb-5 animate-fade-in cursor-pointer" onClick={skip}>
        {/* 角色名 + 立绘小头像 + 情感 */}
        <div className="flex items-center gap-2.5 mb-2">
          {/* 小头像 */}
          {portrait && (
            <img src={portrait} alt={message.speaker}
                 className="w-7 h-7 rounded-lg object-cover shrink-0 ring-1 ring-accent/20" />
          )}
          {/* 角色名 */}
          <span className="text-accent-light font-bold text-sm tracking-wide">{message.speaker}</span>
          {/* 情感标签 */}
          {message.emotion && (
            <span className="text-[10px] px-2 py-0.5 rounded-full
                             bg-accent/8 text-accent-light/60 border border-accent/10">
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
