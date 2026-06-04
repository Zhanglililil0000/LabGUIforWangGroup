# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import serial
import time
import sys

class VerticalStage:
    def __init__(self, com, baud=9600) -> None:
        self.ser = serial.Serial(com)
        self.ser.baudrate = baud
        self.ser.BYTESIZES=serial.EIGHTBITS
        self.ser.PARITIES=serial.PARITY_NONE
        self.ser.STOPBITS=serial.STOPBITS_ONE
        self.ser.timeout=5
        self.ser.rtscts=True

    def __del__(self):
        self.close()
    
    def ifbusy(self):
        if not self.ser:
            return
        wdata = "!:\r\n"
        self.ser.write(wdata.encode())
        rdata = self.ser.readline()
        # print(rdata)
        return rdata == b"B\r\n"
    
    def home(self, axis):
        if not self.ser:
            return
        wdata = "H:" + str(axis) + "\r\n"
        print(wdata)
        self.ser.write(wdata.encode())
        rdata = self.ser.readline()
        print(rdata)
        while self.ifbusy():
            time.sleep(1)

    def move_pulse(self, axis, distance):
        if not self.ser:
            return
        wdata = "M:" + str(axis) + "+P" + str(distance) + "\r\n"
        print(wdata)
        self.ser.write(wdata.encode())
        rdata = self.ser.readline()
        print(rdata)
        time.sleep(1)
        wdata = 'G:\r\n'
        print(wdata)
        self.ser.write(wdata.encode())
        rdata = self.ser.readline()
        print(rdata)
        while self.ifbusy():
            time.sleep(1)
        
    def moveto_pulse(self, axis, position):
        if not self.ser:
            return
        wdata = "A:" + str(axis) + "+P" + str(position) + "\r\n"
        print(wdata)
        self.ser.write(wdata.encode())
        rdata = self.ser.readline()
        print(rdata)
        time.sleep(1)
        wdata = 'G:\r\n'
        print(wdata)
        self.ser.write(wdata.encode())
        rdata = self.ser.readline()
        print(rdata)
        while self.ifbusy():
            print("test")
            time.sleep(1)

    def set_speed_pulse(self, axis, minimum_speed, maximum_speed, acceleration_time):
        if not self.ser:
            return
        wdata = "D:" + str(axis) + "S" + str(minimum_speed) + "F" + str(maximum_speed) + "R" + str(acceleration_time) + "\r\n"
        print(wdata)
        self.ser.write(wdata.encode())
        rdata = self.ser.readline()
        print(rdata)
        while self.ifbusy():
            time.sleep(1)

    def move(self, axis, distance):
        if not self.ser:
            return
        wdata = "M:" + str(axis) + "+P" + str(distance * 2) + "\r\n"
        print(wdata)
        self.ser.write(wdata.encode())
        rdata = self.ser.readline()
        print(rdata)
        time.sleep(1)
        wdata = 'G:\r\n'
        print(wdata)
        self.ser.write(wdata.encode())
        rdata = self.ser.readline()
        print(rdata)
        while self.ifbusy():
            time.sleep(1)
        
    def moveto(self, axis, position):
        if not self.ser:
            return
        wdata = "A:" + str(axis) + "+P" + str(position * 2) + "\r\n"
        print(wdata)
        self.ser.write(wdata.encode())
        rdata = self.ser.readline()
        print(rdata)
        time.sleep(1)
        wdata = 'G:\r\n'
        print(wdata)
        self.ser.write(wdata.encode())
        rdata = self.ser.readline()
        print(rdata)
        while self.ifbusy():
            time.sleep(1)

    def set_speed(self, axis, minimum_speed, maximum_speed, acceleration_time):
        if not self.ser:
            return
        wdata = "D:" + str(axis) + "S" + str(minimum_speed * 2) + "F" + str(maximum_speed * 2) + "R" + str(acceleration_time) + "\r\n"
        print(wdata)
        self.ser.write(wdata.encode())
        rdata = self.ser.readline()
        print(rdata)
        while self.ifbusy():
            time.sleep(1)

    def get_status(self):
        if self.ser == None:
            return
        wdata = "Q:" + "\r\n" 
        print(wdata)
        self.ser.write(wdata.encode())
        rdata = self.ser.readline()
        print(rdata)
        while self.ifbusy():
            time.sleep(1)

    def close(self):
        self.ser.close()


# if __name__ == "__main__":
#     verticalStage = VerticalStage("COM4", 9600)
#     verticalStage.home(1)
#     verticalStage.get_status()
#     verticalStage.move_pulse(1, 1000)
#     verticalStage.get_status()
#     verticalStage.set_speed_pulse(1, 500, 5000, 200)
#     verticalStage.get_status()
#     verticalStage.moveto_pulse(1, 500)
#     verticalStage.get_status()