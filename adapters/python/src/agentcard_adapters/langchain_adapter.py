"""
agentcard_adapters.langchain_adapter
=====================================

Bidirectional adapter between LangChain tools/agents and AgentCard v1.0.

Usage
-----
**Export a LangChain tool as AgentCard:**

    from langchain.tools import BaseTool
    from agentcard_adapters.langchain_adapter import tool_to_agentcard

    class SearchTool(BaseTool):
        name = "web_search"
        description = "Search the web for current information."
        ...

    card = tool_to_agentcard(
        tool=SearchTool(),
        agent_id="01HZQK3P8EMXR9V7T5N2W4J6C0",
        endpoint_url="https://my-agent.example.com/api",
    )
    card.validate()
    print(card.to_json(indent=2))

**Wrap a LangChain agent executor with AgentCard identity:**

    from langchain.agents import AgentExecutor
    from agentcard_adapters.langchain_adapter import AgentCardMixin

    executor: AgentExecutor = ...
    mixin = AgentCardMixin(executor, agent_id="01HZQK3P8EMXR9V7T5N2W4J6C0",
                          endpoint_url="https://my-agent.example.com/api")
    card = mixin.agent_card
    print(card.to_json(indent=2))

**Reconstruct a LangChain StructuredTool from AgentCard:**

    from agentcard_adapters.langchain_adapter import agentcard_to_tool
    tool = agentcard_to_tool(card)

License
-------
Apache 2.0.  See https://github.com/kwailapt/AgentCard/blob/main/LICENSE
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Optional

from .core import (
    AgentCard,
    Capability,
    Endpoint,
    PricingModel,
    LANDAUER_FLOOR_JOULES,
)

if TYPE_CHECKING:
    # Avoid hard dependency at import time.
    from langchain_core.tools import BaseTool
    from langchain.agents import AgentExecutor

__all__ = [
    "tool_to_agentcard",
    "tools_to_agentcard",
    "agentcard_to_tool",
    "AgentCardMixin",
]

# ── Name normalisation ────────────────────────────────────────────────────────

def _normalise_capability_id(name: str) -> str:
    """
    Convert a LangChain tool name to a valid AgentCard capability id.

    Rules:
    - lowercase
    - spaces and hyphens become underscores
    - non-alphanumeric (except ``.``, ``_``, ``-``) are removed
    - id must start with [a-z0-9]

    Examples:
        "Web Search"     → "web_search"
        "Code Executor"  → "code_executor"
        "sql-query"      → "sql-query"
        "ArXiv Search"   → "arxiv_search"
    """
    s = name.lower().strip()
    s = re.sub(r"[\s]+", "_", s)
    s = re.sub(r"[^a-z0-9._-]", "", s)
    s = re.sub(r"^[^a-z0-9]+", "", s)  # strip leading non-alnum
    if not s:
        s = "tool"
    return s


# ── Single tool → AgentCard ───────────────────────────────────────────────────

def tool_to_agentcard(
    tool: "BaseTool",
    agent_id: str,
    endpoint_url: str,
    *,
    version: str = "1.0.0",
    protocol: str = "http",
    health_url: Optional[str] = None,
    estimated_latency_ms: Optional[float] = None,
    tags: Optional[list[str]] = None,
) -> AgentCard:
    """
    Convert a single LangChain ``BaseTool`` to an ``AgentCard``.

    Parameters
    ----------
    tool:
        Any ``BaseTool`` instance (``StructuredTool``, ``Tool``, subclass).
    agent_id:
        26-character Crockford Base32 ULID for this agent. Generate with::

            python -c "import uuid; print(str(uuid.uuid4()).upper().replace('-','')[:26])"

    endpoint_url:
        The URL where this agent/tool is reachable.
    version:
        Semantic version of this agent card. Defaults to ``"1.0.0"``.
    protocol:
        Transport protocol. One of ``http``, ``websocket``, ``sse``,
        ``grpc``, ``mcp``, ``native``. Defaults to ``"http"``.
    health_url:
        Optional health-check endpoint.
    estimated_latency_ms:
        Estimated response latency in milliseconds.
    tags:
        Optional semantic tags for capability discovery.

    Returns
    -------
    AgentCard
        A validated AgentCard representing this tool.
    """
    cap_id = _normalise_capability_id(tool.name)

    # Extract JSON Schema from args_schema if available (Pydantic model)
    input_schema: Optional[dict[str, Any]] = None
    if hasattr(tool, "args_schema") and tool.args_schema is not None:
        try:
            if hasattr(tool.args_schema, "model_json_schema"):
                # Pydantic v2
                input_schema = tool.args_schema.model_json_schema()
            elif hasattr(tool.args_schema, "schema"):
                # Pydantic v1
                input_schema = tool.args_schema.schema()
        except Exception:  # noqa: BLE001
            pass

    pricing = None
    if estimated_latency_ms is not None:
        pricing = PricingModel(
            base_cost_joules=LANDAUER_FLOOR_JOULES,  # minimum physical cost
            estimated_latency_ms=estimated_latency_ms,
        )

    card = AgentCard(
        agent_id=agent_id,
        name=tool.name,
        version=version,
        capabilities=[
            Capability(
                id=cap_id,
                description=tool.description,
                tags=tags,
                input_schema=input_schema,
            )
        ],
        endpoint=Endpoint(
            protocol=protocol,
            url=endpoint_url,
            health_url=health_url,
        ),
        pricing=pricing,
    )
    card.validate()
    return card


# ── Multiple tools → AgentCard ────────────────────────────────────────────────

def tools_to_agentcard(
    tools: list["BaseTool"],
    agent_id: str,
    agent_name: str,
    endpoint_url: str,
    *,
    version: str = "1.0.0",
    protocol: str = "http",
    health_url: Optional[str] = None,
    estimated_latency_ms: Optional[float] = None,
) -> AgentCard:
    """
    Convert a list of LangChain ``BaseTool`` instances to a single AgentCard.

    Each tool becomes one ``Capability`` entry.  The resulting card represents
    an agent that bundles all the tools under a single identity.

    Parameters
    ----------
    tools:
        List of ``BaseTool`` instances.
    agent_id:
        26-character ULID for the bundled agent.
    agent_name:
        Display name for the bundled agent.
    endpoint_url:
        The URL where this bundled agent is reachable.

    Returns
    -------
    AgentCard
        A validated AgentCard with one capability per tool.
    """
    if not tools:
        raise ValueError("tools list must not be empty")

    capabilities = []
    for tool in tools:
        cap_id = _normalise_capability_id(tool.name)
        input_schema = None
        if hasattr(tool, "args_schema") and tool.args_schema is not None:
            try:
                if hasattr(tool.args_schema, "model_json_schema"):
                    input_schema = tool.args_schema.model_json_schema()
                elif hasattr(tool.args_schema, "schema"):
                    input_schema = tool.args_schema.schema()
            except Exception:  # noqa: BLE001
                pass
        capabilities.append(
            Capability(
                id=cap_id,
                description=tool.description,
                input_schema=input_schema,
            )
        )

    pricing = None
    if estimated_latency_ms is not None:
        pricing = PricingModel(
            base_cost_joules=LANDAUER_FLOOR_JOULES,
            estimated_latency_ms=estimated_latency_ms,
        )

    card = AgentCard(
        agent_id=agent_id,
        name=agent_name,
        version=version,
        capabilities=capabilities,
        endpoint=Endpoint(
            protocol=protocol,
            url=endpoint_url,
            health_url=health_url,
        ),
        pricing=pricing,
    )
    card.validate()
    return card


# ── AgentCard → LangChain StructuredTool ─────────────────────────────────────

def agentcard_to_tool(card: AgentCard, capability_index: int = 0) -> "BaseTool":
    """
    Reconstruct a LangChain ``StructuredTool`` from an ``AgentCard``.

    The tool, when invoked, performs an HTTP POST to ``card.endpoint.url``
    with the provided arguments and returns the response text.

    Parameters
    ----------
    card:
        The AgentCard to convert.
    capability_index:
        Which capability to use as the tool's signature. Defaults to ``0``
        (the first capability).

    Returns
    -------
    BaseTool
        A ``StructuredTool`` backed by the AgentCard's endpoint.

    Raises
    ------
    ImportError
        If ``langchain_core`` is not installed.
    """
    try:
        from langchain_core.tools import StructuredTool
    except ImportError as e:
        raise ImportError(
            "langchain_core is required: pip install langchain-core"
        ) from e

    cap = card.capabilities[capability_index]

    def _invoke(**kwargs: Any) -> str:
        import urllib.request
        import json as _json
        url = card.endpoint.url
        body = _json.dumps(kwargs).encode()
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            return resp.read().decode()

    return StructuredTool.from_function(
        func=_invoke,
        name=cap.id.replace(".", "_"),
        description=cap.description,
    )


# ── AgentCardMixin for AgentExecutor ─────────────────────────────────────────

class AgentCardMixin:
    """
    Wraps a LangChain ``AgentExecutor`` with AgentCard identity.

    Usage
    -----
    ::

        executor = AgentExecutor(agent=agent, tools=tools)
        mixin = AgentCardMixin(
            executor,
            agent_id="01HZQK3P8EMXR9V7T5N2W4J6C0",
            agent_name="My Research Agent",
            endpoint_url="https://my-agent.example.com/api",
        )
        # Expose identity to A2A peers
        print(mixin.agent_card.to_json(indent=2))

        # Use normally
        result = mixin.invoke({"input": "What is 2+2?"})
    """

    def __init__(
        self,
        executor: "AgentExecutor",
        agent_id: str,
        endpoint_url: str,
        *,
        agent_name: Optional[str] = None,
        version: str = "1.0.0",
        protocol: str = "http",
    ) -> None:
        self._executor = executor
        tools = getattr(executor, "tools", []) or []
        name = agent_name or "LangChain Agent"

        if tools:
            self._card = tools_to_agentcard(
                tools=tools,
                agent_id=agent_id,
                agent_name=name,
                endpoint_url=endpoint_url,
                version=version,
                protocol=protocol,
            )
        else:
            # Agent with no explicit tools — generic capability
            self._card = AgentCard(
                agent_id=agent_id,
                name=name,
                version=version,
                capabilities=[
                    Capability(
                        id="agent.invoke",
                        description="General-purpose LangChain agent execution.",
                    )
                ],
                endpoint=Endpoint(protocol=protocol, url=endpoint_url),
            )
            self._card.validate()

    @property
    def agent_card(self) -> AgentCard:
        """The AgentCard representing this executor's identity."""
        return self._card

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to the underlying AgentExecutor."""
        return self._executor.invoke(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._executor, name)
