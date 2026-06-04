"""
简化版光电二极管测试程序
每次读取100个点取平均，间隔1秒，共读取20次
CSV文件只包含两列：次数和平均值
"""

import sys
import numpy as np
import pandas as pd
import time
from datetime import datetime

# 添加 API 目录到路径
sys.path.append('API')
from API.SmacqAPI import SmacqAICard


def simple_photodiode_test():
    """
    简化版光电二极管测试
    输出CSV只有两列：次数和平均值
    修改：每次读取后关闭采集卡，下次读取前重新打开
    """
    print("简化版光电二极管测试（每次独立打开/关闭采集卡）")
    print("每次读取100个点取平均，间隔1秒，共读取20次")
    print("CSV格式: 第一列=次数, 第二列=平均值(V)")
    print("-" * 50)
    
    # 存储结果
    measurement_numbers = []
    average_values = []
    
    print("\n开始测量...")
    
    for i in range(20):
        start_time = time.time()
        
        print(f"测量 {i+1}/20...", end='')
        
        try:
            # 每次测量前初始化采集卡（通道1，差分模式）
            # 注意：channels=2 表示通道1（二进制 10）
            card = SmacqAICard(
                device_id=0,
                channels=1,       # 通道0
                sample_rate=1000,
                range_val=5.0
            )
            
            # 读取100个点
            data = card.read_channels(num_points=100)
            
            if data is not None:
                avg_value = float(np.mean(data))  # 转换为Python float
                measurement_numbers.append(i + 1)
                average_values.append(avg_value)
                print(f" 平均值: {avg_value:.6f} V")
            else:
                print(f" 失败")
                measurement_numbers.append(i + 1)
                average_values.append(np.nan)
            
            # 立即关闭采集卡
            card.close()
            
        except Exception as e:
            print(f" 错误: {e}")
            measurement_numbers.append(i + 1)
            average_values.append(np.nan)
        
        # 等待到总共1秒间隔
        elapsed = time.time() - start_time
        wait_time = max(0, 1.0 - elapsed)
        
        if i < 19 and wait_time > 0:
            time.sleep(wait_time)
    
    print("\n测量完成!")
    
    # 保存为简单CSV（只有两列）
    save_simple_csv(measurement_numbers, average_values)
    
    # 显示简要统计
    if average_values:
        valid_values = [v for v in average_values if not np.isnan(v)]
        if valid_values:
            valid_array = np.array(valid_values)
            print(f"\n统计:")
            print(f"  测量次数: {len(valid_array)}")
            print(f"  平均值: {valid_array.mean():.6f} V")
            print(f"  范围: {valid_array.min():.6f} - {valid_array.max():.6f} V")
    
    print("\n设备已关闭（每次测量后已独立关闭）")


def save_simple_csv(measurement_numbers, average_values):
    """保存为简单CSV文件（只有两列）"""
    if not measurement_numbers:
        print("错误: 没有数据")
        return
    
    # 创建只有两列的DataFrame
    df = pd.DataFrame({
        'Measurement': measurement_numbers,
        'Average_Voltage_V': average_values
    })
    
    # 生成文件名
    filename = f"simple_photodiode_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # 保存CSV（不保存索引）
    df.to_csv(filename, index=False)
    
    print(f"\n数据已保存: {filename}")
    print(f"文件格式: 第一列=次数, 第二列=平均值(V)")
    
    # 显示文件内容
    print("\nCSV文件内容:")
    print(df.to_string(index=False))
    
    return filename


if __name__ == "__main__":
    try:
        simple_photodiode_test()
    except KeyboardInterrupt:
        print("\n测试被中断")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
