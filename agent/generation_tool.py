"""The one tool that actually triggers chatbot generation -- gated by
Agno's human-in-the-loop tool confirmation.

Everything else Agen does (recording connector, knowledge base, skills,
persona) is low-stakes and safe to let the agent do freely. Generating the
chatbot is not -- it's the one irreversible, real-world action in this
whole flow, so it must never fire just because a model decided the
conversation sounded finished. `requires_confirmation=True` makes Agno
pause the run the instant the model tries to call this tool, and it stays
paused until a human explicitly approves or rejects that specific call.
The model's own judgment about whether to *offer* to generate is untrusted
by design; only the human's explicit yes/no here actually lets it run.

The extra `@approval` decorator (stacked on top of `@tool`) marks this as
an admin-approval-gated tool, not just a confirmation-gated one. That's
what makes Agno write a real, DB-backed approval record the moment the run
pauses (`agent.db`, via `agno.run.approval.create_approval_from_pause`) --
which is what lets `demo/server.py`'s AgentOS-backed reviewer page discover
a pending "generate now?" from *any* session through the plain `GET
/approvals` endpoint, instead of needing to already know a session_id.
`main.py`'s single-terminal CLI loop still works exactly as before --
`agent.continue_run(updated_tools=...)` resolves the pause directly and
never touches the approval record at all.
"""

from __future__ import annotations

from pydantic import ValidationError

from agno.approval import approval
from agno.run import RunContext
from agno.tools import tool

from .feature_model import build_spec_from_state
from .generator_stub import generate_chatbot
from .state import is_complete
from .yaml_export import export_spec_to_yaml


@approval
@tool(requires_confirmation=True)
def generate_chatbot_now(run_context: RunContext) -> str:
    """Generate the chatbot from everything recorded in this session.

    Only call this once every feature area (business name, connector,
    knowledge base, at least one skill, persona) has been resolved, and
    only after you've summarized what you've gathered back to the user in
    plain language and they've agreed it's ready. This tool itself will
    still pause for the user's explicit go-ahead before anything actually
    runs, but don't rely on that as a substitute for asking first.
    """
    state = run_context.session_state

    if not is_complete(state):
        return (
            "Not ready yet -- some required information is still missing. "
            "Keep asking the user about whatever's unresolved before "
            "calling this again."
        )

    try:
        spec = build_spec_from_state(state)
    except ValidationError as exc:
        return f"Could not build a valid specification yet: {exc}"

    yaml_path = export_spec_to_yaml(spec)
    generate_chatbot(yaml_path)
    return f"Chatbot generation started from {yaml_path}."
