"""Pydantic 数据模型, 定义所有 API 请求/响应结构。"""

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────
# 实验模式
# ─────────────────────────────────────────────────────────────

class ExperimentMode(str, Enum):
    SFG = "sfg"
    SRS = "srs"
    CALIBRATION = "calibration"

    @property
    def label(self) -> str:
        return {
            "sfg": "SFG 实验",
            "srs": "SRS 实验",
            "calibration": "系统调试",
        }.get(self.value, self.value)

    @property
    def description(self) -> str:
        return {
            "sfg": "和频振动光谱 — VIS/SFG 偏振 + 延迟线 + 光谱仪",
            "srs": "受激拉曼散射 — Pump(532nm)偏振扫描 + 多帧差分计算",
            "calibration": "偏振标定、功率扫描、高度扫描、样品对焦",
        }.get(self.value, "")


# ─────────────────────────────────────────────────────────────
# 步骤
# ─────────────────────────────────────────────────────────────

class StepType(str, Enum):
    MOTOR_HOME = "MotorHome"
    MOTOR_MOVE_TO = "MotorMoveTo"
    DELAY_HOME = "DelayStageHome"
    DELAY_MOVE_TO = "DelayStageMoveTo"
    SET_EXPOSURE = "SetExposure"
    SET_WAVELENGTH = "SetWavelength"
    SET_GRATING = "SetGrating"
    ACQUIRE = "AcquireSpectrum"
    ACQUIRE_SRS = "AcquireSRSSpectrum"
    SET_POLARIZATION = "SetPolarization"
    SLEEP = "Sleep"
    LOG = "LogMessage"
    READ_POWER = "ReadPower"
    READ_DISTANCE = "ReadDistance"
    VERTICAL_MOVE = "VerticalStageMove"


class StepDef(BaseModel):
    type: StepType
    params: dict[str, Any] = Field(default_factory=dict)

    _PARAM_SPECS = {
        StepType.MOTOR_HOME:       {"device": "vis_rotator"},
        StepType.MOTOR_MOVE_TO:    {"device": "vis_rotator", "position": 0.0},
        StepType.DELAY_HOME:       {"device": "delay_stage", "axis": "X"},
        StepType.DELAY_MOVE_TO:    {"device": "delay_stage", "axis": "X", "position": 150.0},
        StepType.SET_EXPOSURE:     {"exposure_ms": 60000},
        StepType.SET_WAVELENGTH:   {"wavelength_nm": 475},
        StepType.SET_GRATING:      {"grating": "300"},
        StepType.ACQUIRE:          {"name": "sample", "exposure_ms": 60000, "frames": 1, "compute_diff": False},
        StepType.ACQUIRE_SRS:      {"name": "sample", "wavelength_nm": 630, "frames": 10000, "pump_pol": "VV", "exposure_ms": 1000},
        StepType.SET_POLARIZATION: {"mode": "ssp"},
        StepType.SLEEP:            {"seconds": 1.0},
        StepType.LOG:              {"message": "步骤开始", "level": "info"},
        StepType.READ_POWER:       {"wavelength_nm": 532.0},
        StepType.READ_DISTANCE:    {},
        StepType.VERTICAL_MOVE:   {"device": "vertical_stage", "axis": 1, "position": 500},
    }

    @staticmethod
    def default_params(step_type: str) -> dict:
        try:
            return dict(StepDef._PARAM_SPECS.get(StepType(step_type), {}))
        except ValueError:
            return {}


# ─────────────────────────────────────────────────────────────
# 组
# ─────────────────────────────────────────────────────────────

class GroupOptions(BaseModel):
    capture_background: bool = False
    stability_check: bool = False
    background_position: float = 100.0
    signal_position: float = 222.5


class GroupDef(BaseModel):
    name: str = ""
    options: GroupOptions = Field(default_factory=GroupOptions)
    steps: list[StepDef] = Field(default_factory=list)

    class Config:
        extra = "allow"

    @staticmethod
    def _normalize(raw: dict) -> dict:
        flat_opts = {"capture_background", "stability_check", "background_position", "signal_position"}
        if any(k in raw for k in flat_opts):
            opts = raw.get("options", {})
            d = dict(raw)
            for k in flat_opts:
                if k in d:
                    opts[k] = d.pop(k)
            d["options"] = opts
            return d
        return raw

    def __init__(self, **data):
        data = self._normalize(data)
        options_data = data.get("options", {})
        if isinstance(options_data, dict):
            data["options"] = GroupOptions(
                capture_background=bool(options_data.get("capture_background", False)),
                stability_check=bool(options_data.get("stability_check", False)),
                background_position=float(options_data.get("background_position", 100.0) or 0),
                signal_position=float(options_data.get("signal_position", 222.5) or 0),
            )
        super().__init__(**data)


# ─────────────────────────────────────────────────────────────
# 实验流程
# ─────────────────────────────────────────────────────────────

class ExperimentFlow(BaseModel):
    name: str = "Unnamed"
    sample: str = "sample"
    base_path: str = "D:\\SFGData"
    mode: ExperimentMode = ExperimentMode.SFG
    groups: list[GroupDef] = Field(default_factory=list)

    def flatten_steps(self) -> list[StepDef]:
        flat = []
        for group in self.groups:
            flat.extend(self._expand_group(group))
        return flat

    def _expand_group(self, group: GroupDef) -> list[StepDef]:
        steps = list(group.steps)
        if not group.options.capture_background and not group.options.stability_check:
            return steps

        result = []
        for step in steps:
            if step.type == StepType.ACQUIRE:
                main_name = step.params.get("name", "sample")
                main_exp = step.params.get("exposure_ms", 60000)
                main_frames = step.params.get("frames", 1)

                if group.options.stability_check:
                    result.append(StepDef(
                        type=StepType.ACQUIRE,
                        params={"name": f"{main_name}_check_before", "exposure_ms": 1000, "frames": 1}
                    ))
                result.append(step)
                if group.options.stability_check:
                    result.append(StepDef(
                        type=StepType.ACQUIRE,
                        params={"name": f"{main_name}_check_after", "exposure_ms": 1000, "frames": 1}
                    ))
                if group.options.capture_background:
                    bg_pos = group.options.background_position
                    sig_pos = group.options.signal_position
                    result.append(StepDef(type=StepType.DELAY_MOVE_TO, params={"device": "delay_stage", "axis": "X", "position": bg_pos}))
                    result.append(StepDef(type=StepType.ACQUIRE, params={"name": f"{main_name}_bg", "exposure_ms": main_exp, "frames": main_frames}))
                    result.append(StepDef(type=StepType.DELAY_MOVE_TO, params={"device": "delay_stage", "axis": "X", "position": sig_pos}))
            else:
                result.append(step)
        return result


# ─────────────────────────────────────────────────────────────
# 设备
# ─────────────────────────────────────────────────────────────

class DeviceBrief(BaseModel):
    name: str
    type: str
    connected: bool
    position: Optional[float] = None
    details: dict[str, Any] = Field(default_factory=dict)
    # details 示例: {"serial": "55358884", "driver": "Cage", "port": "COM4", "baud": 19200}


# ─────────────────────────────────────────────────────────────
# 模式信息
# ─────────────────────────────────────────────────────────────

class ModeInfo(BaseModel):
    id: str
    name: str
    description: str
    lightfield_experiment: str
    devices: list[str]
    step_types: list[str]


class ModeList(BaseModel):
    modes: dict[str, ModeInfo]


# ─────────────────────────────────────────────────────────────
# 实验控制
# ─────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    flow: ExperimentFlow


class ExperimentStatus(BaseModel):
    running: bool
    pipeline_name: str = ""
    current_step: int = 0
    total_steps: int = 0
    status: str = "idle"
    mode: str = ""


# ─────────────────────────────────────────────────────────────
# 模板
# ─────────────────────────────────────────────────────────────

class TemplateMeta(BaseModel):
    name: str
    filename: str
    mode: str = ""
    group_count: int = 0
    step_count: int = 0


class TemplateSaveRequest(BaseModel):
    name: str
    mode: ExperimentMode = ExperimentMode.SFG
    flow: ExperimentFlow



