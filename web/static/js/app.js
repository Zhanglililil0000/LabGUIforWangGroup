/**
 * SFG Web Control Panel - Core Module (app.js)
 *
 * 提供 WebSocket 连接、消息分发、HTTP 工具、日志管理、
 * 模态对话框、时间格式化等全局基础能力。
 * 此文件最先加载，定义共享 state 对象。
 */

/* ================================================================
   Shared State Object
   ================================================================ */
const state = {
    ws: null,
    devices: [],
    flow: {
        name: "SSP+PPP实验",
        sample: "sample",
        base_path: "D:\\SFGData",
        groups: []
    },
    experiment: { running: false, current_step: 0, total_steps: 0, elapsed: "" },
    logs: [],
    _logContainer: null,
    currentMode: "sfg",
    modes: {},
};

/* ================================================================
   WebSocket
   ================================================================ */

/**
 * 建立 WebSocket 连接，自动注册消息处理和断线重连。
 * 连接地址 ws://<host>/ws，使用 location.host 动态适配部署环境。
 */
function connectWS() {
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${location.host}/ws`;

    const ws = new WebSocket(url);
    state.ws = ws;

    ws.onopen = () => {
        addLog("info", "WebSocket 已连接");
    };

    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            handleWSMessage(msg);
        } catch (e) {
            addLog("error", "WebSocket 消息解析失败: " + e.message);
        }
    };

    ws.onerror = () => {
        addLog("error", "WebSocket 连接错误");
    };

    ws.onclose = () => {
        addLog("warn", "WebSocket 已断开，2 秒后自动重连...");
        state.ws = null;
        setTimeout(connectWS, 2000);
    };
}

/**
 * WebSocket 消息分发器。
 * 根据 msg.type 路由到对应处理逻辑。
 *
 * @param {Object} msg - 从服务端接收的 JSON 消息
 */
function handleWSMessage(msg) {
    // normalize: runner's nested format → flat
    if (msg.step && typeof msg.step === "object") {
        msg.step_name = msg.step.name || "";
        msg.step_index = msg.step.index;
    }
    if (msg.progress && typeof msg.progress === "object") {
        msg.current_step = msg.progress.current;
        msg.total_steps = msg.progress.total;
    }
    // normalize: runner's flat field names → expected names
    if (msg.index != null) {
        msg.current_step = msg.index;
        msg.step_index = msg.index;
    }
    if (msg.total != null) {
        msg.total_steps = msg.total;
    }
    if (msg.name != null && msg.step_name == null) {
        msg.step_name = msg.name;
    }

    switch (msg.type) {
        case "experiment_start":
            state.experiment.running = true;
            state.experiment.current_step = 0;
            state.experiment.total_steps = msg.total_steps || 0;
            state.experiment.elapsed = "0s";
            if (typeof updateRunButtons === "function") updateRunButtons(true);
            if (typeof updateStatusBar === "function") updateStatusBar();
            if (typeof renderMonitorProgress === "function") renderMonitorProgress();
            if (msg.steps && typeof renderMonitorSteps === "function") {
                renderMonitorSteps({ steps: msg.steps });
            }
            break;

        case "step_start":
            state.experiment.running = true;
            state.experiment.current_step = msg.current_step || msg.step_index || 0;
            state.experiment.total_steps = msg.total_steps || state.experiment.total_steps;
            state.experiment.elapsed = msg.elapsed_s ? formatTime(msg.elapsed_s) : state.experiment.elapsed;
            if (typeof renderMonitorProgress === "function") renderMonitorProgress();
            if (typeof renderMonitorSteps === "function") renderMonitorSteps({
                step: msg.step_index != null ? msg.step_index : msg.current_step,
                status: "running",
                name: msg.step_name
            });
            if (typeof updateRunButtons === "function") updateRunButtons(true);
            break;

        case "step_done":
            state.experiment.current_step = msg.current_step || msg.step_index || 0;
            state.experiment.total_steps = msg.total_steps || state.experiment.total_steps;
            state.experiment.elapsed = msg.elapsed_s ? formatTime(msg.elapsed_s) : state.experiment.elapsed;
            if (typeof renderMonitorProgress === "function") renderMonitorProgress();
            if (typeof renderMonitorSteps === "function") renderMonitorSteps({
                step: msg.step_index != null ? msg.step_index : msg.current_step,
                status: "done",
                name: msg.step_name
            });
            break;

        case "step_error":
            state.experiment.current_step = msg.current_step || 0;
            state.experiment.total_steps = msg.total_steps || state.experiment.total_steps;
            addLog("error", msg.message || "步骤执行错误");
            if (typeof renderMonitorProgress === "function") renderMonitorProgress();
            if (typeof renderMonitorSteps === "function") renderMonitorSteps({
                step: msg.current_step || 0,
                status: "error",
                name: msg.step_name || ""
            });
            break;

        case "log":
            addLog(msg.level || "info", msg.message || "", msg.timestamp);
            break;

        case "experiment_done":
            state.experiment.running = false;
            state.experiment.total_steps = msg.total_steps || msg.steps_total || state.experiment.total_steps;
            state.experiment.current_step = msg.total_steps || msg.steps_total || state.experiment.total_steps;
            if (typeof renderMonitorProgress === "function") renderMonitorProgress();
            if (typeof renderMonitorSteps === "function") renderMonitorSteps({ steps: [] });
            if (typeof renderMonitorDone === "function") renderMonitorDone(msg);
            if (typeof updateRunButtons === "function") updateRunButtons(false);
            if (typeof updateStatusBar === "function") updateStatusBar();
            addLog("info", "实验完成");
            break;

        case "device_update":
            if (typeof refreshDevices === "function") refreshDevices();
            break;

        default:
            break;
    }
}

/* ================================================================
   HTTP Helper
   ================================================================ */

/**
 * 统一的 API 请求封装。
 * 自动设置 JSON Content-Type，非 2xx 响应抛出 Error。
 *
 * @param {string} path - API 路径 (如 "/api/devices")
 * @param {Object} [options={}] - fetch 额外选项
 * @returns {Promise<any>} 解析后的 JSON 响应体
 */
async function api(path, options = {}) {
    const res = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });
    if (!res.ok) {
        const err = await res.text();
        throw new Error(err);
    }
    return res.json();
}

/* ================================================================
   Log System
   ================================================================ */

/**
 * 添加一条日志到 state.logs。
 * 保留最近 200 条，自动触发 renderLogs() 刷新 UI。
 *
 * @param {string} level - 日志级别: "info" | "warn" | "error" | "debug"
 * @param {string} message - 日志内容
 * @param {string} [timestamp] - ISO 时间戳，未提供时使用当前时间
 */
function addLog(level, message, timestamp) {
    const time = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
    state.logs.push({ level, message, time });

    // 限制最大 200 条
    if (state.logs.length > 200) {
        state.logs = state.logs.slice(-200);
    }

    if (typeof renderLogs === "function") {
        renderLogs();
    }
}

/* ================================================================
   Time Formatter
   ================================================================ */

/**
 * 将秒数转换为可读格式。
 *
 * @param {number} seconds - 秒数
 * @returns {string} 格式化后的时间字符串，如 "1m 05s" 或 "0.5s"
 */
function formatTime(seconds) {
    if (seconds < 1) {
        return seconds.toFixed(1) + "s";
    }
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    if (m > 0) {
        return m + "m " + String(s).padStart(2, "0") + "s";
    }
    return s + "s";
}

/* ================================================================
   Modal Dialog
   ================================================================ */

/**
 * 显示模态对话框。
 * HTML 结构与 style.css 中的 #modal-overlay / #modal-box 定义匹配。
 *
 * @param {string} title - 对话框标题
 * @param {string} contentHtml - 对话框正文 HTML
 * @param {Function} [onConfirm] - 点击"确认"按钮的回调
 */
function showModal(title, contentHtml, onConfirm) {
    const overlay = document.getElementById("modal-overlay");
    const box = document.getElementById("modal-box");

    if (!overlay || !box) return;

    box.innerHTML = `
        <div class="modal-title">${title}</div>
        <div class="modal-body">${contentHtml}</div>
        <div class="modal-footer">
            <button class="modal-cancel">取消</button>
            <button class="modal-confirm">确认</button>
        </div>
    `;

    // 绑定按钮事件
    const confirmBtn = box.querySelector(".modal-confirm");
    const cancelBtn = box.querySelector(".modal-cancel");

    const cleanup = () => {
        if (confirmBtn) confirmBtn.removeEventListener("click", onConfirmClick);
        if (cancelBtn) cancelBtn.removeEventListener("click", onCancelClick);
    };

    const onConfirmClick = () => {
        cleanup();
        if (typeof onConfirm === "function") {
            onConfirm();
        }
        closeModal();
    };

    const onCancelClick = () => {
        cleanup();
        closeModal();
    };

    confirmBtn.addEventListener("click", onConfirmClick);
    cancelBtn.addEventListener("click", onCancelClick);

    // 点击遮罩层关闭
    overlay.onclick = () => {
        cleanup();
        closeModal();
    };

    overlay.classList.remove("hidden");
    box.classList.remove("hidden");
}

/**
 * 关闭模态对话框。
 */
function closeModal() {
    const overlay = document.getElementById("modal-overlay");
    const box = document.getElementById("modal-box");

    if (overlay) {
        overlay.classList.add("hidden");
        overlay.onclick = null;
    }
    if (box) {
        box.classList.add("hidden");
        box.innerHTML = "";
    }
}

/* ================================================================
   Experiment Mode Management
   ================================================================ */

/**
 * 从后端加载所有实验模式信息。
 * 存储到 state.modes 并渲染模式标签页。
 */
async function loadModes() {
    try {
        const data = await api("/api/modes");
        state.modes = data.modes || data;
        renderModeTabs();
        addLog("info", "实验模式信息已加载");
    } catch (e) {
        addLog("warn", "加载实验模式失败: " + e.message + "（使用默认模式）");
        state.modes = {
            sfg: { description: "SFG 和频光谱实验", devices: [], step_types: ["MotorHome","MotorMoveTo","SetExposure","SetWavelength","AcquireSpectrum","SetPolarization","Sleep","LogMessage"] }
        };
        renderModeTabs();
    }
}

/**
 * 切换到指定的实验模式。
 * 更新 UI 标签页、模式信息、设备列表、模板列表和编辑器步骤类型。
 *
 * @param {string} modeId - 模式标识符 (如 "sfg", "srs", "calibration", "debug")
 */
function switchMode(modeId) {
    if (!state.modes[modeId]) {
        addLog("warn", "未知模式: " + modeId);
        return;
    }
    state.currentMode = modeId;
    renderModeTabs();

    // 更新模式描述信息
    var info = document.getElementById("mode-info");
    if (info && state.modes[modeId]) {
        info.textContent = state.modes[modeId].description || "";
    }

    // 刷新设备列表（按模式过滤）
    if (typeof refreshDevices === "function") {
        refreshDevices();
    }

    // 标定模式使用独立面板，SFG/SRS 使用步骤编辑器
    if (modeId === "calibration") {
        if (typeof initCalibrationPanel === "function") initCalibrationPanel();
        var btnRun = document.getElementById("btn-run");
        var btnPause = document.getElementById("btn-pause");
        var btnStop = document.getElementById("btn-stop");
        if (btnRun) btnRun.style.display = "none";
        if (btnPause) btnPause.style.display = "none";
        if (btnStop) btnStop.style.display = "none";
    } else {
        if (typeof exitCalibrationPanel === "function") exitCalibrationPanel();
        var btnRun = document.getElementById("btn-run");
        var btnPause = document.getElementById("btn-pause");
        var btnStop = document.getElementById("btn-stop");
        if (btnRun) btnRun.style.display = "";
        if (btnPause) btnPause.style.display = "";
        if (btnStop) btnStop.style.display = "";
        // 更新编辑器标题
        var title = document.getElementById("editor-title");
        if (title && state.modes[modeId]) title.textContent = (state.modes[modeId].name || "实验流程");
        // 刷新模板列表（按模式过滤）
        if (typeof refreshTemplateList === "function") {
            refreshTemplateList();
        }
        // 重新渲染流程编辑器（步骤类型按模式过滤）
        if (typeof renderFlow === "function") {
            renderFlow();
        }
    }

    addLog("info", "已切换到模式: " + modeId);
}

/**
 * 获取当前模式下的可用设备列表。
 *
 * @returns {string[]} 设备名称数组
 */
function getModeDevices() {
    if (state.modes[state.currentMode] && state.modes[state.currentMode].devices) {
        return state.modes[state.currentMode].devices;
    }
    return [];
}

/**
 * 获取当前模式下的可用步骤类型列表。
 *
 * @returns {string[]} 步骤类型标识符数组
 */
function getModeStepTypes() {
    if (state.modes[state.currentMode] && state.modes[state.currentMode].step_types) {
        return state.modes[state.currentMode].step_types;
    }
    // 默认全部步骤类型
    return ["MotorHome","MotorMoveTo","SetExposure","SetWavelength","AcquireSpectrum","SetPolarization","Sleep","LogMessage"];
}

/**
 * 渲染模式标签页的激活状态。
 */
function renderModeTabs() {
    document.querySelectorAll(".mode-tab").forEach(function(tab) {
        tab.classList.toggle("active", tab.dataset.mode === state.currentMode);
    });
    var info = document.getElementById("mode-info");
    if (info && state.modes[state.currentMode]) {
        info.textContent = state.modes[state.currentMode].description || "";
    }
}

/* ================================================================
   Template List
   ================================================================ */

/**
 * 刷新模板列表。
 * 从服务端获取当前模式下的可用模板并渲染到 UI。
 */
async function refreshTemplateList(selectFilename) {
    try {
        const templates = await api("/api/templates?mode=" + state.currentMode);
        state.templates = templates;
        if (typeof renderTemplateList === "function") {
            renderTemplateList(selectFilename);
        }
        addLog("info", "模板列表已刷新");
    } catch (e) {
        addLog("error", "刷新模板列表失败: " + e.message);
    }
}

/* ================================================================
   Initialization
   ================================================================ */

/**
 * 应用入口初始化函数。
 * 在 DOMContentLoaded 时自动调用，完成 WebSocket 连接、
 * 模式加载、设备列表加载、模板列表刷新和默认流程组添加。
 */
async function initApp() {
    connectWS();

    // 先加载实验模式，后续操作依赖模式信息
    await loadModes();

    // 初始化默认模式（SFG）
    switchMode("sfg");

    if (typeof renderFlow === "function") {
        renderFlow();
    }
}

document.addEventListener("DOMContentLoaded", initApp);
