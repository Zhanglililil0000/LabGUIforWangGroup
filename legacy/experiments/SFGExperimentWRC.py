# Created in 2024.06.28 by Zhang Li

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
FilePath = 'D:\\2024\\zhangli\\20240814\\1M_2-MIM_D2O'

# Devices Initialize
experiment = Experiment(ExperimentName)
experiment.set_file_path(FilePath)
SFG_Rotator_VIS = Rotator("Cage", VISRotatorSN)
SFG_Rotator_SFG = Rotator("Cage", SFGRotatorSN)

# Other Parameter
VIS_RotatorAngle_S = 36.65
VIS_RotatorAngle_P = 81.65
SFG_RotatorAngle_S = 30.97
SFG_RotatorAngle_P = 75.97


def SFGmain(ExposureTime,DataName):
    experiment.set_exposure_time(ExposureTime)
    experiment.save_file(DataName)
    experiment.get_frame()



if __name__ == "__main__":

    # Experiment Initialize
    SFG_Rotator_VIS.home()
    SFG_Rotator_SFG.home()
    SFG_Rotator_VIS.moveto(VIS_RotatorAngle_S)
    SFG_Rotator_SFG.moveto(SFG_RotatorAngle_S)
        
    SFGmain(1200000,'ssp1200s')

    SFG_Rotator_SFG.home()
    SFG_Rotator_VIS.home()
    SFG_Rotator_VIS.moveto(VIS_RotatorAngle_P)
    SFG_Rotator_SFG.moveto(SFG_RotatorAngle_P)

    SFGmain(1200000,'ppp1200s')