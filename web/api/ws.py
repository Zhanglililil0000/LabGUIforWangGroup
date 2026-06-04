"""WebSocket 端点。管理活跃连接，提供广播和线程安全发送。"""
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from web.services.runner import get_runner

router = APIRouter(tags=["ws"])
_active_connections: list[WebSocket] = []


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
    """从 Pipeline 线程调用的同步发送函数。"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    for ws in _active_connections:
        try:
            loop.call_soon_threadsafe(
                lambda w=ws, m=msg: asyncio.ensure_future(_safe_send(w, m))
            )
        except Exception:
            pass


async def _safe_send(ws: WebSocket, msg: dict):
    try:
        await ws.send_json(msg)
    except Exception:
        if ws in _active_connections:
            _active_connections.remove(ws)
