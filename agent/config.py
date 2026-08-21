"""Runtime configuration for Agen, loaded from environment / .env."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    model_id: str = os.getenv("AGEN_MODEL_ID", "openai/gpt-5-mini")
    db_file: str = os.getenv("AGEN_DB_FILE", "agen_sessions.db")
    spec_output_dir: str = os.getenv("AGEN_SPEC_OUTPUT_DIR", "specs")
    max_tokens: int = int(os.getenv("AGEN_MAX_TOKENS", "4096"))

    def validate(self) -> None:
        if not self.openrouter_api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Copy .env.example to .env "
                "and add your OpenRouter API key."
            )


settings = Settings()
