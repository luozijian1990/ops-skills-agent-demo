# Claude Agent Web Service — DeepAgents 进阶版

基于 **FastAPI + Vue 3 + DeepAgents** 构建的 Web 对话 Agent。已支持完整的长时记忆对话上下文、多组件 UI 及基于 Markdown 零代码的 Skill 加载能力。

## ✨ 核心特性

- **DeepAgents & LangGraph**：底层抛弃基础调用，转用 LangGraph 架构，原生支持复杂 Agent 循环并提供安全的 LocalShellBackend。
- **打字机流式输出 (Streaming)**：真正的逐 Token 细粒度推流（通过 WebSocket），前端实时回显思考及回答过程。
- **全自动零代码技能 (Skills)**：后端取消硬编码，仅需丢入 Markdown 技能描述（`backend/skills/`），Agent 热插拔即可拥有系统级能力。
- **原生上下文记忆**：集成 `MemorySaver`，数据库与图状态协同，真正记住你在历史会话里聊了什么。
- **持久化存储 (PostgreSQL)**：彻底从内存切到数据库，持久化你的全部对话列表与消息，前端随时加载漫游。
- **高颜值纯享 UI**：分离左右双侧边栏（会话列表与动态技能表），黑暗/明亮模式无缝切换，参数结果代码块高亮。

## 🚀 快速开始

### 环境依赖

- Python >= 3.10
- Node.js >= 18
- PostgreSQL >= 14

### 1. 配置数据库与环境变量

```bash
cd backend
cp .env.example .env
# 编辑 .env：填入你的 ANTHROPIC_API_KEY 以及 PostgreSQL 的 DB_USER/DB_PASSWORD
```

### 2. 初始化与启动后端

#### 方法 A：使用 Docker Compose（推荐）

项目根目录提供了 `docker-compose.yml` 文件，可通过容器方式一键启动 PostgreSQL 数据库与后端服务。

```bash
# 在项目根目录执行
docker-compose up -d --build
```

> **提示**：如果使用 Docker 启动，您不需要在本地安装 Python 依赖或配置单独的 PostgreSQL 服务。第一次启动时会自动创建数据库及表结构。
> 后端服务运行在 `http://127.0.0.1:8000`。
> 注意：环境变量文件 `.env` 依然需要配置，特别提供 `ANTHROPIC_API_KEY`。

#### 方法 B：本地环境运行

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 初次运行时，代码中的 init_db 会自动在 PostgreSQL 里创建表格
python main.py
```

> 后端默认运行在 `http://127.0.0.1:8000`

### 3. 配置前端环境变量并构建/启动

在启动前端或者构建 Docker 镜像前往，**必须要设置生产环境变量配置**。

```bash
cd frontend
cp .env.production.example .env.production
# 编辑 .env.production 文件，配置好后端/WebSocket 接口的对应访问地址和端口

# 本地调试启动：
npm install
npm run dev

# 如需构建生产版本：
# npm run build
```

> 前端本地运行默认在 `http://127.0.0.1:5173`

打开浏览器访问，开启你的 Agent 会话。

## 📂 项目结构

```text
demo-agent/
├── backend/                  # FastAPI 核心处理层
│   ├── main.py               # 路由入口与静态挂载
│   ├── agent.py              # Deepagent Graph 定义与流式解析
│   ├── config.py             # 配置模块（含 PostgreSQL, 目录等）
│   ├── AGENTS.md             # ⭐️ 核心 Agent 系统提示词/人设注入
│   ├── api/
│   │   ├── routers/skills.py # Restful 技能查询接口
│   │   └── ws/chat.py        # WebSocket 连接、增量推流分发、数据库写库
│   ├── db/
│   │   ├── session.py        # SQLAlchemy 异步引擎
│   │   └── base_class.py     # Base
│   ├── models/               # ORM 表模型 (Conversation, Message)
│   └── skills/               # ⭐️ Markdown 格式的指令集
│       ├── shell_command.md
│       ├── file_reader.md
│       └── code_explainer.md
└── frontend/                 # Vue 3 前端界面
    ├── index.html
    ├── src/
    │   ├── App.vue           # 布局框架 (左会话、中聊天、右技能)
    │   ├── stores/chat.ts    # 基于 Pinia 的状态流转器 & WebSocket 控制中心
    │   └── components/
    │       ├── MessageBubble.vue     # Markdown 富文本渲染与指令折腾
    │       ├── ConversationList.vue  # 历史会话漫游
    │       └── SkillPanel.vue        # 技能卡片
```

## 🛠️ 关于自定义技能开发

无需修改任意一行 Python 代码，只需在 `backend/skills/` 目录下创建一个新的 `.md` 文件（参照已有的格式，包含 yaml metadata 描述和正文指导即可）。后端会自动装载该 Skill，同时前端右上角 `⚡` 面板会实时展示出你的扩建能力。

> 💡 **快速生成 Skill**：`backend/skills/` 下的所有技能均可通过官方的 **skill-creator** 工具自动生成，只需描述你想要的能力，它就能帮你产出完整的 Skill Markdown 文件。
>
> 👉 [skill-creator — Anthropic 官方技能生成器](https://github.com/anthropics/skills/tree/main/skills/skill-creator)

## 🔌 HTTP API（程序调用）

除了 WebSocket 前端交互之外，项目提供了 **HTTP POST 接口**，供外部程序（告警系统、CI/CD、运维脚本等）直接调用 Agent 并获取最终结果。

### 接口地址

```http
POST http://localhost:8000/api/agent/chat
Content-Type: application/json
```

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `message` | string | ✅ | 用户问题 |
| `conversation_id` | string | ❌ | 会话 ID，传入可继续上下文对话 |
| `skill` | string | ❌ | 指定使用的 Skill 名称 |

### 响应格式

```json
{
  "conversation_id": "uuid",
  "content": "Agent 最终回复（Markdown 文本）",
  "thinking": "Agent 思考过程",
  "tool_calls": [
    {
      "tool_name": "execute",
      "tool_input": {"command": "df -h"},
      "result": "Filesystem  Size  Used  ..."
    }
  ]
}
```

### 调用示例

**单轮调用**：

```bash
curl -X POST http://localhost:8000/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "帮我分析下 10.0.0.1 的磁盘使用情况", "skill": "remote-ops"}'
```

**多轮对话**（传入上一轮返回的 `conversation_id`）：

```bash
curl -X POST http://localhost:8000/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "继续看一下内存", "conversation_id": "上一轮返回的 uuid"}'
```

**Python 调用**：

```python
import requests

resp = requests.post("http://localhost:8000/api/agent/chat", json={
    "message": "SELECT * FROM orders WHERE status='pending' 这条 SQL 为什么慢",
    "skill": "sql-analyzer"
}, timeout=300)

result = resp.json()
print(result["content"])      # 最终分析结果
print(result["tool_calls"])   # 工具调用过程
```

> ⚠️ **超时提示**：Agent 执行可能较耗时（SSH 排查、多轮工具调用），建议客户端设置 **5 分钟超时**。

## 🇨🇳 国产替代：MiniMax-M2.5

如果你没有 Claude API Key 或者希望使用国产大模型，本项目兼容 **MiniMax-M2.5**（海螺 AI）。MiniMax 提供了与 Anthropic 完全兼容的 API 接口，只需修改 `backend/.env` 中的 API 配置即可无缝切换：

```bash
# backend/.env
ANTHROPIC_API_KEY=你的MiniMax_API_Key
ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic
MODEL_NAME=MiniMax-M2.5
```

> 🎁 **新用户福利**：注册并完成实名认证后即可获得 **15 元体验券**，足够深度测试。
>
> 👉 [MiniMax Anthropic 兼容 API 文档](https://platform.minimaxi.com/docs/api-reference/text-anthropic-api)
