# 基于 AI Agent 的泵站能效优化调度系统

> 智慧水利应用 — 结合大模型的泵站能效优化与智能调度平台

**GitHub 仓库**：<https://github.com/wandou12123/AI-Agent-Based-Eco-Efficient-Pump-Scheduling-System>

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus + ECharts + Pinia |
| 后端 | Python FastAPI + SQLAlchemy (async) + Uvicorn |
| 数据库 | MySQL 8+ |
| 队列 | Redis + Celery（Docker 部署默认启用） |
| 大模型 | 兼容 OpenAI 格式的 HTTP API |
| AI Agent | 多角色编排 + 工具调用 |

## 快速开始

### 方式一：Docker Compose（答辩演示推荐）

```bash
export LLM_API_KEY=sk-your-key   # Windows: set LLM_API_KEY=...
docker compose up -d --build
# 前端 http://localhost:5173  后端 http://localhost:8000
# 默认演示账号 admin / admin123（需先 seed，见下）
docker compose exec backend python scripts/seed_data.py
```

服务包含：**MySQL + Redis + Backend + Celery Worker + Frontend**。`USE_CELERY=true` 时调度页可切换异步优化。

### 方式二：本地开发

```bash
mysql -u root -p < sql/init.sql
cd backend && cp .env.example .env && pip install -r requirements.txt
python scripts/seed_data.py    # 3 座演示泵站 + 机组/工况 + admin/operator/viewer 账号（改 seed 后需重新执行）
python main.py                 # http://localhost:8000
cd ../frontend && npm install && npm run dev
```

本地默认 `USE_CELERY=false`；需异步时启动 Redis 并运行：

```bash
celery -A app.worker.celery_app worker --loglevel=info
```

## 演示账号（seed 后）

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员 |
| operator | operator123 | 操作员 |
| viewer | viewer123 | 只读 |

## 主要功能

- 智能对话（SSE）+ 工具 Agent（查泵站/建任务/一键创建并优化）
- 文书 `.docx` 分析 / 参数提取 / 一键创建调度任务
- 调度优化（贪心 + LLM 解释 + 安全校验 + 方案图表）
- 统一 API：`{ success, data }` / `{ success, error: { code, message } }`
- RBAC、审计日志、LLM 降级、request_id 访问日志

## 测试

```bash
cd backend && pytest tests/ -v
```

CI：`.github/workflows/ci.yml`（push 到 main 自动跑 pytest + 前端 build）

## 文档（仓库外 `Agent/docs/`）

- 详设活文档 v1.2：`智慧水利应用_详细设计报告_v1.1.md`
- 进度报告：第 1/2/3 周 md
- 验收：`AC验收记录.md`

## 团队

| 姓名 | 学号 | 职责 |
|------|------|------|
| 王焓栋 | 2023b49038 | 后端、Agent、架构 |
| 郑坚 | 2023b49053 | 数据库、算法、测试 |
| 金南帆 | 2023b49054 | 前端 |
| 王俊杰 | 2023b49058 | 文档 |

MIT — 见 [LICENSE](LICENSE).
