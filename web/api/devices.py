"""Device management REST API.

提供设备列表查询、单设备/批量连接与断开功能。
_device_pool 模块级字典存储所有设备实例，与 experiments runner 共享。
"""

from fastapi import APIRouter, HTTPException, Query
from web.schemas import DeviceBrief
from web.services.runner import get_available_device_configs

router = APIRouter(tags=["devices"])

_device_pool: dict[str, object] = {}


def _get_mode_device_names(mode: str) -> set[str]:
    """读取 defaults.yaml 中指定模式的设备列表。"""
    try:
        from core.config import Config
        config = Config("configs/defaults.yaml")
        mode_cfg = config.get(f"modes.{mode}")
        if mode_cfg and "devices" in mode_cfg:
            return set(mode_cfg["devices"])
    except Exception:
        pass
    return set()


def get_device_pool() -> dict[str, object]:
    """返回当前设备池（模块级单例）。"""
    return _device_pool


def set_device_pool(pool: dict[str, object]) -> None:
    """替换整个设备池。

    Args:
        pool: 新的设备名称到实例映射字典
    """
    global _device_pool
    _device_pool = pool


def _get_position_safe(device) -> float | None:
    """安全地获取设备位置，失败时返回 None。"""
    try:
        if hasattr(device, "get_position"):
            return device.get_position()
    except Exception:
        pass
    try:
        if hasattr(device, "status") and isinstance(device.status, dict):
            return device.status.get("position")
    except Exception:
        pass
    return None


def _extract_details(cfg: dict) -> dict:
    """从设备配置中提取关键展示信息（序列号、端口等）。"""
    skip = {"type", "name"}
    # 只保留简单类型值
    result = {}
    for k, v in cfg.items():
        if k in skip:
            continue
        if isinstance(v, (str, int, float, bool)):
            result[k] = v
    return result


@router.get("/devices", response_model=list[DeviceBrief])
async def list_devices(mode: str = Query(default="")):
    """获取设备状态列表。可选 mode 参数按实验模式过滤。"""
    try:
        configs = get_available_device_configs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"无法加载设备配置: {e}")

    allowed = _get_mode_device_names(mode) if mode else set()

    result: list[DeviceBrief] = []
    for dev_name, dev_cfg in configs.items():
        if allowed and dev_name not in allowed:
            continue
        dev = _device_pool.get(dev_name)
        connected = False
        position = None

        if dev is not None:
            try:
                connected = dev.is_connected
            except Exception:
                connected = False
            position = _get_position_safe(dev)

        result.append(DeviceBrief(
            name=dev_name,
            type=dev_cfg.get("type", "unknown"),
            connected=connected,
            position=position,
            details=_extract_details(dev_cfg),
        ))

    return result


@router.post("/devices/{name}/connect")
async def connect_device(name: str):
    """连接指定名称的设备。

    Args:
        name: 设备名称（如 vis_rotator）
    """
    dev = _device_pool.get(name)
    if dev is None:
        raise HTTPException(status_code=404, detail=f"设备 '{name}' 不在设备池中")

    if not hasattr(dev, "connect"):
        raise HTTPException(status_code=500, detail=f"设备 '{name}' 不支持连接操作")

    try:
        dev.connect()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设备 '{name}' 连接失败: {e}")

    return {"name": name, "connected": True}


@router.post("/devices/{name}/disconnect")
async def disconnect_device(name: str):
    """断开指定名称的设备。

    Args:
        name: 设备名称（如 vis_rotator）
    """
    dev = _device_pool.get(name)
    if dev is None:
        raise HTTPException(status_code=404, detail=f"设备 '{name}' 不在设备池中")

    if not hasattr(dev, "disconnect"):
        raise HTTPException(status_code=500, detail=f"设备 '{name}' 不支持断开操作")

    try:
        dev.disconnect()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设备 '{name}' 断开失败: {e}")

    return {"name": name, "connected": False}


@router.post("/devices/connect-all")
async def connect_all_devices():
    """连接设备池中所有设备。"""
    errors: dict[str, str] = {}
    connected = 0

    for name, dev in _device_pool.items():
        if not hasattr(dev, "connect"):
            continue
        try:
            dev.connect()
            connected += 1
        except Exception as e:
            errors[name] = str(e)

    return {
        "connected": connected,
        "total": len(_device_pool),
        "errors": errors,
    }


@router.post("/devices/disconnect-all")
async def disconnect_all_devices():
    """断开设备池中所有设备。"""
    errors: dict[str, str] = {}
    disconnected = 0

    for name, dev in _device_pool.items():
        if not hasattr(dev, "disconnect"):
            continue
        try:
            dev.disconnect()
            disconnected += 1
        except Exception as e:
            errors[name] = str(e)

    return {
        "disconnected": disconnected,
        "total": len(_device_pool),
        "errors": errors,
    }
