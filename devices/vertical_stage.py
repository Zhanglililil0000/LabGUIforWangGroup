"""垂直位移台设备驱动 (串口步进电机控制)。"""

import serial
import time

from devices.base import DeviceBase, DeviceConnectionError, DeviceOperationError


class VerticalStage(DeviceBase):
    """垂直电动位移台 (串口 RS-232 控制)。

    Usage:
        stage = VerticalStage(name="vertical_stage", port="COM9", baud=9600)
        stage.connect()
        stage.home(axis=1)
        stage.move(axis=1, distance=100)
    """

    def __init__(self, name: str = "vertical_stage",
                 port: str = "COM9", baud: int = 9600):
        super().__init__(name)
        self._port = port
        self._baud = baud
        self._ser = None

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

    def _check(self, op: str):
        if not self._ser:
            raise DeviceOperationError(self.name, op, "设备未连接")

    def _is_busy(self) -> bool:
        if not self._ser:
            return False
        self._ser.write(b"!:\r\n")
        rdata = self._ser.readline()
        return rdata == b"B\r\n"

    def _wait_ready(self):
        while self._is_busy():
            time.sleep(1)

    def home(self, axis: int = 1):
        """指定轴归零。"""
        self._check("home")
        self._ser.write(f"H:{axis}\r\n".encode())
        self._ser.readline()
        self._wait_ready()
        print(f"[{self.name}] 轴 {axis} 归零完成")

    def move(self, axis: int, distance: int):
        """相对移动。

        Args:
            axis: 轴号
            distance: 移动距离
        """
        self._check("move")
        self._ser.write(f"M:{axis}+P{distance * 2}\r\n".encode())
        self._ser.readline()
        time.sleep(1)
        self._ser.write(b"G:\r\n")
        self._ser.readline()
        self._wait_ready()
        print(f"[{self.name}] 轴 {axis} 移动 {distance} 完成")

    def move_to(self, axis: int, position: int):
        """绝对移动。

        Args:
            axis: 轴号
            position: 目标位置
        """
        self._check("move_to")
        self._ser.write(f"A:{axis}+P{position * 2}\r\n".encode())
        self._ser.readline()
        time.sleep(1)
        self._ser.write(b"G:\r\n")
        self._ser.readline()
        self._wait_ready()
        print(f"[{self.name}] 轴 {axis} 移动到 {position} 完成")

    def set_speed(self, axis: int, min_speed: int,
                  max_speed: int, accel_time: int):
        """设置速度参数。

        Args:
            axis: 轴号
            min_speed: 最小速度
            max_speed: 最大速度
            accel_time: 加速时间
        """
        self._check("set_speed")
        wdata = f"D:{axis}S{min_speed * 2}F{max_speed * 2}R{accel_time}\r\n"
        self._ser.write(wdata.encode())
        self._ser.readline()
        self._wait_ready()
        print(f"[{self.name}] 轴 {axis} 速度设置完成")
