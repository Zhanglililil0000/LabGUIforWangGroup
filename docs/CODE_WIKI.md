# CommandMode Code Wiki

> **项目**: CommandMode — SFG/SRS 实验控制平台
> **版本**: v2.0
> **日期**: 2026-06-03
> **适用范围**: SFG（和频振动光谱）与 SRS（受激拉曼散射）实验

---

## 目录

1. [项目概述](#1-项目概述)
2. [项目架构](#2-项目架构)
3. [核心模块 (core)](#3-核心模块-core)
4. [设备驱动层 (devices)](#4-设备驱动层-devices)
5. [原子操作层 (operations)](#5-原子操作层-operations)
6. [API层 (API)](#6-api层-api)
7. [Web服务层 (web)](#7-web服务层-web)
8. [配置文件 (configs)](#8-配置文件-configs)
9. [关键数据流](#9-关键数据流)
10. [依赖关系](#10-依赖关系)
11. [项目运行方式](#11-项目运行方式)

---

## 1. 项目概述

CommandMode 是一个基于 Python 的分层架构实验控制平台，用于控制 **SFG（Sum Frequency Generation，和频振动光谱）** 和 **SRS（Stimulated Raman Scattering，受激拉曼散射）** 实验的全流程仪器设备。

### 1.1 核心功能

- 光谱仪控制（Princeton Instruments LightField）
- 旋转电机控制（Thorlabs Kinesis）
- 光学延迟线控制（Feinixs）
- 功率计/距离传感器读取
- 偏振扫描与差分信号采集
- 管道化实验流程编排
- Web GUI 可视化操作

### 1.2 两种使用模式

| 模式 | 入口 | 适用场景 |
|------|------|----------|
| **IDE 模式** | `python examples/*.py` | Python 脚本开发、调试、自动化 |
| **Web GUI 模式** | `python -m web.app` | 日常操作、可视化编辑 |

---

## 2. 项目架构

### 2.1 架构分层图

```
┌─────────────────────────────────────────────────────────────┐
│                      Web GUI (web/)                        │
│   FastAPI + Static HTML/JS/CSS + WebSocket 实时通信         │
├─────────────────────────────────────────────────────────────┤
│                    API 封装层 (API/)                        │
│        原始硬件驱动 DLL 封装 (Thorlabs/Princeton/...)       │
├─────────────────────────────────────────────────────────────┤
│                 原子操作层 (operations/)                    │
│     Pipeline 可执行单元: MotorOps / SpectrometerOps / ...   │
├─────────────────────────────────────────────────────────────┤
│                  设备驱动层 (devices/)                      │
│       统一设备接口: DeviceBase → Motor / Spectrometer / ... │
├─────────────────────────────────────────────────────────────┤
│                    核心框架层 (core/)                        │
│   Config / Context / Pipeline / Registry / SignalProcessing │
├─────────────────────────────────────────────────────────────┤
│                     配置文件 (configs/)                     │
│        devices.yaml / defaults.yaml / experiments/*.yaml   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 目录结构

```
CommandMode/
├── API/                          # 原始硬件驱动 DLL 封装
│   ├── ThorlabsAPI.py           # Thorlabs 旋转电机 (.NET)
│   ├── LightFieldAPI.py         # Princeton 光谱仪 (Automation)
│   ├── feinixsAPI.py            # Feinixs 延迟线 (.NET)
│   ├── ThorlabsTLPM.py          # Thorlabs 功率计 (VISA)
│   ├── KEYENCEAPI.py            # KEYENCE 距离传感器
│   ├── SmacqAPI.py              # Smacq 采集卡
│   └── ...
│
├── core/                         # 核心框架层
│   ├── config.py                # YAML 配置加载/继承/嵌套访问
│   ├── context.py              # 实验运行时上下文
│   ├── pipeline.py             # 管道编排引擎
│   ├── registry.py             # 设备 & 操作注册中心
│   └── signal_processing.py   # 信号处理算法
│
├── devices/                      # 设备驱动层 (统一接口)
│   ├── base.py                 # DeviceBase 抽象基类
│   ├── motor.py                # Thorlabs 旋转电机
│   ├── spectrometer.py         # Princeton 光谱仪
│   ├── delay_stage.py          # Feinixs 延迟线
│   ├── power_meter.py          # Thorlabs 功率计
│   ├── distance_sensor.py      # KEYENCE 距离传感器
│   ├── vertical_stage.py      # 垂直位移台
│   └── daq_card.py             # Smacq 采集卡
│
├── operations/                   # 原子操作层
│   ├── base.py                 # Operation 抽象基类
│   ├── motor_ops.py            # MotorHome / MotorMoveTo
│   ├── spectrometer_ops.py     # SetExposure / AcquireSpectrum
│   ├── delay_ops.py            # DelayStageHome / DelayStageMoveTo
│   └── utility_ops.py          # SetPolarization / Sleep / LogMessage
│
├── configs/                      # 配置文件
│   ├── devices.yaml            # 设备序列号/端口/驱动类型
│   ├── defaults.yaml           # 实验默认值 & 模式定义
│   ├── experiments/            # 实验配方
│   └── templates/              # Web GUI 模板
│
├── web/                         # Web GUI
│   ├── app.py                 # FastAPI 入口
│   ├── api/                   # REST API
│   │   ├── devices.py
│   │   ├── experiments.py
│   │   ├── templates.py
│   │   ├── calibration.py
│   │   └── ws.py
│   ├── services/
│   │   └── runner.py         # Pipeline 执行服务
│   └── static/                # 前端资源
│
├── examples/                    # 示例脚本
│   ├── 01_connect_devices.py
│   ├── 03_sfg_simple.py
│   ├── 04_pol_scan.py
│   └── 09_pipeline_workflow.py
│
├── tests/                       # 单元测试
├── legacy/                      # 旧版代码归档
└── resources/                  # DLL 资源文件
```

---

## 3. 核心模块 (core)

### 3.1 config.py — 配置管理

**类**: `Config`

负责从 YAML 文件加载配置，支持嵌套路径访问和继承机制。

**核心方法**:

| 方法 | 说明 |
|------|------|
| `Config(config_path)` | 加载 YAML 配置文件 |
| `get(key_path, default)` | 通过点号路径获取配置值，如 `"devices.vis_rotator.serial"` |
| `get_devices()` | 获取设备配置字典 |
| `get_experiment()` | 获取实验配置字典 |
| `get_output()` | 获取输出配置字典 |
| `get_polarization()` | 获取偏振配置字典 |
| `get_spectrometer()` | 获取光谱仪配置字典 |
| `to_dict()` | 返回完整配置字典副本 |

**特性**:
- 支持 `extends` 继承机制（子配置可继承父配置，深度合并）
- 支持嵌套键路径访问
- 默认值回退

**使用示例**:
```python
config = Config("configs/experiments/sfg_example.yaml")
serial = config.get("devices.vis_rotator.serial")  # "55358884"
```

---

### 3.2 context.py — 运行时上下文

**类**: `ExperimentContext`

实验运行时上下文，在管道执行期间保持。包含所有设备引用、配置、共享数据和运行状态。

**核心属性**:

| 属性 | 类型 | 说明 |
|------|------|------|
| `config` | `Config` | Config 实例 |
| `devices` | `dict[str, Any]` | 设备实例字典 |
| `data` | `dict[str, Any]` | 共享数据空间 |
| `logger` | `logging.Logger` | 日志记录器 |
| `start_time` | `datetime` | 实验开始时间 |
| `status` | `str` | 实验状态 |

**核心方法**:

| 方法 | 说明 |
|------|------|
| `set_device(name, device)` | 注册设备实例到上下文 |
| `get_device(name)` | 获取设备实例 |
| `pause()` | 请求暂停 |
| `resume()` | 恢复执行 |
| `stop()` | 请求停止 |
| `reset_flags()` | 重置暂停/停止标志 |

**状态流转**:
```
initializing → running → done / failed / paused → running
```

---

### 3.3 pipeline.py — 管道编排引擎

**类**: `Pipeline`

线性管道：顺序执行一组 Operation。支持错误策略、步骤回调、暂停/恢复/停止控制。

**核心组件**:

| 组件 | 说明 |
|------|------|
| `Pipeline` | 主管道执行器 |
| `StepResult` | 单步执行结果 |
| `PipelineResult` | 管道执行结果 |
| `ErrorStrategy` | 错误处理策略抽象基类 |
| `RetryStrategy` | 重试策略 |
| `SkipStrategy` | 跳过策略 |
| `AbortStrategy` | 中止策略 |

**Pipeline 核心方法**:

| 方法 | 说明 |
|------|------|
| `Pipeline(name, steps, on_error, on_step, on_complete)` | 创建管道 |
| `run(ctx)` | 执行管道，返回 PipelineResult |

**错误处理流程**:
```
操作失败 → ErrorStrategy.handle() → RetryAction (RETRY/SKIP/ABORT)
```

**使用示例**:
```python
pipeline = Pipeline("SFG_SSP_PPP", [
    MotorHome("vis_rotator"),
    SetWavelength(475),
    AcquireSpectrum("sample_ssp", exposure_ms=60000),
], on_error=RetryStrategy(max_retries=3, delay_seconds=5))

result = pipeline.run(ctx)
```

---

### 3.4 registry.py — 注册中心

**类**: `DeviceRegistry`, `OperationRegistry`

提供设备和操作的插件式注册/查找机制。

**DeviceRegistry**:

| 方法 | 说明 |
|------|------|
| `register_device_type(name, device_cls)` | 注册设备类型 |
| `create_device(type_name, name, config)` | 创建设备实例 |
| `get_device(name)` | 获取已创建的设备实例 |
| `list_devices()` | 列出所有设备实例 |
| `list_device_types()` | 列出所有注册的设备类型 |

**OperationRegistry**:

| 方法 | 说明 |
|------|------|
| `register(op_cls)` | 注册操作类型（装饰器） |
| `create(name, **kwargs)` | 创建操作实例 |
| `list_all()` | 列出所有已注册的操作 |

**使用示例**:
```python
@DeviceRegistry.register_device_type("thorlabs_rotator")
class ThorlabsRotator(DeviceBase): ...

dev = DeviceRegistry.create_device("thorlabs_rotator", "vis_rotator", config_dict)

@OperationRegistry.register
class AcquireSpectrum(Operation): ...

op = OperationRegistry.create("AcquireSpectrum", exposure_ms=60000)
```

---

### 3.5 signal_processing.py — 信号处理算法

**函数**:

| 函数 | 说明 |
|------|------|
| `compute_differential_signal(intensities, frames)` | 计算泵浦-探测差分信号（SRS/SFG多帧模式） |
| `fit_polarization_curve(intensities, angles_deg)` | 拟合偏振角度-强度曲线（余弦平方拟合） |

**compute_differential_signal 返回**:
- `ret`: 信号更强的一组（max-min 差更大者）
- `ret1`: 奇数帧/偶数帧比值的平均
- `ret2`: 偶数帧/奇数帧比值的平均

**偏振曲线拟合模型**:
```
I(θ) = A * cos²(θ - θ₀) + B
```

---

## 4. 设备驱动层 (devices)

### 4.1 base.py — 设备基类

**抽象基类**: `DeviceBase`

所有设备的抽象接口，子类必须实现 `connect`, `disconnect`, `is_connected`。

**异常类**:

| 异常 | 说明 |
|------|------|
| `DeviceError` | 设备相关错误基类 |
| `DeviceConnectionError` | 设备连接错误 |
| `DeviceOperationError` | 设备操作错误 |

**DeviceBase 抽象方法**:

| 方法 | 说明 |
|------|------|
| `connect() -> bool` | 建立设备连接 |
| `disconnect() -> None` | 断开设备连接 |

**DeviceBase 属性**:

| 属性 | 说明 |
|------|------|
| `name` | 设备名称 |
| `is_connected` | 设备是否已连接 |
| `status` | 设备状态字典 |

---

### 4.2 motor.py — Thorlabs 旋转电机

**类**: `ThorlabsRotator`

Thorlabs 旋转电机设备驱动，封装 Kinesis .NET API。支持 CageRotator 和 KCube DCServo 两种驱动类型。

**构造参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | `str` | `"rotator"` | 设备实例名称 |
| `driver` | `str` | `"Cage"` | 驱动器类型 `"Cage"` 或 `"KCube"` |
| `serial` | `str` | `""` | 设备序列号 |

**核心方法**:

| 方法 | 说明 |
|------|------|
| `connect()` | 连接设备 |
| `disconnect()` | 断开连接 |
| `home()` | 电机归零 |
| `move_to(position: float)` | 移动到绝对角度位置 |
| `stop()` | 急停 |

---

### 4.3 spectrometer.py — 光谱仪

**类**: `LightFieldSpectrometer`

Princeton Instruments 光谱仪，通过 LightField Automation API 控制。

**构造参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | `str` | `"spectrometer"` | 设备实例名称 |
| `experiment_name` | `str` | `"HRBBSFGVS-PyLon"` | LightField 实验预设名 |
| `file_path` | `str` | `""` | 数据保存路径 |

**核心方法**:

| 方法 | 说明 |
|------|------|
| `connect()` | 连接 LightField 应用 |
| `set_exposure_time(ms: int)` | 设置曝光时间（毫秒） |
| `set_center_wavelength(nm: float)` | 设置光栅中心波长 |
| `set_frames_number(frames: int)` | 设置采集帧数 |
| `set_grating(grating: str)` | 切换光栅 |
| `save_file(filename: str)` | 设置保存文件名 |
| `acquire()` | 触发采集（阻塞直到完成） |
| `get_pixels() -> int` | 获取传感器像素数 |

---

### 4.4 delay_stage.py — 光学延迟线

**类**: `DelayStage`

Feinixs 光学延迟线，支持 SMC/AMC/NANO/MINI04 控制器。

**构造参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | `str` | `"delay_stage"` | 设备实例名称 |
| `port` | `str` | `"COM4"` | 串口端口 |
| `baud` | `int` | `19200` | 波特率 |
| `controller` | `str` | `"SMC"` | 控制器类型 |
| `slave` | `int` | `0xCC` | 从机地址 |
| `limit_isnegative` | `bool` | `True` | 限位方向 |

**核心方法**:

| 方法 | 说明 |
|------|------|
| `connect()` | 连接设备 |
| `home(axis: str = "X")` | 归零指定轴 |
| `move_to(axis: str, position: float)` | 绝对移动到指定位置 |
| `move_by(axis: str, delta: float)` | 相对移动 |
| `get_position(axis: str = "X") -> float` | 获取当前位置 |
| `is_running(axis: str = "X") -> bool` | 检查轴是否在运动 |

---

### 4.5 其他设备

| 设备 | 文件 | 说明 |
|------|------|------|
| `ThorlabsPowerMeter` | `devices/power_meter.py` | Thorlabs 功率计 |
| `KEYENCEDistanceSensor` | `devices/distance_sensor.py` | KEYENCE 激光距离传感器 |
| `VerticalStage` | `devices/vertical_stage.py` | 串口垂直位移台 |
| `SmacqDAQCard` | `devices/daq_card.py` | Smacq USB-1000 采集卡 |

---

## 5. 原子操作层 (operations)

### 5.1 base.py — 操作基类

**抽象基类**: `Operation`

原子操作：管道的最小编排单元。

**OperationStatus 枚举**:

| 状态 | 说明 |
|------|------|
| `PENDING` | 待执行 |
| `RUNNING` | 执行中 |
| `DONE` | 已完成 |
| `FAILED` | 失败 |
| `SKIPPED` | 已跳过 |

**Operation 抽象方法**:

| 方法 | 说明 |
|------|------|
| `execute(ctx) -> dict` | 执行操作 |
| `validate(ctx) -> bool` | 执行前校验（返回 False 则跳过） |
| `rollback(ctx) -> None` | 失败时的回滚操作 |

---

### 5.2 motor_ops.py — 电机操作

| 操作类 | 说明 | 参数 |
|--------|------|------|
| `MotorHome` | 电机归零 | `device_name` |
| `MotorMoveTo` | 移动到指定角度 | `device_name`, `position` |

---

### 5.3 spectrometer_ops.py — 光谱仪操作

| 操作类 | 说明 | 参数 |
|--------|------|------|
| `SetExposure` | 设置曝光时间 | `exposure_ms: int` |
| `SetWavelength` | 设置光栅中心波长 | `wavelength_nm: float` |
| `AcquireSpectrum` | 采集光谱并保存 | `data_name`, `exposure_ms`, `frames`, `compute_diff` |

**AcquireSpectrum 特性**:
- 支持单帧和多帧模式
- 多帧模式下自动计算差分信号
- 保存结果为 CSV 文件

---

### 5.4 delay_ops.py — 延迟线操作

| 操作类 | 说明 | 参数 |
|--------|------|------|
| `DelayStageHome` | 延迟线归零 | `device_name`, `axis` |
| `DelayStageMoveTo` | 延迟线移动到指定位置 | `device_name`, `axis`, `position` |

---

### 5.5 utility_ops.py — 辅助操作

| 操作类 | 说明 | 参数 |
|--------|------|------|
| `SetPolarization` | 设置偏振组合 | `polarization`, `config` |
| `Sleep` | 等待指定秒数 | `seconds: float` |
| `LogMessage` | 记录日志消息 | `message`, `level` |

**SetPolarization 支持的偏振模式**:
- `ssp`: VIS-S, SFG-S, IR-P
- `ppp`: VIS-P, SFG-P, IR-P
- `sps`: VIS-S, SFG-P, IR-S
- `pss`: VIS-P, SFG-S, IR-S
- `spp`: VIS-S, SFG-P, IR-P
- `psp`: VIS-P, SFG-S, IR-P

---

## 6. API层 (API)

API 层封装了原始硬件驱动的 DLL，提供 Python 级别的接口。

| 文件 | 封装对象 | 说明 |
|------|----------|------|
| `ThorlabsAPI.py` | Thorlabs Kinesis .NET | 旋转电机底层 |
| `LightFieldAPI.py` | Princeton LightField | 光谱仪底层 |
| `feinixsAPI.py` | Feinixs 延迟线 | 延迟线底层 |
| `ThorlabsTLPM.py` | Thorlabs TLPM VISA | 功率计底层 |
| `KEYENCEAPI.py` | KEYENCE CL3_IF.dll | 距离传感器底层 |
| `SmacqAPI.py` | Smacq usb-1000.dll | 采集卡底层 |
| `AndorAPI.py` | Andor 相机 | 相机底层 |
| `verticalStageAPI.py` | 串口通信 | 垂直台底层 |

---

## 7. Web服务层 (web)

### 7.1 app.py — FastAPI 入口

**路由**:
- `/api/devices` — 设备 API
- `/api/templates` — 模板 API
- `/api/experiments` — 实验 API
- `/api/calibration` — 校准 API
- `/ws` — WebSocket 实时通信

**启动方式**:
```python
from web.app import run
run(host="0.0.0.0", port=8080)
```

或：
```powershell
python -m web.app
```

---

### 7.2 services/runner.py — 实验运行器

**类**: `ExperimentRunner`

单例模式，桥接 FastAPI 后端与 CommandMode 核心模块。

**核心职责**:
1. 将前端 `ExperimentFlow` JSON 转换为 `Pipeline` 实例
2. 创建 `MockDevice` 池和 `ExperimentContext`
3. 在守护线程中执行管道
4. 通过 WebSocket 推送实时进度和日志
5. 提供暂停/恢复/停止控制

**MockDevice**: 在无硬件环境下模拟设备响应，支持所有设备接口。

**关键方法**:

| 方法 | 说明 |
|------|------|
| `run(flow: ExperimentFlow)` | 启动实验执行 |
| `pause()` | 暂停实验 |
| `resume()` | 恢复实验 |
| `stop()` | 停止实验 |
| `is_running() -> bool` | 检查是否在运行 |
| `get_available_device_configs()` | 加载设备配置 |

---

### 7.3 api/ — REST API

| 文件 | 路由前缀 | 说明 |
|------|----------|------|
| `devices.py` | `/api/devices` | 设备列表、连接状态 |
| `experiments.py` | `/api/experiments` | 实验启动/暂停/恢复/停止 |
| `templates.py` | `/api/templates` | 模板 CRUD |
| `calibration.py` | `/api/calibration` | 校准操作 |
| `ws.py` | `/ws` | WebSocket 实时通信 |

---

## 8. 配置文件 (configs)

### 8.1 devices.yaml — 设备连接参数

定义所有设备的连接参数：

```yaml
devices:
  vis_rotator:
    type: "thorlabs_rotator"
    driver: "Cage"
    serial: "55358884"

  delay_stage:
    type: "delay_stage"
    port: "COM4"
    baud: 19200
    controller: "SMC"
    slave: 204

  spectrometer:
    type: "lightfield"
    experiment_name: "HRBBSFGVS-PyLon"
```

### 8.2 defaults.yaml — 全局默认配置

定义实验模式和默认参数：

```yaml
modes:
  sfg:
    name: "SFG 实验"
    lightfield_experiment: "HRBBSFGVS-PyLon"
    devices:
      - spectrometer
      - vis_rotator
      - sfg_rotator
      - delay_stage

  srs:
    name: "SRS 实验"
    lightfield_experiment: "FSRS-Blaze"
    frames: 10000
```

### 8.3 experiments/ — 实验配方

| 文件 | 说明 |
|------|------|
| `sfg_example.yaml` | SFG 示例 |
| `srs_example.yaml` | SRS 示例 |
| `pol_scan_example.yaml` | 偏振扫描示例 |

支持通过 `extends` 继承 `defaults.yaml`。

---

## 9. 关键数据流

### 9.1 管道执行流程

```
用户代码 / Web GUI
       ↓
  ExperimentContext 创建
       ↓
  Pipeline.run(ctx)
       ↓
  ┌─────────────────────────────────┐
  │  For each Operation in steps:   │
  │    1. validate(ctx)             │
  │    2. execute(ctx)              │
  │    3. 捕获异常 → ErrorStrategy  │
  │    4. 状态更新 → on_step 回调   │
  │    5. 结果存储 → StepResult     │
  └─────────────────────────────────┘
       ↓
  PipelineResult 返回
```

### 9.2 Web GUI 实验流程

```
前端 (HTML/JS)
    ↓ POST /api/experiments/run {flow}
Web API (experiments.py)
    ↓
ExperimentRunner.run(flow)
    ↓
Pipeline 构建 + MockDevice 创建
    ↓
守护线程 pipeline.run(ctx)
    ↓
WebSocket 实时推送 (step_start/step_done/log)
    ↓
前端更新进度条/日志
```

### 9.3 数据保存流程

```
AcquireSpectrum.execute(ctx)
    ↓
spectrometer.acquire() 触发 LightField 采集
    ↓
LightField 保存 CSV 到 output.base_path
    ↓
_parse_csv 解析波长和强度
    ↓
compute_differential_signal (多帧模式)
    ↓
_save_ret 保存 _ret.csv, _ret1.csv, _ret2.csv
    ↓
ctx.data["last_spectrum"] 更新
```

---

## 10. 依赖关系

### 10.1 外部依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | 3.9+ | 运行环境 |
| PyYAML | - | 配置文件解析 |
| NumPy | - | 信号处理 |
| FastAPI | - | Web 服务 |
| Uvicorn | - | ASGI 服务器 |
| Pythonnet | - | .NET DLL 调用 |
| PySerial | - | 串口通信 |

### 10.2 硬件依赖

| 设备 | 驱动/软件 |
|------|-----------|
| Thorlabs 旋转电机 | Thorlabs Kinesis |
| Princeton 光谱仪 | LightField 软件 |
| Feinixs 延迟线 | ftcorecs.dll |
| Thorlabs 功率计 | TLPM VISA |

### 10.3 模块依赖图

```
operations/
    ├── motor_ops.py ───────→ devices/motor.py
    ├── spectrometer_ops.py ─→ devices/spectrometer.py
    ├── delay_ops.py ───────→ devices/delay_stage.py
    └── utility_ops.py

core/
    ├── config.py ───────────→ YAML 解析
    ├── context.py ──────────→ 运行时状态
    ├── pipeline.py ─────────→ operations.base
    └── signal_processing.py ← numpy

web/
    ├── app.py ──────────────→ FastAPI
    ├── api/experiments.py ─→ core/* + operations/*
    └── services/runner.py ─→ core/* + operations/* + devices/*
```

---

## 11. 项目运行方式

### 11.1 IDE 模式

**查看设备列表（Mock 模式，无需硬件）**:
```powershell
cd d:\TraeProject\Project4SFG操作系统\CommandMode
python examples/01_connect_devices.py
```

**管道编排练习（Mock 模式）**:
```powershell
python examples/09_pipeline_workflow.py
```

**完整 SFG 实验（需要硬件）**:
```powershell
python examples/03_sfg_simple.py
```

**自定义实验**:
1. 在 `configs/experiments/` 下创建 YAML 配置
2. 编写 Python 脚本构建 Pipeline
3. 运行脚本

### 11.2 Web GUI 模式

**启动服务**:
```powershell
cd d:\TraeProject\Project4SFG操作系统\CommandMode
python -m web.app
# 或
python web/app.py
```

**访问地址**: `http://localhost:8080`

### 11.3 运行前检查

1. **配置文件**: 确认 `configs/devices.yaml` 中的序列号/COM 口正确
2. **硬件连接**: Thorlabs Kinesis / LightField 软件已启动
3. **Python 环境**: 已安装所有依赖 (`pip install pyserial pyyaml numpy fastapi uvicorn pythonnet`)

### 11.4 测试

```powershell
pytest tests/
```

---

## 附录

### A. 偏振角度映射表

| 模式 | VIS 旋转台 | SFG 旋转台 | 含义 |
|------|-----------|-----------|------|
| SSP | 45.58° (S) | 29.01° (S) | SFG-S, VIS-S, IR-P |
| PPP | 90.58° (P) | 74.01° (P) | SFG-P, VIS-P, IR-P |
| SPS | 45.58° (S) | 74.01° (P) | SFG-S, VIS-P, IR-S |
| PSS | 90.58° (P) | 29.01° (S) | SFG-P, VIS-S, IR-S |

### B. SRS 偏振角度

| 模式 | Raman 旋转台角度 | 含义 |
|------|----------------|------|
| VV | 42.47° | Pump 垂直, Probe 垂直 |
| VH | 87.47° | Pump 垂直, Probe 水平 |

### C. 错误代码

| 错误策略 | 行为 |
|----------|------|
| `RetryStrategy` | 失败后重试指定次数 |
| `SkipStrategy` | 失败后跳过，继续下一步 |
| `AbortStrategy` | 失败后立即中止管道 |

---

*本文档由代码分析自动生成，如有疑问请联系实验室管理员。*
