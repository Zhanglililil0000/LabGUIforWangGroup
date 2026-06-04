"""信号处理模块的单元测试。"""

import numpy as np
import sys
import os

# 确保可以 import core 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.signal_processing import compute_differential_signal, fit_polarization_curve


def test_compute_differential_signal_basic():
    """基本功能测试：已知输入验证输出形状和数值范围。"""
    # 模拟 4 帧数据，每帧 50 个像素，每像素强度逐像素递增
    np.random.seed(42)
    n = 50
    # 每帧逐像素递增 + 随机扰动，确保 max-min > 0
    frame0 = np.arange(n) * 0.1 + 10.0 + np.random.randn(n) * 0.01   # pump on
    frame1 = np.arange(n) * 0.1 + 8.0 + np.random.randn(n) * 0.01    # pump off (弱20%)
    frame2 = np.arange(n) * 0.1 + 10.0 + np.random.randn(n) * 0.01   # pump on
    frame3 = np.arange(n) * 0.1 + 8.0 + np.random.randn(n) * 0.01    # pump off
    intensities = [frame0, frame1, frame2, frame3]

    ret, ret1, ret2 = compute_differential_signal(intensities, frames=4)

    assert len(ret) == n, f"ret length expected {n}, got {len(ret)}"
    assert len(ret1) == n
    assert len(ret2) == n

    # 所有值都应该是有限数值
    assert not np.any(np.isnan(ret)), "ret should not contain NaN"
    assert not np.any(np.isinf(ret)), "ret should not contain Inf"

    # ret1 应该为正（pump on / pump off > 1）
    assert np.all(ret1 > 0), f"ret1 should be positive, min={ret1.min()}"
    # ret2 应该为负（pump off / pump on < 1）
    assert np.all(ret2 < 0), f"ret2 should be negative, max={ret2.max()}"
    # 由于 frame0>>frame1 且 frame2>>frame3, ret1 的跨度更大, 应选中 ret1
    assert np.all(ret > 0), "selected ret should be positive"

    print("  PASS test_compute_differential_signal_basic")


def test_compute_differential_signal_odd_frames_raises():
    """奇数帧应抛出 ValueError。"""
    intensities = [np.ones(10) for _ in range(3)]
    try:
        compute_differential_signal(intensities, frames=3)
        assert False, "应该抛出 ValueError"
    except ValueError:
        pass
    print("  PASS test_compute_differential_signal_odd_frames_raises")


def test_compute_differential_signal_mismatch_raises():
    """帧数不匹配应抛出 ValueError。"""
    intensities = [np.ones(10) for _ in range(4)]
    try:
        compute_differential_signal(intensities, frames=6)
        assert False, "应该抛出 ValueError"
    except ValueError:
        pass
    print("  PASS test_compute_differential_signal_mismatch_raises")


def test_fit_polarization_curve():
    """偏振拟合测试：理想 cos² 曲线应完美拟合。"""
    angles = np.arange(0, 181, 10)
    angles_rad = np.deg2rad(angles)

    true_amplitude = 2.0
    true_phase = np.deg2rad(45)
    true_offset = 1.0

    n_pixels = 5
    intensities = np.zeros((len(angles), n_pixels))
    for i, a in enumerate(angles_rad):
        intensities[i, :] = true_amplitude * np.cos(a - true_phase)**2 + true_offset

    result = fit_polarization_curve(intensities, angles)

    for i in range(n_pixels):
        assert abs(result["amplitude"][i] - true_amplitude) < 0.1, \
            f"amplitude[{i}]={result['amplitude'][i]}"
        assert result["r_squared"][i] > 0.99, \
            f"r_squared[{i}]={result['r_squared'][i]}"

    print("  PASS test_fit_polarization_curve")


def test_config_and_registry():
    """测试配置和注册中心的基本功能。"""
    from core.config import Config
    from core.registry import DeviceRegistry, OperationRegistry

    # Test Config
    import tempfile
    import yaml

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
        yaml.dump({
            "devices": {"vis_rotator": {"serial": "12345", "driver": "cage"}},
            "experiment": {"type": "sfg"},
        }, f)
        tmp_path = f.name

    try:
        config = Config(tmp_path)
        assert config.get("devices.vis_rotator.serial") == "12345"
        assert config.get("experiment.type") == "sfg"
        assert config.get("nonexistent.key", "default") == "default"
        assert config.get_devices() == {"vis_rotator": {"serial": "12345", "driver": "cage"}}
        print("  PASS test_config")
    finally:
        os.unlink(tmp_path)

    # Test Registry - Device
    from devices.base import DeviceBase

    class MockDevice(DeviceBase):
        def connect(self): self._connected = True; return True
        def disconnect(self): self._connected = False
        @property
        def is_connected(self): return self._connected

    DeviceRegistry.register_device_type("mock", MockDevice)
    dev = DeviceRegistry.create_device("mock", "test_dev", {})
    assert DeviceRegistry.get_device("test_dev") is dev
    assert "mock" in DeviceRegistry.list_device_types()
    
    # Cleanup
    DeviceRegistry.clear()
    print("  PASS test_device_registry")

    # Test Registry - Operation
    from operations.base import Operation, OperationStatus

    @OperationRegistry.register
    class MockOperation(Operation):
        def execute(self, ctx):
            ctx.data["mock_executed"] = True
            return {"done": True}

    assert "MockOperation" in OperationRegistry.list_all()
    op = OperationRegistry.create("MockOperation")
    assert op is not None

    OperationRegistry.clear()
    print("  PASS test_operation_registry")


def test_context():
    """测试 ExperimentContext 基本功能。"""
    from core.context import ExperimentContext

    ctx = ExperimentContext()
    assert ctx.status == "initializing"
    ctx.reset_flags()
    assert ctx.status == "running"
    ctx.pause()
    assert ctx.should_pause
    ctx.resume()
    assert not ctx.should_pause
    ctx.stop()
    assert ctx.should_stop

    # 测试设备注册
    ctx.set_device("test", "fake_device")
    assert ctx.get_device("test") == "fake_device"
    try:
        ctx.get_device("nonexistent")
        assert False, "应该抛出 KeyError"
    except KeyError:
        pass

    print("  PASS test_context")


if __name__ == "__main__":
    print("Running signal processing tests...")
    test_compute_differential_signal_basic()
    test_compute_differential_signal_odd_frames_raises()
    test_compute_differential_signal_mismatch_raises()
    test_fit_polarization_curve()

    print("\nRunning config & registry tests...")
    test_config_and_registry()

    print("\nRunning context tests...")
    test_context()

    print("\n" + "=" * 40)
    print("All tests passed!")
