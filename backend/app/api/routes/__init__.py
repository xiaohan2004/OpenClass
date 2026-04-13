"""API 路由集合。"""

from .rest import router as rest_router
from .websocket import router as websocket_router

__all__ = ["rest_router", "websocket_router"]
