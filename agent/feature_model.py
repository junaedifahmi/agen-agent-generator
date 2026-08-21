"""SPLE feature model for the generated chatbot product line.

This module is the *domain engineering* artifact: it defines the fixed set
of features and variation points that every generated chatbot is assembled
from. Each elicitation session (application engineering) produces exactly
one validated `ChatbotSpec` instance, which is what gets serialized to YAML
and handed to the downstream generator.

Feature tree (mandatory features in CAPS, variation points in brackets):

    ChatbotSpec
    |-- CONNECTOR              (mandatory, single-select variation point)
    |     |-- [whatsapp | webapp | telegram]
    |-- KNOWLEDGE_BASE         (mandatory feature, optional content)
    |     |-- [vector | api]  -- retrieval mode only
    |-- SKILLS                 (mandatory, one or more)
    |-- PERSONA                (mandatory feature)
          |-- system_prompt, tone, language, escalation_rule

Agen only resolves *which* variant is selected for connector and knowledge
base -- implementation detail (API tokens, phone number IDs, bot tokens,
embed origins, which vector database, embedding models, ingestion sources,
etc.) is configured separately on the monitoring dashboard once the chatbot
is generated, not elicited in conversation. Keeping that detail out of the
feature model here is deliberate: it's dashboard/application-engineering
territory, not business-elicitation territory.

Adding a new connector or knowledge-base mode later means adding one enum
member here -- the elicitor's instructions and the YAML schema stay generic
over the feature model rather than hardcoding choices.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ConnectorType(str, Enum):
    WHATSAPP = "whatsapp"
    WEBAPP = "webapp"
    TELEGRAM = "telegram"


class ConnectorFeature(BaseModel):
    """Variation point: which channel the chatbot is deployed on.

    Connection detail (API tokens, phone number IDs, bot tokens, embed
    origins, ...) is configured on the dashboard after generation, not
    elicited here.
    """

    type: ConnectorType = Field(
        ..., description="Which channel the generated chatbot is deployed on."
    )


class KnowledgeBaseMode(str, Enum):
    VECTOR = "vector"
    API = "api"


class KnowledgeBaseFeature(BaseModel):
    """Variation point: how the chatbot looks up information, not what.

    The underlying implementation (which vector database, which API,
    embedding models, ingestion sources, ...) is fixed by SPLE and
    configured on the dashboard -- Agen only needs to confirm whether the
    chatbot should have a knowledge base at all, and if so, whether it's
    backed by a vector store or an external API.
    """

    enabled: bool = Field(
        default=True,
        description="Whether the generated chatbot has a knowledge base at all.",
    )
    mode: KnowledgeBaseMode | None = Field(
        default=None,
        description="'vector' or 'api'. Required when enabled is true, "
        "otherwise left unset.",
    )

    @model_validator(mode="after")
    def mode_required_when_enabled(self) -> "KnowledgeBaseFeature":
        if self.enabled and self.mode is None:
            raise ValueError(
                "knowledge_base.enabled is true but no mode ('vector' or "
                "'api') was provided."
            )
        return self


class ChatbotSkill(BaseModel):
    """One capability the generated chatbot should have, in plain language."""

    name: str = Field(..., description="Short name for the skill, e.g. 'Order tracking'.")
    description: str = Field(
        ..., description="What the chatbot should be able to do for this skill."
    )


class PersonaFeature(BaseModel):
    name: str = Field(..., description="The chatbot's display name / persona name.")
    system_prompt: str = Field(
        ..., description="The system prompt that defines the persona's behavior."
    )
    tone: str = Field(default="friendly and professional")
    language: str = Field(default="id", description="Primary reply language, e.g. 'id' or 'en'.")
    escalation_rule: str | None = Field(
        default=None,
        description="When/how the bot should hand off to a human.",
    )


class ChatbotSpec(BaseModel):
    """The full application-engineering artifact for one elicitation session."""

    business_name: str = Field(..., description="Name of the business the chatbot serves.")
    connector: ConnectorFeature
    knowledge_base: KnowledgeBaseFeature
    skills: list[ChatbotSkill] = Field(
        ..., min_length=1, description="The chatbot's capabilities, one or more."
    )
    persona: PersonaFeature


def build_spec_from_state(state: dict[str, Any]) -> "ChatbotSpec":
    """Deterministically build a ChatbotSpec from tracked session state.

    This is what `agent/tools.py`'s tool calls populate turn by turn. Going
    straight from that structured record to `ChatbotSpec` (rather than
    asking the model to re-summarize the whole conversation into a schema
    at the end) means the final YAML can never drift from what was actually
    recorded during elicitation -- Pydantic's validators here are the only
    thing standing between "what Agen tracked" and "what gets exported."
    """
    return ChatbotSpec(
        business_name=state.get("business_name"),
        connector=ConnectorFeature(type=state.get("connector_type")),
        knowledge_base=KnowledgeBaseFeature(
            enabled=bool(state.get("kb_enabled")),
            mode=state.get("kb_mode"),
        ),
        skills=[
            ChatbotSkill(name=s["name"], description=s["description"])
            for s in state.get("skills", [])
        ],
        persona=PersonaFeature(
            name=state.get("persona_name"),
            system_prompt=state.get("persona_system_prompt"),
            tone=state.get("persona_tone") or "friendly and professional",
            language=state.get("persona_language") or "id",
            escalation_rule=state.get("persona_escalation_rule"),
        ),
    )
