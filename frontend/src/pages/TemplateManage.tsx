/**
 * TemplateManage - 模板管理页
 * 织梦绮谭 - 浏览、创建、编辑、删除自定义模板
 */

import React, { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Home, Plus, Pencil, Trash2, Globe, BookMarked, Users, Sparkles, X } from 'lucide-react'
import { templateApi } from '@/services/api'
import { useUIStore } from '@/stores/uiStore'
import { useAuthStore } from '@/stores/authStore'
import type { TemplateSummary } from '@/types'
import { TemplateForm } from '@/components/TemplateForm'

const TABS = [
  { key: 'world', label: '世界观', icon: Globe },
  { key: 'character', label: '角色', icon: Users },
  { key: 'scenario', label: '剧本', icon: BookMarked },
] as const

type TabKey = (typeof TABS)[number]['key']

export const TemplateManage: React.FC = () => {
  const navigate = useNavigate()
  const setLoading = useUIStore((s) => s.setLoading)
  const { user } = useAuthStore()

  const [activeTab, setActiveTab] = useState<TabKey>('world')
  const [templates, setTemplates] = useState<TemplateSummary[]>([])
  const [loading, setLoadingState] = useState(true)
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)

  // 表单状态
  const [showForm, setShowForm] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<TemplateSummary | null>(null)

  // 加载模板列表
  const loadTemplates = useCallback(() => {
    setLoadingState(true)
    templateApi
      .list(activeTab, 1, 50)
      .then((res) => {
        // 只显示当前用户的自定义模板（非预设）
        const custom = res.items.filter(
          (t) => !t.is_preset
        )
        setTemplates(custom)
      })
      .catch((err) => console.error('加载模板失败:', err))
      .finally(() => setLoadingState(false))
  }, [activeTab])

  useEffect(() => {
    loadTemplates()
  }, [loadTemplates])

  // 删除模板
  const handleDelete = async (id: string) => {
    try {
      await templateApi.delete(id)
      setConfirmDelete(null)
      loadTemplates()
    } catch (err) {
      console.error('删除模板失败:', err)
      alert('删除失败: ' + (err as Error).message)
    }
  }

  // 打开编辑表单
  const handleEdit = async (tpl: TemplateSummary) => {
    setLoading(true, '加载模板详情...')
    try {
      const detail = await templateApi.get(tpl.template_id)
      setEditingTemplate({
        ...tpl,
        ...detail,
        categories: detail.categories || [],
      } as TemplateSummary & { data: Record<string, unknown>; categories?: Array<{ code: string; name: string }> })
      setShowForm(true)
    } catch (err) {
      console.error('加载模板详情失败:', err)
      alert('加载失败: ' + (err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  // 打开新建表单
  const handleCreate = () => {
    setEditingTemplate(null)
    setShowForm(true)
  }

  // 表单保存后
  const handleFormSaved = () => {
    setShowForm(false)
    setEditingTemplate(null)
    loadTemplates()
  }

  // 格式化日期
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return ''
    try {
      const d = new Date(dateStr)
      return `${d.getFullYear()}/${(d.getMonth() + 1).toString().padStart(2, '0')}/${d.getDate().toString().padStart(2, '0')}`
    } catch {
      return ''
    }
  }

  const typeIcon = (type: string) => {
    if (type === 'world') return <Globe size={14} className="text-primary-light" />
    if (type === 'character') return <Users size={14} className="text-accent-light" />
    return <BookMarked size={14} className="text-emerald-400" />
  }

  return (
    <div className="min-h-screen bg-surface-dark flex flex-col">
      {/* ====== 头部 ====== */}
      <header className="glass-panel-strong mx-3 mt-3 p-4 flex items-center gap-3">
        <button
          onClick={() => navigate(-1)}
          className="w-8 h-8 rounded-lg flex items-center justify-center
                     bg-surface-light/50 hover:bg-surface-light transition-colors"
          title="返回上一页"
        >
          <ArrowLeft size={16} className="text-text-dim" />
        </button>
        <button
          onClick={() => navigate('/')}
          className="w-8 h-8 rounded-lg flex items-center justify-center
                     bg-surface-light/50 hover:bg-surface-light transition-colors"
          title="返回首页"
        >
          <Home size={16} className="text-text-dim" />
        </button>
        <div className="flex-1">
          <h1 className="text-text-bright font-bold text-base">模板管理</h1>
          <p className="text-text-dim/50 text-[11px] mt-0.5">
            织梦绮谭 · {user ? `${user.display_name || user.username} 的自定义模板` : '自定义模板'}
          </p>
        </div>
        <button
          onClick={handleCreate}
          className="btn-gradient flex items-center gap-1.5 px-4 py-2 text-white text-xs font-medium rounded-xl"
        >
          <Plus size={13} /> 新建模板
        </button>
      </header>

      {/* ====== Tab 栏 ====== */}
      <div className="mx-3 mt-3 flex gap-2">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-medium transition-all duration-200
              ${
                activeTab === key
                  ? 'bg-primary/15 text-primary-light border border-primary/25'
                  : 'glass-panel text-text-dim/60 hover:text-text-dim hover:bg-surface-light/30'
              }`}
          >
            <Icon size={13} />
            {label}
          </button>
        ))}
      </div>

      {/* ====== 模板列表 ====== */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="flex items-center justify-center h-64 text-text-dim">
            <div className="w-8 h-8 rounded-full border-2 border-primary/20 border-t-primary animate-spin" />
          </div>
        ) : templates.length === 0 ? (
          /* 空状态 */
          <div className="flex flex-col items-center justify-center h-64">
            <div className="w-16 h-16 rounded-2xl bg-surface-light/5 flex items-center justify-center mb-4">
              <Sparkles size={28} className="text-text-dim/20" />
            </div>
            <p className="text-text-dim/50 text-sm mb-1">还没有自定义模板</p>
            <p className="text-text-dim/30 text-xs mb-5">点击下方按钮创建你的第一个模板</p>
            <button
              onClick={handleCreate}
              className="btn-gradient flex items-center gap-1.5 px-5 py-2.5 text-white text-xs font-medium rounded-xl"
            >
              <Plus size={13} /> 创建模板
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-w-5xl mx-auto">
            {templates.map((tpl) => {
              const isConfirming = confirmDelete === tpl.template_id
              return (
                <div key={tpl.template_id} className="glass-panel p-4 flex flex-col min-h-[130px]">
                  {/* 卡片头 */}
                  <div className="flex items-start gap-2 mb-1">
                    <div className="w-7 h-7 rounded-lg bg-surface-light/10 flex items-center justify-center shrink-0 mt-0.5">
                      {typeIcon(tpl.template_type)}
                    </div>
                    <div className="min-w-0 flex-1">
                      <h3 className="text-text-bright text-sm font-medium truncate">{tpl.name}</h3>
                      {tpl.description && (
                        <p className="text-text-dim/50 text-xs mt-0.5 line-clamp-2 leading-relaxed">
                          {tpl.description}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex-1" />

                  {/* 日期 */}
                  <div className="flex items-center justify-between mt-3">
                    <span className="text-text-dim/30 text-[10px]">
                      {tpl.tags.length > 0 && (
                        <span className="mr-2">{tpl.tags.join(', ')}</span>
                      )}
                    </span>
                  </div>

                  {/* 操作按钮 */}
                  {isConfirming ? (
                    <div className="flex items-center gap-2 mt-2">
                      <span className="text-accent text-xs flex-1">确定删除？</span>
                      <button
                        onClick={() => handleDelete(tpl.template_id)}
                        className="text-[11px] px-3 py-1 rounded-lg bg-accent/15 text-accent hover:bg-accent/25 transition-colors"
                      >
                        确定
                      </button>
                      <button
                        onClick={() => setConfirmDelete(null)}
                        className="text-[11px] px-3 py-1 rounded-lg bg-surface-light/50 text-text-dim hover:bg-surface-light transition-colors"
                      >
                        取消
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 mt-2">
                      <button
                        onClick={() => handleEdit(tpl)}
                        className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg
                                   btn-gradient text-white text-xs font-medium"
                      >
                        <Pencil size={12} /> 编辑
                      </button>
                      <button
                        onClick={() => setConfirmDelete(tpl.template_id)}
                        className="flex items-center justify-center px-2.5 py-2 rounded-lg
                                   hover:bg-accent/10 text-text-dim/40 hover:text-accent transition-colors"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* ====== 表单 Modal ====== */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto glass-panel-strong rounded-2xl">
            {/* Modal 头部 */}
            <div className="sticky top-0 z-10 flex items-center justify-between p-5 pb-4 bg-surface-dark/95 backdrop-blur-sm border-b border-white/[0.04]">
              <div>
                <h2 className="text-text-bright font-bold text-base">
                  {editingTemplate ? '编辑模板' : '新建模板'}
                </h2>
                <p className="text-text-dim/50 text-[11px] mt-0.5">
                  {editingTemplate ? `正在编辑: ${editingTemplate.name}` : '填写模板信息，或使用 AI 自动生成'}
                </p>
              </div>
              <button
                onClick={() => { setShowForm(false); setEditingTemplate(null) }}
                className="w-8 h-8 rounded-lg flex items-center justify-center
                           bg-surface-light/50 hover:bg-surface-light transition-colors"
              >
                <X size={14} className="text-text-dim" />
              </button>
            </div>

            {/* 表单内容 */}
            <div className="p-5">
              <TemplateForm
                initialType={editingTemplate?.template_type as TabKey | undefined}
                initialData={editingTemplate as (TemplateSummary & { data: Record<string, unknown>; categories?: Array<{ code: string; name: string }> }) | null}
                onSaved={handleFormSaved}
                onCancel={() => { setShowForm(false); setEditingTemplate(null) }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
