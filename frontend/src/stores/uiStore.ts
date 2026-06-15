/**
 * 织梦绮谭 - UI 状态 Store
 * 管理界面层面的状态（侧边栏、设置等）
 */

import { create } from 'zustand'

interface UIState {
  /** 侧边栏是否展开 */
  sidePanelOpen: boolean

  /** 是否显示好感度数值（默认隐藏，保持沉浸感） */
  showAffectionNumbers: boolean

  /** 打字机速度 (毫秒/字符) */
  typewriterSpeed: number

  /** 对话文字字号 (px) */
  fontSize: number

  /** 全局加载状态 */
  loading: boolean
  loadingText: string

  // Actions
  toggleSidePanel: () => void
  setSidePanelOpen: (v: boolean) => void
  toggleAffectionNumbers: () => void
  setTypewriterSpeed: (ms: number) => void
  setFontSize: (px: number) => void
  setLoading: (v: boolean, text?: string) => void
}

export const useUIStore = create<UIState>((set) => ({
  sidePanelOpen: false,
  showAffectionNumbers: false,
  typewriterSpeed: 35,
  fontSize: 15,
  loading: false,
  loadingText: '',

  toggleSidePanel: () => set((s) => ({ sidePanelOpen: !s.sidePanelOpen })),
  setSidePanelOpen: (v) => set({ sidePanelOpen: v }),
  toggleAffectionNumbers: () =>
    set((s) => ({ showAffectionNumbers: !s.showAffectionNumbers })),
  setTypewriterSpeed: (ms) => set({ typewriterSpeed: ms }),
  setFontSize: (px) => set({ fontSize: px }),
  setLoading: (v, text = '') => set({ loading: v, loadingText: text }),
}))
