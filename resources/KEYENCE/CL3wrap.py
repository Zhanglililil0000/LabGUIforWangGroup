# -*- coding: 'unicode' -*-
# Copyright (c) 2023 KEYENCE CORPORATION. All rights reserved.
from enum import Enum
import ctypes
from ctypes import cdll
import os.path

# These const parameters are used in
# CL3IF_GetTrendData and CL3IF_GetStorageData.
NUMBER_OF_OUT_TO_BE_STORED = 1
REQUEST_DATA_COUNT = 1


#########################################################
# Select the library according to the Operating System
#########################################################
dll_name = "CL3_IF.dll"        # For Windows

dllabspath = os.path.dirname(os.path.abspath(__file__))+os.path.sep+dll_name
mdll = cdll.LoadLibrary(dllabspath)


#########################################################
# Enums
#########################################################
class CL3IF_DEVICETYPE_ENUM(Enum):
    CL3IF_DEVICETYPE_INVALID = 0x00
    CL3IF_DEVICETYPE_CONTROLLER = 0x01
    CL3IF_DEVICETYPE_OPTICALUNIT1 = 0x11
    CL3IF_DEVICETYPE_OPTICALUNIT2 = 0x12
    CL3IF_DEVICETYPE_OPTICALUNIT3 = 0x13
    CL3IF_DEVICETYPE_OPTICALUNIT4 = 0x14
    CL3IF_DEVICETYPE_OPTICALUNIT5 = 0x15
    CL3IF_DEVICETYPE_OPTICALUNIT6 = 0x16
    CL3IF_DEVICETYPE_EXUNIT1 = 0x41
    CL3IF_DEVICETYPE_EXUNIT2 = 0x42


class CL3IF_VALUE_INFO_ENUM(Enum):
    CL3IF_VALUE_INFO_VALID = 0
    CL3IF_VALUE_INFO_JUDGMENTSTANDBY = 1
    CL3IF_VALUE_INFO_INVALID = 2
    CL3IF_VALUE_INFO_OVERDISPRANGE_P = 3
    CL3IF_VALUE_INFO_OVERDISPRANGE_N = 4


class CL3IF_JUDGE_RESULT_ENUM(Enum):
    CL3IF_JUDGE_RESULT_HI = 1
    CL3IF_JUDGE_RESULT_GO = 2
    CL3IF_JUDGE_RESULT_LO = 4
    CL3IF_JUDGE_RESULT_STANDBY = 0
    CL3IF_JUDGE_RESULT_INVALID = 5


class CL3IF_SELECTED_INDEX_ENUM(Enum):
    CL3IF_SELECTED_INDEX_OLDEST = 0
    CL3IF_SELECTED_INDEX_NEWEST = 1


#########################################################
# Structures
#########################################################
class CL3IF_ETHERNET_SETTING(ctypes.Structure):
    _fields_ = [
        ("abyIpAddress", ctypes.c_ubyte * 4),
        ("wPortNo", ctypes.c_ushort),
        ("reserve", ctypes.c_ubyte * 2)]


class CL3IF_DEVICETYPE(ctypes.Structure):
    _fields_ = [
        ("devicetype", ctypes.c_ushort * 9)]


class CL3IF_ADD_INFO(ctypes.Structure):
    _fields_ = [
        ("triggerCount", ctypes.c_uint32),
        ("pulseCount", ctypes.c_int),
        ]


class CL3IF_OUTMEASUREMENT_DATA(ctypes.Structure):
    _fields_ = [
        ("measurementValue", ctypes.c_int),
        ("valueInfo", ctypes.c_ubyte),
        ("judgeResult", ctypes.c_ubyte),
        ("reserved", ctypes.c_ubyte * 2),
        ]


class CL3IF_MEASUREMENT_DATA(ctypes.Structure):
    _fields_ = [
        ("addInfo", CL3IF_ADD_INFO),
        ("outMeasurementData", CL3IF_OUTMEASUREMENT_DATA * 8),
        ]


class CL3IF_OUTNO(ctypes.Structure):
    _fields_ = [
        ("outno", ctypes.c_ushort),
        ]


class CL3IF_MEASUREMENT_DATA_SELECT(ctypes.Structure):
    _fields_ = [
        ("addInfo", CL3IF_ADD_INFO),
        ("outMeasurementData",
         CL3IF_OUTMEASUREMENT_DATA * NUMBER_OF_OUT_TO_BE_STORED),
        ]


class CL3IF_WAVE_DATA(ctypes.Structure):
    _fields_ = [
        ("wavedata", ctypes.c_ushort * 2048),
        ]


#########################################################
# DLL Wrapper Functions
#########################################################

# CL3IF_OpenUsbCommunication
CL3IF_OpenUsbCommunication = mdll.CL3IF_OpenUsbCommunication
CL3IF_OpenUsbCommunication.restype = ctypes.c_int
CL3IF_OpenUsbCommunication.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_uint                               # lTimeout
    ]

# CL3IF_OpenEthernetCommunication
CL3IF_OpenEthernetCommunication = mdll.CL3IF_OpenEthernetCommunication
CL3IF_OpenEthernetCommunication.restype = ctypes.c_int
CL3IF_OpenEthernetCommunication.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.POINTER(CL3IF_ETHERNET_SETTING),     # pEthernetConfig
    ctypes.c_uint                               # lTimeout
    ]

# CL3IF_CloseCommunication
CL3IF_CloseCommunication = mdll.CL3IF_CloseCommunication
CL3IF_CloseCommunication.restype = ctypes.c_int
CL3IF_CloseCommunication.argtypes = [
    ctypes.c_int                                # deviceId
    ]

# CL3IF_ReturnToFactoryDefaultSetting
CL3IF_ReturnToFactoryDefaultSetting = mdll.CL3IF_ReturnToFactoryDefaultSetting
CL3IF_ReturnToFactoryDefaultSetting.restype = ctypes.c_int
CL3IF_ReturnToFactoryDefaultSetting.argtypes = [
    ctypes.c_int                                # deviceId
    ]

# CL3IF_GetSystemConfiguration
CL3IF_GetSystemConfiguration = mdll.CL3IF_GetSystemConfiguration
CL3IF_GetSystemConfiguration.restype = ctypes.c_int
CL3IF_GetSystemConfiguration.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.POINTER(ctypes.c_ubyte),             # deviceCount
    ctypes.POINTER(CL3IF_DEVICETYPE)            # deviceTypeList
    ]

# CL3IF_GetMeasurementData
CL3IF_GetMeasurementData = mdll.CL3IF_GetMeasurementData
CL3IF_GetMeasurementData.restype = ctypes.c_int
CL3IF_GetMeasurementData.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.POINTER(CL3IF_MEASUREMENT_DATA),     # measurementData
    ]

# CL3IF_GetTrendIndex
CL3IF_GetTrendIndex = mdll.CL3IF_GetTrendIndex
CL3IF_GetTrendIndex.restype = ctypes.c_int
CL3IF_GetTrendIndex.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.POINTER(ctypes.c_uint),              # index
    ]

# CL3IF_GetTrendData
CL3IF_GetTrendData = mdll.CL3IF_GetTrendData
CL3IF_GetTrendData.restype = ctypes.c_int
CL3IF_GetTrendData.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_uint,                              # index
    ctypes.c_uint,                              # requestDataCount
    ctypes.POINTER(ctypes.c_uint),              # nextIndex
    ctypes.POINTER(ctypes.c_uint),              # obtainedDataCount
    ctypes.POINTER(CL3IF_OUTNO),                # outTarget
    ctypes.POINTER(
        CL3IF_MEASUREMENT_DATA_SELECT
        * REQUEST_DATA_COUNT)                    # measurementData
    ]

# CL3IF_GetStorageIndex
CL3IF_GetStorageIndex = mdll.CL3IF_GetStorageIndex
CL3IF_GetStorageIndex.restype = ctypes.c_int
CL3IF_GetStorageIndex.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_uint,                              # selectedIndex
    ctypes.POINTER(ctypes.c_uint)               # index
    ]

# CL3IF_GetStorageData
CL3IF_GetStorageData = mdll.CL3IF_GetStorageData
CL3IF_GetStorageData.restype = ctypes.c_int
CL3IF_GetStorageData.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_uint,                              # index
    ctypes.c_uint,                              # requestDataCount
    ctypes.POINTER(ctypes.c_uint),              # nextIndex
    ctypes.POINTER(ctypes.c_uint),              # obtainedDataCount
    ctypes.POINTER(CL3IF_OUTNO),                # outTarget
    ctypes.POINTER(
        CL3IF_MEASUREMENT_DATA_SELECT
        * REQUEST_DATA_COUNT)                    # measurementData
    ]

# CL3IF_StartStorage
CL3IF_StartStorage = mdll.CL3IF_StartStorage
CL3IF_StartStorage.restype = ctypes.c_int
CL3IF_StartStorage.argtypes = [
    ctypes.c_int                                # deviceId
    ]

# CL3IF_StopStorage
CL3IF_StopStorage = mdll.CL3IF_StopStorage
CL3IF_StopStorage.restype = ctypes.c_int
CL3IF_StopStorage.argtypes = [
    ctypes.c_int                                # deviceId
    ]

# CL3IF_ClearStorageData
CL3IF_ClearStorageData = mdll.CL3IF_ClearStorageData
CL3IF_ClearStorageData.restype = ctypes.c_int
CL3IF_ClearStorageData.argtypes = [
    ctypes.c_int                                # deviceId
    ]

# CL3IF_AutoZeroSingle
CL3IF_AutoZeroSingle = mdll.CL3IF_AutoZeroSingle
CL3IF_AutoZeroSingle.restype = ctypes.c_int
CL3IF_AutoZeroSingle.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_ushort,                            # outNo
    ctypes.c_ubyte                              # onOff
    ]

# CL3IF_AutoZeroMulti
CL3IF_AutoZeroMulti = mdll.CL3IF_AutoZeroMulti
CL3IF_AutoZeroMulti.restype = ctypes.c_int
CL3IF_AutoZeroMulti.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_ushort,                            # outNo
    ctypes.c_ubyte                              # onOff
    ]

# CL3IF_AutoZeroGroup
CL3IF_AutoZeroGroup = mdll.CL3IF_AutoZeroGroup
CL3IF_AutoZeroGroup.restype = ctypes.c_int
CL3IF_AutoZeroGroup.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_ushort,                            # group
    ctypes.c_ubyte                              # onOff
    ]

# CL3IF_TimingSingle
CL3IF_TimingSingle = mdll.CL3IF_TimingSingle
CL3IF_TimingSingle.restype = ctypes.c_int
CL3IF_TimingSingle.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_ushort,                            # outNo
    ctypes.c_ubyte                              # onOff
    ]

# CL3IF_TimingMulti
CL3IF_TimingMulti = mdll.CL3IF_TimingMulti
CL3IF_TimingMulti.restype = ctypes.c_int
CL3IF_TimingMulti.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_ushort,                            # outNo
    ctypes.c_ubyte                              # onOff
    ]

# CL3IF_TimingGroup
CL3IF_TimingGroup = mdll.CL3IF_TimingGroup
CL3IF_TimingGroup.restype = ctypes.c_int
CL3IF_TimingGroup.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_ushort,                            # group
    ctypes.c_ubyte                              # onOff
    ]

# CL3IF_ResetSingle
CL3IF_ResetSingle = mdll.CL3IF_ResetSingle
CL3IF_ResetSingle.restype = ctypes.c_int
CL3IF_ResetSingle.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_ushort                             # group
    ]

# CL3IF_ResetMulti
CL3IF_ResetMulti = mdll.CL3IF_ResetMulti
CL3IF_ResetMulti.restype = ctypes.c_int
CL3IF_ResetMulti.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_ushort                             # outNo
    ]

# CL3IF_ResetGroup
CL3IF_ResetGroup = mdll.CL3IF_ResetGroup
CL3IF_ResetGroup.restype = ctypes.c_int
CL3IF_ResetGroup.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_ushort                             # group
    ]

# CL3IF_LightControl
CL3IF_LightControl = mdll.CL3IF_LightControl
CL3IF_LightControl.restype = ctypes.c_int
CL3IF_LightControl.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_ubyte                              # onOff
    ]

# CL3IF_MeasurementControl
CL3IF_MeasurementControl = mdll.CL3IF_MeasurementControl
CL3IF_MeasurementControl.restype = ctypes.c_int
CL3IF_MeasurementControl.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_ubyte                              # onOff
    ]

# CL3IF_SwitchProgram
CL3IF_SwitchProgram = mdll.CL3IF_SwitchProgram
CL3IF_SwitchProgram.restype = ctypes.c_int
CL3IF_SwitchProgram.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_ubyte                              # programNo
    ]

# CL3IF_GetProgramNo
CL3IF_GetProgramNo = mdll.CL3IF_GetProgramNo
CL3IF_GetProgramNo.restype = ctypes.c_int
CL3IF_GetProgramNo.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.POINTER(ctypes.c_ubyte)              # programNo
    ]

# CL3IF_LockPanel
CL3IF_LockPanel = mdll.CL3IF_LockPanel
CL3IF_LockPanel.restype = ctypes.c_int
CL3IF_LockPanel.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_ubyte                              # onOff
    ]

# CL3IF_GetTerminalStatus
CL3IF_GetTerminalStatus = mdll.CL3IF_GetTerminalStatus
CL3IF_GetTerminalStatus.restype = ctypes.c_int
CL3IF_GetTerminalStatus.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.POINTER(ctypes.c_ushort),            # inputTerminalStatus
    ctypes.POINTER(ctypes.c_ushort)             # outputTerminalStatus
    ]

# CL3IF_GetPulseCount
CL3IF_GetPulseCount = mdll.CL3IF_GetPulseCount
CL3IF_GetPulseCount.restype = ctypes.c_int
CL3IF_GetPulseCount.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.POINTER(ctypes.c_int)                # pulseCount
    ]

# CL3IF_ResetPulseCount
CL3IF_ResetPulseCount = mdll.CL3IF_ResetPulseCount
CL3IF_ResetPulseCount.restype = ctypes.c_int
CL3IF_ResetPulseCount.argtypes = [
    ctypes.c_int,                               # deviceId
    ]

# CL3IF_GetLightWaveform
CL3IF_GetLightWaveform = mdll.CL3IF_GetLightWaveform
CL3IF_GetLightWaveform.restype = ctypes.c_int
CL3IF_GetLightWaveform.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_ubyte,                             # headNo
    ctypes.c_ubyte,                             # peakNo
    ctypes.POINTER(CL3IF_WAVE_DATA)             # waveData
    ]

# CL3IF_GetHeadAlignLevel
CL3IF_GetHeadAlignLevel = mdll.CL3IF_GetHeadAlignLevel
CL3IF_GetHeadAlignLevel.restype = ctypes.c_int
CL3IF_GetHeadAlignLevel.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_ubyte,                             # headNo1
    ctypes.c_ubyte,                             # headNo2
    ctypes.POINTER(ctypes.c_int),               # optAxis1
    ctypes.POINTER(ctypes.c_int),               # optAxis2
    ctypes.POINTER(ctypes.c_int),               # optAxis3
    ctypes.POINTER(ctypes.c_int),               # optAxis4
    ctypes.POINTER(ctypes.c_int)                # total
    ]

# CL3IF_StartLightIntensityTuning
CL3IF_StartLightIntensityTuning = mdll.CL3IF_StartLightIntensityTuning
CL3IF_StartLightIntensityTuning.restype = ctypes.c_int
CL3IF_StartLightIntensityTuning.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_ubyte                              # headNo
    ]

# CL3IF_StopLightIntensityTuning
CL3IF_StopLightIntensityTuning = mdll.CL3IF_StopLightIntensityTuning
CL3IF_StopLightIntensityTuning.restype = ctypes.c_int
CL3IF_StopLightIntensityTuning.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_ubyte                              # headNo
    ]

# CL3IF_CancelLightIntensityTuning
CL3IF_CancelLightIntensityTuning = mdll.CL3IF_CancelLightIntensityTuning
CL3IF_CancelLightIntensityTuning.restype = ctypes.c_int
CL3IF_CancelLightIntensityTuning.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_ubyte                              # headNo
    ]

# CL3IF_StartCalibration
CL3IF_StartCalibration = mdll.CL3IF_StartCalibration
CL3IF_StartCalibration.restype = ctypes.c_int
CL3IF_StartCalibration.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_ubyte                              # headNo
    ]

# CL3IF_StopCalibration
CL3IF_StopCalibration = mdll.CL3IF_StopCalibration
CL3IF_StopCalibration.restype = ctypes.c_int
CL3IF_StopCalibration.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_ubyte                              # headNo
    ]

# CL3IF_CancelCalibration
CL3IF_CancelCalibration = mdll.CL3IF_CancelCalibration
CL3IF_CancelCalibration.restype = ctypes.c_int
CL3IF_CancelCalibration.argtypes = [
    ctypes.c_int,                               # deviceId
    ctypes.c_ubyte                              # headNo
    ]

# CL3IF_TransitToMeasurementMode
CL3IF_TransitToMeasurementMode = mdll.CL3IF_TransitToMeasurementMode
CL3IF_TransitToMeasurementMode.restype = ctypes.c_int
CL3IF_TransitToMeasurementMode.argtypes = [
    ctypes.c_int                                # deviceId
    ]

# CL3IF_TransitToSettingMode
CL3IF_TransitToSettingMode = mdll.CL3IF_TransitToSettingMode
CL3IF_TransitToSettingMode.restype = ctypes.c_int
CL3IF_TransitToSettingMode.argtypes = [
    ctypes.c_int                                # deviceId
    ]


def CL3IF_hex(num):
    if num == 0:
        hexed_num = "OK"
    else:
        hexed_num = "NG("+str(num)+")"

    return hexed_num
