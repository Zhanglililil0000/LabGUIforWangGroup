"""信号处理模块。提供 SFG/SRS 实验的公共数据分析算法。"""

import numpy as np


def compute_differential_signal(
    intensities: list[np.ndarray],
    frames: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """计算泵浦-探测差分信号。

    用于 SRS 和 SFG 实验的 multi-frame 模式，交替采集泵浦开/关帧。
    通过比较相邻帧的强度比来计算差分信号。

    Args:
        intensities: 每帧的光谱强度数组列表，长度为 frames
        frames: 总帧数（必须为偶数）

    Returns:
        (ret, ret1, ret2) 三元组:
        - ret1: 奇数帧/偶数帧比值的平均 (pump-on / pump-off 方向1)
        - ret2: 偶数帧/奇数帧比值的平均 (pump-off / pump-on 方向2)
        - ret: 信号更强的一组 (max - min 差更大者)

    Raises:
        ValueError: frames 不是偶数或 intensities 长度不匹配
    """
    if frames % 2 != 0:
        raise ValueError(f"frames 必须为偶数，当前值: {frames}")
    if len(intensities) != frames:
        raise ValueError(
            f"intensities 长度 ({len(intensities)}) 与 frames ({frames}) 不匹配"
        )

    half = frames // 2

    # ret1: odd/even (i=0,2,4,... / i=1,3,5,...)
    ret1 = sum([
        intensities[i] / intensities[i + 1] - 1
        for i in range(0, frames, 2)
    ]) / half

    # ret2: even/odd (i=1,3,5,... / i=0,2,4,...)
    ret2 = sum([
        intensities[i + 1] / intensities[i] - 1
        for i in range(0, frames, 2)
    ]) / half

    # 选择信号动态范围更大的一组
    ret = ret1 if (max(ret1) - min(ret1) > max(ret2) - min(ret2)) else ret2

    return ret, ret1, ret2


def fit_polarization_curve(
    intensities: np.ndarray,
    angles_deg: np.ndarray
) -> dict:
    """拟合偏振角度-强度曲线。

    对每个波长的强度随偏振角变化做余弦平方拟合:
    I(θ) = A * cos²(θ - θ₀) + B

    Args:
        intensities: 形状为 (n_angles, n_pixels) 的强度矩阵
        angles_deg: 角度数组 (度)，长度为 n_angles

    Returns:
        dict with keys: "amplitude", "phase_offset_deg", "offset", "r_squared"
        每个值都是长度为 n_pixels 的 numpy 数组
    """
    angles_rad = np.deg2rad(angles_deg)
    n_pixels = intensities.shape[1]

    amplitudes = np.zeros(n_pixels)
    phase_offsets = np.zeros(n_pixels)
    offsets = np.zeros(n_pixels)
    r_squared = np.zeros(n_pixels)

    for i in range(n_pixels):
        y = intensities[:, i]
        try:
            # I(θ) = A*cos²(θ-θ₀) + B
            #      = (A/2)*cos(2θ-2θ₀) + (A/2 + B)
            # 线性化: y = a*cos(2θ) + b*sin(2θ) + c
            cos_2theta = np.cos(2 * angles_rad)
            sin_2theta = np.sin(2 * angles_rad)
            X = np.column_stack([cos_2theta, sin_2theta, np.ones_like(angles_rad)])
            coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)

            a, b, c = coeffs
            amplitude = 2 * np.sqrt(a**2 + b**2)
            phase_offset = np.arctan2(b, a) / 2  # 弧度
            offset_val = c - amplitude / 2

            amplitudes[i] = amplitude
            phase_offsets[i] = np.rad2deg(phase_offset) % 180
            offsets[i] = offset_val

            # R²
            y_pred = amplitude/2 * np.cos(2*(angles_rad - phase_offset)) + amplitude/2 + offset_val
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared[i] = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        except np.linalg.LinAlgError:
            amplitudes[i] = 0
            phase_offsets[i] = 0
            offsets[i] = 0
            r_squared[i] = 0

    return {
        "amplitude": amplitudes,
        "phase_offset_deg": phase_offsets,
        "offset": offsets,
        "r_squared": r_squared,
    }
