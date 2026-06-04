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
ExperimentName = 'HRBBSFGVS-ProEM'
FilePath = 'D:\\2024\\zbj\\20240627'

# Devices Initialize
experiment = Experiment(ExperimentName)
experiment.set_file_path(FilePath)
SFG_Rotator_VIS = Rotator("Cage", VISRotatorSN)
SFG_Rotator_SFG = Rotator("Cage", SFGRotatorSN)
Delay_Stage = DelayStage("com4")
axis = "X"

# Other Parameter
VIS_RotatorAngle_S = 28.5
VIS_RotatorAngle_P= 73.5
SFG_RotatorAngle_S = 123
SFG_RotatorAngle_P = 168


def SFG_Time(DataName,DelayStagePos):
    experiment.save_file(DataName)

    Delay_Stage.moveto(axis, DelayStagePos)

    experiment.get_frame()



if __name__ == "__main__":

    # Experiment Initialize
    # SFG_Rotator_VIS.home()
    # SFG_Rotator_SFG.home()
    SFG_Rotator_VIS.moveto(VIS_RotatorAngle_S)
    SFG_Rotator_SFG.moveto(SFG_RotatorAngle_S)
    experiment.set_center_wavelength(475)
    Delay_Stage.home(axis)

    for position in np.arange(138, 158, 1.0):
        SFG_Time("quartz"+str(format(position, ".4f")).replace(".", "_")+"mm",
                 position)
        


