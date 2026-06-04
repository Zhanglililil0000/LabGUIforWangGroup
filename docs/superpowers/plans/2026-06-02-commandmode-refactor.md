# CommandMode 重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 CommandMode 代码库从混乱的单文件实验脚本重构为分层管道架构，支持配置驱动、设备热插拔、实验序列编排，为 Web GUI 预留清晰 API。

**Architecture:** 5 层架构（devices → core → operations → recipes → api），管道引擎驱动实验编排，YAML 配置分离设备参数和实验参数。

**Tech Stack:** Python 3.9+, PyYAML, numpy, dataclasses, ABC, typing; 现有 DLL 依赖保持不变。

**Design Doc:** `docs/specs/2026-06-02-commandmode-refactor-design.md`

---

## 文件结构总览

```
CommandMode/
├── core/
│   ├── __init__.py
│   ├── config.py              # Config: YAML 配置加载
│   ├── registry.py            # DeviceRegistry + OperationRegistry
│   ├── context.py             # ExperimentContext 数据类
│   └── signal_processing.py   # compute_differential_signal
├── devices/
│   ├── __init__.py
│   ├── base.py                # DeviceBase ABC
│   ├── spectrometer.py        # LightFieldSpectrometer
│   ├── motor.py               # ThorlabsRotator
│   ├── delay_stage.py         # DelayStage
│   ├── power_meter.py         # ThorlabsPowerMeter
│   ├── distance_sensor.py     # KeyenceDistanceSensor
│   ├── vertical_stage.py      # VerticalStage
│   └── daq_card.py            # SmacqAICard
├── operations/
│   ├── __init__.py
│   ├── base.py                # Operation ABC + OperationStatus
│   ├── motor_ops.py           # MotorHome, MotorMoveTo
│   ├── spectrometer_ops.py    # AcquireSpectrum, SetExposure, SetWavelength
│   ├── delay_ops.py           # DelayStageHome, DelayStageMoveTo
│   ├── power_ops.py           # MeasurePower, PowerPolarizationScan
│   ├── height_ops.py          # SetPolarization, LockHeight
│   └── utility_ops.py         # Sleep, LogMessage
├── recipes/
│   ├── __init__.py
│   ├── sfg.py                 # sfg_polarization_scan, sfg_time_scan, sfg_pol_angle_scan
│   ├── srs.py                 # srs_wavelength_scan, srs_pol_scan, srs_time_scan
│   ├── raman.py               # raman_spectrum
│   └── diagnostics.py         # height_scan, power_pol_scan, system_diagnostics
├── configs/
│   ├── defaults.yaml
│   ├── devices.yaml
│   └── experiments/
│       ├── sfg_example.yaml
│       └── srs_example.yaml
├── api/
│   ├── __init__.py
│   └── schemas.py             # Pydantic models (远期)
├── examples/
│   ├── 01_connect_devices.py
│   ├── 02_acquire_single.py
│   ├── 03_sfg_simple.py
│   ├── 04_sfg_pol_scan.py
│   ├── 05_sfg_time_scan.py
│   ├── 06_srs_simple.py
│   ├── 07_height_scan.py
│   ├── 08_power_scan.py
│   ├── 09_pipeline_workflow.py
│   └── 10_batch_experiment.py
├── docs/
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── DEVICE_SETUP.md
│   ├── TUTORIAL.md
│   └── FAQ.md
└── tests/
    ├── __init__.py
    └── test_signal_processing.py
```

---

## Phase 1: 基础设施

### Task 1.1: 创建目录结构

**Files:**
- Create: `CommandMode/core/__init__.py`
- Create: `CommandMode/devices/__init__.py`
- Create: `CommandMode/operations/__init__.py`
- Create: `CommandMode/recipes/__init__.py`
- Create: `CommandMode/configs/` (empty dir)
- Create: `CommandMode/configs/experiments/` (empty dir)
- Create: `CommandMode/api/__init__.py`
- Create: `CommandMode/examples/` (empty dir)
- Create: `CommandMode/tests/__init__.py`

- [ ] **Step 1: 创建所有目录和 `__init__.py`**

```bash
mkdir -p d:\TraeProject\Project4SFG操作系统\CommandMode\core
mkdir -p d:\TraeProject\Project4SFG操作系统\CommandMode\devices
mkdir -p d:\TraeProject\Project4SFG操作系统\CommandMode\operations
mkdir -p d:\TraeProject\Project4SFG操作系统\CommandMode\recipes
mkdir -p d:\TraeProject\Project4SFG操作系统\CommandMode\configs\experiments
mkdir -p d:\TraeProject\Project4SFG操作系统\CommandMode\api
mkdir -p d:\TraeProject\Project4SFG操作系统\CommandMode\examples
mkdir -p d:\TraeProject\Project4SFG操作系统\CommandMode\tests
mkdir -p d:\TraeProject\Project4SFG操作系统\CommandMode\docs
```

- [ ] **Step 2: 创建所有 `__init__.py` 文件（空文件）**

在每个新建目录下创建空的 `__init__.py`。

- [ ] **Step 3: 验证目录结构**

Run: `pwd` in CommandMode, then list directories
Verify: core/, devices/, operations/, recipes/, configs/, configs/experiments/, api/, examples/, tests/, docs/ all exist with __init__.py

---

### Task 1.2: 实现 Config 配置管理 (`core/config.py`)

**Files:**
- Create: `CommandMode/core/config.py`

- [ ] **Step 1: 编写 Config 类**

```python
"""配置管理模块。从 YAML 加载配置，支持嵌套路径访问和环境变量覆盖。"""

import os
import yaml
from typing import Any, Optional


class Config:
    """从 YAML 文件加载实验配置。

    支持:
    - 嵌套键路径访问 (如 "devices.vis_rotator.serial")
    - extends 继承机制 (子配置可继承父配置)
    - 默认值回退

    Usage:
        config = Config("configs/experiments/sfg_example.yaml")
        serial = config.get("devices.vis_rotator.serial")  # "55358884"
    """

    def __init__(self, config_path: str):
        """加载 YAML 配置文件。

        Args:
            config_path: 相对于 CommandMode 目录的配置文件路径
        """
        self._config_path = config_path
        self._data: dict = {}

        # 确定基础路径 (CommandMode 目录)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(base_dir, config_path)

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"配置文件不存在: {full_path}")

        self._load_file(full_path)

    def _load_file(self, filepath: str):
        """加载文件并处理 extends 继承。"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # 处理继承
        if data.get("extends"):
            parent_path = data.pop("extends")
            parent_full = os.path.join(os.path.dirname(filepath), parent_path)
            parent_full = os.path.normpath(parent_full)
            if os.path.exists(parent_full):
                parent_config = {}
                with open(parent_full, "r", encoding="utf-8") as f:
                    parent_config = yaml.safe_load(f) or {}
                # 深度合并：子配置覆盖父配置
                self._deep_merge(parent_config, data)
                self._data = parent_config
            else:
                # 父配置不存在时直接使用当前数据
                self._data = data
        else:
            self._data = data

    def _deep_merge(self, base: dict, override: dict):
        """深度合并两个字典，override 覆盖 base 中的值。"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, key_path: str, default: Any = None) -> Any:
        """通过点号分隔的路径获取配置值。

        Args:
            key_path: 配置路径，如 "devices.vis_rotator.serial"
            default: 键不存在时的默认值

        Returns:
            配置值，或 default
        """
        keys = key_path.split(".")
        node = self._data
        for key in keys:
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                return default
        return node

    def get_devices(self) -> dict:
        """获取设备配置字典。

        Returns:
            devices 配置段，如 {"vis_rotator": {"type": "thorlabs_rotator", ...}, ...}
        """
        return self._data.get("devices", {})

    def get_experiment(self) -> dict:
        """获取实验配置字典。"""
        return self._data.get("experiment", {})

    def get_output(self) -> dict:
        """获取输出配置字典。"""
        return self._data.get("output", {})

    def get_scan(self) -> dict:
        """获取扫描配置字典。"""
        return self._data.get("scan", {})

    def get_polarization(self) -> dict:
        """获取偏振配置字典。"""
        return self._data.get("polarization", {})

    def get_spectrometer(self) -> dict:
        """获取光谱仪配置字典。"""
        return self._data.get("spectrometer", {})

    def to_dict(self) -> dict:
        """返回完整配置字典的副本。"""
        return dict(self._data)

    def __repr__(self) -> str:
        return f"Config({self._config_path})"
```

- [ ] **Step 2: 确保 PyYAML 可用**

Run: `python -c "import yaml; print(yaml.__version__)"`

If fails: `pip install PyYAML`

- [ ] **Step 3: 验证 Config 能正常 import**

Run: `python -c "import sys; sys.path.insert(0, 'd:\\TraeProject\\Project4SFG操作系统\\CommandMode'); from core.config import Config; print('OK')"`

---

### Task 1.3: 实现注册中心 (`core/registry.py`)

**Files:**
- Create: `CommandMode/core/registry.py`

- [ ] **Step 1: 编写 DeviceRegistry 和 OperationRegistry**

```python
"""注册中心模块。提供设备和操作的插件式注册/查找机制。"""

from typing import Any, Optional


class DeviceRegistry:
    """全局设备注册中心。

    设备类型在此注册，运行时按配置创建实例。

    Usage:
        @DeviceRegistry.register_device_type("thorlabs_rotator")
        class ThorlabsRotator(DeviceBase): ...

        dev = DeviceRegistry.create_device("thorlabs_rotator", "vis_rotator", config_dict)
        dev = DeviceRegistry.get_device("vis_rotator")
    """

    _device_types: dict[str, type] = {}
    _instances: dict[str, Any] = {}

    @classmethod
    def register_device_type(cls, name: str, device_cls: type):
        """注册设备类型。

        Args:
            name: 设备类型名称，如 "thorlabs_rotator"
            device_cls: 设备类（需继承 DeviceBase）
        """
        cls._device_types[name] = device_cls
        return device_cls

    @classmethod
    def create_device(cls, type_name: str, name: str, config: dict) -> Any:
        """根据类型名和配置创建设备实例。

        Args:
            type_name: 设备类型名 (已在 register_device_type 注册)
            name: 设备实例名 (如 "vis_rotator")
            config: 设备连接参数字典

        Returns:
            设备实例

        Raises:
            ValueError: 设备类型未注册
        """
        if type_name not in cls._device_types:
            raise ValueError(
                f"未注册的设备类型: {type_name}。"
                f"已注册: {list(cls._device_types.keys())}"
            )
        device_cls = cls._device_types[type_name]
        instance = device_cls(name=name, **cls._filter_init_params(device_cls, config))
        cls._instances[name] = instance
        return instance

    @classmethod
    def get_device(cls, name: str) -> Optional[Any]:
        """获取已创建的设备实例。"""
        return cls._instances.get(name)

    @classmethod
    def list_devices(cls) -> dict[str, Any]:
        """列出所有已创建的设备实例。"""
        return dict(cls._instances)

    @classmethod
    def list_device_types(cls) -> list[str]:
        """列出所有已注册的设备类型。"""
        return list(cls._device_types.keys())

    @classmethod
    def clear(cls):
        """清除所有注册（用于测试）。"""
        cls._device_types.clear()
        cls._instances.clear()

    @classmethod
    def _filter_init_params(cls, device_cls: type, config: dict) -> dict:
        """过滤配置字典，只保留 __init__ 接受的参数。"""
        import inspect
        try:
            sig = inspect.signature(device_cls.__init__)
            params = set(sig.parameters.keys()) - {"self"}
            return {k: v for k, v in config.items() if k in params}
        except (ValueError, TypeError):
            return config


class OperationRegistry:
    """全局操作注册中心。

    操作类型在此注册，管道通过操作名创建操作实例。

    Usage:
        @OperationRegistry.register
        class AcquireSpectrum(Operation): ...

        op = OperationRegistry.create("AcquireSpectrum", exposure_ms=60000)
    """

    _operations: dict[str, type] = {}

    @classmethod
    def register(cls, op_cls: type):
        """注册操作类型。

        Args:
            op_cls: 操作类（需继承 Operation）
        """
        cls._operations[op_cls.__name__] = op_cls
        return op_cls

    @classmethod
    def create(cls, name: str, **kwargs) -> Any:
        """根据操作名创建操作实例。

        Args:
            name: 操作类名
            **kwargs: 传递给操作构造函数的参数

        Returns:
            Operation 实例

        Raises:
            ValueError: 操作类型未注册
        """
        if name not in cls._operations:
            raise ValueError(
                f"未注册的操作类型: {name}。"
                f"已注册: {list(cls._operations.keys())}"
            )
        return cls._operations[name](**kwargs)

    @classmethod
    def list_all(cls) -> list[str]:
        """列出所有已注册的操作名。"""
        return list(cls._operations.keys())

    @classmethod
    def clear(cls):
        """清除所有注册（用于测试）。"""
        cls._operations.clear()
```

- [ ] **Step 2: 验证 import**

Run: `python -c "import sys; sys.path.insert(0, 'd:\\TraeProject\\Project4SFG操作系统\\CommandMode'); from core.registry import DeviceRegistry, OperationRegistry; print('OK')"`

---

### Task 1.4: 实现信号处理模块 (`core/signal_processing.py`)

**Files:**
- Create: `CommandMode/core/signal_processing.py`
- Create: `CommandMode/tests/test_signal_processing.py`

- [ ] **Step 1: 编写 compute_differential_signal 函数**

```python
"""信号处理模块。提供 SFG/SRS 实验的公共数据分析算法。"""

import numpy as np
from typing import Optional


def compute_differential_signal(
    intensities: list[np.ndarray],
    frames: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """计算泵浦-探测差分信号。

    用于 SRS 和 SFG 实验的 multi-frame 模式，交替采集泵浦开/关帧。
    通过比较相邻帧的强度比来计算差分信号。

    Args:
        intensities: 每帧的光谱强度数组列表，长度为 frames
        frames: 总帧数（必须为偶数）

    Returns:
        (ret, ret1, ret2) 三元组:
        - ret1: 奇数帧/偶数帧比值的平均 (pump-on / pump-off)
        - ret2: 偶数帧/奇数帧比值的平均 (pump-off / pump-on)
        - ret: 信号更强的一组 (max - min 更大者)

    Raises:
        ValueError: frames 不是偶数或 intensities 长度不匹配
    """
    if frames % 2 != 0:
        raise ValueError(f"frames 必须为偶数，当前值: {frames}")
    if len(intensities) != frames:
        raise ValueError(
            f"intensities 长度 ({len(intensities)}) 与 frames ({frames}) 不匹配"
        )

    # ret1: odd/even (i=0,2,4,... / i=1,3,5,...)
    ret1 = sum([
        intensities[i] / intensities[i + 1] - 1
        for i in range(0, frames, 2)
    ]) / (frames / 2)

    # ret2: even/odd (i=1,3,5,... / i=0,2,4,...)
    ret2 = sum([
        intensities[i + 1] / intensities[i] - 1
        for i in range(0, frames, 2)
    ]) / (frames / 2)

    # 选择信号动态范围更大的一组
    ret = ret1 if (max(ret1) - min(ret1) > max(ret2) - min(ret2)) else ret2

    return ret, ret1, ret2


def fit_polarization_curve(
    intensities: np.ndarray,
    angles_deg: np.ndarray
) -> dict:
    """拟合偏振角度-强度曲线。

    对每个波长的强度随偏振角变化做余弦平方拟合:
    I(θ) = A * cos²(θ - θ₀) + B

    Args:
        intensities: 形状为 (n_angles, n_pixels) 的强度矩阵
        angles_deg: 角度数组 (度)，长度为 n_angles

    Returns:
        dict with keys: "amplitude", "phase_offset_deg", "offset", "r_squared"
    """
    angles_rad = np.deg2rad(angles_deg)
    n_pixels = intensities.shape[1]

    amplitudes = np.zeros(n_pixels)
    phase_offsets = np.zeros(n_pixels)
    offsets = np.zeros(n_pixels)
    r_squared = np.zeros(n_pixels)

    for i in range(n_pixels):
        y = intensities[:, i]
        try:
            # 使用最小二乘法拟合 A*cos²(θ-θ₀) + B = A*(cos(2(θ-θ₀))+1)/2 + B
            # = (A/2)*cos(2θ-2θ₀) + (A/2 + B)
            # 线性化: y = a*cos(2θ) + b*sin(2θ) + c
            cos_2theta = np.cos(2 * angles_rad)
            sin_2theta = np.sin(2 * angles_rad)
            X = np.column_stack([cos_2theta, sin_2theta, np.ones_like(angles_rad)])
            coeffs, residuals, rank, s = np.linalg.lstsq(X, y, rcond=None)

            a, b, c = coeffs
            amplitude = 2 * np.sqrt(a**2 + b**2)
            phase_offset = np.arctan2(b, a) / 2  # 弧度
            offset_val = c - amplitude / 2

            amplitudes[i] = amplitude
            phase_offsets[i] = np.rad2deg(phase_offset) % 180
            offsets[i] = offset_val

            # R²
            y_pred = amplitude/2 * np.cos(2*(angles_rad - phase_offset)) + amplitude/2 + offset_val
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared[i] = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        except np.linalg.LinAlgError:
            amplitudes[i] = 0
            phase_offsets[i] = 0
            offsets[i] = 0
            r_squared[i] = 0

    return {
        "amplitude": amplitudes,
        "phase_offset_deg": phase_offsets,
        "offset": offsets,
        "r_squared": r_squared,
    }
```

- [ ] **Step 2: 编写测试**

```python
"""信号处理模块的单元测试。"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.signal_processing import compute_differential_signal, fit_polarization_curve


def test_compute_differential_signal_basic():
    """基本功能测试：已知输入验证输出形状和数值范围。"""
    # 模拟 4 帧数据，每帧 100 个像素
    intensities = [
        np.ones(100) * 1.0,   # frame 0 (pump on)  - 信号
        np.ones(100) * 0.9,   # frame 1 (pump off) - 参考
        np.ones(100) * 1.1,   # frame 2 (pump on)  - 信号
        np.ones(100) * 0.95,  # frame 3 (pump off) - 参考
    ]

    ret, ret1, ret2 = compute_differential_signal(intensities, frames=4)

    assert len(ret) == 100
    assert len(ret1) == 100
    assert len(ret2) == 100

    # ret1: avg of (1.0/0.9 - 1) + (1.1/0.95 - 1) / 2 ≈ avg of 0.1111 + 0.1579 / 2 ≈ 0.1345
    expected_ret1_0 = (1.0 / 0.9 - 1 + 1.1 / 0.95 - 1) / 2
    assert abs(ret1[0] - expected_ret1_0) < 0.001

    # 结果应该全为非负（因为是比值减一且奇数帧 >= 偶数帧）
    assert np.all(ret >= 0)


def test_compute_differential_signal_odd_frames_raises():
    """奇数帧应抛出 ValueError。"""
    intensities = [np.ones(10) for _ in range(3)]
    try:
        compute_differential_signal(intensities, frames=3)
        assert False, "应该抛出 ValueError"
    except ValueError:
        pass


def test_compute_differential_signal_mismatch_raises():
    """帧数不匹配应抛出 ValueError。"""
    intensities = [np.ones(10) for _ in range(4)]
    try:
        compute_differential_signal(intensities, frames=6)
        assert False, "应该抛出 ValueError"
    except ValueError:
        pass


def test_fit_polarization_curve():
    """偏振拟合测试：理想 cos² 曲线应完美拟合。"""
    angles = np.arange(0, 181, 10)  # 0, 10, 20, ..., 180
    angles_rad = np.deg2rad(angles)

    # 生成理想 cos² 数据: I(θ) = 2*cos²(θ - 45°) + 1
    true_amplitude = 2.0
    true_phase = np.deg2rad(45)
    true_offset = 1.0

    n_pixels = 5
    intensities = np.zeros((len(angles), n_pixels))
    for i, a in enumerate(angles_rad):
        intensities[i, :] = true_amplitude * np.cos(a - true_phase)**2 + true_offset

    result = fit_polarization_curve(intensities, angles)

    # 每个像素的拟合结果应接近真实值
    for i in range(n_pixels):
        assert abs(result["amplitude"][i] - true_amplitude) < 0.1
        assert result["r_squared"][i] > 0.99


if __name__ == "__main__":
    test_compute_differential_signal_basic()
    test_compute_differential_signal_odd_frames_raises()
    test_compute_differential_signal_mismatch_raises()
    test_fit_polarization_curve()
    print("All tests passed!")
```

- [ ] **Step 3: 运行测试**

Run: `python d:\TraeProject\Project4SFG操作系统\CommandMode\tests\test_signal_processing.py`
Expected: `All tests passed!`

---

### Task 1.5: 实现实验上下文 (`core/context.py`)

**Files:**
- Create: `CommandMode/core/context.py`

- [ ] **Step 1: 编写 ExperimentContext**

```python
"""实验运行时上下文。贯穿整个管道执行过程。"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
import logging


@dataclass
class ExperimentContext:
    """实验运行时上下文，在管道执行期间保持。

    包含所有设备引用、配置、共享数据和运行状态。

    Usage:
        ctx = ExperimentContext(config=config)
        ctx.devices["vis_rotator"] = rotator_instance
        ctx.data["last_spectrum"] = {...}
    """

    config: Any = None
    """Config 实例"""

    devices: dict[str, Any] = field(default_factory=dict)
    """设备实例字典，key 为设备名如 "vis_rotator", "spectrometer" """

    data: dict[str, Any] = field(default_factory=dict)
    """共享数据空间，管道步骤间通过此字典传递计算结果"""

    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("SFGExperiment"))
    """日志记录器"""

    start_time: datetime = field(default_factory=datetime.now)
    """实验开始时间"""

    status: str = "initializing"
    """实验状态: "initializing" | "running" | "paused" | "done" | "failed" """

    _pause_flag: bool = field(default=False, repr=False)
    _stop_flag: bool = field(default=False, repr=False)

    def pause(self):
        """请求暂停。当前步骤完成后暂停。"""
        self._pause_flag = True
        self.status = "paused"
        self.logger.info("实验已请求暂停")

    def resume(self):
        """恢复执行。"""
        self._pause_flag = False
        self.status = "running"
        self.logger.info("实验已恢复")

    def stop(self):
        """请求停止。当前步骤完成后退出。"""
        self._stop_flag = True
        self.status = "failed"
        self.logger.info("实验已请求停止")

    @property
    def should_pause(self) -> bool:
        return self._pause_flag

    @property
    def should_stop(self) -> bool:
        return self._stop_flag

    def reset_flags(self):
        """重置暂停/停止标志（管道开始时调用）。"""
        self._pause_flag = False
        self._stop_flag = False
        self.status = "running"
```

- [ ] **Step 2: 验证 import**

Run: `python -c "import sys; sys.path.insert(0, 'd:\\TraeProject\\Project4SFG操作系统\\CommandMode'); from core.context import ExperimentContext; ctx = ExperimentContext(); print('OK:', ctx.status)"`

---

### Task 1.6: 实现设备基类 (`devices/base.py`)

**Files:**
- Create: `CommandMode/devices/base.py`

- [ ] **Step 1: 编写 DeviceBase**

```python
"""设备基类。所有硬件的抽象接口。"""

from abc import ABC, abstractmethod
from typing import Any


class DeviceError(Exception):
    """设备相关错误的基类。"""


class DeviceConnectionError(DeviceError):
    """设备连接错误。"""
    def __init__(self, device_name: str, detail: str = ""):
        self.device_name = device_name
        self.detail = detail
        super().__init__(f"设备 '{device_name}' 连接失败: {detail}")


class DeviceOperationError(DeviceError):
    """设备操作错误。"""
    def __init__(self, device_name: str, operation: str, detail: str = ""):
        self.device_name = device_name
        self.operation = operation
        self.detail = detail
        super().__init__(f"设备 '{device_name}' 操作 '{operation}' 失败: {detail}")


class DeviceBase(ABC):
    """所有设备的抽象基类。

    子类必须实现 connect, disconnect, is_connected。
    推荐使用上下文管理器:

        with MyDevice(name="dev1", ...) as dev:
            dev.some_operation()
    """

    def __init__(self, name: str = ""):
        """初始化设备。

        Args:
            name: 设备实例名称，如 "vis_rotator"
        """
        self._name = name
        self._connected = False

    @property
    def name(self) -> str:
        """设备名称。"""
        return self._name

    @abstractmethod
    def connect(self) -> bool:
        """建立设备连接。

        Returns:
            True 表示连接成功
        """
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """断开设备连接，释放资源。"""
        ...

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """设备是否已连接。"""
        ...

    @property
    def status(self) -> dict:
        """返回设备状态字典，供 GUI / 日志使用。

        Returns:
            包含 name, type, is_connected 等字段的字典
        """
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "is_connected": self.is_connected,
        }

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', connected={self.is_connected})"
```

- [ ] **Step 2: 验证 import 和 DeviceBase 使用**

Run: `python -c "import sys; sys.path.insert(0, 'd:\\TraeProject\\Project4SFG操作系统\\CommandMode'); from devices.base import DeviceBase, DeviceError, DeviceConnectionError; print('OK')"`

---

## Phase 2: 设备层重构

### Task 2.1: 迁移光谱仪 (`devices/spectrometer.py`)

**Files:**
- Create: `CommandMode/devices/spectrometer.py`

- [ ] **Step 1: 编写 LightFieldSpectrometer**

```python
"""光谱仪设备驱动。封装 LightField Automation API。"""

import os
import time
import sys
import clr
from typing import Optional

from System.IO import Path
from System.Threading import AutoResetEvent
from System import String, Array
from System.Collections.Generic import List

# LightField 路径配置
sys.path.append(os.environ.get('LIGHTFIELD_ROOT', ''))
sys.path.append(os.path.join(os.environ.get('LIGHTFIELD_ROOT', ''), 'AddInViews'))
clr.AddReference('PrincetonInstruments.LightFieldViewV5')
clr.AddReference('PrincetonInstruments.LightField.AutomationV5')
clr.AddReference('PrincetonInstruments.LightFieldAddInSupportServices')

from PrincetonInstruments.LightField.Automation import Automation
from PrincetonInstruments.LightField.AddIns import ExperimentSettings, SpectrometerSettings, CameraSettings, DeviceType

from devices.base import DeviceBase, DeviceConnectionError, DeviceOperationError


class LightFieldSpectrometer(DeviceBase):
    """Princeton Instruments 光谱仪 (通过 LightField 软件控制)。

    支持 PyLon 和 ProEM 相机。

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
        self._auto: Optional[Automation] = None
        self._application = None
        self._experiment = None
        self._acquire_completed: Optional[AutoResetEvent] = None

    def connect(self) -> bool:
        try:
            self._auto = Automation(True, List[String]())
            self._application = self._auto.LightFieldApplication
            self._experiment = self._application.Experiment
            self._acquire_completed = AutoResetEvent(False)

            # 加载实验配置
            self._experiment.Load(self._experiment_name)

            # 验证设备
            if not self._device_found():
                raise DeviceConnectionError(self.name, "未找到相机设备")

            # 设置文件保存路径
            if self._file_path:
                self._experiment.SetValue(
                    ExperimentSettings.FileNameGenerationDirectory,
                    self._file_path
                )

            self._connected = True
            print(f"[{self.name}] LightField 光谱仪已连接，实验: {self._experiment_name}")
            return True

        except Exception as e:
            raise DeviceConnectionError(self.name, str(e))

    def _device_found(self) -> bool:
        for device in self._experiment.ExperimentDevices:
            if device.Type == DeviceType.Camera:
                return True
        return False

    def disconnect(self) -> None:
        try:
            if self._auto:
                self._auto.Dispose()
                self._auto = None
            self._connected = False
            print(f"[{self.name}] LightField 光谱仪已断开")
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

    def set_file_path(self, file_path: str):
        """设置数据文件保存目录。"""
        self._file_path = file_path
        if self._connected and self._experiment:
            self._experiment.SetValue(
                ExperimentSettings.FileNameGenerationDirectory,
                file_path
            )

    def save_file(self, filename: str):
        """设置保存文件名（不带扩展名）。"""
        if not self._experiment:
            raise DeviceOperationError(self.name, "save_file", "设备未连接")
        self._experiment.SetValue(
            ExperimentSettings.FileNameGenerationBaseFileName,
            Path.GetFileName(filename)
        )
        self._experiment.SetValue(ExperimentSettings.FileNameGenerationAttachIncrement, False)
        self._experiment.SetValue(ExperimentSettings.FileNameGenerationAttachDate, False)
        self._experiment.SetValue(ExperimentSettings.FileNameGenerationAttachTime, False)

    def set_frames_number(self, frames: int):
        """设置采集帧数。"""
        if not self._experiment:
            raise DeviceOperationError(self.name, "set_frames_number", "设备未连接")
        self._experiment.SetValue(ExperimentSettings.AcquisitionFramesToStore, str(frames))

    def set_center_wavelength(self, wavelength_nm: float):
        """设置光栅中心波长 (nm)。"""
        if not self._experiment:
            raise DeviceOperationError(self.name, "set_center_wavelength", "设备未连接")
        self._experiment.SetValue(SpectrometerSettings.GratingCenterWavelength, str(wavelength_nm))

    def set_exposure_time(self, exposure_ms: int):
        """设置曝光时间 (ms)。"""
        if not self._experiment:
            raise DeviceOperationError(self.name, "set_exposure_time", "设备未连接")
        self._experiment.SetValue(CameraSettings.ShutterTimingExposureTime, str(exposure_ms))

    def set_grating(self, grating: str):
        """选择光栅。"""
        if not self._experiment:
            raise DeviceOperationError(self.name, "set_grating", "设备未连接")
        self._experiment.SetValue(SpectrometerSettings.GratingSelected, grating)

    def get_pixels(self) -> int:
        """获取 CCD 像素数。"""
        if not self._experiment:
            raise DeviceOperationError(self.name, "get_pixels", "设备未连接")
        return int(self._experiment.GetValue(CameraSettings.SensorInformationActiveAreaWidth))

    def acquire(self) -> None:
        """触发光谱采集（阻塞直到完成）。"""
        if not self._experiment or not self._acquire_completed:
            raise DeviceOperationError(self.name, "acquire", "设备未连接")

        # 注册采集完成事件
        self._acquire_completed.Reset()

        def on_completed(sender, event_args):
            print(f"[{self.name}] 采集完成")
            self._acquire_completed.Set()

        self._experiment.ExperimentCompleted += on_completed
        self._experiment.Acquire()
        self._acquire_completed.WaitOne()
        self._experiment.ExperimentCompleted -= on_completed
```

- [ ] **Step 2: 验证 import**

Run: `python -c "import sys; sys.path.insert(0, 'd:\\TraeProject\\Project4SFG操作系统\\CommandMode'); from devices.spectrometer import LightFieldSpectrometer; print('OK')"`

Note: 此文件依赖 LightField 运行时环境（LIGHTFIELD_ROOT 环境变量、Kinesis DLL），在无硬件环境下 import 可能因 clr.AddReference 失败。若失败则跳过——Phase 5 测试时在实际环境中验证。

---

### Task 2.2: 迁移旋转电机 (`devices/motor.py`)

**Files:**
- Create: `CommandMode/devices/motor.py`

- [ ] **Step 1: 编写 ThorlabsRotator**

```python
"""Thorlabs 旋转电机设备驱动。封装 Kinesis .NET API。"""

import time
import clr
from System import Decimal

clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\ThorLabs.MotionControl.IntegratedStepperMotorsCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\ThorLabs.MotionControl.KCube.DCServoCLI.dll")

from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI
from Thorlabs.MotionControl.GenericMotorCLI import *
from Thorlabs.MotionControl.IntegratedStepperMotorsCLI import *
from Thorlabs.MotionControl.KCube.DCServoCLI import *
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
        self._driver_type = driver  # "Cage" 或 "KCube"
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
        s.update({
            "driver": self._driver_type,
            "serial": self._serial,
        })
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
```

- [ ] **Step 2: 验证 import**

Run: `python -c "import sys; sys.path.insert(0, 'd:\\TraeProject\\Project4SFG操作系统\\CommandMode'); from devices.motor import ThorlabsRotator; print('OK')"`

---

### Task 2.3: 迁移光学延迟线 (`devices/delay_stage.py`)

**Files:**
- Create: `CommandMode/devices/delay_stage.py`

- [ ] **Step 1: 编写 DelayStage**

```python
"""光学延迟线设备驱动 (Feinixs SMC/AMC/NANO 控制器)。"""

import time
import clr

clr.AddReference('resources/ftcorecs')
from ftcorecs import ftcore

from devices.base import DeviceBase, DeviceConnectionError, DeviceOperationError


class DelayStage(DeviceBase):
    """光学延迟线 (Feinixs 控制器)。

    Usage:
        stage = DelayStage(name="delay_stage", port="COM4", baud=19200,
                          controller="SMC", slave=0xCC)
        stage.connect()
        stage.home("X")
        stage.move_to("X", 150.0)
    """

    CONTROLLER_TYPES = {
        "SMC": ftcore.CONTROLLER_TYPE_SMC,
        "AMC": ftcore.CONTROLLER_TYPE_AMC,
        "NANO": ftcore.CONTROLLER_TYPE_NANO,
        "MINI04": ftcore.CONTROLLER_TYPE_MINI04,
    }

    def __init__(
        self,
        name: str = "delay_stage",
        port: str = "COM4",
        baud: int = 19200,
        controller: str = "SMC",
        slave: int = 0xCC,
        limit_isnegative: bool = True,
    ):
        super().__init__(name)
        self._port = port
        self._baud = baud
        self._controller_type = controller
        self._slave = slave
        self._limit_isnegative = limit_isnegative
        self._handle = None

    def connect(self) -> bool:
        try:
            ct = self.CONTROLLER_TYPES.get(self._controller_type, ftcore.CONTROLLER_TYPE_SMC)
            limit_flag = ftcore.FT_TRUE if self._limit_isnegative else ftcore.FT_FALSE

            ret, handle = ftcore.ft_open_com(
                self._port, self._baud, ct, self._slave, limit_flag, 0
            )

            if ret != ftcore.FT_SUCESS:
                raise DeviceConnectionError(self.name, f"打开串口失败 (ret={ret})")

            self._handle = handle
            self._connected = True
            print(f"[{self.name}] 已连接 (port={self._port}, controller={self._controller_type})")
            return True

        except Exception as e:
            raise DeviceConnectionError(self.name, str(e))

    def disconnect(self) -> None:
        try:
            if self._handle is not None:
                ftcore.ft_close(self._handle)
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
        s.update({"port": self._port, "controller": self._controller_type})
        return s

    def _check_connected(self, op: str):
        if self._handle is None:
            raise DeviceOperationError(self.name, op, "设备未连接")

    def _ret_check(self, ret, op: str):
        if ret != ftcore.FT_SUCESS:
            raise DeviceOperationError(self.name, op, f"操作失败 (ret={ret})")

    def home(self, axis: str = "X"):
        """归零指定轴。"""
        self._check_connected("home")
        pos = self.get_position(axis)
        homing_vel = self.get_homing_velocity(axis)
        ret = ftcore.ft_single_home(self._handle, axis)
        self._ret_check(ret, "home")
        print(f"[{self.name}] {axis} 轴正在归零...")

        expected_sleep = abs(pos) / max(homing_vel, 1)
        time.sleep(expected_sleep)
        while self.is_running(axis):
            time.sleep(2)

        current_pos = self.get_position(axis)
        print(f"[{self.name}] {axis} 轴归零完成, 位置: {current_pos}")
        return current_pos

    def move_to(self, axis: str, position: float):
        """绝对移动。"""
        self._check_connected("move_to")
        current_pos = self.get_position(axis)
        vel = self.get_velocity(axis)
        ret = ftcore.ft_single_moveabs(self._handle, axis, position)
        self._ret_check(ret, "move_to")
        print(f"[{self.name}] {axis} 轴移动到 {position}...")

        travel_time = abs(current_pos - position) / max(vel, 0.001)
        time.sleep(travel_time)
        while self.is_running(axis):
            time.sleep(2)

        new_pos = self.get_position(axis)
        print(f"[{self.name}] {axis} 轴移动完成, 位置: {new_pos}")
        return new_pos

    def move_by(self, axis: str, delta: float):
        """相对移动。"""
        self._check_connected("move_by")
        vel = self.get_velocity(axis)
        ret = ftcore.ft_single_move(self._handle, axis, delta)
        self._ret_check(ret, "move_by")
        print(f"[{self.name}] {axis} 轴相对移动 {delta}...")

        time.sleep(abs(delta) / max(vel, 0.001))
        while self.is_running(axis):
            time.sleep(2)

        return self.get_position(axis)

    def get_position(self, axis: str = "X") -> float:
        self._check_connected("get_position")
        ret, pos = ftcore.ft_single_getpos(self._handle, axis, 0)
        self._ret_check(ret, "get_position")
        return pos

    def is_running(self, axis: str = "X") -> bool:
        self._check_connected("is_running")
        ret, running = ftcore.ft_single_isrunning(self._handle, axis, 0)
        self._ret_check(ret, "is_running")
        return running == ftcore.FT_TRUE

    def stop(self, axis: str = "X"):
        self._check_connected("stop")
        ret = ftcore.ft_single_stop(self._handle, axis)
        self._ret_check(ret, "stop")
        print(f"[{self.name}] {axis} 轴已停止")

    def get_velocity(self, axis: str = "X") -> float:
        self._check_connected("get_velocity")
        ret, vel = ftcore.ft_get_vel(self._handle, axis, 0)
        self._ret_check(ret, "get_velocity")
        return vel

    def get_homing_velocity(self, axis: str = "X") -> float:
        self._check_connected("get_homing_velocity")
        ret, vel = ftcore.ft_get_homingvel(self._handle, axis, 0)
        self._ret_check(ret, "get_homing_velocity")
        return vel
```

- [ ] **Step 2: 验证 import**

Run: `python -c "import sys; sys.path.insert(0, 'd:\\TraeProject\\Project4SFG操作系统\\CommandMode'); from devices.delay_stage import DelayStage; print('OK')"`

---

### Task 2.4: 迁移其余设备驱动

**Files:**
- Create: `CommandMode/devices/power_meter.py` (封装 ThorlabsTLPM)
- Create: `CommandMode/devices/distance_sensor.py` (封装 KEYENCEAPI)
- Create: `CommandMode/devices/vertical_stage.py` (封装 verticalStageAPI)
- Create: `CommandMode/devices/daq_card.py` (封装 SmacqAPI)

- [ ] **Step 1: `devices/power_meter.py`**

```python
"""Thorlabs 光功率计设备驱动。"""

import time
from ctypes import (
    cdll, c_long, c_ulong, c_uint32, byref, create_string_buffer,
    c_bool, c_char_p, c_int, c_int16, c_double, sizeof, c_voidp
)

from devices.base import DeviceBase, DeviceConnectionError, DeviceOperationError

# 导入 ThorlabsTLPM 类（复用现有 DLL 绑定）
import sys
import os
_current_dir = os.path.dirname(os.path.abspath(__file__))
_api_dir = os.path.join(os.path.dirname(_current_dir), 'API')
if _api_dir not in sys.path:
    sys.path.insert(0, os.path.dirname(_current_dir))
from API.ThorlabsTLPM import TLPM


class ThorlabsPowerMeter(DeviceBase):
    """Thorlabs 光功率计 (PM100D/PM100A/PM160/PM400 系列)。

    Usage:
        pm = ThorlabsPowerMeter(name="power_meter", wavelength_nm=532.0)
        pm.connect()
        power = pm.measure()  # 返回功率值 (W)
    """

    def __init__(self, name: str = "power_meter", wavelength_nm: float = 532.0):
        super().__init__(name)
        self._wavelength_nm = wavelength_nm
        self._tlpm: TLPM = TLPM()
        self._resource_name = None

    def connect(self) -> bool:
        try:
            device_count = c_uint32()
            self._tlpm.findRsrc(byref(device_count))
            print(f"[{self.name}] 找到 {device_count.value} 个功率计设备")

            if device_count.value == 0:
                raise DeviceConnectionError(self.name, "未找到功率计设备")

            resource_name = create_string_buffer(1024)
            self._tlpm.getRsrcName(c_int(0), resource_name)
            self._resource_name = resource_name

            self._tlpm.open(resource_name, c_bool(True), c_bool(True))

            message = create_string_buffer(1024)
            self._tlpm.getCalibrationMsg(message)
            print(f"[{self.name}] 已连接, 校准日期: {c_char_p(message.raw).value}")

            time.sleep(1)

            # 设置波长
            self.set_wavelength(self._wavelength_nm)
            # 自动量程
            self._tlpm.setPowerAutoRange(c_int16(1))
            # 单位: Watt
            self._tlpm.setPowerUnit(c_int16(0))

            self._connected = True
            return True

        except Exception as e:
            raise DeviceConnectionError(self.name, str(e))

    def disconnect(self) -> None:
        try:
            if self._tlpm:
                self._tlpm.close()
            self._connected = False
            print(f"[{self.name}] 已断开")
        except Exception:
            pass

    @property
    def is_connected(self) -> bool:
        return self._connected

    def set_wavelength(self, nm: float):
        self._tlpm.setWavelength(c_double(nm))
        self._wavelength_nm = nm

    def measure(self) -> float:
        """测量当前功率。

        Returns:
            功率值 (W)
        """
        if not self._connected:
            raise DeviceOperationError(self.name, "measure", "设备未连接")
        power = c_double()
        self._tlpm.measPower(byref(power))
        return power.value

    def measure_average(self, n_samples: int = 10, interval_s: float = 0.1) -> float:
        """多次测量取平均。

        Args:
            n_samples: 采样次数
            interval_s: 采样间隔 (秒)

        Returns:
            平均功率值 (W)
        """
        total = 0.0
        for _ in range(n_samples):
            total += self.measure()
            time.sleep(interval_s)
        return total / n_samples
```

- [ ] **Step 2: `devices/distance_sensor.py`**

```python
"""KEYENCE 距离传感器设备驱动。"""

from devices.base import DeviceBase, DeviceConnectionError, DeviceOperationError

import sys
import os
_current_dir = os.path.dirname(os.path.abspath(__file__))
_api_dir = os.path.join(os.path.dirname(_current_dir), 'API')
if _api_dir not in sys.path:
    sys.path.insert(0, os.path.dirname(_current_dir))
from API.KEYENCEAPI import DistanceDetector


class KeyenceDistanceSensor(DeviceBase):
    """KEYENCE CL-3000 系列激光距离传感器。

    Usage:
        sensor = KeyenceDistanceSensor(name="distance_sensor")
        sensor.connect()
        height, is_valid = sensor.get_distance()
    """

    def __init__(self, name: str = "distance_sensor", device_id: int = 0, timeout: int = 10000):
        super().__init__(name)
        self._device_id = device_id
        self._timeout = timeout
        self._detector: DistanceDetector = None

    def connect(self) -> bool:
        try:
            self._detector = DistanceDetector(
                deviceId=self._device_id,
                timeout=self._timeout
            )
            self._connected = True
            print(f"[{self.name}] KEYENCE 距离传感器已连接")
            return True
        except Exception as e:
            raise DeviceConnectionError(self.name, str(e))

    def disconnect(self) -> None:
        self._connected = False
        self._detector = None
        print(f"[{self.name}] 已断开")

    @property
    def is_connected(self) -> bool:
        return self._connected

    def get_distance(self) -> tuple:
        """读取距离值。

        Returns:
            (height_um, is_valid) 元组
        """
        if not self._detector:
            raise DeviceOperationError(self.name, "get_distance", "设备未连接")
        return self._detector.get_distance()
```

- [ ] **Step 3: `devices/vertical_stage.py`**

```python
"""垂直位移台设备驱动 (串口控制)。"""

import serial
import time

from devices.base import DeviceBase, DeviceConnectionError, DeviceOperationError


class VerticalStage(DeviceBase):
    """垂直电动位移台 (串口步进电机)。

    Usage:
        stage = VerticalStage(name="vertical_stage", port="COM9", baud=9600)
        stage.connect()
        stage.home(axis=1)
        stage.move(axis=1, distance=100)
    """

    def __init__(self, name: str = "vertical_stage", port: str = "COM9", baud: int = 9600):
        super().__init__(name)
        self._port = port
        self._baud = baud
        self._ser: serial.Serial = None

    def connect(self) -> bool:
        try:
            self._ser = serial.Serial(self._port)
            self._ser.baudrate = self._baud
            self._ser.bytesize = serial.EIGHTBITS
            self._ser.parity = serial.PARITY_NONE
            self._ser.stopbits = serial.STOPBITS_ONE
            self._ser.timeout = 5
            self._ser.rtscts = True
            self._connected = True
            print(f"[{self.name}] 垂直位移台已连接 (port={self._port})")
            return True
        except Exception as e:
            raise DeviceConnectionError(self.name, str(e))

    def disconnect(self) -> None:
        try:
            if self._ser:
                self._ser.close()
            self._connected = False
            print(f"[{self.name}] 已断开")
        except Exception:
            pass

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _is_busy(self) -> bool:
        if not self._ser:
            return False
        wdata = "!:\r\n"
        self._ser.write(wdata.encode())
        rdata = self._ser.readline()
        return rdata == b"B\r\n"

    def _wait_until_ready(self):
        while self._is_busy():
            time.sleep(1)

    def home(self, axis: int = 1):
        self._check_connected("home")
        wdata = f"H:{axis}\r\n"
        self._ser.write(wdata.encode())
        self._ser.readline()
        self._wait_until_ready()
        print(f"[{self.name}] 轴 {axis} 归零完成")

    def move(self, axis: int, distance: int):
        self._check_connected("move")
        wdata = f"M:{axis}+P{distance * 2}\r\n"
        self._ser.write(wdata.encode())
        self._ser.readline()
        time.sleep(1)
        self._ser.write(b'G:\r\n')
        self._ser.readline()
        self._wait_until_ready()
        print(f"[{self.name}] 轴 {axis} 移动 {distance} 完成")

    def move_to(self, axis: int, position: int):
        self._check_connected("move_to")
        wdata = f"A:{axis}+P{position * 2}\r\n"
        self._ser.write(wdata.encode())
        self._ser.readline()
        time.sleep(1)
        self._ser.write(b'G:\r\n')
        self._ser.readline()
        self._wait_until_ready()
        print(f"[{self.name}] 轴 {axis} 移动到 {position} 完成")

    def set_speed(self, axis: int, min_speed: int, max_speed: int, accel_time: int):
        self._check_connected("set_speed")
        wdata = f"D:{axis}S{min_speed * 2}F{max_speed * 2}R{accel_time}\r\n"
        self._ser.write(wdata.encode())
        self._ser.readline()
        self._wait_until_ready()
        print(f"[{self.name}] 轴 {axis} 速度设置完成")

    def _check_connected(self, op: str):
        if not self._ser:
            raise DeviceOperationError(self.name, op, "设备未连接")
```

- [ ] **Step 4: `devices/daq_card.py`**

```python
"""Smacq 采集卡设备驱动。"""

import ctypes
import numpy as np
from ctypes import windll, c_int, c_float, c_char, c_ulong, c_ushort, c_uint, c_long, POINTER

from devices.base import DeviceBase, DeviceConnectionError, DeviceOperationError


class SmacqAICard(DeviceBase):
    """Smacq USB-1000 采集卡。

    Usage:
        card = SmacqAICard(name="daq", device_id=0, channels=1, sample_rate=1000)
        card.connect()
        data = card.read(num_points=100)
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
                self._dll = windll.LoadLibrary('resources\\Smacq\\x64\\usb-1000.dll')
            except Exception:
                try:
                    self._dll = windll.LoadLibrary('resources\\Smacq\\x86\\usb-1000.dll')
                except Exception as e:
                    raise DeviceConnectionError(self.name, f"无法加载 DLL: {e}")

            res = self._dll.OpenDevice(c_int(self._device_id))
            if res != 0:
                raise DeviceConnectionError(self.name, f"OpenDevice 失败 (code={res})")

            self._dll.ResetDevice(c_int(self._device_id))
            self._dll.SetChanMode(c_int(self._device_id), c_char(0))  # 差分模式
            self._dll.SetUSB1AiRange(c_int(self._device_id), c_float(self._range_val))
            self._dll.SetSampleRate(c_int(self._device_id), c_uint(self._sample_rate))
            self._dll.SetChanSel(c_int(self._device_id), c_ushort(self._channels))
            self._dll.StartRead(c_int(self._device_id))
            self._dll.SetSoftTrig(c_int(self._device_id), c_char(1))

            self._connected = True
            print(f"[{self.name}] Smacq 采集卡已连接 (device_id={self._device_id})")
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

        channel_count = self._count_channels()
        total_points = num_points * channel_count
        ai_buffer = np.zeros(total_points, dtype='float32')

        res = self._dll.GetAiChans(
            c_int(self._device_id),
            c_ulong(num_points),
            c_ushort(self._channels),
            ai_buffer.ctypes.data_as(POINTER(ctypes.c_float)),
            c_long(self._timeout_val),
        )

        if res < 0:
            raise DeviceOperationError(self.name, "read", f"GetAiChans 失败 (code={res})")

        if channel_count > 1:
            return ai_buffer.reshape(channel_count, num_points)
        return ai_buffer.reshape(1, num_points)

    def _count_channels(self) -> int:
        count = 0
        ch = self._channels
        while ch:
            count += ch & 1
            ch >>= 1
        return count
```

- [ ] **Step 5: 批量验证 import**

Run:
```bash
python -c "import sys; sys.path.insert(0, 'd:\\TraeProject\\Project4SFG操作系统\\CommandMode'); from devices.power_meter import ThorlabsPowerMeter; print('power_meter OK')"
python -c "import sys; sys.path.insert(0, 'd:\\TraeProject\\Project4SFG操作系统\\CommandMode'); from devices.distance_sensor import KeyenceDistanceSensor; print('distance_sensor OK')"
python -c "import sys; sys.path.insert(0, 'd:\\TraeProject\\Project4SFG操作系统\\CommandMode'); from devices.vertical_stage import VerticalStage; print('vertical_stage OK')"
python -c "import sys; sys.path.insert(0, 'd:\\TraeProject\\Project4SFG操作系统\\CommandMode'); from devices.daq_card import SmacqAICard; print('daq_card OK')"
```

---

## Phase 3: 原子操作层

### Task 3.1: 操作基类 (`operations/base.py`)

Create `CommandMode/operations/base.py` — 定义 `OperationStatus` 枚举和 `Operation` 抽象基类，包含 `execute(ctx)`, `validate(ctx)`, `rollback(ctx)` 方法。

### Task 3.2: 光谱仪操作 (`operations/spectrometer_ops.py`)

`AcquireSpectrum`, `SetExposure`, `SetWavelength` — 封装 LightFieldSpectrometer 的采集、曝光设置、波长设置。

### Task 3.3: 电机操作 (`operations/motor_ops.py`)

`MotorHome`, `MotorMoveTo` — 封装 ThorlabsRotator 的归零和移动。

### Task 3.4: 延迟线操作 (`operations/delay_ops.py`)

`DelayStageHome`, `DelayStageMoveTo` — 封装 DelayStage。

### Task 3.5: 辅助操作 (`operations/utility_ops.py`)

`SetPolarization` (设置 S/P 偏振组合), `Sleep`, `LogMessage`。

### Task 3.6: 功率/高度操作 (`operations/power_ops.py`, `operations/height_ops.py`)

`MeasurePower`, `PowerPolarizationScan`, `LockHeight`, `HeightScan`。

---

## Phase 4: 管道引擎

### Task 4.1: 实现 `core/pipeline.py`

实现 `Pipeline` 类：顺序执行 Operation 列表，支持 `on_step` 回调、`on_error` 策略（RetryStrategy/SkipStrategy/AbortStrategy）、`pause/resume/stop` 控制。实现 `PipelineResult` 数据类记录执行统计。

---

## Phase 5: 实验配方 + 配置 + 向后兼容

### Task 5.1: 配置文件

创建 `configs/defaults.yaml`, `configs/devices.yaml`, `configs/experiments/sfg_example.yaml`, `configs/experiments/srs_example.yaml`。

### Task 5.2: 配方文件

`recipes/sfg.py` — 所有 SFG 配方函数（`sfg_polarization_scan`, `sfg_time_scan`, `sfg_pol_angle_scan`, `sfg_pna_scan`）。

`recipes/srs.py` — 所有 SRS 配方函数（`srs_wavelength_scan`, `srs_pol_scan`, `srs_time_scan`）。

`recipes/raman.py` — `raman_spectrum`。

`recipes/diagnostics.py` — `height_scan`, `power_pol_scan`, `system_diagnostics`, `photodiode_test`, `photodiode_correlation`。

### Task 5.3: 向后兼容

在原 `API/` 文件中添加 deprecation import，使旧代码仍可运行但提示迁移。

---

## Phase 6: 文档与示例

### Task 6.1: 核心文档

`docs/README.md` (项目简介/快速开始), `docs/ARCHITECTURE.md` (架构说明), `docs/TUTORIAL.md` (教程), `docs/DEVICE_SETUP.md` (硬件指南), `docs/FAQ.md`。

### Task 6.2: 10 个示例脚本

`examples/01_connect_devices.py` 到 `examples/10_batch_experiment.py`，从单步操作到完整实验编排，渐进式学习。

### Task 6.3: API Schema (`api/schemas.py`)

定义 Pydantic 模型（`DeviceStatus`, `PipelineStatus`, `OperationRequest`）作为远期 GUI 接口契约。

---

## 执行说明

Phases 1-2 是基础层（本次 session 优先完成），Phases 3-6 可在后续 sessions 逐步实现。每阶段独立可测试，不破坏现有代码。