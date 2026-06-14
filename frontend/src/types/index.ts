/**
 * 织梦绮谭 - TypeScript 类型定义
 * 与后端 Pydantic schemas 对应的所有前端类型
 */

// ========== 模板相关 ==========

/** 模板摘要（列表展示用） */
export interface TemplateSummary {
  template_id: string
  template_type: 'world' | 'character' | 'scenario'
  name: string
  is_preset: boolean
  description: string
  tags: string[]
  avatar_url?: string | null
}

/** 模板完整详情 */
export interface TemplateDetail {
  template_id: string
  template_type: string
  name: string
  version: string
  is_preset: boolean
  description: string
  data: Record<string, unknown>
  categories: Array<{ code: string; name: string }>
  avatar_url?: string | null
}

// ========== 游戏相关 ==========

/** 开始游戏的请求参数 */
export interface GameStartRequest {
  world_template_id: string
  scenario_template_id: string
  player_name: string
  player_data: Record<string, string>
  character_template_ids: string[]
}

/** 开始游戏后的响应 */
export interface GameStartResponse {
  session_id: string
  opening_narration: string
  opening_dialogues: DialogueLine[]
  choices: DialogueChoice[]
  scene_state: SceneState
  updated_characters: CharacterSummary[]
  progress: ProgressInfo
}

/** 剧情进度信息 */
export interface ProgressInfo {
  chapter: number
  total_chapters: number
  current_turn: number
}

/** 游戏状态 */
export interface GameState {
  session_id: string
  player_name: string
  chapter: number
  total_chapters: number
  current_scene: string
  world_state: Record<string, unknown>
  character_count: number
  dialogue_count: number
  total_turns: number
  created_at: string
  updated_at: string
}

// ========== 对话相关 ==========

/** AI 生成的一个选项 */
export interface DialogueChoice {
  id: string
  text: string
  tone: string
  hint: string
}

/** 一句角色台词 */
export interface DialogueLine {
  speaker: string
  text: string
  emotion: string
  action: string
}

/** 场景状态 */
export interface SceneState {
  location?: string
  time?: string
  mood?: string
}

/** AI 生成的完整对话轮次 */
export interface DialogueAdvanceResponse {
  narration: string
  dialogues: DialogueLine[]
  choices: DialogueChoice[]
  scene_state: SceneState
  affection_changes: AffectionChange[]
  updated_characters: CharacterSummary[]
  progress: ProgressInfo
}

/** 好感度变化记录 */
export interface AffectionChange {
  character: string
  dimension: string
  delta: number
  reason: string
}

// ========== 角色相关 ==========

/** 角色摘要 */
export interface CharacterSummary {
  character_id: string
  character_name: string
  current_rank: string
  relationship_label: string
  overall_score: number
  intimacy: number
  trust: number
  respect: number
  curiosity: number
  fear: number
  avatar_url?: string | null
}

/** 角色详情（含好感度数值） */
export interface CharacterDetail extends CharacterSummary {
  intimacy: number
  trust: number
  respect: number
  curiosity: number
  fear: number
  triggered_events: string[]
  known_secrets: string[]
  avatar_url?: string | null
}

// ========== 存档相关 ==========

/** 存档位信息 */
export interface SaveSlot {
  id: string
  slot_number: number
  auto_save: boolean
  title: string
  description: string
  session_id: string
  created_at: string
}

// ========== 对话历史 ==========

/** 对话历史记录 */
export interface DialogueHistoryEntry {
  turn_number: number
  speaker: string
  content: string
  emotion: string | null
  action: string | null
  choices_offered: DialogueChoice[] | null
  choice_made: string | null
  input_type: string
}

// ========== 模板分类 ==========

/** 模板分类 */
export interface Category {
  id: number
  code: string
  name: string
  description: string
  icon: string
  sort_order: number
}

// ========== 用户认证 ==========

/** 当前用户信息 */
export interface AuthUser {
  id: string
  username: string
  display_name: string
  role: 'user' | 'admin'
  avatar_url?: string | null
}

/** 登录/注册响应 */
export interface AuthResponse {
  access_token: string
  user: AuthUser
}

// ========== 文件上传 ==========

/** 上传响应 */
export interface UploadResponse {
  url: string
  message: string
}

// ========== 游戏设置 ==========

/** 游戏设置 */
export interface GameSettings {
  bgm_url: string | null
  bgm_volume: number
  bgm_enabled: boolean
  sfx_volume: number
  bg_url: string | null
  text_speed: 'slow' | 'normal' | 'fast' | 'instant'
  theme: 'dark' | 'light' | 'sakura' | 'ocean' | 'forest' | 'sunset'
  font_size: number
  auto_advance: boolean
  show_affection_popup: boolean
}

/** 游戏设置更新（部分） */
export interface GameSettingsUpdate {
  bgm_url?: string | null
  bgm_volume?: number
  bgm_enabled?: boolean
  sfx_volume?: number
  bg_url?: string | null
  text_speed?: 'slow' | 'normal' | 'fast' | 'instant'
  theme?: 'dark' | 'light' | 'sakura' | 'ocean' | 'forest' | 'sunset'
  font_size?: number
  auto_advance?: boolean
  show_affection_popup?: boolean
}
