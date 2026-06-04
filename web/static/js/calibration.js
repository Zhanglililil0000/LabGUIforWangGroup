/**
 * calibration.js - 系统调试选项卡（标定扫描）
 *
 * 三种标定模式：
 *   1. VIS 偏振标定 — vis_rotator + power_meter，角度扫描 + 功率测量
 *   2. SFG 偏振标定 — sfg_rotator + 光谱仪，角度扫描 + 光谱采集
 *   3. 高度扫描    — 距离传感器 + 光谱仪，高度扫描 + 光谱采集
 *
 * 与 SFG/SRS 不同，标定模式不使用步骤编辑器，
 * 而是设置扫描参数后直接运行。
 */

/* ──────────────── 标定状态 ──────────────── */
const calState = {
    /** "vis_pol" | "sfg_pol" | "height" */
    type: "vis_pol",
    running: false,
    /** 扫描结果 { x:[], y:[] } */
    result: null,
    /** 实时进度 */
    progress: { current: 0, total: 0 },
};

/* ──────────────── 面板切换 ──────────────── */

/**
 * 初始化标定面板（切换到系统调试模式时调用）。
 */
function initCalibrationPanel() {
    // 隐藏 SFG/SRS 的步骤编辑器
    var flowContainer = document.getElementById("flow-container");
    var editorActions = document.getElementById("editor-actions");
    if (flowContainer) flowContainer.style.display = "none";
    if (editorActions) editorActions.style.display = "none";

    // 显示标定面板
    var calPanel = document.getElementById("calibration-panel");
    if (calPanel) calPanel.style.display = "";

    // 模板选择器清空（标定模式不用模板）
    var sel = document.getElementById("select-template");
    if (sel) sel.innerHTML = '<option value="">-- 标定模式 --</option>';
    var btnLoad = document.getElementById("btn-delete-template");
    if (btnLoad) btnLoad.style.display = "none";
    var btnSave = document.getElementById("btn-save-template");
    if (btnSave) btnSave.style.display = "none";

    renderCalibrationForm();
}

/**
 * 退出标定模式（切换到 SFG/SRS 时调用）。
 */
function exitCalibrationPanel() {
    var flowContainer = document.getElementById("flow-container");
    var editorActions = document.getElementById("editor-actions");
    if (flowContainer) flowContainer.style.display = "";
    if (editorActions) editorActions.style.display = "";

    var calPanel = document.getElementById("calibration-panel");
    if (calPanel) calPanel.style.display = "none";

    var btnDelete = document.getElementById("btn-delete-template");
    if (btnDelete) btnDelete.style.display = "";
    var btnSave = document.getElementById("btn-save-template");
    if (btnSave) btnSave.style.display = "";
}

/* ──────────────── 表单渲染 ──────────────── */

/**
 * 根据当前标定类型渲染参数表单。
 */
function renderCalibrationForm() {
    var form = document.getElementById("cal-form");
    if (!form) return;

    var t = calState.type;

    // 通用参数
    var html = '<div class="cal-form-row"><label class="cal-label">标定类型</label>';
    html += '<select id="cal-type" onchange="onCalTypeChange()">';
    html += '<option value="vis_pol"' + (t === "vis_pol" ? " selected" : "") + '>VIS 偏振标定</option>';
    html += '<option value="sfg_pol"' + (t === "sfg_pol" ? " selected" : "") + '>SFG 偏振标定</option>';
    html += '<option value="height"' + (t === "height" ? " selected" : "") + '>高度扫描</option>';
    html += '<option value="delay_scan"' + (t === "delay_scan" ? " selected" : "") + '>延迟扫描</option>';
    html += '</select></div>';

    if (t === "vis_pol") {
        html += _calParamNumber("起始角度 (°)", "start", 20, 0, 360, 0.1);
        html += _calParamNumber("终止角度 (°)", "end", 130, 0, 360, 0.1);
        html += _calParamNumber("步长 (°)", "step", 1, 0.1, 90, 0.1);
        html += _calParamNumber("每步测量次数", "samples", 500, 1, 10000, 1);
        html += _calParamNumber("功率计波长 (nm)", "wavelength", 532, 200, 1100, 1);
        html += _calParamNumber("移动后等待 (s)", "settle_time", 1.0, 0, 60, 0.1);
    } else if (t === "sfg_pol") {
        html += _calParamNumber("VIS 固定角度 (°)", "vis_angle", 90.58, 0, 360, 0.01);
        html += _calParamNumber("SFG 起始角度 (°)", "start", 10, 0, 360, 0.1);
        html += _calParamNumber("SFG 终止角度 (°)", "end", 110, 0, 360, 0.1);
        html += _calParamNumber("步长 (°)", "step", 1, 0.1, 90, 0.1);
        html += _calParamNumber("曝光时间 (ms)", "exposure_ms", 60000, 100, 3600000, 100);
        html += _calParamNumber("中心波长 (nm)", "wavelength", 475, 200, 1100, 1);
        html += _calParamNumber("移动后等待 (s)", "settle_time", 1.0, 0, 60, 0.1);
    } else if (t === "height") {
        html += _calParamNumber("起始高度", "start", 400, 0, 99999, 1);
        html += _calParamNumber("终止高度", "end", 1500, 1, 99999, 1);
        html += _calParamNumber("步长", "step", 10, 1, 10000, 1);
        html += _calParamNumber("曝光时间 (ms)", "exposure_ms", 1000, 100, 3600000, 100);
        html += _calParamNumber("中心波长 (nm)", "wavelength", 475, 200, 1100, 1);
        html += _calParamNumber("高度误差阈值 (um)", "height_tolerance", 5, 1, 100, 1);
    } else if (t === "delay_scan") {
        html += _calParamNumber("起始位置", "start", 100, 0, 9999, 1);
        html += _calParamNumber("终止位置", "end", 200, 1, 9999, 1);
        html += _calParamNumber("步长", "step", 5, 1, 1000, 1);
        html += _calParamNumber("曝光时间 (ms)", "exposure_ms", 60000, 100, 3600000, 100);
        html += _calParamNumber("中心波长 (nm)", "wavelength", 475, 200, 1100, 1);
        html += _calParamNumber("移动后等待 (s)", "settle_time", 1.0, 0, 60, 0.1);
    }

    // 通用参数
    html += _calParamText("保存路径", "filepath", "D:\\CalibrationData", 30);
    html += _calParamText("数据文件名", "filename", "calibration", 20);

    form.innerHTML = html;

    // 更新扫描点数估算
    updateScanEstimate();
}

/** 数值参数输入 */
function _calParamNumber(label, key, defaultVal, min, max, step) {
    var val = calState[key] != null ? calState[key] : defaultVal;
    calState[key] = val;
    return '<div class="cal-form-row">' +
        '<label class="cal-label">' + label + '</label>' +
        '<input type="number" class="cal-input" id="cal-' + key + '" value="' + val + '"' +
        ' min="' + min + '" max="' + max + '" step="' + step + '"' +
        ' onchange="calState[\'' + key + '\']=this.valueAsNumber;updateScanEstimate()" />' +
        '</div>';
}

/** 文本参数输入 */
function _calParamText(label, key, defaultVal, size) {
    var val = calState[key] || defaultVal;
    calState[key] = val;
    return '<div class="cal-form-row">' +
        '<label class="cal-label">' + label + '</label>' +
        '<input type="text" class="cal-input" id="cal-' + key + '" value="' + val + '"' +
        ' size="' + size + '" onchange="calState[\'' + key + '\']=this.value" />' +
        '</div>';
}

/** 标定类型切换 */
function onCalTypeChange() {
    var sel = document.getElementById("cal-type");
    if (!sel) return;
    calState.type = sel.value;
    calState.result = null;
    renderCalibrationForm();
    renderCalResult();
}

/** 更新扫描点数估算 */
function updateScanEstimate() {
    var el = document.getElementById("cal-estimate");
    if (!el) return;
    var start = calState.start || 0;
    var end = calState.end || 0;
    var step = calState.step || 1;
    if (step <= 0) step = 1;
    var count = Math.floor(Math.abs(end - start) / step) + 1;
    el.textContent = "预计扫描 " + count + " 个点";
}

/* ──────────────── 扫描控制 ──────────────── */

/**
 * 启动标定扫描。
 */
async function startCalibration() {
    if (calState.running) return;

    calState.running = true;
    calState.result = null;
    renderCalResult();
    updateCalButtons(true);

    var payload = {
        type: calState.type,
        start: calState.start,
        end: calState.end,
        step: calState.step,
        filepath: calState.filepath || "D:\\CalibrationData",
        filename: calState.filename || "calibration",
    };

    if (calState.type === "vis_pol") {
        payload.samples = calState.samples || 500;
        payload.wavelength_nm = calState.wavelength || 532;
        payload.settle_time = calState.settle_time || 1;
    } else if (calState.type === "sfg_pol") {
        payload.vis_angle = calState.vis_angle || 90.58;
        payload.exposure_ms = calState.exposure_ms || 60000;
        payload.wavelength_nm = calState.wavelength || 475;
        payload.settle_time = calState.settle_time || 1;
    } else if (calState.type === "height") {
        payload.exposure_ms = calState.exposure_ms || 1000;
        payload.wavelength_nm = calState.wavelength || 475;
        payload.height_tolerance = calState.height_tolerance || 5;
    } else if (calState.type === "delay_scan") {
        payload.exposure_ms = calState.exposure_ms || 60000;
        payload.wavelength_nm = calState.wavelength || 475;
        payload.settle_time = calState.settle_time || 1;
    }

    addLog("info", "开始" + getCalTypeName() + "...");

    try {
        var resp = await api("/api/calibration/scan", {
            method: "POST",
            body: JSON.stringify(payload),
        });

        if (resp.status === "ok") {
            calState.result = resp.result;
            addLog("info", getCalTypeName() + "完成，共 " + (resp.result.x ? resp.result.x.length : 0) + " 个点");
        } else {
            addLog("error", resp.message || "扫描失败");
        }
    } catch (e) {
        addLog("error", "扫描出错: " + e.message);
    } finally {
        calState.running = false;
        updateCalButtons(false);
        renderCalResult();
    }
}

/** 停止扫描 */
async function stopCalibration() {
    try {
        await api("/api/calibration/stop", { method: "POST" });
        calState.running = false;
        updateCalButtons(false);
        addLog("info", "标定扫描已请求停止");
    } catch (e) {
        addLog("error", "停止失败: " + e.message);
    }
}

function updateCalButtons(running) {
    var btnStart = document.getElementById("btn-cal-start");
    var btnStop = document.getElementById("btn-cal-stop");
    if (btnStart) btnStart.disabled = running;
    if (btnStop) btnStop.disabled = !running;
}

function getCalTypeName() {
    if (calState.type === "vis_pol") return "VIS偏振标定";
    if (calState.type === "sfg_pol") return "SFG偏振标定";
    if (calState.type === "height") return "高度扫描";
    return "延迟扫描";
}

/* ──────────────── 结果显示 ──────────────── */

/**
 * 渲染标定结果区域。
 */
function renderCalResult() {
    var el = document.getElementById("cal-result");
    if (!el) return;

    if (!calState.result || !calState.result.x) {
        el.innerHTML = '<div class="cal-empty">运行扫描后在此显示结果图表和数据</div>';
        return;
    }

    var x = calState.result.x;
    var y = calState.result.y;
    var xLabel = calState.result.x_label || "X";
    var yLabel = calState.result.y_label || "Y";

    // 计算简单统计数据
    var yMax = Math.max.apply(null, y);
    var yMin = Math.min.apply(null, y);
    var yAvg = (y.reduce(function (a, b) { return a + b; }, 0) / y.length).toFixed(4);

    var html = '<div class="cal-result-stats">';
    html += '<span>点数: ' + x.length + '</span>';
    html += '<span>范围: ' + yMin.toFixed(4) + ' ~ ' + yMax.toFixed(4) + '</span>';
    html += '<span>均值: ' + yAvg + '</span>';
    html += '</div>';

    // 简易 SVG 图表
    if (x.length > 1) {
        html += '<div class="cal-chart-wrap"><svg class="cal-chart" viewBox="0 0 400 200">';
        html += _buildSvgChart(x, y, xLabel, yLabel);
        html += '</svg></div>';
    }

    // CSV 下载按钮
    html += '<div class="cal-actions">';
    html += '<button onclick="downloadCalCSV()" class="btn-download">📥 下载 CSV 数据</button>';
    html += '</div>';

    el.innerHTML = html;
}

/**
 * 构建简易 SVG 折线图。
 */
function _buildSvgChart(x, y, xLabel, yLabel) {
    var w = 380, h = 170, padL = 50, padR = 10, padT = 10, padB = 30;
    var cw = w - padL - padR;
    var ch = h - padT - padB;

    var xMin = Math.min.apply(null, x);
    var xMax = Math.max.apply(null, x);
    var yMin = Math.min.apply(null, y);
    var yMax = Math.max.apply(null, y);

    if (xMin === xMax) xMax = xMin + 1;
    if (yMin === yMax) yMax = yMin + 1;

    var xScale = function (v) { return padL + (v - xMin) / (xMax - xMin) * cw; };
    var yScale = function (v) { return padT + ch - (v - yMin) / (yMax - yMin) * ch; };

    var path = "M" + x.map(function (v, i) { return xScale(v).toFixed(1) + "," + yScale(y[i]).toFixed(1); }).join(" L");

    var html = '';

    // 网格线
    for (var i = 0; i <= 4; i++) {
        var yv = yMin + (yMax - yMin) * i / 4;
        var yy = yScale(yv);
        html += '<line x1="' + padL + '" y1="' + yy + '" x2="' + (padL + cw) + '" y2="' + yy + '" stroke="#e0e0e0" stroke-width="0.5"/>';
        html += '<text x="' + (padL - 5) + '" y="' + (yy + 4) + '" text-anchor="end" font-size="9" fill="#888">' + yv.toExponential(1) + '</text>';
    }

    // Y轴标签
    html += '<text x="' + (padL - 46) + '" y="' + (padT + ch / 2) + '" text-anchor="middle" font-size="10" fill="#666" transform="rotate(-90,' + (padL - 46) + ',' + (padT + ch / 2) + ')">' + yLabel + '</text>';

    // X轴标签
    html += '<text x="' + (padL + cw / 2) + '" y="' + (h - 3) + '" text-anchor="middle" font-size="10" fill="#666">' + xLabel + '</text>';

    // X轴刻度
    for (var i = 0; i <= 4; i++) {
        var xv = xMin + (xMax - xMin) * i / 4;
        var xx = xScale(xv);
        html += '<line x1="' + xx + '" y1="' + (padT + ch) + '" x2="' + xx + '" y2="' + (padT + ch + 4) + '" stroke="#888" stroke-width="0.5"/>';
        html += '<text x="' + xx + '" y="' + (padT + ch + 15) + '" text-anchor="middle" font-size="9" fill="#888">' + xv.toFixed(0) + '</text>';
    }

    // 轴线
    html += '<line x1="' + padL + '" y1="' + padT + '" x2="' + padL + '" y2="' + (padT + ch) + '" stroke="#888" stroke-width="1"/>';
    html += '<line x1="' + padL + '" y1="' + (padT + ch) + '" x2="' + (padL + cw) + '" y2="' + (padT + ch) + '" stroke="#888" stroke-width="1"/>';

    // 数据线
    html += '<polyline points="' + x.map(function (v, i) { return xScale(v).toFixed(1) + "," + yScale(y[i]).toFixed(1); }).join(" ") + '" fill="none" stroke="#3498db" stroke-width="1.5"/>';

    // 数据点
    html += x.map(function (v, i) {
        return '<circle cx="' + xScale(v).toFixed(1) + '" cy="' + yScale(y[i]).toFixed(1) + '" r="2" fill="#3498db"/>';
    }).join("");

    return html;
}

/* ──────────────── CSV 下载 ──────────────── */

/**
 * 下载标定数据为 CSV 文件。
 */
function downloadCalCSV() {
    if (!calState.result || !calState.result.x) return;

    var x = calState.result.x;
    var y = calState.result.y;
    var xLabel = calState.result.x_label || "X";
    var yLabel = calState.result.y_label || "Y";

    var csv = xLabel + "," + yLabel + "\n";
    for (var i = 0; i < x.length; i++) {
        csv += x[i] + "," + y[i] + "\n";
    }

    var filename = (calState.filename || "calibration") + ".csv";
    var blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    addLog("info", "CSV 已下载: " + filename);
}

/* ──────────────── 按钮绑定 ──────────────── */

document.addEventListener("DOMContentLoaded", function () {
    var btnStart = document.getElementById("btn-cal-start");
    var btnStop = document.getElementById("btn-cal-stop");

    if (btnStart) btnStart.addEventListener("click", startCalibration);
    if (btnStop) btnStop.addEventListener("click", stopCalibration);
});
