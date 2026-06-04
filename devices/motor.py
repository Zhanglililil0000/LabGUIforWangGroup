"""Thorlabs 旋转电机设备驱动。封装 Kinesis .NET API。

依赖：Thorlabs Kinesis 软件已安装，DLL 位于 C:\\Program Files\\Thorlabs\\Kinesis\\
"""

import time
import clr
from System import Decimal

clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\ThorLabs.MotionControl.IntegratedStepperMotorsCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\ThorLabs.MotionControl.KCube.DCServoCLI.dll")

from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI
from Thorlabs.MotionControl.IntegratedStepperMotorsCLI import CageRotator
from Thorlabs.MotionControl.KCube.DCServoCLI import KCubeDCServo
from Thorlabs.MotionControl.GenericMotorCLI import DeviceConfiguration

from devices.base import DeviceBase, DeviceConnectionError, DeviceOperationError


class ThorlabsRotator(DeviceBase):
    """Thorlabs 旋转电机 (CageRotator / KCube)。

    Usage:
        rot = ThorlabsRotator(name="vis_rotator", driver="Cage", serial="55358884")
        rot.connect()
        rot.home()
        rot.move_to(45.58)
    """

    def __init__(self, name: str = "rotator", driver: str = "Cage", serial: str = ""):
        super().__init__(name)
        self._driver_type = driver
        self._serial = str(serial)
        self._device = None

    def connect(self) -> bool:
        try:
            DeviceManagerCLI.BuildDeviceList()
            serial_no = self._serial

            if self._driver_type == "Cage":
                self._device = CageRotator.CreateCageRotator(serial_no)
            elif self._driver_type == "KCube":
                self._device = KCubeDCServo.CreateKCubeDCServo(serial_no)
            else:
                raise ValueError(f"未知的驱动器类型: {self._driver_type}")

            self._device.Connect(serial_no)

            if not self._device.IsSettingsInitialized():
                self._device.WaitForSettingsInitialized(10000)
                assert self._device.IsSettingsInitialized() is True

            self._device.StartPolling(250)
            time.sleep(0.25)
            self._device.EnableDevice()
            time.sleep(0.25)

            device_info = self._device.GetDeviceInfo()
            print(f"[{self.name}] 已连接: {device_info.Description}")

            self._device.LoadMotorConfiguration(
                serial_no,
                DeviceConfiguration.DeviceSettingsUseOptionType.UseDeviceSettings
            )

            self._connected = True
            return True
        except Exception as e:
            raise DeviceConnectionError(self.name, str(e))

    def disconnect(self) -> None:
        try:
            if self._device:
                self._device.StopPolling()
                self._device.Disconnect()
            self._connected = False
            print(f"[{self.name}] 已断开")
        except Exception:
            pass

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def status(self) -> dict:
        s = super().status
        s.update({"driver": self._driver_type, "serial": self._serial})
        return s

    def home(self):
        """电机归零。"""
        if not self._device:
            raise DeviceOperationError(self.name, "home", "设备未连接")
        print(f"[{self.name}] 正在归零...")
        self._device.Home(60000)
        print(f"[{self.name}] 归零完成")

    def move_to(self, position: float):
        """移动电机到绝对角度位置。

        Args:
            position: 目标角度 (度)
        """
        if not self._device:
            raise DeviceOperationError(self.name, "move_to", "设备未连接")
        print(f"[{self.name}] 移动到 {position}°")
        self._device.MoveTo(Decimal(position), 60000)
        print(f"[{self.name}] 移动完成")

    def stop(self):
        """急停。"""
        if self._device:
            self._device.Stop(0)
            print(f"[{self.name}] 已停止")
