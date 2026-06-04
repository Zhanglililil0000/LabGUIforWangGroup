# Update in 2024.06.09 by Zhang Li

import json
import os
import numpy as np 
from API.LightFieldAPI import Experiment
from API.ThorlabsAPI import Rotator

# Experiment Devices Parameters
RotatorSN = '55169544'
ExperimentName = 'Raman-ProEM'
FilePath = 'D:\\2024\\zhangli\\20240605Raman\\benzene'

# Devices Initialize
experiment = Experiment(ExperimentName)
experiment.set_file_path(FilePath)
Raman_Rotator = Rotator("Cage", RotatorSN)

# Other Parameter
RotatorAngle1 = 40.5 # vertical polarization
RotatorAngle2 = 85.5 # horizontal polarization

def Raman(RotatorAngle,CenterWavelength,ExposureTime,FileName):
    Raman_Rotator.moveto(RotatorAngle)
    experiment.save_file(FileName)
    experiment.set_exposure_time(ExposureTime * 1000) # Set exposure time
    experiment.set_center_wavelength(CenterWavelength) # Move to set wavelength
    experiment.get_frame() # get the spectra


if __name__ == "__main__":

    # wavelength scanning
    for WL in np.arange(540,661,10):
        Raman(RotatorAngle1,WL,300,'benzene1800gvv5mW300s' + str(WL) + 'nm')

    for WL in np.arange(540,661,10):
        Raman(RotatorAngle2,WL,300,'benzene1800ghv5mW300s' + str(WL) + 'nm')

    # ## Polarization Scanning
    # for Pol in np.arange(25,111,1.0):
    #     Raman(Pol,600,10,'CYCPolinAngle' + str(Pol))

    

