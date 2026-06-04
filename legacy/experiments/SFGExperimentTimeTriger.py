# Created in 2024.06.28 by Zhang Li

import json
import os
import numpy as np
import matplotlib.pyplot as plt
import csv
import bisect
import time
from API.LightFieldAPI import Experiment
from API.feinixsAPI import DelayStage
from API.ThorlabsAPI import Rotator

# Experiment Devices Parameters
VISRotatorSN = '55358884'
SFGRotatorSN = '55355234'
ExperimentName = 'HRBBSFGVS-PyLon'
FilePath = 'D:\\2026\\ZJK\\20260520_C18CN\\quartz\\Intensity_Scan2'
SampleName = 'Quartz'

# Devices Initialize
experiment = Experiment(ExperimentName)
experiment.set_file_path(FilePath)
# Rotator_VIS = Rotator("Cage", VISRotatorSN)
# Rotator_SFG = Rotator("Cage", SFGRotatorSN)
# Delay_Stage = DelayStage("com4")
# axis = "X"

# Other Parameter
VIS_RotatorAngle_S = 45.83
VIS_RotatorAngle_P = 90.83
VIS_RotatorAngle_PM = VIS_RotatorAngle_P + 22.5
VIS_RotatorAngle_MM = VIS_RotatorAngle_P - 22.5
SFG_RotatorAngle_S = 28.00 #35.60
SFG_RotatorAngle_P = 73.00 #80.60
DelayStagePos =102.00 #99.50
# DelayStagePos_P =74.6
# DelayStagePos_S =78.7
# horizontal height =1600
# sample height =1600

 
def SFGmain(ExposureTime,DataName):
    experiment.set_exposure_time(ExposureTime)
    experiment.save_file(DataName)
    experiment.get_frame()    

import time

if __name__ == "__main__":

    start_time = time.time()
    for i in range(600):

        now = int(time.time() - start_time)
        SFGmain(1000,'quartz_ssp1s' + str(now))
        time.sleep(1)
