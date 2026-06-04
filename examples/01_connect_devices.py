"""
示例 01: 连接设备

学习目标：
- 使用 Config 加载设备配置
- 逐个连接设备并检查状态
- 正确断开设备连接

运行前请修改 configs/devices.yaml 中的设备参数。
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config


def main():
    print("=" * 50)
    print("示例 01: 连接设备")
    print("=" * 50)

    # 1. 加载设备配置
    config = Config("configs/devices.yaml")
    devices_config = config.get_devices()
    print(f"\n配置文件中有 {len(devices_config)} 个设备:\n")

    for name, cfg in devices_config.items():
        print(f"  [{name}]")
        for key, val in cfg.items():
            print(f"    {key}: {val}")
        print()

    # 2. 尝试连接设备（这里只演示配置加载和状态查询模式）
    # 在实际环境中，可以逐设备连接:
    #
    # from devices.spectrometer import LightFieldSpectrometer
    # spec = LightFieldSpectrometer(
    #     name="spectrometer",
    #     experiment_name=config.get("spectrometer.experiment_name"),
    # )
    # spec.connect()
    # print(spec.status)
    # spec.disconnect()

    print("配置加载成功！")
    print("实际连接设备请参考具体示例 (02-10)。")


if __name__ == "__main__":
    main()
