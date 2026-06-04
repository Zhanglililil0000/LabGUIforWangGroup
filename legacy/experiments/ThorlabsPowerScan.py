# for power-pol scanning

import json
import os
import numpy as np
import matplotlib.pyplot as plt
import csv
import bisect
from API.ThorlabsAPI import Rotator
from datetime import datetime
from ctypes import cdll,c_long, c_ulong, c_uint32,byref,create_string_buffer,c_bool,c_char_p,c_int,c_int16,c_double, sizeof, c_voidp
from API.ThorlabsTLPM import TLPM
import time



# Experiment Devices Parameters
VISRotatorSN = '55358884'
FilePath = 'D:\\2026\\zhangzekun\\20260401_PolPurity\\visPol'
DataName = 'quartz3'

# instrument initialize
# Rotator
Rotator_VIS = Rotator("Cage", VISRotatorSN)

# Power Meter
tlPM = TLPM()
deviceCount = c_uint32()
tlPM.findRsrc(byref(deviceCount))

print("Number of found devices: " + str(deviceCount.value))
print("")

resourceName = create_string_buffer(1024)

for i in range(0, deviceCount.value):
    tlPM.getRsrcName(c_int(i), resourceName)
    print("Resource name of device", i, ":", c_char_p(resourceName.raw).value)
print("")
tlPM.close()

tlPM = TLPM()
tlPM.open(resourceName, c_bool(True), c_bool(True))
message = create_string_buffer(1024)
tlPM.getCalibrationMsg(message)
print("Connected to device", i)
print("Last calibration date: ",c_char_p(message.raw).value)
print("")

time.sleep(2)


wavelength = c_double(532)
tlPM.setWavelength(wavelength)
tlPM.setPowerAutoRange(c_int16(0))  # Enable auto-range mode.
tlPM.setPowerUnit(c_int16(0))       # Set power unit to Watt.


if __name__ == "__main__":

    # Experiment Initialize
    Rotator_VIS.home()

    # Angle Range
    step = 1.0
    Angles = np.arange(20, 130, step)
    steps = len(Angles)
    count = 0
    SampleNum = 500
    SampleEnergy = []
    ResultEnergy = []

    while count < steps:

        Rotator_VIS.moveto(Angles[count])
        time.sleep(1)
        
        for sampleing in np.arange(0,SampleNum,1):
            power =  c_double()
            tlPM.measPower(byref(power))
            SampleEnergy.append(power.value)
        
        ResultEnergy.append(np.average(SampleEnergy))
        print("Energy is", np.average(SampleEnergy))
        SampleEnergy = []
        print("measured" + str(Angles[count]))
        time.sleep(1)
        count+=1

    print(ResultEnergy)

    with open(FilePath + "\\" + DataName+ ".csv", "w", newline="") as ret_file:
        writer = csv.writer(ret_file)
        writer.writerows(list(np.array([Angles, ResultEnergy]).T))

    tlPM.close()