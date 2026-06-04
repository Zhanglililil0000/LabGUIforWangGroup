# CommandMode — IDE 模式使用手册

> **模式**: IDE / 命令行 / Python 脚本直接控制  
> **版本**: v2.0  
> **日期**: 2026-06-03  
> **适用范围**: SFG（和频振动光谱）与 SRS（受激拉曼散射）实验

---

## 目录

1. [项目概述](#项目概述)
2. [文件结构](#文件结构)
3. [环境要求](#环境要求)
4. [配置设备参数](#配置设备参数)
5. [快速开始](#快速开始)
6. [核心概念](#核心概念)
7. [可用操作列表](#可用操作列表)
8. [实验示例](#实验示例)
9. [动手编写自己的实验](#动手编写自己的实验)
10. [故障排查](#故障排查)
11. [IDE 模式 vs Web GUI 模式](#ide-模式-vs-web-gui-模式)

---

## 项目概述

本系统是一个基于 Python 的分层架构实验控制平台，用于控制 **SFG（Sum Frequency Generation，和频振动光谱）** 和 **SRS（Stimulated Raman Scattering，受激拉曼散射）** 实验的全流程仪器设备。

项目提供两种使用模式：

| 模式 | 适用场景 | 入口 |
|------|---------|------|
| **IDE 模式**（本手册） | Python 脚本开发、调试、自动化、批量实验 | `examples/*.py` 或直接编写脚本 |
| **Web GUI 模式** | 日常操作、可视化编辑、模板快存快取 | 启动 `web/app.py` 在浏览器操作 |

---

## 文件结构

```
CommandMode/
├── README.md                          ← 本手册
├── API/                               ← 原始硬件驱动 (DLL 封装)
│   ├── ThorlabsAPI.py                 #     Thorlabs 旋转电机 (.NET)
│   ├── LightFieldAPI.py               #     Princeton 光谱仪 (Automation)
│   ├── feinixsAPI.py                  #     Feinixs 延迟线 (.NET)
│   ├── ThorlabsTLPM.py                #     Thorlabs 功率计 (TLPM VISA)
│   ├── KEYENCEAPI.py                  #     KEYENCE 距离传感器 (CL3_IF.dll)
│   ├── SmacqAPI.py                    #     Smacq 采集卡 (usb-1000.dll)
│   ├── AndorAPI.py                    #     Andor 相机
│   └── verticalStageAPI.py            #     串口垂直位移台
│
├── configs/                           ← 配置文件 (所有参数在这里改)
│   ├── devices.yaml                   #     设备序列号/端口/驱动类型
│   ├── defaults.yaml                  #     实验默认值 & 模式定义 (SFG/SRS/标定)
│   ├── experiments/                   #     实验配方 (含参数)
│   │   ├── sfg_example.yaml           #         SFG 示例
│   │   ├── srs_example.yaml           #         SRS 示例
│   │   └── pol_scan_example.yaml      #         偏振扫描示例
│   └── templates/                     #     模板 (Web GUI 加载用)
│       ├── sfg/
│       ├── srs/
│       └── calibration/
│
├── core/                              ← 核心框架层
│   ├── config.py                      #     配置管理 (YAML 加载/继承/嵌套访问)
│   ├── context.py                     #     运行时上下文 (设备池/数据空间/日志)
│   ├── pipeline.py                    #     管道编排引擎 (顺序执行/错误策略)
│   ├── registry.py                    #     设备 & 操作注册中心
│   └── signal_processing.py           #     信号处理算法 (差分信号/偏振拟合)
│
├── devices/                           ← 设备驱动层 (统一接口)
│   ├── motor.py                       #     Thorlabs 旋转电机
│   ├── spectrometer.py                #     Princeton 光谱仪
│   ├── delay_stage.py                 #     Feinixs 延迟线
│   ├── power_meter.py                 #     Thorlabs 功率计
│   ├── distance_sensor.py             #     KEYENCE 距离传感器
│   ├── vertical_stage.py              #     垂直位移台
│   └── daq_card.py                    #     Smacq 采集卡
│
├── operations/                        ← 原子操作层 (管道可执行单元)
│   ├── motor_ops.py                   #     MotorHome / MotorMoveTo
│   ├── spectrometer_ops.py            #     SetExposure / SetWavelength / AcquireSpectrum
│   ├── delay_ops.py                   #     DelayStageHome / DelayStageMoveTo
│   ├── utility_ops.py                 #     SetPolarization / Sleep / LogMessage
│   └── base.py                        #     Operation 抽象基类
│
├── examples/                          ← 示例脚本 (从这里开始)
│   ├── 01_connect_devices.py          #     连接设备、查看列表
│   ├── 03_sfg_simple.py               #     SFG SSP+PPP 完整实验
│   ├── 04_pol_scan.py                 #     偏振扫描实验
│   └── 09_pipeline_workflow.py        #     Mock 模式管道编排 (无需硬件)
│
├── docs/                              ← 设计文档
│   └── specs/                         #     需求与架构文档
│
├── legacy/                            ← 旧版代码归档
│   ├── experiments/                   #     旧版实验脚本 (参考用)
│   └── utils/                         #     旧版工具脚本
│
├── resources/                         ← 原生 DLL 资源文件
│   ├── KEYENCE/
│   ├── Smacq/
│   ├── ThorlabsPowerMeter/
│   └── lib/
│
├── tests/                             ← 单元测试
├── web/                               ← Web GUI (见 web/README.md)
│   └── ...
│
└── recipes/                           ← 预定义实验配方 (规划中)
```

---

## 环境要求

### 硬件

| 用途 | 设备 |
|------|------|
| 光谱采集 | Princeton PyLon / ProEM CCD + LightField 软件 |
| 可见光偏振 | Thorlabs CageRotator / KCube (VIS 偏振) |
| SFG 偏振 | Thorlabs CageRotator / KCube (SFG 偏振) |
| Raman 偏振 | Thorlabs CageRotator / KCube (Pump 偏振) |
| 时间延迟 | Feinixs 光学延迟线 |
| 功率测量 | Thorlabs PM100D 系列功率计 |
| 距离测量 | KEYENCE CL-3000 激光距离传感器 |
| 样品高度 | 串口垂直电动位移台 |
| 模拟信号 | Smacq USB-1000 采集卡 |

### 软件

- **Python 3.9+** (Windows 64-bit)
- **Thorlabs Kinesis** (旋转电机驱动)
- **Princeton Instruments LightField** (光谱仪控制软件)
- .NET Framework 4.8 (旋转电机和延迟线的 `clr` 调用需要)

```powershell
pip install pyserial pyyaml numpy fastapi uvicorn pythonnet
```

---

## 配置设备参数

### 1. 修改设备序列号和端口

编辑 **`configs/devices.yaml`**：

```yaml
devices:
  vis_rotator:
    type: "thorlabs_rotator"
    driver: "Cage"
    serial: "55358884"              # ← 修改为你的序列号

  sfg_rotator:
    serial: "55355234"              # ← 修改为你的序列号

  raman_rotator:
    serial: "55169544"              # ← 修改为你的序列号

  delay_stage:
    port: "COM4"                    # ← 修改为你的 COM 口

  spectrometer:
    type: "lightfield"
    experiment_name: "HRBBSFGVS-PyLon"  # ← 修改为你的 LightField 预设

  power_meter:
    wavelength_nm: 532.0

  distance_sensor:
    device_id: 0

  vertical_stage:
    port: "COM9"                    # ← 修改为你的 COM 口
```

### 2. 修改实验默认参数

编辑 **`configs/defaults.yaml`**，可以修改：
- 每种模式使用的 LightField 预设名称
- 每种模式可用的设备列表
- 默认波长和曝光时间

### 3. 创建自己的实验配置

在 `configs/experiments/` 下新建 YAML 文件，通过 `extends` 继承默认配置：

```yaml
extends: "../defaults.yaml"

output:
  base_path: "D:\\MyExperiment"

spectrometer:
  wavelength_nm: 475
  exposure_ms: 60000

motor:
  vis_home: true
  vis_angle_s: 45.58
  vis_angle_p: 90.58
```

---

## 快速开始

### 示例 1：查看设备列表（无需硬件，读取配置即可）

```powershell
cd CommandMode
python examples/01_connect_devices.py
```

### 示例 2：管道编排练习（Mock 模式，不需要硬件）

```powershell
python examples/09_pipeline_workflow.py
```

输出示例：
```
Pipeline: MyExperiment
  #1 MotorHome(vis_rotator)       ... DONE
  #2 SetPolarization(ssp)         ... DONE
  #3 AcquireSpectrum(sample_ssp)  ... DONE
  完成: 3/3 步
```

### 示例 3：完整 SFG 实验（需要硬件连接）

```powershell
python examples/03_sfg_simple.py
```

---

## 核心概念

### 管道 (Pipeline)

实验流程由 **管道（Pipeline）** 编排，按顺序执行一系列原子操作：

```
管道 = 开始 → 操作1 → 操作2 → ... → 操作N → 完成
               ↓失败    ↓失败              ↓失败
             重试     跳过               中止  (ErrorStrategy)
```

三种错误策略：
- **RetryStrategy** — 失败后重试指定次数
- **SkipStrategy** — 失败后跳过，继续下一步
- **AbortStrategy** — 失败后立即中止管道

### 运行时上下文 (ExperimentContext)

管道执行过程中的共享状态：

```python
ctx = ExperimentContext(config=config)
# ctx.get_device("vis_rotator")  → 获取设备实例
# ctx.data["last_spectrum"]      → 读写共享数据
# ctx.logger                      → 日志输出
```

### 原子操作 (Operation)

最小的可编排执行单元，每个操作封装一个具体的设备动作。操作通过 `execute(ctx)` 方法执行，自动接收上下文中的设备实例。

---

## 可用操作列表

### 电机操作

| 操作 | 参数 | 说明 |
|------|------|------|
| `MotorHome()` | `device` — 设备名 (如 `"vis_rotator"`) | 旋转台归零 |
| `MotorMoveTo()` | `device` `position` — 角度 | 旋转台移动到指定角度 |

### 延迟线操作

| 操作 | 参数 | 说明 |
|------|------|------|
| `DelayStageHome()` | `device` `axis` — 轴名 | 延迟线归零 |
| `DelayStageMoveTo()` | `device` `axis` `position` | 延迟线移动到指定位置 |

### 光谱仪操作

| 操作 | 参数 | 说明 |
|------|------|------|
| `SetExposure()` | `exposure_ms` — 曝光时间 (ms) | 设置硬件曝光时间 |
| `SetWavelength()` | `wavelength_nm` — 中心波长 (nm) | 设置光栅中心波长 |
| `SetGrating()` | `grating` — 光栅 ("300"/"600"/"1200"/"1500") | 切换光栅 |
| `AcquireSpectrum()` | `name` `exposure_ms` `frames` `compute_diff` | 采集光谱。多帧模式下自动差分计算 |

### 偏振操作

| 操作 | 参数 | 说明 |
|------|------|------|
| `SetPolarization()` | `mode` — 偏振模式 | SSP / PPP / SPS / PSS / SPP / PSP |

**偏振角度映射表：**

| 模式 | VIS 旋转台 | SFG 旋转台 | 含义 |
|------|-----------|-----------|------|
| SSP | 45.58° (S) | 29.01° (S) | SFG-S, VIS-S, IR-P |
| PPP | 90.58° (P) | 74.01° (P) | SFG-P, VIS-P, IR-P |
| SPS | 45.58° (S) | 74.01° (P) | SFG-S, VIS-P, IR-S |
| PSS | 90.58° (P) | 29.01° (S) | SFG-P, VIS-S, IR-S |

> 角度值在 `configs/experiments/sfg_example.yaml` 中定义，可根据实际设备修改。

### SRS 偏振操作

SRS 模式使用 Raman 旋转台控制 Pump (532nm) 偏振：

| 模式 | Raman 旋转台角度 | 含义 |
|------|----------------|------|
| VV | 42.47° | Pump 垂直, Probe 垂直 |
| VH | 87.47° | Pump 垂直, Probe 水平 |

### 辅助操作

| 操作 | 参数 | 说明 |
|------|------|------|
| `Sleep()` | `seconds` — 等待秒数 | 暂停指定时间 |
| `LogMessage()` | `message` `level` — info/warn/error | 输出日志 |
| `ReadPower()` | `wavelength_nm` — 波长 | 读取功率计 |
| `ReadDistance()` | 无 | 读取距离传感器 |
| `VerticalStageMove()` | `device` `axis` `position` | 垂直台移动 |

---

## 实验示例

### SFG SSP+PPP 实验

```python
from core.config import Config
from core.context import ExperimentContext
from core.pipeline import Pipeline
from operations.motor_ops import MotorHome
from operations.spectrometer_ops import SetWavelength, SetExposure, AcquireSpectrum
from operations.utility_ops import SetPolarization

# 加载配置
config = Config("configs/experiments/sfg_example.yaml")
ctx = ExperimentContext(config=config)

# 构建管道
pipeline = Pipeline("SFG_SSP_PPP", [
    # 初始化
    MotorHome("vis_rotator"),
    MotorHome("sfg_rotator"),
    SetWavelength(475),
    SetExposure(60000),

    # SSP 采集
    SetPolarization("ssp", config),
    AcquireSpectrum("methanol_ssp", exposure_ms=60000, frames=1),

    # PPP 采集
    SetPolarization("ppp", config),
    AcquireSpectrum("methanol_ppp", exposure_ms=60000, frames=1),
])

result = pipeline.run(ctx)
print(f"完成: {result.completed_steps}/{result.total_steps} 步")
```

### SRS 偏振扫描实验

```python
pipeline = Pipeline("SRS_Pol_Scan", [
    MotorHome("raman_rotator"),

    # VV 偏振
    MotorMoveTo("raman_rotator", 42.47),
    SetWavelength(630),
    AcquireSpectrum("srs_vv", exposure_ms=1000, frames=10000, compute_diff=True),

    # VH 偏振
    MotorMoveTo("raman_rotator", 87.47),
    AcquireSpectrum("srs_vh", exposure_ms=1000, frames=10000, compute_diff=True),
])

result = pipeline.run(ctx)
```

### 偏振标定扫描

```python
import numpy as np

# VIS 旋转台功率标定
pipeline = Pipeline("VIS_Pol_Cal", [])

for angle in np.arange(20, 130, 1.0):
    pipeline.add_step(MotorMoveTo("vis_rotator", angle))
    pipeline.add_step(ReadPower(532.0))
    pipeline.add_step(Sleep(1.0))

result = pipeline.run(ctx)
```

---

## 动手编写自己的实验

1. **创建配置文件**

   在 `configs/experiments/` 下新建 `my_experiment.yaml`：
   ```yaml
   extends: "../defaults.yaml"
   output:
     base_path: "D:\\MyData"
   spectrometer:
     wavelength_nm: 475
     exposure_ms: 60000
   ```

2. **编写实验脚本**

   ```python
   import sys
   sys.path.insert(0, ".")  # 确保能导入项目模块

   from core.config import Config
   from core.context import ExperimentContext
   from core.pipeline import Pipeline
   from operations.spectrometer_ops import *
   from operations.motor_ops import *
   from operations.utility_ops import *

   config = Config("configs/experiments/my_experiment.yaml")
   ctx = ExperimentContext(config=config)

   pipeline = Pipeline("MyExperiment", [
       MotorHome("vis_rotator"),
       SetWavelength(475),
       AcquireSpectrum("my_data", exposure_ms=60000, frames=1),
   ])

   result = pipeline.run(ctx)
   for step in result.steps:
       print(f"  {step.name}: {step.status.value}")
   ```

3. **运行**

   ```powershell
   python my_experiment.py
   ```

---

## 故障排查

### 设备连接失败

1. 检查 `configs/devices.yaml` 中的序列号/COM 口是否正确
2. 检查 Thorlabs Kinesis / LightField 是否已启动
3. 使用 `python examples/01_connect_devices.py` 测试所有设备连接

### 光谱仪采集无响应

1. 确保 LightField 软件**已启动**并加载了正确的实验预设
2. 确保相机已冷却
3. 检查 `spectrometer.experiment_name` 与 LightField 中的预设名一致

### 旋转台不移动

1. 检查电机序列号
2. 先运行 `MotorHome()` 归零
3. 确保角度值在物理范围内

### 导入报错 `ModuleNotFoundError`

项目需要在 `CommandMode/` 根目录运行，确保当前目录正确：

```powershell
cd d:\TraeProject\Project4SFG操作系统\CommandMode
python examples/09_pipeline_workflow.py
```

---

## IDE 模式 vs Web GUI 模式

| 特性 | IDE 模式 | Web GUI 模式 |
|------|---------|-------------|
| 适用场景 | 开发调试、批量自动化 | 日常操作、快速实验 |
| 交互方式 | 编写 Python 脚本 | 浏览器可视化操作 |
| 学习曲线 | 需要 Python 基础 | 几乎零代码 |
| 实验编辑 | 代码构建 Pipeline | 拖拽/下拉式编辑器 |
| 模板管理 | 手动编辑 YAML | 一键保存/加载/删除 |
| 实时监控 | print 输出 | 进度条 + 步骤状态 + 日志 |
| 数据类型 | 全部 (含高级自定义) | 预设的14种步骤类型 |
| 启动命令 | `python my_script.py` | `python -m web.app` |

> **如何选择？**  
> 日常实验 → Web GUI；新功能开发/批量实验/高级定制 → IDE 模式。  
> 两者共享相同的配置文件和设备定义，无缝切换。

---

*本手册随系统版本更新。如有疑问，请联系实验室管理员。*
