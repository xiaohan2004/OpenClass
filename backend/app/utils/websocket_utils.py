"""WebSocket 传输层辅助工具。"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket


class SafeWebSocket:
    """为 WebSocket 的 send_json 操作加锁，避免并发冲突。"""

    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.lock = asyncio.Lock()

    async def send_json(self, data: dict[str, Any]) -> None:
        """安全地通过 WebSocket 发送 JSON 数据，避免并发冲突。"""
        async with self.lock:
            await self.ws.send_json(data)
