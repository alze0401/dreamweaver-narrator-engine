/**
 * 织梦绮谭 - 资源文件管理
 * 处理场景图、BGM、角色立绘的路径映射和加载检测
 * 所有资源均为可选，不存在时静默降级
 */

// ========== 场景背景图 ==========

/** 场景关键词 → 文件名映射（不含扩展名） */
const SCENE_KEYWORDS: Record<string, string> = {
  '教室': 'classroom',
  '学校': 'school',
  '校园': 'school',
  '咖啡厅': 'cafe',
  '咖啡馆': 'cafe',
  '公园': 'park',
  '图书馆': 'library',
  '天台': 'rooftop',
  '屋顶': 'rooftop',
  '街道': 'street',
  '小巷': 'alley',
  '商店': 'shop',
  '家': 'home',
  '卧室': 'bedroom',
  '客厅': 'livingroom',
  '厨房': 'kitchen',
  '海边': 'beach',
  '森林': 'forest',
  '神社': 'shrine',
  '城堡': 'castle',
  '地下城': 'dungeon',
  '酒馆': 'tavern',
  '市场': 'market',
  '广场': 'plaza',
  '医院': 'hospital',
  '车站': 'station',
  '火车': 'train',
  '夜晚': 'night',
  '黄昏': 'sunset',
  '早晨': 'morning',
}

/** 支持的图片格式（按优先级） */
const IMG_EXTS = ['.jpg', '.jpeg', '.png', '.webp']

/**
 * 根据场景描述获取背景图 URL
 * 返回可用的图片 URL，如果没有匹配则返回 null
 */
export function getSceneBackground(location: string | undefined): string | null {
  if (!location) return null

  // 遍历场景关键词，找到匹配的英文文件名
  for (const [keyword, filename] of Object.entries(SCENE_KEYWORDS)) {
    if (location.includes(keyword)) {
      // 尝试各种扩展名，返回第一个（实际由浏览器 onerror 处理降级）
      return `/assets/scenes/${filename}.jpg`
    }
  }

  // 尝试直接用场景名作为文件名（去除空格）
  const sanitized = location.replace(/\s+/g, '_').toLowerCase()
  return `/assets/scenes/${sanitized}.jpg`
}

// ========== 背景音乐 ==========

/** 氛围关键词 → BGM 文件名映射 */
const MOOD_KEYWORDS: Record<string, string> = {
  '平静': 'peaceful',
  '温馨': 'warm',
  '浪漫': 'romantic',
  '紧张': 'tense',
  '悲伤': 'sad',
  '欢乐': 'happy',
  '神秘': 'mysterious',
  '战斗': 'battle',
  '恐怖': 'horror',
  '日常': 'daily',
  '悠闲': 'relaxed',
  '激昂': 'epic',
  '沉思': 'contemplative',
  '危险': 'danger',
}

const AUDIO_EXTS = ['.mp3', '.ogg', '.wav']

/**
 * 根据氛围获取 BGM URL
 * 返回可用的音频 URL，如果没有匹配则返回 null
 */
export function getBgmUrl(mood: string | undefined): string | null {
  if (!mood) return null

  for (const [keyword, filename] of Object.entries(MOOD_KEYWORDS)) {
    if (mood.includes(keyword)) {
      return `/assets/bgm/${filename}.mp3`
    }
  }

  // 尝试直接用氛围名
  const sanitized = mood.replace(/\s+/g, '_').toLowerCase()
  return `/assets/bgm/${sanitized}.mp3`
}

// ========== 角色立绘 ==========

/**
 * 获取角色立绘 URL
 * 优先使用角色名，也支持角色 id
 */
export function getCharacterPortrait(name: string, id?: string): string {
  // 优先用中文名
  const sanitized = name.replace(/\s+/g, '_')
  return `/assets/characters/${sanitized}.png`
}

/**
 * 尝试多个路径获取角色立绘，返回第一个可用的
 * 通过 Image.onerror 在组件中处理降级
 */
export function getCharacterPortraitCandidates(name: string, id?: string): string[] {
  const candidates: string[] = []

  // 中文名
  candidates.push(`/assets/characters/${name.replace(/\s+/g, '_')}.png`)

  // 角色 ID（如果有）
  if (id) candidates.push(`/assets/characters/${id}.png`)

  // jpg 备选
  candidates.push(`/assets/characters/${name.replace(/\s+/g, '_')}.jpg`)

  return candidates
}
