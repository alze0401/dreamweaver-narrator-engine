/**
 * Game - 游戏主界面
 * 织梦绮谭 - 精致二次元 Galgame 核心体验
 * 含场景背景图 + BGM（资源不存在时静默降级）
 */

import React, { useEffect, useRef, useCallback, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Menu, MapPin, Clock, Save, BookOpen, Volume2, VolumeX, Settings } from 'lucide-react'
import { useGameStore, type DisplayMessage } from '@/stores/gameStore'
import { useUIStore } from '@/stores/uiStore'
import { useBgmStore } from '@/stores/bgmStore'
import { gameApi, characterApi } from '@/services/api'
import { DialogueBox } from '@/components/DialogueBox'
import { ChoicePanel } from '@/components/ChoicePanel'
import { FreeInput } from '@/components/FreeInput'
import { SidePanel } from '@/components/SidePanel'
import { AffectionToast } from '@/components/AffectionToast'
import { getSceneBackground, getBgmUrl } from '@/utils/assets'
import type { DialogueChoice } from '@/types'

export const Game: React.FC = () => {
  const navigate = useNavigate()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const turnCountRef = useRef(0)  // 对话轮次计数（用于自动存档）

  // Store
  const sessionId = useGameStore((s) => s.sessionId)
  const messages = useGameStore((s) => s.messages)
  const currentChoices = useGameStore((s) => s.currentChoices)
  const isGenerating = useGameStore((s) => s.isGenerating)
  const sceneState = useGameStore((s) => s.sceneState)
  const chapter = useGameStore((s) => s.chapter)
  const totalChapters = useGameStore((s) => s.totalChapters)
  const currentTurn = useGameStore((s) => s.currentTurn)
  const characters = useGameStore((s) => s.characters)
  const addMessages = useGameStore((s) => s.addMessages)
  const setChoices = useGameStore((s) => s.setChoices)
  const setGenerating = useGameStore((s) => s.setGenerating)
  const setScene = useGameStore((s) => s.setScene)
  const setCharacters = useGameStore((s) => s.setCharacters)
  const addAffectionChanges = useGameStore((s) => s.addAffectionChanges)
  const setProgress = useGameStore((s) => s.setProgress)
  const toggleSidePanel = useUIStore((s) => s.toggleSidePanel)

  // ---- 好感度飘出提示 ----
  const recentAffectionChanges = useGameStore((s) => s.recentAffectionChanges)

  // ---- 角色头像映射（speaker name → avatar_url） ----
  const avatarMap = useMemo(() => {
    const map: Record<string, string | null> = {}
    characters.forEach((c) => {
      if (c.avatar_url) map[c.character_name] = c.avatar_url
    })
    return map
  }, [characters])

  // ---- 场景背景图（加载失败时隐藏） ----
  const [bgUrl, setBgUrl] = useState<string | null>(null)

  useEffect(() => {
    const url = getSceneBackground(sceneState.location)
    if (url) {
      const img = new Image()
      img.onload = () => setBgUrl(url)
      img.onerror = () => setBgUrl(null)
      img.src = url
    } else {
      setBgUrl(null)
    }
  }, [sceneState.location])

  // ---- BGM（全局播放，此处仅控制 mood 切换） ----
  const bgmMuted = useBgmStore((s) => s.muted)
  const bgmEnabled = useBgmStore((s) => s.enabled)
  const toggleBgmMute = useBgmStore((s) => s.toggleMuted)
  const setGlobalBgmUrl = useBgmStore((s) => s.setBgmUrl)
  const prevMoodRef = useRef<string | undefined>()

  // 根据 mood 切换全局 BGM 曲目
  useEffect(() => {
    const mood = sceneState.mood
    if (mood === prevMoodRef.current) return
    prevMoodRef.current = mood

    const moodUrl = getBgmUrl(mood)
    if (moodUrl) {
      // 有匹配的 mood BGM → 切换
      setGlobalBgmUrl(moodUrl)
    }
    // 如果没有匹配的 mood BGM → 保持当前曲目不变
  }, [sceneState.mood])

  // 切换静音（来自 bgmStore）

  // ---- 基本逻辑 ----
  useEffect(() => {
    if (!sessionId) navigate('/')
  }, [sessionId, navigate])

  // ---- 主题同步（从设置页返回时自动应用最新主题） ----
  useEffect(() => {
    try {
      const t = localStorage.getItem('dw_theme')
      if (t) document.documentElement.setAttribute('data-theme', t)
    } catch {}
    const handleThemeChange = (e: Event) => {
      const theme = (e as CustomEvent).detail?.theme
      if (theme) document.documentElement.setAttribute('data-theme', theme)
    }
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        try {
          const t = localStorage.getItem('dw_theme')
          if (t) document.documentElement.setAttribute('data-theme', t)
        } catch {}
      }
    }
    window.addEventListener('dw:themeChanged', handleThemeChange)
    document.addEventListener('visibilitychange', handleVisibility)
    return () => {
      window.removeEventListener('dw:themeChanged', handleThemeChange)
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [])

  useEffect(() => {
    if (!sessionId) return
    characterApi.list(sessionId)
      .then(chars => setCharacters(chars))
      .catch(console.error)
  }, [sessionId]) // eslint-disable-line

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const processResponse = useCallback((res: import('@/types').DialogueAdvanceResponse) => {
    const newMsgs: DisplayMessage[] = []
    if (res.narration) newMsgs.push({ id: '', type: 'narration', text: res.narration })
    for (const d of res.dialogues) {
      newMsgs.push({ id: '', type: 'dialogue', speaker: d.speaker, text: d.text, emotion: d.emotion, action: d.action })
    }
    addMessages(newMsgs)
    setChoices(res.choices)
    setScene(res.scene_state.location || '', res.scene_state)
    if (res.affection_changes?.length) addAffectionChanges(res.affection_changes)
    // 实时更新角色好感度数据（驱动雷达图刷新）
    if (res.updated_characters?.length) setCharacters(res.updated_characters)
    if (res.progress) setProgress(res.progress)
    setGenerating(false)

    // ---- 自动存档逻辑（暂时关闭）----
    turnCountRef.current += 1
    // if (sessionId && turnCountRef.current % AUTO_SAVE_INTERVAL === 0
    //     && useAuthStore.getState().isAuthenticated) {
    //   saveApi.autoSave(sessionId).catch((err) => {
    //     console.warn('自动存档失败（不影响游戏）:', err)
    //   })
    // }
  }, [addMessages, setChoices, setScene, addAffectionChanges, setGenerating, setProgress, sessionId])

  const sendInput = useCallback(async (inputType: 'choice' | 'free', content: string) => {
    if (!sessionId || isGenerating) return
    addMessages([{ id: '', type: 'player', text: content }])
    setChoices([])
    setGenerating(true)
    try {
      const res = await gameApi.advance(sessionId, inputType, content)
      processResponse(res)
    } catch (err) {
      console.error('剧情推进失败:', err)
      addMessages([{ id: '', type: 'system', text: `系统错误: ${(err as Error).message}` }])
      setGenerating(false)
    }
  }, [sessionId, isGenerating, addMessages, setChoices, setGenerating, processResponse])

  const handleChoiceSelect = useCallback((choice: DialogueChoice) => {
    if (!sessionId || isGenerating) return
    addMessages([{ id: '', type: 'player', text: choice.text }])
    setChoices([])
    setGenerating(true)
    // 发送 choice.text（而非 choice.id），确保 LLM 能看到玩家实际选择的内容
    gameApi.advance(sessionId, 'choice', choice.text)
      .then(processResponse)
      .catch((err) => {
        console.error('剧情推进失败:', err)
        addMessages([{ id: '', type: 'system', text: `系统错误: ${(err as Error).message}` }])
        setGenerating(false)
      })
  }, [sessionId, isGenerating, addMessages, setChoices, setGenerating, processResponse])

  const handleFreeInput = (text: string) => sendInput('free', text)

  return (
    <div className="h-screen flex flex-col overflow-hidden relative game-container">

      {/* ====== 场景背景图 ====== */}
      {bgUrl && (
        <div
          className="absolute inset-0 z-0 transition-opacity duration-1000"
          style={{
            backgroundImage: `url(${bgUrl})`,
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            opacity: 0.2,
          }}
        />
      )}
      {/* 背景遮罩（始终有，保证文字可读性） */}
      <div className="absolute inset-0 z-0 game-bg-overlay" />

      {/* ====== 顶部栏 ====== */}
      <header className="shrink-0 z-10 game-header border-b border-white/[0.03]">
        <div className="flex items-center justify-between px-4 py-2.5">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/')}
              className="w-8 h-8 rounded-lg flex items-center justify-center
                         hover:bg-surface-light/50 transition-colors"
            >
              <ArrowLeft size={16} className="text-text-dim" />
            </button>

            {/* 场景信息 */}
            <div className="flex items-center gap-3 text-sm">
              {sceneState.location && (
                <div className="flex items-center gap-1.5 text-text-dim/70">
                  <MapPin size={12} className="text-primary-light/60" />
                  <span className="text-xs">{sceneState.location}</span>
                </div>
              )}
              {sceneState.time && (
                <div className="flex items-center gap-1.5 text-text-dim/50">
                  <Clock size={11} />
                  <span className="text-xs">{sceneState.time}</span>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            {/* BGM 静音/开启切换 */}
            <button
              onClick={toggleBgmMute}
              className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors
                         ${bgmMuted || !bgmEnabled
                           ? 'text-text-dim/40 hover:bg-surface-light/50 hover:text-text-dim'
                           : 'text-primary-light/70 hover:bg-primary/10 hover:text-primary-light'
                         }`}
              title={bgmMuted ? '开启音乐' : '静音'}
            >
              {bgmMuted || !bgmEnabled ? <VolumeX size={16} /> : <Volume2 size={16} />}
            </button>
            <button
              onClick={() => navigate('/load-save')}
              className="w-8 h-8 rounded-lg flex items-center justify-center
                         hover:bg-surface-light/50 transition-colors"
              title="存档管理"
            >
              <Save size={15} className="text-text-dim" />
            </button>
            <button
              onClick={() => navigate('/settings')}
              className="w-8 h-8 rounded-lg flex items-center justify-center
                         hover:bg-surface-light/50 transition-colors"
              title="设置"
            >
              <Settings size={15} className="text-text-dim" />
            </button>
            <button
              onClick={toggleSidePanel}
              className="w-8 h-8 rounded-lg flex items-center justify-center
                         hover:bg-surface-light/50 transition-colors"
            >
              <Menu size={16} className="text-text-dim" />
            </button>
          </div>
        </div>

        {/* 进度条 */}
        <div className="px-4 pb-2">
          <div className="flex items-center gap-2">
            <BookOpen size={12} className="text-primary-light/70 shrink-0" />
            <div className="flex-1 h-1.5 bg-surface-light/20 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-primary to-primary-light rounded-full transition-all duration-500 ease-out"
                style={{ width: `${totalChapters > 0 ? Math.min((chapter / totalChapters) * 100, 100) : 0}%` }}
              />
            </div>
            <span className="text-[10px] text-text-dim/60 shrink-0">
              第{chapter}/{totalChapters}章 · 第{currentTurn}回合
            </span>
          </div>
        </div>
      </header>

      {/* ====== 对话消息区 ====== */}
      <div className="flex-1 overflow-y-auto px-4 py-6 max-w-3xl mx-auto w-full relative z-10">
        {messages.map((msg, index) => (
          <DialogueBox
            key={msg.id || index}
            message={msg}
            isLatest={index === messages.length - 1}
            avatarUrl={msg.speaker ? avatarMap[msg.speaker] ?? null : null}
          />
        ))}

        {/* AI 生成中的加载指示器 */}
        {isGenerating && (
          <div className="flex items-center gap-3 py-3 animate-fade-in">
            <div className="glass-panel px-4 py-2.5 flex items-center gap-3">
              <div className="flex gap-1.5">
                <span className="w-2 h-2 rounded-full bg-primary-light/80"
                      style={{ animation: 'glowPulse 1.2s ease-in-out infinite' }} />
                <span className="w-2 h-2 rounded-full bg-primary-light/60"
                      style={{ animation: 'glowPulse 1.2s ease-in-out 0.2s infinite' }} />
                <span className="w-2 h-2 rounded-full bg-primary-light/40"
                      style={{ animation: 'glowPulse 1.2s ease-in-out 0.4s infinite' }} />
              </div>
              <span className="text-text-dim/50 text-xs">编织梦境中...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* ====== 底部输入区 ====== */}
      <div className="shrink-0 px-4 py-3 max-w-3xl mx-auto w-full relative z-10 game-input-area">
        <div className="divider-gradient mb-3" />

        <ChoicePanel
          choices={currentChoices}
          disabled={isGenerating}
          onSelect={handleChoiceSelect}
        />

        <FreeInput
          disabled={isGenerating}
          onSubmit={handleFreeInput}
        />
      </div>

      {/* 侧边栏 */}
      <SidePanel />

      {/* 好感度飘出提示 */}
      <AffectionToast changes={recentAffectionChanges} />
    </div>
  )
}
