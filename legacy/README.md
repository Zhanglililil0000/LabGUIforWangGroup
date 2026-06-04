# Legacy 归档

此目录存放 2026-06-02 重构前的旧代码，仅供参考。

## 目录说明

| 子目录 | 内容 |
|--------|------|
| `experiments/` | 旧版实验脚本（SFG/SRS/偏振扫描/波长扫描等） |
| `utils/` | 旧版工具和测试脚本 |

## 为什么归档

旧版代码存在以下问题：
- 每个实验脚本各自硬编码设备参数，修改需逐一更新
- 差分信号计算（ret1/ret2）在多个文件中重复实现
- 设备连接/断开生命周期不统一
- 无统一的错误处理和流程编排机制

新架构使用 **devices → operations → pipeline** 分层设计解决了以上问题。

## 旧文件的替代方案

| 旧文件 | 新方案 |
|--------|--------|
| SFGExperimentMain.py | 通过 Pipeline + AcquireSpectrum + SetPolarization 组合实现 |
| SRSExperimentMain.py | 同上，配置不同偏振和延迟参数 |
| SFGPolScan.py / SRSPolScan.py | 使用 SetPolarization + MotorMoveTo 循环 |
| SFGTimeScan.py / SRSTimeScan.py | 使用 DelayStageMoveTo + AcquireSpectrum 循环 |
| SpontaneousRaman.py | 使用 AcquireSpectrum 即可 |

## 注意

旧版脚本依赖 `API/` 目录下的模块，这些文件在新的 `devices/` 模块中已有更规范的封装，但部分 API 模块仍被新代码引用（如 `API.ThorlabsTLPM`、`API.KEYENCEAPI`），因此保留在 `API/` 中未移动。
