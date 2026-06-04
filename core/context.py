"""实验运行时上下文。贯穿整个管道执行过程。"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import logging


@dataclass
class ExperimentContext:
    """实验运行时上下文，在管道执行期间保持。

    包含所有设备引用、配置、共享数据和运行状态。
    管道中的每个 Operation 都接收并修改此上下文。

    Usage:
        ctx = ExperimentContext(config=config)
        ctx.devices["vis_rotator"] = rotator_instance
        ctx.data["last_spectrum"] = {...}
    """

    config: Any = None
    """Config 实例"""

    devices: dict[str, Any] = field(default_factory=dict)
    """设备实例字典，key 为设备名如 "vis_rotator", "spectrometer" """

    data: dict[str, Any] = field(default_factory=dict)
    """共享数据空间，管道步骤间通过此字典传递计算结果"""

    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("SFGExperiment")
    )
    """日志记录器"""

    start_time: datetime = field(default_factory=datetime.now)
    """实验开始时间"""

    status: str = "initializing"
    """实验状态: "initializing" | "running" | "paused" | "done" | "failed" """

    _pause_flag: bool = field(default=False, repr=False)
    _stop_flag: bool = field(default=False, repr=False)

    def pause(self):
        """请求暂停。当前步骤完成后暂停。"""
        self._pause_flag = True
        self.status = "paused"
        self.logger.info("实验已请求暂停")

    def resume(self):
        """恢复执行。"""
        self._pause_flag = False
        self.status = "running"
        self.logger.info("实验已恢复")

    def stop(self):
        """请求停止。当前步骤完成后退出。"""
        self._stop_flag = True
        self.status = "failed"
        self.logger.info("实验已请求停止")

    @property
    def should_pause(self) -> bool:
        """是否需要暂停。"""
        return self._pause_flag

    @property
    def should_stop(self) -> bool:
        """是否需要停止。"""
        return self._stop_flag

    def reset_flags(self):
        """重置暂停/停止标志（管道开始时调用）。"""
        self._pause_flag = False
        self._stop_flag = False
        self.status = "running"

    def set_device(self, name: str, device: Any):
        """注册一个设备实例到上下文。"""
        self.devices[name] = device

    def get_device(self, name: str) -> Any:
        """获取设备实例。"""
        if name not in self.devices:
            raise KeyError(f"设备 '{name}' 不在上下文中。可用设备: {list(self.devices.keys())}")
        return self.devices[name]
