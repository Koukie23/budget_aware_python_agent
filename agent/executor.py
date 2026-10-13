"""Run generated code against tests in an isolated process or Docker container."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from agent.config import MEMORY_LIMIT_MB, TEST_TIMEOUT_SEC

DOCKER_IMAGE = "python:3.11-slim"

RUNNER_SOURCE = r'''
import json, sys, traceback
payload = json.load(open("/work/payload.json" if len(sys.argv) < 2 else sys.argv[1]))
results = []
ns = {}
try:
    exec(compile(payload["code"], "<solution>", "exec"), ns)
except Exception as exc:
    err = f"{type(exc).__name__}: {exc}"
    for t in payload["tests"]:
        results.append({"test": t, "passed": False, "error": err, "kind": "load_error"})
    print(json.dumps({"results": results}))
    sys.exit(0)
for imp in payload.get("imports") or []:
    exec(imp, ns)
for t in payload["tests"]:
    try:
        exec(t, ns)
        results.append({"test": t, "passed": True, "error": None, "kind": "passed"})
    except AssertionError as exc:
        results.append({"test": t, "passed": False, "error": f"AssertionError: {exc}", "kind": "assertion"})
    except Exception as exc:
        results.append({"test": t, "passed": False, "error": f"{type(exc).__name__}: {exc}", "kind": "exception"})
print(json.dumps({"results": results}))
'''


@dataclass
class TestReport:
    results: list[dict]
    passed: int
    total: int
    status: str  # passed | failed | timeout | system_error
    duration_sec: float
    error: str | None = None

    @property
    def all_passed(self) -> bool:
        return self.status == "passed"


def _summarize(results: list[dict], duration: float) -> TestReport:
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    status = "passed" if total and passed == total else "failed"
    return TestReport(results, passed, total, status, duration)


DOCKER_FALLBACK_PATHS = (
    Path.home() / ".docker" / "bin" / "docker",
    Path("/usr/local/bin/docker"),
    Path("/opt/homebrew/bin/docker"),
    Path("/Applications/Docker.app/Contents/Resources/bin/docker"),
)


def docker_binary() -> str | None:
    found = shutil.which("docker")
    if found:
        return found
    for candidate in DOCKER_FALLBACK_PATHS:
        if candidate.is_file():
            return str(candidate)
    return None


def run_tests(
    code: str,
    tests: list[str],
    imports: list[str] | None = None,
    backend: str = "docker",
    timeout_sec: int = TEST_TIMEOUT_SEC,
) -> TestReport:
    payload = {"code": code, "tests": tests, "imports": imports or []}
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="bapa_run_") as tmp:
        work = Path(tmp)
        (work / "payload.json").write_text(json.dumps(payload))
        (work / "runner.py").write_text(RUNNER_SOURCE)

        if backend == "docker":
            docker = docker_binary()
            if docker is None:
                return TestReport(
                    [], 0, len(tests), "system_error", 0.0,
                    "docker command not found; start Docker Desktop or use --executor subprocess",
                )
            cmd = [
                docker, "run", "--rm",
                "--network", "none",
                "--memory", f"{MEMORY_LIMIT_MB}m",
                "--pids-limit", "64",
                "--cpus", "1",
                "--read-only",
                "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges",
                "--user", "65534:65534",
                "-v", f"{work}:/work:ro",
                DOCKER_IMAGE,
                "timeout", "-s", "KILL", f"{timeout_sec}s",
                "python", "-I", "/work/runner.py",
            ]
            # The docker CLI looks up credential helpers next to itself via PATH.
            env = dict(os.environ)
            env["PATH"] = f"{Path(docker).parent}{os.pathsep}{env.get('PATH', '')}"
        elif backend == "subprocess":
            cmd = [sys.executable, "-I", str(work / "runner.py"), str(work / "payload.json")]
            env = {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}
        else:
            raise ValueError(f"unknown executor backend: {backend}")

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec + (20 if backend == "docker" else 0),
                env=env,
                cwd=str(work),
            )
        except subprocess.TimeoutExpired:
            duration = time.monotonic() - start
            results = [
                {"test": t, "passed": False, "error": "Timeout", "kind": "timeout"} for t in tests
            ]
            return TestReport(results, 0, len(tests), "timeout", duration, "execution timed out")

        duration = time.monotonic() - start
        if backend == "docker" and proc.returncode in (124, 137):
            results = [
                {"test": t, "passed": False, "error": "Timeout", "kind": "timeout"} for t in tests
            ]
            return TestReport(results, 0, len(tests), "timeout", duration, "execution timed out")
        if proc.returncode != 0:
            return TestReport(
                [], 0, len(tests), "system_error", duration,
                (proc.stderr or proc.stdout).strip()[-500:] or f"exit code {proc.returncode}",
            )
        try:
            data = json.loads(proc.stdout.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            return TestReport(
                [], 0, len(tests), "system_error", duration,
                f"unparseable runner output: {proc.stdout[-300:]}",
            )
        return _summarize(data["results"], duration)
