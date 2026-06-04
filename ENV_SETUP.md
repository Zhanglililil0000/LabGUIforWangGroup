# MultimodalHRSystem — 环境配置指南

> 在新实验室电脑上部署本系统前，请按本文档完成所有环境的安装和配置。

---

## 目录

1. [硬件清单](#硬件清单)
2. [系统软件安装](#系统软件安装)
3. [Python 环境配置](#python-环境配置)
4. [安装 pip 依赖](#安装-pip-依赖)
5. [配置设备参数](#配置设备参数)
6. [启动验证](#启动验证)
7. [设备驱动依赖速查表](#设备驱动依赖速查表)
8. [故障排查](#故障排查)
9. [维护建议](#维护建议)

---

## 硬件清单

| 设备 | 品牌/型号 | 通信方式 | 连接接口 |
|------|----------|---------|---------|
| 光谱仪 CCD | Princeton PyLon / ProEM | LightField 软件 | USB |
| 可见光旋转台 | Thorlabs CageRotator / KCube | Kinesis 驱动 | USB |
| SFG 旋转台 | Thorlabs CageRotator / KCube | Kinesis 驱动 | USB |
| Raman 旋转台 | Thorlabs CageRotator / KCube | Kinesis 驱动 | USB |
| 光学延迟线 | Feinixs / SMC 控制器 | 串口 (RS-232) | COM4 |
| 光功率计 | Thorlabs PM100D | VISA 驱动 | USB |
| 距离传感器 | KEYENCE CL-3000 | USB 驱动 | USB |
| 垂直位移台 | 串口电机 | RS-232 | COM9 |
| 采集卡 | Smacq USB-1000 | USB 驱动 | USB |

> 如果只运行部分实验模式，硬件可相应减少。仅做 SFG 实验只需要：光谱仪 + VIS/SFG 旋转台 + 延迟线。

---

## 系统软件安装

### 必装软件（按顺序）

#### 1. Python 3.10（64-bit）

- **必须使用 64 位版本**（硬件 DLL 为 64-bit）
- 推荐使用 Anaconda 管理 Python 环境（见下文）

#### 2. .NET Runtime

Thorlabs Kinesis、LightField、延迟线控制器均通过 .NET 调用。

- **.NET Framework 4.8**（推荐）：https://dotnet.microsoft.com/download/dotnet-framework/net48

#### 3. Thorlabs Kinesis Motion Control

- 下载：https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=Motion_Control
- 安装后重启电脑

#### 4. Princeton Instruments LightField

- 安装 LightField（随相机附带或 PI 官网下载）
- 启动 LightField → 创建实验预设 → 记录预设名称（默认: `HRBBSFGVS-PyLon`）

#### 5. 各设备 USB/串口驱动

- SMC/Newport 延迟线 → FTDI/CH340 USB 转串口驱动
- KEYENCE CL-3000 → 随传感器附带
- Smacq USB-1000 → 随采集卡附带
- Thorlabs PM100D → 安装 Thorlabs 光学测量软件包

---

## Python 环境配置

### 使用 Anaconda（推荐）

本系统已在 Anaconda 默认 Python 3.7 环境下验证，**需要单独创建 Python 3.10 环境**。

```powershell
# 1. 创建 py310 环境
conda create -n py310 python=3.10 -y

# 2. 激活环境
conda activate py310

# 3. 验证 Python 版本
python --version
# Python 3.10.x
```

### 安装 conda 可管理的包（优先用 conda）

```powershell
conda activate py310
conda install numpy matplotlib pyyaml pyserial -y
```

### 安装 pip 依赖

```powershell
conda activate py310
cd d:\TraeProject\Project4SFG操作系统\MultimodalHRSystem_V0
pip install -r requirements.txt
```

### 验证安装

```powershell
python -c "import numpy, yaml, fastapi, uvicorn, pydantic, serial; print('All OK')"
```

---

## 安装 pip 依赖

```powershell
conda activate py310
cd d:\TraeProject\Project4SFG操作系统\MultimodalHRSystem_V0
pip install -r requirements.txt
```

**requirements.txt 内容：**

| 包名 | 用途 | 必需 |
|------|------|:--:|
| `numpy` | 科学计算、信号处理 | ✅ |
| `matplotlib` | 数据可视化 | |
| `pyyaml` | 配置文件解析 | ✅ |
| `fastapi` | Web 框架 | ✅ |
| `pydantic` | 数据模型验证 | ✅ |
| `uvicorn` | Web 服务器 | ✅ |
| `websockets` | WebSocket 实时推送 | ✅ |
| `python-multipart` | 文件上传支持 | ✅ |
| `pyserial` | 串口通信（垂直位移台） | |
| `pythonnet` | .NET 互操作（Thorlabs/LightField/延迟线） | ✅ |
| `pyAndorSpectrograph` | Andor 相机（需单独安装 Andor SDK） | |
| `pyAndorSDK2` | Andor SDK（需单独安装 Andor SDK） | |

---

## 配置设备参数

### 1. 获取设备信息

先连接所有硬件：

| 设备 | 查看方式 |
|------|---------|
| Thorlabs 旋转台 | Kinesis → 设备面板 → Serial Number |
| 延迟线 | Windows 设备管理器 → 端口 (COM and LPT) |
| 光功率计 | Thorlabs 光学测量软件 |
| 垂直位移台 | Windows 设备管理器 → 端口 (COM and LPT) |

### 2. 修改 `configs/devices.yaml`

```yaml
devices:
  vis_rotator:
    serial: "你的VIS电机序列号"      # ← 改这里

  sfg_rotator:
    serial: "你的SFG电机序列号"      # ← 改这里

  raman_rotator:
    serial: "你的Raman电机序列号"    # ← 改这里

  delay_stage:
    port: "你的COM口号"              # ← 改这里

  spectrometer:
    experiment_name: "你的LightField预设名"   # ← 改这里

  vertical_stage:
    port: "你的COM口号"              # ← 改这里
```

---

## 启动验证

### 1. 命令行启动

```powershell
conda activate py310
cd d:\TraeProject\Project4SFG操作系统\MultimodalHRSystem_V0
python -m uvicorn web.app:app --host 0.0.0.0 --port 8080
```

### 2. 一键启动（双击 bat 文件）

双击 **`start_web.bat`**，脚本会自动激活 `py310` 环境并安装/更新依赖。

浏览器打开：**http://localhost:8080**

### 3. 功能验证清单

- [ ] 浏览器正常显示控制台界面
- [ ] 切换 SFG / SRS / 系统调试 标签，界面正确切换
- [ ] 点击「全部连接」→ 设备面板显示绿色圆点
- [ ] 下拉框选择模板 → 实验流程自动加载
- [ ] 编辑步骤参数 → 数值正确保存
- [ ] 保存新模板 → 下拉框中出现新模板名

---

## 设备驱动依赖速查表

```
Python 代码
   │
   ├── pythonnet (clr) ─── Thorlabs Kinesis .NET     → 3 台旋转台
   │                    ─── LightField .NET Automation  → 光谱仪 CCD
   │                    ─── ftcorecs.dll (feinixs)    → 延迟线
   │
   ├── ctypes          ─── usb-1000.dll (Smacq)      → 采集卡
   │                    ─── TLPM_64.dll (VISA)        → 光功率计
   │                    ─── CL3_IF.dll (KEYENCE)      → 距离传感器
   │
   └── pyserial        ─── COM 口                      → 垂直位移台
```

---

## 故障排查

### conda activate py310 失败

```powershell
# 检查已有环境
conda env list

# 如果不存在，创建
conda create -n py310 python=3.10 -y
```

### pip 报错缺少 C++ 编译工具

`pythonnet` 可能需要编译。优先用预编译 wheel：
```powershell
pip install --only-binary :all: pythonnet
```

### ImportError: No module named 'clr'

```powershell
conda activate py310
pip install pythonnet
```

### 旋转台 / 光谱仪 / 延迟线无法连接

1. 确认 Kinesis / LightField 已安装
2. 确认 .NET Framework 4.8 已安装
3. 确认 pythonnet 已安装：`python -c "import clr; print('OK')"`
4. 检查 `configs/devices.yaml` 序列号/COM 口

### DLL 找不到

确保在项目根目录运行，`API/` 中的路径是相对路径：
```powershell
# 错误
cd C:\Users\admin
python d:\...\MultimodalHRSystem_V0\web\app.py

# 正确
cd d:\TraeProject\Project4SFG操作系统\MultimodalHRSystem_V0
python -m uvicorn web.app:app --host 0.0.0.0 --port 8080
```

---

## 维护建议

| 项目 | 频率 | 说明 |
|------|------|------|
| 数据备份 | 每周 | 备份 `D:\SFGData` 下的实验数据 |
| DLL 备份 | 一次性 | 备份 `resources/` 目录 |
| 软件更新 | 重大版本 | 关注 LightField 和 Kinesis 更新 |

---

*使用手册：IDE 模式 [README.md](README.md) | Web GUI 模式 [web/README.md](web/README.md)*
