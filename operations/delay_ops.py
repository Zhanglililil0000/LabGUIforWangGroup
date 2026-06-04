"""光学延迟线操作。"""

from operations.base import Operation


class DelayStageHome(Operation):
    """延迟线归零。

    Usage:
        DelayStageHome(device_name="delay_stage", axis="X")
    """

    def __init__(self, device_name: str = "delay_stage", axis: str = "X"):
        super().__init__(f"DelayHome({device_name}.{axis})")
        self.device_name = device_name
        self.axis = axis

    def execute(self, ctx) -> dict:
        stage = ctx.get_device(self.device_name)
        stage.home(self.axis)
        return {"device": self.device_name, "axis": self.axis, "action": "home"}


class DelayStageMoveTo(Operation):
    """延迟线移动到指定位置。

    Usage:
        DelayStageMoveTo(device_name="delay_stage", axis="X", position=150.0)
    """

    def __init__(self, device_name: str = "delay_stage",
                 axis: str = "X", position: float = 0.0):
        super().__init__(f"DelayMoveTo({device_name}.{axis} -> {position})")
        self.device_name = device_name
        self.axis = axis
        self.position = position

    def execute(self, ctx) -> dict:
        stage = ctx.get_device(self.device_name)
        stage.move_to(self.axis, self.position)
        return {
            "device": self.device_name,
            "axis": self.axis,
            "action": "move_to",
            "position": self.position,
        }
