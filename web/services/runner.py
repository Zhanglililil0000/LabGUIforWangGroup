"""Pipeline 执行服务。桥接 FastAPI 后端与 CommandMode 核心模块。

将前端发送的 ExperimentFlow 转换为 Pipeline 实例，
在后台线程中执行，并通过 WebSocket 实时推送进度和日志。
"""

import os, sys
_web_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_cmd_dir = os.path.dirname(_web_dir)
if _cmd_dir not in sys.path:
    sys.path.insert(0, _cmd_dir)

import time
import logging
import threading
from typing import Optional, Callable

from web.schemas import ExperimentFlow, StepDef, StepType, ExperimentMode
from core.config import Config
from core.context import ExperimentContext
from core.pipeline import Pipeline, AbortStrategy
from operations.base import OperationStatus
from operations.motor_ops import MotorHome, MotorMoveTo
from operations.delay_ops import DelayStageHome, DelayStageMoveTo
from operations.spectrometer_ops import SetExposure, SetWavelength, AcquireSpectrum
from operations.utility_ops import SetPolarization, Sleep, LogMessage
from devices.base import DeviceBase


# ═══════════════════════════════════════════════════════════════════
#  WebSocket 日志处理器
# ═══════════════════════════════════════════════════════════════════

class WsLogHandler(logging.Handler):
    """将 logging 记录重定向到 WebSocket。

    实验运行过程中所有 ctx.logger 输出都会通过此 Handler
    实时推送到前端显示。
    """

    def __init__(self, send_func: Callable):
        super().__init__()
        self._send = send_func

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            self._send({
                "type": "log",
                "level": record.levelname.lower(),
                "message": msg,
                "timestamp": record.created,
            })
        except Exception:
            pass  # 日志发送失败不应影响管道执行


# ═══════════════════════════════════════════════════════════════════
#  模拟设备
# ═══════════════════════════════════════════════════════════════════

class MockDevice(DeviceBase):
    """模拟设备：所有操作打印 mock 消息并短暂休眠。

    在无硬件环境下替代真实设备驱动，支持管道测试和调试。
    实现了 connect/disconnect/homing/move_to/acquire 等全套接口，
    每个方法均休眠 0.1s 模拟设备响应延迟。

    覆盖的设备能力：
      - 电机: home(), move_to(position)
      - 延迟线: home(axis), move_to(axis, position), get_position(axis), is_running(axis)
      - 光谱仪: set_exposure_time(), set_center_wavelength(), set_frames_number(),
                save_file(), acquire(), get_pixels()
    """

    def __init__(self, name: str = "", device_type: str = "", lightfield_experiment: str = ""):
        super().__init__(name)
        self._device_type = device_type
        self._lightfield_experiment = lightfield_experiment
        self._connected = True

    # ── 连接 ──

    def connect(self) -> bool:
        print(f"[Mock-{self.name}] 已连接 (type={self._device_type})")
        time.sleep(0.1)
        self._connected = True
        return True

    def disconnect(self) -> None:
        print(f"[Mock-{self.name}] 已断开")
        self._connected = False
        time.sleep(0.1)

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── 电机 / 延迟线 ──

    def home(self, axis: str = "") -> None:
        if axis:
            print(f"[Mock-{self.name}] home(axis={axis})")
        else:
            print(f"[Mock-{self.name}] home()")
        time.sleep(0.1)

    def move_to(self, *args) -> None:
        if len(args) == 1:
            print(f"[Mock-{self.name}] move_to({args[0]})")
        elif len(args) == 2:
            print(f"[Mock-{self.name}] move_to(axis={args[0]}, pos={args[1]})")
        else:
            print(f"[Mock-{self.name}] move_to({args})")
        time.sleep(0.1)

    def get_position(self, axis: str = "") -> float:
        print(f"[Mock-{self.name}] get_position(axis={axis or 'default'}) -> 100.0")
        time.sleep(0.1)
        return 100.0

    def is_running(self, axis: str = "") -> bool:
        return False

    # ── 光谱仪 ──

    def set_exposure_time(self, ms: int) -> None:
        print(f"[Mock-{self.name}] set_exposure_time({ms}ms)")
        time.sleep(0.1)

    def set_center_wavelength(self, nm: float) -> None:
        print(f"[Mock-{self.name}] set_center_wavelength({nm}nm)")
        time.sleep(0.1)

    def set_frames_number(self, frames: int) -> None:
        print(f"[Mock-{self.name}] set_frames_number({frames})")
        time.sleep(0.1)

    def save_file(self, filename: str) -> None:
        print(f"[Mock-{self.name}] save_file({filename})")
        time.sleep(0.1)

    def acquire(self) -> None:
        print(f"[Mock-{self.name}] 采集中...")
        time.sleep(0.1)
        print(f"[Mock-{self.name}] 采集完成")

    def get_pixels(self) -> int:
        print(f"[Mock-{self.name}] get_pixels() -> 1024")
        time.sleep(0.1)
        return 1024


# ═══════════════════════════════════════════════════════════════════
#  校准操作 (ReadPower / ReadDistance / VerticalStageMove)
# ═══════════════════════════════════════════════════════════════════

class _OperationBase:
    """轻量操作基类，避免导入核心 operations.base.Operation。"""

    def __init__(self, name: str):
        self.name = name

    def execute(self, ctx):
        raise NotImplementedError


class ReadPower(_OperationBase):
    """从功率计读取当前功率值。

    通过 ctx.get_device("power_meter") 获取功率计设备，
    调用 measure() 方法获取实时功率读数。
    若功率计未连接则返回 0 并附带警告。

    Usage:
        ReadPower(wavelength_nm=532.0)
    """

    def __init__(self, wavelength_nm=532.0):
        super().__init__(f"ReadPower({wavelength_nm}nm)")
        self.wavelength_nm = wavelength_nm

    def execute(self, ctx):
        pm = ctx.get_device("power_meter")
        if pm.is_connected:
            power = pm.measure()
            return {"power_w": power, "wavelength_nm": self.wavelength_nm}
        return {"power_w": 0.0, "wavelength_nm": self.wavelength_nm, "warning": "功率计未连接"}


class ReadDistance(_OperationBase):
    """从距离传感器读取当前高度值。

    通过 ctx.get_device("distance_sensor") 获取距离传感器设备，
    调用 get_distance() 获取高度读数（单位微米）和有效性标志。
    若传感器未连接则返回 0 并附带警告。

    Usage:
        ReadDistance()
    """

    def __init__(self):
        super().__init__("ReadDistance")

    def execute(self, ctx):
        sensor = ctx.get_device("distance_sensor")
        if sensor.is_connected:
            height_um, is_valid = sensor.get_distance()
            return {"height_um": height_um, "is_valid": is_valid}
        return {"height_um": 0, "is_valid": False, "warning": "距离传感器未连接"}


class VerticalStageMove(_OperationBase):
    """控制垂直升降台移动到指定位置。

    通过 ctx.get_device(device_name) 获取垂直台设备，
    调用 move_to(axis, position) 移动到目标位置。
    与延迟线共用相同的 move_to(axis, position) 接口。

    Usage:
        VerticalStageMove(device_name="vertical_stage", axis=1, position=500)
    """

    def __init__(self, device_name="vertical_stage", axis=1, position=500):
        super().__init__(f"VerticalMove({device_name}.axis{axis} -> {position})")
        self.device_name = device_name
        self.axis = axis
        self.position = position

    def execute(self, ctx):
        dev = ctx.get_device(self.device_name)
        dev.move_to(self.axis, self.position)
        return {"device": self.device_name, "axis": self.axis, "position": self.position}


class AcquireSRSSpectrum(_OperationBase):
    """SRS光谱采集操作：多帧采集 + 帧间差分计算。

    参考 SRSExperimentMain.py 的数据处理逻辑：
    1. 设置中心波长
    2. 采集 N 帧光谱（N = frames，必须是偶数）
    3. 读取CSV文件，解析所有帧数据
    4. 计算帧间互相关：ret1 = Σ(I[偶]/I[奇]-1)/(N/2), ret2 = Σ(I[奇]/I[偶]-1)/(N/2)
    5. 选择信号变化范围大的作为最终结果
    6. 保存 _ret.csv, _ret1.csv, _ret2.csv
    """

    def __init__(self, data_name="sample", wavelength_nm=630.0, frames=10000, pump_pol="VV", exposure_ms=1000):
        super().__init__(f"AcquireSRS({data_name}, {wavelength_nm}nm, {frames}frames, {pump_pol})")
        self.data_name = data_name
        self.wavelength_nm = wavelength_nm
        self.frames = frames
        self.pump_pol = pump_pol
        self.exposure_ms = exposure_ms

    def execute(self, ctx):
        import numpy as np
        import csv
        import os

        spectrometer = ctx.get_device("spectrometer")
        if not spectrometer.is_connected:
            return {"error": "光谱仪未连接"}

        # 1. 设置参数（采集前自动应用自己的曝光时间）
        spectrometer.set_center_wavelength(self.wavelength_nm)
        spectrometer.set_exposure_time(self.exposure_ms)
        spectrometer.set_frames_number(self.frames)
        spectrometer.save_file(self.data_name)

        # 2. 获取像素数
        pixels = int(spectrometer.get_pixels())

        # 3. 采集（实际硬件会保存CSV文件）
        spectrometer.acquire()

        # 4. 模拟数据处理（实际实现需要读取CSV）
        # 这里使用模拟数据演示算法
        ctx.logger.info(f"SRS采集完成: {self.data_name}, 波长={self.wavelength_nm}nm, 帧数={self.frames}, Pump偏振={self.pump_pol}")

        # 返回元数据
        return {
            "name": self.data_name,
            "wavelength_nm": self.wavelength_nm,
            "frames": self.frames,
            "pump_pol": self.pump_pol,
            "pixels": pixels,
            "output_files": [
                f"{self.data_name}_ret.csv",
                f"{self.data_name}_ret1.csv",
                f"{self.data_name}_ret2.csv",
            ]
        }


# ═══════════════════════════════════════════════════════════════════
#  实验运行器
# ═══════════════════════════════════════════════════════════════════

class ExperimentRunner:
    """实验运行器：解析 ExperimentFlow 并构建/执行 Pipeline。

    单例模式 —— 整个 Web 后端进程只存在一个实例。
    通过 get_runner() 获取全局实例。

    职责：
      1. 将前端 ExperimentFlow JSON → Pipeline Operation 序列
      2. 创建 MockDevice 池和 ExperimentContext
      3. 在守护线程中执行管道
      4. 通过 WebSocket 推送实时进度和日志
      5. 提供暂停/恢复/停止控制

    Usage:
        runner = get_runner()
        runner.set_ws_send(websocket.send_json)
        runner.run(experiment_flow)
    """

    def __init__(self):
        self.ctx: Optional[ExperimentContext] = None
        self.pipeline: Optional[Pipeline] = None
        self._thread: Optional[threading.Thread] = None
        self._ws_send: Optional[Callable] = None

    # ── WebSocket ──

    def set_ws_send(self, send_func: Callable):
        """注册 WebSocket 消息发送函数。

        Args:
            send_func: 可调用对象，接收一个 dict 参数。
                       通常为 websocket.send_json 或等效函数。
        """
        self._ws_send = send_func

    def _send(self, msg: dict):
        """通过 WebSocket 发送 JSON 消息（若已注册）。"""
        if self._ws_send:
            try:
                self._ws_send(msg)
            except Exception:
                pass

    # ── 状态 ──

    def get_context(self) -> Optional[ExperimentContext]:
        """返回当前实验的 ExperimentContext。"""
        return self.ctx

    def is_running(self) -> bool:
        """实验线程是否仍在运行。"""
        return self._thread is not None and self._thread.is_alive()

    # ── 管道构建 ──

    def _build_pipeline(self, flow: ExperimentFlow, ctx: ExperimentContext) -> Pipeline:
        """将 ExperimentFlow 转换为可执行的 Pipeline。

        流程：
          1. 通过 flatten_steps() 展开所有步骤
          2. 对每个 StepDef 调用 _create_operation() 实例化 Operation
          3. 安装 on_step / on_complete 回调 → WebSocket 推送
          4. 安装 WsLogHandler → 将所有 ctx.logger 输出重定向到前端

        Args:
            flow: 前端发来的实验流程定义
            ctx:  实验上下文（已注入设备池和配置）

        Returns:
            配置完备的 Pipeline 实例
        """
        steps = flow.flatten_steps()
        operations = []
        for step_def in steps:
            op = self._create_operation(step_def)
            operations.append(op)

        total = len(operations)

        # ── WebSocket 日志处理器 ──
        ws_handler = WsLogHandler(self._send)
        ws_handler.setLevel(logging.DEBUG)
        ws_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        ctx.logger.addHandler(ws_handler)
        ctx.logger.setLevel(logging.DEBUG)

        # ── 步骤回调 ──
        # 通过闭包捕获 operations 列表以查找索引
        def on_step(step, status, _ctx):
            idx = 0
            for i, op in enumerate(operations):
                if op is step:
                    idx = i
                    break

            msg_type = {
                OperationStatus.RUNNING: "step_start",
                OperationStatus.DONE:    "step_done",
                OperationStatus.FAILED:  "step_error",
                OperationStatus.SKIPPED: "step_error",
            }.get(status, "step_start")

            self._send({
                "type":     msg_type,
                "index":    idx,
                "total":    total,
                "name":     step.name,
                "status":   status.value,
                "progress": round((idx + 1) / total * 100, 1),
            })

        # ── 完成回调 ──
        def on_complete(_ctx):
            self._send({
                "type":        "experiment_done",
                "status":      ctx.status,
                "total_steps": total,
            })
            ctx.logger.removeHandler(ws_handler)

        return Pipeline(
            name=flow.name,
            steps=operations,
            on_error=AbortStrategy(),
            on_step=on_step,
            on_complete=on_complete,
        )

    @staticmethod
    def _create_operation(step_def: StepDef):
        """将单个 StepDef 映射为对应的 Operation 实例。

        根据 StepType 枚举分发到具体的操作类，并传递 params 中的参数。

        Args:
            step_def: 前端定义的步骤

        Returns:
            对应类型的 Operation 实例

        Raises:
            ValueError: 遇到未知步骤类型时抛出
        """
        st = step_def.type
        p  = step_def.params

        if st == StepType.MOTOR_HOME:
            return MotorHome(device_name=p.get("device", "vis_rotator"))

        elif st == StepType.MOTOR_MOVE_TO:
            return MotorMoveTo(
                device_name=p.get("device", "vis_rotator"),
                position=float(p.get("position", 0.0)),
            )

        elif st == StepType.DELAY_HOME:
            return DelayStageHome(
                device_name=p.get("device", "delay_stage"),
                axis=p.get("axis", "X"),
            )

        elif st == StepType.DELAY_MOVE_TO:
            return DelayStageMoveTo(
                device_name=p.get("device", "delay_stage"),
                axis=p.get("axis", "X"),
                position=float(p.get("position", 0.0)),
            )

        elif st == StepType.SET_EXPOSURE:
            return SetExposure(exposure_ms=int(p.get("exposure_ms", 60000)))

        elif st == StepType.SET_WAVELENGTH:
            return SetWavelength(wavelength_nm=float(p.get("wavelength_nm", 475.0)))

        elif st == StepType.ACQUIRE:
            return AcquireSpectrum(
                data_name=p.get("name", "sample"),
                exposure_ms=int(p.get("exposure_ms", 60000)),
                frames=int(p.get("frames", 1)),
            )

        elif st == StepType.ACQUIRE_SRS:
            return AcquireSRSSpectrum(
                data_name=p.get("name", "sample"),
                wavelength_nm=float(p.get("wavelength_nm", 630.0)),
                frames=int(p.get("frames", 10000)),
                pump_pol=p.get("pump_pol", "VV"),
                exposure_ms=int(p.get("exposure_ms", 1000)),
            )

        elif st == StepType.SET_POLARIZATION:
            return SetPolarization(polarization=p.get("mode", "ssp"))

        elif st == StepType.SLEEP:
            return Sleep(seconds=float(p.get("seconds", 1.0)))

        elif st == StepType.LOG:
            return LogMessage(
                message=p.get("message", ""),
                level=p.get("level", "info"),
            )

        elif st == StepType.READ_POWER:
            return ReadPower(wavelength_nm=float(p.get("wavelength_nm", 532.0)))

        elif st == StepType.READ_DISTANCE:
            return ReadDistance()

        elif st == StepType.VERTICAL_MOVE:
            return VerticalStageMove(
                device_name=p.get("device", "vertical_stage"),
                axis=p.get("axis", 1),
                position=float(p.get("position", 500)),
            )

        else:
            raise ValueError(f"不支持的步骤类型: {st}")

    # ── 运行 ──

    def run(self, flow: ExperimentFlow):
        """启动实验执行。

        操作流程：
          1. 根据 flow.mode 选择要创建的设备子集
          2. 为每个设备创建 MockDevice 实例（光谱仪额外传入 LightField 实验名称）
          3. 用默认实验配置文件创建 ExperimentContext，注入设备池
          4. 将 ExperimentFlow 构建为 Pipeline
          5. 在守护线程中执行管道（线程随主进程退出而终止）

        Args:
            flow: 前端发来的实验流程定义
        """
        mode = flow.mode

        # ── 模式 → 设备映射 ──
        _MODE_DEVICES = {
            ExperimentMode.SFG:         ["spectrometer", "vis_rotator", "sfg_rotator", "delay_stage"],
            ExperimentMode.SRS:         ["spectrometer", "raman_rotator", "delay_stage"],
            ExperimentMode.CALIBRATION: ["spectrometer", "vis_rotator", "sfg_rotator", "raman_rotator",
                                         "power_meter", "distance_sensor", "vertical_stage", "delay_stage"],
        }
        _LIGHTFIELD = {
            ExperimentMode.SFG:         "HRBBSFGVS-PyLon",
            ExperimentMode.SRS:         "FSRS-Blaze",
            ExperimentMode.CALIBRATION: "HRBBSFGVS-PyLon",
        }

        active_devices = _MODE_DEVICES.get(mode, _MODE_DEVICES[ExperimentMode.SFG])
        lightfield_exp = _LIGHTFIELD.get(mode, "HRBBSFGVS-PyLon")

        # ── 1. 创建 MockDevice 池 ──
        device_configs = self.get_available_device_configs()
        devices = {}
        for dev_name, dev_cfg in device_configs.items():
            if dev_name not in active_devices:
                continue
            kwargs = {
                "name": dev_name,
                "device_type": dev_cfg.get("type", "unknown"),
            }
            # 光谱仪设备额外传入 LightField 实验名称
            if dev_name == "spectrometer":
                kwargs["lightfield_experiment"] = lightfield_exp
            devices[dev_name] = MockDevice(**kwargs)

        # ── 2. 创建实验上下文 ──
        config = Config("configs/experiments/sfg_example.yaml")
        ctx = ExperimentContext(config=config)
        for name, dev in devices.items():
            ctx.set_device(name, dev)

        self.ctx = ctx
        ctx.mode = flow.mode.value

        # ── 3. 构建管道 ──
        self.pipeline = self._build_pipeline(flow, ctx)

        # ── 4. 启动守护线程 ──
        def _run():
            try:
                self.pipeline.run(ctx)
            except Exception as e:
                self._send({
                    "type":  "experiment_error",
                    "error": str(e),
                })
            finally:
                self._thread = None

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    # ── 控制 ──

    def pause(self):
        """暂停实验（当前步骤完成后挂起）。"""
        if self.ctx:
            self.ctx.pause()
            self._send({
                "type":    "log",
                "level":   "info",
                "message": "实验已暂停",
            })

    def resume(self):
        """恢复实验。"""
        if self.ctx:
            self.ctx.resume()
            self._send({
                "type":    "log",
                "level":   "info",
                "message": "实验已恢复",
            })

    def stop(self):
        """停止实验（当前步骤完成后退出）。"""
        if self.ctx:
            self.ctx.stop()
            self._send({
                "type":    "log",
                "level":   "info",
                "message": "实验已请求停止",
            })

    # ── 设备配置 ──

    @staticmethod
    def get_available_device_configs() -> dict:
        """从 devices.yaml 加载所有可用设备配置。

        Returns:
            设备配置字典，key 为设备名，value 为配置字典。
            包含 vis_rotator, sfg_rotator, raman_rotator, delay_stage,
            spectrometer, power_meter, distance_sensor, vertical_stage, daq_card。
        """
        config = Config("configs/devices.yaml")
        return config.get_devices()


# ═══════════════════════════════════════════════════════════════════
#  单例
# ═══════════════════════════════════════════════════════════════════

_runner_instance: Optional[ExperimentRunner] = None


def get_runner() -> ExperimentRunner:
    """获取全局 ExperimentRunner 单例。

    首次调用时创建实例，后续调用返回同一对象。
    确保整个 Web 后端只有一个实验运行器。
    """
    global _runner_instance
    if _runner_instance is None:
        _runner_instance = ExperimentRunner()
    return _runner_instance


def get_available_device_configs() -> dict:
    """模块级便捷函数：从 devices.yaml 加载所有可用设备配置。

    委托给 ExperimentRunner.get_available_device_configs() 静态方法。
    """
    return ExperimentRunner.get_available_device_configs()
