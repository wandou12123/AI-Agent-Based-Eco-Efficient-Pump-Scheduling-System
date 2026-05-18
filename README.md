# 基于 AI Agent 的泵站能效优化调度系统

> 智慧水利应用 — 结合大模型的泵站能效优化与智能调度平台

**GitHub 仓库**：<https://github.com/wandou12123/AI-Agent-Based-Eco-Efficient-Pump-Scheduling-System>

```bash
git clone https://github.com/wandou12123/AI-Agent-Based-Eco-Efficient-Pump-Scheduling-System.git
cd AI-Agent-Based-Eco-Efficient-Pump-Scheduling-System
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus + ECharts + Pinia |
| 后端 | Python FastAPI + SQLAlchemy (async) + Uvicorn |
| 数据库 | MySQL 8+ |
| 大模型 | Anthropic Claude（兼容 OpenAI 格式的第三方 API） |
| AI Agent | 多角色编排（调度员 / 能效分析 / 安全校验 / 文书分析） |

## 目录结构

```
AI-Agent-Based-Eco-Efficient-Pump-Scheduling-System/
├── backend/                # Python 后端
│   ├── main.py             # FastAPI 入口 + Uvicorn 启动
│   ├── requirements.txt    # Python 依赖
│   ├── .env.example        # 环境变量模板
│   └── app/
│       ├── api/            # 路由层 (auth, chat, stations, tasks, upload, voice)
│       ├── core/           # 核心配置 (config, database, security)
│       ├── models/         # SQLAlchemy ORM 模型
│       ├── schemas/        # Pydantic 请求/响应模型
│       ├── services/       # 业务服务 (llm_client, optimization, docx_parser)
│       ├── agents/         # AI Agent 编排 (orchestrator)
│       ├── prompts/        # Prompt 模板 (.md)
│       └── utils/          # 工具函数
├── frontend/               # Vue 3 前端
│   ├── src/
│   │   ├── api/            # Axios 封装 + 接口定义
│   │   ├── views/          # 页面 (Chat, Schedule, Station, Config, Login)
│   │   ├── router/         # Vue Router
│   │   └── stores/         # Pinia 状态管理
│   ├── package.json
│   └── vite.config.ts
├── sql/
│   └── init.sql            # 数据库初始化脚本 (9 张表)
└── scripts/
    └── md_to_docx.py       # 详设 Markdown 转 Word（可选）
```

> 课程报告（选题/需求/概要/详设/进度报告等）存放在仓库外的 `docs/` 目录，不随本仓库提交。

## 快速开始

### 1. 数据库

```bash
mysql -u root -p < sql/init.sql
```

### 2. 后端

```bash
cd backend
cp .env.example .env       # 编辑 .env 填写 API Key、MySQL 密码等
pip install -r requirements.txt
python main.py             # http://localhost:8000
```

### 3. 前端

```bash
cd frontend
npm install
npm run dev                # http://localhost:5173
```

## 环境变量说明

| 变量 | 说明 | 示例 |
|------|------|------|
| `LLM_API_BASE_URL` | 大模型 API 地址 | `https://aicode.cat` |
| `LLM_API_KEY` | API 密钥 | `sk-xxx` |
| `LLM_MODEL_NAME` | 模型名称 | `claude-sonnet-4-6` |
| `MYSQL_HOST` | MySQL 地址 | `127.0.0.1` |
| `MYSQL_PORT` | MySQL 端口 | `3306` |
| `MYSQL_USER` | MySQL 用户名 | `root` |
| `MYSQL_PASSWORD` | MySQL 密码 | （自行设置） |
| `MYSQL_DATABASE` | 数据库名 | `pump_station` |
| `JWT_SECRET_KEY` | JWT 签名密钥 | （随机字符串） |

## 主要功能

- **智能对话** — 文本对话与 `.docx` 文书分析，AI 流式回复（SSE）
- **语音输入** — 浏览器 STT + 后端转写回退
- **泵站管理** — 泵站与机组 CRUD、工况数据可视化
- **调度优化** — 贪心优化 + LLM 解释 + 安全校验
- **用户系统** — 注册登录、JWT 鉴权

## 团队

| 姓名 | 学号 | 职责 |
|------|------|------|
| 王焓栋（组长） | 2023b49038 | 后端核心、AI Agent、系统架构、演讲 |
| 郑坚 | 2023b49053 | 后端辅助、数据库、调度算法 |
| 金南帆 | 2023b49054 | 前端开发 |
| 王俊杰 | 2023b49058 | 文档撰写 |

## License

MIT — 见 [LICENSE](LICENSE)。
