"""课堂 WebSocket 路由。"""

from __future__ import annotations

import asyncio
import base64
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
            if not isinstance(msg, dict):
                raise TypeError("消息必须是 JSON 对象")
            if msg.get("type") == "audio_in":
                audio_bytes, start_time, end_time = _parse_audio_data(msg.get("data"))

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


def _parse_audio_data(data: Any) -> tuple[bytes, int, int]:
    """严格解析 audio_in.data，不符合协议直接抛异常。"""
    if not isinstance(data, dict):
        raise TypeError("audio_in.data 必须是对象")

    required_keys = {"audio", "start_time", "end_time"}
    if set(data.keys()) != required_keys:
        raise TypeError("audio_in.data 字段必须且仅能包含 audio/start_time/end_time")

    audio = data.get("audio")
    if not isinstance(audio, str):
        raise TypeError("audio_in.data.audio 必须是 base64 字符串")

    start_time = data.get("start_time")
    end_time = data.get("end_time")
    if not isinstance(start_time, int):
        raise TypeError("audio_in.data.start_time 必须是 int")
    if not isinstance(end_time, int):
        raise TypeError("audio_in.data.end_time 必须是 int")

    return _decode_audio_base64(audio), start_time, end_time


def _decode_audio_base64(audio_text: str) -> bytes:
    """解析纯 base64 音频字符串。"""
    payload = audio_text.strip()
    if not payload:
        raise TypeError("audio_in.data.audio 不能为空")
    if payload.startswith("data:"):
        raise TypeError("audio_in.data.audio 必须是纯 base64 字符串，不能是 data URL")

    try:
        return base64.b64decode(payload, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise TypeError("audio_in.data.audio 不是合法 base64 编码") from exc
