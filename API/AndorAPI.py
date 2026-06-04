import matplotlib.pyplot as plt
import numpy as np
import time
from pyAndorSpectrograph.spectrograph import ATSpectrograph
from pyAndorSDK2 import atmcd, atmcd_codes, atmcd_errors

class AndorExperiment:
    def __init__(self) -> None:
        print("Initializing Camera")
        #Load libraries
        self.sdk = atmcd()
        self.spc = ATSpectrograph()
        self.codes = atmcd_codes

        #Initialize libraries
        shm = self.spc.Initialize("")
        print("Function Initialize returned {}".format(
            self.spc.GetFunctionReturnDescription(shm, 64)[1]))

        ret = self.sdk.Initialize("")
        print("Function Initialize returned {}".format(ret))
        if atmcd_errors.Error_Codes.DRV_SUCCESS == ret:
            if ATSpectrograph.ATSPECTROGRAPH_SUCCESS==shm:
            #Configure camera
                ret = self.sdk.SetTemperature(-80)
                print("Function SetTemperature returned {} target temperature -80".format(ret))

                ret = self.sdk.CoolerON()
                print("Function CoolerON returned {}".format(ret))
                
                while ret != atmcd_errors.Error_Codes.DRV_TEMP_STABILIZED:
                    time.sleep(5)
                    (ret, temperature) = self.sdk.GetTemperature()
                    print("Function GetTemperature returned {} current temperature = {}".format(
                    ret, temperature), end="\r")

                print("")
                print("Temperature stabilized")
                
                ret = self.sdk.SetReadMode(self.codes.Read_Mode.MULTI_TRACK)
                print("Function SetReadMode returned {}".format(ret))
                
                ret = self.sdk.SetTriggerMode(self.codes.Trigger_Mode.INTERNAL)
                print("Function SetTriggerMode returned {}".format(ret))
                
                ret = self.sdk.SetAcquisitionMode(self.codes.Acquisition_Mode.ACCUMULATE)
                print("Function SetAcquisitionMode returned {}".format(ret))
                
                (ret, self.xpixels, self.ypixels) = self.sdk.GetDetector()
                print("Function GetDetector returned {} xpixel = {} ypixel = {} ".format(ret,self.xpixels,self.ypixels))
            else:
                raise Exception("Cannot continue, could not initialise Spectrograph", shm)
        else:
            raise Exception("Cannot continue, could not initialise Camera", ret)
        



    