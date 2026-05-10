# Repository Guidelines

## 项目结构与模块组织
本仓库以 `backend/` 为主，包含 FastAPI 服务与核心逻辑。主要路径如下：
- `backend/app/`：应用入口与业务模块（`api/`、`core/`、`services/`、`db/`、`utils/`）。
- `backend/tests/`：单元测试与测试运行脚本。
- `data/`：本地数据占位目录（如需要可写入运行期数据）。
- `frontend/`、`tauri/`：前端与桌面端占位目录，目前为空。
- `scripts/`：一次性脚本或运维脚本占位。

## 构建、测试与本地运行
后端依赖位于 `backend/requirements.txt`：
```bash
pip install -r backend/requirements.txt
python -m playwright install chromium
```
本地启动（任一方式即可）：
```bash
python backend/app/main.py
# 或
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
运行全部测试：
```bash
python backend/tests/run_tests.py
```
单个测试文件可直接运行，例如：
```bash
python backend/tests/test_api.py
```

## 编码风格与命名约定
使用 Python 风格约定（4 空格缩进、`snake_case` 变量/函数、`PascalCase` 类名）。当前未配置自动格式化或 lint 工具；请确保新增代码符合 PEP8，可读性优先。

## 测试规范
测试基于 `unittest`，文件命名为 `test_*.py`，测试类以 `Test` 开头。新增功能需配套新增/更新测试，优先覆盖核心业务与 API 行为。

## 提交与 Pull Request 规范
提交信息遵循 `type: 描述` 形式，常见类型包括 `feat`、`docs`、`chore`、`style`、`test`。PR 需包含清晰描述、关键改动点与相关测试结果；涉及接口变化请附示例请求/响应。

## 配置与安全
运行前请参考 `backend/.env.example` 创建 `backend/.env`，配置模型相关的密钥与地址（如 `deepseek_api_key`）。不要提交任何真实密钥或敏感配置。

## Agent 指令
本仓库要求所有自动化或协作型回复使用中文输出。
