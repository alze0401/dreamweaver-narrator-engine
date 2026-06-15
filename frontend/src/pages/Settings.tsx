/**
 * 织梦绮谭 - 设置页
 * 用户头像上传 + 游戏参数设置（BGM / 背景 / 音量 / 文字速度 / 主题等）
 */

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Upload, Camera, Volume2, VolumeX, Music, Image,
  Type, Palette, RotateCcw, Check, Loader2, X,
} from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { useBgmStore } from '@/stores/bgmStore'
import { useUIStore } from '@/stores/uiStore'
import { uploadApi, settingsApi } from '@/services/api'
import type { GameSettings } from '@/types'
import { ImageCropper } from '@/components/ImageCropper'


// ---- 默认设置 ----
const DEFAULT_SETTINGS: GameSettings = {
  bgm_url: null,
  bgm_volume: 0.7,
  bgm_enabled: true,
  sfx_volume: 0.8,
  bg_url: null,
  text_speed: 'normal',
  theme: 'dark',
  font_size: 16,
  auto_advance: false,
  show_affection_popup: true,
}

const TEXT_SPEEDS: Array<{ value: GameSettings['text_speed']; label: string }> = [
  { value: 'slow', label: '缓慢' },
  { value: 'normal', label: '正常' },
  { value: 'fast', label: '快速' },
  { value: 'instant', label: '瞬间' },
]

/** text_speed 枚举 → typewriterSpeed 毫秒/字符 */
const TEXT_SPEED_MAP: Record<string, number> = {
  slow: 60,
  normal: 35,
  fast: 15,
  instant: 0,
}

const THEMES: Array<{ value: string; label: string; desc: string; colors: string }> = [
  { value: 'dark', label: '暗夜', desc: '深紫黑底色', colors: 'from-[#1a1625] to-[#0c0a15] border-white/10' },
  { value: 'sakura', label: '樱花', desc: '浪漫粉嫩', colors: 'from-[#40263a] to-[#150a12] border-pink-400/20' },
  { value: 'ocean', label: '深海', desc: '静谧蓝调', colors: 'from-[#1e2d46] to-[#0a0f1a] border-blue-400/20' },
  { value: 'forest', label: '翠林', desc: '自然清新', colors: 'from-[#1e3728] to-[#0a1510] border-emerald-400/20' },
  { value: 'sunset', label: '夕照', desc: '暖色渐变', colors: 'from-[#3c2a1e] to-[#150e0a] border-orange-400/20' },
  { value: 'light', label: '晨光', desc: '浅色明亮', colors: 'from-[#f5f0ff] to-[#e8e0f5] border-purple-200/40' },
]


// ============================================================
// 子组件：滑块
// ============================================================
const Slider: React.FC<{
  value: number
  onChange: (v: number) => void
  min?: number
  max?: number
  step?: number
  label: string
  icon?: React.ReactNode
  disabled?: boolean
}> = ({ value, onChange, min = 0, max = 1, step = 0.05, label, icon, disabled }) => (
  <div className={`flex items-center gap-3 ${disabled ? 'opacity-40' : ''}`}>
    {icon && <span className="text-primary-light shrink-0">{icon}</span>}
    <span className="text-text text-sm w-16 shrink-0">{label}</span>
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(parseFloat(e.target.value))}
      className="flex-1 h-1.5 appearance-none rounded-full bg-surface-light cursor-pointer
                 accent-primary [&::-webkit-slider-thumb]:appearance-none
                 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4
                 [&::-webkit-slider-thumb]:rounded-full
                 [&::-webkit-slider-thumb]:bg-gradient-to-br
                 [&::-webkit-slider-thumb]:from-primary [&::-webkit-slider-thumb]:to-accent
                 [&::-webkit-slider-thumb]:shadow-lg [&::-webkit-slider-thumb]:cursor-pointer"
    />
    <span className="text-text-dim text-xs w-10 text-right tabular-nums">
      {Math.round(value * 100)}%
    </span>
  </div>
)


// ============================================================
// 子组件：分段选择器
// ============================================================
const SegmentedControl: React.FC<{
  options: Array<{ value: string; label: string }>
  value: string
  onChange: (v: string) => void
}> = ({ options, value, onChange }) => (
  <div className="flex gap-1 p-1 rounded-xl bg-surface-dark/60 border border-white/5">
    {options.map((opt) => (
      <button
        key={opt.value}
        onClick={() => onChange(opt.value)}
        className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
          value === opt.value
            ? 'bg-gradient-to-r from-primary/30 to-accent/20 text-text-bright shadow-sm'
            : 'text-text-dim hover:text-text hover:bg-white/5'
        }`}
      >
        {opt.label}
      </button>
    ))}
  </div>
)


// ============================================================
// 子组件：开关
// ============================================================
const Toggle: React.FC<{
  checked: boolean
  onChange: (v: boolean) => void
  label: string
  desc?: string
}> = ({ checked, onChange, label, desc }) => (
  <div className="flex items-center justify-between">
    <div>
      <span className="text-text text-sm">{label}</span>
      {desc && <p className="text-text-dim/60 text-xs mt-0.5">{desc}</p>}
    </div>
    <button
      onClick={() => onChange(!checked)}
      className={`relative w-11 h-6 rounded-full transition-colors duration-200 ${
        checked
          ? 'bg-gradient-to-r from-primary to-accent'
          : 'bg-surface-light border border-white/10'
      }`}
    >
      <span
        className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform duration-200 ${
          checked ? 'translate-x-[22px]' : 'translate-x-0.5'
        }`}
      />
    </button>
  </div>
)


// ============================================================
// 子组件：区块标题
// ============================================================
const SectionTitle: React.FC<{ icon: React.ReactNode; title: string }> = ({ icon, title }) => (
  <div className="flex items-center gap-2 mb-4">
    <span className="text-primary-light">{icon}</span>
    <h3 className="text-text-bright text-sm font-medium tracking-wide">{title}</h3>
    <div className="flex-1 divider-gradient ml-2" />
  </div>
)


// ============================================================
// 主页面
// ============================================================
export const Settings: React.FC = () => {
  const navigate = useNavigate()
  const { user, isAuthenticated, setAuth } = useAuthStore()

  // ---- 状态 ----
  const [settings, setSettings] = useState<GameSettings>(DEFAULT_SETTINGS)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saveOk, setSaveOk] = useState(false)

  // 头像上传
  const avatarInputRef = useRef<HTMLInputElement>(null)
  const [avatarUploading, setAvatarUploading] = useState(false)
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null)
  const [cropImageSrc, setCropImageSrc] = useState<File | null>(null)
  const [avatarImgFailed, setAvatarImgFailed] = useState(false)

  // BGM 上传
  const bgmInputRef = useRef<HTMLInputElement>(null)
  const [bgmUploading, setBgmUploading] = useState(false)

  // 背景上传
  const bgInputRef = useRef<HTMLInputElement>(null)
  const [bgUploading, setBgUploading] = useState(false)

  // 音频预览
  const audioRef = useRef<HTMLAudioElement>(null)

  // ---- 加载设置 ----
  useEffect(() => {
    if (!isAuthenticated) return
    settingsApi.get()
      .then((s) => {
        setSettings(s)
        // 加载时也应用主题
        if (s.theme) {
          document.documentElement.setAttribute('data-theme', s.theme)
          try { localStorage.setItem('dw_theme', s.theme) } catch {}
        }
        // 同步音频设置到 bgmStore
        const bgm = useBgmStore.getState()
        bgm.setEnabled(s.bgm_enabled !== false)
        bgm.setVolume(s.bgm_volume ?? 0.3)
        bgm.setMuted(s.bgm_enabled === false)
        if (s.bgm_url) bgm.setBgmUrl(s.bgm_url)
        // 同步字号和文字速度到 uiStore
        if (s.font_size) useUIStore.getState().setFontSize(s.font_size)
        if (s.text_speed) {
          const ms = TEXT_SPEED_MAP[s.text_speed] ?? 35
          useUIStore.getState().setTypewriterSpeed(ms)
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [isAuthenticated])

  // ---- 自动保存（防抖） ----
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const debouncedSave = useCallback(
    (patch: Partial<GameSettings>) => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
      saveTimerRef.current = setTimeout(() => {
        setSaving(true)
        setSaveOk(false)
        settingsApi.update(patch)
          .then((updated) => setSettings(updated))
          .catch(() => {})
          .finally(() => {
            setSaving(false)
            setSaveOk(true)
            setTimeout(() => setSaveOk(false), 1500)
          })
      }, 600)
    },
    [],
  )

  const updateSetting = <K extends keyof GameSettings>(key: K, value: GameSettings[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }))
    // 主题变更时立即应用并缓存到 localStorage
    if (key === 'theme') {
      document.documentElement.setAttribute('data-theme', value as string)
      try { localStorage.setItem('dw_theme', value as string) } catch {}
      window.dispatchEvent(new CustomEvent('dw:themeChanged', { detail: { theme: value } }))
    }
    // 音频设置同步到 bgmStore（实时生效）
    if (key === 'bgm_enabled') {
      const enabled = value as boolean
      useBgmStore.getState().setEnabled(enabled)
      if (!enabled) useBgmStore.getState().setMuted(true)
      else useBgmStore.getState().setMuted(false)
    }
    if (key === 'bgm_volume') {
      useBgmStore.getState().setVolume(value as number)
    }
    if (key === 'bgm_url') {
      useBgmStore.getState().setBgmUrl((value as string) || '/assets/bgm/default.mp3')
    }
    // 字号同步到 uiStore（实时生效）
    if (key === 'font_size') {
      useUIStore.getState().setFontSize(value as number)
    }
    // 文字速度同步到 uiStore
    if (key === 'text_speed') {
      const ms = TEXT_SPEED_MAP[value as string] ?? 35
      useUIStore.getState().setTypewriterSpeed(ms)
    }
    debouncedSave({ [key]: value })
  }

  // ---- 头像上传 ----
  const handleAvatarClick = () => avatarInputRef.current?.click()
  const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    // 打开裁剪器而不是直接上传
    setCropImageSrc(file)
    e.target.value = ''
  }

  const handleCropConfirm = async (croppedBlob: Blob) => {
    setCropImageSrc(null)
    // 预览裁剪结果
    const previewUrl = URL.createObjectURL(croppedBlob)
    setAvatarPreview(previewUrl)
    setAvatarImgFailed(false)
    setAvatarUploading(true)
    try {
      // 将 Blob 转为 File 对象用于上传
      const croppedFile = new File([croppedBlob], 'avatar.webp', { type: 'image/webp' })
      const { url } = await uploadApi.avatar(croppedFile)
      // 更新 authStore 中的 user
      if (user) {
        const updatedUser = { ...user, avatar_url: url }
        setAuth(useAuthStore.getState().token!, updatedUser)
      }
      setAvatarPreview(url)
    } catch (err: any) {
      alert(`头像上传失败: ${err.message}`)
      setAvatarPreview(null)
    } finally {
      setAvatarUploading(false)
      URL.revokeObjectURL(previewUrl)
    }
  }

  const handleCropCancel = () => {
    setCropImageSrc(null)
  }

  // ---- BGM 上传 ----
  const handleBgmUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setBgmUploading(true)
    try {
      const name = file.name.replace(/\.[^.]+$/, '')
      const { url } = await uploadApi.bgm(name, file)
      updateSetting('bgm_url', url)
    } catch (err: any) {
      alert(`BGM 上传失败: ${err.message}`)
    } finally {
      setBgmUploading(false)
      e.target.value = ''
    }
  }

  // ---- 背景上传 ----
  const handleBgUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setBgUploading(true)
    try {
      const name = file.name.replace(/\.[^.]+$/, '')
      const { url } = await uploadApi.background(name, file)
      updateSetting('bg_url', url)
    } catch (err: any) {
      alert(`背景上传失败: ${err.message}`)
    } finally {
      setBgUploading(false)
      e.target.value = ''
    }
  }

  // ---- 重置 ----
  const handleReset = async () => {
    if (!confirm('确定要重置所有设置为默认值吗？')) return
    try {
      const reset = await settingsApi.reset()
      setSettings(reset)
    } catch {}
  }

  // ---- 试听 BGM ----
  const playBgmPreview = () => {
    if (audioRef.current && settings.bgm_url) {
      if (audioRef.current.paused) {
        audioRef.current.play()
      } else {
        audioRef.current.pause()
      }
    }
  }

  // ---- 移除 BGM ----
  const handleRemoveBgm = async () => {
    try {
      await settingsApi.removeBgm()
      updateSetting('bgm_url', null)
    } catch {}
  }

  // ---- 移除背景 ----
  const handleRemoveBg = async () => {
    try {
      await settingsApi.removeBg()
      updateSetting('bg_url', null)
    } catch {}
  }

  // 当前显示的头像
  const displayAvatar = avatarPreview || user?.avatar_url || null

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-dark">
        <div className="glass-panel p-8 text-center max-w-sm">
          <p className="text-text text-lg mb-4">请先登录后再使用设置功能</p>
          <button
            onClick={() => navigate('/login')}
            className="btn-gradient px-6 py-2 rounded-xl text-sm text-white font-medium"
          >
            前往登录
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-surface-dark via-surface to-surface-dark py-8 px-4">
      <div className="max-w-2xl mx-auto">

        {/* ---- 顶部导航 ---- */}
        <div className="flex items-center justify-between mb-8 animate-fade-in">
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate(-1)}
              className="glass-panel flex items-center gap-2 px-4 py-2
                         text-text-dim hover:text-text-bright text-sm transition-colors duration-200"
            >
              <ArrowLeft size={15} />
              <span>返回</span>
            </button>
            <button
              onClick={() => navigate('/')}
              className="glass-panel flex items-center gap-2 px-3 py-2
                         text-text-dim/50 hover:text-text-dim text-xs transition-colors duration-200"
            >
              <span>返回首页</span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            {saving && (
              <span className="flex items-center gap-1.5 text-primary-light text-xs">
                <Loader2 size={12} className="animate-spin" />
                保存中...
              </span>
            )}
            {saveOk && (
              <span className="flex items-center gap-1.5 text-emerald-400 text-xs animate-fade-in">
                <Check size={12} />
                已保存
              </span>
            )}
            <button
              onClick={handleReset}
              className="glass-panel flex items-center gap-1.5 px-3 py-2
                         text-text-dim/60 hover:text-amber-300 text-xs transition-colors duration-200"
              title="重置为默认设置"
            >
              <RotateCcw size={13} />
              <span>重置</span>
            </button>
          </div>
        </div>

        {/* ---- 页面标题 ---- */}
        <div className="text-center mb-10 animate-fade-in">
          <h1 className="title-shimmer text-3xl font-bold tracking-wider font-display">
            设置
          </h1>
          <p className="text-text-dim/40 text-xs tracking-widest mt-2">
            PREFERENCES & PERSONALIZATION
          </p>
        </div>

        {loading ? (
          <div className="flex justify-center py-20">
            <Loader2 size={28} className="animate-spin text-primary-light" />
          </div>
        ) : (
          <div className="space-y-6">

            {/* ==========================================
                头像区域
                ========================================== */}
            <section className="glass-panel p-6 choice-appear">
              <SectionTitle icon={<Camera size={16} />} title="个人头像" />
              <div className="flex items-center gap-6">
                {/* 头像预览 */}
                <button
                  onClick={handleAvatarClick}
                  className="relative group w-24 h-24 rounded-2xl overflow-hidden shrink-0
                             bg-surface-light border border-white/5
                             hover:border-primary/30 transition-all duration-300"
                >
                  {displayAvatar && !avatarImgFailed ? (
                    <img
                      src={displayAvatar}
                      alt="头像"
                      className="w-full h-full object-cover"
                      onError={() => setAvatarImgFailed(true)}
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <span className="text-4xl font-display text-primary/40">
                        {(user?.display_name || user?.username || '?')[0]}
                      </span>
                    </div>
                  )}
                  {/* hover 遮罩 */}
                  <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100
                                  flex items-center justify-center transition-opacity duration-200">
                    {avatarUploading ? (
                      <Loader2 size={24} className="animate-spin text-white" />
                    ) : (
                      <Upload size={20} className="text-white" />
                    )}
                  </div>
                </button>

                <div className="flex-1">
                  <p className="text-text text-sm mb-1">
                    {user?.display_name || user?.username}
                  </p>
                  <p className="text-text-dim/50 text-xs mb-3">
                    点击头像上传新图片，支持 PNG / JPEG / WebP，最大 5MB
                  </p>
                  <button
                    onClick={handleAvatarClick}
                    className="text-xs text-primary-light hover:text-accent-light transition-colors"
                  >
                    {displayAvatar ? '更换头像' : '上传头像'}
                  </button>
                </div>
              </div>
              <input
                ref={avatarInputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif"
                className="hidden"
                onChange={handleAvatarChange}
              />
            </section>

            {/* ==========================================
                音频设置
                ========================================== */}
            <section className="glass-panel p-6 choice-appear">
              <SectionTitle icon={<Volume2 size={16} />} title="音频设置" />
              <div className="space-y-5">
                {/* BGM 开关 */}
                <Toggle
                  checked={settings.bgm_enabled}
                  onChange={(v) => updateSetting('bgm_enabled', v)}
                  label="启用背景音乐"
                  desc="关闭后游戏内不播放 BGM"
                />

                {/* BGM 音量 */}
                <Slider
                  value={settings.bgm_volume}
                  onChange={(v) => updateSetting('bgm_volume', v)}
                  label="BGM 音量"
                  icon={<Music size={14} />}
                  disabled={!settings.bgm_enabled}
                />

                {/* 音效音量 */}
                <Slider
                  value={settings.sfx_volume}
                  onChange={(v) => updateSetting('sfx_volume', v)}
                  label="音效音量"
                  icon={<Volume2 size={14} />}
                />

                {/* BGM 文件 */}
                <div className="border-t border-white/5 pt-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-text text-sm">自定义 BGM</span>
                    <div className="flex items-center gap-2">
                      {settings.bgm_url && (
                        <>
                          <button
                            onClick={playBgmPreview}
                            className="text-xs text-primary-light hover:text-accent-light transition-colors"
                          >
                            试听
                          </button>
                          <button
                            onClick={handleRemoveBgm}
                            className="text-xs text-text-dim/50 hover:text-red-400 transition-colors"
                          >
                            <X size={12} />
                          </button>
                        </>
                      )}
                    </div>
                  </div>

                  {settings.bgm_url ? (
                    <div className="glass-panel px-4 py-3 flex items-center gap-3">
                      <Music size={14} className="text-accent-light shrink-0" />
                      <span className="text-text-dim text-xs truncate flex-1">{settings.bgm_url}</span>
                    </div>
                  ) : (
                    <button
                      onClick={() => bgmInputRef.current?.click()}
                      disabled={bgmUploading}
                      className="glass-panel w-full px-4 py-3 flex items-center justify-center gap-2
                                 text-text-dim/60 hover:text-primary-light text-xs
                                 border border-dashed border-white/10 hover:border-primary/30
                                 transition-all duration-200 cursor-pointer"
                    >
                      {bgmUploading ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <Upload size={14} />
                      )}
                      <span>{bgmUploading ? '上传中...' : '点击上传 BGM 文件 (MP3/OGG/WAV)'}</span>
                    </button>
                  )}
                  <input
                    ref={bgmInputRef}
                    type="file"
                    accept="audio/mpeg,audio/mp3,audio/ogg,audio/wav,audio/flac"
                    className="hidden"
                    onChange={handleBgmUpload}
                  />
                  {settings.bgm_url && (
                    <audio ref={audioRef} src={settings.bgm_url} preload="none" />
                  )}
                </div>
              </div>
            </section>

            {/* ==========================================
                视觉设置
                ========================================== */}
            <section className="glass-panel p-6 choice-appear">
              <SectionTitle icon={<Palette size={16} />} title="视觉设置" />
              <div className="space-y-5">
                {/* 主题 */}
                <div>
                  <span className="text-text text-sm block mb-3">界面主题</span>
                  <div className="grid grid-cols-3 gap-2">
                    {THEMES.map((t) => (
                      <button
                        key={t.value}
                        onClick={() => updateSetting('theme', t.value as GameSettings['theme'])}
                        className={`glass-panel px-3 py-3 text-center transition-all duration-200 ${
                          settings.theme === t.value
                            ? 'card-selected'
                            : 'hover:border-white/15'
                        }`}
                      >
                        <div className={`w-8 h-8 rounded-full mx-auto mb-2 bg-gradient-to-br ${t.colors}`} />
                        <p className="text-text text-xs font-medium">{t.label}</p>
                        <p className="text-text-dim/40 text-[10px] mt-0.5">{t.desc}</p>
                      </button>
                    ))}
                  </div>
                </div>

                {/* 字号 */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-text text-sm flex items-center gap-2">
                      <Type size={14} className="text-primary-light" />
                      对话文字字号
                    </span>
                    <span className="text-text-dim text-xs tabular-nums">{settings.font_size}px</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-text-dim/60 text-xs">A</span>
                    <input
                      type="range"
                      min={12}
                      max={24}
                      step={1}
                      value={settings.font_size}
                      onChange={(e) => updateSetting('font_size', parseInt(e.target.value))}
                      className="flex-1 h-1.5 appearance-none rounded-full bg-surface-light cursor-pointer
                                 accent-primary [&::-webkit-slider-thumb]:appearance-none
                                 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4
                                 [&::-webkit-slider-thumb]:rounded-full
                                 [&::-webkit-slider-thumb]:bg-gradient-to-br
                                 [&::-webkit-slider-thumb]:from-primary [&::-webkit-slider-thumb]:to-accent
                                 [&::-webkit-slider-thumb]:shadow-lg [&::-webkit-slider-thumb]:cursor-pointer"
                    />
                    <span className="text-text-dim/60 text-base font-medium">A</span>
                  </div>
                  {/* 预览文字 */}
                  <div className="mt-3 glass-panel px-4 py-3">
                    <p style={{ fontSize: `${settings.font_size}px` }} className="text-text leading-relaxed">
                      示例对话：月色如水，花瓣轻落湖面，泛起层层涟漪。
                    </p>
                  </div>
                </div>

                {/* 背景图 */}
                <div className="border-t border-white/5 pt-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-text text-sm flex items-center gap-2">
                      <Image size={14} className="text-primary-light" />
                      自定义游戏背景
                    </span>
                    {settings.bg_url && (
                      <button
                        onClick={handleRemoveBg}
                        className="text-xs text-text-dim/50 hover:text-red-400 transition-colors"
                      >
                        <X size={12} />
                      </button>
                    )}
                  </div>

                  {settings.bg_url ? (
                    <div className="relative rounded-xl overflow-hidden h-36 border border-white/5">
                      <img
                        src={settings.bg_url}
                        alt="游戏背景"
                        className="w-full h-full object-cover"
                      />
                    </div>
                  ) : (
                    <button
                      onClick={() => bgInputRef.current?.click()}
                      disabled={bgUploading}
                      className="glass-panel w-full px-4 py-8 flex flex-col items-center justify-center gap-2
                                 text-text-dim/60 hover:text-primary-light text-xs
                                 border border-dashed border-white/10 hover:border-primary/30
                                 transition-all duration-200 cursor-pointer"
                    >
                      {bgUploading ? (
                        <Loader2 size={20} className="animate-spin" />
                      ) : (
                        <Image size={20} />
                      )}
                      <span>{bgUploading ? '上传中...' : '点击上传背景图 (PNG/JPEG/WebP)'}</span>
                    </button>
                  )}
                  <input
                    ref={bgInputRef}
                    type="file"
                    accept="image/png,image/jpeg,image/webp,image/gif"
                    className="hidden"
                    onChange={handleBgUpload}
                  />
                </div>
              </div>
            </section>

            {/* ==========================================
                游戏偏好
                ========================================== */}
            <section className="glass-panel p-6 choice-appear">
              <SectionTitle icon={<Type size={16} />} title="游戏偏好" />
              <div className="space-y-5">
                {/* 文字速度 */}
                <div>
                  <span className="text-text text-sm block mb-3">文字显示速度</span>
                  <SegmentedControl
                    options={TEXT_SPEEDS.map((s) => ({ value: s.value, label: s.label }))}
                    value={settings.text_speed}
                    onChange={(v) => updateSetting('text_speed', v as GameSettings['text_speed'])}
                  />
                </div>

                {/* 自动推进 */}
                <Toggle
                  checked={settings.auto_advance}
                  onChange={(v) => updateSetting('auto_advance', v)}
                  label="自动推进对话"
                  desc="开启后 AI 生成内容将自动逐字显示完毕后自动跳转"
                />

                {/* 好感度弹窗 */}
                <Toggle
                  checked={settings.show_affection_popup}
                  onChange={(v) => updateSetting('show_affection_popup', v)}
                  label="显示好感度变化"
                  desc="角色好感度变化时弹出通知提示"
                />
              </div>
            </section>

          </div>
        )}

        {/* ---- 底部留白 ---- */}
        <div className="h-12" />
      </div>

      {/* 头像裁剪器 */}
      {cropImageSrc && (
        <ImageCropper
          imageSrc={cropImageSrc}
          cropSize={240}
          onConfirm={handleCropConfirm}
          onCancel={handleCropCancel}
        />
      )}
    </div>
  )
}
