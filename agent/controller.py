"""Explicit state machine: generate -> test -> accept | repair | escalate | stop."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field

from agent.config import MAX_MODEL_CALLS
from agent.executor import TestReport, run_tests
from agent.models import ModelClient, build_prompt, estimate_call_cost
from agent.policy import DESCRIPTIONS, plan_for
from agent.task import CodingTask

SYSTEM_ERROR_RETRIES = 1


@dataclass
class Step:
    index: int
    action: str  # generate | repair | escalate
    model_id: str
    estimated_cost_usd: float
    actual_cost_usd: float
    input_tokens: int
    output_tokens: int
    model_latency_sec: float
    code: str
    test_status: str
    tests_passed: int
    tests_total: int
    test_duration_sec: float
    error_summary: str | None


@dataclass
class RunResult:
    task_id: int | str
    preference: str
    budget_usd: float
    executor: str
    policy: str
    status: str  # succeeded | failed | budget_exhausted | system_error
    stop_reason: str
    final_code: str | None
    model_calls: int
    total_estimated_cost_usd: float
    total_actual_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    wall_time_sec: float
    steps: list[Step] = field(default_factory=list)
    hidden_test_report: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def summarize_errors(report: TestReport, limit: int = 3) -> str:
    if report.status == "system_error":
        return f"System error: {report.error}"
    failed = [r for r in report.results if not r["passed"]][:limit]
    lines = [f"{report.passed}/{report.total} tests passed."]
    for r in failed:
        lines.append(f"- {r['test']}\n  -> {r['error']}")
    return "\n".join(lines)


def _test_with_retry(code: str, task: CodingTask, executor: str) -> TestReport:
    report = run_tests(code, task.feedback_tests, task.test_imports, backend=executor)
    retries = 0
    while report.status == "system_error" and retries < SYSTEM_ERROR_RETRIES:
        retries += 1
        report = run_tests(code, task.feedback_tests, task.test_imports, backend=executor)
    return report


def run_agent(
    task: CodingTask,
    preference: str,
    budget_usd: float,
    client: ModelClient,
    executor: str = "docker",
    on_step: Callable[[Step], None] | None = None,
) -> RunResult:
    start = time.monotonic()
    plan = plan_for(preference)[:MAX_MODEL_CALLS]
    result = RunResult(
        task_id=task.task_id,
        preference=preference,
        budget_usd=budget_usd,
        executor=executor,
        policy=DESCRIPTIONS[preference],
        status="failed",
        stop_reason="",
        final_code=None,
        model_calls=0,
        total_estimated_cost_usd=0.0,
        total_actual_cost_usd=0.0,
        total_input_tokens=0,
        total_output_tokens=0,
        wall_time_sec=0.0,
    )

    previous_code: str | None = None
    error_summary: str | None = None

    for action, model_id in plan:
        prompt = build_prompt(task, previous_code, error_summary)
        estimate = estimate_call_cost(model_id, prompt)
        remaining = budget_usd - result.total_actual_cost_usd
        if estimate > remaining:
            result.status = "budget_exhausted"
            result.stop_reason = (
                f"next {action} on {model_id} estimated ${estimate:.6f} "
                f"> remaining ${remaining:.6f}"
            )
            break

        response = client.generate(model_id, prompt, task)
        result.model_calls += 1
        result.total_estimated_cost_usd += estimate
        result.total_actual_cost_usd += response.cost_usd
        result.total_input_tokens += response.input_tokens
        result.total_output_tokens += response.output_tokens
        result.final_code = response.code

        report = _test_with_retry(response.code, task, executor)
        error_summary = None if report.all_passed else summarize_errors(report)
        result.steps.append(
            Step(
                index=result.model_calls,
                action=action,
                model_id=model_id,
                estimated_cost_usd=estimate,
                actual_cost_usd=response.cost_usd,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                model_latency_sec=response.latency_sec,
                code=response.code,
                test_status=report.status,
                tests_passed=report.passed,
                tests_total=report.total,
                test_duration_sec=report.duration_sec,
                error_summary=error_summary,
            )
        )
        if on_step is not None:
            on_step(result.steps[-1])

        if report.all_passed:
            result.status = "succeeded"
            result.stop_reason = "all feedback tests passed"
            break
        if report.status == "system_error":
            result.status = "system_error"
            result.stop_reason = f"executor failed after {SYSTEM_ERROR_RETRIES} retry: {report.error}"
            break

        previous_code = response.code
    else:
        result.status = "failed"
        result.stop_reason = f"all {len(plan)} planned attempts failed (preference={preference})"

    if task.hidden_tests and result.final_code is not None:
        hidden = run_tests(result.final_code, task.hidden_tests, task.test_imports, backend=executor)
        result.hidden_test_report = {
            "status": hidden.status,
            "passed": hidden.passed,
            "total": hidden.total,
        }

    result.wall_time_sec = time.monotonic() - start
    return result
