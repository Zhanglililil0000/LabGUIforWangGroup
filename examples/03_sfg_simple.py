"""
示例 03: 简单 SFG 实验 (SSP + PPP)

学习目标：
- 使用 Pipeline 编排实验步骤
- 连接光谱仪 + 旋转电机
- 采集不同偏振组合的光谱

运行前：
1. 确保 LightField 已打开
2. 修改 configs/devices.yaml 中的序列号
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config
from core.context import ExperimentContext
from core.pipeline import Pipeline, RetryStrategy
from operations.motor_ops import MotorHome, MotorMoveTo
from operations.spectrometer_ops import AcquireSpectrum, SetExposure, SetWavelength
from operations.utility_ops import SetPolarization


def main():
    print("=" * 50)
    print("示例 03: 简单 SFG 实验")
    print("=" * 50)

    # 1. 加载配置
    config = Config("configs/experiments/sfg_example.yaml")

    # 2. 创建实验上下文
    ctx = ExperimentContext(config=config)

    # 3. 创建设备（需要硬件环境）
    # from devices.spectrometer import LightFieldSpectrometer
    # from devices.motor import ThorlabsRotator
    #
    # spec = LightFieldSpectrometer(
    #     name="spectrometer",
    #     experiment_name=config.get("spectrometer.experiment_name"),
    #     file_path=config.get("output.base_path"),
    # )
    # spec.connect()
    # ctx.set_device("spectrometer", spec)
    #
    # vis_rot = ThorlabsRotator(
    #     name="vis_rotator",
    #     driver=config.get("devices.vis_rotator.driver"),
    #     serial=config.get("devices.vis_rotator.serial"),
    # )
    # vis_rot.connect()
    # ctx.set_device("vis_rotator", vis_rot)
    #
    # sfg_rot = ThorlabsRotator(
    #     name="sfg_rotator",
    #     driver=config.get("devices.sfg_rotator.driver"),
    #     serial=config.get("devices.sfg_rotator.serial"),
    # )
    # sfg_rot.connect()
    # ctx.set_device("sfg_rotator", sfg_rot)

    # 4. 编排管道
    sample = config.get("output.sample_name")
    exposure = config.get("spectrometer.exposure_ms")
    wavelength = config.get("spectrometer.center_wavelength_nm")

    pipeline = Pipeline("SFG_Simple", [
        # 初始化
        MotorHome("vis_rotator"),
        MotorHome("sfg_rotator"),

        # 设置光谱仪
        SetWavelength(wavelength),
        SetExposure(exposure),

        # SSP 采集
        SetPolarization("ssp", config),
        AcquireSpectrum(f"{sample}_ssp", exposure_ms=exposure),

        # PPP 采集
        SetPolarization("ppp", config),
        AcquireSpectrum(f"{sample}_ppp", exposure_ms=exposure),

        # 归位
        MotorHome("vis_rotator"),
        MotorHome("sfg_rotator"),
    ],
        on_error=RetryStrategy(max_retries=1, delay_seconds=5),
    )

    print(f"\n管道 '{pipeline.name}' 包含 {len(pipeline.steps)} 个步骤:")
    for i, step in enumerate(pipeline.steps):
        print(f"  {i+1}. {step.name}")

    # 5. 运行实验（需要硬件环境）
    # result = pipeline.run(ctx)
    # print(f"\n实验完成: {result.status}")
    # print(f"成功: {result.completed_steps}, 失败: {result.failed_steps}")
    #
    # # 6. 断开设备
    # spec.disconnect()
    # vis_rot.disconnect()
    # sfg_rot.disconnect()

    print("\n管道步骤已编排完成。在有硬件环境的电脑上运行此脚本即可执行。")


if __name__ == "__main__":
    main()
