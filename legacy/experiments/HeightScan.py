import sys
from API.LightFieldAPI import Experiment
from API.feinixsAPI import DelayStage
from API.ThorlabsAPI import Rotator
from API.KEYENCEAPI import DistanceDetector
from API.verticalStageAPI import VerticalStage

from threading import Thread, Event
import time

# Experiment Devices Parameters
VISRotatorSN = '55358884'
SFGRotatorSN = '55355234'
ExperimentName = 'HRBBSFGVS-PyLon'
vertical_stage_com = "COM9"
FilePath = 'D:\\2026\\JJH\\20260303SFGrecover\\heightscan'

# Devices Initialize
experiment = Experiment(ExperimentName)
experiment.set_file_path(FilePath)
# SFG_Rotator_VIS = Rotator("Cage", VISRotatorSN)
# SFG_Rotator_SFG = Rotator("Cage", SFGRotatorSN)
vertical_stage = VerticalStage(vertical_stage_com)
detector = DistanceDetector()
axis = 1

# Other Parameter
VIS_RotatorAngle_S = 45.83
VIS_RotatorAngle_P = 90.83
VIS_RotatorAngle_PM = VIS_RotatorAngle_P + 22.5
VIS_RotatorAngle_MM = VIS_RotatorAngle_P - 22.5
SFG_RotatorAngle_S = 28.00 #35.60
SFG_RotatorAngle_P = 73.00 #80.60
DelayStagePos =142 

target_height = 0

locking_event = Event()

def get_distance():
    detect_height, res = detector.get_distance()
    if not res:
        print("Height is out of range!")
        sys.exit()
    print("Current height: ", detect_height)
    distance = int(detect_height - target_height)
    return distance

def lock_height():
    while locking_event.wait():
        distance = get_distance()
        while abs(distance) >= 5 and locking_event.wait():
            vertical_stage.move(axis, distance)
            distance = get_distance()
        time.sleep(1)
        

def height_scan(start_height, end_height, step):

    locking = Thread(target=lock_height)
    locking.setDaemon(True)
    locking.start()
    
    for height in range(start_height, end_height, step):

        global target_height
        target_height = height
        print(target_height)

        distance = get_distance()
        vertical_stage.move(axis, distance)
        distance = get_distance()
        while abs(distance) >= 5:
            vertical_stage.move(axis, distance)
            distance = get_distance()

        locking_event.set()

        experiment.save_file(str(height))
        experiment.get_frame()

        locking_event.clear()

if __name__ == "__main__":
    experiment.set_exposure_time(1000)
    height_scan(400, 1500, 10) #高度不能为负值height can not be a negative value