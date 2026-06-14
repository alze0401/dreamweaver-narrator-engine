/**
 * 织梦绮谭 - 全局 BGM 状态 Store
 * BGM 在所有页面持续播放，不仅限于游戏内
 */

import { create } from 'zustand'

interface BgmState {
  /** 当前 BGM URL */
  bgmUrl: string | null
  /** 是否静音 */
  muted: boolean
  /** 是否启用 BGM */
  enabled: boolean
  /** 音量 0-1 */
  volume: number

  setBgmUrl: (url: string | null) => void
  setMuted: (muted: boolean) => void
  toggleMuted: () => void
  setEnabled: (enabled: boolean) => void
  setVolume: (volume: number) => void
}

export const useBgmStore = create<BgmState>((set) => ({
  bgmUrl: null,
  muted: false,
  enabled: true,
  volume: 0.3,

  setBgmUrl: (url) => set({ bgmUrl: url }),
  setMuted: (muted) => set({ muted }),
  toggleMuted: () => set((s) => ({ muted: !s.muted })),
  setEnabled: (enabled) => set({ enabled }),
  setVolume: (volume) => set({ volume }),
}))
