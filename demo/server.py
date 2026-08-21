"""Two-interface demo of Agen's human-in-the-loop gate -- served by Agno's
own AgentOS.

`/`        -- the chat interface, for the business user having the
              conversation with Agen. Every reply on this page comes from
              the real agent (agent/elicitor.py) via a real model call.
`/review`  -- a deliberately separate interface, for whoever is allowed to
              authorize chatbot generation. It lists every pending
              "generate now?" across *all* sessions and can approve or
              decline them.

Both pages are static HTML/JS that talk directly to AgentOS's real REST
protocol -- there is no bespoke `/api/...` layer in between:

- Chat sends messages with `POST /agents/agen/runs` and, once a run pauses,
  polls `GET /agents/agen/runs/{run_id}` until it's no longer PAUSED.
- Review lists pending approvals with `GET /approvals?status=pending&
  agent_id=agen`, resolves one with `POST /approvals/{id}/resolve`, then
  resumes the paused run with `POST /agents/agen/runs/{run_id}/continue`.

The two pages never talk to each other directly -- they only meet through
the paused run and its approval record sitting in Agen's own SQLite db.
Nothing about the chat UI can bypass that: the run stays PAUSED, and the
only thing that ever unpauses it is the review page resolving the approval
and calling `.../continue`.

--- Why base_app, and not just @app.get("/") on the AgentOS app ---

AgentOS registers its OWN `GET /` (a JSON identity endpoint: {"name":
"AgentOS API", ...}), and its default conflict policy is
`on_route_conflict="preserve_agentos"`. So adding `@app.get("/")` to the
app returned by `get_app()` is silently ignored -- visiting `/` serves
AgentOS's JSON instead of the chat page, and the UI appears not to exist.
Building the UI routes on our own FastAPI app and handing it to AgentOS as
`base_app=` with `on_route_conflict="preserve_base_app"` is what makes our
`/` win. AgentOS's own identity endpoint stays available at `/os`.

Run with:  uv run uvicorn demo.server:app --reload
Then open http://127.0.0.1:8000/         (chat)
 and    http://127.0.0.1:8000/review     (reviewer)
"""

from __future__ import annotations

from pathlib import Path

from agno.os import AgentOS
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from agent.elicitor import build_agen_agent

STATIC_DIR = Path(__file__).parent / "static"

# One shared Agent instance, safe across concurrent sessions: Agno
# deep-copies the constructor's session_state default into each new
# session record rather than sharing it by reference (verified against
# agno/agent/_storage.py). `id="agen"` (set in agent/elicitor.py) is what
# gives it the stable "/agents/agen/..." URL below, instead of an
# auto-slugified name that would change if `name=` ever gets edited.
agent = build_agen_agent()

# The UI lives on our own app, which AgentOS then layers its API onto.
ui_app = FastAPI(title="Agen demo")


@ui_app.get("/", include_in_schema=False)
def chat_page() -> FileResponse:
    """The business user's chat interface."""
    return FileResponse(STATIC_DIR / "chat.html")


# Deliberately not "/approvals" -- AgentOS owns that path for its JSON
# approvals API (GET/POST /approvals...). This is the human-facing page
# that talks to it.
@ui_app.get("/review", include_in_schema=False)
def review_page() -> FileResponse:
    """The reviewer's approval interface -- a separate screen by design."""
    return FileResponse(STATIC_DIR / "review.html")


ui_app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Passing the same db as AgentOS's own `db=` is what turns on the built-in
# `/approvals` router (agno.os.app only mounts it when a db capable of the
# approval methods is configured) and lets it read the approval records
# written to *this* db the moment `generate_chatbot_now` pauses a run.
agent_os = AgentOS(
    agents=[agent],
    db=agent.db,
    base_app=ui_app,
    on_route_conflict="preserve_base_app",
)
app = agent_os.get_app()
