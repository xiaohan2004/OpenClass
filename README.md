<div align="center">
  <img src="assets/openclass-icon-readme-small.png" alt="OpenClass 图标" width="200" />
  <h1>OpenClass</h1>
  <p>
    OpenClass 是一个课堂模拟学生提问助手，用于在课堂进行中接收教师讲课转录，
    结合上下文生成模拟学生提问、课堂摘要、关键词、知识点、小测题和课后报告。
    项目包含 FastAPI 后端、Vue 3 前端以及 Tauri 桌面端封装。
  </p>
</div>

## 功能特性

- 课程与课堂管理：创建课程、创建课堂，并按课堂组织转录、问题和报告数据。
- 实时课堂转录：通过 WebSocket 接收课堂文本流，并在前端实时展示。
- 模拟学生提问：根据近期讲课内容和历史摘要生成问题队列，支持手动触发提问。
- 课堂学习辅助：生成阶段摘要、关键词、知识点和课堂小测。
- 课后报告：基于课堂材料生成结构化 HTML 报告，并通过 Playwright/Chromium 生成 PDF 版本；如果 PDF 导出失败，会保留 HTML 文件作为降级产物。
- 数据与统计：记录会话、转录、问题、模型调用日志和基础统计数据。
- 桌面端入口：通过 Tauri 将前端封装为 Windows 桌面窗口。

## 项目结构

```text
.
├── backend/              # FastAPI 后端服务
│   ├── app/
│   │   ├── api/          # REST 与 WebSocket 路由
│   │   ├── core/         # 提问、摘要、关键词、小测、报告等核心逻辑
│   │   ├── db/           # SQLModel 数据模型、会话与 CRUD
│   │   ├── services/     # LLM、ASR、TTS、指标服务
│   │   └── utils/        # 时间、队列、用量统计等工具
│   ├── data/             # 本地 SQLite 数据目录
│   ├── tests/            # unittest 测试
│   └── requirements.txt  # Python 依赖
├── frontend/             # Vue 3 + Vite 前端
├── tauri/                # Tauri 桌面端壳
├── scripts/              # 桌面启动、批处理与压测脚本
├── assets/               # README 图标与项目截图
└── OpenClass-Desktop.cmd # Windows 桌面端一键启动脚本
```

## 环境要求

- Python 3.10+
- Node.js 与 npm
- Rust 1.87.0+ 与 Cargo（桌面端运行/构建需要）
- Chromium Playwright 浏览器依赖（PDF 生成需要）

## 安装依赖

安装后端依赖：

```bash
python -m pip install -r backend/requirements.txt
python -m playwright install chromium
```

安装前端依赖：

```bash
cd frontend
npm install
```

如需运行或构建桌面端，还需要安装 Tauri 目录依赖：

```bash
cd tauri
npm install
```

## 配置说明

运行配置建议优先通过前端“设置”界面修改。应用启动时会初始化数据库，并通过设置接口读写配置；`backend/app/config_defaults.py` 主要用于提供首次初始化和配置缺失时的默认值，不建议在日常使用中直接修改该文件来调整运行参数。

主要配置项包括：

- LLM 配置：`deepseek_api_key`、`deepseek_base_url`、`model_name`、`max_tokens`、`temperature`。
- ASR/TTS 配置：`qwen_api_key`、`asr_*`、`tts_*`，用于语音识别和语音合成相关能力。
- 数据库配置：`database_url`，默认使用 `sqlite:///backend/data/openclass.db`。
- 课堂参数：最大问题数、提问并发数、近期课堂窗口、历史摘要窗口等。
- 提示词配置：模拟提问、问题质量评估、阶段摘要、关键词、知识点、小测题和课后报告等系统提示词。

桌面端前端连接后端时读取 `frontend/.env.tauri`：

```env
VITE_API_BASE=http://127.0.0.1:8000
VITE_WS_BASE=ws://127.0.0.1:8000
```

其中 `VITE_API_BASE` 是 REST API 地址，`VITE_WS_BASE` 是 WebSocket 地址。敏感配置不要提交到 Git 仓库。

## 本地运行

### 方式一：分别启动后端和前端，使用浏览器访问

先启动后端：

```bash
cd backend
python -m app.main
```

也可以使用 Uvicorn 启动：

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

两种后端启动方式运行的是同一个 FastAPI 应用，接口效果基本一致。
- `python -m app.main` 会执行 `app/main.py` 中的 `uvicorn.run(...)`，不带热重载，适合普通启动或快速验证
- `uvicorn app.main:app --reload ...` 由 Uvicorn 直接导入 `app.main:app`，带热重载，代码修改后会自动重启，更适合开发调试。

然后启动前端：

```bash
cd frontend
npm run dev
```

启动完成后，在浏览器中打开 Vite 输出的本地地址即可使用。后端默认运行在 `http://127.0.0.1:8000`。

### 方式二：运行桌面端一键脚本

Windows 下在仓库根目录运行：

```bat
OpenClass-Desktop.cmd
```

脚本会按顺序完成以下操作：

1. 检查 Node.js、npm、Python、Rust、Cargo 是否可用，并检查 Python 与 Rust 版本。
2. 检查 `frontend/node_modules`、`tauri/node_modules` 和后端 Python 依赖；如果缺失，会询问是否安装。
3. 请求 `http://127.0.0.1:8000/health` 检查 FastAPI 后端是否已经运行；如果未运行，会打开独立 PowerShell 窗口启动后端，并等待后端就绪。
4. 检查桌面端可执行文件是否存在；如果 `tauri/src-tauri/target/release/openclass-desktop.exe` 不存在，会先执行 Tauri 构建。
5. 打开 OpenClass 桌面窗口。

## 脚本

- `OpenClass-Desktop.cmd`：Windows 一键启动桌面端（包括前后端）。
- `scripts/desktop/start-openclass.ps1`：一键启动主脚本，负责依赖检查、后端健康检查、后端启动和桌面端启动调度。
- `scripts/desktop/start-backend.ps1`：检查后端 Python 环境，并启动 FastAPI 服务。
- `scripts/desktop/start-frontend.ps1`：检查前端与 Tauri 环境，默认构建缺失的 release exe 并打开桌面窗口；传入 `-Dev` 时运行 Tauri 开发模式。
- `scripts/batch_classroom_runner.py`：批量课堂处理脚本。
- `scripts/locustfile.py`：Locust 压测脚本。
- `scripts/transcribe_videos_dashscope.py`：基于 DashScope 的视频转录脚本。

## 项目截图

<table>
  <tr>
    <td align="center">
      <img src="assets/项目截图 (1).png" alt="课堂主界面" width="420" />
      <br />
      <strong>课堂主界面</strong>
    </td>
    <td align="center">
      <img src="assets/项目截图 (2).png" alt="问题队列" width="420" />
      <br />
      <strong>问题队列</strong>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="assets/项目截图 (3).png" alt="课堂转录" width="420" />
      <br />
      <strong>课堂小测</strong>
    </td>
    <td align="center">
      <img src="assets/项目截图 (4).png" alt="课堂小测" width="420" />
      <br />
      <strong>统计页面</strong>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="assets/项目截图 (5).png" alt="课程管理" width="420" />
      <br />
      <strong>外部服务请求日志</strong>
    </td>
    <td align="center">
      <img src="assets/项目截图 (6).png" alt="课堂数据" width="420" />
      <br />
      <strong>课程课堂数据</strong>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="assets/项目截图 (7).png" alt="设置页面" width="420" />
      <br />
      <strong>设置页面</strong>
    </td>
    <td align="center">
      <img src="assets/项目截图 (8).png" alt="统计与日志" width="420" />
      <br />
      <strong>日志详情</strong>
    </td>
  </tr>
</table>
