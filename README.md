# 织梦绮谭 — AI 驱动的 Galgame 叙事引擎

> **DreamWeaver / Narrator Engine** — 让 AI 成为即兴演员 + 地下城主，玩家的每一个选择都在塑造独一无二的故事。

## 项目简介

织梦绮谭是一个以 AI 大模型（DeepSeek）为核心驱动力的 Galgame 文字冒险引擎。玩家在预设或自定义的世界观中与性格各异的角色互动，通过**选项分支 + 自由对话**的混合模式推进剧情。引擎追踪五维好感度变化、维护三层记忆架构、管理角色名字渐进揭示，从而生成连贯且具有个性化的叙事体验。

**核心理念**：不是"用 AI 替代编剧"，而是"让 AI 成为即兴演员 + 地下城主 (DM)"——它在世界观和人设的框架内即兴发挥，玩家的每一个选择都在塑造独一无二的故事。

## 核心特性

- **AI 实时叙事** — DeepSeek 大模型实时生成剧情、对话、选项，每局游戏独一无二
- **五维好感度系统** — intimacy / trust / respect / curiosity / fear，精细追踪角色关系变化
- **三层记忆架构** — 工作记忆（12轮对话）+ 情景记忆（场景摘要）+ 语义记忆（ChromaDB 向量检索），保证长期连贯性
- **渐进式名字揭示** — 角色初始显示为 `???`，在剧情中自然自我介绍后才揭示真名
- **12 套角色原型** — 傲娇、元气、病娇、中二、大和抚子等经典 Galgame 角色类型
- **9 套世界观模板** — 仙侠、西幻、赛博朋克、星际探索、异世界等多种题材
- **选项 + 自由输入** — 混合交互模式，玩家可选择 AI 提供的选项，也可自由输入
- **打字机效果** — 逐字显示的沉浸式文字渲染
- **自动存档** — 每 3 轮自动存档，20 个手动存档位
- **LangGraph 工作流** — `build_prompt → call_llm → parse_response` 三节点管线，含重试与降级

## 技术栈

```
┌────────────────────────────────────────────────────────┐
│  Frontend (SPA)                                        │
│  React 18 · TypeScript 5.4 · Vite 5.2                  │
│  TailwindCSS 3.4 · Recharts 3.8 · Zustand 4.5          │
└───────────────────────┬────────────────────────────────┘
                        │ REST API (JSON)
┌───────────────────────▼────────────────────────────────┐
│  Backend (API Server)                                   │
│  Python 3.12 · FastAPI · Uvicorn (异步)                │
│  SQLAlchemy 2.0 async · LangChain · LangGraph          │
│  Jinja2 模板引擎 · Redis 缓存                          │
└───────────────────────┬────────────────────────────────┘
                        │
┌───────────────────────▼────────────────────────────────┐
│  Data Layer                                             │
│  MySQL (aiomysql) · Redis · ChromaDB (向量索引)         │
└────────────────────────────────────────────────────────┘
```

## 项目结构

```
project_code/
├── templates/                  # 预设游戏内容 (JSON)
│   ├── worlds/                 #   9 套世界观模板
│   ├── characters/             #   12 套角色原型
│   └── scenarios/              #   8 套剧本模板
│
├── backend/
│   ├── run.py                  # 启动脚本 (uvicorn)
│   ├── requirements.txt        # Python 依赖
│   ├── .env.example            # 环境变量示例
│   ├── sql/
│   │   └── init.sql            # MySQL 初始化 + 种子数据
│   ├── prompts/                # Jinja2 Prompt 模板
│   │   ├── system_prompt.j2    #   主系统提示词
│   │   ├── memory_extract.j2   #   记忆提取提示词
│   │   └── affection_eval.j2   #   好感度评估提示词
│   └── app/                    # 应用源码
│       ├── main.py             #   FastAPI 入口
│       ├── config.py           #   Pydantic Settings
│       ├── database.py         #   SQLAlchemy async + 自动迁移
│       ├── cache.py            #   RedisCache 单例
│       ├── api/                #   6 个 API Router
│       ├── engine/             #   核心叙事引擎
│       │   ├── narrator.py     #     调度中心
│       │   ├── narrator_graph.py#    LangGraph 工作流
│       │   ├── prompt_builder.py#    Prompt 动态组装
│       │   ├── affection.py    #     五维好感度计算器
│       │   └── memory.py       #     三层记忆管理器
│       ├── llm/                #   LLM 适配层 (DeepSeek)
│       ├── models/             #   ORM 模型 (11 张表)
│       └── schemas/            #   Pydantic DTO
│
└── frontend/
    ├── src/
    │   ├── pages/              # 4 个页面
    │   │   ├── Home.tsx        #   主菜单 (粒子动效)
    │   │   ├── TemplateSelect.tsx# 5 步向导
    │   │   ├── Game.tsx        #   核心游戏
    │   │   └── SaveLoad.tsx    #   存档管理
    │   ├── components/         # 7 个组件
    │   │   ├── DialogueBox.tsx #   消息渲染 (4种类型)
    │   │   ├── ChoicePanel.tsx #   选项卡片 (交错动画)
    │   │   ├── CharacterCard.tsx#  角色卡 + 雷达图
    │   │   └── SidePanel.tsx   #   侧栏面板
    │   ├── stores/             # Zustand 状态管理
    │   ├── hooks/              # useTypewriter 等
    │   ├── services/           # API 客户端
    │   └── types/              # TypeScript 类型
    └── vite.config.ts
```

## 快速开始

### 前置条件

- **Python 3.12+**
- **Node.js 18+**
- **MySQL 8.0+**
- **Redis 5.0+**
- **DeepSeek API Key** — 从 [platform.deepseek.com](https://platform.deepseek.com) 获取

### 1. 克隆项目

```bash
git clone https://github.com/alze0401/dreamweaver-narrator-engine.git
cd dreamweaver-narrator-engine
```

### 2. 后端部署

```bash
# 创建并激活虚拟环境
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 复制并编辑环境变量
cp .env.example .env
# 编辑 .env，填入你的 DeepSeek API Key 和数据库密码

# 创建 MySQL 数据库
mysql -u root -p -e "CREATE DATABASE narrator_engine CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 导入初始化数据（表结构 + 种子数据）
mysql -u root -p narrator_engine < sql/init.sql

# 启动后端服务
python run.py
# 服务运行在 http://localhost:8000
# Swagger 文档: http://localhost:8000/docs
```

### 3. 前端部署

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
# 默认运行在 http://localhost:5173
```

### 4. 开始游戏

1. 打开浏览器访问 `http://localhost:5173`
2. 选择分类 → 世界观 → 剧本 → 角色 → 确认开始
3. 通过选项或自由输入与 AI 互动，体验独一无二的故事

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/game/start` | 开始新游戏 |
| POST | `/api/game/{id}/advance` | 推进剧情 |
| GET | `/api/game/{id}/state` | 获取游戏状态 |
| GET | `/api/game/{id}/characters` | 获取角色列表 |
| GET/POST | `/api/templates` | 模板管理 |
| GET/POST | `/api/saves` | 存档管理 |
| GET | `/api/dialogue/{id}/history` | 对话历史 |

完整 API 文档启动后端后访问 `http://localhost:8000/docs`（Swagger UI）。

## 架构设计

叙事生成通过 **LangGraph StateGraph** 编排为三节点管线：

```
[build_prompt] → [call_llm] → [parse_response]
  组装 Prompt       调用 DeepSeek    JSON 解析 + 兜底
  + 对话历史        JSON mode         结构化验证
  + 记忆上下文      空响应重试×3      narration 生成
```

详细的系统架构设计请参阅 [`galgame-ai-architecture.md`](./galgame-ai-architecture.md)，架构图源文件见 [`architecture-diagram.mermaid`](./architecture-diagram.mermaid)。

## License

MIT License
