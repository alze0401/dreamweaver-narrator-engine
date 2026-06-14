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
  AuthResponse,
  UploadResponse,
  GameSettings,
  GameSettingsUpdate,
} from '@/types'

const BASE = '/api'

// ========== 通用请求函数 ==========

function getAuthHeaders(): Record<string, string> {
  try {
    const token = localStorage.getItem('dw_token')
    if (token) return { Authorization: `Bearer ${token}` }
  } catch {}
  return {}
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const mergedHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...getAuthHeaders(),
    ...(options?.headers as Record<string, string> || {}),
  }
  const { headers: _h, ...restOptions } = options || {}
  const res = await fetch(`${BASE}${url}`, {
    headers: mergedHeaders,
    ...restOptions,
  })
  if (res.status === 401) {
    try { localStorage.removeItem('dw_token') } catch {}
    try { localStorage.removeItem('dw_user') } catch {}
    window.dispatchEvent(new CustomEvent('auth-required'))
    throw new Error('NEED_LOGIN')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `API Error ${res.status}`)
  }
  return res.json()
}

// ========== 认证 API ==========

export const authApi = {
  login: (username: string, password: string) =>
    request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  register: (username: string, password: string, display_name?: string) =>
    request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, password, display_name: display_name || username }),
    }),

  me: () => request<{ id: string; username: string; display_name: string; role: string }>('/auth/me'),

  changePassword: (oldPassword: string, newPassword: string) =>
    request<{ success: boolean; message: string }>('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    }),

  updateProfile: (data: { display_name?: string }) =>
    request<{ id: string; username: string; display_name: string; role: string; avatar_url?: string | null }>('/auth/profile', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
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
    category_codes?: string[]
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

  /** 更新自定义模板 */
  update: (id: string, data: { name?: string; description?: string; data?: Record<string, unknown>; category_codes?: string[] }) =>
    request<{ success: boolean; data: { template_id: string } }>(`/templates/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  /** 删除自定义模板 */
  delete: (id: string) =>
    request<{ success: boolean; message: string }>(`/templates/${id}`, {
      method: 'DELETE',
    }),

  /** AI 生成模板数据 */
  aiGenerate: (templateType: string, userPrompt: string) =>
    request<{ success: boolean; data: Record<string, unknown> }>('/templates/ai-generate', {
      method: 'POST',
      body: JSON.stringify({ template_type: templateType, user_prompt: userPrompt }),
    }),
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
    request<SaveSlot>('/saves/auto', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    }),

  /** 加载存档 */
  load: (saveId: string) =>
    request<{
      success: boolean
      data: {
        session_id: string
        chapter: number
        current_scene: string
        world_state: Record<string, unknown>
        characters_state: Array<Record<string, unknown>>
        recent_dialogues: Array<{
          turn_number: number
          speaker: string
          content: string
          emotion: string | null
          action: string | null
        }>
      }
    }>('/saves/load', {
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

// ========== 文件上传 API ==========

/** multipart/form-data 上传辅助函数 */
async function uploadFile<T>(url: string, formData: FormData): Promise<T> {
  const headers: Record<string, string> = { ...getAuthHeaders() }
  const res = await fetch(`${BASE}${url}`, {
    method: 'POST',
    headers,
    body: formData,
  })
  if (res.status === 401) {
    try { localStorage.removeItem('dw_token') } catch {}
    try { localStorage.removeItem('dw_user') } catch {}
    window.dispatchEvent(new CustomEvent('auth-required'))
    throw new Error('NEED_LOGIN')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Upload Error ${res.status}`)
  }
  return res.json()
}

export const uploadApi = {
  /** 上传用户头像 */
  avatar: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return uploadFile<UploadResponse>('/upload/avatar', fd)
  },

  /** 上传角色头像/立绘 */
  characterAvatar: (templateId: string, file: File) => {
    const fd = new FormData()
    fd.append('template_id', templateId)
    fd.append('file', file)
    return uploadFile<UploadResponse>('/upload/character', fd)
  },

  /** 上传背景图 */
  background: (name: string, file: File, isPreset = false) => {
    const fd = new FormData()
    fd.append('name', name)
    fd.append('file', file)
    fd.append('is_preset', String(isPreset))
    return uploadFile<UploadResponse>('/upload/background', fd)
  },

  /** 上传 BGM */
  bgm: (name: string, file: File, isPreset = false) => {
    const fd = new FormData()
    fd.append('name', name)
    fd.append('file', file)
    fd.append('is_preset', String(isPreset))
    return uploadFile<UploadResponse>('/upload/bgm', fd)
  },

  /** 删除文件 */
  delete: (url: string) => {
    const fd = new FormData()
    fd.append('url', url)
    return uploadFile<{ message: string }>('/upload/file', fd)
  },
}

// ========== 游戏设置 API ==========

export const settingsApi = {
  /** 获取游戏设置 */
  get: () => request<GameSettings>('/settings/'),

  /** 更新游戏设置（部分更新） */
  update: (data: GameSettingsUpdate) =>
    request<GameSettings>('/settings/', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  /** 重置为默认设置 */
  reset: () =>
    request<GameSettings>('/settings/reset', { method: 'POST' }),

  /** 设置 BGM URL */
  setBgm: (bgm_url: string) =>
    request<GameSettings>('/settings/bgm', {
      method: 'POST',
      body: JSON.stringify({ bgm_url }),
    }),

  /** 设置背景图 URL */
  setBg: (bg_url: string) =>
    request<GameSettings>('/settings/background', {
      method: 'POST',
      body: JSON.stringify({ bg_url }),
    }),

  /** 移除 BGM */
  removeBgm: () =>
    request<{ message: string }>('/settings/bgm', { method: 'DELETE' }),

  /** 移除背景图 */
  removeBg: () =>
    request<{ message: string }>('/settings/background', { method: 'DELETE' }),
}
