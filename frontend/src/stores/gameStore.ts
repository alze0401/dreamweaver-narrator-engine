/**
 * 织梦绮谭 - 游戏状态 Store
 * 管理一局游戏的所有运行时状态
 */

import { create } from 'zustand'
import type {
  DialogueChoice,
  SceneState,
  CharacterSummary,
  AffectionChange,
  DialogueHistoryEntry,
  ProgressInfo,
} from '@/types'

/** 游戏中显示的一条消息（统一格式） */
export interface DisplayMessage {
  id: string
  type: 'narration' | 'dialogue' | 'player' | 'system'
  speaker?: string
  text: string
  emotion?: string
  action?: string
}

interface GameState {
  // ---- 会话信息 ----
  sessionId: string | null
  chapter: number
  totalChapters: number
  currentTurn: number
  currentScene: string
  sceneState: SceneState

  // ---- 对话内容 ----
  messages: DisplayMessage[]
  currentChoices: DialogueChoice[]
  isGenerating: boolean  // AI 是否正在生成

  // ---- 角色 ----
  characters: CharacterSummary[]

  // ---- 对话历史 ----
  dialogueHistory: DialogueHistoryEntry[]

  // ---- 好感度变化通知 ----
  recentAffectionChanges: AffectionChange[]

  // ---- Actions ----
  setSession: (id: string) => void
  setScene: (scene: string, state: SceneState) => void
  setChapter: (ch: number) => void
  setProgress: (progress: ProgressInfo) => void

  /** 添加消息到显示列表 */
  addMessages: (msgs: DisplayMessage[]) => void

  /** 设置当前可选选项 */
  setChoices: (choices: DialogueChoice[]) => void

  /** 设置 AI 生成状态 */
  setGenerating: (v: boolean) => void

  /** 设置角色列表 */
  setCharacters: (chars: CharacterSummary[]) => void

  /** 记录好感度变化 */
  addAffectionChanges: (changes: AffectionChange[]) => void

  /** 清空当前好感度通知 */
  clearAffectionChanges: () => void

  /** 重置游戏状态（退出游戏时调用） */
  reset: () => void
}

let _msgIdCounter = 0
function nextMsgId() {
  return `msg_${++_msgIdCounter}_${Date.now()}`
}

export const useGameStore = create<GameState>((set) => ({
  // 初始状态
  sessionId: null,
  chapter: 1,
  totalChapters: 5,
  currentTurn: 0,
  currentScene: '',
  sceneState: {},
  messages: [],
  currentChoices: [],
  isGenerating: false,
  characters: [],
  dialogueHistory: [],
  recentAffectionChanges: [],

  setSession: (id) => set({ sessionId: id }),

  setScene: (scene, state) => set({ currentScene: scene, sceneState: state }),

  setChapter: (ch) => set({ chapter: ch }),

  setProgress: (progress) =>
    set({
      chapter: progress.chapter,
      totalChapters: progress.total_chapters,
      currentTurn: progress.current_turn,
    }),

  addMessages: (msgs) =>
    set((s) => ({
      messages: [
        ...s.messages,
        ...msgs.map((m) => ({ ...m, id: m.id || nextMsgId() })),
      ],
    })),

  setChoices: (choices) => set({ currentChoices: choices }),

  setGenerating: (v) => set({ isGenerating: v }),

  setCharacters: (chars) => set({ characters: chars }),

  addAffectionChanges: (changes) =>
    set((s) => ({
      recentAffectionChanges: [...s.recentAffectionChanges, ...changes],
    })),

  clearAffectionChanges: () => set({ recentAffectionChanges: [] }),

  reset: () =>
    set({
      sessionId: null,
      chapter: 1,
      totalChapters: 5,
      currentTurn: 0,
      currentScene: '',
      sceneState: {},
      messages: [],
      currentChoices: [],
      isGenerating: false,
      characters: [],
      dialogueHistory: [],
      recentAffectionChanges: [],
    }),
}))
