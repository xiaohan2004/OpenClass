"""
FastAPI 应用入口
"""

import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(title="OpenClass - 课堂模拟学生提问助手")


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return JSONResponse({"status": "ok", "message": "服务正常运行"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
