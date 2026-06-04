/**
 * editor.js - SFG Flow Editor
 * Depends on: app.js (state, api, addLog, showModal, closeModal)
 */

/* ============================================================
   Constants
   ============================================================ */

const STEP_TYPES = [
    { value: "MotorHome",      label: "MotorHome",      params: { device: "vis_rotator" } },
    { value: "MotorMoveTo",    label: "MotorMoveTo",    params: { device: "vis_rotator", position: 0 } },
    { value: "SetExposure",    label: "SetExposure",    params: { exposure_ms: 60000 } },
    { value: "SetWavelength",  label: "SetWavelength",  params: { wavelength_nm: 475 } },
    { value: "SetGrating",     label: "SetGrating",     params: { grating: "300" } },
    { value: "AcquireSpectrum",label: "AcquireSpectrum",params: { name: "sample", exposure_ms: 60000, frames: 1, compute_diff: false } },
    { value: "AcquireSRSSpectrum", label: "SRS采集",    params: { name: "sample", wavelength_nm: 630, frames: 10000, pump_pol: "VV", exposure_ms: 1000 } },
    { value: "SetPolarization",label: "SetPolarization",params: { mode: "ssp" } },
    { value: "DelayStageHome", label: "DelayStageHome", params: { device: "delay_stage", axis: "X" } },
    { value: "DelayStageMoveTo",label:"DelayStageMoveTo",params: { device: "delay_stage", axis: "X", position: 150 } },
    { value: "Sleep",          label: "Sleep",          params: { seconds: 1 } },
    { value: "LogMessage",     label: "LogMessage",     params: { message: "步骤开始", level: "info" } },
    { value: "ReadPower",      label: "ReadPower",      params: { wavelength_nm: 532 } },
    { value: "ReadDistance",   label: "ReadDistance",   params: {} },
    { value: "VerticalStageMove", label: "垂直台移动",   params: { device: "vertical_stage", axis: 1, position: 500 } },
];

const POLARIZATION_MODES = ["ssp", "ppp", "sps", "pss", "spp", "psp"];
const SRS_PUMP_POLARIZATIONS = ["VV", "VH"];

/**
 * 根据当前实验模式获取允许的步骤类型。
 * 从 state.modes[state.currentMode].step_types 获取允许列表，
 * 与完整 STEP_TYPES 做交集过滤。
 *
 * @returns {Array} 过滤后的步骤类型对象数组
 */
function getAllowedStepTypes() {
    var allowed = (state.modes[state.currentMode] && state.modes[state.currentMode].step_types)
        ? state.modes[state.currentMode].step_types
        : [];
    if (!allowed.length) {
        allowed = ["MotorHome","MotorMoveTo","SetExposure","SetWavelength","SetGrating","AcquireSpectrum","SetPolarization","Sleep","LogMessage","ReadPower","ReadDistance","VerticalStageMove"];
    }
    return STEP_TYPES.filter(function(s) { return allowed.indexOf(s.value) !== -1; });
}

/* ============================================================
   Utility
   ============================================================ */

function escHtml(str) {
    if (typeof str !== "string") return str;
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function _deepClone(obj) {
    return JSON.parse(JSON.stringify(obj));
}

function _defaultParamsForType(typeValue) {
    var found = STEP_TYPES.find(function (t) { return t.value === typeValue; });
    return found ? _deepClone(found.params) : {};
}

/* ============================================================
   Core Actions
   ============================================================ */

function addGroup(name) {
    var groupName = name || "新采集组";
    var groupSteps = [];

    switch (state.currentMode) {
        case "srs":
            groupName = name || "SRS采集组";
            groupSteps = [
                { type: "MotorHome", params: { device: "raman_rotator" } },
                { type: "AcquireSpectrum", params: { name: "srs", exposure_ms: 60000, frames: 10000, compute_diff: true } },
            ];
            break;
        case "calibration":
            groupName = name || "调试组";
            groupSteps = [
                { type: "MotorHome", params: { device: "vis_rotator" } },
                { type: "ReadPower", params: { wavelength_nm: 532 } },
            ];
            break;
        default: // sfg or fallback
            groupName = name || "新采集组";
            groupSteps = [
                { type: "SetPolarization", params: _defaultParamsForType("SetPolarization") },
                { type: "AcquireSpectrum", params: _defaultParamsForType("AcquireSpectrum") },
            ];
            break;
    }

    state.flow.groups.push({
        name: groupName,
        steps: groupSteps,
    });
    renderFlow();
}

function addStepToGroup(gi) {
    if (!state.flow.groups[gi]) return;
    state.flow.groups[gi].steps.push({
        type: "MotorHome",
        params: _defaultParamsForType("MotorHome"),
    });
    renderFlow();
}

function deleteStep(gi, si) {
    var group = state.flow.groups[gi];
    if (!group) return;
    group.steps.splice(si, 1);
    renderFlow();
}

function deleteGroup(gi) {
    state.flow.groups.splice(gi, 1);
    renderFlow();
}

function startRenameGroup(gi) {
    var group = state.flow.groups[gi];
    if (!group) return;
    showModal("重命名采集组",
        '<label>新名称: <input id="rename-input" type="text" value="' + escHtml(group.name || '') + '" /></label>',
        function () {
            var input = document.getElementById("rename-input");
            if (input && input.value.trim()) {
                group.name = input.value.trim();
                renderFlow();
            }
        }
    );
    // 自动聚焦
    setTimeout(function () {
        var inp = document.getElementById("rename-input");
        if (inp) { inp.focus(); inp.select(); }
    }, 100);
}

function updateStepParam(gi, si, key, value) {
    var group = state.flow.groups[gi];
    if (!group || !group.steps[si]) return;
    group.steps[si].params[key] = value;
}

function updateStepType(gi, si, newType) {
    var group = state.flow.groups[gi];
    if (!group || !group.steps[si]) return;
    group.steps[si].type = newType;
    group.steps[si].params = _defaultParamsForType(newType);
    renderFlow();
}

/* ============================================================
   Template Serialization
   ============================================================ */

function serializeFlow() {
    return state.flow.groups.map(function (g) {
        return {
            name: g.name,
            steps: g.steps.map(function (s) {
                return { type: s.type, params: s.params };
            }),
        };
    });
}

function deserializeFlow(groups) {
    return groups.map(function (g) {
        return {
            name: g.name || "",
            steps: (g.steps || []).map(function (s) {
                return {
                    type: s.type,
                    params: s.params || _defaultParamsForType(s.type),
                };
            }),
        };
    });
}

/* ============================================================
   Rendering
   ============================================================ */

function renderFlow() {
    var container = document.getElementById("flow-container");
    if (!container) return;

    // ── 流程配置栏（样品名称 + 保存路径） ──
    var configHtml = '<div class="flow-config-bar">' +
        '<label class="flow-config-label">样品名</label>' +
        '<input type="text" class="flow-config-input" id="flow-sample" value="' + escHtml(state.flow.sample || "") + '"' +
        ' onchange="state.flow.sample=this.value" placeholder="输入样品名" />' +
        '<label class="flow-config-label">保存路径</label>' +
        '<input type="text" class="flow-config-input" id="flow-basepath" value="' + escHtml(state.flow.base_path || "") + '"' +
        ' onchange="state.flow.base_path=this.value" placeholder="D:\\SFGData" style="flex:1;" />' +
        '</div>';

    if (!state.flow.groups.length) {
        container.innerHTML =
            configHtml +
            '<div class="flow-empty">暂无采集组。<br>点击「添加采集组」开始构建实验流程。</div>';
        return;
    }

    var html = configHtml;

    state.flow.groups.forEach(function (group, gi) {
        // ---------- group header ----------
        html += '<div class="flow-group">';
        html +=
            '<div class="flow-group-header">' +
            '<span class="flow-group-name" onclick="startRenameGroup(' + gi + ')" title="点击重命名">' +
            escHtml(group.name) +
            "</span>" +
            '<button class="btn-rename-group" onclick="startRenameGroup(' + gi + ')" title="重命名">✎</button>' +
            '<button class="btn-delete-group" onclick="deleteGroup(' +
            gi +
            ')" title="删除采集组">✕</button>' +
            "</div>";

        // ---------- step rows ----------
        html += '<div class="flow-steps">';

        group.steps.forEach(function (step, si) {
            html +=
                '<div class="flow-step-row" data-gi="' +
                gi +
                '" data-si="' +
                si +
                '">';

            // step number
            html +=
                '<span class="step-index">#' + (si + 1) + "</span>";

            // type selector
            html +=
                '<select class="step-type-select" onchange="updateStepType(' +
                gi +
                "," +
                si +
                ',this.value)">';
            var allowedTypes = getAllowedStepTypes();
            allowedTypes.forEach(function (t) {
                html +=
                    '<option value="' +
                    t.value +
                    '"' +
                    (step.type === t.value ? " selected" : "") +
                    ">" +
                    t.label +
                    "</option>";
            });
            html += "</select>";

            // params based on step type
            html += '<span class="step-params">';
            html += _renderStepParams(gi, si, step);
            html += "</span>";

            // delete button
            html +=
                '<button class="btn-delete-step" onclick="deleteStep(' +
                gi +
                "," +
                si +
                ')" title="删除步骤">✕</button>';

            html += "</div>";
        });

        // add step link
        html +=
            '<div class="flow-add-step">' +
            '<a href="javascript:void(0)" onclick="addStepToGroup(' +
            gi +
            ')">+ 添加步骤</a>' +
            "</div>";

        html += "</div>"; // .flow-steps
        html += "</div>"; // .flow-group
    });

    container.innerHTML = html;
}

/**
 * Render parameter inputs for a single step.
 */
function _renderStepParams(gi, si, step) {
    var p = step.params || {};
    var t = step.type;
    var html = "";

    switch (t) {
        case "MotorHome":
            html += _renderSelect(
                "device",
                gi,
                si,
                p.device,
                ["vis_rotator", "sfg_rotator", "raman_rotator"]
            );
            break;

        case "MotorMoveTo":
            html += _renderSelect(
                "device",
                gi,
                si,
                p.device,
                ["vis_rotator", "sfg_rotator", "raman_rotator"]
            );
            html += _renderNumberInput("position", gi, si, p.position);
            break;

        case "SetExposure":
            html += _renderNumberInput("exposure_ms", gi, si, p.exposure_ms);
            break;

        case "SetWavelength":
            html += _renderNumberInput("wavelength_nm", gi, si, p.wavelength_nm);
            break;

        case "SetGrating":
            html += _renderSelect("grating", gi, si, p.grating, ["300", "600", "1200", "1500"]);
            break;

        case "AcquireSpectrum":
            html += _renderTextInput("name", gi, si, p.name);
            html += _renderNumberInput("exposure_ms", gi, si, p.exposure_ms);
            html += _renderNumberInput("frames", gi, si, p.frames);
            break;

        case "AcquireSRSSpectrum":
            html += _renderTextInput("name", gi, si, p.name);
            html += _renderNumberInput("wavelength_nm", gi, si, p.wavelength_nm);
            html += _renderNumberInput("exposure_ms", gi, si, p.exposure_ms);
            html += _renderNumberInput("frames", gi, si, p.frames);
            html += _renderSelect("pump_pol", gi, si, p.pump_pol, SRS_PUMP_POLARIZATIONS);
            break;

        case "SetPolarization":
            html += _renderSelect(
                "mode",
                gi,
                si,
                p.mode,
                POLARIZATION_MODES
            );
            break;

        case "DelayStageHome":
            // device + axis are already default; show device and axis as readonly-ish text
            html += _renderTextInput("device", gi, si, p.device);
            html += _renderTextInput("axis", gi, si, p.axis);
            break;

        case "DelayStageMoveTo":
            html += _renderTextInput("device", gi, si, p.device);
            html += _renderTextInput("axis", gi, si, p.axis);
            html += _renderNumberInput("position", gi, si, p.position);
            break;

        case "Sleep":
            html += _renderNumberInput("seconds", gi, si, p.seconds);
            break;

        case "LogMessage":
            html += _renderTextInput("message", gi, si, p.message);
            break;

        case "ReadPower":
            html += _renderNumberInput("wavelength_nm", gi, si, p.wavelength_nm);
            break;

        case "ReadDistance":
            html += '<span style="font-size:12px;color:#999;">读取高度值</span>';
            break;

        case "VerticalStageMove":
            html += _renderTextInput("device", gi, si, p.device);
            html += _renderNumberInput("axis", gi, si, p.axis);
            html += _renderNumberInput("position", gi, si, p.position);
            break;

        default:
            html += '<span class="step-params-unknown">未知类型</span>';
            break;
    }

    return html;
}

/* ---- helper renderers ---- */

function _renderNumberInput(key, gi, si, val) {
    return (
        '<label class="param-label">' +
        escHtml(key) +
        ' <input type="number" class="param-input" value="' +
        (val != null ? val : "") +
        '" onchange="updateStepParam(' +
        gi +
        "," +
        si +
        ",&#39;" +
        key +
        "&#39;,this.valueAsNumber||0)" +
        '" /></label>'
    );
}

function _renderTextInput(key, gi, si, val) {
    return (
        '<label class="param-label">' +
        escHtml(key) +
        ' <input type="text" class="param-input" value="' +
        escHtml(val != null ? String(val) : "") +
        '" onchange="updateStepParam(' +
        gi +
        "," +
        si +
        ",&#39;" +
        key +
        "&#39;,this.value)" +
        '" /></label>'
    );
}

function _renderSelect(key, gi, si, currentVal, options) {
    var html =
        '<label class="param-label">' +
        escHtml(key) +
        ' <select class="param-select" onchange="updateStepParam(' +
        gi +
        "," +
        si +
        ",&#39;" +
        key +
        "&#39;,this.value)\">";
    options.forEach(function (opt) {
        html +=
            '<option value="' +
            opt +
            '"' +
            (currentVal === opt ? " selected" : "") +
            ">" +
            opt +
            "</option>";
    });
    html += "</select></label>";
    return html;
}

/* ============================================================
   Button Bindings (runs on DOMContentLoaded)
   ============================================================ */

/**
 * 渲染模板列表到工具栏下拉框。
 * 将 state.templates 填充到 #select-template 中。
 */
function renderTemplateList(selectFilename) {
    var sel = document.getElementById("select-template");
    if (!sel) return;

    var html = '<option value="">-- 选择模板 --</option>';
    if (state.templates && state.templates.length) {
        state.templates.forEach(function (t) {
            var fname = (t.filename || "").replace(".yaml", "").replace(".yml", "");
            html += '<option value="' + escHtml(fname) + '">' + escHtml(t.name) + '</option>';
        });
    }
    sel.innerHTML = html;
    // 如果指定了文件名则选中它，否则保持空（不触发加载）
    sel.value = selectFilename || "";
}

/**
 * 加载指定模板。如有 {sample} 占位符则弹窗输入样品名。
 */
async function loadTemplate(fname) {
    try {
        var data = await api("/api/templates/" + encodeURIComponent(fname));
        var groups = deserializeFlow(data.groups || []);
        var hasPlaceholder = false;

        groups.forEach(function (g) {
            g.steps.forEach(function (s) {
                for (var k in s.params) {
                    if (typeof s.params[k] === "string" && s.params[k].indexOf("{sample}") !== -1)
                        hasPlaceholder = true;
                }
            });
        });

        var applyGroups = function (sampleName) {
            if (sampleName && sampleName.trim()) {
                var name = sampleName.trim();
                state.flow.sample = name;
                groups.forEach(function (g) {
                    g.steps.forEach(function (s) {
                        for (var k in s.params) {
                            if (typeof s.params[k] === "string" && s.params[k].indexOf("{sample}") !== -1)
                                s.params[k] = s.params[k].replace(/\{sample\}/g, name);
                        }
                    });
                });
            }
            state.flow.groups = groups;
            if (data.name) state.flow.name = data.name;
            renderFlow();
            addLog("info", "模板「" + data.name + "」已加载");
        };

        if (hasPlaceholder) {
            showModal("加载模板 — 输入样品名",
                '<label>样品名称 (替换 {sample}): <input id="template-sample-name" type="text" placeholder="输入样品名" /></label>',
                function () {
                    applyGroups((document.getElementById("template-sample-name") || {}).value || "");
                }
            );
            setTimeout(function () {
                var inp = document.getElementById("template-sample-name");
                if (inp) inp.focus();
            }, 100);
        } else {
            applyGroups("");
        }
    } catch (e) {
        addLog("error", "模板加载失败: " + e.message);
    }
}

/**
 * 删除工具栏下拉框中当前选中的模板。
 */
async function deleteTemplate() {
    var sel = document.getElementById("select-template");
    if (!sel || !sel.value) {
        addLog("warn", "请先在工具栏下拉框中选择要删除的模板");
        return;
    }
    var fname = sel.value;
    var displayName = sel.options[sel.selectedIndex].text;

    showModal("删除模板",
        '<p>确定删除模板「<strong>' + escHtml(displayName) + '</strong>」？</p><p style="color:#e74c3c;font-size:13px;">此操作不可恢复。</p>',
        function () {
            api("/api/templates/" + encodeURIComponent(fname), { method: "DELETE" })
                .then(function () {
                    addLog("info", "模板「" + displayName + "」已删除");
                    refreshTemplateList();
                })
                .catch(function (err) {
                    addLog("error", "删除模板失败: " + err.message);
                });
        }
    );
}

/* ── 下拉框选择即加载 ── */
document.addEventListener("DOMContentLoaded", function () {
    var sel = document.getElementById("select-template");
    if (sel) {
        sel.addEventListener("change", function () {
            if (!sel.value) return;
            loadTemplate(sel.value);
        });
    }

    var btnAddGroup = document.getElementById("btn-add-group");
    if (btnAddGroup) {
        btnAddGroup.addEventListener("click", function () {
            addGroup("新采集组");
        });
    }

    // ---- Save Template ----
    var btnSave = document.getElementById("btn-save-template");
    if (btnSave) {
        btnSave.addEventListener("click", function () {
            if (!state.flow.groups.length) {
                addLog("warn", "没有可保存的步骤组");
                return;
            }
            showModal("保存模板",
                '<label>模板名称: <input id="template-save-name" type="text" placeholder="输入模板名" /></label>',
                function () {
                    var name = document.getElementById("template-save-name").value.trim();
                    if (!name) return;
                    api("/api/templates", { method: "POST", body: JSON.stringify({
                        name: name,
                        mode: state.currentMode,
                        flow: {
                            name: state.flow.name,
                            sample: state.flow.sample,
                            base_path: state.flow.base_path,
                            groups: serializeFlow(),
                        }
                    }) }).then(function (resp) {
                        addLog("info", "模板「" + name + "」已保存");
                        // 乐观更新：立即添加到本地列表并渲染下拉框
                        var savedFname = (resp.filename || name);
                        var meta = {
                            name: name,
                            filename: savedFname,
                            mode: state.currentMode,
                            group_count: state.flow.groups.length,
                            step_count: state.flow.groups.reduce(function (n, g) { return n + g.steps.length; }, 0)
                        };
                        // 避免重复
                        state.templates = state.templates || [];
                        var found = false;
                        for (var i = 0; i < state.templates.length; i++) {
                            if (state.templates[i].filename === savedFname) {
                                state.templates[i] = meta;
                                found = true;
                                break;
                            }
                        }
                        if (!found) state.templates.push(meta);
                        renderTemplateList(savedFname.replace(".yaml", "").replace(".yml", ""));
                        // 后台刷新确保与服务器同步
                        refreshTemplateList();
                    }).catch(function (err) {
                        addLog("error", "模板保存失败: " + err.message);
                    });
                }
            );
            setTimeout(function () {
                var inp = document.getElementById("template-save-name");
                if (inp) inp.focus();
            }, 100);
        });
    }

    // ---- Delete Template ----
    var btnDelete = document.getElementById("btn-delete-template");
    if (btnDelete) {
        btnDelete.addEventListener("click", deleteTemplate);
    }

    // initial render
    renderFlow();
});
