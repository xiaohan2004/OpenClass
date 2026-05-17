# OpenClass Tauri 前端

本目录用于把 OpenClass 前端封装成桌面应用窗口。

Tauri 当前只负责桌面壳：

- 加载前端页面。
- 生成可运行的 Windows 桌面 exe。
- 使用 Tauri 配置管理窗口、图标和前端构建产物。

Tauri 不负责启动后端，也不等待后端健康检查。前端需要真实接口时，应确保 FastAPI 后端已经在本机运行。

## 前端连接配置

Tauri 模式下，前端读取 `frontend/.env.tauri`：

```env
VITE_API_BASE=http://127.0.0.1:8000
VITE_WS_BASE=ws://127.0.0.1:8000
```

也就是说：

- REST API 默认请求 `http://127.0.0.1:8000`
- WebSocket 默认连接 `ws://127.0.0.1:8000`

如果后端未运行，桌面窗口仍能打开，但接口和 WebSocket 会失败。

## 开发模式

在 `tauri/` 目录运行：

```powershell
npm run tauri:dev
```

开发模式使用 `tauri.conf.json` 中的配置：

```json
"devUrl": "http://127.0.0.1:5173"
```

Tauri 会加载 Vite 开发服务提供的前端页面。

## 构建桌面 exe

在 `tauri/` 目录运行：

```powershell
npm run tauri:build
```

构建完成后，桌面 exe 位于：

```text
tauri\src-tauri\target\release\openclass-desktop.exe
```

构建模式使用 `tauri.conf.json` 中的配置：

```json
"frontendDist": "../../frontend/dist"
```

也就是加载已经构建好的前端静态文件。

当前 `bundle.active` 为 `false`，因此只生成可运行 exe，不生成 MSI/NSIS 安装包。

## 关键文件

```text
tauri\package.json
tauri\src-tauri\Cargo.toml
tauri\src-tauri\tauri.conf.json
tauri\src-tauri\src\main.rs
```

`main.rs` 当前只启动 Tauri 应用壳：

```rust
fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("failed to run OpenClass desktop");
}
```
