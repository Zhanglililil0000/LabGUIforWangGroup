# Created in 2024.06.12 by Zhang Li

import json
import os
import numpy as np
import matplotlib.pyplot as plt
import csv
import bisect
from API.LightFieldAPI import Experiment
from API.feinixsAPI import DelayStage
from API.ThorlabsAPI import Rotator

# Experiment Devices Parameters
VISRotatorSN = '55358884'
SFGRotatorSN = '55355234'
ExperimentName = 'HRBBSFGVS-PyLon'
FilePath = 'D:\\2026\\zhangzekun\\20260401_PolPurity\\sfgPol\\gold_ppp4'


# Devices Initialize
experiment = Experiment(ExperimentName)
experiment.set_file_path(FilePath)
Rotator_VIS = Rotator("Cage", VISRotatorSN)
Rotator_SFG = Rotator("Cage", SFGRotatorSN)
Delay_Stage = DelayStage("com4")
axis = "X"

# Other Parameter
VIS_RotatorAngle_S = 45.58
VIS_RotatorAngle_P = 90.58
VIS_RotatorAngle_PM = VIS_RotatorAngle_P + 22.5
VIS_RotatorAngle_MM = VIS_RotatorAngle_P - 22.5
SFG_RotatorAngle_S = 29.01
SFG_RotatorAngle_P = 74.01
# DelayStagePos = 138.0
DelayStagePos =153.0025

def SFG_Time(DataName):
    experiment.save_file(DataName)
    experiment.get_frame()



if __name__ == "__main__":

    # Experiment Initialize
    Rotator_VIS.home()
    Rotator_SFG.home()
    # Rotator_SFG.moveto(SFG_RotatorAngle_P)
    Rotator_VIS.moveto(VIS_RotatorAngle_P)


    for Angle in np.arange(10, 110, 1.0):
        Rotator_SFG.moveto(Angle)
        #Rotator_VIS.moveto(Angle)
        # SFG_Time("DMSO"+str(format(Angle, ".4f")).replace(".", "_"))
        SFG_Time("goldNPP"+str(format(Angle, ".4f")).replace(".", "_"))


