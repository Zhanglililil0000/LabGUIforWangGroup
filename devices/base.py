"""设备基类。所有硬件的抽象接口。"""

from abc import ABC, abstractmethod


class DeviceError(Exception):
    """设备相关错误的基类。"""


class DeviceConnectionError(DeviceError):
    """设备连接错误。"""

    def __init__(self, device_name: str, detail: str = ""):
        self.device_name = device_name
        self.detail = detail
        super().__init__(f"设备 '{device_name}' 连接失败: {detail}")


class DeviceOperationError(DeviceError):
    """设备操作错误。"""

    def __init__(self, device_name: str, operation: str, detail: str = ""):
        self.device_name = device_name
        self.operation = operation
        self.detail = detail
        super().__init__(f"设备 '{device_name}' 操作 '{operation}' 失败: {detail}")


class DeviceBase(ABC):
    """所有设备的抽象基类。

    子类必须实现 connect, disconnect, is_connected。
    推荐使用上下文管理器:

        with MyDevice(name="dev1", ...) as dev:
            dev.some_operation()
    """

    def __init__(self, name: str = ""):
        """初始化设备。

        Args:
            name: 设备实例名称，如 "vis_rotator"
        """
        self._name = name
        self._connected = False

    # ========== 抽象方法 ==========

    @abstractmethod
    def connect(self) -> bool:
        """建立设备连接。

        Returns:
            True 表示连接成功

        Raises:
            DeviceConnectionError: 连接失败
        """
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """断开设备连接，释放资源。"""
        ...

    # ========== 属性 ==========

    @property
    def name(self) -> str:
        """设备名称。"""
        return self._name

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """设备是否已连接。"""
        ...

    @property
    def status(self) -> dict:
        """返回设备状态字典，供 GUI / 日志使用。

        Returns:
            包含 name, type, is_connected 等字段的字典
        """
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "is_connected": self.is_connected,
        }

    # ========== 上下文管理 ==========

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', connected={self.is_connected})"
