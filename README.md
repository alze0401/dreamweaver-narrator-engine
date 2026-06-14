# 织梦绮谭 — AI 驱动的 Galgame 叙事引擎

> **DreamWeaver / Narrator Engine** — 让 AI 成为即兴演员 + 地下城主，玩家的每一个选择都在塑造独一无二的故事。

## 项目简介

织梦绮谭是一个以 AI 大模型（DeepSeek v4-pro）为核心驱动力的 Galgame 文字冒险引擎。玩家在预设或自定义的世界观中与性格各异的角色互动，通过**选项分支 + 自由对话**的混合模式推进剧情。引擎追踪五维好感度变化、维护三层记忆架构、管理角色名字渐进揭示，从而生成连贯且具有个性化的叙事体验。

**核心理念**：不是"用 AI 替代编剧"，而是"让 AI 成为即兴演员 + 地下城主 (DM)"——它在世界观和人设的框架内即兴发挥，玩家的每一个选择都在塑造独一无二的故事。

## 核心特性

- **AI 实时叙事** — DeepSeek v4-pro 大模型实时生成剧情、对话、选项，每局游戏独一无二
- **结构化输出** — Pydantic 模型 + LangChain `with_structured_output`，确保 LLM 输出严格符合预定义 schema
- **五维好感度系统** — intimacy / trust / respect / curiosity / fear，精细追踪角色关系变化
- **三层记忆架构** — 工作记忆（12轮对话）+ 情景记忆（场景摘要）+ 语义记忆（ChromaDB 向量检索），保证长期连贯性
- **渐进式名字揭示** — 角色初始显示为 `???`，在剧情中自然自我介绍后才揭示真名
- **14 套角色原型** — 傲娇、元气、病娇、中二、大和抚子、剑客、狐仙等经典 Galgame 角色类型
- **12 套世界观模板** — 仙侠、西幻、赛博朋克、星际探索、异世界、妖怪、侦探等多种题材
- **8 套剧本模板** — 宿命邂逅、禁忌之恋、宫廷阴谋、校园祭典、轮回世界等
- **选项 + 自由输入** — 混合交互模式，玩家可选择 AI 提供的选项，也可自由输入
- **用户系统** — JWT 注册/登录，懒登录弹窗，个人资料管理
- **模板管理** — 查看/创建/编辑/克隆自定义模板，AI 辅助生成模板内容
- **MinIO 对象存储** — 头像/立绘/背景/BGM 上传，S3 兼容协议，公开读 + Nginx 代理
- **打字机效果** — 逐字显示的沉浸式文字渲染
- **全局 BGM** — 跨页面持续播放，支持自定义 BGM 上传
- **自动存档** — 每 3 轮自动存档，20 个手动存档位
- **LangGraph 工作流** — `build_prompt → call_llm → parse_response` 三节点管线，含重试与降级
- **Docker 部署** — Docker Compose 一键部署（backend + MySQL + Redis + MinIO），Nginx 反向代理

## 技术栈

```
┌────────────────────────────────────────────────────────┐
│  Frontend (SPA)                                        │
│  React 18 · TypeScript 5.4 · Vite 5.2                  │
│  TailwindCSS 3.4 · Recharts 3.8 · Zustand 4.5          │
└───────────────────────┬────────────────────────────────┘
                        │ REST API (JSON) + JWT
┌───────────────────────▼────────────────────────────────┐
│  Backend (API Server)                                   │
│  Python 3.12 · FastAPI · Uvicorn (异步)                │
│  SQLAlchemy 2.0 async · LangChain · LangGraph          │
│  Pydantic 结构化输出 · JWT (bcrypt) · MinIO            │
│  Jinja2 模板引擎 · Redis 缓存                          │
└───────────────────────┬────────────────────────────────┘
                        │
┌───────────────────────▼────────────────────────────────┐
│  Data Layer                                             │
│  MySQL 8.0 · Redis 7 · ChromaDB · MinIO (S3)           │
└────────────────────────────────────────────────────────┘
```

## 项目结构

```
project_code/
├── docker-compose.yml            # Docker Compose 部署 (4 服务)
├── nginx/                        # Nginx 反向代理配置
│
├── templates/                    # 预设游戏内容 (JSON)
│   ├── worlds/                   #   12 套世界观模板
│   ├── characters/               #   14 套角色原型
│   └── scenarios/                #   8 套剧本模板
│
├── backend/
│   ├── Dockerfile                # Docker 镜像 (Python 3.12)
│   ├── .env.prod                 # 生产环境配置
│   ├── run.py                    # 启动脚本 (uvicorn)
│   ├── requirements.txt          # Python 依赖
│   ├── sql/
│   │   └── init.sql              # MySQL 初始化 + 种子数据
│   ├── prompts/                  # Jinja2 Prompt 模板
│   │   ├── system_prompt.j2      #   主系统提示词
│   │   ├── memory_extract.j2     #   记忆提取提示词
│   │   └── affection_eval.j2     #   好感度评估提示词
│   └── app/                      # 应用源码
│       ├── main.py               #   FastAPI 入口 (9 个 Router)
│       ├── config.py             #   Pydantic Settings
│       ├── auth.py               #   JWT 认证 (bcrypt + Token)
│       ├── storage.py            #   MinIO 存储服务
│       ├── database.py           #   SQLAlchemy async + 自动迁移
│       ├── cache.py              #   RedisCache 单例
│       ├── api/                  #   9 个 API Router
│       │   ├── auth.py           #     认证 (注册/登录/资料)
│       │   ├── game.py           #     游戏流程
│       │   ├── template.py       #     模板管理 + AI 生成
│       │   ├── settings.py       #     游戏设置
│       │   ├── upload.py         #     文件上传
│       │   └── ...               #     character/category/save/dialogue
│       ├── engine/               #   核心叙事引擎
│       │   ├── narrator.py       #     调度中心
│       │   ├── narrator_graph.py #     LangGraph 工作流
│       │   ├── prompt_builder.py #     Prompt 动态组装
│       │   ├── affection.py      #     五维好感度计算器
│       │   └── memory.py         #     三层记忆管理器
│       ├── llm/                  #   LLM 适配层
│       │   ├── deepseek.py       #     DeepSeek v4-pro (thinking mode)
│       │   ├── narrator_schemas.py#    结构化输出 Pydantic 模型
│       │   └── response_parser.py#     4策略 JSON 解析 + 安全网
│       ├── models/               #   ORM 模型 (12 张表)
│       └── schemas/              #   Pydantic DTO
│
└── frontend/
    ├── src/
    │   ├── pages/                # 8 个页面
    │   │   ├── Home.tsx          #   主菜单 (粒子动效)
    │   │   ├── Login.tsx         #   登录/注册
    │   │   ├── TemplateSelect.tsx#   5 步向导
    │   │   ├── Game.tsx          #   核心游戏
    │   │   ├── SaveLoad.tsx      #   存档管理
    │   │   ├── TemplateManage.tsx#   模板管理
    │   │   ├── Settings.tsx      #   游戏设置
    │   │   └── Profile.tsx       #   个人资料
    │   ├── components/           # 12 个组件
    │   │   ├── DialogueBox.tsx   #   消息渲染 (4种类型)
    │   │   ├── ChoicePanel.tsx   #   选项卡片 (交错动画)
    │   │   ├── CharacterCard.tsx #   角色卡 + 雷达图
    │   │   ├── AuthModal.tsx     #   懒登录弹窗
    │   │   ├── GlobalBgm.tsx     #   全局 BGM 播放器
    │   │   ├── TemplateForm.tsx  #   模板创建/编辑
    │   │   └── SidePanel.tsx     #   侧栏面板
    │   ├── stores/               # 4 个 Zustand Store
    │   │   ├── gameStore.ts      #   游戏状态
    │   │   ├── uiStore.ts        #   UI 状态
    │   │   ├── authStore.ts      #   认证状态
    │   │   └── bgmStore.ts       #   BGM 播放
    │   ├── hooks/                # useTypewriter 等
    │   ├── services/             # API 客户端
    │   └── types/                # TypeScript 类型
    └── vite.config.ts
```

## 快速开始

### 方式一：Docker Compose 部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/alze0401/dreamweaver-narrator-engine.git
cd dreamweaver-narrator-engine

# 2. 配置环境变量
cp backend/.env.example backend/.env.prod
# 编辑 backend/.env.prod，填入 DeepSeek API Key

# 3. 构建前端
cd frontend
npm install
npm run build
cd ..

# 4. 启动所有服务
docker-compose up -d

# 5. 配置 Nginx（将 nginx/dreamweaver.conf 复制到 Nginx 配置目录）
# 重启 Nginx 后访问 http://<server-ip>
```

### 方式二：本地开发

**前置条件**：Python 3.12+, Node.js 18+, MySQL 8.0+, Redis 5.0+, DeepSeek API Key

```bash
git clone https://github.com/alze0401/dreamweaver-narrator-engine.git
cd dreamweaver-narrator-engine

# 后端
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入 DeepSeek API Key 和数据库密码

mysql -u root -p -e "CREATE DATABASE narrator_engine CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p narrator_engine < sql/init.sql
python run.py
# 后端运行在 http://localhost:8000 (Swagger: http://localhost:8000/docs)

# 前端
cd frontend
npm install
npm run dev
# 前端运行在 http://localhost:5173
```

## API 概览

| 方法      | 路径                         | 说明         |
| --------- | ---------------------------- | ------------ |
| POST      | `/api/auth/register`         | 用户注册     |
| POST      | `/api/auth/login`            | 用户登录     |
| POST      | `/api/game/start`            | 开始新游戏   |
| POST      | `/api/game/{id}/advance`     | 推进剧情     |
| GET       | `/api/game/{id}/state`       | 获取游戏状态 |
| GET       | `/api/game/{id}/characters`  | 获取角色列表 |
| GET/POST  | `/api/templates`             | 模板管理     |
| POST      | `/api/templates/ai-generate` | AI 生成模板  |
| GET/PATCH | `/api/settings/`             | 游戏设置     |
| POST      | `/api/upload/avatar`         | 上传头像     |
| POST      | `/api/upload/character`      | 上传角色立绘 |
| GET/POST  | `/api/saves`                 | 存档管理     |
| GET       | `/api/dialogue/{id}/history` | 对话历史     |

完整 API 文档启动后端后访问 `http://localhost:8000/docs`（Swagger UI）。

## 架构设计

叙事生成通过 **LangGraph StateGraph** 编排为三节点管线：

```
[build_prompt] → [call_llm] → [parse_response]
  组装 Prompt       调用 DeepSeek v4-pro    JSON 解析 + 安全网
  + 对话历史        结构化输出优先            反填充 + JSON泄漏清洗
  + 记忆上下文      function_calling         空选项兜底
  + 自然语言记忆    → json_mode 降级         narration 非空保证
                   空响应重试×3
```

详细的系统架构设计请参阅 [`galgame-ai-architecture.md`](./galgame-ai-architecture.md)。

## License

MIT License
