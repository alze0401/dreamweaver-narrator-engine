/**
 * GlobalBgm - 全局 BGM 播放组件
 * 织梦绮谭 - 在所有页面持续播放背景音乐
 */

import React, { useEffect, useRef } from 'react'
import { useBgmStore } from '@/stores/bgmStore'
import { useUIStore } from '@/stores/uiStore'
import { settingsApi } from '@/services/api'
import { getBgmUrl } from '@/utils/assets'

const DEFAULT_BGM = '/assets/bgm/default.mp3'

/** text_speed 枚举 → typewriterSpeed 毫秒/字符 */
const TEXT_SPEED_MAP: Record<string, number> = {
  slow: 60,
  normal: 35,
  fast: 15,
  instant: 0,
}

export const GlobalBgm: React.FC = () => {
  const audioRef = useRef<HTMLAudioElement>(null)
  const bgmUrl = useBgmStore((s) => s.bgmUrl)
  const muted = useBgmStore((s) => s.muted)
  const enabled = useBgmStore((s) => s.enabled)
  const volume = useBgmStore((s) => s.volume)

  // 启动时从用户设置加载 BGM 配置 + 字号/速度
  useEffect(() => {
    settingsApi.get()
      .then((s) => {
        const store = useBgmStore.getState()
        store.setEnabled(s.bgm_enabled !== false)
        store.setVolume(s.bgm_volume ?? 0.3)
        if (s.bgm_enabled === false) store.setMuted(true)

        // 如果用户有自定义 BGM，优先使用
        if (s.bgm_url) {
          store.setBgmUrl(s.bgm_url)
        } else if (!store.bgmUrl) {
          store.setBgmUrl(DEFAULT_BGM)
        }

        // 同步字号和文字速度到 uiStore
        const ui = useUIStore.getState()
        if (s.font_size) ui.setFontSize(s.font_size)
        if (s.text_speed) {
          const ms = TEXT_SPEED_MAP[s.text_speed] ?? 35
          ui.setTypewriterSpeed(ms)
        }
      })
      .catch(() => {
        // 设置加载失败时使用默认 BGM
        if (!useBgmStore.getState().bgmUrl) {
          useBgmStore.getState().setBgmUrl(DEFAULT_BGM)
        }
      })
  }, [])

  // 控制音频播放
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const cleanupFns: (() => void)[] = []

    if (bgmUrl && !muted && enabled) {
      // 切换曲目
      const fullUrl = window.location.origin + bgmUrl
      if (audio.src !== fullUrl) {
        audio.src = bgmUrl
      }
      audio.volume = volume
      audio.loop = true

      // 加载失败时回退到默认 BGM
      const handleError = () => {
        const store = useBgmStore.getState()
        if (store.bgmUrl !== DEFAULT_BGM) {
          store.setBgmUrl(DEFAULT_BGM)
        }
      }
      audio.addEventListener('error', handleError)
      cleanupFns.push(() => audio.removeEventListener('error', handleError))

      const playPromise = audio.play()
      if (playPromise) {
        playPromise.catch(() => {
          // 浏览器阻止自动播放 → 等待用户交互后恢复
          const resume = () => {
            audio.play().catch(() => {})
            cleanupFns.forEach((fn) => fn())
          }
          const events = ['click', 'touchstart', 'keydown']
          events.forEach((evt) => {
            const handler = () => resume()
            document.addEventListener(evt, handler, { once: true, passive: true })
            cleanupFns.push(() => document.removeEventListener(evt, handler))
          })
        })
      }
    } else {
      audio.pause()
    }

    return () => {
      cleanupFns.forEach((fn) => fn())
    }
  }, [bgmUrl, muted, enabled, volume])

  return <audio ref={audioRef} loop preload="auto" />
}
