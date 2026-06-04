# CommandMode 重构设计文档

> **版本**: v1.0  
> **日期**: 2026-06-02  
> **作者**: Zhang Li  
> **状态**: 待审核

---

## 目录

1. [背景与动机](#1-背景与动机)
2. [设计目标](#2-设计目标)
3. [架构总览](#3-架构总览)
4. [分层设计](#4-分层设计)
   - [4.1 设备驱动层 (`devices/`)](#41-设备驱动层-devices)
   - [4.2 核心框架层 (`core/`)](#42-核心框架层-core)
   - [4.3 原子操作层 (`operations/`)](#43-原子操作层-operations)
   - [4.4 实验配方层 (`recipes/`)](#44-实验配方层-recipes)
   - [4.5 配置层 (`configs/`)](#45-配置层-configs)
   - [4.6 GUI 接口层 (`api/`)](#46-gui-接口层-api)
   - [4.7 示例与文档 (`examples/` + `docs/`)](#47-示例与文档-examples--docs)
5. [数据流](#5-数据流)
6. [管道编排引擎详解](#6-管道编排引擎详解)
7. [可扩展性设计](#7-可扩展性设计)
8. [错误处理策略](#8-错误处理策略)
9. [向后兼容策略](#9-向后兼容策略)
10. [实施计划](#10-实施计划)
11. [附录：设备清单与接口定义](#11-附录设备清单与接口定义)

---

## 1. 背景与动机

### 1.1 当前问题

`CommandMode/` 目录包含 SFG（和频光谱）和 SRS（受激拉曼散射）实验的仪器控制代码，控制 8 种硬件设备。存在以下问题：

| 问题 | 影响 |
|------|------|
| 设备参数硬编码在实验文件中 | 更换设备需修改实验代码，易出错 |
| 差分信号处理逻辑在 4 个文件重复 | 修改算法需改 4 处，维护困难 |
| 实验文件与采集逻辑高度耦合 | 无法复用，新实验需大量复制代码 |
| 无统一的设备生命周期管理 | 资源泄漏风险（设备未正确关闭） |
| 大量注释的旧代码混在主文件中 | 可读性差，新手上手困难 |
| 无文档、无示例 | 学习曲线陡峭（仅靠阅读源码） |

### 1.2 未来需求

1. **实验序列编排**：支持条件分支、重试、步骤组合
2. **Web GUI 预留**：远期开发浏览器控制面板，当前预留清晰 API
3. **可扩展**：新设备、新实验类型可插件式添加
4. **降低学习门槛**：示例代码（example）+ 完整 README + 教程

---

## 2. 设计目标

| 目标 | 度量标准 |
|------|----------|
| **消除代码重复** | 相同算法只存在一处，所有实验共享 |
| **配置与代码分离** | 设备参数、实验参数均在 YAML 文件中 |
| **设备无关的实验编写** | 切换相机（PyLon/ProEM/Andor）只需改配置 |
| **管道式实验编排** | 支持序列、条件、重试、嵌套管道 |
| **GUI 就绪** | 所有功能通过 Python API 暴露，可直接被 FastAPI 路由调用 |
| **新手友好** | 10 个渐进式 example，配套 README 和教程文档 |

---

## 3. 架构总览

```
                         ┌──────────────────────────┐
                         │       Web GUI (远期)       │
                         │   Flask / FastAPI + Vue   │
                         └────────────┬─────────────┘
                                      │ REST / WebSocket
                         ┌────────────▼─────────────┐
                         │      api/ (GUI接口层)      │
                         │   routes / schemas        │
                         └────────────┬─────────────┘
                                      │ Python API
┌──────────────────────────────────────┼──────────────────────────────────────┐
│                                      │                                       │
│  ┌───────────────────────────────────▼───────────────────────────────────┐  │
│  │                       recipes/ (实验配方层)                             │  │
│  │    sfg.py   srs.py   raman.py   diagnostics.py                        │  │
│  │    编排 Pipeline: 校准 → 扫描 → 保存 → 关机                            │  │
│  └───────────────────────────────────┬───────────────────────────────────┘  │
│                                      │                                       │
│  ┌───────────────────────────────────▼───────────────────────────────────┐  │
│  │                      operations/ (原子操作层)                           │  │
│  │    motor_ops.py   spectrometer_ops.py   delay_ops.py   data_ops.py    │  │
│  │    每个原子操作：单步可执行、可组合、可追踪状态                           │  │
│  └───────────────────────────────────┬───────────────────────────────────┘  │
│                                      │                                       │
│  ┌───────────────────────────────────▼───────────────────────────────────┐  │
│  │                        core/ (核心框架层)                                │  │
│  │    pipeline.py (编排引擎)   registry.py (注册中心)                      │  │
│  │    config.py (配置管理)     signal_processing.py (算法)                 │  │
│  │    context.py (实验上下文)                                              │  │
│  └───────────────────────────────────┬───────────────────────────────────┘  │
│                                      │                                       │
│  ┌───────────────────────────────────▼───────────────────────────────────┐  │
│  │                       devices/ (设备驱动层)                              │  │
│  │    spectrometer.py   motor.py   delay_stage.py   power_meter.py        │  │
│  │    distance_sensor.py   vertical_stage.py   daq_card.py               │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      resources/ (DLL/原生库)                            │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 依赖规则

```
上层可以 import 下层（包括同层），下层不可以 import 上层。

recipes ──→ operations ──→ devices
    │             │             │
    └─────────────┼─────────────┘
                  ▼
               core (被所有层共享)
```

---

## 4. 分层设计

### 4.1 设备驱动层 (`devices/`)

#### 4.1.1 设备基类 (`devices/base.py`)

所有设备必须实现此接口：

```python
class DeviceBase(ABC):
    """所有设备的抽象基类"""

    # --- 生命周期 ---
    @abstractmethod
    def connect(self) -> bool: ...
    @abstractmethod
    def disconnect(self) -> None: ...

    # --- 状态查询 ---
    @property
    @abstractmethod
    def is_connected(self) -> bool: ...
    @property
    def status(self) -> dict:
        """返回设备状态字典，供 GUI 展示"""

    # --- 上下文管理 ---
    def __enter__(self): self.connect(); return self
    def __exit__(self, *args): self.disconnect()
```

#### 4.1.2 现有设备映射

| 原文件 | 新文件 | 类名 | 关键变更 |
|--------|--------|------|----------|
| `API/LightFieldAPI.py` | `devices/spectrometer.py` | `LightFieldSpectrometer` | 统一接口，继承 `DeviceBase` |
| `API/AndorAPI.py` | `devices/spectrometer.py` | `AndorSpectrometer` | 补充采集方法，统一接口 |
| `API/ThorlabsAPI.py` | `devices/motor.py` | `ThorlabsRotator` | 继承 `DeviceBase` |
| `API/feinixsAPI.py` | `devices/delay_stage.py` | `DelayStage` | 继承 `DeviceBase`，修复析构函数 |
| `API/ThorlabsTLPM.py` | `devices/power_meter.py` | `ThorlabsPowerMeter` | 封装 ctypes，提供 Pythonic API |
| `API/KEYENCEAPI.py` | `devices/distance_sensor.py` | `KeyenceDistanceSensor` | 继承 `DeviceBase` |
| `API/verticalStageAPI.py` | `devices/vertical_stage.py` | `VerticalStage` | 继承 `DeviceBase` |
| `API/SmacqAPI.py` | `devices/daq_card.py` | `SmacqAICard` | 保持现有接口，加 `DeviceBase` |

#### 4.1.3 光谱仪统一接口

关键设计：通过 `SpectrometerDriver` 统一 LightField 和 Andor 的接口：

```python
class SpectrometerDriver(ABC):
    """光谱仪抽象，屏蔽 LightField vs Andor 差异"""

    @abstractmethod
    def set_exposure_time(self, ms: int) -> None: ...
    @abstractmethod
    def set_center_wavelength(self, nm: float) -> None: ...
    @abstractmethod
    def set_grating(self, grating: str) -> None: ...
    @abstractmethod
    def set_frames(self, n: int) -> None: ...
    @abstractmethod
    def acquire(self) -> None: ...  # 触发采集
    @abstractmethod
    def get_last_data(self) -> np.ndarray: ...  # 获取最近一次数据
    @abstractmethod
    def save_file(self, name: str) -> None: ...
```

`LightFieldSpectrometer` 和 `AndorSpectrometer` 分别实现此接口。实验代码只依赖 `SpectrometerDriver`，不关心具体实现。

---

### 4.2 核心框架层 (`core/`)

#### 4.2.1 配置管理 (`core/config.py`)

```python
class Config:
    """从 YAML 加载配置，支持环境变量覆盖和嵌套路径访问"""

    def __init__(self, config_path: str): ...
    def get(self, key_path: str, default=None): ...  # 点号分隔，如 "devices.vis_rotator.serial"
    def get_devices(self) -> list[dict]: ...  # 返回需初始化的设备列表
    def get_pipeline(self) -> dict: ...  # 返回管道定义

# 使用示例：
config = Config("configs/experiments/sfg_methanol.yaml")
serial = config.get("devices.vis_rotator.serial")  # "55358884"
```

#### 4.2.2 注册中心 (`core/registry.py`)

插件式扩展的关键。设备和操作类型在此注册：

```python
class DeviceRegistry:
    """全局设备注册中心"""
    _device_types: dict[str, type] = {}     # {"rotator": ThorlabsRotator, ...}
    _instances: dict[str, DeviceBase] = {}  # {"vis_rotator": <instance>, ...}

    @classmethod
    def register_device_type(cls, name: str, device_cls: type): ...
    @classmethod
    def create_device(cls, type_name: str, name: str, config: dict) -> DeviceBase: ...
    @classmethod
    def get_device(cls, name: str) -> DeviceBase: ...

class OperationRegistry:
    """全局操作注册中心"""
    _operations: dict[str, type] = {}

    @classmethod
    def register(cls, op_cls: type): ...
    @classmethod
    def list_all(cls) -> list[str]: ...
    @classmethod
    def create(cls, name: str, **kwargs) -> "Operation": ...
```

#### 4.2.3 管道编排引擎 (`core/pipeline.py`)

架构核心，详见 [第 6 节](#6-管道编排引擎详解)。

#### 4.2.4 实验上下文 (`core/context.py`)

```python
@dataclass
class ExperimentContext:
    """实验运行时上下文，贯穿整个管道"""
    config: Config
    devices: dict[str, DeviceBase]
    data: dict[str, Any]        # 共享数据空间（管道步骤间传递数据）
    logger: logging.Logger
    start_time: datetime
    status: str                 # "initializing" | "running" | "paused" | "done" | "failed"
```

#### 4.2.5 信号处理 (`core/signal_processing.py`)

从原 SFG/SRS 文件中提取的公共算法：

```python
def compute_differential_signal(
    intensities: list[np.ndarray],
    frames: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    计算泵浦-探测差分信号。
    返回 (ret, ret1, ret2)
    - ret1: odd/even 帧比值的平均
    - ret2: even/odd 帧比值的平均
    - ret: 选择信号更强的一组
    """

def analyze_polarization(
    wavelength: np.ndarray,
    intensity_matrix: np.ndarray,  # shape (n_angles, n_pixels)
    angles: np.ndarray
) -> dict:
    """偏振分析：拟合各波长的偏振曲线"""
```

---

### 4.3 原子操作层 (`operations/`)

#### 4.3.1 操作基类 (`operations/base.py`)

```python
class OperationStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"

class Operation(ABC):
    """原子操作：管道的最小编排单元"""

    def __init__(self, name: str): ...

    @abstractmethod
    def execute(self, ctx: ExperimentContext) -> dict:
        """执行操作。返回结果字典。"""

    def validate(self, ctx: ExperimentContext) -> bool:
        """执行前校验。返回 False 则跳过。"""
        return True

    def rollback(self, ctx: ExperimentContext) -> None:
        """失败时的回滚操作（可选覆盖）"""
        pass
```

#### 4.3.2 分类

| 文件 | 包含的操作 | 说明 |
|------|-----------|------|
| `motor_ops.py` | `MotorHome`, `MotorMoveTo`, `MotorScanRange` | 电机归零、定点移动、范围扫描 |
| `spectrometer_ops.py` | `SetExposure`, `SetWavelength`, `AcquireSpectrum`, `SaveData` | 光谱仪设置和采集 |
| `delay_ops.py` | `DelayStageHome`, `DelayStageMoveTo`, `DelayScan` | 延迟线操作 |
| `power_ops.py` | `MeasurePower`, `PowerPolarizationScan` | 功率计测量 |
| `height_ops.py` | `LockHeight`, `HeightScan` | 距离传感器 + 垂直位移台 |
| `data_ops.py` | `ExportCSV`, `GenerateReport` | 数据导出和后处理 |
| `utility_ops.py` | `Sleep`, `LogMessage`, `ConditionalBranch` | 流程控制 |

#### 4.3.3 示例：AcquireSpectrum

```python
@OperationRegistry.register
class AcquireSpectrum(Operation):
    """采集一帧光谱，保存到指定路径"""

    def execute(self, ctx: ExperimentContext) -> dict:
        spec = ctx.devices["spectrometer"]
        spec.save_file(self.data_name)
        spec.set_exposure_time(self.exposure_ms)
        spec.set_frames(self.frames)
        spec.acquire()

        # 读取数据
        filepath = ctx.config.get("output.base_path") + "/" + self.data_name + ".csv"
        wavelengths, intensities = self._parse_csv(filepath)

        # 计算差分信号（多帧模式）
        if self.frames > 1:
            ret, ret1, ret2 = compute_differential_signal(intensities, self.frames)
            self._save_ret_data(filepath, wavelengths, ret, ret1, ret2)

        ctx.data["last_spectrum"] = {"wavelengths": wavelengths, "intensities": intensities}
        return {"filepath": filepath, "frames": self.frames}
```

---

### 4.4 实验配方层 (`recipes/`)

#### 4.4.1 配方 = 管道编排

```python
# recipes/sfg.py

def sfg_polarization_scan_recipe(config: Config) -> Pipeline:
    """SFG 偏振扫描标准配方"""

    return Pipeline("SFG_Polarization_Scan", [
        # 步骤 1: 初始化
        MotorHome("vis_rotator"),
        MotorHome("sfg_rotator"),

        # 步骤 2: 设置光谱仪
        SetWavelength(config.get("spectrometer.center_wavelength")),
        SetExposure(config.get("spectrometer.exposure_ms")),

        # 步骤 3: SSP 采集
        SetPolarization("ssp", config),
        AcquireSpectrum(data_name=f"{config.sample}_ssp"),

        # 步骤 4: PPP 采集
        SetPolarization("ppp", config),
        AcquireSpectrum(data_name=f"{config.sample}_ppp"),

        # 步骤 5: 背景采集
        DelayStageMoveTo("x", config.get("background.delay_position")),
        AcquireSpectrum(data_name=f"{config.sample}_bg"),

        # 步骤 6: 设备归零
        MotorHome("vis_rotator"),
        MotorHome("sfg_rotator"),
    ],
        on_error=RetryStrategy(max_retries=1),
        on_complete=lambda ctx: ctx.logger.info("SFG 偏振扫描完成"),
    )


def sfg_time_scan_recipe(config: Config) -> Pipeline:
    """SFG 时间扫描（延迟线扫描）"""
    steps = [
        MotorHome("vis_rotator"),
        MotorHome("sfg_rotator"),
        SetPolarization(config.get("polarization.mode", "ssp"), config),
        SetWavelength(config.get("spectrometer.center_wavelength")),
        SetExposure(config.get("spectrometer.exposure_ms")),
    ]

    # 参数化步骤：对每个延迟位置
    for pos in config.get("scan.delay_positions"):
        steps.append(DelayStageMoveTo("x", pos))
        steps.append(AcquireSpectrum(
            data_name=f"{config.sample}_delay_{pos:.2f}mm"
        ))

    return Pipeline("SFG_Time_Scan", steps,
        on_complete=lambda ctx: ctx.logger.info("时间扫描完成"),
    )
```

#### 4.4.2 内置配方清单

| 配方名 | 文件 | 描述 |
|--------|------|------|
| `sfg_polarization_scan` | `recipes/sfg.py` | SFG 多偏振组合采集 + 背景 |
| `sfg_time_scan` | `recipes/sfg.py` | SFG 延迟线扫描 |
| `sfg_pol_angle_scan` | `recipes/sfg.py` | SFG 偏振角度扫描（旋转检偏器） |
| `sfg_pna_scan` | `recipes/sfg.py` | SFG 偏振零角法 |
| `srs_wavelength_scan` | `recipes/srs.py` | SRS 波长扫描 + 差分信号 |
| `srs_pol_scan` | `recipes/srs.py` | SRS 偏振扫描 |
| `srs_time_scan` | `recipes/srs.py` | SRS 延迟线扫描 |
| `raman_spectrum` | `recipes/raman.py` | 自发拉曼光谱 |
| `height_scan` | `recipes/diagnostics.py` | 样品高度扫描 |
| `power_pol_scan` | `recipes/diagnostics.py` | 功率-偏振扫描 |
| `photodiode_test` | `recipes/diagnostics.py` | 光电二极管测试 |
| `photodiode_correlation` | `recipes/diagnostics.py` | 光电二极管相关性扫描 |
| `system_diagnostics` | `recipes/diagnostics.py` | 系统自检（所有设备连通性） |

---

### 4.5 配置层 (`configs/`)

#### 4.5.1 示例：设备配置 (`configs/devices.yaml`)

```yaml
# 设备连接参数（通常不变，全局共享）
devices:
  vis_rotator:
    type: "thorlabs_rotator"
    driver: "cage"            # "cage" | "kcube"
    serial: "55358884"

  sfg_rotator:
    type: "thorlabs_rotator"
    driver: "cage"
    serial: "55355234"

  delay_stage:
    type: "delay_stage"
    port: "COM4"
    baud: 19200
    controller: "SMC"         # "SMC" | "AMC" | "NANO" | "MINI04"
    axis: "X"

  spectrometer:
    type: "lightfield"        # "lightfield" | "andor"
    experiment_name: "HRBBSFGVS-PyLon"

  power_meter:
    type: "thorlabs_tlpm"
    wavelength_nm: 532.0

  distance_sensor:
    type: "keyence_cl3"
    device_id: 0

  vertical_stage:
    type: "vertical_stage"
    port: "COM9"
    baud: 9600
```

#### 4.5.2 示例：实验配置 (`configs/experiments/sfg_methanol.yaml`)

```yaml
# SFG 实验 - Methanol 样品
# 继承自 defaults.yaml
extends: "../defaults.yaml"

experiment:
  type: "sfg"
  name: "SFG_Methanol"

output:
  base_path: "D:\\2026\\ZGC\\20260527"
  sample_name: "methanol"
  auto_increment: false

spectrometer:
  center_wavelength_nm: 475
  exposure_ms: 60000

polarization:
  vis_angle_s: 45.58
  vis_angle_p: 90.58
  sfg_angle_s: 29.21
  sfg_angle_p: 74.21
  sequence: ["ssp", "ppp"]   # 要执行的偏振组合

delay_stage:
  signal_position: 222.5     # 样品信号位置
  background_position: 100.0 # 背景位置

scan:                         # 可选：扫描参数
  type: "time"                # "time" | "polarization" | "none"
  delay_start: 135.0
  delay_end: 161.0
  delay_step: 0.5
```

---

### 4.6 GUI 接口层 (`api/`)

本层当前仅定义接口契约（schemas），不实现服务器。远期在此实现 FastAPI。

#### 4.6.1 API 路由规划

```
GET    /api/devices                    # 列出所有设备及状态
POST   /api/devices/{name}/home        # 设备归零
POST   /api/devices/{name}/move        # {target: 45.0}
GET    /api/devices/{name}/status      # 设备实时状态

GET    /api/operations                 # 列出所有可用操作
POST   /api/operations/execute         # 执行单个操作 {operation: "acquire_spectrum", params: {...}}

GET    /api/recipes                    # 列出所有可用配方
POST   /api/recipes/run                # {recipe: "sfg_time_scan", config: "configs/experiments/sfg_methanol.yaml"}
GET    /api/recipes/{id}/status        # 查询管道状态 {status, progress, current_step, log}
POST   /api/recipes/{id}/pause         # 暂停
POST   /api/recipes/{id}/resume        # 恢复
POST   /api/recipes/{id}/stop          # 停止

GET    /api/data/latest                # 获取最新采集数据（JSON）
GET    /api/data/preview               # 数据预览（含缩略图数据）
```

#### 4.6.2 Pydantic Schema（节选）

```python
# api/schemas.py
from pydantic import BaseModel

class DeviceStatus(BaseModel):
    name: str
    type: str
    is_connected: bool
    extra: dict = {}

class PipelineStatus(BaseModel):
    id: str
    name: str
    status: str  # "running" | "paused" | "done" | "failed"
    current_step: int
    total_steps: int
    progress_pct: float
    start_time: str
    elapsed_seconds: float
    log: list[str]

class OperationRequest(BaseModel):
    operation: str
    params: dict = {}
```

---

### 4.7 示例与文档 (`examples/` + `docs/`)

#### 4.7.1 示例代码结构（10 个渐进式示例）

| 编号 | 文件 | 内容 | 预计耗时 |
|------|------|------|----------|
| 01 | `01_connect_devices.py` | 连接设备、打印状态、断开 | 5 min |
| 02 | `02_acquire_single.py` | 单帧光谱采集和查看 | 10 min |
| 03 | `03_sfg_simple.py` | 简单 SFG 实验（SSP + PPP） | 15 min |
| 04 | `04_sfg_pol_scan.py` | SFG 偏振角度扫描 | 15 min |
| 05 | `05_sfg_time_scan.py` | SFG 延迟线时间扫描 | 15 min |
| 06 | `06_srs_simple.py` | SRS 波长扫描 + 差分信号 | 15 min |
| 07 | `07_height_scan.py` | 样品高度扫描 + 锁定 | 15 min |
| 08 | `08_power_scan.py` | 功率-偏振扫描 | 10 min |
| 09 | `09_pipeline_workflow.py` | 序列编排：校准→采集→关机 | 20 min |
| 10 | `10_batch_experiment.py` | 批量实验：多样品/多配置 | 15 min |

#### 4.7.2 文档清单

| 文件 | 内容 | 目标读者 |
|------|------|----------|
| `README.md` | 项目简介、快速开始（5 分钟跑起来） | 所有人 |
| `ARCHITECTURE.md` | 架构设计、分层说明、扩展指南 | 贡献者/维护者 |
| `DEVICE_SETUP.md` | 硬件连接、驱动安装、串口号配置 | 实验操作者 |
| `TUTORIAL.md` | 从零开始的教程（跟着 example 走） | 新手 |
| `API_REFERENCE.md` | 所有公共类和函数的文档 | 开发者 |
| `FAQ.md` | 常见问题排查 | 所有人 |

---

## 5. 数据流

### 5.1 典型实验数据流

```
用户编写 YAML 配置
        │
        ▼
Config 加载配置 → 解析设备列表和实验参数
        │
        ▼
DeviceRegistry 按配置初始化设备 → 存入 ExperimentContext
        │
        ▼
Recipe（管道编排）启动
        │
        ▼
Pipeline 逐步骤执行 Operation
        │
        ├── MotorMoveTo("vis_rotator", 45.58)
        │       │
        │       ▼
        │   ctx.devices["vis_rotator"].move_to(45.58)
        │       │
        │       ▼
        │   [Thorlabs Kinesis DLL] → 电机物理移动
        │
        ├── AcquireSpectrum("methanol_ssp", exposure=60000)
        │       │
        │       ▼
        │   ctx.devices["spectrometer"].set_exposure(60000)
        │   ctx.devices["spectrometer"].save_file("methanol_ssp")
        │   ctx.devices["spectrometer"].acquire()
        │       │
        │       ▼
        │   [LightField Automation] → CCD 曝光 → 写入 .csv
        │       │
        │       ▼
        │   读取 .csv → compute_differential_signal() → 写入 _ret.csv
        │       │
        │       ▼
        │   ctx.data["last_spectrum"] = {...}
        │
        └── 输出：CSV 文件 + 日志 + 运行报告
```

### 5.2 GUI 调用数据流（远期）

```
浏览器 [点击 "运行 SSP 实验"]
    │ POST /api/recipes/run {"recipe": "sfg_polarization_scan", "config": "..."}
    ▼
FastAPI route
    │ 创建 Pipeline，启动后台线程
    ▼
Pipeline.run() [后台线程]
    │ 每完成一步 → 回调 → 更新内存状态
    ▼
浏览器轮询 GET /api/recipes/{id}/status
    │ { "status": "running", "progress_pct": 60, "current_step": "SSP采集" }
    ▼
浏览器实时渲染进度条和日志
    │ 实验完成 → { "status": "done" }
    ▼
用户点击 "查看数据" → GET /api/data/latest → 渲染光谱图
```

---

## 6. 管道编排引擎详解

### 6.1 核心类

```python
class Pipeline:
    """线性管道：顺序执行一组 Operation"""
    def __init__(self, name, steps, on_error=None, on_complete=None, on_step=None):
        self.name = name
        self.steps: list[Operation] = steps
        self.on_error: Callable = on_error    # (step, error, ctx) -> RetryAction
        self.on_complete: Callable = on_complete  # (ctx) -> None
        self.on_step: Callable = on_step      # (step, status, ctx) -> None

    def run(self, ctx: ExperimentContext) -> PipelineResult:
        """执行管道，返回结果"""

    def pause(self): ...   # 当前步骤完成后暂停
    def resume(self): ...  # 继续执行
    def stop(self): ...    # 标记停止，当前步骤完成后退出


class ConditionalPipeline(Pipeline):
    """条件管道：根据步骤返回值决定下一步"""
    def __init__(self, name, branches: dict[str, list[Operation]], ...): ...


class ParallelPipeline(Pipeline):
    """并行管道：多步骤同时执行（用于不冲突的设备操作）"""
```

### 6.2 错误处理与重试

```python
class ErrorStrategy(ABC):
    @abstractmethod
    def handle(self, step: Operation, error: Exception, ctx: ExperimentContext) -> RetryAction: ...

class RetryStrategy(ErrorStrategy):
    def __init__(self, max_retries=3, delay_seconds=5): ...

class SkipStrategy(ErrorStrategy):
    """跳过失败的步骤，记录警告"""

class AbortStrategy(ErrorStrategy):
    """立即中止整个管道"""
```

### 6.3 步骤回调（GUI 监控的关键）

```python
def step_callback(step: Operation, status: OperationStatus, ctx: ExperimentContext):
    """每步状态变化时调用，GUI 通过此回调获取实时进度"""
    # status: PENDING → RUNNING → DONE/FAILED/SKIPPED
    # GUI 可据此更新进度条

pipeline = Pipeline("MyExperiment", steps,
    on_step=step_callback,   # ← GUI 注入
    on_complete=lambda ctx: notify("实验完成"),
)
```

---

## 7. 可扩展性设计

### 7.1 新增设备

1. 在 `devices/` 创建新文件，继承 `DeviceBase`
2. 用 `@DeviceRegistry.register_device_type("my_device")` 注册
3. 在 `configs/devices.yaml` 中添加设备配置
4. 无需修改任何现有代码

```python
# devices/fiber_spectrometer.py
from devices.base import DeviceBase
from core.registry import DeviceRegistry

@DeviceRegistry.register_device_type("ccs_spectrometer")
class CCSSpectrometer(DeviceBase):
    def connect(self): ...
    def acquire(self, exposure_ms): ...
    # ...
```

### 7.2 新增实验类型

1. 在 `operations/` 补充所需的原子操作（如果现有操作不够）
2. 在 `recipes/` 创建新配方文件，编排管道
3. 在 `configs/experiments/` 添加示例配置
4. 在 `examples/` 添加示例脚本

### 7.3 切换相机/光谱仪

只需修改 YAML 配置：

```yaml
# 使用 ProEM
devices:
  spectrometer:
    type: "lightfield"
    experiment_name: "HRBBSFGVS-ProEM"

# 切换到 PyLon
devices:
  spectrometer:
    type: "lightfield"
    experiment_name: "HRBBSFGVS-PyLon"

# 切换到 Andor
devices:
  spectrometer:
    type: "andor"
```

上层实验代码完全不变。

---

## 8. 错误处理策略

| 层级 | 策略 |
|------|------|
| **设备层** | 连接失败抛 `DeviceConnectionError`，操作失败抛 `DeviceOperationError`，带设备名和错误上下文 |
| **操作层** | `Operation.execute()` 可能返回包含 `error` 字段的结果字典，或抛 `/OperationError` |
| **管道层** | 根据 `ErrorStrategy` 决定重试/跳过/中止，所有错误写入日志 |
| **日志** | 使用 Python `logging`，分级记录（DEBUG=设备通信细节，INFO=步骤进度，WARNING=可恢复错误，ERROR=严重错误） |

---

## 9. 向后兼容策略

| 策略 | 说明 |
|------|------|
| `API/` 目录保留 | 原设备驱动文件保留不动，标记为 `@deprecated`，内部 import 新 `devices/` 实现 |
| `from API.LightFieldAPI import Experiment` | 仍然可用，但会打印 DeprecationWarning |
| 旧实验脚本 | 不做修改仍可运行。但建议逐步迁移到新架构 |

---

## 10. 实施计划

分 6 个阶段，每阶段完成后现有代码仍可运行：

| 阶段 | 内容 | 文件数 | 风险 | 验证方式 |
|------|------|--------|------|----------|
| **Phase 1: 基础设施** | 创建目录结构、`core/config.py`、`core/registry.py`、`core/signal_processing.py`、设备基类 `devices/base.py` | ~6 | 低 | import 测试 |
| **Phase 2: 设备层重构** | 将 `API/` 中的类迁移到 `devices/`，加 `DeviceBase` 继承，统一命名 | ~7 | 中 | 有设备时做连通性测试 |
| **Phase 3: 原子操作层** | 创建所有 `operations/*.py`，封装原子操作 | ~6 | 低 | 单元测试（mock 设备） |
| **Phase 4: 管道引擎** | 实现 `core/pipeline.py`（Pipeline, ErrorStrategy, 回调） | ~1 | 中 | 用 mock 操作测试编排逻辑 |
| **Phase 5: 实验配方** | 创建 `recipes/` 所有配方 + `configs/` 所有配置 + 向后兼容的旧 `API/` 标记 | ~10 | 中 | 在实际环境中运行一个完整实验 |
| **Phase 6: 文档与示例** | 编写所有 example、README、教程、API 参考 | ~15 | 低 | 让一个新同学按文档操作 |

---

## 11. 附录：设备清单与接口定义

### 11.1 完整设备清单

| 设备 | 型号/系列 | 通信 | 原驱动文件 | 关键功能 |
|------|-----------|------|------------|----------|
| CCD 光谱仪 | Princeton Instruments (PyLon/ProEM) | LightField .NET | `LightFieldAPI.py` | 设置波长/曝光/光栅，采集光谱 |
| CCD 光谱仪 | Andor | pyAndorSDK2 | `AndorAPI.py` | 同上（待补完） |
| 旋转电机 ×2 | Thorlabs CageRotator / KCube | Kinesis .NET | `ThorlabsAPI.py` | 归零，移动到指定角度 |
| 光学延迟线 | Feinixs (SMC 控制器) | 串口 + ftcore DLL | `feinixsAPI.py` | 归零，绝对/相对移动，速度/加速度设置 |
| 光功率计 | Thorlabs PM100/PM160/PM400 系列 | ctypes + VISA | `ThorlabsTLPM.py` | 测量功率，设置波长/量程 |
| 距离传感器 | KEYENCE CL-3000 系列 | CL3_IF.dll | `KEYENCEAPI.py` | 读取距离值（µm 精度） |
| 垂直位移台 | 通用步进电机（串口控制） | 串口 RS-232 | `verticalStageAPI.py` | 上下移动，速度控制，归零 |
| 采集卡 | Smacq USB-1000 | ctypes + usb-1000.dll | `SmacqAPI.py` | 差分模拟输入，多通道，可调采样率 |

### 11.2 设备方法速览（统一后）

```python
# 电机类设备通用接口
motor.home()              # 归零
motor.move_to(position)   # 绝对移动
motor.move_by(delta)      # 相对移动
motor.stop()              # 急停
motor.position            # 当前位置（property）

# 光谱仪通用接口
spec.set_exposure(ms)
spec.set_wavelength(nm)
spec.set_frames(n)
spec.acquire()            # 开始采集（阻塞直到完成）
spec.get_data()           # 返回 np.ndarray
spec.save(filename)

# 功率计
pm.measure()              # 返回功率值 (float, W)
pm.set_wavelength(nm)

# 距离传感器
sensor.get_distance()     # 返回 (float_um, is_valid: bool)

# 采集卡
daq.read(n_points=100)    # 返回 np.ndarray, shape (n_channels, n_points)
daq.close()
```

---

## 变更记录

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-06-02 | v1.0 | 初始设计文档 |
