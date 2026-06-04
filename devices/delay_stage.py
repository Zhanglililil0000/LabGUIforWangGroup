"""光学延迟线设备驱动 (Feinixs 控制器)。

通信方式：串口 + ftcorecs DLL
"""

import time
import clr

clr.AddReference('resources/ftcorecs')
from ftcorecs import ftcore

from devices.base import DeviceBase, DeviceConnectionError, DeviceOperationError


class DelayStage(DeviceBase):
    """光学延迟线 (Feinixs SMC/AMC/NANO/MINI04 控制器)。

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
            ct = self.CONTROLLER_TYPES.get(
                self._controller_type, ftcore.CONTROLLER_TYPE_SMC
            )
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

    def _check(self, op: str):
        if self._handle is None:
            raise DeviceOperationError(self.name, op, "设备未连接")

    def _ok(self, ret, op: str):
        if ret != ftcore.FT_SUCESS:
            raise DeviceOperationError(self.name, op, f"ret={ret}")

    def home(self, axis: str = "X"):
        """归零指定轴。"""
        self._check("home")
        pos = self.get_position(axis)
        vel = self.get_homing_velocity(axis)
        ret = ftcore.ft_single_home(self._handle, axis)
        self._ok(ret, "home")
        print(f"[{self.name}] {axis} 轴正在归零...")

        time.sleep(abs(pos) / max(vel, 1))
        while self.is_running(axis):
            time.sleep(2)
        current_pos = self.get_position(axis)
        print(f"[{self.name}] {axis} 轴归零完成, 位置: {current_pos}")
        return current_pos

    def move_to(self, axis: str, position: float):
        """绝对移动到指定位置。"""
        self._check("move_to")
        cur = self.get_position(axis)
        vel = self.get_velocity(axis)
        ret = ftcore.ft_single_moveabs(self._handle, axis, position)
        self._ok(ret, "move_to")
        print(f"[{self.name}] {axis} 轴移动到 {position}...")

        time.sleep(abs(cur - position) / max(vel, 0.001))
        while self.is_running(axis):
            time.sleep(2)
        return self.get_position(axis)

    def move_by(self, axis: str, delta: float):
        """相对移动。"""
        self._check("move_by")
        vel = self.get_velocity(axis)
        ret = ftcore.ft_single_move(self._handle, axis, delta)
        self._ok(ret, "move_by")
        print(f"[{self.name}] {axis} 轴相对移动 {delta}...")

        time.sleep(abs(delta) / max(vel, 0.001))
        while self.is_running(axis):
            time.sleep(2)
        return self.get_position(axis)

    def get_position(self, axis: str = "X") -> float:
        self._check("get_position")
        ret, pos = ftcore.ft_single_getpos(self._handle, axis, 0)
        self._ok(ret, "get_position")
        return pos

    def is_running(self, axis: str = "X") -> bool:
        self._check("is_running")
        ret, running = ftcore.ft_single_isrunning(self._handle, axis, 0)
        self._ok(ret, "is_running")
        return running == ftcore.FT_TRUE

    def get_velocity(self, axis: str = "X") -> float:
        self._check("get_velocity")
        ret, vel = ftcore.ft_get_vel(self._handle, axis, 0)
        self._ok(ret, "get_velocity")
        return vel

    def get_homing_velocity(self, axis: str = "X") -> float:
        self._check("get_homing_velocity")
        ret, vel = ftcore.ft_get_homingvel(self._handle, axis, 0)
        self._ok(ret, "get_homing_velocity")
        return vel
