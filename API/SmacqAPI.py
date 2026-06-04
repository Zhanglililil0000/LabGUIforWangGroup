import sys
import ctypes
import numpy as np
from ctypes import windll, c_int, c_float, c_char, c_ulong, c_ushort, c_uint, c_long, POINTER

class SmacqAICard:
    """Smacq 采集卡 API，用于差分模式下读取设定通道的结果"""
    
    def __init__(self, device_id=0, timeout=1000, range_val=5.0, sample_rate=1000, channels=1):
        """
        初始化 Smacq 采集卡
        
        参数:
            device_id: 设备索引，默认 0
            timeout: 超时时间（毫秒），默认 1000
            range_val: 量程，5.0 表示 ±5V，10.0 表示 0-10V，默认 5.0
            sample_rate: 采样率（Hz），默认 1000
            channels: 通道数（二进制表示，如 1 表示通道 0，3 表示通道 0 和 1），默认 1
        """
        self.device_id = device_id
        self.timeout = timeout
        self.range_val = range_val
        self.sample_rate = sample_rate
        self.channels = channels
        
        # 加载 DLL
        try:
            # 尝试加载 x64 版本
            self.dll = windll.LoadLibrary(r'resources\Smacq\x64\usb-1000.dll')
        except Exception as e:
            try:
                # 尝试加载 x86 版本
                self.dll = windll.LoadLibrary(r'resources\Smacq\x86\usb-1000.dll')
            except Exception as e2:
                print(f"无法加载 DLL: {e}, {e2}")
                sys.exit(1)
        
        # 初始化参数
        self.dev_index = c_int(self.device_id)
        self.range_param = c_float(self.range_val)
        self.mode = c_char(0)  # 0 表示差分模式 (diff)
        self.sample_rate_param = c_uint(self.sample_rate)
        self.channel_sel = c_ushort(self.channels)
        self.timeout_param = c_long(self.timeout)
        
        # 打开设备
        res = self.dll.OpenDevice(self.dev_index)
        print(f"OpenDevice: {res}")
        if res != 0:
            print("Failed to open device.")
            sys.exit()
        
        # 重置设备
        res = self.dll.ResetDevice(self.dev_index)
        print(f"ResetDevice: {res}")
        
        # 设置通道接线方式（差分模式）
        res = self.dll.SetChanMode(self.dev_index, self.mode)
        print(f"SetChanMode (diff): {res}")
        
        # 设置量程
        res = self.dll.SetUSB1AiRange(self.dev_index, self.range_param)
        print(f"SetUSB1AiRange: {res}")
        
        # 设置采样率
        res = self.dll.SetSampleRate(self.dev_index, self.sample_rate_param)
        print(f"SetSampleRate: {res}")
        
        # 设置通道选择
        res = self.dll.SetChanSel(self.dev_index, self.channel_sel)
        print(f"SetChanSel: {res}")
        
        # 开启读数线程
        res = self.dll.StartRead(self.dev_index)
        print(f"StartRead: {res}")
        
        # 开启软件触发
        self.trig_open = c_char(1)
        res = self.dll.SetSoftTrig(self.dev_index, self.trig_open)
        print(f"SetSoftTrig (open): {res}")
        
        print("Smacq AI Card initialized successfully.")
    
    def read_channels(self, num_points=100):
        """
        读取设定通道的数据
        
        参数:
            num_points: 每个通道读取的点数，默认 100
            
        返回:
            包含通道数据的 numpy 数组，形状为 (通道数, num_points)
        """
        # 创建数据缓冲区
        total_points = num_points * self._count_channels()
        ai_buffer = np.zeros(total_points, dtype='float32')
        
        # 准备参数
        num_param = c_ulong(num_points)
        
        # 获取数据
        res = self.dll.GetAiChans(
            self.dev_index,
            num_param,
            self.channel_sel,
            ai_buffer.ctypes.data_as(POINTER(ctypes.c_float)),
            self.timeout_param
        )
        
        print(f"GetAiChans: {res}")
        
        if res < 0:
            error_msg = self._get_error_message(res)
            print(f"Error reading data: {error_msg}")
            return None
        
        # 重新组织数据为 (通道数, num_points)
        channel_count = self._count_channels()
        if channel_count > 0:
            data = ai_buffer.reshape(channel_count, num_points)
            return data
        else:
            return ai_buffer
    
    def _count_channels(self):
        """计算选择的通道数量"""
        count = 0
        ch = self.channels
        while ch:
            count += ch & 1
            ch >>= 1
        return count
    
    def _get_error_message(self, error_code):
        """获取错误码对应的错误信息"""
        error_messages = {
            -1: "NO_USBDAQ",
            -2: "DevIndex_Overflow",
            -3: "Bad_Firmware",
            -4: "USBDAQ_Closed",
            -5: "Transfer_Data_Fail",
            -6: "NO_Enough_Memory",
            -7: "Time_Out",
            -8: "Not_Reading"
        }
        return error_messages.get(error_code, f"Unknown error: {error_code}")
    
    def close(self):
        """关闭设备"""
        # 关闭软件触发
        trig_close = c_char(0)
        res = self.dll.SetSoftTrig(self.dev_index, trig_close)
        print(f"SetSoftTrig (close): {res}")
        
        # 停止读数线程
        res = self.dll.StopRead(self.dev_index)
        print(f"StopRead: {res}")
        
        # 清空缓冲区
        res = self.dll.ClearBufs(self.dev_index)
        print(f"ClearBufs: {res}")
        
        # 关闭设备
        self.dll.CloseDevice(self.dev_index)
        print("Device closed.")
    
    def __del__(self):
        """析构函数，确保设备被关闭"""
        # 避免重复关闭导致的错误
        pass


if __name__ == "__main__":
    # 测试代码
    try:
        # 创建采集卡实例（默认参数：设备0，差分模式，±5V量程，1000Hz采样率，通道0）
        card = SmacqAICard()
        
        # 读取数据（每个通道100个点）
        data = card.read_channels(num_points=100)
        
        if data is not None:
            print(f"Data shape: {data.shape}")
            print(f"Channel 0 first 10 points: {data[0, :10] if data.ndim > 1 else data[:10]}")
        
        # 关闭设备
        card.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
