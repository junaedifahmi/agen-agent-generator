"""Serialize a validated ChatbotSpec to the YAML file the generator consumes."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .config import settings
from .feature_model import ChatbotSpec


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "chatbot"


def export_spec_to_yaml(spec: ChatbotSpec) -> Path:
    """Write `spec` to `<spec_output_dir>/<business-slug>-<timestamp>.yaml`."""
    out_dir = Path(settings.spec_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"{_slugify(spec.business_name)}-{timestamp}.yaml"
    path = out_dir / filename

    # mode="json" so enums serialize as their plain string values.
    data = spec.model_dump(mode="json", exclude_none=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    return path
