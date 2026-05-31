# 基于 AI Agent 的泵站能效优化调度系统



> 智慧水利应用 — 结合大模型的泵站能效优化与智能调度平台



**GitHub 仓库**：<https://github.com/wandou12123/AI-Agent-Based-Eco-Efficient-Pump-Scheduling-System>



## 技术栈



| 层级 | 技术 |

|------|------|

| 前端 | Vue 3 + Vite + Element Plus + ECharts + Pinia |

| 后端 | Python FastAPI + SQLAlchemy (async) + Uvicorn |

| 数据库 | MySQL 8+ |

| 队列 | Redis + Celery（可选，Docker 部署默认启用） |

| 大模型 | Anthropic Claude（兼容 OpenAI 格式的第三方 API） |

| AI Agent | 多角色编排 + 工具调用（调度员 / 能效分析 / 安全校验 / 文书分析） |



## 目录结构



```

AI-Agent-Based-Eco-Efficient-Pump-Scheduling-System/

├── backend/                # Python 后端

│   ├── main.py             # FastAPI 入口

│   ├── Dockerfile

│   ├── app/

│   │   ├── api/            # 路由层

│   │   ├── agents/         # orchestrator + tool_agent

│   │   ├── core/           # config, security, middleware, response

│   │   ├── services/       # optimization, schedule_pipeline, audit

│   │   ├── worker/         # Celery 异步任务

│   │   └── prompts/

│   └── tests/              # 单元测试

├── frontend/               # Vue 3 前端

├── docker-compose.yml      # 一键部署（MySQL + Redis + Backend + Celery + Frontend）

├── .github/workflows/ci.yml

└── sql/init.sql

```



## 快速开始



### 方式一：Docker Compose（推荐）



```bash

# 在项目根目录，可选设置 LLM API Key

export LLM_API_KEY=sk-your-key



docker compose up -d --build

# 访问 http://localhost:5173  后端 http://localhost:8000

# 默认账号 admin / admin123

```



### 方式二：本地开发



```bash

# 1. 数据库

mysql -u root -p < sql/init.sql



# 2. 后端

cd backend

cp .env.example .env

pip install -r requirements.txt

python main.py



# 3. （可选）Celery Worker

celery -A app.worker.celery_app worker --loglevel=info



# 4. 前端

cd frontend && npm install && npm run dev

```



## 环境变量



| 变量 | 说明 | 默认 |

|------|------|------|

| `LLM_API_KEY` | 大模型 API 密钥 | — |

| `USE_CELERY` | 是否启用 Celery 异步优化 | `false` |

| `REDIS_URL` | Redis 连接 | `redis://127.0.0.1:6379/0` |

| `CELERY_BROKER_URL` | Celery Broker | `redis://127.0.0.1:6379/1` |



## 主要功能



- **智能对话** — SSE 流式回复 + 多 Agent 工具调用（`/chat/tool`）

- **文书分析** — `.docx` 问答 / 参数提取 / **一键创建调度任务**

- **调度优化** — 贪心算法 + LLM 解释 + 安全校验；支持 Celery 异步队列

- **统一 API** — 成功 `{ success, data }` / 错误 `{ success, error: { code, message } }`

- **RBAC** — admin/operator 可写，viewer 只读

- **审计日志** — 关键写操作落库



## 测试



```bash

cd backend && pytest tests/ -v

```



## 团队



| 姓名 | 学号 | 职责 |

|------|------|------|

| 王焓栋（组长） | 2023b49038 | 后端核心、AI Agent、系统架构 |

| 郑坚 | 2023b49053 | 后端辅助、数据库、调度算法 |

| 金南帆 | 2023b49054 | 前端开发 |

| 王俊杰 | 2023b49058 | 文档撰写 |



## License



MIT — 见 [LICENSE](LICENSE)。

