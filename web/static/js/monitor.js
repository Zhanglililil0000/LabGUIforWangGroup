/**
 * monitor.js - SFG Running Monitor Panel
 * Depends on: app.js (state, api, addLog, showModal, closeModal)
 */

/* ============================================================
   Internal State (local to monitor)
   ============================================================ */

var _monitorSteps = [];   // [{ name, status }]  status: "pending"|"running"|"done"|"error"
var _monitorDoneShown = false;

/* ============================================================
   renderMonitorProgress
   ============================================================ */

function renderMonitorProgress() {
    var container = document.getElementById("monitor-progress");
    if (!container) return;

    var exp = state.experiment;

    if (!exp.running) {
        container.innerHTML =
            '<div class="monitor-waiting">等待实验开始...</div>';
        return;
    }

    var current = exp.current_step || 0;
    var total = exp.total_steps || 0;
    var pct = total > 0 ? Math.round((current / total) * 100) : 0;
    var elapsed = exp.elapsed || "0s";

    // current step name from latest info
    var currentStepName = "";
    var runningStep = _monitorSteps.find(function (s) { return s.status === "running"; });
    if (!runningStep) {
        // fallback to last completed + 1
        var nextIdx = _monitorSteps.filter(function (s) { return s.status === "done"; }).length;
        if (nextIdx < _monitorSteps.length) {
            currentStepName = _monitorSteps[nextIdx].name;
        }
    } else {
        currentStepName = runningStep.name;
    }

    var progressBarHtml =
        '<div class="progress-bar-bg">' +
        '<div class="progress-bar-fill" style="width:' +
        pct +
        '%"></div>' +
        "</div>";

    container.innerHTML =
        '<div class="monitor-progress-content">' +
        '<div class="monitor-status">状态: 运行中</div>' +
        progressBarHtml +
        '<div class="monitor-step-count">' +
        current +
        "/" +
        total +
        " 步骤</div>" +
        '<div class="monitor-current-step">当前步骤: ' +
        escHtml(currentStepName || "---") +
        "</div>" +
        '<div class="monitor-elapsed">已用时间: ' +
        escHtml(elapsed) +
        "</div>" +
        "</div>";
}

/* ============================================================
   renderMonitorSteps
   ============================================================ */

function renderMonitorSteps(msg) {
    var container = document.getElementById("monitor-steps");
    if (!container) return;

    // If msg contains step list info, rebuild _monitorSteps
    if (msg && msg.steps && Array.isArray(msg.steps)) {
        _monitorSteps = msg.steps.map(function (s) {
            return {
                name: s.name || s.type || "未知步骤",
                status: s.status || "pending",
            };
        });
    }

    // If msg has a single step update
    if (msg && msg.step != null) {
        var stepIdx = msg.step;
        if (_monitorSteps[stepIdx]) {
            _monitorSteps[stepIdx].status = msg.status || "done";
        }
    }

    if (!_monitorSteps.length) {
        container.innerHTML =
            '<div class="monitor-empty-steps">等待步骤信息...</div>';
        return;
    }

    var html = '<ul class="step-list">';
    _monitorSteps.forEach(function (s) {
        var icon = "";
        var cls = "step-item";
        switch (s.status) {
            case "done":
                icon = "\u2713 "; // checkmark
                cls += " step-done";
                break;
            case "running":
                icon = "\u2192 "; // arrow
                cls += " step-current";
                break;
            case "error":
                icon = "\u2717 "; // cross
                cls += " step-error";
                break;
            default:
                // pending: no icon, gray
                cls += " step-pending";
                break;
        }
        html +=
            '<li class="' + cls + '">' + icon + escHtml(s.name) + "</li>";
    });
    html += "</ul>";

    container.innerHTML = html;
}

/* ============================================================
   renderLogs
   ============================================================ */

function renderLogs() {
    var container = document.getElementById("monitor-logs");
    if (!container) return;

    var logs = state.logs || [];

    if (!logs.length) {
        container.innerHTML =
            '<div class="monitor-empty-logs">暂无日志记录。</div>';
        return;
    }

    // virtual window: show last 50
    var visible = logs.length > 50 ? logs.slice(logs.length - 50) : logs;

    var html = "";
    visible.forEach(function (log) {
        var level = log.level || "info";
        var timestamp = log.timestamp || "";
        var message = log.message || "";
        html +=
            '<div class="log-line ' +
            escHtml(level) +
            '">' +
            '<span class="log-ts">' +
            escHtml(timestamp) +
            "</span> " +
            escHtml(message) +
            "</div>";
    });

    container.innerHTML = html;

    // auto-scroll to bottom
    container.scrollTop = container.scrollHeight;
}

/* ============================================================
   renderMonitorDone
   ============================================================ */

function renderMonitorDone(msg) {
    _monitorDoneShown = true;

    var container = document.getElementById("monitor-logs");
    if (!container) return;

    var elapsed = (msg && msg.elapsed) || state.experiment.elapsed || "---";
    var fileCount = (msg && msg.file_count) || 0;

    var doneHtml =
        '<div class="monitor-done">' +
        '<div class="monitor-done-title">实验完成 (耗时 ' +
        escHtml(elapsed) +
        ")</div>" +
        '<div class="monitor-done-files">产出: ' +
        fileCount +
        " 个文件</div>" +
        "</div>";

    // append after logs
    container.insertAdjacentHTML("beforeend", doneHtml);

    // re-enable run button
    updateRunButtons(false);

    // update experiment state
    state.experiment.running = false;
    updateStatusBar();
}

/* ============================================================
   updateRunButtons
   ============================================================ */

function updateRunButtons(running) {
    var btnRun = document.getElementById("btn-run");
    var btnPause = document.getElementById("btn-pause");
    var btnStop = document.getElementById("btn-stop");

    if (btnRun) btnRun.disabled = running;
    if (btnPause) btnPause.disabled = !running;
    if (btnStop) btnStop.disabled = !running;

    state.experiment.running = running;
}

/* ============================================================
   updateStatusBar
   ============================================================ */

function updateStatusBar() {
    var indicator = document.getElementById("status-indicator");
    var time = document.getElementById("status-time");
    var modeInfo = document.getElementById("mode-info");

    // indicator
    if (indicator) {
        if (state.experiment.running) {
            indicator.innerHTML =
                '<span class="status-dot status-running"></span> 运行中';
        } else {
            indicator.innerHTML =
                '<span class="status-dot status-ready"></span> 就绪';
        }
    }

    // estimated time
    if (time) {
        time.textContent = "预计耗时: " + _estimateTotalTime();
    }

    // mode info
    if (modeInfo) {
        if (state.modes[state.currentMode]) {
            modeInfo.textContent = state.modes[state.currentMode].description || "";
        }
        modeInfo.classList.toggle("mode-active", !!state.currentMode);
    }
}

/**
 * Estimate total experiment time based on total steps and exposure parameters.
 */
function _estimateTotalTime() {
    var total = 0;
    var groups = (state.flow && state.flow.groups) || [];
    groups.forEach(function (g) {
        g.steps.forEach(function (s) {
            switch (s.type) {
                case "MotorHome":
                case "MotorMoveTo":
                    total += 5;  // ~5s motor movement
                    break;
                case "SetExposure":
                    total += 1;
                    break;
                case "SetWavelength":
                    total += 1;
                    break;
                case "SetGrating":
                    total += 1;
                    break;
                case "AcquireSpectrum":
                    var exposure = (s.params && s.params.exposure_ms) || 60000;
                    var frames = (s.params && s.params.frames) || 1;
                    total += (exposure / 1000) * frames + 2;
                    break;
                case "AcquireSRSSpectrum":
                    // SRS: 10000 frames ~ 10s acquisition + processing
                    var frames = (s.params && s.params.frames) || 10000;
                    total += (frames / 1000) + 5;  // ~1s per 1000 frames + processing
                    break;
                case "SetPolarization":
                    total += 2;
                    break;
                case "DelayStageHome":
                    total += 5;
                    break;
                case "DelayStageMoveTo":
                    total += 5;
                    break;
                case "Sleep":
                    total += (s.params && s.params.seconds) || 1;
                    break;
                case "LogMessage":
                    total += 0;
                    break;
            }
        });
    });

    if (total < 60) {
        return Math.round(total) + " 秒";
    }
    var mins = Math.floor(total / 60);
    var secs = Math.round(total % 60);
    return mins + " 分 " + secs + " 秒";
}

/* ============================================================
   Button Bindings (runs on DOMContentLoaded)
   ============================================================ */

document.addEventListener("DOMContentLoaded", function () {
    // ---- Mode Tab Clicks ----
    document.querySelectorAll(".mode-tab").forEach(function(tab) {
        tab.addEventListener("click", function() {
            switchMode(this.dataset.mode);
        });
    });

    // ---- Run ----
    var btnRun = document.getElementById("btn-run");
    if (btnRun) {
        btnRun.addEventListener("click", function () {
            if (!state.flow || !state.flow.groups || !state.flow.groups.length) {
                addLog(warn, "请先在编辑器中添加采集组");
                return;
            }
            // reset monitor state
            _monitorSteps = [];
            _monitorDoneShown = false;
            // clear done panel if any
            var donePanel = document.querySelector(".monitor-done");
            if (donePanel) donePanel.remove();

            api("/api/experiments/run", { method: "POST", body: JSON.stringify({ flow: state.flow }) })
                .then(function (res) {
                    state.experiment.running = true;
                    state.experiment.current_step = 0;
                    state.experiment.elapsed = "0s";
                    updateRunButtons(true);
                    updateStatusBar();
                    renderMonitorProgress();
                    addLog(info, "实验已启动");
                })
                .catch(function (err) {
                    addLog(error, "启动实验失败: " + err.message);
                });
        });
    }

    // ---- Pause ----
    var btnPause = document.getElementById("btn-pause");
    if (btnPause) {
        btnPause.addEventListener("click", function () {
            api("/api/experiments/pause", { method: "POST" })
                .then(function () {
                    addLog(warn, "实验已暂停");
                })
                .catch(function (err) {
                    addLog(error, "暂停失败: " + err.message);
                });
        });
    }

    // ---- Stop ----
    var btnStop = document.getElementById("btn-stop");
    if (btnStop) {
        btnStop.addEventListener("click", function () {
            api("/api/experiments/stop", { method: "POST" })
                .then(function () {
                    state.experiment.running = false;
                    updateRunButtons(false);
                    updateStatusBar();
                    renderMonitorProgress();
                    addLog(warn, "实验已停止");
                })
                .catch(function (err) {
                    addLog(error, "停止失败: " + err.message);
                });
        });
    }

    // initial render
    renderMonitorProgress();
    renderMonitorSteps();
    renderLogs();
    updateRunButtons(false);
    updateStatusBar();
});

/* ============================================================
   WebSocket Message Router
   Called by app.js when WS messages arrive.
   ============================================================ */

/**
 * Handle incoming WebSocket messages related to experiment monitoring.
 * Expected msg shapes:
 *   { type: "experiment_start", steps: [...], total_steps: N }
 *   { type: "step_start", step: N, name: "..." }
 *   { type: "step_done",  step: N }
 *   { type: "step_error", step: N, error: "..." }
 *   { type: "experiment_progress", current_step: N, total_steps: N, elapsed: "..." }
 *   { type: "experiment_done", elapsed: "...", file_count: N }
 */
function handleMonitorMessage(msg) {
    if (!msg || !msg.type) return;

    switch (msg.type) {
        case "experiment_start":
            state.experiment.running = true;
            state.experiment.current_step = 0;
            state.experiment.total_steps = msg.total_steps || 0;
            state.experiment.elapsed = "0s";
            _monitorDoneShown = false;
            // clear done panel
            var donePanel = document.querySelector(".monitor-done");
            if (donePanel) donePanel.remove();
            updateRunButtons(true);
            updateStatusBar();
            if (msg.steps) {
                renderMonitorSteps({ steps: msg.steps });
            }
            renderMonitorProgress();
            break;

        case "step_start":
            state.experiment.current_step = (msg.step != null ? msg.step : 0) + 1;
            renderMonitorSteps({ step: msg.step, status: "running", name: msg.name });
            renderMonitorProgress();
            break;

        case "step_done":
            renderMonitorSteps({ step: msg.step, status: "done" });
            renderMonitorProgress();
            break;

        case "step_error":
            renderMonitorSteps({ step: msg.step, status: "error" });
            renderMonitorProgress();
            if (msg.error) {
                addLog(error, "步骤错误: " + msg.error);
            }
            break;

        case "experiment_progress":
            state.experiment.current_step = msg.current_step || 0;
            state.experiment.total_steps = msg.total_steps || state.experiment.total_steps;
            state.experiment.elapsed = msg.elapsed || state.experiment.elapsed;
            renderMonitorProgress();
            break;

        case "experiment_done":
            state.experiment.current_step = state.experiment.total_steps;
            state.experiment.elapsed = msg.elapsed || state.experiment.elapsed;
            renderMonitorProgress();
            renderMonitorDone(msg);
            updateStatusBar();
            break;

        default:
            break;
    }
}
