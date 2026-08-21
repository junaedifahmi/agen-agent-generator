"""Agen: the SPLE-driven elicitor agent.

Conversation pattern with a single underlying Agno session:

1. Free-form phase: the agent talks to the business user in plain language,
   mapping what they say onto the feature model's mandatory features
   (connector, knowledge_base, skills, persona). The moment the user
   answers something, Agen calls the matching tool in `agent/tools.py`,
   which records it into `session_state` (see `agent/state.py`). That
   state is rendered straight back into Agen's own instructions on the
   next turn via Agno's `{key}` placeholder substitution -- so "what's
   already been resolved" is always read from a structured record instead
   of being re-derived by the model scanning the whole transcript, which is
   what caused it to lose track and loop back to already-answered
   questions on longer conversations.

2. Generation phase: once every feature area is resolved, Agen summarizes
   what it's gathered and asks the user whether to generate the chatbot
   now. If they agree, it calls `generate_chatbot_now` (see
   `agent/generation_tool.py`) -- but that tool is registered with
   `requires_confirmation=True`, so Agno pauses the run right there rather
   than letting it execute. The caller (see `main.py`) is what shows the
   pending call to the user and asks for an explicit yes/no before
   resuming with `agent.continue_run(...)`. That confirmation gate is
   independent of anything Agen said in the chat -- it's the actual human-
   in-the-loop control, not a courtesy.

Agen's system prompt itself lives in `agent/prompts/elicitor_system_prompt.md`
(loaded by `load_instructions()` below), not inline in this module.
"""

from __future__ import annotations

from pathlib import Path

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openrouter import OpenRouter

from .config import settings
from .generation_tool import generate_chatbot_now
from .guardrails import default_guardrails
from .state import initial_session_state
from .tools import ELICITOR_TOOLS

PROMPTS_DIR = Path(__file__).parent / "prompts"
ELICITOR_SYSTEM_PROMPT_PATH = PROMPTS_DIR / "elicitor_system_prompt.md"


def load_instructions() -> str:
    """Load Agen's system prompt from its markdown file, unmodified.

    Kept out of the Python source so the prompt can be read, reviewed, and
    edited (e.g. by a non-engineer refining Agen's elicitation style)
    without touching code. The file's `{business_name}`-style placeholders
    are left as-is here -- Agno substitutes those itself at runtime from
    live session state.
    """
    return ELICITOR_SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def build_agen_agent() -> Agent:
    settings.validate()
    db = SqliteDb(db_file=settings.db_file)
    return Agent(
        id="agen",
        name="Agen - Agent Generator Elicitor",
        model=OpenRouter(
            id=settings.model_id,
            api_key=settings.openrouter_api_key,
            max_tokens=settings.max_tokens,
        ),
        db=db,
        instructions=load_instructions(),
        pre_hooks=default_guardrails(),
        tools=[*ELICITOR_TOOLS, generate_chatbot_now],
        session_state=initial_session_state(),
        add_session_state_to_context=True,
        add_history_to_context=True,
        markdown=False,
    )
