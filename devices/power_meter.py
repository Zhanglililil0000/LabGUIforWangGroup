"""Thorlabs 光功率计设备驱动。封装 ThorlabsTLPM (ctypes + VISA)。"""

import time
import sys
import os
from ctypes import (
    c_long, c_ulong, c_uint32, byref, create_string_buffer,
    c_bool, c_char_p, c_int, c_int16, c_double,
)

# 导入原始 TLPM 绑定
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent = os.path.dirname(_current_dir)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from API.ThorlabsTLPM import TLPM
from devices.base import DeviceBase, DeviceConnectionError, DeviceOperationError


class ThorlabsPowerMeter(DeviceBase):
    """Thorlabs 光功率计 (PM100D/PM100A/PM160/PM400 系列)。

    Usage:
        pm = ThorlabsPowerMeter(name="power_meter", wavelength_nm=532.0)
        pm.connect()
        power = pm.measure()  # 返回功率值 (W)
    """

    def __init__(self, name: str = "power_meter",
                 wavelength_nm: float = 532.0):
        super().__init__(name)
        self._wavelength_nm = wavelength_nm
        self._tlpm = TLPM()
        self._resource_name = None

    def connect(self) -> bool:
        try:
            device_count = c_uint32()
            self._tlpm.findRsrc(byref(device_count))
            print(f"[{self.name}] 找到 {device_count.value} 个功率计设备")

            if device_count.value == 0:
                raise DeviceConnectionError(self.name, "未找到功率计设备")

            resource_name = create_string_buffer(1024)
            self._tlpm.getRsrcName(c_int(0), resource_name)
            self._resource_name = resource_name

            self._tlpm.open(resource_name, c_bool(True), c_bool(True))

            message = create_string_buffer(1024)
            self._tlpm.getCalibrationMsg(message)
            print(f"[{self.name}] 已连接, 校准日期: {c_char_p(message.raw).value}")

            time.sleep(1)

            self.set_wavelength(self._wavelength_nm)
            self._tlpm.setPowerAutoRange(c_int16(1))
            self._tlpm.setPowerUnit(c_int16(0))

            self._connected = True
            return True
        except Exception as e:
            raise DeviceConnectionError(self.name, str(e))

    def disconnect(self) -> None:
        try:
            if self._tlpm:
                self._tlpm.close()
            self._connected = False
            print(f"[{self.name}] 已断开")
        except Exception:
            pass

    @property
    def is_connected(self) -> bool:
        return self._connected

    def set_wavelength(self, nm: float):
        """设置测量波长 (nm)。"""
        self._tlpm.setWavelength(c_double(nm))
        self._wavelength_nm = nm

    def measure(self) -> float:
        """测量当前功率。

        Returns:
            功率值 (W)
        """
        if not self._connected:
            raise DeviceOperationError(self.name, "measure", "设备未连接")
        power = c_double()
        self._tlpm.measPower(byref(power))
        return power.value

    def measure_average(self, n_samples: int = 10,
                        interval_s: float = 0.1) -> float:
        """多次测量取平均。

        Args:
            n_samples: 采样次数
            interval_s: 采样间隔 (秒)

        Returns:
            平均功率值 (W)
        """
        total = 0.0
        for _ in range(n_samples):
            total += self.measure()
            time.sleep(interval_s)
        return total / n_samples
