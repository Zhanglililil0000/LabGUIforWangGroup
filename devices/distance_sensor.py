"""KEYENCE 距离传感器设备驱动。封装 CL3_IF.dll。"""

import sys
import os

# 延迟导入，避免在无 DLL 环境下 import 失败
_DistanceDetector = None

def _get_detector():
    global _DistanceDetector
    if _DistanceDetector is None:
        _current_dir = os.path.dirname(os.path.abspath(__file__))
        _parent = os.path.dirname(_current_dir)
        if _parent not in sys.path:
            sys.path.insert(0, _parent)
        from API.KEYENCEAPI import DistanceDetector as DD
        _DistanceDetector = DD
    return _DistanceDetector

from devices.base import DeviceBase, DeviceConnectionError, DeviceOperationError


class KeyenceDistanceSensor(DeviceBase):
    """KEYENCE CL-3000 系列激光距离传感器。

    Usage:
        sensor = KeyenceDistanceSensor(name="distance_sensor")
        sensor.connect()
        height, is_valid = sensor.get_distance()
    """

    def __init__(self, name: str = "distance_sensor",
                 device_id: int = 0, timeout: int = 10000):
        super().__init__(name)
        self._device_id = device_id
        self._timeout = timeout
        self._detector = None

    def connect(self) -> bool:
        try:
            Detector = _get_detector()
            self._detector = Detector(
                deviceId=self._device_id, timeout=self._timeout
            )
            self._connected = True
            print(f"[{self.name}] KEYENCE 距离传感器已连接")
            return True
        except Exception as e:
            raise DeviceConnectionError(self.name, str(e))

    def disconnect(self) -> None:
        self._connected = False
        self._detector = None
        print(f"[{self.name}] 已断开")

    @property
    def is_connected(self) -> bool:
        return self._connected

    def get_distance(self) -> tuple:
        """读取距离值。

        Returns:
            (height_um, is_valid) 元组
        """
        if not self._detector:
            raise DeviceOperationError(self.name, "get_distance", "设备未连接")
        return self._detector.get_distance()
