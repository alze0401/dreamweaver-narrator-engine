/**
 * SidePanel - 侧边栏
 * 织梦绮谭 - 毛玻璃侧边面板，展示角色与场景信息
 */

import React from 'react'
import { X, MapPin, Clock, Heart, Settings } from 'lucide-react'
import { useGameStore } from '@/stores/gameStore'
import { useUIStore } from '@/stores/uiStore'
import { CharacterCard, DIMENSION_LABELS } from './CharacterCard'

export const SidePanel: React.FC = () => {
  const sidePanelOpen = useUIStore((s) => s.sidePanelOpen)
  const toggleSidePanel = useUIStore((s) => s.toggleSidePanel)
  const showNumbers = useUIStore((s) => s.showAffectionNumbers)
  const toggleNumbers = useUIStore((s) => s.toggleAffectionNumbers)

  const characters = useGameStore((s) => s.characters)
  const sceneState = useGameStore((s) => s.sceneState)
  const chapter = useGameStore((s) => s.chapter)
  const recentChanges = useGameStore((s) => s.recentAffectionChanges)
  const clearChanges = useGameStore((s) => s.clearAffectionChanges)

  if (!sidePanelOpen) return null

  return (
    <>
      {/* 遮罩 */}
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden" onClick={toggleSidePanel} />

      {/* 侧边栏 */}
      <div className="fixed right-0 top-0 bottom-0 w-80 z-50 flex flex-col overflow-hidden animate-fade-in
                      bg-surface-dark/90 backdrop-blur-xl border-l border-white/[0.04]">
        {/* 头部 */}
        <div className="flex items-center justify-between p-4 border-b border-white/[0.04]">
          <h2 className="text-text-bright font-bold text-base tracking-wide">状态面板</h2>
          <button
            onClick={toggleSidePanel}
            className="w-8 h-8 rounded-lg flex items-center justify-center
                       hover:bg-surface-light/50 transition-colors"
          >
            <X size={16} className="text-text-dim" />
          </button>
        </div>

        {/* 内容 */}
        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          {/* 场景信息 */}
          <section className="glass-panel p-4">
            <h3 className="text-text-dim/50 text-[10px] font-medium uppercase tracking-[0.2em] mb-3">
              当前场景
            </h3>
            <div className="space-y-2.5 text-sm">
              <div className="flex items-center gap-2.5 text-text">
                <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                  <MapPin size={13} className="text-primary-light" />
                </div>
                <span className="text-xs">{sceneState.location || '未知地点'}</span>
              </div>
              {sceneState.time && (
                <div className="flex items-center gap-2.5 text-text">
                  <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                    <Clock size={13} className="text-primary-light" />
                  </div>
                  <span className="text-xs">{sceneState.time}</span>
                </div>
              )}
              {sceneState.mood && (
                <p className="text-text-dim/40 text-xs italic pl-9">{sceneState.mood}</p>
              )}
              <div className="divider-gradient mt-2" />
              <p className="text-text-dim/30 text-[10px] pl-1">第 {chapter} 章</p>
            </div>
          </section>

          {/* 角色列表 */}
          <section>
            <h3 className="text-text-dim/50 text-[10px] font-medium uppercase tracking-[0.2em] mb-3">
              角色
            </h3>
            {characters.length === 0 ? (
              <p className="text-text-dim/30 text-sm italic">尚无角色</p>
            ) : (
              <div className="space-y-2">
                {characters.map(char => (
                  <CharacterCard key={char.character_id} character={char} />
                ))}
              </div>
            )}
          </section>

          {/* 好感度变化 */}
          {recentChanges.length > 0 && (
            <section>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-text-dim/50 text-[10px] font-medium uppercase tracking-[0.2em]">
                  好感度变化
                </h3>
                <button
                  onClick={clearChanges}
                  className="text-text-dim/40 text-[10px] hover:text-text-dim transition-colors"
                >
                  清除
                </button>
              </div>
              <div className="space-y-1.5">
                {recentChanges.map((change, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs animate-fade-in
                                          glass-panel px-3 py-2">
                    <Heart size={11} className={change.delta > 0 ? 'text-pink-400' : 'text-blue-400'} />
                    <span className="text-text flex-1">{change.character}</span>
                    <span className={`font-medium ${change.delta > 0 ? 'text-pink-400' : 'text-blue-400'}`}>
                      {DIMENSION_LABELS[change.dimension] || change.dimension} {change.delta > 0 ? '+' : ''}{change.delta}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        {/* 底部设置 */}
        <div className="p-4 border-t border-white/[0.04]">
          <button
            onClick={toggleNumbers}
            className="flex items-center gap-2 text-text-dim/50 text-xs hover:text-text-dim transition-colors"
          >
            <Settings size={13} />
            <span>{showNumbers ? '隐藏' : '显示'}好感度数值</span>
          </button>
        </div>
      </div>
    </>
  )
}
