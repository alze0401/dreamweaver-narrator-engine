/**
 * CharacterCard - 角色信息卡片
 * 织梦绮谭 - 含五维雷达图、头像和详细信息
 */

import React, { useState, useEffect } from 'react'
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer } from 'recharts'
import type { CharacterSummary } from '@/types'
import { AffectionBar } from './AffectionBar'
import { getCharacterPortrait } from '@/utils/assets'

/** 维度中文名称映射 */
export const DIMENSION_LABELS: Record<string, string> = {
  intimacy: '亲密',
  trust: '信任',
  respect: '尊重',
  curiosity: '好奇',
  fear: '畏惧',
}

/** 好感度等级对应的颜色（十六进制） */
const RANK_COLORS: Record<string, string> = {
  '敌对': '#ef4444',
  '冷漠': '#f87171',
  '陌生': '#9ca3af',
  '认识': '#60a5fa',
  '友好': '#34d399',
  '亲密': '#f472b6',
  '挚爱': '#fb7185',
}

/** 根据等级获取头像边框渐变 */
const RANK_BORDER: Record<string, string> = {
  '敌对': 'ring-red-500/40',
  '冷漠': 'ring-red-400/30',
  '陌生': 'ring-gray-400/30',
  '认识': 'ring-blue-400/30',
  '友好': 'ring-emerald-400/30',
  '亲密': 'ring-pink-400/40',
  '挚爱': 'ring-rose-400/50',
}

interface Props {
  character: CharacterSummary
}

export const CharacterCard: React.FC<Props> = ({ character }) => {
  const color = RANK_COLORS[character.current_rank] || '#a882ff'
  const ringClass = RANK_BORDER[character.current_rank] || 'ring-primary/30'
  const avatarLetter = character.character_name.charAt(0)

  // 角色立绘检测（不存在时降级为首字母头像）
  const [portraitUrl, setPortraitUrl] = useState<string | null>(null)
  useEffect(() => {
    const url = getCharacterPortrait(character.character_name, character.character_id)
    const img = new Image()
    img.onload = () => setPortraitUrl(url)
    img.onerror = () => setPortraitUrl(null)
    img.src = url
  }, [character.character_name, character.character_id])

  // 构建雷达图数据
  const radarData = [
    { dimension: '亲密', value: character.intimacy, fullMark: 100 },
    { dimension: '信任', value: character.trust, fullMark: 100 },
    { dimension: '尊重', value: character.respect, fullMark: 100 },
    { dimension: '好奇', value: character.curiosity, fullMark: 100 },
    { dimension: '畏惧', value: character.fear, fullMark: 100 },
  ]

  return (
    <div className="glass-panel p-3.5 transition-all duration-300">
      {/* 上半部分：头像 + 基本信息 */}
      <div className="flex items-start gap-3 mb-3">
        {/* 头像（立绘 or 首字母） */}
        <div className={`w-12 h-12 rounded-xl shrink-0 overflow-hidden
                        bg-gradient-to-br from-surface-light to-surface-dark
                        ring-2 ${ringClass} transition-all duration-500
                        flex items-center justify-center`}>
          {portraitUrl ? (
            <img src={portraitUrl} alt={character.character_name}
                 className="w-full h-full object-cover" />
          ) : (
            <span className="text-text-bright font-bold text-base">{avatarLetter}</span>
          )}
        </div>

        <div className="flex-1 min-w-0">
          <h4 className="text-text-bright text-sm font-medium truncate">{character.character_name}</h4>
          <p className="text-text-dim/50 text-[11px] mt-0.5 truncate">{character.relationship_label}</p>
          {/* 好感度等级 + 综合分数 */}
          <div className="flex items-center gap-2 mt-1.5">
            <span className="text-[10px] px-2 py-0.5 rounded-full font-medium"
                  style={{ color, background: `${color}15`, border: `1px solid ${color}30` }}>
              {character.current_rank}
            </span>
            <span className="text-text-dim/30 text-[10px]">
              {character.overall_score.toFixed(0)}/100
            </span>
          </div>
        </div>
      </div>

      {/* 好感度进度条 */}
      <AffectionBar rank={character.current_rank} score={character.overall_score} />

      {/* 五维雷达图 */}
      <div className="mt-2 h-[130px]">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="68%">
            <PolarGrid stroke="rgba(255,255,255,0.05)" />
            <PolarAngleAxis
              dataKey="dimension"
              tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }}
            />
            <Radar
              name="好感度"
              dataKey="value"
              stroke={color}
              fill={color}
              fillOpacity={0.15}
              strokeWidth={1.5}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
