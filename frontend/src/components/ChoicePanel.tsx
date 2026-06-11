/**
 * ChoicePanel - 选项面板
 * 织梦绮谭 - 精致选项卡片，逐个淡入动画
 */

import React from 'react'
import type { DialogueChoice } from '@/types'

interface Props {
  choices: DialogueChoice[]
  disabled: boolean
  onSelect: (choice: DialogueChoice) => void
}

export const ChoicePanel: React.FC<Props> = ({ choices, disabled, onSelect }) => {
  if (choices.length === 0) return null

  return (
    <div className="space-y-2">
      {choices.map((choice, index) => (
        <button
          key={choice.id}
          className="choice-appear choice-btn w-full text-left px-5 py-3.5
                     glass-panel hover:border-primary/25
                     disabled:opacity-30 disabled:cursor-not-allowed
                     group cursor-pointer"
          style={{ animationDelay: `${index * 0.08}s` }}
          disabled={disabled}
          onClick={() => onSelect(choice)}
        >
          <div className="flex items-start gap-3 relative z-10">
            {/* 选项标记 */}
            <div className="w-6 h-6 rounded-lg shrink-0 flex items-center justify-center mt-0.5
                            bg-primary/10 group-hover:bg-primary/20 transition-colors duration-300">
              <span className="text-primary-light text-xs font-bold">
                {String.fromCharCode(65 + index)}
              </span>
            </div>

            <div className="flex-1 min-w-0">
              <p className="text-text-bright text-[14px] leading-relaxed
                            group-hover:text-primary-light transition-colors duration-300">
                {choice.text}
              </p>
              {choice.hint && (
                <p className="text-text-dim/50 text-xs mt-1.5 leading-relaxed">
                  {choice.hint}
                </p>
              )}
            </div>

            {/* 右侧箭头 */}
            <div className="opacity-0 group-hover:opacity-100 -translate-x-1
                            group-hover:translate-x-0 transition-all duration-300 shrink-0 mt-1">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" className="text-primary-light/60">
                <path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
          </div>
        </button>
      ))}
    </div>
  )
}
