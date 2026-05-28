"""
FastAPI 应用入口

环境变量：
    OPENCLASS_OFFLINE=1            - 强制离线模式，跳过模型联网检查，加快启动
    DISABLE_KEYWORD_ALGORITHM=1    - 关闭传统算法提取关键词（仅使用 LLM 路径）
"""

from contextlib import asynccontextmanager
import logging
import os
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

_startup_total = time.perf_counter()

# 检测离线模式
_offline_mode = os.environ.get("OPENCLASS_OFFLINE", "").lower() in ("1", "true", "yes")
# 检测是否关闭传统算法关键词提取
_disable_keyword_algorithm = os.environ.get("DISABLE_KEYWORD_ALGORITHM", "").lower() in ("1", "true", "yes")

# 配置日志（必须在任何业务导入之前，以便所有模块都能使用）
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
logger.info("[启动耗时] === 程序启动开始 ===")
if _offline_mode:
    logger.info("[启动模式] 离线模式已启用 (OPENCLASS_OFFLINE=1)")
if _disable_keyword_algorithm:
    logger.info("[启动模式] 传统算法提取关键词已关闭 (DISABLE_KEYWORD_ALGORITHM=1)")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """应用生命周期，启动时初始化数据库。"""
    logger.info("[启动耗时] --- lifespan 开始 ---")
    init_db()
    preload_runtime_dependencies()
    logger.info("[启动耗时] --- lifespan 初始化完成 ---")
    yield


# 步骤1: 导入 REST router（触发 db/models, db/session, config, all CRUD 等模块）
_step1 = time.perf_counter()
from app.api.routes.rest import router as rest_router  # noqa: E402
logger.info("[启动耗时] 第1步 | rest_router 导入完成 | 耗时=%.3fs | 累计=%.3fs",
            time.perf_counter() - _step1, time.perf_counter() - _startup_total)

# 步骤2: 导入 WebSocket router（触发 core/main_flow → core/keyword → keyword_extraction_algorithm 重量级导入）
_step2 = time.perf_counter()
from app.api.routes.websocket import router as websocket_router  # noqa: E402
from app.core.main_flow import preload_runtime_dependencies  # noqa: E402
logger.info("[启动耗时] 第2步 | websocket_router 导入完成 | 耗时=%.3fs | 累计=%.3fs",
            time.perf_counter() - _step2, time.perf_counter() - _startup_total)

# 步骤3: 导入 db（仅 init_db，models 和 engine 已在第1步加载）
_step3 = time.perf_counter()
from app.db import init_db  # noqa: E402
logger.info("[启动耗时] 第3步 | init_db 导入完成 | 耗时=%.3fs | 累计=%.3fs",
            time.perf_counter() - _step3, time.perf_counter() - _startup_total)

logger.info("[启动耗时] === 所有 import 完成 | 累计耗时=%.3fs ===",
            time.perf_counter() - _startup_total)


_step4 = time.perf_counter()
app = FastAPI(title="OpenClass - 课堂模拟学生提问助手", lifespan=lifespan)
logger.info("[启动耗时] 第4步 | FastAPI 实例创建完成 | 耗时=%.3fs | 累计=%.3fs",
            time.perf_counter() - _step4, time.perf_counter() - _startup_total)

_step5 = time.perf_counter()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("[启动耗时] 第5步 | CORS 中间件添加完成 | 耗时=%.3fs | 累计=%.3fs",
            time.perf_counter() - _step5, time.perf_counter() - _startup_total)

_step6 = time.perf_counter()
app.include_router(rest_router)
logger.info("[启动耗时] 第6步 | rest_router 注册完成 | 耗时=%.3fs | 累计=%.3fs",
            time.perf_counter() - _step6, time.perf_counter() - _startup_total)

_step7 = time.perf_counter()
app.include_router(websocket_router)
logger.info("[启动耗时] 第7步 | websocket_router 注册完成 | 耗时=%.3fs | 累计=%.3fs",
            time.perf_counter() - _step7, time.perf_counter() - _startup_total)

logger.info("[启动耗时] === main.py 顶层代码执行完毕 | 总耗时=%.3fs ===",
            time.perf_counter() - _startup_total)


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return JSONResponse({"status": "ok", "message": "服务正常运行"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
