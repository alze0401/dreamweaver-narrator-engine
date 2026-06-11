/**
 * AffectionBar - 好感度指示器
 * 显示角色的好感度等级和进度条
 */

import React from 'react'
import { useUIStore } from '@/stores/uiStore'

interface Props {
  rank: string
  score: number          // 0-100
  maxScore?: number
  showNumbers?: boolean  // 是否显示具体数值
}

/** 好感度等级对应的颜色 */
const RANK_COLORS: Record<string, string> = {
  '敌对': 'bg-red-500',
  '冷漠': 'bg-red-400/60',
  '陌生': 'bg-gray-400',
  '认识': 'bg-blue-400',
  '友好': 'bg-emerald-400',
  '亲密': 'bg-pink-400',
  '挚爱': 'bg-rose-400',
  // 通用 fallback
}

/** 根据分数获取进度百分比 */
function scoreToPercent(score: number, max = 100): number {
  return Math.max(0, Math.min(100, (score / max) * 100))
}

export const AffectionBar: React.FC<Props> = ({
  rank,
  score,
  maxScore = 100,
}) => {
  const showNumbers = useUIStore((s) => s.showAffectionNumbers)
  const color = RANK_COLORS[rank] || 'bg-primary'
  const percent = scoreToPercent(score, maxScore)

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-1">
        <span className={`text-xs font-medium ${color.replace('bg-', 'text-')}`}>
          {rank}
        </span>
        {showNumbers && (
          <span className="text-text-dim text-xs tabular-nums">
            {score.toFixed(0)}/{maxScore}
          </span>
        )}
      </div>

      {/* 进度条 */}
      <div className="w-full h-1.5 bg-surface-dark rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-700 ease-out`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  )
}
