"""CLI entry point for Agen: talk to the elicitor, get a generated chatbot.

Chatbot generation is gated by Agno's human-in-the-loop tool confirmation
(see `agent/generation_tool.py`): whenever Agen tries to call
`generate_chatbot_now`, `agent.run()` returns with `response.is_paused`
True instead of executing it. This loop is what actually asks the human
and only resumes the run once they've explicitly said yes or no -- that
approval can't be skipped by anything said earlier in the chat.
"""

import uuid

from agent.elicitor import build_agen_agent


def resolve_pending_confirmations(agent, response, session_id: str):
    """Ask the user about every tool call Agen is waiting to make, then
    resume the run with their answers. Loops in case a resumed run itself
    triggers another tool requiring confirmation."""
    while response.is_paused:
        for pending in response.tools_requiring_confirmation:
            print(f"\nAgen wants to run: {pending.tool_name}({pending.tool_args})")
            answer = input("Allow this? (y/n): ").strip().lower()
            pending.confirmed = answer in {"y", "yes"}
            if not pending.confirmed:
                pending.confirmation_note = "The user declined this action."

        response = agent.continue_run(
            run_response=response,
            updated_tools=response.tools,
            session_id=session_id,
        )
    return response


def main() -> None:
    agent = build_agen_agent()
    session_id = str(uuid.uuid4())

    print(
        "Agen: Hi, I'm Agen. I'll turn your business requirements into a "
        "technical spec for your chatbot. Tell me about the business and "
        "what you want the chatbot to do. (type 'exit' to quit)\n"
    )

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break

        try:
            response = agent.run(user_input, session_id=session_id)
            response = resolve_pending_confirmations(agent, response, session_id)
        except Exception as exc:  # guardrail rejection or model error
            print(f"Agen: I can't process that message. ({exc})\n")
            continue

        text = response.content if isinstance(response.content, str) else str(response.content)
        print(f"Agen: {text}\n")


if __name__ == "__main__":
    main()
