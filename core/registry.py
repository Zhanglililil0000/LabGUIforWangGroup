"""注册中心模块。提供设备和操作的插件式注册/查找机制。"""

from typing import Any, Optional


class DeviceRegistry:
    """全局设备注册中心。

    设备类型在此注册，运行时按配置创建实例。

    Usage:
        @DeviceRegistry.register_device_type("thorlabs_rotator")
        class ThorlabsRotator(DeviceBase): ...

        dev = DeviceRegistry.create_device("thorlabs_rotator", "vis_rotator", config_dict)
        dev = DeviceRegistry.get_device("vis_rotator")
    """

    _device_types: dict[str, type] = {}
    _instances: dict[str, Any] = {}

    @classmethod
    def register_device_type(cls, name: str, device_cls: type):
        """注册设备类型（也可作为装饰器使用）。

        Args:
            name: 设备类型名称，如 "thorlabs_rotator"
            device_cls: 设备类（需继承 DeviceBase）

        Returns:
            device_cls (方便作为装饰器)
        """
        cls._device_types[name] = device_cls
        return device_cls

    @classmethod
    def create_device(cls, type_name: str, name: str, config: dict) -> Any:
        """根据类型名和配置创建设备实例。

        Args:
            type_name: 设备类型名 (已在 register_device_type 注册)
            name: 设备实例名 (如 "vis_rotator")
            config: 设备连接参数字典（仅保留 __init__ 接受的参数）

        Returns:
            设备实例

        Raises:
            ValueError: 设备类型未注册
        """
        if type_name not in cls._device_types:
            raise ValueError(
                f"未注册的设备类型: {type_name}。"
                f"已注册: {list(cls._device_types.keys())}"
            )
        device_cls = cls._device_types[type_name]
        # 只传递构造器接受的参数
        filtered = cls._filter_params(device_cls, config)
        # 始终注入 name
        if "name" not in filtered:
            filtered["name"] = name
        instance = device_cls(**filtered)
        cls._instances[name] = instance
        return instance

    @classmethod
    def get_device(cls, name: str) -> Optional[Any]:
        """获取已创建的设备实例。"""
        return cls._instances.get(name)

    @classmethod
    def list_devices(cls) -> dict[str, Any]:
        """列出所有已创建的设备实例。"""
        return dict(cls._instances)

    @classmethod
    def list_device_types(cls) -> list[str]:
        """列出所有已注册的设备类型。"""
        return list(cls._device_types.keys())

    @classmethod
    def clear(cls):
        """清除所有注册（用于测试）。"""
        cls._device_types.clear()
        cls._instances.clear()

    @classmethod
    def _filter_params(cls, device_cls: type, config: dict) -> dict:
        """过滤配置字典，只保留 __init__ 接受的参数。"""
        import inspect
        try:
            sig = inspect.signature(device_cls.__init__)
            params = set(sig.parameters.keys()) - {"self"}
            return {k: v for k, v in config.items() if k in params}
        except (ValueError, TypeError):
            return dict(config)


class OperationRegistry:
    """全局操作注册中心。

    操作类型在此注册，管道通过操作类名创建操作实例。

    Usage:
        @OperationRegistry.register
        class AcquireSpectrum(Operation): ...

        op = OperationRegistry.create("AcquireSpectrum", exposure_ms=60000)
    """

    _operations: dict[str, type] = {}

    @classmethod
    def register(cls, op_cls: type):
        """注册操作类型（装饰器）。

        Args:
            op_cls: 操作类（需继承 Operation）
        """
        cls._operations[op_cls.__name__] = op_cls
        return op_cls

    @classmethod
    def create(cls, name: str, **kwargs) -> Any:
        """根据操作名创建操作实例。

        Args:
            name: 操作类名
            **kwargs: 传递给操作构造函数的参数

        Returns:
            Operation 实例

        Raises:
            ValueError: 操作类型未注册
        """
        if name not in cls._operations:
            raise ValueError(
                f"未注册的操作类型: {name}。"
                f"已注册: {list(cls._operations.keys())}"
            )
        return cls._operations[name](**kwargs)

    @classmethod
    def list_all(cls) -> list[str]:
        """列出所有已注册的操作名。"""
        return list(cls._operations.keys())

    @classmethod
    def clear(cls):
        """清除所有注册（用于测试）。"""
        cls._operations.clear()
