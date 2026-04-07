"""课堂 WebSocket 路由。"""

from __future__ import annotations

import asyncio
import binascii
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.classcontext import ClassContext
from app.core.main_flow import handle_audio
from app.utils.websocket_utils import SafeWebSocket

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/session/{session_id}")
async def ws_session(websocket: WebSocket, session_id: str) -> None:
    """课堂 WebSocket 连接处理器，处理音频输入。"""
    await websocket.accept()

    safe_ws = SafeWebSocket(websocket)
    context = ClassContext()  # 每个 session 独立

    try:
        while True:
            msg = await websocket.receive_json()

            if msg.get("type") == "audio_in":
                # 接受到前端的音频输入，格式为 bytes
                try:
                    audio_bytes = _check_audio_bytes(msg.get("data", b""))
                except (TypeError, binascii.Error) as exc:
                    logger.error("无效的音频数据: %s", exc)
                    await safe_ws.send(
                        {"type": "error", "data": {"message": f"无效的音频数据: {exc}"}}
                    )
                    continue

                # 主流程（异步任务，不阻塞接收）
                asyncio.create_task(handle_audio(audio_bytes, context, safe_ws))

    except WebSocketDisconnect as exc:
        logger.info("连接断开: %s", exc)


def _check_audio_bytes(data: Any) -> bytes:
    """检查 WebSocket 消息里的音频载荷是否为 bytes 并返回。"""
    if isinstance(data, bytes):
        return data

    raise TypeError("audio_in 数据必须是 bytes格式")
