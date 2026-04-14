"""课堂 WebSocket 路由。"""

from __future__ import annotations

import asyncio
import binascii
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.db import get_engine
from app.db.crud import get_session_by_id
from app.core.classcontext import ClassContext
from app.core.main_flow import handle_audio
from app.utils.websocket_utils import SafeWebSocket
from sqlmodel import Session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/session/{session_id}")
async def ws_session(websocket: WebSocket, session_id: int) -> None:
    """课堂 WebSocket 连接处理器，处理音频输入。"""
    await websocket.accept()

    with Session(get_engine()) as db:
        session_record = get_session_by_id(db, session_id)
    if session_record is None:
        await websocket.send_json(
            {"type": "error", "data": {"message": f"课堂不存在: {session_id}"}}
        )
        await websocket.close(code=1008)
        return

    safe_ws = SafeWebSocket(websocket)
    context = ClassContext(session_id=session_id)  # 每个 session 独立

    try:
        while True:
            msg = await websocket.receive_json()

            if msg.get("type") == "audio_in":
                # 接受到前端的音频输入，格式为 bytes
                try:
                    audio_bytes, start_time, end_time = _parse_audio_input(
                        msg.get("data", b"")
                    )
                except (TypeError, binascii.Error) as exc:
                    logger.error("无效的音频数据: %s", exc)
                    await safe_ws.send_json(
                        {"type": "error", "data": {"message": f"无效的音频数据: {exc}"}}
                    )
                    continue

                # 主流程（异步任务，不阻塞接收）
                asyncio.create_task(
                    handle_audio(
                        audio_bytes,
                        context,
                        safe_ws,
                        transcript_start_time=start_time,
                        transcript_end_time=end_time,
                    )
                )

    except WebSocketDisconnect as exc:
        logger.info("连接断开: %s", exc)


def _parse_audio_input(data: Any) -> tuple[bytes, int | None, int | None]:
    """解析 WebSocket 音频输入，兼容 bytes 与对象格式。"""
    if isinstance(data, bytes):
        return data, None, None

    if isinstance(data, dict):
        audio = data.get("audio")
        if not isinstance(audio, bytes):
            raise TypeError("audio_in.data.audio 必须是 bytes格式")

        start_time = data.get("start_time")
        end_time = data.get("end_time")

        if start_time is not None and not isinstance(start_time, int):
            raise TypeError("audio_in.data.start_time 必须是 int")
        if end_time is not None and not isinstance(end_time, int):
            raise TypeError("audio_in.data.end_time 必须是 int")

        return audio, start_time, end_time

    raise TypeError("audio_in 数据必须是 bytes格式")
