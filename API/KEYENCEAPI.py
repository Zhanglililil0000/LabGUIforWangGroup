import sys
import resources.KEYENCE.CL3wrap as CL3wrap

class DistanceDetector:
    def __init__(self, deviceId=0, timeout=10000) -> None:
        self.deviceId = deviceId
        self.timeout = timeout
        res = CL3wrap.CL3IF_OpenUsbCommunication(self.deviceId, self.timeout)
        print("CL3wrap.CL3IF_OpenUsbCommunication:", CL3wrap.CL3IF_hex(res))
        if res != 0:
            print("Failed to connect controller.")
            sys.exit()
        print("----")

    def get_distance(self):
        measurementData = CL3wrap.CL3IF_MEASUREMENT_DATA()
        res = CL3wrap.CL3IF_GetMeasurementData(self.deviceId, measurementData)
        height = measurementData.outMeasurementData[0].measurementValue / 10
        valid = CL3wrap.CL3IF_VALUE_INFO_ENUM(measurementData.outMeasurementData[0].valueInfo).name
        return (height, valid == "CL3IF_VALUE_INFO_VALID")
    
# if __name__ == "__main__":
#     distance_detector = DistanceDetector()
#     print(distance_detector.get_distance())