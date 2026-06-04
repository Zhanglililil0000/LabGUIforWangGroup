"""Template management REST API.

模板以 YAML 文件形式存储在 CommandMode/configs/templates/{mode}/ 子目录下。
提供模板列表、读取、创建和删除功能，支持按实验模式分类存储。
"""

import os
import re

import yaml
from fastapi import APIRouter, HTTPException, Query

from web.schemas import TemplateMeta, TemplateSaveRequest

router = APIRouter(tags=["templates"])


def _templates_dir(mode: str | None = None) -> str:
    """获取模板目录的绝对路径，不存在时自动创建。

    Args:
        mode: 实验模式名称（如 sfg, srs），为 None 时返回基础 templates 目录

    Returns:
        CommandMode/configs/templates/ 或 CommandMode/configs/templates/{mode}/ 的绝对路径
    """
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    d = os.path.join(base, "configs", "templates")
    if mode:
        d = os.path.join(d, mode)
    os.makedirs(d, exist_ok=True)
    return d


def _all_template_dirs() -> list[str]:
    """返回所有可能存在模板的目录路径（根目录 + 各 mode 子目录）。

    Returns:
        目录路径列表，根目录在前
    """
    base = _templates_dir()
    dirs = [base]
    try:
        for entry in sorted(os.listdir(base)):
            sub = os.path.join(base, entry)
            if os.path.isdir(sub):
                dirs.append(sub)
    except Exception:
        pass
    return dirs


def _find_template_file(name: str) -> str | None:
    """在所有模板目录中查找指定名称的模板文件。

    Args:
        name: 模板名称（不含扩展名时自动尝试 .yaml 和 .yml）

    Returns:
        文件绝对路径，或未找到时返回 None
    """
    candidates = [name]
    if not (name.endswith(".yaml") or name.endswith(".yml")):
        candidates = [f"{name}.yaml", f"{name}.yml", name]

    for search_dir in _all_template_dirs():
        try:
            for cand in candidates:
                fp = os.path.join(search_dir, cand)
                if os.path.isfile(fp):
                    return fp
        except Exception:
            pass

    return None


def _sanitize_name(name: str) -> str:
    """清理模板名称，替换空格和斜杠为下划线。

    Args:
        name: 原始名称

    Returns:
        清理后的安全名称
    """
    return re.sub(r"[\s/\\]+", "_", name.strip())


def _read_template_meta(filepath: str) -> TemplateMeta | None:
    """从 YAML 文件读取模板元信息。

    Args:
        filepath: YAML 模板文件的绝对路径

    Returns:
        TemplateMeta 实例，或读取失败时返回 None
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    # 优先使用 template_name（用户输入的模板名），其次用 name（兼容旧模板）
    name = data.get("template_name", data.get("name", ""))
    groups = data.get("groups", [])
    group_count = len(groups) if isinstance(groups, list) else 0
    step_count = 0
    if isinstance(groups, list):
        for g in groups:
            if isinstance(g, dict):
                steps = g.get("steps", [])
                step_count += len(steps) if isinstance(steps, list) else 0

    filename = os.path.basename(filepath)
    # 从父目录名推断 mode
    parent_dir = os.path.basename(os.path.dirname(filepath))
    inferred_mode = parent_dir if parent_dir in ("sfg", "srs", "calibration", "debug") else ""

    return TemplateMeta(
        name=name or os.path.splitext(filename)[0],
        filename=filename,
        mode=data.get("mode", inferred_mode),
        group_count=group_count,
        step_count=step_count,
    )


def _scan_templates_in_dir(dir_path: str) -> list[TemplateMeta]:
    """扫描单个目录下的所有 YAML 模板文件。

    Args:
        dir_path: 要扫描的目录绝对路径

    Returns:
        TemplateMeta 列表
    """
    results: list[TemplateMeta] = []
    try:
        entries = sorted(os.listdir(dir_path))
    except Exception:
        return results

    for entry in entries:
        if not (entry.endswith(".yaml") or entry.endswith(".yml")):
            continue
        filepath = os.path.join(dir_path, entry)
        if not os.path.isfile(filepath):
            continue
        meta = _read_template_meta(filepath)
        if meta is not None:
            results.append(meta)

    return results


@router.get("/templates", response_model=list[TemplateMeta])
async def list_templates(mode: str | None = Query(None, description="按实验模式过滤，如 sfg / srs / calibration / debug")):
    """列出所有可用实验模板。

    支持可选的 ?mode= 查询参数，仅返回指定模式的模板。
    不指定时返回所有模式下的全部模板。
    """
    if mode:
        dir_path = _templates_dir(mode)
        return _scan_templates_in_dir(dir_path)

    results: list[TemplateMeta] = []
    for d in _all_template_dirs():
        results.extend(_scan_templates_in_dir(d))
    return results


@router.get("/templates/{name}")
async def get_template(name: str):
    """获取指定模板的完整 YAML 内容。

    Args:
        name: 模板名称（不含扩展名时自动尝试 .yaml 和 .yml）
    """
    filepath = _find_template_file(name)
    if filepath is None:
        raise HTTPException(status_code=404, detail=f"模板 '{name}' 不存在")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取模板 '{name}' 失败: {e}")

    if data is None:
        data = {}

    return data


@router.post("/templates")
async def create_template(req: TemplateSaveRequest):
    """创建或覆盖一个实验模板。

    将 TemplateSaveRequest 中的 experiment flow 序列化为 YAML 写入文件。
    根据 req.mode 字段保存到对应的子目录中。

    Args:
        req: 包含模板名称、模式和实验流程定义的请求体
    """
    safe_name = _sanitize_name(req.name)
    if not safe_name:
        raise HTTPException(status_code=400, detail="模板名称不能为空")

    mode = req.mode.value if req.mode else "sfg"
    dir_path = _templates_dir(mode)
    filepath = os.path.join(dir_path, f"{safe_name}.yaml")

    # 将 ExperimentFlow 转为可序列化的字典
    try:
        flow_dict = req.flow.model_dump(mode="json")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"模板数据序列化失败: {e}")

    # 注入用户输入的模板显示名（区别于 flow.name 实验流程名）
    flow_dict["template_name"] = req.name

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.safe_dump(flow_dict, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"写入模板文件失败: {e}")

    return {
        "name": safe_name,
        "filename": f"{safe_name}.yaml",
        "mode": mode,
        "message": "模板已保存",
    }


@router.delete("/templates/{name}")
async def delete_template(name: str):
    """删除指定名称的模板文件。

    Args:
        name: 模板名称（不含扩展名）
    """
    filepath = _find_template_file(name)
    if filepath is None:
        raise HTTPException(status_code=404, detail=f"模板 '{name}' 不存在")

    try:
        os.remove(filepath)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除模板 '{name}' 失败: {e}")

    return {"name": name, "deleted": True}
