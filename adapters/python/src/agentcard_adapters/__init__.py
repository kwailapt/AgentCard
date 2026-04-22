"""
agentcard-adapters
==================

AgentCard v1.0 adapters for LangChain, CrewAI, and AutoGen.

Provides bidirectional conversion between major Python AI agent frameworks
and the AgentCard v1.0 schema (https://github.com/kwailapt/AgentCard).

Quick start
-----------
::

    pip install agentcard-adapters

LangChain::

    from agentcard_adapters import tool_to_agentcard
    card = tool_to_agentcard(my_tool, agent_id="...", endpoint_url="...")

CrewAI::

    from agentcard_adapters import agent_to_agentcard   # CrewAI
    card = agent_to_agentcard(researcher, agent_id="...", endpoint_url="...")

AutoGen::

    from agentcard_adapters.autogen_adapter import agent_to_agentcard
    card = agent_to_agentcard(assistant, agent_id="...", endpoint_url="...")

Core schema (framework-independent)::

    from agentcard_adapters.core import AgentCard, Capability, Endpoint
    card = AgentCard(agent_id="...", name="My Agent", version="1.0.0",
                     capabilities=[...], endpoint=...)
    card.validate()

License
-------
Apache 2.0 + CC-BY 4.0 (spec).
Patent non-reservation: https://github.com/kwailapt/AgentCard/blob/main/NOTICE
"""

from .core import (
    AgentCard,
    AuthConfig,
    Capability,
    Endpoint,
    EpiplexityCert,
    GoalSubscription,
    Metadata,
    PricingModel,
    LANDAUER_FLOOR_JOULES,
)

# Lazy-import adapters to avoid hard dependencies
def __getattr__(name: str):  # noqa: ANN001
    if name in ("tool_to_agentcard", "tools_to_agentcard",
                "agentcard_to_tool", "AgentCardMixin"):
        from . import langchain_adapter as _lc
        return getattr(_lc, name)
    if name in ("agent_to_agentcard", "crew_to_agentcards",
                "agentcard_to_agent"):
        from . import crewai_adapter as _cr
        return getattr(_cr, name)
    raise AttributeError(f"module 'agentcard_adapters' has no attribute {name!r}")


__all__ = [
    # Core types
    "AgentCard",
    "AuthConfig",
    "Capability",
    "Endpoint",
    "EpiplexityCert",
    "GoalSubscription",
    "Metadata",
    "PricingModel",
    "LANDAUER_FLOOR_JOULES",
    # LangChain (lazy)
    "tool_to_agentcard",
    "tools_to_agentcard",
    "agentcard_to_tool",
    "AgentCardMixin",
    # CrewAI (lazy)
    "agent_to_agentcard",
    "crew_to_agentcards",
    "agentcard_to_agent",
]

__version__ = "0.1.0"
