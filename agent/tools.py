"""Tools Agen calls to record elicitation answers into session state.

Each tool corresponds to one piece of the feature model. The instructions
tell Agen to call the matching tool the moment the user gives an answer,
*before* replying -- that's what keeps `session_state` (and therefore what
Agen sees reflected back in its own instructions next turn) always in sync
with what's actually been said, instead of relying on re-reading the whole
conversation and guessing.
"""

from __future__ import annotations

from agno.run import RunContext

from .feature_model import ConnectorType, KnowledgeBaseMode


def record_business_context(run_context: RunContext, business_name: str) -> str:
    """Record the name of the business the chatbot is being built for."""
    run_context.session_state["business_name"] = business_name
    return f"Recorded business name: {business_name}"


def set_connector(run_context: RunContext, connector_type: str) -> str:
    """Record which channel the chatbot will run on.

    connector_type must be one of: whatsapp, webapp, telegram.
    """
    normalized = connector_type.strip().lower()
    valid = {c.value for c in ConnectorType}
    if normalized not in valid:
        return f"Invalid connector_type '{connector_type}'. Must be one of: {sorted(valid)}."
    run_context.session_state["connector_type"] = normalized
    return f"Recorded connector: {normalized}"


def set_knowledge_base(run_context: RunContext, enabled: bool, mode: str | None = None) -> str:
    """Record whether the chatbot has a knowledge base and its retrieval mode.

    mode must be 'vector' or 'api' when enabled is true; omit it otherwise.
    """
    if enabled:
        if not mode:
            return "enabled is true but mode was not given; ask the user vector or api."
        normalized_mode = mode.strip().lower()
        valid = {m.value for m in KnowledgeBaseMode}
        if normalized_mode not in valid:
            return f"Invalid mode '{mode}'. Must be one of: {sorted(valid)}."
        run_context.session_state["kb_enabled"] = True
        run_context.session_state["kb_mode"] = normalized_mode
        return f"Recorded knowledge base: enabled, mode={normalized_mode}"

    run_context.session_state["kb_enabled"] = False
    run_context.session_state["kb_mode"] = None
    return "Recorded knowledge base: disabled"


def add_skill(run_context: RunContext, name: str, description: str) -> str:
    """Record one capability the chatbot should have. Call once per skill."""
    skills = run_context.session_state.setdefault("skills", [])
    skills.append({"name": name, "description": description})
    return f"Recorded skill: {name} (total so far: {len(skills)})"


def finish_skills(run_context: RunContext) -> str:
    """Mark the skills list as complete once the user has no more to add.

    Only call this after at least one skill has been recorded with
    add_skill -- a chatbot needs at least one capability.
    """
    skills = run_context.session_state.get("skills", [])
    if not skills:
        return "No skills recorded yet; ask what the chatbot should be able to do before finishing."
    run_context.session_state["skills_done"] = True
    return f"Skills finalized: {len(skills)} recorded."


def set_persona(
    run_context: RunContext,
    name: str,
    system_prompt: str,
    tone: str = "friendly and professional",
    language: str = "id",
    escalation_rule: str | None = None,
) -> str:
    """Record the chatbot's persona once name, tone, language, and any
    escalation rule are known. Draft system_prompt yourself from the
    conversation -- don't ask the user to write it."""
    state = run_context.session_state
    state["persona_name"] = name
    state["persona_system_prompt"] = system_prompt
    state["persona_tone"] = tone
    state["persona_language"] = language
    state["persona_escalation_rule"] = escalation_rule
    return f"Recorded persona: {name}"


def get_elicitation_progress(run_context: RunContext) -> dict:
    """Return everything recorded so far. Call this if you're ever unsure
    what's already been resolved, instead of guessing from memory."""
    return dict(run_context.session_state)


ELICITOR_TOOLS = [
    record_business_context,
    set_connector,
    set_knowledge_base,
    add_skill,
    finish_skills,
    set_persona,
    get_elicitation_progress,
]
"""Tools for recording elicitation answers.

`generate_chatbot_now` (the tool that actually triggers generation) lives
separately in `agent/generation_tool.py` and is added to the agent's tool
list alongside these in `agent/elicitor.py` -- kept apart because it's the
one tool gated by human-in-the-loop confirmation, not just state-tracking.
"""
