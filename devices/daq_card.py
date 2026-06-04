"""Smacq USB-1000 采集卡设备驱动。"""

import ctypes
import numpy as np
from ctypes import c_int, c_float, c_char, c_ulong, c_ushort, c_uint, c_long, POINTER, windll

from devices.base import DeviceBase, DeviceConnectionError, DeviceOperationError


class SmacqAICard(DeviceBase):
    """Smacq USB-1000 系列采集卡 (差分模拟输入)。

    Usage:
        card = SmacqAICard(name="daq", device_id=0, channels=1, sample_rate=1000)
        card.connect()
        data = card.read(num_points=100)  # shape: (channels, points)
    """

    def __init__(
        self,
        name: str = "daq_card",
        device_id: int = 0,
        timeout: int = 1000,
        range_val: float = 5.0,
        sample_rate: int = 1000,
        channels: int = 1,
    ):
        super().__init__(name)
        self._device_id = device_id
        self._timeout_val = timeout
        self._range_val = range_val
        self._sample_rate = sample_rate
        self._channels = channels
        self._dll = None

    def connect(self) -> bool:
        try:
            try:
                self._dll = windll.LoadLibrary(
                    'resources\\Smacq\\x64\\usb-1000.dll'
                )
            except Exception:
                try:
                    self._dll = windll.LoadLibrary(
                        'resources\\Smacq\\x86\\usb-1000.dll'
                    )
                except Exception as e:
                    raise DeviceConnectionError(
                        self.name, f"无法加载 DLL: {e}"
                    )

            res = self._dll.OpenDevice(c_int(self._device_id))
            if res != 0:
                raise DeviceConnectionError(
                    self.name, f"OpenDevice 失败 (code={res})"
                )

            self._dll.ResetDevice(c_int(self._device_id))
            self._dll.SetChanMode(c_int(self._device_id), c_char(0))
            self._dll.SetUSB1AiRange(
                c_int(self._device_id), c_float(self._range_val)
            )
            self._dll.SetSampleRate(
                c_int(self._device_id), c_uint(self._sample_rate)
            )
            self._dll.SetChanSel(
                c_int(self._device_id), c_ushort(self._channels)
            )
            self._dll.StartRead(c_int(self._device_id))
            self._dll.SetSoftTrig(c_int(self._device_id), c_char(1))

            self._connected = True
            print(f"[{self.name}] Smacq 采集卡已连接 (id={self._device_id})")
            return True
        except Exception as e:
            raise DeviceConnectionError(self.name, str(e))

    def disconnect(self) -> None:
        try:
            if self._dll:
                self._dll.SetSoftTrig(c_int(self._device_id), c_char(0))
                self._dll.StopRead(c_int(self._device_id))
                self._dll.ClearBufs(c_int(self._device_id))
                self._dll.CloseDevice(c_int(self._device_id))
            self._connected = False
            print(f"[{self.name}] 已断开")
        except Exception:
            pass

    @property
    def is_connected(self) -> bool:
        return self._connected

    def read(self, num_points: int = 100) -> np.ndarray:
        """读取通道数据。

        Args:
            num_points: 每个通道的点数

        Returns:
            numpy 数组，形状为 (通道数, num_points)
        """
        if not self._dll:
            raise DeviceOperationError(self.name, "read", "设备未连接")

        n_ch = self._count_channels()
        total = num_points * n_ch
        buf = np.zeros(total, dtype='float32')

        res = self._dll.GetAiChans(
            c_int(self._device_id),
            c_ulong(num_points),
            c_ushort(self._channels),
            buf.ctypes.data_as(POINTER(ctypes.c_float)),
            c_long(self._timeout_val),
        )
        if res < 0:
            raise DeviceOperationError(
                self.name, "read", f"GetAiChans 失败 (code={res})"
            )

        return buf.reshape(n_ch, num_points) if n_ch > 1 else buf.reshape(1, num_points)

    def _count_channels(self) -> int:
        count = 0
        ch = self._channels
        while ch:
            count += ch & 1
            ch >>= 1
        return count
