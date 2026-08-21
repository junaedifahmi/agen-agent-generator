"""Guardrails for the Agen elicitor agent.

Two layers:
1. `PromptInjectionGuardrail` -- Agno's built-in detector for classic
   injection phrases ("ignore previous instructions", "developer mode", …).
2. `ScopeLockGuardrail` -- a custom guardrail keeping the conversation
   inside the elicitation task, so a user can't redirect Agen into acting
   as a general-purpose assistant, revealing its system prompt, or running
   arbitrary instructions unrelated to requirements gathering.
"""

from __future__ import annotations

import re

from agno.exceptions import CheckTrigger, InputCheckError
from agno.guardrails import BaseGuardrail, PromptInjectionGuardrail
from agno.run.agent import RunInput

_OFF_SCOPE_PATTERNS = [
    r"ignore (all|any|your) (previous|prior|above) instructions",
    r"reveal (your|the) system prompt",
    r"act as (?!.*business)",  # "act as X" outside a business-context request
    r"you are now (?!agen)",
    r"disregard (your|the) (rules|guardrails|instructions)",
]


class ScopeLockGuardrail(BaseGuardrail):
    """Blocks attempts to pull Agen out of its elicitor role."""

    def __init__(self) -> None:
        self._compiled = [re.compile(p, re.IGNORECASE) for p in _OFF_SCOPE_PATTERNS]

    def check(self, run_input: RunInput) -> None:
        text = str(run_input.input_content or "")
        for pattern in self._compiled:
            if pattern.search(text):
                raise InputCheckError(
                    "This message tries to change Agen's role or override its "
                    "instructions, which isn't allowed. Please rephrase your "
                    "business requirement instead.",
                    check_trigger=CheckTrigger.INPUT_NOT_ALLOWED,
                )

    async def async_check(self, run_input: RunInput) -> None:
        self.check(run_input)


def default_guardrails() -> list[BaseGuardrail]:
    """The guardrail stack attached to every Agen agent instance."""
    return [PromptInjectionGuardrail(), ScopeLockGuardrail()]
