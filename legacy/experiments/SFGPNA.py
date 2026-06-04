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
FilePath = 'D:\\2025\\zhangzekun\\20250925_PCP75mM\\PNA\\SPS_second_BG2'

# Devices Initialize
experiment = Experiment(ExperimentName)
experiment.set_file_path(FilePath)
SFG_Rotator_VIS = Rotator("Cage", VISRotatorSN)
SFG_Rotator_SFG = Rotator("Cage", SFGRotatorSN)
Delay_Stage = DelayStage("com4")
axis = "X"

# Other Parameter
VIS_RotatorAngle_S = 45.87
VIS_RotatorAngle_PNA = VIS_RotatorAngle_S + 22.5
VIS_RotatorAngle_P = VIS_RotatorAngle_S + 45
SFG_RotatorAngle_S = 24.42
SFG_RotatorAngle_P = SFG_RotatorAngle_S + 45
# DelayStagePos = 29.5
# DelayStagePos = 36
DelayStagePos = 227

def getSFG(DataName,ExposureTime):
    experiment.set_exposure_time(ExposureTime)
    experiment.save_file(DataName)
    experiment.get_frame()



if __name__ == "__main__":

   
    # SFG PNA
    SFG_Rotator_VIS.home()
    SFG_Rotator_VIS.moveto(VIS_RotatorAngle_PNA)
    SFG_Rotator_SFG.home()
    for Angle in np.arange(48.72, 113.72, 10.00):
        SFG_Rotator_SFG.moveto(Angle)
        getSFG("pcp60PNA"+str(format(Angle, ".4f")).replace(".", "_"), 1800000)
        
    # # BG 
    # Delay_Stage.moveto(axis,50)
    # getSFG(1200000,'1200sBG')

    # # SPS SFG
    # SFG_Rotator_SFG.moveto(SFG_RotatorAngle_S)
    # SFG_Rotator_VIS.moveto(VIS_RotatorAngle_P)
    # getSFG("TBA63SPS10s" , 10000)
    # getSFG("TBA63SPS600s" , 600000)

    # # PSS SFG
    # SFG_Rotator_VIS.home()
    # SFG_Rotator_SFG.home()
    # SFG_Rotator_SFG.moveto(SFG_RotatorAngle_P)
    # SFG_Rotator_VIS.moveto(VIS_RotatorAngle_S)
    # getSFG("TBA63PSS600s" , 600000)
    # SFG_Rotator_VIS.home()
    # SFG_Rotator_SFG.home()
    # SFG_Rotator_SFG.moveto(SFG_RotatorAngle_S)
    # SFG_Rotator_VIS.moveto(VIS_RotatorAngle_P)
    # getSFG("TBA63SPS10scheck" , 10000)


