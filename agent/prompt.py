"""Single prompt template used for training (generate) and Agent inference."""

from __future__ import annotations

from typing import Sequence


def _body(requirement: str, function_signature: str, feedback_tests: Sequence[str]) -> str:
    tests = "\n".join(feedback_tests)
    return "\n\n".join(
        [
            "You are an expert Python programmer.",
            f"Task: {requirement}",
            f"Implement exactly this function: {function_signature}",
            f"Your code should pass these tests:\n{tests}",
        ]
    )


def generate_prompt(requirement: str, function_signature: str, feedback_tests: Sequence[str]) -> str:
    return _body(requirement, function_signature, feedback_tests) + "\n\nReturn only one ```python``` code block."


def repair_prompt(
    requirement: str,
    function_signature: str,
    feedback_tests: Sequence[str],
    previous_code: str,
    error_summary: str,
) -> str:
    return "\n\n".join(
        [
            _body(requirement, function_signature, feedback_tests),
            f"Your previous code:\n```python\n{previous_code}\n```",
            f"It failed with:\n{error_summary}",
            "Fix the code.",
            "Return only one ```python``` code block.",
        ]
    )
