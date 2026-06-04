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
ExperimentName = 'HRBBSFGVS-PyLon'
FilePath = 'D:\\2026\\ZGC\\20260527'
SampleName = 'methanol'

# Devices Initialize
experiment = Experiment(ExperimentName)
experiment.set_file_path(FilePath)
# Rotator_VIS = Rotator("Cage", VISRotatorSN)
# Rotator_SFG = Rotator("Cage", SFGRotatorSN)
Delay_Stage = DelayStage("com4")
axis = "X"

# Other Parameter
VIS_RotatorAngle_S = 45.58
VIS_RotatorAngle_P = 90.58
VIS_RotatorAngle_PM = VIS_RotatorAngle_P + 22.5
VIS_RotatorAngle_MM = VIS_RotatorAngle_P - 22.5
SFG_RotatorAngle_S = 29.21
SFG_RotatorAngle_P = 74.21
DelayStagePos =222.5
# DelayStagePos_P =223
# DelayStagePos_S =227
# horizontal height =400
# sample height =1040

 
def SFGmain(ExposureTime,DataName):
    experiment.set_exposure_time(ExposureTime)
    experiment.save_file(DataName)
    experiment.get_frame()    

import time

if __name__ == "__main__":

    # SSP
    # Rotator_VIS.home()
    # Rotator_SFG.home()
    # Rotator_VIS.moveto(VIS_RotatorAngle_S)
    # Rotator_SFG.moveto(SFG_RotatorAngle_S)
    # SFGmain(100000,'6MNaBr_ssp_100s_1')
    # SFGmain(3600000,'6MNaBr_ssp_3600s')
    # SFGmain(100000,'6MNaBr_ssp_100s_2')

    # PPP
    # Rotator_VIS.moveto(VIS_RotatorAngle_P)
    # Rotator_SFG.moveto(SFG_RotatorAngle_P)
    SFGmain(60000,'methanol_ppp_60s_4')
    SFGmain(2400000,'methanol_ppp_2400s')
    # Rotator_VIS.moveto(VIS_RotatorAngle_S)
    # Rotator_SFG.moveto(SFG_RotatorAngle_S)
    SFGmain(2400000,'methanol_ppp_2400s_1')
    SFGmain(2400000,'methanol_ppp_2400s_2')
    SFGmain(60000,'methanol_ppp_60s_5')

    # BG
    Delay_Stage.moveto(axis,100) 
    SFGmain(2400000,'methanol_ppp_2400s_bg')
    SFGmain(2400000,'methanol_ppp_2400s_bg_1')
    SFGmain(2400000,'methanol_ppp_2400s_bg_2')
    Delay_Stage.moveto(axis,222) 
    SFGmain(60000,'methanol_ppp_60s_6')

    # # PSP
    # Rotator_VIS.moveto(VIS_RotatorAngle_S)
    # Rotator_SFG.moveto(SFG_RotatorAngle_P)
    # SFGmain(60000,'sigma_d_2_psp60s_pspStart')
    # SFGmain(7200000,'sigma_d_2_psp_7200s')
    # Rotator_VIS.moveto(VIS_RotatorAngle_S)
    # Rotator_SFG.moveto(SFG_RotatorAngle_S)
    # SFGmain(60000,'sigma_d_2_ssp60s_pspEND')

    # # SPP
    # Rotator_VIS.moveto(VIS_RotatorAngle_P)
    # Rotator_SFG.moveto(SFG_RotatorAngle_S)
    # SFGmain(60000,'sigma_d_2_spp60s_Start')
    # SFGmain(7200000,'sigma_d_2_SPP_7200s')
    # Rotator_VIS.moveto(VIS_RotatorAngle_S)
    # Rotator_SFG.moveto(SFG_RotatorAngle_S)
    # SFGmain(60000,'sigma_d_2_ssp60s_SPPEND')

    # # PSP
    # Rotator_VIS.moveto(VIS_RotatorAngle_S)
    # Rotator_SFG.moveto(SFG_RotatorAngle_P)
    # SFGmain(60000,'sigma_d_2_psp60s_psp2Start')
    # SFGmain(7200000,'sigma_d_2_psp_7200s2')
    # Rotator_VIS.moveto(VIS_RotatorAngle_S)
    # Rotator_SFG.moveto(SFG_RotatorAngle_S)
    # SFGmain(60000,'sigma_d_2_ssp60s_psp2END')

    # # SPP
    # Rotator_VIS.moveto(VIS_RotatorAngle_P)
    # Rotator_SFG.moveto(SFG_RotatorAngle_S)
    # SFGmain(60000,'sigma_d_2_spp60s_Start2')
    # SFGmain(7200000,'sigma_d_2_SPP_7200s2')
    # Rotator_VIS.moveto(VIS_RotatorAngle_S)
    # Rotator_SFG.moveto(SFG_RotatorAngle_S)
    # SFGmain(60000,'sigma_d_2_ssp60s_SPP2END')
 
    # # # BG
    # Delay_Stage.moveto(axis,299) 
    # Rotator_VIS.moveto(VIS_RotatorAngle_S)
    # Rotator_SFG.moveto(SFG_RotatorAngle_P)
    # SFGmain(7200000,'sigma_d_2_PSP_7200s_BG')
    # Rotator_VIS.moveto(VIS_RotatorAngle_P)
    # Rotator_SFG.moveto(SFG_RotatorAngle_P)
    # SFGmain(1800000,'PPP_1800s_BG')
    # # Rotator_VIS.moveto(VIS_RotatorAngle_P)
    # # Rotator_SFG.moveto(SFG_RotatorAngle_S)
    # # SFGmain(7200000,'SPP_7200s_BG')

    # # Delay_Stage.moveto(axis,221.5700)
    # # Rotator_VIS.moveto(VIS_RotatorAngle_S)
    # # Rotator_SFG.moveto(SFG_RotatorAngle_S)
    # # SFGmain(60000,'tci_d_ssp60s_BG2hEND')

    

    

    
    # # SPS
    # Rotator_VIS.home()
    # Rotator_SFG.home()
    # Rotator_VIS.moveto(VIS_RotatorAngle_P)
    # Rotator_SFG.moveto(SFG_RotatorAngle_S)
    # SFGmain(120000,'tci_L_sps120s_spsStart')
    # SFGmain(1800000,'tci_L_SPS_1800s')
    # SFGmain(120000,'tci_L_SPS120s_spsEnd')

    # # PSS
    # Rotator_VIS.moveto(VIS_RotatorAngle_S)
    # Rotator_SFG.moveto(SFG_RotatorAngle_P)
    # SFGmain(1800000,'tci_L_PSS_1800s')
    # Rotator_VIS.moveto(VIS_RotatorAngle_P)
    # Rotator_SFG.moveto(SFG_RotatorAngle_S)
    # SFGmain(120000,'tci_L_sps120s_pssEnd')

    # # PPS
    # Rotator_VIS.moveto(VIS_RotatorAngle_P)
    # Rotator_SFG.moveto(SFG_RotatorAngle_P)
    # SFGmain(120000,'tci_L_pps120s_ppsStart')
    # SFGmain(7200000,'tci_L_pps7200s')
    # Rotator_VIS.moveto(VIS_RotatorAngle_P)
    # Rotator_SFG.moveto(SFG_RotatorAngle_S)
    # SFGmain(120000,'tci_L_sps120s_ppsEnd')

    # # BG
    # Delay_Stage.moveto(axis,299)
    # Rotator_VIS.moveto(VIS_RotatorAngle_P)
    # Rotator_SFG.moveto(SFG_RotatorAngle_P)
    # SFGmain(7200000,'tci_L_pps7200s_bg')
    # Rotator_VIS.moveto(VIS_RotatorAngle_P)
    # Rotator_SFG.moveto(SFG_RotatorAngle_S)
    # SFGmain(1800000,'tci_L_SPS_1800s_bg')
    # Delay_Stage.moveto(axis,226)
    # Rotator_VIS.moveto(VIS_RotatorAngle_P)
    # Rotator_SFG.moveto(SFG_RotatorAngle_S)
    # SFGmain(60000,'tci_L_sps120s_END')

    




    

    



    
