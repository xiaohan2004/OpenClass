"""
FastAPI 应用入口
"""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.rest import router as rest_router
from app.api.routes.websocket import router as websocket_router
from app.db import init_db
from app.utils.model_download_policy import (
    prepare_keyword_model_download_policy,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """应用生命周期，启动时初始化数据库。"""
    prepare_keyword_model_download_policy()
    init_db()
    logger.info("数据库初始化完成")
    yield


app = FastAPI(title="OpenClass - 课堂模拟学生提问助手", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(rest_router)
app.include_router(websocket_router)


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return JSONResponse({"status": "ok", "message": "服务正常运行"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
