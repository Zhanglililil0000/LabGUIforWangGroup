"""WebSocket 端点。管理活跃连接，提供广播和线程安全发送。"""

import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from web.services.runner import get_runner

router = APIRouter(tags=["ws"])
_active_connections: list[WebSocket] = []
_main_loop: asyncio.AbstractEventLoop = None


async def broadcast(msg: dict):
    """向所有 WebSocket 连接推送消息。"""
    dead = []
    for ws in _active_connections:
        try:
            await ws.send_json(msg)
        except Exception:
            dead.append(ws)
    for d in dead:
        _active_connections.remove(d)


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    global _main_loop
    _main_loop = asyncio.get_running_loop()
    await ws.accept()
    _active_connections.append(ws)
    runner = get_runner()
    if runner:
        runner.set_ws_send(lambda msg: _sync_send(msg))
    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
                cmd = data.get("type")
                if cmd == "pause" and runner:
                    runner.pause()
                elif cmd == "stop" and runner:
                    runner.stop()
            except Exception:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        if ws in _active_connections:
            _active_connections.remove(ws)


def _sync_send(msg: dict):
    """从 Pipeline 线程调用的同步发送函数。

    利用 asyncio.run_coroutine_threadsafe 将协程发送到
    FastAPI 主事件循环，确保跨线程安全。
    """
    if _main_loop is None:
        return
    for ws in list(_active_connections):
        try:
            asyncio.run_coroutine_threadsafe(_safe_send(ws, msg), _main_loop)
        except Exception:
            pass


async def _safe_send(ws: WebSocket, msg: dict):
    """异步安全发送 JSON 消息。发送失败时自动移除连接。"""
    try:
        await ws.send_json(msg)
    except Exception:
        if ws in _active_connections:
            _active_connections.remove(ws)