"""光谱仪设备驱动。

封装 Princeton Instruments LightField Automation API。
支持 PyLon / ProEM CCD 相机。

注意：此模块依赖 LightField 运行时环境和 Kinesis .NET 库，
在无硬件环境下无法 import。
"""

import os
import sys
import clr
from typing import Optional

# 添加 LightField 路径
sys.path.append(os.environ.get('LIGHTFIELD_ROOT', ''))
sys.path.append(os.path.join(os.environ.get('LIGHTFIELD_ROOT', ''), 'AddInViews'))
clr.AddReference('PrincetonInstruments.LightFieldViewV5')
clr.AddReference('PrincetonInstruments.LightField.AutomationV5')
clr.AddReference('PrincetonInstruments.LightFieldAddInSupportServices')

from System.IO import Path
from System.Threading import AutoResetEvent
from System import String
from System.Collections.Generic import List

from PrincetonInstruments.LightField.Automation import Automation
from PrincetonInstruments.LightField.AddIns import (
    ExperimentSettings, SpectrometerSettings,
    CameraSettings, DeviceType
)

from devices.base import DeviceBase, DeviceConnectionError, DeviceOperationError


class LightFieldSpectrometer(DeviceBase):
    """Princeton Instruments 光谱仪 (通过 LightField 软件控制)。

    Usage:
        spec = LightFieldSpectrometer(
            name="spectrometer",
            experiment_name="HRBBSFGVS-PyLon",
            file_path="D:\\data"
        )
        spec.connect()
        spec.set_exposure_time(60000)
        spec.set_center_wavelength(475)
        spec.save_file("my_sample")
        spec.acquire()
    """

    def __init__(
        self,
        name: str = "spectrometer",
        experiment_name: str = "HRBBSFGVS-PyLon",
        file_path: str = "",
    ):
        super().__init__(name)
        self._experiment_name = experiment_name
        self._file_path = file_path
        self._auto = None
        self._app = None
        self._exp = None
        self._evt = None

    def connect(self) -> bool:
        try:
            self._auto = Automation(True, List[String]())
            self._app = self._auto.LightFieldApplication
            self._exp = self._app.Experiment
            self._evt = AutoResetEvent(False)

            self._exp.Load(self._experiment_name)

            if not self._device_found():
                raise DeviceConnectionError(self.name, "未找到相机设备")

            if self._file_path:
                self._exp.SetValue(
                    ExperimentSettings.FileNameGenerationDirectory,
                    self._file_path
                )

            self._connected = True
            print(f"[{self.name}] 已连接, 实验: {self._experiment_name}")
            return True
        except Exception as e:
            raise DeviceConnectionError(self.name, str(e))

    def _device_found(self) -> bool:
        for device in self._exp.ExperimentDevices:
            if device.Type == DeviceType.Camera:
                return True
        return False

    def disconnect(self) -> None:
        try:
            if self._auto:
                self._auto.Dispose()
                self._auto = None
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
        s["experiment_name"] = self._experiment_name
        s["file_path"] = self._file_path
        return s

    def set_file_path(self, path: str):
        self._file_path = path
        if self._connected and self._exp:
            self._exp.SetValue(
                ExperimentSettings.FileNameGenerationDirectory, path
            )

    def save_file(self, filename: str):
        if not self._exp:
            raise DeviceOperationError(self.name, "save_file", "设备未连接")
        self._exp.SetValue(
            ExperimentSettings.FileNameGenerationBaseFileName,
            Path.GetFileName(filename)
        )
        self._exp.SetValue(ExperimentSettings.FileNameGenerationAttachIncrement, False)
        self._exp.SetValue(ExperimentSettings.FileNameGenerationAttachDate, False)
        self._exp.SetValue(ExperimentSettings.FileNameGenerationAttachTime, False)

    def set_frames_number(self, frames: int):
        if not self._exp:
            raise DeviceOperationError(self.name, "set_frames_number", "设备未连接")
        self._exp.SetValue(ExperimentSettings.AcquisitionFramesToStore, str(frames))

    def set_center_wavelength(self, nm: float):
        if not self._exp:
            raise DeviceOperationError(self.name, "set_center_wavelength", "设备未连接")
        self._exp.SetValue(SpectrometerSettings.GratingCenterWavelength, str(nm))

    def set_exposure_time(self, ms: int):
        if not self._exp:
            raise DeviceOperationError(self.name, "set_exposure_time", "设备未连接")
        self._exp.SetValue(CameraSettings.ShutterTimingExposureTime, str(ms))

    def set_grating(self, grating: str):
        if not self._exp:
            raise DeviceOperationError(self.name, "set_grating", "设备未连接")
        self._exp.SetValue(SpectrometerSettings.GratingSelected, grating)

    def get_pixels(self) -> int:
        if not self._exp:
            raise DeviceOperationError(self.name, "get_pixels", "设备未连接")
        return int(self._exp.GetValue(CameraSettings.SensorInformationActiveAreaWidth))

    def acquire(self) -> None:
        """触发光谱采集（阻塞直到完成）。"""
        if not self._exp or not self._evt:
            raise DeviceOperationError(self.name, "acquire", "设备未连接")

        self._evt.Reset()

        def _on_done(sender, event_args):
            print(f"[{self.name}] 采集完成")
            self._evt.Set()

        self._exp.ExperimentCompleted += _on_done
        self._exp.Acquire()
        self._evt.WaitOne()
        self._exp.ExperimentCompleted -= _on_done
