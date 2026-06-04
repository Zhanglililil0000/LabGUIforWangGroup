# SFG/SRS 实验系统 Web GUI 设计规范

**版本**: 1.0  
**日期**: 2026-06-02  
**状态**: 设计中

---

## 1. 背景与目标

### 1.1 现状

当前实验系统通过 Python 脚本直接控制设备，操作人员需要：
- 手动编辑 YAML 配置文件
- 在命令行运行 Python 脚本
- 实验中无法直观看到设备状态和采集进度
- 切换实验流程需要编辑代码或配置文件

### 1.2 目标

构建一个 Web 面板作为实验控制中心，提供：

1. **可视化设备监控** — 实时查看所有设备连接状态和读数
2. **搭积木式流程编辑** — 通过表单编排实验步骤，保存/加载模板
3. **运行状态追踪** — 清晰显示当前步骤、进度、日志
4. **灵活的参数控制** — 每步骤独立曝光时间、可选背景测量、可选稳定性检查
5. **零改动集成** — 前端仅驱动现有 `core/` + `devices/` + `operations/` 模块，不改动现有代码

### 1.3 非目标

- 远程多用户协作
- 数据分析和后处理
- 用户权限管理
- 历史数据回溯（第一版不做）

---

## 2. 整体架构

### 2.1 三层架构

```
┌──────────────────────────────────────────┐
│  Browser (HTML + JS)                      │  前端
│  - 三栏控制台布局                         │
│  - WebSocket 接收步骤进度和日志           │
│  - 无图表依赖，纯文本/状态展示            │
├──────────────────────────────────────────┤
│  FastAPI (Python)                         │  API 层
│  - REST: 配置/模板/设备 CRUD              │
│  - WebSocket: 进度/光谱/日志推送          │
│  - Pipeline 调度: 运行/暂停/停止          │
├──────────────────────────────────────────┤
│  core/ + devices/ + operations/ (不改动)   │  业务层
│  - Pipeline / ExperimentContext            │
│  - Config / SignalProcessing               │
│  - 8 类设备驱动                            │
└──────────────────────────────────────────┘
```

### 2.2 目录结构

```
CommandMode/
├── web/                       # 新增
│   ├── app.py                 # FastAPI 入口
│   ├── api/
│   │   ├── devices.py         # 设备管理接口
│   │   ├── templates.py       # 模板管理接口
│   │   ├── experiments.py     # 实验控制接口
│   │   └── ws.py              # WebSocket 处理
│   ├── static/
│   │   ├── index.html         # 主页面
│   │   ├── css/
│   │   │   └── style.css      # 样式
│   │   └── js/
│   │       ├── app.js         # 主逻辑
│   │       ├── editor.js      # 流程编辑器
│   │       └── monitor.js     # 监控面板
│   └── schemas.py             # Pydantic 数据模型
├── configs/
│   ├── templates/             # 模板存储 (YAML)
│   │   └── sfg_ssp_ppp_with_bg.yaml
│   └── ...
├── core/                      # 不改动
├── devices/                   # 不改动
├── operations/                # 不改动
└── ...
```

### 2.3 API 设计

| 方法 | 路径 | 用途 |
|------|------|------|
| `GET` | `/api/devices` | 获取所有设备状态 |
| `POST` | `/api/devices/{name}/connect` | 连接指定设备 |
| `POST` | `/api/devices/{name}/disconnect` | 断开指定设备 |
| `POST` | `/api/devices/connect-all` | 连接所有设备 |
| `POST` | `/api/devices/disconnect-all` | 断开所有设备 |
| `GET` | `/api/templates` | 模板列表 |
| `POST` | `/api/templates` | 保存模板 (YAML) |
| `DELETE` | `/api/templates/{name}` | 删除模板 |
| `POST` | `/api/experiments/run` | 启动实验 |
| `POST` | `/api/experiments/pause` | 暂停实验 |
| `POST` | `/api/experiments/stop` | 停止实验 |
| `GET` | `/api/experiments/status` | 当前实验状态 |
| `WS` | `/ws` | WebSocket 实时数据 |

### 2.4 WebSocket 消息协议

**服务端 → 客户端:**

```json
{ "type": "step_start",  "step": { "index": 0, "name": "MotorHome(vis)" }, "progress": { "current": 0, "total": 14 } }
{ "type": "step_done",   "step": { "index": 0, "name": "MotorHome(vis)" }, "elapsed_s": 1.2 }
{ "type": "step_error",  "step": { "index": 5, "name": "Acquire(ssp)" }, "message": "连接超时", "retry": 2 }
{ "type": "log",         "level": "info", "timestamp": "14:02:15", "message": "光谱仪已连接" }
{ "type": "log",         "level": "warn", "timestamp": "14:03:20", "message": "稳定性检查: 信号衰减 8%" }
{ "type": "experiment_done", "status": "completed", "steps_total": 14, "steps_done": 14, "steps_failed": 0, "elapsed": "~11min", "data_files": ["gold_ssp_main.csv", ...] }
{ "type": "device_update", "device": "vis_rotator", "position": 45.58 }
```

**客户端 → 服务端:**

```json
{ "type": "pause" }
{ "type": "stop" }
```

---

## 3. 前端设计

### 3.1 整体布局：三栏控制台

```
┌─────────────────────────────────────────────────────────────────┐
│  工具栏  [保存模板 ▼] [加载模板 ▼] │  [▶ 运行] [⏸ 暂停] [■ 停止]  │
├────────────┬──────────────────────────┬──────────────────────────┤
│  设备面板   │  实验流程编辑器           │  运行状态                 │
│  (左侧 22%) │  (中间 48%)              │  (右侧 30%)              │
├────────────┴──────────────────────────┴──────────────────────────┤
│  状态栏  ● 就绪 │ 模板: sfg_standard │ 预计耗时: ~3min              │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 左侧：设备面板

- 每个设备显示连接状态（● 绿 / ○ 灰）、关键读数
- 电机显示当前位置，延迟线显示位置
- 底部 `[全部连接]` `[全部断开]` 按钮
- 运行中设备状态自动通过 WebSocket 更新

### 3.3 中间：流程编辑器

**核心概念**: 实验流程由 **组 (Group)** 包含 **步骤 (Step)** 构成。组和步骤均可拖拽排序。

**步骤支持的类型:**

| 分类 | 步骤类型 | 可编辑参数 |
|------|---------|-----------|
| 设备操作 | MotorHome | 设备名下拉 |
| | MotorMoveTo | 设备名下拉, 角度输入框 |
| | DelayStageHome | 轴名 |
| | DelayStageMoveTo | 位置输入框 |
| 光谱采集 | SetExposure | 曝光时间 (ms) |
| | SetWavelength | 波长 (nm) |
| | AcquireSpectrum | 数据名, 曝光 (ms), 帧数 |
| | SetGrating | 光栅名称 |
| 辅助 | SetPolarization | 模式下拉 (ssp/ppp/sps/pss/spp/psp) |
| | Sleep | 秒数 |
| | LogMessage | 文本内容 |

**每步独立参数**: 所有参数在步骤行内直接编辑。不同步骤可设置不同曝光时间。

**采集组的特殊开关 (☑):**

| 开关 | 开启后自动插入的步骤 |
|------|-------------------|
| ☑ 采集背景 | `DelayStageMoveTo(背景位置)` → `AcquireSpectrum(背景)` → `DelayStageMoveTo(信号位置)` |
| ☑ 稳定性检查 | `AcquireSpectrum(check_before, 1000ms)` 插入主采集前, `AcquireSpectrum(check_after, 1000ms)` 插入主采集后 |

**编辑操作:**

```
[+ 添加步骤] → 选择步骤类型 → 自动插入当前光标位置
[+ 添加采集组] → 创建包含 SetPolarization + AcquireSpectrum 的新组
[保存为模板] → 弹出命名框 → 保存 YAML 到 configs/templates/
[加载模板] → 下拉选择模板 → 弹出样品名输入框 → 替换 {sample} 占位符 → 加载到编辑器
```

### 3.4 右侧：运行状态面板

实验运行时，右侧面板显示三个区块：

```
┌── 运行状态 ──────────────────────────────────────┐
│                                                   │
│  ┌─ 进度 ─────────────────────────────────────┐  │
│  │                                            │  │
│  │  ● 状态: 运行中                             │  │
│  │  ████████████░░░░░░░░░░░  8/14 步骤        │  │
│  │                                            │  │
│  │  当前步骤: AcquireSpectrum(gold_ssp)        │  │
│  │  步骤耗时: 1m 05s (已采集 65/100 帧)        │  │
│  │  预计剩余: ~8min                             │  │
│  └────────────────────────────────────────────┘  │
│                                                   │
│  ┌─ 步骤列表 ────────────────────────────────┐  │
│  │  ✓  MotorHome(vis_rotator)       0.8s     │  │
│  │  ✓  MotorHome(sfg_rotator)       0.9s     │  │
│  │  ✓  SetWavelength(475nm)         <0.1s    │  │
│  │  ✓  SetExposure(60000ms)         <0.1s    │  │
│  │  →  AcquireSpectrum(ssp)         1m 05s   │  │  ← 当前
│  │     AcquireSpectrum(ppp)         等待...  │  │
│  │     MotorHome(vis_rotator)       等待...  │  │
│  │     MotorHome(sfg_rotator)       等待...  │  │
│  └────────────────────────────────────────────┘  │
│                                                   │
│  ┌─ 日志 ─────────────────────────────────────┐  │
│  │  14:02:15 [✓] 光谱仪已连接                  │  │
│  │  14:02:17 [✓] vis_rotator 已连接            │  │
│  │  14:02:20 [→] 开始 SSP 采集...              │  │
│  │  14:02:21 [✓] SetPolarization(ssp)          │  │
│  │  14:02:22 [→] AcquireSpectrum 采集中...      │  │
│  └────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────┘
```

**进度条**: 顶部显示总步骤进度，当前步骤名称和时间。

**步骤列表**: 已完成步骤显示 ✓ 和耗时，当前步骤高亮闪烁，待执行步骤灰显。

**日志**: 自动滚动，运行中实时追加。稳定性检查的警告通过 `warn` 级别日志输出。

采集完成后，`experiment_done` 消息携带产出文件列表，面板底部额外显示：

```
  实验完成 (耗时 11m 03s)
  产出文件: gold_ssp_check_before.csv
           gold_ssp_main.csv
           gold_ssp_check_after.csv
           gold_ppp_main.csv
           gold_ppp_check_before.csv
           gold_ppp_check_after.csv
```

### 3.5 状态栏

- 显示当前状态（就绪/运行中/已暂停/已完成/异常）
- 当前加载的模板名
- 根据步骤数和曝光参数估算总耗时

---

## 4. 模板系统

### 4.1 模板格式

模板保存为 YAML 文件，存储在 `configs/templates/`。格式示例：

```yaml
name: "SFG SSP+PPP (含背景+稳定性)"
groups:
  - name: "初始化"
    steps:
      - { type: MotorHome, device: vis_rotator }
      - { type: MotorHome, device: sfg_rotator }
      - { type: SetWavelength, wavelength_nm: 475 }
      - { type: SetExposure, exposure_ms: 60000 }
  - name: "SSP采集"
    options:
      capture_background: true
      stability_check: true
    background_position: 100.0
    signal_position: 222.5
    steps:
      - { type: SetPolarization, mode: ssp }
      - { type: AcquireSpectrum, name: "{sample}_ssp_main", exposure_ms: 60000, frames: 100 }
      - { type: AcquireSpectrum_CheckBefore, name: "{sample}_ssp_check_before", exposure_ms: 1000, frames: 1 }
      - { type: AcquireSpectrum_CheckAfter, name: "{sample}_ssp_check_after", exposure_ms: 1000, frames: 1 }
  - name: "PPP采集"
    options:
      capture_background: false
      stability_check: true
    steps:
      - { type: SetPolarization, mode: ppp }
      - { type: AcquireSpectrum, name: "{sample}_ppp_main", exposure_ms: 60000, frames: 100 }
      - { type: AcquireSpectrum_CheckBefore, name: "{sample}_ppp_check_before", exposure_ms: 1000, frames: 1 }
      - { type: AcquireSpectrum_CheckAfter, name: "{sample}_ppp_check_after", exposure_ms: 1000, frames: 1 }
```

`{sample}` 为占位符，加载模板时弹出输入框填入实际样品名。

### 4.2 模板操作

- **加载模板**: 选择模板 → 输入样品名 → 编辑器渲染所有步骤
- **保存模板**: 当前编辑器内容 → 命名 → 写入 YAML
- **删除模板**: 从列表删除
- 预置 3-5 个常用模板 (SFG SSP+PPP、SRS 偏振扫描、时间扫描等)

---

## 5. 安全性

| 场景 | 处理方式 |
|------|---------|
| 设备未连接就点运行 | 弹窗列出缺失设备名，阻止执行 |
| 运行中关闭浏览器 | Pipeline 继续执行，WebSocket 断开但后台不中断，刷新页面后重连恢复 |
| 紧急停止 (■) | `ctx.stop()` → Pipeline 立即中断 → 所有电机归零 → 释放设备 |
| 采集超时 | 曝光时间 × 帧数 × 1.5 作为超时阈值，超时自动停止并提示 |
| 非法参数 | 前端表单校验 + 后端 Pydantic 模型校验，双重保障 |

---

## 6. 与现有代码的关系

**零改动原则**: 前端仅通过 FastAPI 封装现有模块调用，不修改任何 `core/` `devices/` `operations/` `configs/` 中的代码。

```
原来 (命令行)          →  python examples/03_sfg_simple.py
新增 (Web Panel)       →  python web/app.py
共用 (零改动)          →  core/ devices/ operations/ configs/
```

实验模板编辑器产出的 YAML 与现有配置文件格式兼容，用 `Config.load()` 即可解析。

---

## 7. 实施计划概览

| 阶段 | 内容 | 预计文件数 |
|------|------|-----------|
| Phase 1 | FastAPI 后端 + WebSocket 基础框架 | 3-4 个文件 |
| Phase 2 | 前端静态页面 + 三栏布局 + 设备面板 | 4 个文件 |
| Phase 3 | 流程编辑器 (步骤添加/删除/排序/参数编辑) | 2-3 个文件 |
| Phase 4 | 模板系统 + 运行/暂停/停止控制 | 2-3 个文件 |
| Phase 5 | 运行状态面板 (进度条、步骤列表、日志) | 1-2 个文件 |
| Phase 6 | 预置模板 + 端到端测试 | 3-5 个模板文件 |

---

## 8. 关键技术选型

| 组件 | 选择 | 原因 |
|------|------|------|
| Web 框架 | FastAPI | 异步支持好, WebSocket 原生, Pydantic 集成 |
| 前端 | 原生 HTML + JS | 无构建步骤, 轻量, 直接部署 |
| CSS | 原生 CSS（无框架） | 布局简单, 三栏 + 表单 + 列表即可 |
| 模板存储 | YAML 文件 | 与现有 Config 一致, 人类可读 |
| 实时通信 | WebSocket | 低延迟推送步骤进度和日志 |
