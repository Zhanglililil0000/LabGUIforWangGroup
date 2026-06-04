"""通用辅助原子操作。"""

import time
from operations.base import Operation


class SetPolarization(Operation):
    """设置 VIS 和 SFG 旋转电机的偏振组合。

    支持的偏振模式: "ssp", "ppp", "sps", "pss", "spp", "psp"

    Usage:
        SetPolarization("ssp", config)
    """

    POLARIZATION_MAP = {
        "ssp": (("vis_rotator", "vis_angle_s"), ("sfg_rotator", "sfg_angle_s")),
        "ppp": (("vis_rotator", "vis_angle_p"), ("sfg_rotator", "sfg_angle_p")),
        "sps": (("vis_rotator", "vis_angle_s"), ("sfg_rotator", "vis_angle_s")),
        "pss": (("vis_rotator", "vis_angle_p"), ("sfg_rotator", "sfg_angle_s")),
        "spp": (("vis_rotator", "vis_angle_s"), ("sfg_rotator", "vis_angle_p")),
        "psp": (("vis_rotator", "vis_angle_p"), ("sfg_rotator", "sfg_angle_s")),
    }

    def __init__(self, polarization: str, config=None):
        super().__init__(f"SetPolarization({polarization})")
        self.polarization = polarization.lower()
        self._config = config

    def execute(self, ctx) -> dict:
        mapping = self.POLARIZATION_MAP.get(self.polarization)
        if not mapping:
            raise ValueError(f"未知偏振模式: {self.polarization}")

        config = self._config or ctx.config
        angles = {}

        for device_name, angle_key in mapping:
            angle = config.get(f"polarization.{angle_key}")
            if angle is None:
                raise ValueError(f"配置中缺少: polarization.{angle_key}")
            motor = ctx.get_device(device_name)
            motor.move_to(angle)
            angles[device_name] = angle

        return {"polarization": self.polarization, "angles": angles}


class Sleep(Operation):
    """等待指定秒数。

    Usage:
        Sleep(5)  # 等待 5 秒
    """

    def __init__(self, seconds: float):
        super().__init__(f"Sleep({seconds}s)")
        self.seconds = seconds

    def execute(self, ctx) -> dict:
        ctx.logger.info(f"等待 {self.seconds}s ...")
        time.sleep(self.seconds)
        return {"seconds": self.seconds}


class LogMessage(Operation):
    """记录一条日志消息。

    Usage:
        LogMessage("开始偏振扫描", level="info")
    """

    def __init__(self, message: str, level: str = "info"):
        super().__init__(f"Log: {message[:30]}")
        self.message = message
        self.level = level

    def execute(self, ctx) -> dict:
        log_func = getattr(ctx.logger, self.level, ctx.logger.info)
        log_func(self.message)
        return {"message": self.message}
