/**
 * SaveLoad - 存档/读档/删档页面
 * 织梦绮谭 - 12个存档位 + 自动存档
 */

import React, { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Save, Trash2, FolderOpen, Plus, AlertTriangle } from 'lucide-react'
import { saveApi } from '@/services/api'
import { useGameStore } from '@/stores/gameStore'
import { useUIStore } from '@/stores/uiStore'
import type { SaveSlot } from '@/types'

export const SaveLoad: React.FC = () => {
  const navigate = useNavigate()
  const sessionId = useGameStore((s) => s.sessionId)
  const chapter = useGameStore((s) => s.chapter)
  const setLoading = useUIStore((s) => s.setLoading)

  const [saves, setSaves] = useState<SaveSlot[]>([])
  const [loading, setLoadingState] = useState(true)
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)

  // 加载存档列表
  const loadSaves = useCallback(() => {
    setLoadingState(true)
    saveApi.list()
      .then(setSaves)
      .catch((err) => console.error('加载存档失败:', err))
      .finally(() => setLoadingState(false))
  }, [])

  useEffect(() => { loadSaves() }, [loadSaves])

  // 找到指定存档位的数据
  const getSlotSave = (slotNum: number) => saves.find(s => s.slot_number === slotNum)

  // 创建/覆盖存档
  const handleSave = async (slotNum: number) => {
    if (!sessionId) {
      alert('当前没有进行中的游戏')
      return
    }
    setLoading(true, '保存中...')
    try {
      await saveApi.create(slotNum, sessionId, `第${chapter}章 存档`)
      loadSaves()
    } catch (err) {
      console.error('存档失败:', err)
      alert('存档失败: ' + (err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  // 加载存档
  const handleLoad = async (save: SaveSlot) => {
    setLoading(true, '读取存档中...')
    try {
      const res = await saveApi.load(save.id)
      const newSessionId = res.data.session_id
      useGameStore.getState().setSession(newSessionId)
      navigate('/game')
    } catch (err) {
      console.error('读档失败:', err)
      alert('读档失败: ' + (err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  // 删除存档
  const handleDelete = async (saveId: string) => {
    try {
      await saveApi.delete(saveId)
      setConfirmDelete(null)
      loadSaves()
    } catch (err) {
      console.error('删除存档失败:', err)
      alert('删除失败: ' + (err as Error).message)
    }
  }

  // 格式化日期
  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr)
      return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
    } catch {
      return dateStr
    }
  }

  const TOTAL_SLOTS = 12

  return (
    <div className="min-h-screen bg-surface-dark flex flex-col">
      {/* 头部 */}
      <header className="glass-panel-strong mx-3 mt-3 p-4 flex items-center gap-3">
        <button
          onClick={() => navigate(sessionId ? '/game' : '/')}
          className="w-8 h-8 rounded-lg flex items-center justify-center
                     bg-surface-light/50 hover:bg-surface-light transition-colors"
        >
          <ArrowLeft size={16} className="text-text-dim" />
        </button>
        <div>
          <h1 className="text-text-bright font-bold text-base">存档管理</h1>
          <p className="text-text-dim/50 text-[11px] mt-0.5">织梦绮谭 · 存档与读档</p>
        </div>
      </header>

      {/* 存档网格 */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="flex items-center justify-center h-64 text-text-dim">
            <div className="w-8 h-8 rounded-full border-2 border-primary/20 border-t-primary animate-spin" />
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-w-4xl mx-auto">
            {Array.from({ length: TOTAL_SLOTS }, (_, i) => i + 1).map(slotNum => {
              const save = getSlotSave(slotNum)
              const isConfirmingDelete = confirmDelete === save?.id

              return (
                <div key={slotNum} className="glass-panel p-4 min-h-[120px] flex flex-col">
                  {/* 存档位标题 */}
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-text-dim/40 text-[10px] tracking-wider">
                      存档 {slotNum.toString().padStart(2, '0')}
                    </span>
                    {save && (
                      <span className="text-text-dim/30 text-[10px]">
                        {formatDate(save.created_at)}
                      </span>
                    )}
                  </div>

                  {save ? (
                    <>
                      {/* 已有存档 */}
                      <p className="text-text-bright text-sm font-medium truncate mb-1">
                        {save.title || '未命名存档'}
                      </p>
                      {save.description && (
                        <p className="text-text-dim/50 text-xs truncate mb-3">
                          {save.description}
                        </p>
                      )}

                      <div className="flex-1" />

                      {/* 操作按钮 */}
                      {isConfirmingDelete ? (
                        <div className="flex items-center gap-2">
                          <span className="text-accent text-xs flex-1">确定删除？</span>
                          <button onClick={() => handleDelete(save.id)}
                            className="text-[11px] px-3 py-1 rounded-lg bg-accent/15 text-accent hover:bg-accent/25 transition-colors">
                            确定
                          </button>
                          <button onClick={() => setConfirmDelete(null)}
                            className="text-[11px] px-3 py-1 rounded-lg bg-surface-light/50 text-text-dim hover:bg-surface-light transition-colors">
                            取消
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <button onClick={() => handleLoad(save)}
                            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg
                                       btn-gradient text-white text-xs font-medium">
                            <FolderOpen size={12} /> 读取
                          </button>
                          {sessionId && (
                            <button onClick={() => handleSave(slotNum)}
                              className="flex items-center justify-center gap-1 px-3 py-2 rounded-lg
                                         bg-surface-light/50 text-text-dim text-xs hover:bg-surface-light transition-colors">
                              <Save size={12} /> 覆盖
                            </button>
                          )}
                          <button onClick={() => setConfirmDelete(save.id)}
                            className="flex items-center justify-center px-2 py-2 rounded-lg
                                       hover:bg-accent/10 text-text-dim/40 hover:text-accent transition-colors">
                            <Trash2 size={12} />
                          </button>
                        </div>
                      )}
                    </>
                  ) : (
                    <>
                      {/* 空存档位 */}
                      <div className="flex-1 flex items-center justify-center">
                        <span className="text-text-dim/20 text-xs">空</span>
                      </div>
                      {sessionId && (
                        <button onClick={() => handleSave(slotNum)}
                          className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg
                                     bg-primary/10 text-primary-light/70 text-xs
                                     hover:bg-primary/20 hover:text-primary-light transition-colors mt-2">
                          <Plus size={12} /> 保存到这里
                        </button>
                      )}
                    </>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* 底部提示 */}
      {!sessionId && (
        <div className="p-3 text-center">
          <p className="text-text-dim/30 text-[11px] flex items-center justify-center gap-1.5">
            <AlertTriangle size={11} />
            当前没有进行中的游戏，仅可查看和读取存档
          </p>
        </div>
      )}
    </div>
  )
}
