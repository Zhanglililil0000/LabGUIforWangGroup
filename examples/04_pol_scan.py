"""
示例 04: 偏振扫描实验 (Polarization Scan)
==========================================
扫描一个旋转电机的角度（如 SFG 偏振角），在每个角度点采集光谱。

实验流程:
  1. 连接光谱仪 + 2 个旋转电机 + （可选）延迟线
  2. 两个电机归零
  3. 固定电机移动到指定偏振角
  4. 扫描电机从 start_angle 到 end_angle 按 step 步进
  5. 每步: 移动目标角度 → 采集光谱 → 保存
  6. 全部归零、断开设备

配置参数说明:
  - scan.scan_device: 扫描哪个电机 ("vis_rotator" 或 "sfg_rotator")
  - scan.start_angle / end_angle / step: 扫描范围和步长
  - scan.fixed_device + fixed_angle_key: 固定电机的角度

运行方式（有硬件时）:
  python examples/04_pol_scan.py

运行方式（无硬件，仅预览步骤）:
  python examples/04_pol_scan.py
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config
from core.context import ExperimentContext
from core.pipeline import Pipeline, AbortStrategy
from operations.motor_ops import MotorHome, MotorMoveTo
from operations.spectrometer_ops import AcquireSpectrum, SetExposure, SetWavelength
from operations.utility_ops import LogMessage, Sleep


def main():
    print("=" * 55)
    print("  偏振扫描实验")
    print("=" * 55)

    # ════════════════════════════════════════════════════════════
    # 1. 加载配置
    # ════════════════════════════════════════════════════════════
    config = Config("configs/experiments/pol_scan_example.yaml")

    sample = config.get("output.sample_name", "sample")
    base_path = config.get("output.base_path", "D:\\SFGData")
    exposure = config.get("spectrometer.exposure_ms", 60000)
    wavelength = config.get("spectrometer.center_wavelength_nm", 475)
    frames = config.get("spectrometer.frames", 1)

    # 扫描参数
    scan_device = config.get("scan.scan_device", "sfg_rotator")
    start_angle = config.get("scan.start_angle", 10.0)
    end_angle = config.get("scan.end_angle", 110.0)
    step = config.get("scan.step", 1.0)
    fixed_device = config.get("scan.fixed_device", "vis_rotator")
    fixed_angle_key = config.get("scan.fixed_angle_key", "vis_angle_p")

    # 解析固定电机的实际角度值
    fixed_angle_value = config.get(f"polarization.{fixed_angle_key}")
    if fixed_angle_value is None:
        raise ValueError(f"配置中未找到 polarization.{fixed_angle_key}，请设置偏振基础角度")

    # ════════════════════════════════════════════════════════════
    # 2. 生成扫描角度列表
    # ════════════════════════════════════════════════════════════
    angles = list(np.arange(start_angle, end_angle + step * 0.5, step))
    angles = [round(a, 2) for a in angles]  # 避免浮点累积误差

    print(f"\n扫描配置:")
    print(f"  样品: {sample}")
    print(f"  扫描电机: {scan_device} ({start_angle}° → {end_angle}°, 步长 {step}°)")
    print(f"  固定电机: {fixed_device} = {fixed_angle_value}°")
    print(f"  曝光时间: {exposure}ms | 中心波长: {wavelength}nm")
    print(f"  总步数: {len(angles)}")
    print(f"  预计耗时: ~{len(angles) * (exposure/1000 + 5):.0f}s")

    # ════════════════════════════════════════════════════════════
    # 3. 创建设备并连接（需要硬件环境）
    # ════════════════════════════════════════════════════════════
    ctx = ExperimentContext(config=config)

    # ---- 取消注释以下代码以实际运行 ----
    # from devices.spectrometer import LightFieldSpectrometer
    # from devices.motor import ThorlabsRotator
    #
    # spec = LightFieldSpectrometer(
    #     name="spectrometer",
    #     experiment_name=config.get("spectrometer.experiment_name"),
    #     file_path=base_path,
    # )
    # spec.connect()
    # ctx.set_device("spectrometer", spec)
    #
    # vis_rot = ThorlabsRotator(
    #     name="vis_rotator",
    #     driver=config.get("devices.vis_rotator.driver", "Cage"),
    #     serial=config.get("devices.vis_rotator.serial", "55358884"),
    # )
    # vis_rot.connect()
    # ctx.set_device("vis_rotator", vis_rot)
    #
    # sfg_rot = ThorlabsRotator(
    #     name="sfg_rotator",
    #     driver=config.get("devices.sfg_rotator.driver", "Cage"),
    #     serial=config.get("devices.sfg_rotator.serial", "55355234"),
    # )
    # sfg_rot.connect()
    # ctx.set_device("sfg_rotator", sfg_rot)

    # ════════════════════════════════════════════════════════════
    # 4. 编排管道
    # ════════════════════════════════════════════════════════════
    steps = []

    # 步骤 1: 两个电机归零
    steps.append(LogMessage(f"偏振扫描开始: {sample}"))
    steps.append(MotorHome("vis_rotator"))
    steps.append(MotorHome("sfg_rotator"))

    # 步骤 2: 设置光谱仪参数
    steps.append(SetWavelength(wavelength))
    steps.append(SetExposure(exposure))

    # 步骤 3: 固定电机移动到指定偏振角
    steps.append(LogMessage(f"固定电机 {fixed_device} → {fixed_angle_value}°"))
    steps.append(MotorMoveTo(fixed_device, fixed_angle_value))

    # 步骤 4: 扫描循环
    for angle in angles:
        # 文件名: gold_P_29.01 → gold_P_29_01
        angle_str = f"{angle:.2f}".replace(".", "_")
        data_name = f"{sample}_P{angle_str}"

        steps.append(LogMessage(f"扫描: {scan_device} → {angle}°"))
        steps.append(MotorMoveTo(scan_device, angle))
        steps.append(Sleep(0.5))  # 等待电机稳定
        steps.append(AcquireSpectrum(
            data_name=data_name,
            exposure_ms=exposure,
            frames=frames,
        ))

    # 步骤 5: 归位
    steps.append(LogMessage("扫描结束，设备归位"))
    steps.append(MotorHome("vis_rotator"))
    steps.append(MotorHome("sfg_rotator"))

    # 创建管道
    pipeline = Pipeline("PolarizationScan", steps, on_error=AbortStrategy())

    print(f"\n管道 '{pipeline.name}' 共 {len(steps)} 个步骤:")
    for i, step in enumerate(steps):
        print(f"  {i+1:3d}. {step.name}")

    # ════════════════════════════════════════════════════════════
    # 5. 运行实验（需要硬件环境）
    # ════════════════════════════════════════════════════════════
    # result = pipeline.run(ctx)
    # print(f"\n{'='*55}")
    # print(f"实验结果: {result.status}")
    # print(f"成功: {result.completed_steps} | 失败: {result.failed_steps}")
    #
    # spec.disconnect()
    # vis_rot.disconnect()
    # sfg_rot.disconnect()

    print(f"\n{pipeline.name} 管道已编排完成。")
    print("在有硬件环境的电脑上取消注释设备连接和 pipeline.run(ctx) 即可执行。")


if __name__ == "__main__":
    main()
