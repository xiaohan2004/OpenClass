# Repository Guidelines

## 项目结构与模块组织

OpenClass 是课堂辅助应用，包含 FastAPI 后端、Vue 3 前端和 Tauri 桌面端。

- `backend/app/`：后端源码。`api/` 放 REST 与 WebSocket 路由，`core/` 放提问、摘要、报告等核心逻辑，`services/` 放模型、ASR、TTS 等外部服务封装，`db/` 放 SQLModel 模型与 CRUD，`utils/` 放通用工具。
- `backend/tests/`：后端测试与测试运行脚本。
- `frontend/src/`：Vue 3 前端源码；`frontend/public/` 放公开静态资源。
- `tauri/src-tauri/`：Tauri 桌面端配置与 Rust 侧代码。
- `assets/`：项目图标、README 图片等视觉资源。
- `scripts/`：桌面启动、批处理、转写和压测脚本。

## 构建、测试与开发命令

安装后端依赖：

```bash
python -m pip install -r backend/requirements.txt
python -m playwright install chromium
```

启动后端：

```bash
cd backend
python -m app.main
# 或
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动前端开发服务器：

```bash
cd frontend
npm install
npm run dev
```

构建前端：

```bash
cd frontend
npm run build
```

运行或构建桌面端：

```bash
cd tauri
npm install
npm run tauri:dev
npm run tauri:build
```

Windows 下也可在仓库根目录运行 `OpenClass-Desktop.cmd`，脚本会检查依赖并启动桌面应用。

运行后端测试：

```bash
python backend/tests/run_tests.py
```

## 编码风格与命名约定

Python 代码遵循 PEP 8：使用 4 空格缩进，函数和变量使用 `snake_case`，类名使用 `PascalCase`。后端改动应贴合现有模块边界，避免把 API、业务逻辑、数据库访问混在同一层。Vue 代码保持 `frontend/src/` 现有组件组织方式。仓库未配置统一 formatter，提交前请与邻近代码风格保持一致。

## 测试规范

后端测试使用 `unittest`。测试文件命名为 `test_*.py`，测试类以 `Test` 开头。新增核心业务、API 行为或回归修复时，应补充对应测试。优先写靠近变更点的聚焦测试，再按风险增加集成覆盖。

## 提交与 Pull Request 规范

提交信息沿用 `type(scope): 描述` 或 `type: 描述`，例如 `feat(backend): 支持桌面前端跨域访问`。常用类型包括 `feat`、`fix`、`docs`、`test`、`style`、`chore`。

PR 应包含清晰摘要、关键改动、测试结果和相关 issue。涉及 UI 的改动请附截图；涉及 API 的改动请附示例请求和响应。

## 配置与安全

不要提交真实 API Key、模型凭据、本地数据库或生成的密钥。敏感值应放在本地环境或运行时配置中。桌面前端连接后端时读取 `frontend/.env.tauri`，常见配置包括 `VITE_API_BASE` 和 `VITE_WS_BASE`。

## Agent 指令

自动化协作者应使用中文回复仓库用户。创建或修改 Codex skill 时，`SKILL.md` frontmatter 和 `agents/openai.yaml` 使用英文，`SKILL.md` 正文使用中文。`/init` 生成或更新 `AGENTS.md` 时，默认使用中文撰写文档内容。
