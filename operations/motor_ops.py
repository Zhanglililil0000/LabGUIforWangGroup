"""电机操作。封装 ThorlabsRotator 的原子操作。"""

from operations.base import Operation, OperationStatus


class MotorHome(Operation):
    """电机归零操作。

    Usage:
        MotorHome("vis_rotator")
    """

    def __init__(self, device_name: str):
        super().__init__(f"MotorHome({device_name})")
        self.device_name = device_name

    def execute(self, ctx) -> dict:
        motor = ctx.get_device(self.device_name)
        motor.home()
        return {"device": self.device_name, "action": "home"}


class MotorMoveTo(Operation):
    """电机移动到指定角度。

    Usage:
        MotorMoveTo("vis_rotator", 45.58)
    """

    def __init__(self, device_name: str, position: float):
        super().__init__(f"MotorMoveTo({device_name} -> {position}°)")
        self.device_name = device_name
        self.position = position

    def execute(self, ctx) -> dict:
        motor = ctx.get_device(self.device_name)
        motor.move_to(self.position)
        return {
            "device": self.device_name,
            "action": "move_to",
            "position": self.position,
        }
