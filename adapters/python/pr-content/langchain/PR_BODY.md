# Add AgentCard v1.0 integration for agent identity declaration

## Summary

This PR adds a `langchain_community/utilities/agentcard.py` integration that allows
LangChain tools and agents to declare their identity using the **AgentCard v1.0**
open standard (https://github.com/kwailapt/AgentCard).

AgentCard is to A2A (agent-to-agent) communication what HTTP headers are to the web:
a standardised, machine-parseable capability declaration that works with any framework.

## Why this matters

As LangChain agents begin communicating with agents from other frameworks (CrewAI,
AutoGen, custom agents), they need a **framework-neutral identity format**.
AgentCard fills this gap:

- **Zero dependencies** in core — pure Python dataclasses
- **Framework-agnostic** — same JSON schema works for LangChain, CrewAI, AutoGen, MCP
- **Physics-grounded pricing** — `base_cost_joules` uses Landauer's thermodynamic floor
  as a machine-verifiable minimum cost, preventing fake "zero-cost" claims
- **Open standard** — Apache 2.0 + CC-BY 4.0, patent non-reservation

## What's included

### `langchain_community/utilities/agentcard.py`

- `tool_to_agentcard(tool, agent_id, endpoint_url)` — convert a `BaseTool` to AgentCard
- `tools_to_agentcard(tools, agent_id, agent_name, endpoint_url)` — bundle multiple tools
- `agentcard_to_tool(card)` — reconstruct a `StructuredTool` from an AgentCard
- `AgentCardMixin` — wrap any `AgentExecutor` with AgentCard identity

### `tests/unit_tests/utilities/test_agentcard.py`

Full test coverage using mock tools (no network calls, no external dependencies).

## Usage example

```python
from langchain.tools import BaseTool
from langchain_community.utilities.agentcard import tool_to_agentcard

class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the web for current information."
    def _run(self, query: str) -> str: ...

card = tool_to_agentcard(
    tool=WebSearchTool(),
    agent_id="01HZQK3P8EMXR9V7T5N2W4J6C0",  # ULID
    endpoint_url="https://my-agent.example.com/api",
)
print(card.to_json(indent=2))
# {
#   "agent_id": "01HZQK3P8EMXR9V7T5N2W4J6C0",
#   "name": "web_search",
#   "version": "1.0.0",
#   "capabilities": [{"id": "web_search", "description": "Search the web..."}],
#   "endpoint": {"protocol": "http", "url": "https://my-agent.example.com/api"}
# }
```

## AgentCard JSON Schema

Full schema: https://github.com/kwailapt/AgentCard/blob/main/schema.json

Key fields:
| Field | Type | Description |
|-------|------|-------------|
| `agent_id` | string | 26-char Crockford Base32 ULID |
| `name` | string | Display name 1–128 chars |
| `version` | string | Semantic version (semver 2.0) |
| `capabilities[]` | array | Dot-namespaced capability ids |
| `endpoint` | object | Protocol + URL + optional auth |
| `pricing.base_cost_joules` | float | Landauer thermodynamic floor |

## Checklist

- [x] Zero new mandatory dependencies (optional: `agentcard-adapters`)
- [x] Tests pass with mock objects (no real framework calls)
- [x] `BaseTool.args_schema` → `input_schema` (Pydantic v1 + v2 both supported)
- [x] Round-trip serialisation verified (Python dict ↔ JSON ↔ AgentCard)
- [x] Landauer floor validation (physically implausible prices rejected)
- [x] Apache 2.0 license compatible with LangChain MIT license

## References

- AgentCard spec: https://github.com/kwailapt/AgentCard
- JSON Schema: https://github.com/kwailapt/AgentCard/blob/main/schema.json
- License: Apache 2.0 + CC-BY 4.0, no patent reservation
