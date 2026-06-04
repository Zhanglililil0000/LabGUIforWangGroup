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
FilePath = 'D:\\2026\\JJH\\20260503methanol\\timescan2'


# Devices Initialize``
experiment = Experiment(ExperimentName)
experiment.set_file_path(FilePath)
# SFG_Rotator_VIS = Rotator("Cage", VISRotatorSN)
# SFG_Rotator_SFG = Rotator("Cage", SFGRotatorSN)
Delay_Stage = DelayStage("com4")                          
axis = "X"

# # Other Parameter
VIS_RotatorAngle_S = 45.58
VIS_RotatorAngle_P = 90.58
VIS_RotatorAngle_PM = VIS_RotatorAngle_P + 22.5
VIS_RotatorAngle_MM = VIS_RotatorAngle_P - 22.5
SFG_RotatorAngle_S = 29.21 #35.60
SFG_RotatorAngle_P = 74.21 #80.60


def SFG_Time(DataName,DelayStagePos):
    experiment.save_file(DataName)

    Delay_Stage.moveto(axis, DelayStagePos)

    experiment.get_frame()



if __name__ == "__main__":

    # # Experiment Initialize
    # SFG_Rotator_VIS.home()
    # SFG_Rotator_SFG.home()
    # SFG_Rotator_VIS.moveto(VIS_RotatorAngle_S)
    # SFG_Rotator_SFG.moveto(SFG_RotatorAngle_S)


    # for i in range(1, 5):
    #     os.mkdir('D:\\2026\\ZhangLi\\20260205WRGroup\\20260206stabletest\\Scan' + str(i))
    #     experiment.set_file_path('D:\\2026\\ZhangLi\\20260205WRGroup\\20260206stabletest\\Scan' + str(i))
    #     for position in np.arange(120, 156, 0.5):
    #         SFG_Time("quartz"+str(format(position, ".4f")).replace(".", "_")+"mm", position)

    # experiment.close()
    
    for position in np.arange(135,161, 0.5):
            SFG_Time("quartz"+str(format(position, ".4f")).replace(".", "_")+"mm", position)

    experiment.close()    


