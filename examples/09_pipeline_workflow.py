"""
示例 09: 管道序列编排

学习目标：
- 理解 Pipeline 的执行流程
- 使用步骤回调监控进度
- 使用错误策略处理异常

此示例使用 mock 数据，无需硬件即可运行。
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.context import ExperimentContext
from core.pipeline import Pipeline, RetryStrategy, SkipStrategy, AbortStrategy
from operations.base import Operation, OperationStatus
from operations.utility_ops import Sleep, LogMessage


class MockMove(Operation):
    """模拟电机移动操作。"""

    def __init__(self, name: str, target: float, fail: bool = False):
        super().__init__(f"Move({name} -> {target})")
        self.target = target
        self._should_fail = fail
        self._retry_count = 0

    def execute(self, ctx) -> dict:
        if self._should_fail and self._retry_count < 1:
            self._retry_count += 1
            raise RuntimeError(f"模拟: 电机 {self.name} 移动失败")
        time.sleep(0.1)
        return {"target": self.target, "success": True}


class MockAcquire(Operation):
    """模拟光谱采集操作。"""

    def __init__(self, data_name: str, frames: int = 1):
        super().__init__(f"Acquire({data_name})")
        self.data_name = data_name
        self.frames = frames

    def execute(self, ctx) -> dict:
        time.sleep(0.2)
        ctx.data["last_spectrum"] = {"name": self.data_name, "pixels": 100}
        return {"data_name": self.data_name, "frames": self.frames}


def step_callback(step: Operation, status: OperationStatus, ctx):
    """每步状态变化时调用。GUI 可基于此更新进度条。"""
    bar = "[==========]" if status == OperationStatus.DONE else "[...       ]"
    print(f"  {bar} {step.name} -> {status.value}")


def main():
    print("=" * 50)
    print("示例 09: 管道序列编排 (Mock)")
    print("=" * 50)

    ctx = ExperimentContext()
    ctx.reset_flags()

    # 编排实验序列
    pipeline = Pipeline("DemoExperiment", [
        LogMessage("实验开始"),
        Sleep(0.1),

        # 校准步骤
        LogMessage("步骤 1: 校准设备"),
        MockMove("vis_rotator", 0.0),
        MockMove("sfg_rotator", 0.0),

        # 采集步骤
        LogMessage("步骤 2: SSP 采集"),
        MockMove("vis_rotator", 45.0),
        MockAcquire("sample_ssp"),

        LogMessage("步骤 3: PPP 采集"),
        MockMove("sfg_rotator", 90.0),
        MockAcquire("sample_ppp"),

        # 模拟一个会失败的步骤（自动重试后成功）
        LogMessage("步骤 4: 带重试的路径扫描"),
        MockMove("delay_stage", 150.0, fail=True),  # 第一次失败，自动重试
        MockAcquire("sample_scan"),

        # 清理
        LogMessage("实验结束，设备归位"),
        MockMove("vis_rotator", 0.0),
        MockMove("sfg_rotator", 0.0),
    ],
        on_error=RetryStrategy(max_retries=2, delay_seconds=0.1),
        on_step=step_callback,
        on_complete=lambda c: print("\n✓ 实验完成回调已触发"),
    )

    # 运行
    print(f"\n管道 '{pipeline.name}' 包含 {len(pipeline.steps)} 个步骤\n")
    result = pipeline.run(ctx)

    # 结果统计
    print(f"\n{'=' * 50}")
    print(f"结果: {result.status.upper()}")
    print(f"总耗时: {result.duration_seconds:.2f}s")
    print(f"成功: {result.completed_steps}  失败: {result.failed_steps}  跳过: {result.skipped_steps}")

    # 上下文中的数据
    if "last_spectrum" in ctx.data:
        print(f"\n最后采集: {ctx.data['last_spectrum']}")


if __name__ == "__main__":
    main()
