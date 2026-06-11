/**
 * FreeInput - 自由输入框
 * 织梦绮谭 - 毛玻璃风格输入区域
 */

import React, { useState, useRef, useEffect } from 'react'
import { Send } from 'lucide-react'

interface Props {
  disabled: boolean
  onSubmit: (text: string) => void
  placeholder?: string
}

export const FreeInput: React.FC<Props> = ({
  disabled,
  onSubmit,
  placeholder = '输入你想说的话...',
}) => {
  const [text, setText] = useState('')
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = () => {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSubmit(trimmed)
    setText('')
    if (inputRef.current) inputRef.current.style.height = 'auto'
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleInput = () => {
    const el = inputRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 120) + 'px'
    }
  }

  useEffect(() => { handleInput() }, [text])

  return (
    <div className="flex items-end gap-2.5 mt-3">
      <div className="flex-1 relative">
        <textarea
          ref={inputRef}
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={placeholder}
          rows={1}
          className="w-full text-text-bright
                     bg-surface-light/30 backdrop-blur-sm
                     border border-white/[0.06] focus:border-primary/30
                     rounded-2xl px-4 py-3 pr-12
                     resize-none outline-none transition-all duration-300
                     placeholder:text-text-dim/30
                     disabled:opacity-30 text-[14px] leading-relaxed"
        />
      </div>

      <button
        onClick={handleSubmit}
        disabled={disabled || !text.trim()}
        className="shrink-0 w-10 h-10 flex items-center justify-center rounded-xl
                   transition-all duration-300
                   disabled:bg-surface-light/20 disabled:text-text-dim/30
                   bg-gradient-to-br from-primary to-primary-dark
                   text-white hover:shadow-[0_4px_16px_rgba(168,130,255,0.3)]
                   hover:-translate-y-0.5 active:translate-y-0"
      >
        <Send size={16} />
      </button>
    </div>
  )
}
