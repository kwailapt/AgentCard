# agentcard-mcp

> **AgentCard v1.0 identity layer for agent-to-agent (A2A) communication.**  
> Give any Claude / LLM agent a machine-readable identity using the open [AgentCard](https://github.com/kwailapt/AgentCard) standard.

<!-- mcp-name: io.github.kwailapt/agentcard -->

[![Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](../../LICENSE)
[![MCP Compatible](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io)
[![AgentCard v1.0](https://img.shields.io/badge/AgentCard-v1.0-orange.svg)](https://github.com/kwailapt/AgentCard)

## What is AgentCard?

AgentCard is to A2A communication what HTTP headers are to the web:
a standardised, machine-parseable capability declaration that works
with any framework (LangChain, CrewAI, AutoGen, MCP, custom).

```json
{
  "agent_id": "01HZQK3P8EMXR9V7T5N2W4J6C0",
  "name": "WebSearchAgent",
  "version": "1.0.0",
  "capabilities": [
    {"id": "web.search", "description": "Search the web for current information."},
    {"id": "web.scrape", "description": "Extract content from web pages."}
  ],
  "endpoint": {
    "protocol": "https",
    "url": "https://my-agent.example.com/api"
  },
  "pricing": {
    "base_cost_joules": 2.854e-21
  }
}
```

## Installation

```bash
pip install agentcard-mcp
```

## Quick Start — Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "agentcard": {
      "command": "python",
      "args": ["-m", "agentcard_mcp"]
    }
  }
}
```

Then restart Claude Desktop and ask:

> *"Register my identity as a code assistant using AgentCard."*

## Tools

### `agentcard_declare`
Register your AgentCard identity for this session.

```
Input: card_json (string) — JSON conforming to AgentCard v1.0 schema.

Required fields:
  agent_id     — 26-char Crockford Base32 ULID (e.g. 01HZQK3P8EMXR9V7T5N2W4J6C0)
  name         — Display name (1–128 chars)
  version      — Semantic version (e.g. "1.0.0")
  capabilities — Array with ≥1 entry, each with dot-namespaced "id"
  endpoint     — { "protocol": "https"|"http"|"grpc"|"stdio"|"mcp", "url": "..." }
```

### `agentcard_resolve`
Look up a registered agent's AgentCard by name or agent_id.

```
Input: query (string) — partial name (case-insensitive) or exact 26-char ULID.
```

### `agentcard_validate`
Validate any JSON against the AgentCard v1.0 schema.

Checks:
- 26-char Crockford Base32 ULID format
- Semver 2.0 version string
- Dot-namespaced capability ids (`^[a-z0-9][a-z0-9._-]*$`)
- Landauer floor physics check on pricing (`base_cost_joules ≥ 2.854e-21 J`)

### `agentcard_list`
List all AgentCards registered in this session.

## Resources

| URI | Description |
|-----|-------------|
| `agentcard://schema` | Canonical AgentCard v1.0 JSON Schema |
| `agentcard://registry` | All declared cards as JSON array |

## Usage Examples

### Declare an identity
```
User: Register my identity as a data analysis agent.

Claude uses agentcard_declare({
  "agent_id": "01HZQK3P8EMXR9V7T5N2W4J6C0",
  "name": "DataAnalysisAgent",
  "version": "1.0.0",
  "capabilities": [
    {"id": "data.analyze", "description": "Analyze datasets and produce insights."},
    {"id": "data.visualize", "description": "Create charts and visualizations."}
  ],
  "endpoint": {"protocol": "mcp", "url": "mcp://claude-desktop/data-agent"}
})
→ ✓ AgentCard declared — agent_id=01HZQK3P8EMXR9V7T5N2W4J6C0, name='DataAnalysisAgent', capabilities=2
```

### Validate a peer's card
```
User: Is this AgentCard valid? [paste JSON]

Claude uses agentcard_validate(card_json)
→ VALID ✓
    agent_id    : 01HZQK3P8EMXR9V7T5N2W4J6C0
    capabilities: 2 — [data.analyze, data.visualize]
    endpoint    : mcp://claude-desktop/data-agent
```

### Resolve a peer agent
```
User: What can the researcher agent do?

Claude uses agentcard_resolve("researcher")
→ { "agent_id": "...", "capabilities": [...], ... }
```

## AgentCard Schema Highlights

| Field | Type | Description |
|-------|------|-------------|
| `agent_id` | string | 26-char Crockford Base32 ULID — globally unique |
| `name` | string | Display name 1–128 chars |
| `version` | string | Semantic version (semver 2.0) |
| `capabilities[].id` | string | Dot-namespaced (`web.search`, `tool.python`) |
| `endpoint.protocol` | enum | `http`, `https`, `grpc`, `stdio`, `mcp` |
| `pricing.base_cost_joules` | float | ≥ Landauer floor (2.854e-21 J) or 0 |
| `metadata.pacr:trust_tier` | enum | `untrusted \| basic \| established \| verified \| banned` |

Full schema: [`agentcard://schema`](../../schema.json)

## Framework Adapters

| Framework | Package | Import |
|-----------|---------|--------|
| LangChain | `pip install agentcard-adapters[langchain]` | `from agentcard_adapters import tool_to_agentcard` |
| CrewAI | `pip install agentcard-adapters[crewai]` | `from agentcard_adapters import agent_to_agentcard` |
| AutoGen | `pip install agentcard-adapters[autogen]` | `from agentcard_adapters.autogen_adapter import agent_to_agentcard` |

## Development

```bash
pip install -e ".[dev]"
pytest tests/
```

## License

Apache 2.0 + CC-BY 4.0 (spec).  
Patent non-reservation: [NOTICE](../../NOTICE).

## References

- [AgentCard Specification](https://github.com/kwailapt/AgentCard)
- [JSON Schema](https://github.com/kwailapt/AgentCard/blob/main/schema.json)
- [Model Context Protocol](https://modelcontextprotocol.io)
