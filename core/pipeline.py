"""管道编排引擎。

Pipeline 是 CommandMode 的架构核心，支持：
- 线性管道：顺序执行 Operation 列表
- 错误策略：重试 / 跳过 / 中止
- 步骤回调：GUI 可通过 on_step 获取实时进度
- 暂停/恢复/停止控制
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
from typing import Callable, Optional

from operations.base import Operation, OperationStatus


class RetryAction(Enum):
    """重试决策。"""
    RETRY = "retry"
    SKIP = "skip"
    ABORT = "abort"


class ErrorStrategy(ABC):
    """错误处理策略抽象基类。"""

    @abstractmethod
    def handle(self, step: Operation, error: Exception,
               ctx) -> RetryAction:
        """决定如何处理操作失败。

        Args:
            step: 失败的操作
            error: 发生的异常
            ctx: ExperimentContext

        Returns:
            重试 / 跳过 / 中止
        """
        ...


class RetryStrategy(ErrorStrategy):
    """重试策略：失败后等待并重试指定次数。

    Usage:
        RetryStrategy(max_retries=3, delay_seconds=5)
    """

    def __init__(self, max_retries: int = 3, delay_seconds: float = 5.0):
        self.max_retries = max_retries
        self.delay_seconds = delay_seconds

    def handle(self, step: Operation, error: Exception,
               ctx) -> RetryAction:
        attempts = getattr(step, '_retry_count', 0) + 1
        step._retry_count = attempts

        if attempts <= self.max_retries:
            ctx.logger.warning(
                f"操作 '{step.name}' 失败 (尝试 {attempts}/{self.max_retries}): {error}"
            )
            ctx.logger.info(f"等待 {self.delay_seconds}s 后重试...")
            time.sleep(self.delay_seconds)
            return RetryAction.RETRY
        else:
            ctx.logger.error(
                f"操作 '{step.name}' 失败已达最大重试次数 ({self.max_retries})"
            )
            return RetryAction.SKIP


class SkipStrategy(ErrorStrategy):
    """跳过策略：忽略错误，记录警告后继续。"""

    def handle(self, step: Operation, error: Exception,
               ctx) -> RetryAction:
        ctx.logger.warning(f"操作 '{step.name}' 失败，已跳过: {error}")
        return RetryAction.SKIP


class AbortStrategy(ErrorStrategy):
    """中止策略：立即停止管道。"""

    def handle(self, step: Operation, error: Exception,
               ctx) -> RetryAction:
        ctx.logger.error(f"操作 '{step.name}' 失败，中止管道: {error}")
        return RetryAction.ABORT


@dataclass
class StepResult:
    """单步执行结果。"""
    step_name: str
    status: OperationStatus
    result: Optional[dict] = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0


@dataclass
class PipelineResult:
    """管道执行结果。"""
    pipeline_name: str
    total_steps: int
    status: str = "running"  # "done" | "failed" | "stopped"
    completed_steps: int = 0
    failed_steps: int = 0
    skipped_steps: int = 0
    step_results: list = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0


class Pipeline:
    """线性管道：顺序执行一组 Operation。

    Usage:
        pipeline = Pipeline("MyExperiment", [
            MotorHome("vis_rotator"),
            AcquireSpectrum("data", exposure_ms=60000),
        ])
        result = pipeline.run(ctx)
    """

    def __init__(
        self,
        name: str,
        steps: list,
        on_error: Optional[ErrorStrategy] = None,
        on_step: Optional[Callable] = None,
        on_complete: Optional[Callable] = None,
    ):
        """创建管道。

        Args:
            name: 管道名称
            steps: Operation 序列
            on_error: 错误处理策略 (默认 SkipStrategy)
            on_step: 每步状态变化回调 (step, status, ctx) -> None
            on_complete: 管道完成回调 (ctx) -> None
        """
        self.name = name
        self.steps = steps
        self.on_error = on_error or SkipStrategy()
        self.on_step = on_step
        self.on_complete = on_complete

    def run(self, ctx) -> PipelineResult:
        """执行管道。

        Args:
            ctx: ExperimentContext 实例

        Returns:
            PipelineResult: 执行结果统计
        """
        ctx.reset_flags()

        result = PipelineResult(
            pipeline_name=self.name,
            status="running",
            total_steps=len(self.steps),
            start_time=datetime.now(),
        )

        ctx.logger.info(f"管道 '{self.name}' 开始, 共 {len(self.steps)} 步")

        for i, step in enumerate(self.steps):
            # 检查是否要暂停
            while ctx.should_pause and not ctx.should_stop:
                time.sleep(0.5)
            # 检查是否要停止
            if ctx.should_stop:
                ctx.logger.info(f"管道在第 {i+1} 步前被停止")
                result.status = "stopped"
                break

            step_result = self._execute_step(step, ctx, i)
            result.step_results.append(step_result)

            if step_result.status == OperationStatus.DONE:
                result.completed_steps += 1
            elif step_result.status == OperationStatus.FAILED:
                result.failed_steps += 1
            elif step_result.status == OperationStatus.SKIPPED:
                result.skipped_steps += 1

        if result.status == "running":
            result.status = "done"

        result.end_time = datetime.now()
        ctx.status = result.status

        duration = result.duration_seconds
        ctx.logger.info(
            f"管道 '{self.name}' {result.status}, "
            f"耗时: {duration:.1f}s, "
            f"成功: {result.completed_steps}, "
            f"失败: {result.failed_steps}, "
            f"跳过: {result.skipped_steps}"
        )

        if self.on_complete:
            self.on_complete(ctx)

        return result

    def _execute_step(self, step: Operation, ctx, idx: int) -> StepResult:
        """执行单个步骤，含校验和错误处理。"""
        step_result = StepResult(
            step_name=step.name,
            status=OperationStatus.PENDING,
            start_time=datetime.now(),
        )

        # 校验
        try:
            valid = step.validate(ctx)
        except Exception as e:
            ctx.logger.warning(f"步骤 '{step.name}' 校验异常: {e}")
            valid = False

        if not valid:
            step.set_status(OperationStatus.SKIPPED)
            step_result.status = OperationStatus.SKIPPED
            step_result.end_time = datetime.now()
            self._notify_step(step, OperationStatus.SKIPPED, ctx)
            ctx.logger.info(f"[{idx+1}/{len(self.steps)}] 跳过: {step.name}")
            return step_result

        # 执行
        while True:
            step.set_status(OperationStatus.RUNNING)
            self._notify_step(step, OperationStatus.RUNNING, ctx)
            ctx.logger.info(f"[{idx+1}/{len(self.steps)}] 执行: {step.name}")

            try:
                output = step.execute(ctx)
                step.set_status(OperationStatus.DONE)
                step_result.status = OperationStatus.DONE
                step_result.result = output
                step_result.end_time = datetime.now()
                self._notify_step(step, OperationStatus.DONE, ctx)
                ctx.logger.info(
                    f"[{idx+1}/{len(self.steps)}] 完成: {step.name} "
                    f"({step_result.duration_seconds:.1f}s)"
                )
                return step_result

            except Exception as e:
                action = self.on_error.handle(step, e, ctx)

                if action == RetryAction.RETRY:
                    # 重试前清理
                    try:
                        step.rollback(ctx)
                    except Exception:
                        pass
                    continue

                elif action == RetryAction.SKIP:
                    step.set_status(OperationStatus.SKIPPED)
                    step_result.status = OperationStatus.SKIPPED
                    step_result.error = str(e)
                    step_result.end_time = datetime.now()
                    self._notify_step(step, OperationStatus.SKIPPED, ctx)
                    ctx.logger.warning(
                        f"[{idx+1}/{len(self.steps)}] 跳过失败步骤: {step.name}"
                    )
                    return step_result

                elif action == RetryAction.ABORT:
                    step.set_status(OperationStatus.FAILED)
                    step_result.status = OperationStatus.FAILED
                    step_result.error = str(e)
                    step_result.end_time = datetime.now()
                    self._notify_step(step, OperationStatus.FAILED, ctx)
                    ctx.stop()
                    ctx.logger.error(
                        f"[{idx+1}/{len(self.steps)}] 中止: {step.name}"
                    )
                    return step_result

    def _notify_step(self, step: Operation, status: OperationStatus, ctx):
        """通知步骤状态变化。"""
        if self.on_step:
            try:
                self.on_step(step, status, ctx)
            except Exception:
                pass  # 回调不应影响管道执行
