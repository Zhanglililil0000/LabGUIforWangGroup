/**
 * SFG Web Control Panel - Device Panel Module (devices.js)
 *
 * 设备面板管理：设备列表刷新、渲染展示（含序列号/端口等详情）、
 * LightField 预设显示、每个设备独立的连接/断开按钮。
 * 依赖 app.js 中的 state、api、addLog、getModeDevices、currentMode。
 */

/* ================================================================
   Device Data
   ================================================================ */

/** 从后端获取设备列表并更新 state.devices，然后刷新 UI。 */
async function refreshDevices() {
    try {
        var url = "/api/devices";
        if (state.currentMode) url += "?mode=" + state.currentMode;
        const data = await api(url);
        state.devices = data;
    } catch (e) {
        addLog("error", "获取设备列表失败: " + e.message);
    }
    renderDevices();
}

/* ================================================================
   Device Rendering
   ================================================================ */

/** 渲染设备面板 — 每个设备卡片带有独立的连接/断开按钮。 */
function renderDevices() {
    var container = document.getElementById("device-list");
    if (!container) return;
    container.innerHTML = "";

    // ── LightField 预设信息 ──
    var modeConfig = (state.modes && state.modes[state.currentMode]) ? state.modes[state.currentMode] : null;
    if (modeConfig && modeConfig.lightfield_experiment) {
        var lfDiv = document.createElement("div");
        lfDiv.style.cssText = "padding:6px 12px;margin-bottom:8px;background:#eaf2f8;border-radius:4px;font-size:12px;color:#2c3e50;";
        lfDiv.innerHTML = '<strong>LightField 预设:</strong> ' + escapeHtml(modeConfig.lightfield_experiment);
        container.appendChild(lfDiv);
    }

    // ── 模式标签 ──
    var modeDevices = (typeof getModeDevices === "function") ? getModeDevices() : [];
    if (modeConfig) {
        var modeDiv = document.createElement("div");
        modeDiv.style.cssText = "padding:4px 12px;margin-bottom:10px;font-size:12px;color:#888;";
        modeDiv.textContent = modeConfig.description || (state.currentMode + " mode");
        container.appendChild(modeDiv);
    }

    if (!state.devices || state.devices.length === 0) {
        var emptyDiv = document.createElement("div");
        emptyDiv.style.cssText = "color:#999;padding:12px;text-align:center;font-size:13px;";
        emptyDiv.textContent = "未检测到设备";
        container.appendChild(emptyDiv);
        return;
    }

    // 按模式过滤（兜底，服务端已过滤）
    var filtered = state.devices;
    if (modeDevices.length > 0) {
        filtered = state.devices.filter(function (d) { return modeDevices.indexOf(d.name) !== -1; });
    }

    filtered.forEach(function (d) {
        var connected = !!d.connected;
        var card = document.createElement("div");
        card.className = "device-card" + (connected ? " connected" : "");

        // 详细信息行
        var detailsHtml = "";
        if (d.details && Object.keys(d.details).length > 0) {
            var parts = [];
            for (var k in d.details) {
                if (d.details.hasOwnProperty(k)) {
                    parts.push(k + ": " + d.details[k]);
                }
            }
            detailsHtml = parts.join(" &nbsp;|&nbsp; ");
        }
        var posText = (d.position !== null && d.position !== undefined) ? " 位置: " + d.position : "";

        // 设备主体信息
        var infoDiv = document.createElement("div");
        infoDiv.className = "device-info-row";

        var nameDiv = document.createElement("div");
        nameDiv.className = "device-name";
        nameDiv.innerHTML = '<span class="device-dot ' + (connected ? "on" : "off") + '"></span>' + escapeHtml(d.name);
        infoDiv.appendChild(nameDiv);

        // 连接/断开按钮
        var btn = document.createElement("button");
        btn.className = "device-card-btn " + (connected ? "btn-disconnect" : "btn-connect");
        btn.textContent = connected ? "断开" : "连接";
        btn.dataset.deviceName = d.name;
        btn.addEventListener("click", function(e) {
            e.stopPropagation();
            toggleDevice(this.dataset.deviceName, !connected);
        });
        infoDiv.appendChild(btn);

        card.appendChild(infoDiv);

        // 类型与状态行
        var infoLine = document.createElement("div");
        infoLine.className = "device-info";
        infoLine.innerHTML = escapeHtml(d.type) + ' | ' + (connected ? '已连接' : '未连接') + posText;
        card.appendChild(infoLine);

        // 详细信息行
        if (detailsHtml) {
            var detailsLine = document.createElement("div");
            detailsLine.className = "device-details";
            detailsLine.innerHTML = detailsHtml;
            card.appendChild(detailsLine);
        }

        container.appendChild(card);
    });
}


/* ================================================================
   Device Toggle
   ================================================================ */

/**
 * 切换单个设备的连接/断开状态。
 *
 * @param {string} name - 设备名称
 * @param {boolean} connect - true 连接, false 断开
 */
async function toggleDevice(name, connect) {
    var action = connect ? "connect" : "disconnect";
    try {
        await api("/api/devices/" + name + "/" + action, { method: "POST" });
        addLog("info", "设备 " + name + " " + (connect ? "已连接" : "已断开"));
        await refreshDevices();
    } catch (e) {
        addLog("error", name + " " + (connect ? "连接" : "断开") + "失败: " + e.message);
    }
}


/* ================================================================
   Utility
   ================================================================ */

/**
 * 基本 HTML 转义，防止 XSS。
 */
function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}