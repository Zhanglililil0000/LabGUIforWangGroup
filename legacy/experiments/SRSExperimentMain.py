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
RotatorSN = '55169544'
ExperimentName = 'FSRS-Blaze'
FilePath = 'D:\\FSRScache\\Limonene'

# Devices Initialize
experiment = Experiment(ExperimentName)
experiment.set_file_path(FilePath)
Raman_Rotator = Rotator("Cage", RotatorSN)

# Other Parameter
RotatorAngleV = 41.88 # vertical polarization
RotatorAngleH = 86.88 # horizontal polarization

def SRS(DataName,CenterWavelength,Frames):
    experiment.set_center_wavelength(CenterWavelength)
    experiment.save_file(DataName)
    experiment.set_frames_number(Frames)

    pixels = int(experiment.get_pixels())

    experiment.get_frame()

    with open(FilePath + "/" + DataName + ".csv") as f:
            wavelength = []
            intensities = []
            intensity = []
            pixel = 0
            for line in f:
                x, y = map(float, line.split(","))
                if pixel < pixels:
                    wavelength.append(x)
                intensity.append(y)
                pixel += 1
                if pixel % pixels == 0:
                    intensities.append(np.array(intensity))
                    intensity =[]

            ret1 = sum([intensities[i] / intensities[i + 1] - 1 for i in range(0, Frames, 2)]) / (Frames / 2)
            ret2 = sum([intensities[i + 1] / intensities[i] - 1 for i in range(0, Frames, 2)]) / (Frames / 2)
            ret = ret1 if max(ret1) - min(ret1) > max(ret2) - min(ret2) else ret2

            with open(FilePath + "/" + DataName + "_ret.csv", "w", newline="") as ret_file:
                writer = csv.writer(ret_file)
                writer.writerows(list(np.array([wavelength, ret]).T))

            with open(FilePath + "/" + DataName + "_ret1.csv", "w", newline="") as ret_file:
                writer = csv.writer(ret_file)
                writer.writerows(list(np.array([wavelength, ret1]).T))

            with open(FilePath + "/" + DataName + "_ret2.csv", "w", newline="") as ret_file:
                writer = csv.writer(ret_file)
                writer.writerows(list(np.array([wavelength, ret2]).T))
            
            return [list(wavelength), list(ret)]


if __name__ == "__main__":

    # Experiment Initialize
    Raman_Rotator.home()
    Raman_Rotator.moveto(RotatorAngleV)

    SRS("LimoneneVV1800g10000FramesGain625nm",
        625,
        10000)
    SRS("LimoneneVV1800g10000FramesGain630nm",
        630,
        10000)
    SRS("LimoneneVV1800g10000FramesGain635nm",
        635,
        10000)


    Raman_Rotator.home()
    Raman_Rotator.moveto(RotatorAngleH)

    SRS("LimoneneVH1800g10000FramesGain625nm",
        625,
        10000)
    SRS("LimoneneVH1800g10000FramesGain630nm",
        630,
        10000)
    SRS("LimoneneVH1800g10000FramesGain635nm",
        635,
        10000)

    Raman_Rotator.home()
    Raman_Rotator.moveto(RotatorAngleV)


    


