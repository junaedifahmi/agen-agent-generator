"""Structured elicitation progress, tracked via Agno session state.

Relying on the model to re-read the whole transcript every turn and
correctly infer "have I already asked about skills?" is fragile -- on long
conversations it drifts and loops back to re-ask things the user already
answered. Instead, every answer gets recorded into `session_state` through
an explicit tool call the moment it's given, and the current progress is
rendered straight into the agent's instructions (via Agno's `{key}`
placeholder substitution) so the model always sees ground truth rather than
having to reconstruct it.

This module is the single source of truth for that state's shape.
"""

from __future__ import annotations

from typing import Any


def initial_session_state() -> dict[str, Any]:
    """A fresh, empty progress record for a new elicitation session."""
    return {
        "business_name": None,
        "connector_type": None,
        "kb_enabled": None,
        "kb_mode": None,
        "skills": [],
        "skills_done": False,
        "persona_name": None,
        "persona_system_prompt": None,
        "persona_tone": None,
        "persona_language": None,
        "persona_escalation_rule": None,
    }


def is_complete(state: dict[str, Any]) -> bool:
    """Whether every mandatory feature area has been resolved."""
    if not state.get("business_name"):
        return False
    if not state.get("connector_type"):
        return False
    if state.get("kb_enabled") is None:
        return False
    if state["kb_enabled"] and not state.get("kb_mode"):
        return False
    if not state.get("skills_done") or not state.get("skills"):
        return False
    if not state.get("persona_name") or not state.get("persona_system_prompt"):
        return False
    return True
