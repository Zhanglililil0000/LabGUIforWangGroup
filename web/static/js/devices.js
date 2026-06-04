/**
 * SFG Web Control Panel - Device Panel Module (devices.js)
 *
 * 设备面板管理：设备列表刷新、渲染展示（含序列号/端口等详情）、
 * LightField 预设显示、批量连接/断开。
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

/** 渲染设备面板 — 全部使用 DOM 操作避免 innerHTML += 覆盖问题。 */
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
        emptyDiv.textContent = "未检测到设备 — 请先点击「全部连接」";
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

        // 构建设备信息行
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

        card.innerHTML =
            '<div class="device-name">' +
                '<span class="device-dot ' + (connected ? "on" : "off") + '"></span>' +
                escapeHtml(d.name) +
            '</div>' +
            '<div class="device-info">' +
                escapeHtml(d.type) + ' | ' + (connected ? '已连接' : '未连接') + posText +
            '</div>' +
            (detailsHtml ? '<div class="device-details">' + detailsHtml + '</div>' : '');

        container.appendChild(card);
    });
}

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

/* ================================================================
   Button Bindings
   ================================================================ */

document.addEventListener("DOMContentLoaded", function () {
    var btnConnectAll = document.getElementById("btn-connect-all");
    var btnDisconnectAll = document.getElementById("btn-disconnect-all");

    if (btnConnectAll) {
        btnConnectAll.addEventListener("click", async function () {
            try {
                await api("/api/devices/connect-all", { method: "POST" });
                addLog("info", "全部设备连接请求已发送");
                await refreshDevices();
            } catch (e) {
                addLog("error", "全部连接失败: " + e.message);
            }
        });
    }

    if (btnDisconnectAll) {
        btnDisconnectAll.addEventListener("click", async function () {
            try {
                await api("/api/devices/disconnect-all", { method: "POST" });
                addLog("info", "全部设备断开请求已发送");
                await refreshDevices();
            } catch (e) {
                addLog("error", "全部断开失败: " + e.message);
            }
        });
    }
});
