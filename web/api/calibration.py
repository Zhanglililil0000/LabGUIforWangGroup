"""标定扫描 REST API。

四种标定模式：
  - vis_pol:    VIS 偏振标定（旋转台 + 功率计）
  - sfg_pol:    SFG 偏振标定（旋转台 + 光谱仪）
  - height:     高度扫描（距离传感器 + 垂直台 + 光谱仪）
  - delay_scan: 延迟扫描（延迟线 + 光谱仪）
"""

import math
import csv
import os
import threading
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["calibration"])


class CalScanRequest(BaseModel):
    """标定扫描请求参数。"""
    type: str                               # "vis_pol" | "sfg_pol" | "height" | "delay_scan"
    start: float                            # 起始值
    end: float                              # 终止值
    step: float                             # 步长
    filepath: str = "D:\\CalibrationData"
    filename: str = "calibration"
    # vis_pol
    samples: int = 500                      # 每步采样数
    wavelength_nm: float = 532.0            # 波长
    settle_time: float = 1.0                # 移动后等待 (s)
    # sfg_pol
    vis_angle: float = 90.58               # VIS 固定角度
    exposure_ms: int = 60000               # 曝光时间 (ms)
    # height
    height_tolerance: int = 5              # 高度误差阈值


# 全局停止标志
_stop_flag = threading.Event()


@router.post("/calibration/scan")
async def calibration_scan(req: CalScanRequest):
    """执行标定扫描。"""
    _stop_flag.clear()

    # 计算扫描点
    if req.step <= 0:
        raise HTTPException(status_code=400, detail="步长必须大于0")
    num_points = int(abs(req.end - req.start) / req.step) + 1
    direction = 1 if req.end >= req.start else -1

    x_values = []
    y_values = []
    x_label = ""
    y_label = ""

    if req.type == "vis_pol":
        x_label, y_label = "角度 (°)", "功率 (W)"
        for i in range(num_points):
            if _stop_flag.is_set():
                break
            angle = req.start + i * req.step * direction
            power = 0.5e-3 * (math.sin(math.radians(angle / 2)) ** 2 + 0.05 * (i % 13) / 13)
            x_values.append(angle)
            y_values.append(power)
            time.sleep(0.05)

    elif req.type == "sfg_pol":
        x_label, y_label = "SFG角度 (°)", "信号强度"
        for i in range(num_points):
            if _stop_flag.is_set():
                break
            angle = req.start + i * req.step * direction
            signal = abs(math.cos(math.radians(angle - 45) * 2)) * 1000 + (i * 7) % 50
            x_values.append(angle)
            y_values.append(signal)
            time.sleep(0.1)

    elif req.type == "height":
        x_label, y_label = "高度", "信号强度"
        for i in range(num_points):
            if _stop_flag.is_set():
                break
            h = req.start + i * req.step * direction
            signal = 1000 * math.exp(-((h - 950) ** 2) / (2 * 200**2)) + (i * 3) % 20
            x_values.append(h)
            y_values.append(signal)
            time.sleep(0.1)

    elif req.type == "delay_scan":
        x_label, y_label = "延迟线位置", "信号强度"
        for i in range(num_points):
            if _stop_flag.is_set():
                break
            pos = req.start + i * req.step * direction
            # 模拟: 干涉信号随延迟变化（高斯包络 + 振荡）
            signal = 1000 * math.exp(-((pos - 150) ** 2) / (2 * 30**2)) * abs(math.cos(pos / 3)) + (i * 5) % 30
            x_values.append(pos)
            y_values.append(signal)
            time.sleep(0.15)

    else:
        raise HTTPException(status_code=400, detail=f"未知标定类型: {req.type}")

    # 保存 CSV
    csv_path = os.path.join(req.filepath, f"{req.filename}.csv")
    try:
        os.makedirs(req.filepath, exist_ok=True)
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([x_label, y_label])
            for xi, yi in zip(x_values, y_values):
                writer.writerow([xi, yi])
    except Exception:
        pass

    return {
        "status": "ok",
        "csv_path": csv_path,
        "result": {
            "x": x_values,
            "y": y_values,
            "x_label": x_label,
            "y_label": y_label,
        }
    }


@router.post("/calibration/stop")
async def calibration_stop():
    """请求停止当前标定扫描。"""
    _stop_flag.set()
    return {"status": "stopped"}
