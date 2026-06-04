"""Device management REST API.

提供设备列表查询、单设备/批量连接与断开功能。
_device_pool 模块级字典存储所有设备实例，与 experiments runner 共享。
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from web.schemas import DeviceBrief
from web.services.runner import get_available_device_configs

router = APIRouter(tags=["devices"])

_device_pool: dict[str, object] = {}

_log = logging.getLogger(__name__)


def _ensure_device_pool(mode: str = ""):
    """确保 _device_pool 中已根据 devices.yaml 创建了设备实例。

    首次调用时依次尝试导入各设备驱动类并创建全部设备实例。
    导入失败（如驱动未安装）的设备会被跳过，不会阻塞其它设备。
    仅在 pool 为空时执行初始化，已存在则跳过。

    Args:
        mode: 实验模式。仅用于日志记录，不影响创建设备范围
              （始终创建全部设备，由 list_devices 按需过滤）。
    """
    global _device_pool
    if _device_pool:
        return

    try:
        configs = get_available_device_configs()
    except Exception:
        _log.exception("加载 devices.yaml 失败")
        return

    for dev_name, dev_cfg in configs.items():
        dev_type = dev_cfg.get("type", "")
        try:
            dev = _create_device_instance(dev_name, dev_type, dev_cfg)
            if dev is not None:
                _device_pool[dev_name] = dev
                _log.info("设备实例已创建: %s (type=%s)", dev_name, dev_type)
        except Exception:
            _log.warning("创建设备实例失败: %s (type=%s), 已跳过", dev_name, dev_type,
                         exc_info=True)


def _create_device_instance(name: str, dev_type: str, cfg: dict):
    """根据设备类型字符串创建对应的设备实例。

    每个设备驱动模块在函数体内延迟导入，避免模块级 import
    在驱动未安装时阻塞整个 API 模块的加载。

    Returns:
        设备实例，类型未知时返回 None
    """
    if dev_type == "thorlabs_rotator":
        from devices.motor import ThorlabsRotator
        return ThorlabsRotator(
            name=name,
            driver=cfg.get("driver", "Cage"),
            serial=str(cfg.get("serial", "")),
        )

    if dev_type == "lightfield":
        from devices.spectrometer import LightFieldSpectrometer
        return LightFieldSpectrometer(
            name=name,
            experiment_name=cfg.get("experiment_name", ""),
        )

    if dev_type == "delay_stage":
        from devices.delay_stage import DelayStage
        return DelayStage(
            name=name,
            port=cfg.get("port", "COM4"),
            baud=int(cfg.get("baud", 19200)),
            controller=cfg.get("controller", "SMC"),
            slave=int(cfg.get("slave", 0xCC)),
            limit_isnegative=bool(cfg.get("limit_isnegative", True)),
        )

    if dev_type == "thorlabs_tlpm":
        from devices.power_meter import ThorlabsPowerMeter
        return ThorlabsPowerMeter(
            name=name,
            wavelength_nm=float(cfg.get("wavelength_nm", 532.0)),
        )

    if dev_type == "keyence_cl3":
        from devices.distance_sensor import KeyenceDistanceSensor
        return KeyenceDistanceSensor(
            name=name,
            device_id=int(cfg.get("device_id", 0)),
            timeout=int(cfg.get("timeout", 10000)),
        )

    if dev_type == "vertical_stage":
        from devices.vertical_stage import VerticalStage
        return VerticalStage(
            name=name,
            port=cfg.get("port", "COM9"),
            baud=int(cfg.get("baud", 9600)),
        )

    if dev_type == "smacq_ai":
        from devices.daq_card import SmacqAICard
        return SmacqAICard(
            name=name,
            device_id=int(cfg.get("device_id", 0)),
            timeout=int(cfg.get("timeout", 1000)),
            range_val=float(cfg.get("range_val", 5.0)),
            sample_rate=int(cfg.get("sample_rate", 1000)),
            channels=int(cfg.get("channels", 1)),
        )

    _log.warning("未知设备类型: %s (设备: %s)", dev_type, name)
    return None


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
    _ensure_device_pool(mode)
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
    _ensure_device_pool()
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
    _ensure_device_pool()
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
