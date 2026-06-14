/**
 * TemplateForm - 模板创建/编辑表单
 * 织梦绮谭 - 支持世界观/角色/剧本三种类型
 * 含 AI 自动生成功能
 */

import React, { useState, useEffect, useRef } from 'react'
import { Globe, Users, BookMarked, Sparkles, ArrowLeft, Save, Loader2, Tag, Check, Upload, Image } from 'lucide-react'
import { templateApi, categoryApi, uploadApi } from '@/services/api'
import { useUIStore } from '@/stores/uiStore'
import { ImageCropper } from '@/components/ImageCropper'
import type { TemplateSummary, Category } from '@/types'

interface TemplateFormProps {
  /** 编辑时传入当前类型，跳过类型选择步骤 */
  initialType?: 'world' | 'character' | 'scenario'
  /** 编辑时传入当前模板数据 */
  initialData?: (TemplateSummary & { data: Record<string, unknown>; categories?: Array<{ code: string; name: string }> }) | null
  /** 保存成功后回调 */
  onSaved: () => void
  /** 取消回调 */
  onCancel: () => void
}

const TYPE_CARDS = [
  { key: 'world' as const, label: '世界观', desc: '时代背景、世界规则', icon: Globe, color: 'primary' },
  { key: 'character' as const, label: '角色', desc: '性格、关系配置', icon: Users, color: 'accent' },
  { key: 'scenario' as const, label: '剧本', desc: '故事框架、剧情钩子', icon: BookMarked, color: 'emerald' },
]

/* 从模板 data 中提取表单初始值 */
function extractInitialFields(type: string, data?: Record<string, unknown>) {
  if (!data) return {}
  const result: Record<string, unknown> = {}

  if (type === 'world' && data.world && typeof data.world === 'object') {
    const w = data.world as Record<string, unknown>
    result.era = w.era || ''
    result.genre = Array.isArray(w.genre) ? w.genre.join(', ') : (w.genre || '')
    result.setting_description = w.setting_description || ''
    result.rules = Array.isArray(w.rules) ? w.rules.join('\n') : (w.rules || '')
  }

  if (type === 'character') {
    const charData = (data.character || data) as Record<string, unknown>
    const personality = (charData.personality || {}) as Record<string, unknown>
    const speechStyle = (personality.speech_style || {}) as Record<string, unknown>
    result.full_name = charData.full_name || ''
    result.archetype = personality.archetype || ''
    result.mbti = personality.mbti || ''
    result.likes = Array.isArray(personality.likes) ? personality.likes.join(', ') : (personality.likes || '')
    result.dislikes = Array.isArray(personality.dislikes) ? personality.dislikes.join(', ') : (personality.dislikes || '')
    result.speech_tone = speechStyle.tone || ''
  }

  if (type === 'scenario' && data.scenario && typeof data.scenario === 'object') {
    const s = data.scenario as Record<string, unknown>
    const opening = (s.opening_scene || {}) as Record<string, unknown>
    result.premise = s.premise || ''
    result.opening_location = opening.location || ''
    result.opening_time = opening.time || ''
    result.plot_hooks = Array.isArray(s.plot_hooks) ? s.plot_hooks.join('\n') : (s.plot_hooks || '')
    result.estimated_chapters = s.estimated_chapters || 5
  }

  return result
}

/* 将表单字段组装为后端所需的 data dict */
function assembleData(type: string, fields: Record<string, string | number>): Record<string, unknown> {
  if (type === 'world') {
    return {
      world: {
        era: fields.era || '',
        genre: typeof fields.genre === 'string' ? fields.genre.split(',').map((s: string) => s.trim()).filter(Boolean) : [],
        setting_description: fields.setting_description || '',
        rules: typeof fields.rules === 'string' ? fields.rules.split('\n').map((s: string) => s.trim()).filter(Boolean) : [],
      },
    }
  }

  if (type === 'character') {
    return {
      character: {
        full_name: fields.full_name || '',
        personality: {
          archetype: fields.archetype || '',
          mbti: fields.mbti || '',
          likes: typeof fields.likes === 'string' ? fields.likes.split(',').map((s: string) => s.trim()).filter(Boolean) : [],
          dislikes: typeof fields.dislikes === 'string' ? fields.dislikes.split(',').map((s: string) => s.trim()).filter(Boolean) : [],
          speech_style: {
            tone: fields.speech_tone || '',
          },
        },
        relationships: {},
      },
      affection_config: {
        initial_value: 0,
      },
    }
  }

  if (type === 'scenario') {
    return {
      scenario: {
        premise: fields.premise || '',
        opening_scene: {
          location: fields.opening_location || '',
          time: fields.opening_time || '',
          weather: '',
        },
        chapter_beats: [],
        plot_hooks: typeof fields.plot_hooks === 'string' ? fields.plot_hooks.split('\n').map((s: string) => s.trim()).filter(Boolean) : [],
        estimated_chapters: Number(fields.estimated_chapters) || 5,
      },
    }
  }

  return {}
}

export const TemplateForm: React.FC<TemplateFormProps> = ({
  initialType,
  initialData,
  onSaved,
  onCancel,
}) => {
  const setLoading = useUIStore((s) => s.setLoading)
  const isEditing = !!initialData

  // Step state: if editing, skip type selection
  const [step, setStep] = useState<number>(initialType ? 1 : 0)
  const [selectedType, setSelectedType] = useState<'world' | 'character' | 'scenario'>(initialType || 'world')

  // Form fields
  const [name, setName] = useState(initialData?.name || '')
  const [description, setDescription] = useState(initialData?.description || '')
  const [fields, setFields] = useState<Record<string, string | number>>(() =>
    extractInitialFields(initialType || '', initialData?.data) as Record<string, string | number>
  )

  // AI generate state
  const [aiPrompt, setAiPrompt] = useState('')
  const [aiGenerating, setAiGenerating] = useState(false)

  // Category state
  const [allCategories, setAllCategories] = useState<Category[]>([])
  const [selectedCategoryCodes, setSelectedCategoryCodes] = useState<string[]>(() =>
    initialData?.categories?.map(c => c.code) || ['custom']
  )
  const [loadingCategories, setLoadingCategories] = useState(true)

  // Character avatar upload state
  const charAvatarInputRef = useRef<HTMLInputElement>(null)
  const [charAvatarFile, setCharAvatarFile] = useState<File | null>(null)
  const [charAvatarPreview, setCharAvatarPreview] = useState<string | null>(null)
  const [charAvatarUploading, setCharAvatarUploading] = useState(false)
  // ImageCropper state
  const [cropperSrc, setCropperSrc] = useState<File | null>(null)

  // If editing a character template and it has avatar_url in initialData
  useEffect(() => {
    if (initialType === 'character' && initialData?.avatar_url) {
      setCharAvatarPreview(initialData.avatar_url)
    }
  }, [initialData, initialType])

  // Load categories on mount
  useEffect(() => {
    categoryApi.list()
      .then(cats => setAllCategories(cats))
      .catch(err => console.error('加载分类列表失败:', err))
      .finally(() => setLoadingCategories(false))
  }, [])

  const toggleCategory = (code: string) => {
    setSelectedCategoryCodes(prev =>
      prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]
    )
  }

  // When editing and we have initial data, pre-fill after mount
  useEffect(() => {
    if (initialData?.data) {
      const extracted = extractInitialFields(initialType || '', initialData.data)
      setFields(extracted as Record<string, string | number>)
      setName(initialData.name || '')
      setDescription(initialData.description || '')
      // 预填已选分类
      if (initialData.categories) {
        setSelectedCategoryCodes(initialData.categories.map(c => c.code))
      }
    }
  }, [initialData, initialType])

  const setField = (key: string, value: string | number) => {
    setFields((prev) => ({ ...prev, [key]: value }))
  }

  // AI Generate handler
  const handleAiGenerate = async () => {
    if (!aiPrompt.trim()) return
    setAiGenerating(true)
    try {
      const res = await templateApi.aiGenerate(selectedType, aiPrompt.trim())
      const data = res.data

      // 从结构化输出中提取 name 和 description
      if (data.name && !name) {
        setName(data.name as string)
      }
      if (data.description && !description) {
        setDescription(data.description as string)
      }

      // Extract relevant fields from generated data into form
      if (selectedType === 'world') {
        // 兼容两种格式: { world: { era, genre, ... } } 和 { era, genre, ... } (扁平)
        const w = (data.world || data) as Record<string, unknown>
        setFields((prev) => ({
          ...prev,
          era: (w.era as string) || prev.era || '',
          genre: Array.isArray(w.genre) ? w.genre.join(', ') : (w.genre as string) || prev.genre || '',
          setting_description: (w.setting_description as string) || prev.setting_description || '',
          rules: Array.isArray(w.rules) ? w.rules.join('\n') : (w.rules as string) || prev.rules || '',
        }))
      }

      if (selectedType === 'character') {
        const charData = (data.character || data) as Record<string, unknown>
        const personality = (charData.personality || {}) as Record<string, unknown>
        const speechStyle = (personality.speech_style || {}) as Record<string, unknown>
        setFields((prev) => ({
          ...prev,
          full_name: (charData.full_name as string) || prev.full_name || '',
          archetype: (personality.archetype as string) || prev.archetype || '',
          mbti: (personality.mbti as string) || prev.mbti || '',
          likes: Array.isArray(personality.likes) ? personality.likes.join(', ') : (personality.likes as string) || prev.likes || '',
          dislikes: Array.isArray(personality.dislikes) ? personality.dislikes.join(', ') : (personality.dislikes as string) || prev.dislikes || '',
          speech_tone: (speechStyle.tone as string) || prev.speech_tone || '',
        }))
      }

      if (selectedType === 'scenario') {
        const s = (data.scenario || data) as Record<string, unknown>
        const opening = (s.opening_scene || {}) as Record<string, unknown>
        setFields((prev) => ({
          ...prev,
          premise: (s.premise as string) || prev.premise || '',
          opening_location: (opening.location as string) || prev.opening_location || '',
          opening_time: (opening.time as string) || prev.opening_time || '',
          plot_hooks: Array.isArray(s.plot_hooks) ? s.plot_hooks.join('\n') : (s.plot_hooks as string) || prev.plot_hooks || '',
          estimated_chapters: Number(s.estimated_chapters) || prev.estimated_chapters || 5,
        }))
      }

      setAiPrompt('')
    } catch (err) {
      console.error('AI 生成失败:', err)
      alert('AI 生成失败: ' + (err as Error).message)
    } finally {
      setAiGenerating(false)
    }
  }

  // Save handler
  const handleSave = async () => {
    if (!name.trim()) {
      alert('请填写模板名称')
      return
    }

    const data = assembleData(selectedType, fields)

    setLoading(true, isEditing ? '保存中...' : '创建中...')
    try {
      let templateId: string | null = null

      if (isEditing && initialData) {
        await templateApi.update(initialData.template_id, {
          name: name.trim(),
          description: description.trim(),
          data,
          category_codes: selectedCategoryCodes,
        })
        templateId = initialData.template_id
      } else {
        const res = await templateApi.create({
          template_type: selectedType,
          name: name.trim(),
          description: description.trim(),
          data,
          category_codes: selectedCategoryCodes,
        })
        templateId = res.data.template_id
      }

      // 如果是角色模板且有头像文件，上传头像
      if (selectedType === 'character' && charAvatarFile && templateId) {
        setCharAvatarUploading(true)
        try {
          const uploadRes = await uploadApi.characterAvatar(templateId, charAvatarFile)
          // 上传成功后用返回的 URL 更新预览（确保显示最新头像）
          if (uploadRes?.url) {
            setCharAvatarPreview(uploadRes.url)
          } else {
            console.warn('头像上传成功但返回 URL 为空', uploadRes)
          }
        } catch (err) {
          console.error('角色头像上传失败:', err)
          // 通知用户头像上传失败（模板本身已保存成功）
          alert(`模板保存成功，但角色头像上传失败: ${(err as Error).message}\n请重试头像上传。`)
        } finally {
          setCharAvatarUploading(false)
        }
      }

      onSaved()
    } catch (err) {
      console.error('保存模板失败:', err)
      alert('保存失败: ' + (err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  // ===== Shared input styles =====
  const inputCls =
    'w-full bg-surface-dark/60 border border-white/[0.06] focus:border-primary/40 rounded-xl px-4 py-3 text-text-bright text-sm outline-none transition-colors placeholder:text-text-dim/30'
  const textareaCls =
    'w-full bg-surface-dark/60 border border-white/[0.06] focus:border-primary/40 rounded-xl px-4 py-3 text-text-bright text-sm outline-none transition-colors placeholder:text-text-dim/30 resize-none'
  const labelCls = 'text-text-dim/70 text-xs block mb-2 tracking-wide'

  return (
    <div className="space-y-6">
      {/* ====== Step 0: 选择类型 ====== */}
      {step === 0 && (
        <div className="space-y-4 animate-fade-in">
          <p className="text-text-dim/60 text-sm">选择要创建的模板类型</p>
          <div className="grid grid-cols-3 gap-3">
            {TYPE_CARDS.map(({ key, label, desc, icon: Icon }) => (
              <button
                key={key}
                onClick={() => {
                  setSelectedType(key)
                  setStep(1)
                }}
                className="glass-panel p-5 flex flex-col items-center gap-3 hover:border-primary/25 transition-all duration-200 group"
              >
                <div className="w-12 h-12 rounded-xl flex items-center justify-center
                                bg-surface-light/10 group-hover:bg-primary/15 transition-colors duration-200">
                  <Icon size={22} className="text-text-dim/60 group-hover:text-primary-light transition-colors duration-200" />
                </div>
                <div className="text-center">
                  <p className="text-text-bright text-sm font-medium">{label}</p>
                  <p className="text-text-dim/40 text-[10px] mt-1">{desc}</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ====== Step 1: 填写表单 ====== */}
      {step === 1 && (
        <div className="space-y-5 animate-fade-in">
          {/* Type indicator + back */}
          {!isEditing && (
            <button
              onClick={() => setStep(0)}
              className="flex items-center gap-1.5 text-text-dim/50 text-xs hover:text-text-dim transition-colors"
            >
              <ArrowLeft size={12} /> 更换类型
            </button>
          )}

          <div className="flex items-center gap-2 mb-1">
            {TYPE_CARDS.find((t) => t.key === selectedType)?.icon &&
              (() => {
                const Icon = TYPE_CARDS.find((t) => t.key === selectedType)!.icon
                return <Icon size={16} className="text-primary-light" />
              })()}
            <span className="text-text-bright text-sm font-medium">
              {TYPE_CARDS.find((t) => t.key === selectedType)?.label} 模板
            </span>
          </div>

          {/* AI Generate bar */}
          <div className="glass-panel p-4 space-y-3">
            <div className="flex items-center gap-2 mb-1">
              <Sparkles size={13} className="text-accent-light" />
              <span className="text-text-dim/70 text-xs">AI 辅助生成模板内容</span>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !aiGenerating && handleAiGenerate()}
                placeholder="描述你想要的模板，例如：一个架空中世纪魔法世界..."
                className={inputCls}
                disabled={aiGenerating}
              />
              <button
                onClick={handleAiGenerate}
                disabled={aiGenerating || !aiPrompt.trim()}
                className={`shrink-0 flex items-center gap-1.5 px-5 py-3 rounded-xl text-xs font-medium transition-all duration-200
                  ${aiGenerating || !aiPrompt.trim()
                    ? 'bg-surface-light/20 text-text-dim/40 cursor-not-allowed border border-white/[0.04]'
                    : 'btn-accent text-white shadow-[0_4px_16px_rgba(244,114,182,0.2)]'
                  }`}
              >
                {aiGenerating ? (
                  <>
                    <Loader2 size={13} className="animate-spin" /> 生成中
                  </>
                ) : (
                  <>
                    <Sparkles size={13} /> AI 生成
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Basic fields */}
          <div className="space-y-4">
            <div>
              <label className={labelCls}>模板名称 *</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="输入模板名称"
                className={inputCls}
              />
            </div>
            <div>
              <label className={labelCls}>模板描述</label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="简要描述这个模板"
                className={inputCls}
              />
            </div>
          </div>

          {/* Category selection */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Tag size={12} className="text-primary-light/60" />
              <label className={`${labelCls} mb-0`}>关联分类</label>
              <span className="text-text-dim/30 text-[10px]">（可多选）</span>
            </div>
            {loadingCategories ? (
              <div className="flex items-center gap-2 py-3 text-text-dim/40 text-xs">
                <Loader2 size={12} className="animate-spin" />
                加载分类中...
              </div>
            ) : allCategories.length === 0 ? (
              <div className="py-3 text-text-dim/30 text-xs">暂无可用分类</div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {allCategories.map(cat => {
                  const isSelected = selectedCategoryCodes.includes(cat.code)
                  return (
                    <button
                      key={cat.code}
                      type="button"
                      onClick={() => toggleCategory(cat.code)}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-all duration-200
                        ${isSelected
                          ? 'bg-primary/15 text-primary-light border border-primary/30'
                          : 'bg-surface-dark/40 text-text-dim/60 border border-white/[0.06] hover:border-primary/20 hover:text-text-dim'
                        }`}
                    >
                      {isSelected && <Check size={11} />}
                      {cat.name}
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          {/* Divider */}
          <div className="divider-gradient" />

          {/* ====== World fields ====== */}
          {selectedType === 'world' && (
            <div className="space-y-4">
              <div>
                <label className={labelCls}>时代背景</label>
                <input
                  type="text"
                  value={(fields.era as string) || ''}
                  onChange={(e) => setField('era', e.target.value)}
                  placeholder="例如：中世纪、近未来、古代..."
                  className={inputCls}
                />
              </div>
              <div>
                <label className={labelCls}>类型标签（逗号分隔）</label>
                <input
                  type="text"
                  value={(fields.genre as string) || ''}
                  onChange={(e) => setField('genre', e.target.value)}
                  placeholder="例如：奇幻, 冒险, 魔法"
                  className={inputCls}
                />
              </div>
              <div>
                <label className={labelCls}>世界设定描述</label>
                <textarea
                  value={(fields.setting_description as string) || ''}
                  onChange={(e) => setField('setting_description', e.target.value)}
                  placeholder="详细描述这个世界的历史、地理、文化..."
                  className={textareaCls}
                  rows={4}
                />
              </div>
              <div>
                <label className={labelCls}>世界规则（每行一条）</label>
                <textarea
                  value={(fields.rules as string) || ''}
                  onChange={(e) => setField('rules', e.target.value)}
                  placeholder={"例如：\n魔法需要消耗精神力\n贵族享有政治特权"}
                  className={textareaCls}
                  rows={4}
                />
              </div>
            </div>
          )}

          {/* ====== Character fields ====== */}
          {selectedType === 'character' && (
            <div className="space-y-4">
              {/* 角色头像上传 */}
              <div>
                <label className={labelCls}>角色头像（可选）</label>
                <div className="flex items-center gap-4">
                  <button
                    type="button"
                    onClick={() => charAvatarInputRef.current?.click()}
                    className="relative group w-20 h-20 rounded-full overflow-hidden shrink-0
                               bg-surface-dark/60 border border-white/[0.06]
                               hover:border-primary/30 transition-all duration-300
                               flex items-center justify-center"
                  >
                    {charAvatarPreview ? (
                      <img src={charAvatarPreview} alt="角色头像" className="w-full h-full object-contain"
                           onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />
                    ) : (
                      <Image size={24} className="text-text-dim/30" />
                    )}
                    <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100
                                    flex items-center justify-center transition-opacity duration-200">
                      {charAvatarUploading ? (
                        <Loader2 size={18} className="animate-spin text-white" />
                      ) : (
                        <Upload size={16} className="text-white" />
                      )}
                    </div>
                  </button>
                  <div className="flex-1">
                    <p className="text-text-dim/50 text-xs">
                      上传角色人设头像，支持 PNG / JPEG / WebP
                    </p>
                    <p className="text-text-dim/30 text-[10px] mt-1">
                      上传后将显示在角色面板和对话框中
                    </p>
                    {charAvatarPreview && (
                      <button
                        type="button"
                        onClick={() => {
                          setCharAvatarFile(null)
                          setCharAvatarPreview(null)
                        }}
                        className="text-xs text-text-dim/50 hover:text-red-400 transition-colors mt-1"
                      >
                        移除图片
                      </button>
                    )}
                  </div>
                </div>
                <input
                  ref={charAvatarInputRef}
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/gif"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (!file) return
                    // 打开裁剪器
                    setCropperSrc(file)
                    e.target.value = ''
                  }}
                />
                {/* 头像裁剪浮层 */}
                {cropperSrc && (
                  <ImageCropper
                    imageSrc={cropperSrc}
                    cropSize={200}
                    onConfirm={(croppedBlob) => {
                      const croppedFile = new File([croppedBlob], 'char-avatar.webp', { type: 'image/webp' })
                      setCharAvatarFile(croppedFile)
                      setCharAvatarPreview(URL.createObjectURL(croppedBlob))
                      setCropperSrc(null)
                    }}
                    onCancel={() => setCropperSrc(null)}
                  />
                )}
              </div>

              <div>
                <label className={labelCls}>角色全名</label>
                <input
                  type="text"
                  value={(fields.full_name as string) || ''}
                  onChange={(e) => setField('full_name', e.target.value)}
                  placeholder="角色的完整名字"
                  className={inputCls}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>性格原型</label>
                  <input
                    type="text"
                    value={(fields.archetype as string) || ''}
                    onChange={(e) => setField('archetype', e.target.value)}
                    placeholder="例如：傲娇、温柔学姐"
                    className={inputCls}
                  />
                </div>
                <div>
                  <label className={labelCls}>MBTI 类型</label>
                  <input
                    type="text"
                    value={(fields.mbti as string) || ''}
                    onChange={(e) => setField('mbti', e.target.value)}
                    placeholder="例如：INTJ, ENFP"
                    className={inputCls}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>喜好（逗号分隔）</label>
                  <input
                    type="text"
                    value={(fields.likes as string) || ''}
                    onChange={(e) => setField('likes', e.target.value)}
                    placeholder="例如：甜食, 读书, 花"
                    className={inputCls}
                  />
                </div>
                <div>
                  <label className={labelCls}>厌恶（逗号分隔）</label>
                  <input
                    type="text"
                    value={(fields.dislikes as string) || ''}
                    onChange={(e) => setField('dislikes', e.target.value)}
                    placeholder="例如：谎言, 噪音"
                    className={inputCls}
                  />
                </div>
              </div>
              <div>
                <label className={labelCls}>说话风格</label>
                <input
                  type="text"
                  value={(fields.speech_tone as string) || ''}
                  onChange={(e) => setField('speech_tone', e.target.value)}
                  placeholder="例如：温柔但偶尔毒舌、礼貌而疏离"
                  className={inputCls}
                />
              </div>
            </div>
          )}

          {/* ====== Scenario fields ====== */}
          {selectedType === 'scenario' && (
            <div className="space-y-4">
              <div>
                <label className={labelCls}>故事前提</label>
                <textarea
                  value={(fields.premise as string) || ''}
                  onChange={(e) => setField('premise', e.target.value)}
                  placeholder="描述故事的核心前提和背景..."
                  className={textareaCls}
                  rows={3}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>开场地点</label>
                  <input
                    type="text"
                    value={(fields.opening_location as string) || ''}
                    onChange={(e) => setField('opening_location', e.target.value)}
                    placeholder="例如：王城学院、海边小镇"
                    className={inputCls}
                  />
                </div>
                <div>
                  <label className={labelCls}>开场时间</label>
                  <input
                    type="text"
                    value={(fields.opening_time as string) || ''}
                    onChange={(e) => setField('opening_time', e.target.value)}
                    placeholder="例如：春日清晨、深夜"
                    className={inputCls}
                  />
                </div>
              </div>
              <div>
                <label className={labelCls}>剧情钩子（每行一条）</label>
                <textarea
                  value={(fields.plot_hooks as string) || ''}
                  onChange={(e) => setField('plot_hooks', e.target.value)}
                  placeholder={"例如：\n神秘的转学生隐藏了什么秘密\n学院地下室的封印开始松动"}
                  className={textareaCls}
                  rows={4}
                />
              </div>
              <div>
                <label className={labelCls}>预计章节数</label>
                <input
                  type="number"
                  value={(fields.estimated_chapters as number) || 5}
                  onChange={(e) => setField('estimated_chapters', Number(e.target.value))}
                  min={1}
                  max={50}
                  className={`${inputCls} max-w-[120px]`}
                />
              </div>
            </div>
          )}

          {/* Divider */}
          <div className="divider-gradient" />

          {/* Action buttons */}
          <div className="flex items-center justify-end gap-3">
            <button
              onClick={onCancel}
              className="px-5 py-2.5 rounded-xl text-sm text-text-dim/60 bg-surface-light/30
                         hover:bg-surface-light/50 transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleSave}
              disabled={!name.trim()}
              className={`flex items-center gap-1.5 px-6 py-2.5 rounded-xl text-sm font-medium transition-all duration-200
                ${name.trim()
                  ? 'btn-gradient text-white shadow-[0_4px_16px_rgba(168,130,255,0.25)]'
                  : 'bg-surface-light/20 text-text-dim/40 cursor-not-allowed border border-white/[0.04]'
                }`}
            >
              <Save size={13} /> {isEditing ? '保存修改' : '创建模板'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
