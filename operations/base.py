"""原子操作基类。管道的最小编排单元。"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class OperationStatus(Enum):
    """操作状态枚举。"""
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class Operation(ABC):
    """原子操作：管道的最小编排单元。

    每个 Operation 封装一个单一设备操作（如移动电机、采集光谱）。
    管道按顺序执行 Operation 列表。

    子类必须实现 execute() 方法。
    可选择性覆盖 validate() 和 rollback()。

    Usage:
        class MotorHome(Operation):
            def execute(self, ctx):
                ctx.devices["vis_rotator"].home()
                return {"status": "done"}
    """

    def __init__(self, name: str = ""):
        """创建操作实例。

        Args:
            name: 操作的可读名称（用于日志和 GUI 展示）
        """
        self._name = name or self.__class__.__name__
        self._status = OperationStatus.PENDING

    @property
    def name(self) -> str:
        """操作名称。"""
        return self._name

    @property
    def status(self) -> OperationStatus:
        """当前操作状态。"""
        return self._status

    def set_status(self, status: OperationStatus):
        """更新操作状态（由 Pipeline 调用）。"""
        self._status = status

    @abstractmethod
    def execute(self, ctx: Any) -> dict:
        """执行操作。

        Args:
            ctx: ExperimentContext 实例，提供设备引用、配置、共享数据

        Returns:
            结果字典（可包含任意键值对，供后续步骤或日志使用）

        Raises:
            任何异常都会被 Pipeline 捕获并按错误策略处理
        """
        ...

    def validate(self, ctx: Any) -> bool:
        """执行前校验。

        返回 False 会导致该步骤被跳过（状态设为 SKIPPED）。

        Args:
            ctx: ExperimentContext 实例

        Returns:
            True 表示校验通过，继续执行
        """
        return True

    def rollback(self, ctx: Any) -> None:
        """失败时的回滚操作。

        在 Pipeline 的错误策略决定"中止"时调用。
        子类可覆盖以实现清理逻辑。

        Args:
            ctx: ExperimentContext 实例
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', status={self.status.value})"
