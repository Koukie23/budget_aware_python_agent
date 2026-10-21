"""FastAPI agent service. Runs the T2 state machine in the background and reports to Express."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from pathlib import Path

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent.controller import Step, run_agent
from agent.config import DEFAULT_ADAPTER_DIR, FINETUNED_MODEL_ID
from agent.models import CLIENT_KINDS, MOCK_SCENARIOS, LocalLoraClient, make_client
from agent.policy import PREFERENCES
from agent.task import CodingTask

ROOT = Path(__file__).resolve().parents[1]
SAMPLES_PATH = ROOT / "data" / "samples" / "t1_samples.jsonl"
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:3000")
EXECUTOR = os.environ.get("AGENT_EXECUTOR", "docker")
CLIENT_KIND = os.environ.get("AGENT_CLIENT", "local")
_CLIENT = None

logger = logging.getLogger("agent_service")
app = FastAPI(title="Budget-Aware Agent Service")


class RunRequest(BaseModel):
    task_id: int
    requirement: str
    function_name: str
    function_signature: str
    feedback_tests: list[str] = Field(min_length=1)
    test_imports: list[str] = []
    preference: str
    budget_usd: float = Field(gt=0)
    mock_scenario: str = "pass"
    example_task_id: int | None = None


def _target_code(example_task_id: int | None) -> str | None:
    if example_task_id is None:
        return None
    with SAMPLES_PATH.open() as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                if rec["task_id"] == example_task_id:
                    return rec.get("target_code")
    return None


def _post(path: str, payload: dict) -> None:
    try:
        httpx.post(f"{BACKEND_URL}{path}", json=payload, timeout=10).raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("callback %s failed: %s", path, exc)


def _execute(req: RunRequest) -> None:
    base = f"/internal/tasks/{req.task_id}"
    task = CodingTask(
        task_id=req.task_id,
        requirement=req.requirement,
        function_name=req.function_name,
        function_signature=req.function_signature,
        feedback_tests=req.feedback_tests,
        test_imports=req.test_imports,
        target_code=_target_code(req.example_task_id),
    )

    def on_step(step: Step) -> None:
        _post(f"{base}/steps", asdict(step))

    try:
        _post(f"{base}/started", {"executor": EXECUTOR})
        result = run_agent(
            task,
            req.preference,
            req.budget_usd,
            _get_client(req.mock_scenario),
            executor=EXECUTOR,
            on_step=on_step,
        )
        summary = result.to_dict()
        summary.pop("steps")
        _post(f"{base}/finish", summary)
    except Exception as exc:  # report instead of leaving the task stuck in running
        logger.exception("run %s crashed", req.task_id)
        _post(f"{base}/finish", {"status": "system_error", "stop_reason": f"agent crashed: {exc}"})


def _get_client(mock_scenario: str):
    global _CLIENT
    if CLIENT_KIND == "mock":
        return make_client("mock", mock_scenario=mock_scenario)
    if _CLIENT is None:
        _CLIENT = make_client("local")
        _CLIENT.load()
    return _CLIENT


@app.on_event("startup")
def _preload() -> None:
    if CLIENT_KIND == "local":
        logger.info("loading local LoRA from %s", DEFAULT_ADAPTER_DIR)
        _get_client("pass")


@app.get("/health")
def health() -> dict:
    loaded = isinstance(_CLIENT, LocalLoraClient) and _CLIENT._model is not None
    device = str(_CLIENT.device) if isinstance(_CLIENT, LocalLoraClient) and _CLIENT.device else None
    return {
        "status": "ok",
        "executor": EXECUTOR,
        "client": CLIENT_KIND,
        "finetuned_model": FINETUNED_MODEL_ID,
        "adapter": str(DEFAULT_ADAPTER_DIR) if CLIENT_KIND == "local" else None,
        "device": device,
        "loaded": loaded,
    }


@app.get("/options")
def options() -> dict:
    return {
        "preferences": list(PREFERENCES),
        "client": CLIENT_KIND,
        "finetuned_model": FINETUNED_MODEL_ID,
        "mock_scenarios": list(MOCK_SCENARIOS) if CLIENT_KIND == "mock" else [],
    }


@app.post("/runs", status_code=202)
def start_run(req: RunRequest, background: BackgroundTasks) -> dict:
    if req.preference not in PREFERENCES:
        raise HTTPException(422, f"preference must be one of {PREFERENCES}")
    if CLIENT_KIND not in CLIENT_KINDS:
        raise HTTPException(500, f"AGENT_CLIENT must be one of {CLIENT_KINDS}")
    if req.mock_scenario not in MOCK_SCENARIOS:
        raise HTTPException(422, f"mock_scenario must be one of {MOCK_SCENARIOS}")
    background.add_task(_execute, req)
    return {"accepted": True, "task_id": req.task_id, "client": CLIENT_KIND}
