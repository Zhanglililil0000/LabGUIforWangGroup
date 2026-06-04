# SFG/SRS Web GUI 实施计划

> **Goal:** 构建 Web 控制面板，浏览器编排实验流程、监控设备、追踪运行进度。
> **Spec:** `docs/specs/2026-06-02-sfg-gui-design.md`

---

## 文件结构

```
CommandMode/web/                     # 全部新增
├── __init__.py
├── app.py                           # FastAPI 入口
├── schemas.py                       # Pydantic 模型
├── api/
│   ├── __init__.py
│   ├── devices.py                   # 设备 REST
│   ├── templates.py                 # 模板 REST
│   ├── experiments.py               # 运行控制 REST
│   └── ws.py                        # WebSocket
├── services/
│   ├── __init__.py
│   └── runner.py                    # Pipeline 线程执行器
└── static/
    ├── index.html
    ├── css/style.css
    └── js/
        ├── app.js                   # 全局状态 + WS + HTTP
        ├── devices.js               # 设备面板
        ├── editor.js                # 流程编辑器
        └── monitor.js               # 运行状态面板
```

---

## Phase 1: FastAPI 后端

### Task 1.1: 目录与依赖

- [ ] 创建 `web/`, `web/api/`, `web/services/`, `web/static/css/`, `web/static/js/`
- [ ] 安装 `fastapi uvicorn PyYAML`

```powershell
mkdir -Force 'd:\TraeProject\Project4SFG操作系统\CommandMode\web\api','...\web\services','...\web\static\css','...\web\static\js'
pip install fastapi uvicorn PyYAML
```

### Task 1.2: schemas.py

**File:** `CommandMode/web/schemas.py`

定义 `StepType`, `StepDef`, `GroupOptions`, `GroupDef`, `ExperimentFlow`, `DeviceBrief`, `RunRequest`, `ExperimentStatus`, `TemplateMeta`, `TemplateSaveRequest`。
核心：`ExperimentFlow.flatten_steps()` 根据组的 `capture_background` / `stability_check` 开关展开步骤列表。

### Task 1.3: app.py

**File:** `CommandMode/web/app.py`

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from web.api.devices import router as devices_router
from web.api.templates import router as templates_router
from web.api.experiments import router as experiments_router
from web.api.ws import router as ws_router

app = FastAPI(title="SFG Control Panel")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(devices_router, prefix="/api")
app.include_router(templates_router, prefix="/api")
app.include_router(experiments_router, prefix="/api")
app.include_router(ws_router)
app.mount("/", StaticFiles(directory=".../static", html=True))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.app:app", host="0.0.0.0", port=8080, reload=False)
```

### Task 1.4: api/devices.py

**File:** `CommandMode/web/api/devices.py`

- `GET /api/devices` — 返回 `list[DeviceBrief]`
- `POST /api/devices/{name}/connect` — 连接设备
- `POST /api/devices/{name}/disconnect` — 断开设备
- `POST /api/devices/connect-all` — 全部连接
- `POST /api/devices/disconnect-all` — 全部断开

全局 `_device_pool: dict` 由 runner 在实验启动时填充 Mock 设备。

### Task 1.5: api/templates.py

**File:** `CommandMode/web/api/templates.py`

- `GET /api/templates` → `list[TemplateMeta]`
- `GET /api/templates/{name}` → 模板内容 YAML
- `POST /api/templates` → 保存模板
- `DELETE /api/templates/{name}` → 删除模板

模板目录：`CommandMode/configs/templates/`

### Task 1.6: services/runner.py

**File:** `CommandMode/web/services/runner.py`

`ExperimentRunner` 类：
- `run(flow: ExperimentFlow)` — 在线程中构建 Pipeline 并执行
- `pause()` / `stop()` — 调用 `ctx.pause()` / `ctx.stop()`
- `set_ws_send(func)` — 注册 WebSocket 消息推送回调
- `_build_pipeline()` — 将前端 `StepDef` 列表转换为 Operation 列表
- `_create_operation()` — 根据 `StepType` 映射到具体 Operation 类
- WsLogHandler — 将 logger 输出重定向到 WebSocket

### Task 1.7: api/ws.py + api/experiments.py

**ws.py:** WebSocket 端点 `/ws`，接收客户端 `pause`/`stop` 命令，广播服务端消息。  
**experiments.py:** `POST /run`, `/pause`, `/resume`, `/stop`, `GET /status`

### Task 1.8: 后端集成测试

```powershell
cd 'd:\TraeProject\Project4SFG操作系统\CommandMode'
python web/app.py
# 另开终端
curl http://localhost:8080/api/devices        # → []
curl http://localhost:8080/api/templates      # → []
curl http://localhost:8080/api/experiments/status  # → {"running": false}
```

---

## Phase 2: 前端基础

### Task 2.1: index.html

三栏布局：工具栏 (保存/加载/运行/暂停/停止) + 设备面板 + 流程编辑器 + 运行状态 + 状态栏

### Task 2.2: style.css

- 全局：`flex column h-screen`，`#2c3e50` 工具栏，`#f0f2f5` 背景
- 三栏：`display:flex`，22%/48%/30%
- 设备卡片：`.device-card` 带左侧色条（绿=已连接）
- 组/步骤：`.group-box` 边框容器，`.step-row` 行内编辑
- 进度条：`width` 过渡动画
- 日志：深色终端风格 `.monitor-logs`
- 模态框：居中弹窗

---

## Phase 3: 流程编辑器 JS

### Task 3.1: app.js

全局状态 `state`，`connectWS()`，`handleWSMessage()`，`api()` 封装，`addLog()`，`showModal()`。

### Task 3.2: devices.js

`refreshDevices()` → 调用 `/api/devices`，渲染设备卡片。连接/断开按钮绑定。

### Task 3.3: editor.js

核心函数：
- `addGroup(name)` — 添加采集组（默认含 SetPolarization + AcquireSpectrum）
- `addStepToGroup(gi)` — 在指定组末尾添加步骤
- `deleteStep(gi, si)` / `deleteGroup(gi)`
- `updateStepParam(gi, si, key, value)` — 修改步骤参数
- `updateStepType(gi, si, newType)` — 更换步骤类型并重置参数
- `toggleGroupOption(gi, option)` — 切换背景/稳定性检查
- `renderFlow()` — 全量重绘编辑器 HTML

步骤行根据类型渲染不同参数输入：设备下拉、角度数字、曝光时间、波长、帧数、偏振模式下拉等。

模板保存/加载：序列化 `state.flow` → 调用 `/api/templates` → 模态框输入名称/样品名。

---

## Phase 4: 运行状态面板 JS

### Task 4.1: monitor.js

- `renderMonitorProgress()` — 进度条 + 当前步骤名 + 耗时
- `renderMonitorSteps(msg)` — 步骤列表（✓ done / → current / 灰 pending）
- `renderLogs()` — 日志自动滚动到底部
- `renderMonitorDone(msg)` — 实验完成提示 + 产出文件列表
- `updateRunButtons(running)` — 运行/暂停/停止按钮启用状态切换
- `updateStatusBar()` — 状态栏：状态指示、模板名、预计耗时

---

## Phase 5: 预置模板

### Task 5.1: 创建模板 YAML

**Files:**
- `configs/templates/sfg_ssp_ppp.yaml` — SSP+PPP 基础实验
- `configs/templates/sfg_ssp_ppp_with_bg.yaml` — 含背景测量
- `configs/templates/sfg_pol_scan.yaml` — 偏振扫描
- `configs/templates/srs_time_scan.yaml` — SRS 时间扫描

### Task 5.2: 端到端测试

```powershell
# 启动服务器
python web/app.py

# 浏览器打开 http://localhost:8080
# 1. 加载模板 → 选择 sfg_ssp_ppp → 输入样品名 "test"
# 2. 编辑流程 → 勾选稳定性检查
# 3. 点击运行 → 观察右侧进度条/步骤列表/日志
# 4. 点击停止 → 确认实验停止 + 日志显示
```

---

## Phase 6: 验证

- [ ] `pytest tests/` — 6 个原有测试仍然通过
- [ ] `python web/app.py` — 服务器启动正常
- [ ] 浏览器访问 `http://localhost:8080` — 三栏布局正确渲染
- [ ] 添加/删除步骤、修改参数 — 编辑器交互正常
- [ ] 保存模板 → 刷新页面 → 加载模板 — 数据保持
- [ ] 运行 → 进度条前进 → 日志滚动 → 完成提示 — 全流程正常
