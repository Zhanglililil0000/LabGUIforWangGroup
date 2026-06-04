"""光谱仪操作。封装 LightFieldSpectrometer 的原子操作。"""

import csv
import numpy as np

from operations.base import Operation, OperationStatus
from core.signal_processing import compute_differential_signal


class SetExposure(Operation):
    """设置曝光时间。

    Usage:
        SetExposure(60000)  # 60s
    """

    def __init__(self, exposure_ms: int):
        super().__init__(f"SetExposure({exposure_ms}ms)")
        self.exposure_ms = exposure_ms

    def execute(self, ctx) -> dict:
        spec = ctx.get_device("spectrometer")
        spec.set_exposure_time(self.exposure_ms)
        return {"exposure_ms": self.exposure_ms}


class SetWavelength(Operation):
    """设置光栅中心波长。

    Usage:
        SetWavelength(475)  # 475 nm
    """

    def __init__(self, wavelength_nm: float):
        super().__init__(f"SetWavelength({wavelength_nm}nm)")
        self.wavelength_nm = wavelength_nm

    def execute(self, ctx) -> dict:
        spec = ctx.get_device("spectrometer")
        spec.set_center_wavelength(self.wavelength_nm)
        return {"wavelength_nm": self.wavelength_nm}


class AcquireSpectrum(Operation):
    """采集光谱并保存。

    支持单帧和多帧模式。
    多帧模式下自动计算差分信号 (ret, ret1, ret2)。

    Usage:
        # 单帧
        AcquireSpectrum("sample_single", exposure_ms=60000, frames=1)
        # 多帧 SRS/SFG
        AcquireSpectrum("sample_diff", exposure_ms=60000, frames=10000, compute_diff=True)
    """

    def __init__(
        self,
        data_name: str,
        exposure_ms: int = 60000,
        frames: int = 1,
        compute_diff: bool = False,
    ):
        super().__init__(f"Acquire({data_name})")
        self.data_name = data_name
        self.exposure_ms = exposure_ms
        self.frames = frames
        self.compute_diff = compute_diff

    def execute(self, ctx) -> dict:
        spec = ctx.get_device("spectrometer")

        # 设置采集参数
        spec.set_exposure_time(self.exposure_ms)
        spec.set_frames_number(self.frames)
        spec.save_file(self.data_name)

        # 采集
        spec.acquire()

        result = {
            "data_name": self.data_name,
            "exposure_ms": self.exposure_ms,
            "frames": self.frames,
        }

        # 读取并处理数据
        file_path = ctx.config.get("output.base_path", "")
        csv_path = f"{file_path}\\{self.data_name}.csv" if file_path else f"{self.data_name}.csv"

        try:
            wavelengths, intensities = self._parse_csv(csv_path, spec)
            result["n_pixels"] = len(wavelengths)

            if self.compute_diff and self.frames > 1:
                ret, ret1, ret2 = compute_differential_signal(intensities, self.frames)
                self._save_ret(csv_path, wavelengths, ret, ret1, ret2)
                result["diff_computed"] = True

            ctx.data["last_spectrum"] = {
                "wavelengths": wavelengths,
                "intensities": intensities[-1] if len(intensities) > 1 else intensities[0],
            }
        except Exception as e:
            ctx.logger.warning(f"数据读取失敗: {e}")

        return result

    @staticmethod
    def _parse_csv(filepath: str, spec) -> tuple:
        """从 LightField 输出的 CSV 解析波长和强度。"""
        pixels = spec.get_pixels()
        wavelength = []
        intensities_all = []
        current_intensity = []
        pixel_idx = 0

        with open(filepath, "r") as f:
            for line in f:
                x, y = map(float, line.split(","))
                if pixel_idx < pixels:
                    wavelength.append(x)
                current_intensity.append(y)
                pixel_idx += 1
                if pixel_idx % pixels == 0:
                    intensities_all.append(np.array(current_intensity))
                    current_intensity = []

        return wavelength, intensities_all

    @staticmethod
    def _save_ret(filepath: str, wavelengths, ret, ret1, ret2):
        """保存差分信号结果。"""
        base = filepath.rsplit(".", 1)[0]
        for suffix, data in [("_ret", ret), ("_ret1", ret1), ("_ret2", ret2)]:
            with open(f"{base}{suffix}.csv", "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerows(list(np.array([wavelengths, data]).T))
