"""实验控制 REST API。

提供实验的启动、暂停、恢复、停止、状态查询和模式列表接口。
"""

from fastapi import APIRouter, HTTPException
from web.schemas import RunRequest, ExperimentStatus, ModeInfo, ModeList
from web.services.runner import get_runner, ExperimentRunner
from core.config import Config

router = APIRouter(tags=["experiments"])


@router.post("/experiments/run")
async def run_experiment(req: RunRequest):
    """启动实验。

    接收 ExperimentFlow，构建 Pipeline 并在后台线程中执行。
    若已有实验在运行则返回 409。
    """
    runner = get_runner()
    if runner.is_running():
        raise HTTPException(status_code=409, detail="实验已在运行中")
    runner.run(req.flow)
    steps = req.flow.flatten_steps()
    return {
        "status": "started",
        "total_steps": len(steps),
        "pipeline_name": req.flow.name,
    }


@router.post("/experiments/pause")
async def pause_experiment():
    """暂停实验。当前步骤完成后挂起。"""
    runner = get_runner()
    runner.pause()
    return {"status": "paused"}


@router.post("/experiments/resume")
async def resume_experiment():
    """恢复已暂停的实验。"""
    runner = get_runner()
    runner.resume()
    return {"status": "resumed"}


@router.post("/experiments/stop")
async def stop_experiment():
    """停止实验。当前步骤完成后退出。"""
    runner = get_runner()
    runner.stop()
    return {"status": "stopped"}


@router.get("/experiments/status", response_model=ExperimentStatus)
async def experiment_status():
    """查询当前实验运行状态。"""
    runner = get_runner()
    pipeline = runner.pipeline
    ctx = runner.ctx

    running = runner.is_running()
    pipeline_name = ""
    total_steps = 0
    status = "idle"

    if pipeline is not None:
        pipeline_name = pipeline.name
        total_steps = len(pipeline.steps)

    if ctx is not None:
        status = ctx.status

    return ExperimentStatus(
        running=running,
        pipeline_name=pipeline_name,
        current_step=0,
        total_steps=total_steps,
        status=status,
    )


@router.get("/modes", response_model=ModeList)
async def list_modes():
    """列出所有支持的实验模式及其配置。

    从 configs/defaults.yaml 读取 modes 配置节，
    返回每种模式的名称、描述、LightField 实验名称、设备列表和步骤类型列表。
    """
    try:
        config = Config("configs/defaults.yaml")
        modes_data = config.get("modes")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取模式配置失败: {e}")

    if not modes_data or not isinstance(modes_data, dict):
        raise HTTPException(status_code=500, detail="默认配置中未定义 modes 节")

    modes: dict[str, ModeInfo] = {}
    for mode_id, mode_cfg in modes_data.items():
        if not isinstance(mode_cfg, dict):
            continue
        modes[mode_id] = ModeInfo(
            id=mode_id,
            name=mode_cfg.get("name", mode_id),
            description=mode_cfg.get("description", ""),
            lightfield_experiment=mode_cfg.get("lightfield_experiment", ""),
            devices=mode_cfg.get("devices", []),
            step_types=mode_cfg.get("step_types", []),
        )

    return ModeList(modes=modes)
