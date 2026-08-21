"""Stand-in for the (assumed already-existing) chatbot generator.

Per the brief, the real `generate_chatbot(yaml_path)` already exists
elsewhere in the pipeline. This stub keeps Agen runnable end-to-end today;
swap the body for a call/import into the real generator when it's wired up.
"""

from __future__ import annotations

from pathlib import Path


def generate_chatbot(yaml_path: Path) -> None:
    print(
        f"[generator_stub] Would now generate a chatbot from: {yaml_path}\n"
        f"[generator_stub] Replace agent/generator_stub.py with the real "
        f"generate_chatbot() implementation when available."
    )
