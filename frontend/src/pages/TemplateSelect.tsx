/**
 * TemplateSelect - 模板选择页
 * 织梦绮谭 - 精致二次元风格模板选择
 * 5 步向导：分类 → 世界观 → 剧本 → 角色 → 确认
 */

import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Sparkles, ChevronRight, ChevronLeft, AlertTriangle, RefreshCw, Check, Globe, BookMarked, Users, Tag, Plus } from 'lucide-react'
import { gameApi, categoryApi } from '@/services/api'
import { useGameStore } from '@/stores/gameStore'
import { useUIStore } from '@/stores/uiStore'
import { useAuthStore } from '@/stores/authStore'
import type { TemplateSummary, Category } from '@/types'

const stepLabels = ['选择分类', '选择世界观', '选择剧本', '选择角色', '确认开始']
const stepIcons = [Tag, Globe, BookMarked, Users, Sparkles]
const PAGE_SIZE = 6

/* 预置分类兜底数据——当后端不可用时仍可展示界面 */
const FALLBACK_CATEGORIES: Category[] = [
  { id: 1, code: 'xianxia', name: '仙侠奇缘', description: '御剑乘风，仙路漫漫', icon: 'Mountain', sort_order: 1 },
  { id: 2, code: 'fantasy', name: '西幻冒险', description: '剑与魔法的史诗旅途', icon: 'Swords', sort_order: 2 },
  { id: 3, code: 'court', name: '宫廷权谋', description: '明争暗斗，步步为营', icon: 'Crown', sort_order: 3 },
  { id: 4, code: 'romance', name: '现代恋爱', description: '都市里的怦然心动', icon: 'Moon', sort_order: 4 },
  { id: 5, code: 'campus', name: '校园青春', description: '重返青涩时光', icon: 'GraduationCap', sort_order: 5 },
  { id: 6, code: 'idol', name: '偶像养成', description: '舞台之上的闪耀人生', icon: 'Sparkles', sort_order: 6 },
  { id: 7, code: 'scifi', name: '赛博朋克', description: '霓虹灯下的数字灵魂', icon: 'Cpu', sort_order: 7 },
  { id: 8, code: 'space', name: '星际探索', description: '星辰大海的征途', icon: 'Rocket', sort_order: 8 },
  { id: 9, code: 'detective', name: '悬疑推理', description: '真相永远只有一个', icon: 'Search', sort_order: 9 },
  { id: 10, code: 'horror', name: '暗黑恐怖', description: '午夜时分的不寒而栗', icon: 'Skull', sort_order: 10 },
  { id: 11, code: 'isekai', name: '异世界', description: '穿越时空的命运交错', icon: 'Portal', sort_order: 11 },
  { id: 12, code: 'ghost', name: '灵异怪谈', description: '人与妖鬼的羁绊', icon: 'Ghost', sort_order: 12 },
  { id: 13, code: 'custom', name: '自定义&其他', description: '自由创作，无限可能', icon: 'Palette', sort_order: 99 },
]

export const TemplateSelect: React.FC = () => {
  const navigate = useNavigate()
  const setLoading = useUIStore((s) => s.setLoading)

  // 分类状态
  const [categories, setCategories] = useState<Category[]>([])
  const [selectedCategory, setSelectedCategory] = useState('')
  const [loadingCategories, setLoadingCategories] = useState(true)
  const [categoryError, setCategoryError] = useState('')

  const [worlds, setWorlds] = useState<TemplateSummary[]>([])
  const [scenarios, setScenarios] = useState<TemplateSummary[]>([])
  const [characters, setCharacters] = useState<TemplateSummary[]>([])

  // 分页状态
  const [worldPage, setWorldPage] = useState(1)
  const [worldTotalPages, setWorldTotalPages] = useState(1)
  const [scenarioPage, setScenarioPage] = useState(1)
  const [scenarioTotalPages, setScenarioTotalPages] = useState(1)
  const [charPage, setCharPage] = useState(1)
  const [charTotalPages, setCharTotalPages] = useState(1)

  const [loadingTemplates, setLoadingTemplates] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [retryKey, setRetryKey] = useState(0)

  const [selectedWorld, setSelectedWorld] = useState('')
  const [selectedScenario, setSelectedScenario] = useState('')
  const [selectedChars, setSelectedChars] = useState<string[]>([])
  const [playerName, setPlayerName] = useState('')

  const [step, setStep] = useState(0)

  // ---------- 加载分类列表 ----------
  useEffect(() => {
    let cancelled = false
    setLoadingCategories(true)
    setCategoryError('')
    categoryApi.list()
      .then((rawCats) => {
        if (cancelled) return
        // 如果后端返回空数组，使用兜底分类
        const cats = rawCats.length > 0 ? [...rawCats] : [...FALLBACK_CATEGORIES]
        // 把"自定义&其他"分类放到最前面
        cats.sort((a, b) => {
          if (a.code === 'custom') return -1
          if (b.code === 'custom') return 1
          return (a.sort_order ?? 0) - (b.sort_order ?? 0)
        })
        setCategories(cats)
        setLoadingCategories(false)
      })
      .catch((err) => {
        if (cancelled) return
        console.error('加载分类失败:', err)
        // 后端不可用时使用兜底分类（也把自定义放前面）
        const fallback = [...FALLBACK_CATEGORIES]
        fallback.sort((a, b) => {
          if (a.code === 'custom') return -1
          if (b.code === 'custom') return 1
          return (a.sort_order ?? 0) - (b.sort_order ?? 0)
        })
        setCategories(fallback)
        const errMsg = err instanceof Error ? err.message : String(err)
        setCategoryError(`后端请求失败: ${errMsg}。当前展示预置分类，启动后端后可查看完整内容。`)
        setLoadingCategories(false)
      })
    return () => { cancelled = true }
  }, [])

  // ---------- 加载模板（按分类过滤 + 分页） ----------
  useEffect(() => {
    if (!selectedCategory) return
    let cancelled = false
    setLoadingTemplates(true)
    setLoadError('')
    Promise.all([
      categoryApi.templates(selectedCategory, 'world', worldPage, PAGE_SIZE),
      categoryApi.templates(selectedCategory, 'scenario', scenarioPage, PAGE_SIZE),
      categoryApi.templates(selectedCategory, 'character', charPage, PAGE_SIZE),
    ]).then(([w, s, c]) => {
      if (cancelled) return
      setWorlds(w.items); setWorldTotalPages(w.total_pages)
      setScenarios(s.items); setScenarioTotalPages(s.total_pages)
      setCharacters(c.items); setCharTotalPages(c.total_pages)
      setLoadingTemplates(false)
    }).catch((err) => {
      if (cancelled) return
      console.error('加载模板失败:', err)
      setLoadError('无法连接后端服务，请先启动后端：cd backend && python run.py')
      setLoadingTemplates(false)
    })
    return () => { cancelled = true }
  }, [selectedCategory, worldPage, scenarioPage, charPage, retryKey])

  const toggleChar = (id: string) =>
    setSelectedChars(prev => prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id])

  // ---------- 选择分类 ----------
  const handleSelectCategory = (code: string) => {
    setSelectedCategory(code)
    // 重置选择
    setSelectedWorld('')
    setSelectedScenario('')
    setSelectedChars([])
    setWorldPage(1)
    setScenarioPage(1)
    setCharPage(1)
    setStep(1)
  }

  // ---------- 开始游戏 ----------
  const handleStart = async () => {
    if (!selectedWorld || !selectedScenario || selectedChars.length === 0) return
    // 检查登录状态
    if (!useAuthStore.getState().isAuthenticated) {
      window.dispatchEvent(new CustomEvent('auth-required'))
      return
    }
    setLoading(true, '正在编织梦境...')
    try {
      const res = await gameApi.start({
        world_template_id: selectedWorld,
        scenario_template_id: selectedScenario,
        player_name: playerName || '主角',
        player_data: {},
        character_template_ids: selectedChars,
      })
      // 先重置游戏状态，清除上一局的残留数据
      const store = useGameStore.getState()
      store.reset()
      // 设置新会话
      store.setSession(res.session_id)
      store.addMessages([
        { id: '', type: 'narration', text: res.opening_narration },
        ...res.opening_dialogues.map(d => ({
          id: '', type: 'dialogue' as const,
          speaker: d.speaker, text: d.text, emotion: d.emotion, action: d.action,
        })),
      ])
      store.setChoices(res.choices)
      store.setScene(res.scene_state.location || '', res.scene_state)
      // 使用后端返回的角色数据（名字初始为 ???）
      if (res.updated_characters?.length) {
        store.setCharacters(res.updated_characters)
      }
      if (res.progress) store.setProgress(res.progress)
      navigate('/game')
    } catch (err) {
      console.error('启动游戏失败:', err)
      alert('启动失败: ' + (err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  // ---------- 模板卡片 ----------
  const renderCard = (item: TemplateSummary, isSelected: boolean, onClick: () => void) => (
    <button
      key={item.template_id}
      onClick={onClick}
      className={`w-full text-left p-4 rounded-2xl border transition-all duration-300
        ${isSelected
          ? 'card-selected glass-panel'
          : 'glass-panel hover:border-primary/20'
        }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className={`font-medium text-sm truncate ${isSelected ? 'text-primary-light' : 'text-text-bright'}`}>
              {item.name}
            </h3>
            {item.is_preset && (
              <span className="shrink-0 flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full
                               bg-accent/10 text-accent-light/80">
                <Sparkles size={10} /> 预设
              </span>
            )}
          </div>
          <p className="text-text-dim/70 text-xs mt-1.5 line-clamp-2 leading-relaxed">{item.description}</p>
        </div>
        {/* 选中指示器 */}
        <div className={`w-5 h-5 rounded-full shrink-0 flex items-center justify-center transition-all duration-300
          ${isSelected
            ? 'bg-primary shadow-[0_0_12px_rgba(168,130,255,0.4)]'
            : 'border border-white/10'
          }`}>
          {isSelected && <Check size={12} className="text-white" />}
        </div>
      </div>
      {item.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {item.tags.map(tag => (
            <span key={tag} className="text-[10px] px-2 py-0.5 rounded-full
                                       bg-surface-dark/80 text-text-dim/60 border border-white/[0.03]">
              {tag}
            </span>
          ))}
        </div>
      )}
    </button>
  )

  // ---------- 分类卡片 ----------
  const renderCategoryCard = (cat: Category, isSelected: boolean) => (
    <button
      key={cat.code}
      onClick={() => handleSelectCategory(cat.code)}
      className={`group w-full text-left p-5 rounded-2xl border transition-all duration-300
        ${isSelected
          ? 'card-selected glass-panel border-primary/40 shadow-[0_0_24px_rgba(168,130,255,0.15)]'
          : 'glass-panel hover:border-primary/30 hover:shadow-[0_4px_20px_rgba(168,130,255,0.08)] hover:-translate-y-0.5'
        }`}
    >
      <div className="flex items-center gap-4">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 transition-all duration-300
          ${isSelected
            ? 'bg-primary/25 shadow-[0_0_16px_rgba(168,130,255,0.2)]'
            : 'bg-surface-light/10 group-hover:bg-primary/15 group-hover:shadow-[0_0_12px_rgba(168,130,255,0.1)]'}`}>
          <span className="text-2xl">{cat.icon === 'Mountain' ? '⛰️' : cat.icon === 'Swords' ? '⚔️' : cat.icon === 'Crown' ? '👑' : cat.icon === 'Moon' ? '🌙' : cat.icon === 'GraduationCap' ? '🎓' : cat.icon === 'Sparkles' ? '✨' : cat.icon === 'Cpu' ? '🤖' : cat.icon === 'Rocket' ? '🚀' : cat.icon === 'Search' ? '🔍' : cat.icon === 'Skull' ? '💀' : cat.icon === 'Portal' ? '🌀' : cat.icon === 'Ghost' ? '👻' : cat.icon === 'Palette' ? '🎨' : '📖'}</span>
        </div>
        <div className="min-w-0 flex-1">
          <h3 className={`font-semibold text-[15px] transition-colors duration-200
            ${isSelected ? 'text-primary-light' : 'text-text-bright group-hover:text-white'}`}>
            {cat.name}
          </h3>
          <p className={`text-xs mt-1 line-clamp-1 transition-colors duration-200
            ${isSelected ? 'text-primary-light/60' : 'text-text-dim/60 group-hover:text-text-dim/80'}`}>
            {cat.description}
          </p>
        </div>
        <ChevronRight size={16} className={`shrink-0 transition-all duration-200
          ${isSelected ? 'text-primary-light' : 'text-text-dim/20 group-hover:text-primary-light/60 group-hover:translate-x-0.5'}`} />
      </div>
    </button>
  )

  // ---------- 分页控件 ----------
  const PaginationControls = ({ page, totalPages, onPageChange }: { page: number; totalPages: number; onPageChange: (p: number) => void }) => {
    if (totalPages <= 1) return null
    return (
      <div className="flex items-center justify-center gap-3 mt-4">
        <button
          onClick={() => onPageChange(Math.max(1, page - 1))}
          disabled={page <= 1}
          className="w-8 h-8 rounded-lg flex items-center justify-center bg-surface-light/40
                     hover:bg-surface-light transition-colors disabled:opacity-20 disabled:cursor-not-allowed"
        >
          <ChevronLeft size={14} className="text-text-dim" />
        </button>
        <div className="flex items-center gap-1.5">
          {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
            <button
              key={p}
              onClick={() => onPageChange(p)}
              className={`w-7 h-7 rounded-lg text-xs transition-all duration-200
                ${p === page
                  ? 'bg-primary/20 text-primary-light font-medium'
                  : 'text-text-dim/50 hover:text-text-dim hover:bg-surface-light/30'
                }`}
            >
              {p}
            </button>
          ))}
        </div>
        <button
          onClick={() => onPageChange(Math.min(totalPages, page + 1))}
          disabled={page >= totalPages}
          className="w-8 h-8 rounded-lg flex items-center justify-center bg-surface-light/40
                     hover:bg-surface-light transition-colors disabled:opacity-20 disabled:cursor-not-allowed"
        >
          <ChevronRight size={14} className="text-text-dim" />
        </button>
      </div>
    )
  }

  const canNext = (step === 0 && selectedCategory) ||
                  (step === 1 && selectedWorld) ||
                  (step === 2 && selectedScenario) ||
                  (step === 3 && selectedChars.length > 0)

  // ---------- 创建模板按钮 ----------
  const CreateTemplateButton = () => (
    <button
      onClick={() => navigate('/templates')}
      className="w-full text-left p-4 rounded-2xl border border-dashed border-primary/20
                 hover:border-primary/40 hover:bg-primary/[0.04] transition-all duration-300
                 flex items-center gap-3 group"
    >
      <div className="w-8 h-8 rounded-xl bg-primary/10 flex items-center justify-center shrink-0
                      group-hover:bg-primary/20 transition-colors">
        <Plus size={16} className="text-primary-light" />
      </div>
      <div>
        <p className="text-primary-light text-sm font-medium">创建自定义模板</p>
        <p className="text-text-dim/50 text-[11px] mt-0.5">创建后自动返回选择页面</p>
      </div>
    </button>
  )

  const handleBack = () => {
    if (step === 0) {
      navigate('/')
    } else {
      setStep(step - 1)
    }
  }

  return (
    <div className="min-h-screen bg-surface-dark flex flex-col">
      {/* ====== 顶部导航 + 步骤指示器 ====== */}
      <header className="glass-panel-strong mx-3 mt-3 p-4" style={{ borderRadius: '16px 16px 16px 16px' }}>
        <div className="flex items-center gap-3 mb-4">
          <button
            onClick={handleBack}
            className="w-8 h-8 rounded-lg flex items-center justify-center
                       bg-surface-light/50 hover:bg-surface-light transition-colors"
          >
            <ArrowLeft size={16} className="text-text-dim" />
          </button>
          <div className="flex-1">
            <h1 className="text-text-bright font-bold text-base">{stepLabels[step]}</h1>
            <p className="text-text-dim/50 text-[11px] mt-0.5">织梦绮谭 · 新游戏{selectedCategory ? ` · ${categories.find(c => c.code === selectedCategory)?.name || ''}` : ''}</p>
          </div>
        </div>

        {/* 步骤进度条 */}
        <div className="flex items-center gap-1.5">
          {stepLabels.map((label, i) => {
            const StepIcon = stepIcons[i]
            const isActive = i === step
            const isDone = i < step
            return (
              <React.Fragment key={label}>
                <button
                  key={label}
                  onClick={() => isDone && setStep(i)}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs transition-all duration-300
                    ${isActive
                      ? 'bg-primary/15 text-primary-light'
                      : isDone
                        ? 'text-primary-light/60 hover:text-primary-light cursor-pointer'
                        : 'text-text-dim/30'
                    }`}
                >
                  {isDone ? <Check size={12} /> : <StepIcon size={12} />}
                  <span className="hidden sm:inline">{label}</span>
                </button>
                {i < stepLabels.length - 1 && (
                  <div className={`flex-1 h-px transition-colors duration-500
                    ${isDone ? 'bg-primary/30' : 'bg-white/[0.04]'}`} />
                )}
              </React.Fragment>
            )
          })}
        </div>
      </header>

      {/* ====== 内容区域 ====== */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* 加载分类 */}
        {step === 0 && loadingCategories && (
          <div className="flex flex-col items-center justify-center h-64 text-text-dim">
            <div className="w-10 h-10 rounded-full border-2 border-primary/20 border-t-primary animate-spin mb-4" />
            <p className="text-sm">正在加载分类...</p>
          </div>
        )}

        {/* 加载模板 */}
        {step > 0 && loadingTemplates && (
          <div className="flex flex-col items-center justify-center h-64 text-text-dim">
            <div className="w-10 h-10 rounded-full border-2 border-primary/20 border-t-primary animate-spin mb-4" />
            <p className="text-sm">正在加载模板...</p>
          </div>
        )}

        {/* 错误（仅 step > 0 时展示模板加载错误） */}
        {step > 0 && !loadingTemplates && loadError && (
          <div className="flex flex-col items-center justify-center h-64">
            <div className="w-16 h-16 rounded-2xl bg-accent/10 flex items-center justify-center mb-4">
              <AlertTriangle size={28} className="text-accent" />
            </div>
            <p className="text-text-bright text-lg mb-2 font-medium">无法加载模板</p>
            <p className="text-text-dim/60 text-sm text-center max-w-md mb-6 leading-relaxed">{loadError}</p>
            <button onClick={() => setRetryKey(k => k + 1)}
              className="btn-gradient flex items-center gap-2 px-6 py-3 text-white rounded-xl font-medium text-sm">
              <RefreshCw size={14} /> 重试
            </button>
          </div>
        )}

        {/* 内容 */}
        {!loadingCategories && (step === 0 || !loadingTemplates) && !(step > 0 && loadError) && (<>
          {/* Step 0: 选择分类 */}
          {step === 0 && (
            <div className="max-w-2xl mx-auto animate-fade-in">
              {/* 后端连接警告 */}
              {categoryError && (
                <div className="glass-panel p-4 mb-4 flex items-start gap-3 border-amber-500/20 bg-amber-500/[0.04]">
                  <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center shrink-0 mt-0.5">
                    <AlertTriangle size={16} className="text-amber-400" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-amber-200/80 text-sm font-medium">后端服务未连接</p>
                    <p className="text-text-dim/60 text-xs mt-1 leading-relaxed">{categoryError}</p>
                  </div>
                </div>
              )}

              {/* 提示栏 */}
              <div className="glass-panel p-3 mb-5 flex items-center gap-2.5 text-sm">
                <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                  <Tag size={13} className="text-primary-light" />
                </div>
                <span className="text-text-dim/80">选择一个感兴趣的题材，开始你的故事冒险</span>
              </div>

              {/* 分类网格 */}
              {categories.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16">
                  <div className="w-16 h-16 rounded-2xl bg-surface-light/5 flex items-center justify-center mb-4">
                    <Tag size={28} className="text-text-dim/20" />
                  </div>
                  <p className="text-text-dim/40 text-sm">暂无可用分类</p>
                  <p className="text-text-dim/30 text-xs mt-1">请检查后端服务是否已启动</p>
                </div>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2">
                  {categories.map(cat => renderCategoryCard(cat, selectedCategory === cat.code))}
                </div>
              )}
            </div>
          )}

          {/* Step 1: 选择世界观 */}
          {step === 1 && (
            <div className="max-w-2xl mx-auto animate-fade-in">
              {worlds.length === 0 ? (
                <div className="space-y-3">
                  <div className="text-center py-8 text-text-dim/50">
                    <Globe size={32} className="mx-auto mb-3 opacity-40" />
                    <p className="text-sm">该分类下暂无世界观模板</p>
                  </div>
                  <CreateTemplateButton />
                </div>
              ) : (
                <div className="grid gap-3">
                  <CreateTemplateButton />
                  {worlds.map(w => renderCard(w, selectedWorld === w.template_id, () => setSelectedWorld(w.template_id)))}
                </div>
              )}
              <PaginationControls page={worldPage} totalPages={worldTotalPages} onPageChange={setWorldPage} />
            </div>
          )}

          {/* Step 2: 选择剧本 */}
          {step === 2 && (
            <div className="max-w-2xl mx-auto animate-fade-in">
              {scenarios.length === 0 ? (
                <div className="space-y-3">
                  <div className="text-center py-8 text-text-dim/50">
                    <BookMarked size={32} className="mx-auto mb-3 opacity-40" />
                    <p className="text-sm">该分类下暂无剧本模板</p>
                  </div>
                  <CreateTemplateButton />
                </div>
              ) : (
                <div className="grid gap-3">
                  <CreateTemplateButton />
                  {scenarios.map(s => renderCard(s, selectedScenario === s.template_id, () => setSelectedScenario(s.template_id)))}
                </div>
              )}
              <PaginationControls page={scenarioPage} totalPages={scenarioTotalPages} onPageChange={setScenarioPage} />
            </div>
          )}

          {/* Step 3: 选择角色 */}
          {step === 3 && (
            <div className="max-w-2xl mx-auto space-y-4 animate-fade-in">
              <div className="glass-panel p-3 flex items-center gap-2 text-sm text-text-dim/70">
                <Users size={14} className="text-primary-light/60" />
                <span>选择至少一个角色开始冒险（可多选，已选 <span className="text-primary-light">{selectedChars.length}</span> 个）</span>
              </div>
              {characters.length === 0 ? (
                <div className="space-y-3">
                  <div className="text-center py-8 text-text-dim/50">
                    <Users size={32} className="mx-auto mb-3 opacity-40" />
                    <p className="text-sm">该分类下暂无角色模板</p>
                  </div>
                  <CreateTemplateButton />
                </div>
              ) : (
                <div className="grid gap-3">
                  <CreateTemplateButton />
                  {characters.map(c => renderCard(c, selectedChars.includes(c.template_id), () => toggleChar(c.template_id)))}
                </div>
              )}
              <PaginationControls page={charPage} totalPages={charTotalPages} onPageChange={setCharPage} />
            </div>
          )}

          {/* Step 4: 确认 */}
          {step === 4 && (
            <div className="max-w-md mx-auto space-y-6 animate-fade-in-scale">
              {/* 角色名 */}
              <div className="glass-panel p-5">
                <label className="text-text-dim/70 text-xs block mb-3 tracking-wide">你的角色名</label>
                <input
                  type="text"
                  value={playerName}
                  onChange={e => setPlayerName(e.target.value)}
                  placeholder="主角"
                  className="w-full bg-surface-dark/60 text-text-bright border border-white/[0.06]
                             focus:border-primary/40 rounded-xl px-4 py-3 outline-none transition-colors
                             placeholder:text-text-dim/30"
                />
              </div>

              {/* 选择概览 */}
              <div className="glass-panel p-5 space-y-4">
                <h3 className="text-text-bright font-medium text-sm">冒险概览</h3>
                <div className="divider-gradient" />
                <div className="space-y-3 text-sm">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center shrink-0">
                      <Tag size={14} className="text-accent-light" />
                    </div>
                    <div>
                      <p className="text-text-dim/50 text-[10px] uppercase tracking-wider">分类</p>
                      <p className="text-text-bright">{categories.find(c => c.code === selectedCategory)?.name}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                      <Globe size={14} className="text-primary-light" />
                    </div>
                    <div>
                      <p className="text-text-dim/50 text-[10px] uppercase tracking-wider">世界观</p>
                      <p className="text-text-bright">{worlds.find(w => w.template_id === selectedWorld)?.name}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                      <BookMarked size={14} className="text-primary-light" />
                    </div>
                    <div>
                      <p className="text-text-dim/50 text-[10px] uppercase tracking-wider">剧本</p>
                      <p className="text-text-bright">{scenarios.find(s => s.template_id === selectedScenario)?.name}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center shrink-0">
                      <Users size={14} className="text-accent-light" />
                    </div>
                    <div>
                      <p className="text-text-dim/50 text-[10px] uppercase tracking-wider">角色</p>
                      <p className="text-text-bright">
                        {selectedChars.map(id => characters.find(c => c.template_id === id)?.name).join('、')}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </>)}
      </div>

      {/* ====== 底部按钮 ====== */}
      <div className="p-4 flex justify-end">
        {step < 4 ? (
          <button
            onClick={() => setStep(step + 1)}
            disabled={!canNext}
            className={`flex items-center gap-2 px-7 py-3 rounded-xl font-medium text-sm transition-all duration-300
              ${canNext
                ? 'btn-gradient text-white shadow-[0_4px_16px_rgba(168,130,255,0.25)]'
                : 'bg-surface-light/20 text-text-dim/40 cursor-not-allowed border border-white/[0.04]'
              }`}
          >
            下一步 <ChevronRight size={15} />
          </button>
        ) : (
          <button
            onClick={handleStart}
            className="btn-accent flex items-center gap-2 px-8 py-3 text-white
                       rounded-xl font-medium text-sm shadow-[0_4px_16px_rgba(244,114,182,0.25)]"
          >
            <Sparkles size={15} /> 开始冒险
          </button>
        )}
      </div>
    </div>
  )
}
