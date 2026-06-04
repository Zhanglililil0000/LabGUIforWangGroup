# Import the .NET class library
import clr

# Import python sys module
import sys

# Import System.IO for saving and opening files
from System.IO import *

import time

clr.AddReference('resources/ftcorecs')

from ftcorecs import *

class DelayStage:

    controller_type = {
        "SMC": ftcore.CONTROLLER_TYPE_SMC,
        "AMC": ftcore.CONTROLLER_TYPE_AMC,
        "NANO": ftcore.CONTROLLER_TYPE_NANO,
        "MINI0S": ftcore.CONTROLLER_TYPE_MINI04
    }

    limit_isnegative = {
        True: ftcore.FT_TRUE,
        False: ftcore.FT_FALSE
    }

    def __init__(self, port, baud=19200, controller_type_="SMC", slave=0xCC, limit_isnegative_=True) -> None:
        ret, handle = ftcore.ft_open_com(port, baud, self.controller_type[controller_type_], slave, self.limit_isnegative[limit_isnegative_], 0)
        if ret == ftcore.FT_SUCESS:
            self.handle = handle
            print("Connected!")
        else:
            raise Exception("Can't connect!", ret)
        
    # def __del__(self):
    #     self.close()
        
    def close(self):
        ret = ftcore.ft_close(self.handle)
        if ret == ftcore.FT_SUCESS:
            print("Closed!")
        else:
            raise Exception("Can't close!", ret)
        
    def get_accel(self, axis):
        ret, accel = ftcore.ft_get_accel(self.handle, axis, 0)
        if ret == ftcore.FT_SUCESS:
            print(axis + " acceleration:", accel)
            return accel
        else:
            raise Exception("Can't get " + axis + " acceleration!", ret)
    
    def set_accel(self, axis, value):
        ret = ftcore.ft_set_accel(self.handle, axis, value)
        if ret == ftcore.FT_SUCESS:
            return self.get_accel(axis)
        else:
            raise Exception("Can't set " + axis + " acceleration!", ret)
        
    def get_div(self, axis):
        ret, div = ftcore.ft_get_div(self.handle, axis, 0)
        if ret == ftcore.FT_SUCESS:
            print(axis + " division:", div)
            return div
        else:
            raise Exception("Can't get " + axis + " division!", ret)
    
    def set_div(self, axis, value):
        ret = ftcore.ft_set_div(self.handle, axis, value)
        if ret == ftcore.FT_SUCESS:
            return self.get_div(axis)
        else:
            raise Exception("Can't set " + axis + " division!", ret)
    
    def get_pitch(self, axis):
        ret, pitch = ftcore.ft_get_pitch(self.handle, axis, 0)
        if ret == ftcore.FT_SUCESS:
            print(axis + " pitch:", pitch)
            return pitch
        else:
            raise Exception("Can't get " + axis + " pitch!", ret)
    
    def set_pitch(self, axis, value):
        ret = ftcore.ft_set_pitch(self.handle, axis, value)
        if ret == ftcore.FT_SUCESS:
            return self.get_pitch(axis)
        else:
            raise Exception("Can't set " + axis + " pitch!", ret)

    def get_vel(self, axis):
        ret, vel = ftcore.ft_get_vel(self.handle, axis, 0)
        if ret == ftcore.FT_SUCESS:
            print(axis + " velocity:", vel)
            return vel
        else:
            raise Exception("Can't get " + axis + " velocity!", ret)
    
    def set_vel(self, axis, value):
        ret = ftcore.ft_set_vel(self.handle, axis, value)
        if ret == ftcore.FT_SUCESS:
            return self.get_vel(axis)
        else:
            raise Exception("Can't set " + axis + " velocity!", ret)
        
    def get_homingvel(self, axis):
        ret, homingvel = ftcore.ft_get_homingvel(self.handle, axis, 0)
        if ret == ftcore.FT_SUCESS:
            print(axis + " homing velocity:", homingvel)
            return homingvel
        else:
            raise Exception("Can't get " + axis + " homing velocity!", ret)
    
    def set_homingvel(self, axis, value):
        ret = ftcore.ft_set_homingvel(self.handle, axis, value)
        if ret == ftcore.FT_SUCESS:
            return self.get_homingvel(axis)
        else:
            raise Exception("Can't set " + axis + " homing velocity!", ret)
    
    def get_homeoffset(self, axis):
        ret, homeoffset = ftcore.ft_get_homeoffset(self.handle, axis, 0)
        if ret == ftcore.FT_SUCESS:
            print(axis + " home offset:", homeoffset)
            return homeoffset
        else:
            raise Exception("Can't get " + axis + " home offset!", ret)
    
    def set_homeoffset(self, axis, value):
        ret = ftcore.ft_set_homeoffset(self.handle, axis, value)
        if ret == ftcore.FT_SUCESS:
            return self.get_homeoffset(axis)
        else:
            raise Exception("Can't set " + axis + " home offset!", ret)

    def isrunning(self, axis):
        ret, _isrunning = ftcore.ft_single_isrunning(self.handle, axis, 0)
        if ret == ftcore.FT_SUCESS:
            # print(axis, ("is running!" if _isrunning == ftcore.FT_TRUE else "isn't running!"))
            return _isrunning == ftcore.FT_TRUE
        else:
            raise Exception("Can't get " + axis + " running information!", ret)
        
    def ishomed(self, axis):
        ret, _ishomed = ftcore.ft_single_ishomed(self.handle, axis, 0)
        if ret == ftcore.FT_SUCESS:
            # print(axis, ("is homed!" if _ishomed == ftcore.FT_TRUE else "isn't homed!"))
            return _ishomed == ftcore.FT_TRUE
        else:
            raise Exception("Can't get " + axis + " home information!", ret)
        
    def get_pos(self, axis):
        ret, pos = ftcore.ft_single_getpos(self.handle, axis, 0)
        if ret == ftcore.FT_SUCESS:
            print(axis + " position:", pos)
            return pos
        else:
            raise Exception("Can't get " + axis + " position!", ret)
    
    def stop(self, axis):
        ret = ftcore.ft_single_stop(self.handle, axis)
        if ret == ftcore.FT_SUCESS:
            print(axis + " stopped!")
            return True
        else:
            raise Exception(axis + " can't stop!", ret)
    
    def zero(self, axis):
        ret = ftcore.ft_single_zero(self.handle, axis)
        if ret == ftcore.FT_SUCESS:
            print(axis + " set zero!")
            return True
        else:
            raise Exception("Can't set " + axis + " zero!", ret)
        
    def home(self, axis):
        pos = self.get_pos(axis)
        homingvel = self.get_homingvel(axis)
        ret = ftcore.ft_single_home(self.handle, axis)
        if ret == ftcore.FT_SUCESS:
            print(axis + " is homing ...")
            time.sleep(pos / homingvel)
            while self.isrunning(axis):
                time.sleep(5)
            if self.get_pos(axis) == 0:
                print(axis + " has homed!")
                return self.get_pos(axis)
            else:
                raise Exception(axis + "home failed!")
        else:
            raise Exception(axis + "home failed!", ret)
        
    def move(self, axis, value):
        pos = self.get_pos(axis)
        vel = self.get_vel(axis)
        ret = ftcore.ft_single_move(self.handle, axis, value)
        if ret == ftcore.FT_SUCESS:
            print(axis + " is moving ...")
            time.sleep(abs(value) / vel)
            while self.isrunning(axis):
                time.sleep(5)
            return self.get_pos(axis)
        else:
            raise Exception(axis + " can't move!", ret)
        
    def moveto(self, axis, value):
        pos = self.get_pos(axis)
        vel = self.get_vel(axis)
        ret = ftcore.ft_single_moveabs(self.handle, axis, value)
        if ret == ftcore.FT_SUCESS:
            print(axis + " is moving ...")
            time.sleep(abs(pos - value) / vel)
            while self.isrunning(axis):
                time.sleep(5)
            return self.get_pos(axis)
        else:
            raise Exception(axis + " can't move!", ret)
    

# if __name__ == "__main__":
    
#     delayStage = DelayStage("COM4", 19200, "SMC", 0xCC, True)
#     delayStage.home("X")
#     delayStage.moveto("X", 170)
#     delayStage.close()