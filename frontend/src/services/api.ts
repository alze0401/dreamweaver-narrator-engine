/**
 * 织梦绮谭 - API 服务层
 * 封装所有与后端的 HTTP 通信
 */

import type {
  TemplateSummary,
  TemplateDetail,
  GameStartRequest,
  GameStartResponse,
  GameState,
  DialogueAdvanceResponse,
  CharacterSummary,
  CharacterDetail,
  SaveSlot,
  Category,
} from '@/types'

const BASE = '/api'

// ========== 通用请求函数 ==========

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `API Error ${res.status}`)
  }
  return res.json()
}

// ========== 模板 API ==========

export const templateApi = {
  /** 获取模板列表，可按类型过滤 + 分页 */
  list: (type?: string, page = 1, pageSize = 10) =>
    request<{
      items: TemplateSummary[]
      total: number
      page: number
      page_size: number
      total_pages: number
    }>(`/templates${type ? `?template_type=${type}&page=${page}&page_size=${pageSize}` : `?page=${page}&page_size=${pageSize}`}`),

  /** 获取模板详情 */
  get: (id: string) =>
    request<TemplateDetail>(`/templates/${id}`),

  /** 创建自定义模板 */
  create: (data: {
    template_type: string
    name: string
    description?: string
    data: Record<string, unknown>
  }) => request<{ success: boolean; data: { template_id: string } }>('/templates', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  /** 克隆模板 */
  clone: (id: string, newName?: string) =>
    request<{ success: boolean; data: { template_id: string } }>(
      `/templates/${id}/clone${newName ? `?new_name=${encodeURIComponent(newName)}` : ''}`,
      { method: 'POST' },
    ),
}

// ========== 游戏流程 API ==========

export const gameApi = {
  /** 开始新游戏 */
  start: (data: GameStartRequest) =>
    request<GameStartResponse>('/game/start', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  /** 获取游戏状态 */
  getState: (sessionId: string) =>
    request<GameState>(`/game/${sessionId}/state`),

  /** 推进剧情 */
  advance: (sessionId: string, inputType: 'choice' | 'free', content: string) =>
    request<DialogueAdvanceResponse>(`/game/${sessionId}/advance`, {
      method: 'POST',
      body: JSON.stringify({ input_type: inputType, content }),
    }),
}

// ========== 角色 API ==========

export const characterApi = {
  /** 获取角色列表 */
  list: (sessionId: string) =>
    request<CharacterSummary[]>(`/game/${sessionId}/characters`),

  /** 获取角色详情 */
  get: (sessionId: string, characterId: string) =>
    request<CharacterDetail>(`/game/${sessionId}/characters/${characterId}`),
}

// ========== 存档 API ==========

export const saveApi = {
  /** 获取所有存档 */
  list: () => request<SaveSlot[]>('/saves'),

  /** 创建存档 */
  create: (slotNumber: number, sessionId: string, title?: string) =>
    request<SaveSlot>('/saves', {
      method: 'POST',
      body: JSON.stringify({ slot_number: slotNumber, session_id: sessionId, title }),
    }),

  /** 自动存档（slot 101-103 循环覆盖） */
  autoSave: (sessionId: string) =>
    request<SaveSlot>(`/saves/auto?session_id=${sessionId}`, {
      method: 'POST',
    }),

  /** 加载存档 */
  load: (saveId: string) =>
    request<{ success: boolean; data: { session_id: string } }>('/saves/load', {
      method: 'POST',
      body: JSON.stringify({ save_id: saveId }),
    }),

  /** 删除存档 */
  delete: (saveId: string) =>
    request<{ success: boolean }>(`/saves/${saveId}`, { method: 'DELETE' }),
}

// ========== 对话历史 API ==========

export const dialogueApi = {
  /** 获取对话历史 */
  history: (sessionId: string, limit = 50, offset = 0) =>
    request<{
      total: number
      dialogues: import('@/types').DialogueHistoryEntry[]
    }>(`/dialogue/${sessionId}/history?limit=${limit}&offset=${offset}`),

  /** 获取记忆日志 */
  memories: (sessionId: string, minImportance = 6) =>
    request<{ total: number; memories: unknown[] }>(
      `/dialogue/${sessionId}/memories?min_importance=${minImportance}`,
    ),
}

// ========== 分类 API ==========

export const categoryApi = {
  /** 获取所有分类列表 */
  list: () =>
    request<Category[]>('/categories'),

  /** 获取指定分类下的模板列表 */
  templates: (categoryCode: string, type?: string, page = 1, pageSize = 10) =>
    request<{
      items: TemplateSummary[]
      total: number
      page: number
      page_size: number
      total_pages: number
    }>(`/categories/${categoryCode}/templates${type ? `?template_type=${type}&page=${page}&page_size=${pageSize}` : `?page=${page}&page_size=${pageSize}`}`),
}
