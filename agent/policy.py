"""Rule-based repair and escalation plans per preference (plan section 3.1)."""

from __future__ import annotations

from agent.config import FINETUNED_MODEL_ID, STRONG_MODEL_ID

PREFERENCES = ("cheap", "balanced", "quality")

# Each plan is the ordered list of (action, model) attempts; the run stops at the first pass.
PLANS: dict[str, list[tuple[str, str]]] = {
    "cheap": [("generate", FINETUNED_MODEL_ID), ("repair", FINETUNED_MODEL_ID)],
    "balanced": [
        ("generate", FINETUNED_MODEL_ID),
        ("repair", FINETUNED_MODEL_ID),
        ("escalate", STRONG_MODEL_ID),
    ],
    "quality": [("generate", FINETUNED_MODEL_ID), ("escalate", STRONG_MODEL_ID)],
}

DESCRIPTIONS = {
    "cheap": "fine-tuned generate -> fine-tuned repair; never call the strong model",
    "balanced": "fine-tuned generate -> fine-tuned repair -> strong model",
    "quality": "fine-tuned generate -> strong model (skip local repair)",
}


def plan_for(preference: str) -> list[tuple[str, str]]:
    if preference not in PLANS:
        raise ValueError(f"preference must be one of {PREFERENCES}")
    return PLANS[preference]
