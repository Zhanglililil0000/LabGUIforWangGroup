# Smacq 采集卡 API 使用说明

## 概述

`SmacqAPI.py` 是一个用于控制 Smacq USB-1000 系列采集卡的 Python API。该 API 参考了 `KEYENCEAPI.py` 的设计形式，提供了在差分模式下读取设定通道结果的基本功能。

## 文件结构

```
API/
├── SmacqAPI.py              # 主 API 文件
├── SmacqAPI_README.md       # 本使用说明
├── test_smacq.py           # 测试脚本
└── example_usage.py        # 使用示例
```

## 依赖要求

- Python 3.6+
- NumPy (`pip install numpy`)
- Smacq USB-1000 系列采集卡驱动程序 DLL 文件（已包含在 `resources/Smacq/` 目录中）

## 快速开始

### 1. 基本使用

```python
import sys
sys.path.append('..')  # 如果从其他目录导入
from SmacqAPI import SmacqAICard

# 创建采集卡实例（使用默认参数）
card = SmacqAICard()

try:
    # 读取数据（每个通道100个点）
    data = card.read_channels(num_points=100)
    
    if data is not None:
        print(f"数据形状: {data.shape}")  # (通道数, 点数)
        print(f"通道0数据: {data[0, :10]}")  # 前10个点
finally:
    # 确保关闭设备
    card.close()
```

### 2. 完整示例

```python
from SmacqAPI import SmacqAICard

# 初始化采集卡
card = SmacqAICard(
    device_id=0,      # 设备索引
    timeout=1000,     # 超时时间（毫秒）
    range_val=5.0,    # 量程：5.0=±5V, 10.0=0-10V
    sample_rate=1000, # 采样率（Hz）
    channels=1        # 通道选择：1=通道0, 3=通道0和1, 255=所有8个通道
)

# 读取数据
data = card.read_channels(num_points=50)

if data is not None:
    # 处理数据
    for ch in range(data.shape[0]):
        avg_voltage = data[ch].mean()
        print(f"通道 {ch} 平均电压: {avg_voltage:.4f} V")

# 关闭设备
card.close()
```

## API 参考

### `SmacqAICard` 类

#### 构造函数

```python
SmacqAICard(device_id=0, timeout=1000, range_val=5.0, sample_rate=1000, channels=1)
```

**参数：**
- `device_id` (int): 设备索引，默认 0
- `timeout` (int): 超时时间（毫秒），默认 1000
- `range_val` (float): 量程设置，5.0 表示 ±5V，10.0 表示 0-10V，默认 5.0
- `sample_rate` (int): 采样率（Hz），默认 1000
- `channels` (int): 通道选择（二进制表示），默认 1（通道0）
  - `1` (0b00000001): 通道0
  - `3` (0b00000011): 通道0和1
  - `255` (0b11111111): 所有8个通道

#### 方法

##### `read_channels(num_points=100)`

读取设定通道的数据。

**参数：**
- `num_points` (int): 每个通道读取的点数，默认 100

**返回值：**
- `numpy.ndarray`: 形状为 `(通道数, num_points)` 的数组，包含读取的电压数据（单位：V）
- `None`: 读取失败时返回

##### `close()`

关闭设备，释放资源。应在程序结束时调用。

#### 属性

- `device_id`: 设备索引
- `timeout`: 超时时间（毫秒）
- `range_val`: 量程设置
- `sample_rate`: 采样率（Hz）
- `channels`: 通道选择

## 通道选择说明

通道选择使用二进制表示法，每个位对应一个通道：

| 二进制值 | 十进制 | 选择的通道 |
|---------|-------|-----------|
| 00000001 | 1 | 通道0 |
| 00000011 | 3 | 通道0, 1 |
| 00000111 | 7 | 通道0, 1, 2 |
| 11111111 | 255 | 通道0-7（所有8个通道） |

## 错误处理

API 包含基本的错误处理机制。常见的错误代码：

| 错误代码 | 说明 |
|---------|------|
| 0 | 成功 |
| -1 | NO_USBDAQ（未找到设备） |
| -4 | USBDAQ_Closed（设备已关闭） |
| -7 | Time_Out（超时） |

当发生错误时，API 会在控制台输出错误信息，并返回 `None`。

## 使用注意事项

1. **设备连接**：确保采集卡已通过 USB 连接并安装驱动程序。
2. **资源释放**：使用 `try...finally` 确保 `close()` 方法被调用，避免资源泄漏。
3. **采样率限制**：多通道采集时，总采样率最大为 200kHz。
4. **量程选择**：根据实际信号电压范围选择合适的量程（±5V 或 0-10V）。
5. **差分模式**：API 默认使用差分模式（Mode=0），确保接线正确。

## 示例脚本

### 测试脚本 (`test_smacq.py`)

用于测试 API 基本功能，包含错误处理。

```bash
python test_smacq.py
```

### 使用示例 (`example_usage.py`)

展示 API 的典型用法，包括数据读取和处理。

```bash
python example_usage.py
```

## 与 KEYENCEAPI.py 的对比

| 特性 | KEYENCEAPI.py | SmacqAPI.py |
|------|--------------|-------------|
| 设备类型 | KEYENCE 距离传感器 | Smacq 采集卡 |
| 主要方法 | `get_distance()` | `read_channels()` |
| 返回值 | `(height, valid)` 元组 | `numpy.ndarray` 数组 |
| 数据模式 | 单次测量 | 多通道、多点采集 |
| 接线模式 | 固定 | 可设置（默认差分模式） |

## 故障排除

### 1. DLL 加载失败
- 检查 `resources/Smacq/` 目录中是否存在 DLL 文件
- 确认系统架构（32位/64位）与 DLL 版本匹配
- 尝试以管理员权限运行

### 2. 设备打开失败
- 检查 USB 连接是否正常
- 确认设备驱动程序已安装
- 尝试不同的 `device_id` 值

### 3. 数据读取超时
- 增加 `timeout` 参数值
- 检查采样率设置是否合理
- 确认通道选择正确

### 4. 数据值异常
- 检查量程设置是否匹配信号范围
- 确认接线方式（差分模式）
- 检查信号源是否正常

## 技术支持

如有问题，请参考：
1. `samples/Smacq/` 目录中的参考程序
2. `resources/Smacq/usb-1000.h` 头文件中的函数定义
3. `USB-1252A-Series-User-Manual.pdf` 说明书

## 版本历史

- v1.0.0 (2026-01-04): 初始版本，实现基本功能
  - 支持差分模式数据采集
  - 支持多通道选择
  - 提供完整的错误处理
  - 包含测试和示例代码
