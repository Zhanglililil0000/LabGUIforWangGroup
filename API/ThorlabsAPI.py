# Import the .NET class library
import clr

# Import python sys module
import sys

# Import os module
import os

import time

# Import System.IO for saving and opening files
from System.IO import *

from System.Threading import AutoResetEvent
from System import Decimal

# Write in file paths of dlls needed. 
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\ThorLabs.MotionControl.IntegratedStepperMotorsCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\ThorLabs.MotionControl.KCube.DCServoCLI.dll")

# Import functions from dlls. 
from Thorlabs.MotionControl.DeviceManagerCLI import *
from Thorlabs.MotionControl.GenericMotorCLI import *
from Thorlabs.MotionControl.IntegratedStepperMotorsCLI import *
from Thorlabs.MotionControl.KCube.DCServoCLI import *


class Rotator:
    def __init__(self, mount_type, serial_number) -> None:
        self.device = self.init_mount(mount_type, serial_number)

    def __del__(self):
        self.device.StopPolling()
        self.device.Disconnect()


    def init_mount(self, mount_type, serial_number):
        try:
            # Build device list.  
            DeviceManagerCLI.BuildDeviceList()

            # create new device.
            serial_no = str(serial_number)  # Replace this line with your device's serial number.
            if mount_type == "Cage":
                device = CageRotator.CreateCageRotator(serial_no)
            elif mount_type == "KCube":
                device = KCubeDCServo.CreateKCubeDCServo(serial_no)

            # Connect to device. 
            device.Connect(serial_no)

            # Ensure that the device settings have been initialized.
            if not device.IsSettingsInitialized():
                device.WaitForSettingsInitialized(10000)  # 10 second timeout.
                assert device.IsSettingsInitialized() is True

            # Start polling loop and enable device.
            device.StartPolling(250)  #250ms polling rate.
            time.sleep(25)
            device.EnableDevice()
            time.sleep(0.25)  # Wait for device to enable.

            # Get Device Information and display description.
            device_info = device.GetDeviceInfo()
            print(device_info.Description)

            # Load any configuration settings needed by the controller/stage.
            device.LoadMotorConfiguration(serial_no, DeviceConfiguration.DeviceSettingsUseOptionType.UseDeviceSettings)
            motor_config = device.LoadMotorConfiguration(serial_no)

        except Exception as e:
            print(e)

        return device
    
    def home(self):
        try:
            # Call device methods.
            print("Homing Device")
            self.device.Home(60000)  # 60 second timeout.
            print("Done")
        except Exception as e:
            print(e)
    
    def moveto(self, pos):
        try:
            print(f"Moving to {pos}")
            self.device.MoveTo(Decimal(pos), 60000)
            print("Done")
        except Exception as e:
            print(e)
