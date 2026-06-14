## 织梦绮谭 — Galgame + AI 大模型叙事引擎 系统架构文档

**项目代号**: *DreamWeaver / Narrator Engine*
**版本**: v3.0
**日期**: 2026-06-14

---

### 一、项目概述

本项目是一个以 AI 大模型（DeepSeek v4-pro）为核心驱动力的 Galgame 文字冒险引擎。玩家在预设或自定义的世界观中与性格各异的角色互动，通过"选项分支 + 自由对话"的混合模式推进剧情。引擎追踪五维好感度变化、维护三层记忆架构、管理角色名字渐进揭示，从而生成连贯且具有个性化的叙事体验。

**核心理念**: 不是"用 AI 替代编剧"，而是"让 AI 成为即兴演员 + 地下城主 (DM)"——它在世界观和人设的框架内即兴发挥，玩家的每一个选择都在塑造独一无二的故事。

---

### 二、技术选型

```
┌──────────────────────────────────────────────────────────┐
│                    Frontend (SPA)                         │
│    React 18 + TypeScript 5.4 + Vite 5.2                 │
│    样式: TailwindCSS 3.4   图表: Recharts 3.8           │
│    状态管理: Zustand 4.5   路由: React Router v6        │
│    文字渲染: useTypewriter hook (逐字打字机效果)          │
└────────────────────────┬─────────────────────────────────┘
                         │  REST API (JSON) + JWT 认证
┌────────────────────────▼─────────────────────────────────┐
│                  Backend (API Server)                      │
│         Python 3.12 / FastAPI + Uvicorn (异步)            │
│         ORM: SQLAlchemy 2.0 async (aiomysql 驱动)        │
│         LLM: LangChain ChatOpenAI → DeepSeek API         │
│         结构化输出: Pydantic + with_structured_output     │
│         工作流: LangGraph StateGraph (3节点管线)          │
│         Prompt: Jinja2 模板引擎                           │
│         缓存: Redis 7 (asyncio)                          │
│         认证: JWT (python-jose + bcrypt)                  │
│         存储: MinIO 对象存储 (S3 兼容协议)                │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│                     Data Layer                            │
│    主数据库: MySQL 8.0 (aiomysql 异步驱动, 连接池)       │
│    向量索引: ChromaDB (嵌入式, ONNX all-MiniLM-L6-v2)   │
│    缓存: Redis 7 (会话/对话/模板, TTL 300s-3600s)       │
│    对象存储: MinIO (头像/立绘/背景/BGM, S3 协议)        │
│    文件存储: 本地文件系统 (Jinja2 Prompt 模板)           │
└──────────────────────────────────────────────────────────┘
```

**选型理由**:

- FastAPI 异步原生，天然适合 LLM 流式调用，自带 OpenAPI 文档 (Swagger UI)。
- MySQL 8.0 + aiomysql 提供可靠的异步关系数据库，SQLAlchemy 2.0 ORM 支持类型安全的查询。启动时通过 `INFORMATION_SCHEMA` 自动检测并 `ALTER TABLE` 补齐缺失列，免去手动迁移。
- Redis 7 缓存游戏会话、对话历史、模板数据和分类信息，大幅减少数据库查询。
- LangChain ChatOpenAI 封装 DeepSeek API (OpenAI 兼容协议)，支持结构化输出 (function_calling / json_mode) 和流式调用。
- LangGraph StateGraph 将叙事生成编排为 `build_prompt → call_llm → parse_response` 三节点管线，支持重试和降级。
- Pydantic 结构化输出模型配合 `with_structured_output()`，确保 LLM 输出严格符合预定义 schema，消除字段缺失和类型错误。
- ChromaDB 嵌入式部署，使用 ONNX all-MiniLM-L6-v2 嵌入模型 (79.3MB)，零运维成本，专用于记忆向量相似度检索。
- MinIO 对象存储 (S3 兼容协议) 管理所有媒体资源——用户头像、角色立绘、场景背景、BGM 音频，支持公开读和签名 URL。
- JWT + bcrypt 认证体系，支持注册/登录/懒登录弹窗，Token 过期自动刷新。
- Zustand 比 Redux 轻量，四个 Store (gameStore + uiStore + authStore + bgmStore) 覆盖所有状态。
- Docker Compose 一键部署 (backend + MySQL + Redis + MinIO)，配合宿主机 Nginx 反向代理。

---

### 三、项目目录结构

```
project_code/
├── docker-compose.yml                 # Docker Compose 生产部署 (4 服务)
├── galgame-ai-architecture.md         # 本文档
├── README.md                          # 项目说明
├── .gitignore                         # Git 忽略规则
│
├── nginx/                             # Nginx 反向代理配置
│   ├── nginx.conf                     # Nginx 主配置
│   └── dreamweaver.conf               # 站点配置 (前端/API/MinIO 代理)
│
├── templates/                         # 预设游戏内容 (JSON)
│   ├── template_index.json            # 模板索引
│   ├── worlds/                        # 12 套世界观模板
│   ├── characters/                    # 14 套角色原型
│   └── scenarios/                     # 8 套剧本模板
│
├── backend/
│   ├── Dockerfile                     # 后端 Docker 镜像 (Python 3.12)
│   ├── .dockerignore                  # Docker 构建忽略
│   ├── run.py                         # 启动脚本 (uvicorn)
│   ├── requirements.txt               # Python 依赖
│   ├── .env                           # 开发环境变量
│   ├── .env.example                   # 环境变量示例
│   ├── .env.prod                      # 生产环境变量 (不入 Git)
│   │
│   ├── sql/
│   │   ├── init.sql                   # MySQL 初始化 + 种子数据
│   │   └── migrate_minio.sql          # MinIO 迁移脚本
│   │
│   ├── prompts/                       # Jinja2 Prompt 模板
│   │   ├── system_prompt.j2           # 主系统提示词 (每轮发送)
│   │   ├── memory_extract.j2          # 记忆提取提示词
│   │   └── affection_eval.j2          # 好感度评估提示词
│   │
│   ├── data/
│   │   └── chroma/                    # ChromaDB 持久化向量数据
│   │
│   ├── tests/                         # 测试用例
│   │
│   └── app/                           # 应用源码
│       ├── main.py                    # FastAPI 入口, lifespan, CORS, 9 个路由注册
│       ├── config.py                  # Pydantic Settings (.env 加载, 含 MinIO/JWT 配置)
│       ├── database.py                # SQLAlchemy async engine, 连接池, 自动迁移
│       ├── cache.py                   # RedisCache 单例 (会话/对话/模板/分类缓存)
│       ├── auth.py                    # JWT 认证: Token 管理, bcrypt 密码哈希, 依赖注入
│       ├── storage.py                 # MinIO 存储服务: 上传/删除/签名 URL, CORS 配置
│       │
│       ├── api/                       # API 路由层 (9 个 Router)
│       │   ├── auth.py                # POST /register, /login, GET /me, 修改密码, 更新资料
│       │   ├── game.py                # POST /start, GET /{id}/state, POST /{id}/advance
│       │   ├── character.py           # GET /{id}/characters, GET /{id}/characters/{cid}
│       │   ├── template.py            # GET, GET /{id}, POST, POST /{id}/clone, AI 生成
│       │   ├── category.py            # GET, GET /{code}/templates
│       │   ├── save.py                # GET, POST, POST /auto, POST /load, DELETE /{id}
│       │   ├── dialogue.py            # GET /{id}/history, memories, search, SSE stream
│       │   ├── settings.py            # GET/PATCH 游戏设置, BGM/背景管理, 重置
│       │   └── upload.py              # 头像/角色/背景/BGM 上传, 通用文件, 删除
│       │
│       ├── engine/                    # 核心叙事引擎
│       │   ├── narrator.py            # 调度中心: start_game(), advance(), 名字揭示, 章节推进
│       │   ├── narrator_graph.py      # LangGraph 工作流: build_prompt → call_llm → parse
│       │   ├── prompt_builder.py      # Jinja2 System Prompt 动态组装 + 内置降级
│       │   ├── affection.py           # 五维好感度计算器 + 等级计算 + 事件触发
│       │   └── memory.py              # 三层记忆管理器 (工作/情景/语义)
│       │
│       ├── llm/                       # LLM 适配层
│       │   ├── base.py                # BaseLLMProvider 抽象接口 + LLMMessage
│       │   ├── deepseek.py            # DeepSeekProvider (LangChain ChatOpenAI, thinking mode)
│       │   ├── narrator_schemas.py    # Pydantic 结构化输出模型 (NarratorOutput 等)
│       │   ├── template_schemas.py    # 模板 AI 生成的 Pydantic 模型
│       │   └── response_parser.py     # 4策略 JSON 解析 + 反填充 + JSON泄漏清洗 + 兜底
│       │
│       ├── models/                    # SQLAlchemy ORM 模型 (12 张表)
│       │   ├── game_session.py        # GameSession: 会话生命周期, world_state JSON
│       │   ├── dialogue_log.py        # DialogueLog: 逐轮对话记录
│       │   ├── affection.py           # AffectionState: 五维好感度
│       │   ├── scene_summary.py       # SceneSummary: 场景摘要 (Layer 2 记忆)
│       │   ├── memory.py              # Memory: 语义记忆 (Layer 3, ChromaDB)
│       │   ├── player_profile.py      # PlayerProfile: 玩家画像
│       │   ├── save_slot.py           # SaveSlot: 存档快照 (手动 1-20, 自动 101-103)
│       │   └── template_models.py     # Template, TemplateCategory, User, UserGameSettings
│       │
│       └── schemas/
│           └── schemas.py             # Pydantic DTO: 请求/响应模型
│
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── tailwind.config.js
    ├── vite.config.ts
    │
    └── src/
        ├── main.tsx                   # ReactDOM 入口 + BrowserRouter
        ├── App.tsx                    # 路由定义 (8 个页面路由) + 全局组件
        ├── index.css                  # Tailwind + Galgame 风格 CSS (glass-panel, 粒子, 渐变)
        │
        ├── types/
        │   └── index.ts              # 全部 TypeScript 接口 (与后端 Pydantic 对应)
        │
        ├── services/
        │   └── api.ts                # API 客户端: authApi, gameApi, templateApi, uploadApi...
        │
        ├── stores/
        │   ├── gameStore.ts          # Zustand: session, messages, choices, characters, progress
        │   ├── uiStore.ts            # Zustand: sidePanel, 好感数值开关, 打字速度, loading
        │   ├── authStore.ts          # Zustand: JWT Token, 用户信息, 登录/注册/登出
        │   └── bgmStore.ts           # Zustand: 全局 BGM 播放状态, 音量, 播放列表
        │
        ├── hooks/
        │   └── useTypewriter.ts      # 打字机效果 hook (逐字显示 + 点击跳过)
        │
        ├── utils/
        │   └── assets.ts            # 场景背景/BGM/立绘路径解析 (MinIO URL + 静默降级)
        │
        ├── pages/
        │   ├── Home.tsx              # 主菜单 (标题画面, 浮动粒子, 渐变光球)
        │   ├── Login.tsx             # 登录/注册页面
        │   ├── TemplateSelect.tsx    # 5步向导: 分类 → 世界 → 剧本 → 角色 → 确认开始
        │   ├── Game.tsx              # 核心游戏: 对话展示, 选项, 自由输入, 场景背景, BGM
        │   ├── SaveLoad.tsx          # 存档管理: 12 手动档 + 自动存档展示
        │   ├── TemplateManage.tsx    # 模板管理: 查看/创建/编辑/克隆自定义模板
        │   ├── Settings.tsx          # 游戏设置: BGM/背景/音量/主题/文字速度
        │   └── Profile.tsx           # 个人资料: 头像/昵称/密码修改
        │
        └── components/
            ├── DialogueBox.tsx       # 消息渲染: 叙事(装饰线), 台词(头像+情感), 玩家, 系统
            ├── ChoicePanel.tsx       # 选项卡片 (交错淡入动画 A/B/C/D)
            ├── FreeInput.tsx         # 自适应文本输入框
            ├── SidePanel.tsx         # 侧栏: 场景信息, 角色列表, 好感变动, 设置
            ├── CharacterCard.tsx     # 角色卡: 头像, 名字, 关系徽章, 雷达图
            ├── AffectionBar.tsx      # 好感度彩色进度条
            ├── AffectionToast.tsx    # 好感度变动浮动提示
            ├── AuthModal.tsx         # 懒登录弹窗 (需要登录时自动弹出)
            ├── AvatarLightbox.tsx    # 头像灯箱 (点击放大查看)
            ├── ImageCropper.tsx      # 图片裁剪组件 (头像上传)
            ├── GlobalBgm.tsx         # 全局 BGM 播放器 (跨页面持续播放)
            ├── TemplateForm.tsx      # 模板创建/编辑表单
            └── LoadingOverlay.tsx    # 全屏 Glass 加载遮罩
```

---

### 四、核心系统详细设计

#### 4.1 叙事引擎调度中心 (narrator.py)

`Narrator` 是整个系统的核心调度器，也是项目中最大的文件。它有两个主要方法:

**`start_game()` — 开始新游戏**:

```
1. 从 MySQL 加载世界观/剧本模板 (Redis 缓存优先)
2. 创建 GameSession 记录 (world_state JSON 含 name_reveals, real_name_map)
3. 初始化角色好感度 (character_name = "???", 五维初始值从模板读取)
4. 创建 PlayerProfile
5. 调用 LangGraph 工作流生成开场叙事
6. 将开场叙事写入 DialogueLog (turn_number=0, speaker="narrator")
7. 检查开场叙事中的名字揭示
8. 返回 session_id + 开场内容 + 角色列表
```

**`advance()` — 推进剧情**:

```
1. 记录玩家输入到 DialogueLog
2. 收集全部上下文 (世界/剧本/角色好感/记忆/玩家画像)
3. 调用 LangGraph 工作流 (build_prompt → call_llm → parse_response)
4. 记录 AI 响应到 DialogueLog
5. 应用好感度变化 (多策略名字匹配)
6. 检查名字揭示 (含 3 轮自动揭示兜底)
7. 更新场景状态 + 章节自动推进
8. 更新对话轮次计数
9. 返回叙事/对话/选项/场景状态/角色数据/好感变动
```

#### 4.2 LangGraph 工作流 (narrator_graph.py)

叙事生成通过 LangGraph StateGraph 编排为三节点管线:

```
[Initial State] ──→ build_prompt_node ──→ call_llm_node ──→ parse_response_node ──→ [END]
```

**`build_prompt_node`**: 调用 `PromptBuilder.build_system_prompt()` 渲染 Jinja2 模板，组装消息列表 (system prompt + 对话历史 + 玩家输入)。自动去重: 如果 `recent_dialogues` 最后一条与 `player_input` 相同则跳过。

**`call_llm_node`**: 采用结构化输出优先策略:

```
1. 首先尝试 structured_output (function_calling 方法)
   - 使用 NarratorOutput Pydantic 模型
   - 自动禁用 thinking mode (DeepSeek thinking 与 function_calling 不兼容)
   - 如果 function_calling 失败 → 降级到 json_mode
2. json_mode 降级:
   - response_format={"type": "json_object"}
   - 同样禁用 thinking mode
3. 最终兜底: chat_completion (普通 JSON mode)
4. 空响应自动重试最多 3 次 (含指数退避)
```

**`parse_response_node`**: 通过 `ResponseParser` 的 4 策略提取结构化 JSON。确保 `narration` 不为空 (从对话生成过渡叙事)。额外安全网:

- **反填充安全网**: 检测并清除 LLM 在 narration 中重复填充过去已叙述内容的行为
- **JSON 泄漏清洗**: 当 narration 以 `{` 开头时，尝试从混合文本中提取纯叙事内容
- **空选项兜底**: 当 choices 为空数组时，自动生成合理的默认选项

#### 4.3 结构化输出系统 (narrator_schemas.py)

为解决 LLM 返回不规范 JSON 导致 Pydantic 验证失败的问题，定义了专用的结构化输出模型:

**核心模型 `NarratorOutput`**:

```python
class NarratorOutput(BaseModel):
    narration: str          # 纯叙事文本 (禁止包含角色台词)
    dialogues: list[DialogueLine]  # 角色台词列表
    choices: list[Choice]          # 玩家选项 (3-4 个)
    scene_state: SceneState        # 场景状态 (地点/时间/氛围)
    affection_changes: list[AffectionChange]  # 好感度变化
```

**关键设计决策**:

- `Choice.id` 设置 `default=""` 并添加 `coerce_id_to_str` 验证器，兼容 LLM 返回 `null` 或省略的情况
- `Choice.hint` 使用 `alias="affection_hint"` + `normalize_hint` 验证器，将 `None` 规范化为空字符串，避免 Pydantic `Optional[str]` 被 LangChain schema 生成器错误转换为非空 string 类型
- `DialogueLine.emotion` 添加非空验证器，默认回退为 "平静"
- 所有 `field_validator` 使用 `mode="before"` 在类型转换前进行规范化

**与 LangChain 集成**:

```python
# deepseek.py — structured_completion()
structured_llm = self._llm.with_structured_output(
    NarratorOutput,
    method="function_calling"  # 首选 function_calling
)
result = await structured_llm.ainvoke(messages)
```

#### 4.4 DeepSeek Thinking Mode 兼容 (deepseek.py)

DeepSeek v4-pro 模型支持 thinking mode (深度思考)，但此模式与 function_calling 和 json_mode 不兼容。解决方案:

```python
def _create_llm(self, temperature=0.75, max_tokens=2048, top_p=0.9,
                response_format=None, thinking=None) -> ChatOpenAI:
    kwargs = {
        "model": self._model,  # deepseek-v4-pro
        "api_key": self._api_key,
        "base_url": self._base_url,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": top_p,
    }
    if response_format:
        kwargs["response_format"] = response_format
    if thinking is not None:
        # DeepSeek thinking 参数是 ThinkingOptions 结构体
        # 不能传 boolean，必须传 {"type": "enabled"|"disabled"}
        thinking_type = "disabled" if not thinking else "enabled"
        kwargs["extra_body"] = {"thinking": {"type": thinking_type}}
    return ChatOpenAI(**kwargs)
```

**踩坑记录**:

- `model_kwargs={"thinking": False}` → OpenAI SDK 校验失败 (`unexpected keyword argument`)
- `extra_body={"thinking": False}` → DeepSeek API 400 错误 (`expected struct ThinkingOptions`)
- 最终方案: `extra_body={"thinking": {"type": "disabled"}}` 绕过 SDK 校验，符合 API 规范

#### 4.5 Prompt 构建器 (prompt_builder.py)

使用 Jinja2 模板引擎动态组装 System Prompt。模板文件在 `backend/prompts/` 目录下，不存在时使用内置降级方案。

**`system_prompt.j2` 结构** (每轮发送):

```
核心规则 (8 条)
多角色场景管理 (6 条)
叙事节奏与聚焦 (4 条)
叙事时序与连贯性 (6 条, 最高优先级)
防止重复创作 (6 条)
近期叙事回顾 (避免重复已写内容)
输出格式 (JSON Schema + 名字揭示规则 + 剧情推进规则 + 好感度变化规则)
世界设定 (名称/时代/类型/规则/当前地点时间)
当前场景 (前提/章节/地点/剧情钩子/章节指引)
出场角色 (每人含 name/real_name/name_revealed/性格/喜好/厌恶/说话风格/好感度)
过去的场景回顾 (Layer 2 记忆)
关键事实 (Layer 3 记忆)
玩家信息 (角色名/年龄/背景/已展现特征/游玩风格)
```

**记忆格式**: 工作记忆采用自然语言文本块 (而非 JSON)，提高 LLM 可读性:

```
[第3轮 · 叙事]
晨光洒落，雾气渐散。港口开始忙碌起来...

[第3轮 · 凝光] (捋了捋袖口，略带赞许)
"倒是直爽。璃月港近来确实有几桩事务需要人手。"
```

#### 4.6 好感度系统 (affection.py)

**五维好感模型**:

| 维度      | 含义                           | 范围      |
| --------- | ------------------------------ | --------- |
| intimacy  | 亲密度 — 情感距离              | -30 ~ 100 |
| trust     | 信任度 — 对玩家可靠性的评价    | -30 ~ 100 |
| respect   | 尊重度 — 对玩家能力/品格的评价 | -30 ~ 100 |
| curiosity | 好奇度 — 对玩家的兴趣程度      | -30 ~ 100 |
| fear      | 畏惧度 — 可触发特殊剧情        | 0 ~ 100   |

**好感度等级**: 由五维加权综合值决定，每个角色在模板中自定义等级区间和描述。

**好感度变化流程**:

```
LLM 返回 affection_changes (JSON 数组)
    ↓
_apply_affection_changes() 多策略匹配角色:
  ① character_name (显示名)
  ② canonical_name (从模板提取的真名)
  ③ character_id (模板 ID)
    ↓
AffectionCalculator.apply_changes()
  - 合并 LLM 评估 + 选项预设效果
  - 单次变化限制 ±8
  - 应用到 ORM 模型
```

**前端展示**: 侧栏 `SidePanel` 显示角色列表，每个角色展示:

- `CharacterCard`: 头像/名字/关系徽章
- `AffectionBar`: 彩色进度条 (颜色随等级变化)
- Recharts `RadarChart`: 五维雷达图 (实时更新)
- `AffectionToast`: 好感度变动浮动提示
- 好感变动列表 (显示本轮变化明细)

#### 4.7 名字揭示系统

角色初始显示名为 "???"，只有当角色在剧情中自然自我介绍后才揭示真名。

**揭示机制**:

1. 模板的 `full_name` 字段格式: `"自定义 (参考: 高宫凛 / 白雪·克劳蒂亚 / ...)"` 或直接写名字
2. `_extract_canonical_name()` 自动从模板字符串中提取第一个参考名作为规范名
3. System Prompt 中明确告知 LLM 每个角色的 `real_name`，并指示:
   - 未揭示时用外貌描写代替名字，`speaker` 写 "???"
   - 自我介绍时 `speaker` 切换为真名
   - 必须使用 `real_name` 中的确切名字，不可自创头衔
4. `_check_name_reveals()` 每轮检查 LLM 输出中是否出现角色的真名 (含 `speaker` 字段和叙事文本)
5. **自动揭示兜底**: 如果超过 3 轮仍无任何角色揭示，强制揭示互动最多的角色

**匹配逻辑**: 名字揭示检测同时扫描 `narration`、`dialogues[].text`、`dialogues[].speaker`，确保 LLM 以任何形式提到真名都能触发。

#### 4.8 三层记忆系统 (memory.py)

```
┌──────────────────────────────────────────────┐
│        Layer 1: 工作记忆 (Working)            │
│                                              │
│  最近 12 轮对话 (DialogueLog 直查)           │
│  自然语言格式 (非 JSON)                       │
│  直接作为 LLM messages 发送                  │
└────────────────────┬─────────────────────────┘
                     │ 超出容量时
┌────────────────────▼─────────────────────────┐
│        Layer 2: 情景记忆 (Episodic)           │
│                                              │
│  场景压缩摘要 (SceneSummary 表)              │
│  按章节/场景组织, 每条 200-500 tokens        │
│  保留最近 30 个场景摘要                      │
└────────────────────┬─────────────────────────┘
                     │ 重要事件
┌────────────────────▼─────────────────────────┐
│        Layer 3: 语义记忆 (Semantic)           │
│                                              │
│  关键事实 (Memory 表 + ChromaDB 向量)        │
│  ONNX all-MiniLM-L6-v2 嵌入模型             │
│  向量相似度搜索 (top_k=8)                    │
│  importance >= 6 才保存                      │
└──────────────────────────────────────────────┘
```

**记忆检索** (每轮构建 Prompt 时):

```python
build_memory_context(session_id, chapter, player_input):
    recent_dialogues = get_working_memory(limit=12)    # Layer 1
    scene_summaries  = get_episodic_memory(chapter)    # Layer 2
    key_facts        = search_semantic_memory(input)   # Layer 3 (ChromaDB)
    return {recent_dialogues, scene_summaries, key_facts}
```

**ChromaDB 嵌入模型**: 使用 `all-MiniLM-L6-v2` ONNX 模型 (79.3MB)。生产部署时通过 Docker 卷挂载预下载的模型文件，避免容器内从 AWS S3 慢速下载:

```yaml
# docker-compose.yml
volumes:
  - /opt/chroma_model_cache:/root/.cache/chroma/onnx_models:ro
```

#### 4.9 对话历史管理

每轮对话在 `DialogueLog` 表中产生两条记录:

| 记录     | turn_number | speaker    | content                                                      |
| -------- | ----------- | ---------- | ------------------------------------------------------------ |
| 玩家输入 | N           | "player"   | 选项文本或自由输入                                           |
| AI 响应  | N+1         | "narrator" | 完整 JSON (含 narration/dialogues/choices/scene_state/affection_changes) |

`start_game()` 的开场叙事也作为 `turn_number=0, speaker="narrator"` 存入，确保第二轮 LLM 能看到完整上下文。

#### 4.10 章节推进系统

```
每轮 advance() 结束后:
  total_turns = current_turn + 1
  turns_per_chapter = max(6, total_turns // estimated_chapters)

  如果剧本有 chapter_beats:
    检查当前 beat 的 trigger_turn → 达标则推进章节
  否则:
    每 turns_per_chapter 轮自动推进一章
```

#### 4.11 存档系统 (SaveSlot)

- 20 个手动存档位 (slot 1-20) + 3 个自动存档位 (slot 101-103)
- 前端每 3 轮触发一次自动存档，循环覆盖 101-103
- 存档内容为完整游戏状态快照 (JSON)
- 支持加载存档恢复游戏

#### 4.12 用户认证系统 (auth.py)

基于 JWT + bcrypt 的用户认证体系:

**认证流程**:

```
注册/登录 → 验证凭据 → 生成 JWT Token (HS256) → 返回 access_token
                                                      ↓
后续请求 → Authorization: Bearer <token> → get_current_user 依赖注入 → User 对象
```

**关键组件**:

- `hash_password()` / `verify_password()`: bcrypt 密码哈希 (passlib)
- `create_access_token()`: JWT 生成 (python-jose)，默认 24 小时过期
- `get_current_user()`: FastAPI 依赖，从 Bearer Token 提取用户
- `get_optional_user()`: 可选认证依赖，未登录时返回 None (用于模板列表等公开接口)

**前端集成**: `AuthModal` 组件实现懒登录弹窗——当用户尝试需要认证的操作 (如创建模板、保存设置) 时自动弹出登录/注册表单。

#### 4.13 MinIO 对象存储 (storage.py)

`StorageService` 封装 MinIO 客户端，管理所有媒体资源:

**存储目录结构**:

```
dreamweaver-assets/          (Bucket)
├── preset/
│   ├── characters/          # 预设角色头像/立绘
│   ├── backgrounds/         # 预设场景背景
│   └── bgm/                 # 预设 BGM
└── user/
    ├── avatars/{user_id}/   # 用户头像
    ├── characters/{user_id}/# 自建角色头像
    ├── backgrounds/{user_id}/# 自建背景
    └── bgm/{user_id}/       # 上传 BGM
```

**功能**:

- 文件上传 (头像/角色/背景/BGM)，自动生成 UUID 文件名避免冲突
- 公开读策略 (匿名 GET)，支持 Nginx 代理访问
- CORS 配置 (允许前端跨域加载图片)
- 文件大小限制: 图片 5MB，音频 20MB
- 签名 URL (用于私有文件临时访问)

**Nginx 代理**: MinIO 资源通过 Nginx 反向代理暴露，URL 格式 `/minio/dreamweaver-assets/preset/characters/xxx.webp`，代理到 `127.0.0.1:9000`。

#### 4.14 ResponseParser 4 策略 JSON 解析 (response_parser.py)

`ResponseParser` 负责从 LLM 原始输出中提取结构化数据，包含多层安全网:

**4 级解析策略**:

```
策略 1: 直接 JSON 解析 (json.loads)
    ↓ 失败
策略 2: Markdown 代码块提取 (```json ... ```)
    ↓ 失败
策略 3: 花括号提取 (找到最外层 { ... } 配对)
    ↓ 失败
策略 4: 全文降级 (尝试修复不完整的 JSON，花括号重平衡)
```

**后处理安全网** (在策略 1-3 成功后执行):

- **反填充安全网** (`_clean_refill_narration`): 检测 LLM 是否在 narration 中重复了之前已经叙述过的内容 (如重新描述开场场景)，如果有则截断重复部分
- **JSON 泄漏清洗** (`_clean_json_leak`): 当 narration 以 `{` 开头时，说明 LLM 可能把 JSON 结构混入了叙事文本，尝试从中提取纯文本
- **空选项兜底** (`_ensure_choices_not_empty`): 如果 choices 为空数组，自动生成 "继续探索" / "与她交谈" 等合理默认选项
- **narration 非空保证** (`_ensure_narration`): 如果 narration 为空，从最近一条对话生成过渡叙事

---

### 五、数据模型 (ER 关系)

```
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│   GameSession    │──1:N─<│   DialogueLog    │       │    Template      │
│──────────────────│       │──────────────────│       │──────────────────│
│ id (PK, UUID)    │       │ id (PK)          │       │ template_id (PK) │
│ world_template_id│       │ session_id (FK)  │       │ template_type    │
│ scenario_template_id     │ turn_number      │       │ name             │
│ player_name      │       │ speaker          │       │ data (JSON)      │
│ player_data (JSON)       │ content          │       │ is_preset        │
│ chapter          │       │ input_type       │       │ tags (JSON)      │
│ current_scene    │       │ choices_offered  │       │ version          │
│ world_state (JSON)       │ metadata_json    │       │ creator_id (FK)  │
│ total_turns      │       └──────────────────┘       │ avatar_url       │
└──────┬───────────┘                                   └────────┬─────────┘
       │                                             ┌─────────▼─────────┐
       │  ┌──────────────────┐                       │ TemplateCategory  │
       └─<│ AffectionState   │                       │──────────────────│
          │──────────────────│                       │ code (PK)         │
          │ id (PK)          │                       │ name              │
          │ session_id (FK)  │                       │ icon              │
          │ character_id     │    ┌──────────────┐   │ sort_order        │
          │ character_name   │    │ SceneSummary │   └─────────┬─────────┘
          │ intimacy         │    │──────────────│             │
          │ trust            │    │ id (PK)      │   ┌─────────▼─────────┐
          │ respect          │    │ session_id   │   │ CategoryMapping   │
          │ curiosity        │    │ chapter      │   │──────────────────│
          │ fear             │    │ scene_name   │   │ template_id (FK)  │
          │ current_rank     │    │ summary_text │   │ category_id (FK)  │
          │ relationship_label     │ characters   │   └───────────────────┘
          │ triggered_events │    │ key_events   │
          │ known_secrets    │    │ turn_range   │   ┌──────────────────┐
          └──────────────────┘    └──────────────┘   │     Memory       │
                                                     │──────────────────│
          ┌──────────────────┐                       │ id (PK)          │
          │ PlayerProfile    │                       │ session_id (FK)  │
          │──────────────────│                       │ content          │
          │ id (PK)          │    ┌──────────────┐   │ category         │
          │ session_id (FK)  │    │   SaveSlot   │   │ importance (1-10)│
          │ name             │    │──────────────│   │ related_characters│
          │ age              │    │ id (PK)      │   │ embedding_id     │
          │ background       │    │ session_id   │   │ created_at       │
          │ observed_traits  │    │ slot_number  │   └──────────────────┘
          │ play_style       │    │ state_snapshot   ┌──────────────────┐
          │ key_decisions    │    │ created_at   │   │      User        │
          └──────────────────┘    └──────────────┘   │──────────────────│
                                                     │ id (PK)          │
                                                     │ username         │
                                                     │ password_hash    │
                                                     │ display_name     │
                                                     │ role             │
                                                     │ avatar_url       │
                                                     └────────┬─────────┘
                                                              │
                                                     ┌────────▼─────────┐
                                                     │ UserGameSettings │
                                                     │──────────────────│
                                                     │ user_id (PK,FK)  │
                                                     │ bgm_url          │
                                                     │ bgm_volume       │
                                                     │ bg_url           │
                                                     │ text_speed       │
                                                     │ theme            │
                                                     │ font_size        │
                                                     │ auto_advance     │
                                                     └──────────────────┘
```

---

### 六、API 接口设计

| 方法         | 路径                                 | 说明                                        |
| ------------ | ------------------------------------ | ------------------------------------------- |
| **认证**     |                                      |                                             |
| POST         | `/api/auth/register`                 | 用户注册 (返回 JWT Token)                   |
| POST         | `/api/auth/login`                    | 用户登录 (返回 JWT Token)                   |
| GET          | `/api/auth/me`                       | 获取当前用户信息                            |
| POST         | `/api/auth/change-password`          | 修改密码                                    |
| PATCH        | `/api/auth/profile`                  | 更新个人资料                                |
| **游戏流程** |                                      |                                             |
| POST         | `/api/game/start`                    | 开始新游戏 (选择模板 + 设定角色)            |
| GET          | `/api/game/{id}/state`               | 获取当前游戏状态                            |
| POST         | `/api/game/{id}/advance`             | 推进剧情 (选择选项 / 自由输入)              |
| **角色**     |                                      |                                             |
| GET          | `/api/game/{id}/characters`          | 获取当前游戏所有角色                        |
| GET          | `/api/game/{id}/characters/{cid}`    | 获取角色详情 + 当前好感度                   |
| **模板**     |                                      |                                             |
| GET          | `/api/templates`                     | 获取所有模板 (支持 type 过滤, 含用户自定义) |
| GET          | `/api/templates/{id}`                | 获取单个模板详情                            |
| POST         | `/api/templates`                     | 创建自定义模板                              |
| POST         | `/api/templates/{id}/clone`          | 克隆模板为自定义版本                        |
| POST         | `/api/templates/ai-generate`         | AI 生成模板 (角色/世界观/剧本)              |
| **分类**     |                                      |                                             |
| GET          | `/api/categories`                    | 获取所有分类                                |
| GET          | `/api/categories/{code}/templates`   | 获取分类下的模板                            |
| **存档**     |                                      |                                             |
| GET          | `/api/saves`                         | 获取所有存档                                |
| POST         | `/api/saves`                         | 创建存档                                    |
| POST         | `/api/saves/auto`                    | 自动存档 (循环覆盖 slot 101-103)            |
| POST         | `/api/saves/load`                    | 加载存档                                    |
| DELETE       | `/api/saves/{id}`                    | 删除存档                                    |
| **对话**     |                                      |                                             |
| GET          | `/api/dialogue/{id}/history`         | 获取对话历史                                |
| GET          | `/api/dialogue/{id}/memories`        | 获取记忆日志                                |
| GET          | `/api/dialogue/{id}/memories/search` | 搜索记忆                                    |
| GET          | `/api/dialogue/{id}/stream`          | SSE 流式输出                                |
| **设置**     |                                      |                                             |
| GET          | `/api/settings/`                     | 获取游戏设置                                |
| PATCH        | `/api/settings/`                     | 更新游戏设置 (部分更新)                     |
| POST         | `/api/settings/reset`                | 重置为默认设置                              |
| POST         | `/api/settings/bgm`                  | 设置 BGM URL                                |
| POST         | `/api/settings/background`           | 设置背景 URL                                |
| DELETE       | `/api/settings/bgm`                  | 移除 BGM                                    |
| DELETE       | `/api/settings/background`           | 移除背景                                    |
| **上传**     |                                      |                                             |
| POST         | `/api/upload/avatar`                 | 上传用户头像                                |
| POST         | `/api/upload/character`              | 上传角色头像/立绘                           |
| POST         | `/api/upload/background`             | 上传场景背景图                              |
| POST         | `/api/upload/bgm`                    | 上传背景音乐                                |
| POST         | `/api/upload/file`                   | 通用文件上传                                |
| DELETE       | `/api/upload/file`                   | 删除已上传文件                              |

**核心接口 — `POST /api/game/{id}/advance`**:

```json
// Request
{
  "input_type": "choice",    // "choice" | "free"
  "content": "c1"            // 选项 ID 或自由输入文本
}

// Response (DialogueAdvanceResponse)
{
  "narration": "叙事文本...",
  "dialogues": [
    {"speaker": "角色名", "text": "台词", "emotion": "中文情感", "action": "动作"}
  ],
  "choices": [
    {"id": "c1", "text": "选项文本", "tone": "语气", "hint": "提示"}
  ],
  "scene_state": {"location": "地点", "time": "时间", "mood": "氛围"},
  "affection_changes": [
    {"character": "角色名", "dimension": "trust", "delta": 3, "reason": "原因"}
  ],
  "updated_characters": [
    {"character_id": "char_xxx", "character_name": "???", "intimacy": 5, ...}
  ],
  "progress": {"chapter": 1, "total_chapters": 5, "current_turn": 3}
}
```

---

### 七、前端 UI 架构

**页面路由**:

| 路由               | 页面               | 功能                        |
| ------------------ | ------------------ | --------------------------- |
| `/`                | Home.tsx           | 主菜单 (标题画面, 浮动粒子) |
| `/login`           | Login.tsx          | 登录/注册页面               |
| `/template-select` | TemplateSelect.tsx | 5步向导创建新游戏           |
| `/game`            | Game.tsx           | 核心游戏界面                |
| `/load-save`       | SaveLoad.tsx       | 存档管理                    |
| `/templates`       | TemplateManage.tsx | 模板管理 (创建/编辑/克隆)   |
| `/settings`        | Settings.tsx       | 游戏设置 (BGM/背景/主题)    |
| `/profile`         | Profile.tsx        | 个人资料 (头像/昵称/密码)   |

**全局组件** (挂载在 App.tsx):

- `LoadingOverlay`: 全局 Glass 加载遮罩
- `GlobalBgm`: 全局 BGM 播放器 (跨页面持续播放)
- `AuthModal`: 懒登录弹窗 (需要认证时自动弹出)

**Game.tsx 组件树**:

```
Game.tsx
├── Header (返回, 场景信息, 章节进度条, 存档/菜单按钮)
├── 消息区 (overflow-y-auto)
│   └── DialogueBox.tsx × N (每条消息)
│       ├── type=narration → 装饰线 + serif 字体叙事文本
│       ├── type=dialogue  → 头像 + 角色名 + 情感标签 + 动作 + 台词气泡
│       ├── type=player    → 右对齐玩家消息
│       └── type=system    → 居中系统提示
│       └── useTypewriter hook (逐字动画, 点击跳过)
├── ChoicePanel.tsx (选项卡片 A/B/C/D, 交错淡入)
├── FreeInput.tsx (自适应文本框 + 发送)
└── SidePanel.tsx (侧滑面板)
    ├── 场景信息 (地点/时间/氛围/章节)
    ├── CharacterCard.tsx × N
    │   ├── 头像/名字/关系徽章/综合分数
    │   ├── AffectionBar.tsx (彩色进度条)
    │   └── Recharts RadarChart (五维雷达图)
    ├── AffectionToast.tsx (好感变动浮动提示)
    ├── 好感变动列表
    └── 设置 (好感数值显示开关)
```

**状态管理 (Zustand)**:

`gameStore`:

- `sessionId`, `chapter`, `totalChapters`, `currentTurn`, `sceneState`
- `messages: DisplayMessage[]` — 统一消息列表 (4种类型)
- `currentChoices: DialogueChoice[]` — 当前选项
- `characters: CharacterSummary[]` — 实时角色数据 (含五维好感度)
- `recentAffectionChanges` — 本轮好感变动
- `isGenerating: boolean` — AI 生成中状态

`uiStore`:

- `sidePanelOpen`, `showAffectionNumbers`, `typewriterSpeed`
- `loading`, `loadingText` — 全局加载遮罩

`authStore`:

- `token`, `user` — JWT Token 和用户信息
- `login()`, `register()`, `logout()` — 认证操作
- `hydrate()` — 从 localStorage 恢复认证状态
- `isAuthenticated` — 认证状态派生

`bgmStore`:

- `currentTrack`, `isPlaying`, `volume`
- `playlist`, `currentIndex`
- `play()`, `pause()`, `next()`, `setVolume()`

---

### 八、关键技术挑战与解决方案

| 挑战                                      | 解决方案                                                     |
| ----------------------------------------- | ------------------------------------------------------------ |
| LLM 返回空响应                            | `call_llm_node` 自动重试 3 次 + 指数退避; `response_parser` 用 `_ensure_narration()` 兜底生成过渡叙事 |
| LLM 不遵循 JSON 格式                      | 结构化输出优先 (`with_structured_output` function_calling) → json_mode 降级 → 4 策略解析 (直接JSON → 代码块 → 花括号 → 全文修复) |
| Pydantic 验证失败 (Choice.id/hint)        | `Choice.id` 添加 `default=""` + `coerce_id_to_str` 验证器; `Choice.hint` 使用 `normalize_hint` 将 None 规范化为空字符串 |
| DeepSeek thinking mode 与结构化输出不兼容 | 通过 `extra_body={"thinking": {"type": "disabled"}}` 在结构化调用时禁用 thinking; 必须传 ThinkingOptions 结构体而非 boolean |
| `model_kwargs` 导致 SDK 校验失败          | 改用 `extra_body` 参数绕过 OpenAI SDK 校验，直接传递 DeepSeek 专有参数 |
| 角色名字不揭示                            | 自动揭示兜底: 3 轮未揭示则强制揭示互动最多的角色; Prompt 指示 LLM 在 2-3 轮内让角色自我介绍 |
| 好感度变化匹配失败                        | 多策略匹配: display name + canonical name + character_id; 不匹配时打 WARNING 日志 |
| LLM 重复描述开场场景                      | 开场叙事写入 DialogueLog (turn=0); `recent_dialogues` 包含完整上一轮响应; 玩家输入自动去重; 反填充安全网 |
| LLM 在叙事中混入 JSON                     | JSON 泄漏清洗: 检测 narration 以 `{` 开头时从混合文本中提取纯叙事内容 |
| choices 返回空数组                        | 空选项兜底: 自动生成 "继续探索" / "与她交谈" 等合理默认选项  |
| 剧情不推进 / 只有"继续"选项               | Prompt 中强化剧情推进规则 + 禁止空泛选项 + 章节自动推进系统  |
| 长期游戏上下文溢出                        | 三层记忆架构 + 自然语言记忆格式 (比 JSON 更省 token) + `recent_narration_summary` 防重复 |
| 数据库缺少新列                            | 启动时 `_auto_migrate_columns()` 通过 `INFORMATION_SCHEMA` 检测缺失列并自动 `ALTER TABLE` |
| 模板名不规范                              | `_extract_canonical_name()` 从 `"自定义 (参考: X / Y / Z)"` 格式自动提取第一个名字 |
| 多角色对话混乱                            | Prompt 中强制标注 speaker + 焦点角色限制 + 每轮最多 2-3 个角色有台词 |
| 场景背景/BGM 加载失败                     | 前端 `assets.ts` 全部静默降级 (onerror → null)，不影响游戏体验; MinIO URL 代理通过 Nginx |
| ChromaDB ONNX 模型下载极慢                | 预下载模型文件到宿主机，通过 Docker 卷挂载 (`/opt/chroma_model_cache:/root/.cache/chroma/onnx_models:ro`) |
| Docker 构建 pip 403                       | 将清华 pip 镜像切换为阿里云镜像 (`mirrors.aliyun.com/pypi/simple/`) |

---

### 九、基础设施

#### 9.1 Docker Compose 部署

生产环境使用 Docker Compose 编排 4 个服务:

```yaml
services:
  backend:          # FastAPI 后端 (Python 3.12)
    image: dreamweaver-backend:latest
    ports: ["8000:8000"]
    depends_on: [mysql, redis, minio]
    volumes:
      - /opt/chroma_model_cache:/root/.cache/chroma/onnx_models:ro  # 预下载 ONNX 模型

  mysql:            # MySQL 8.0 数据库
    image: mysql:8.0
    environment:
      MYSQL_DATABASE: narrator_engine
    volumes:
      - mysql_data:/var/lib/mysql
      - ./backend/sql/init.sql:/docker-entrypoint-initdb.d/01-init.sql:ro

  redis:            # Redis 7 缓存
    image: redis:7-alpine
    command: redis-server --requirepass narrator2024 --appendonly yes

  minio:            # MinIO 对象存储
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports: ["9000:9000", "9002:9001"]
```

**服务依赖**: backend 等待 mysql (healthy) + redis (healthy) + minio (started) 后才启动。

**数据卷**: `mysql_data`, `redis_data`, `minio_data`, `backend_data` 四个命名卷持久化数据。

#### 9.2 Nginx 反向代理

宿主机 Nginx 作为统一入口:

```
客户端请求
    │
    ├── /                    → 前端静态文件 (/opt/dreamweaver/frontend/dist)
    ├── /assets/             → 静态资源 (30天缓存)
    ├── /api/                → FastAPI 后端 (127.0.0.1:8000, SSE 支持)
    ├── /docs, /redoc        → Swagger/ReDoc 文档
    └── /minio/              → MinIO 资源代理 (127.0.0.1:9000, 7天缓存)
```

**SSE 支持**: API 代理关闭 `proxy_buffering` 和 `proxy_cache`，读写超时设为 120s。

#### 9.3 数据库自动迁移 (database.py)

```python
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)   # CREATE TABLE IF NOT EXISTS
        await _auto_migrate_columns(conn)                 # ALTER TABLE ADD COLUMN (如有缺失)
```

`_auto_migrate_columns()` 查询 `INFORMATION_SCHEMA.COLUMNS`，对比 ORM 模型定义，对缺失的列自动执行 `ALTER TABLE ADD COLUMN`。JSON 类型列使用 `DEFAULT ('[]')` 语法。

#### 9.4 Redis 缓存 (cache.py)

| 缓存域       | TTL   | 说明                      |
| ------------ | ----- | ------------------------- |
| game_session | 3600s | 游戏会话状态              |
| dialogue     | 300s  | 最近对话历史              |
| template     | 1800s | 模板数据 (世界/角色/剧本) |
| category     | 1800s | 模板分类信息              |

模板加载三级降级: Redis 缓存 → MySQL 查询 → 本地 JSON 文件。

#### 9.5 LLM 适配层

```python
# deepseek.py — 通过 LangChain 调用 DeepSeek v4-pro
self._llm = ChatOpenAI(
    model="deepseek-v4-pro",
    base_url="https://api.deepseek.com",
    ...
)

# 结构化输出 (首选)
structured_llm = self._llm.with_structured_output(
    NarratorOutput, method="function_calling"
)

# JSON mode (降级)
response = await self._llm.bind(
    response_format={"type": "json_object"}
).ainvoke(messages)
```

---

### 十、环境变量配置

#### 开发环境 (.env)

```env
# DeepSeek API
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro

# 应用配置
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DEBUG=true

# MySQL 数据库
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=narrator
MYSQL_PASSWORD=narrator2024
MYSQL_DATABASE=narrator_engine

# Redis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=narrator2024
REDIS_DB=0

# ChromaDB
CHROMA_PERSIST_DIR=./data/chroma

# LLM 参数
LLM_TEMPERATURE=0.75
LLM_MAX_TOKENS=2048
LLM_TOP_P=0.9

# 记忆系统
MEMORY_MAX_WORKING_TURNS=12
MEMORY_MAX_EPISODIC_SUMMARIES=30
MEMORY_MIN_IMPORTANCE=6
MEMORY_VECTOR_SEARCH_TOP_K=8

# 缓存 TTL (秒)
CACHE_TTL_GAME_SESSION=3600
CACHE_TTL_TEMPLATE=1800
CACHE_TTL_DIALOGUE=300
```

#### 生产环境 (.env.prod) — 额外配置

```env
# MinIO 对象存储
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_SECURE=false
MINIO_BUCKET=dreamweaver-assets
MINIO_PUBLIC_URL=http://<server-ip>/minio/dreamweaver-assets

# 文件上传限制 (MB)
UPLOAD_MAX_IMAGE_MB=5
UPLOAD_MAX_AUDIO_MB=20

# JWT 认证
JWT_SECRET_KEY=<your-secret-key>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
```
