# Add AgentCard v1.0 support for agent identity in A2A contexts

## Summary

This PR adds `crewai/utilities/agentcard.py` — a bidirectional adapter between
CrewAI agents/crews and the **AgentCard v1.0** open standard
(https://github.com/kwailapt/AgentCard).

As CrewAI agents increasingly need to communicate with agents from other frameworks
(LangChain tools, AutoGen assistants, custom MCP servers), they need a
**framework-neutral identity layer**. AgentCard provides this:

> AgentCard is to A2A what HTTP headers are to the web.

## Motivation

When a CrewAI `Researcher` agent delegates to a LangChain `WebSearchTool` agent,
both sides need to answer:
- Who am I? (identity)
- What can I do? (capabilities)
- How do you reach me? (endpoint)
- What does this cost? (pricing with physical units)

Without a standard format, each delegation requires custom parsing.
AgentCard makes this zero-config.

## What's included

### `crewai/utilities/agentcard.py`

- `agent_to_agentcard(agent, agent_id, endpoint_url)` — convert a CrewAI `Agent`
  to AgentCard; agent's `role` becomes primary capability id
- `crew_to_agentcards(crew, agent_ids, base_url)` — export all crew agents at once
- `agentcard_to_agent(card, llm)` — reconstruct a CrewAI `Agent` from an AgentCard

### `tests/utilities/test_agentcard.py`

Full mock-based test coverage. Zero network calls.

## Usage example

```python
from crewai import Agent
from crewai.utilities.agentcard import agent_to_agentcard, crew_to_agentcards

researcher = Agent(
    role="Senior Research Analyst",
    goal="Uncover cutting-edge developments in AI",
    backstory="Expert AI researcher with 10 years of experience.",
    tools=[search_tool, scrape_tool],
)

card = agent_to_agentcard(
    agent=researcher,
    agent_id="01HZQK3P8EMXR9V7T5N2W4J6C0",
    endpoint_url="https://my-crew.example.com/api/researcher",
)

print(card.to_json(indent=2))
# {
#   "agent_id": "01HZQK3P8EMXR9V7T5N2W4J6C0",
#   "name": "Senior Research Analyst",
#   "capabilities": [
#     {"id": "senior_research_analyst", "description": "Uncover cutting-edge..."},
#     {"id": "tool.web_search", "description": "Search the web."},
#     {"id": "tool.scrape_website", "description": "Scrape website content."}
#   ],
#   "endpoint": {"protocol": "http", "url": "https://my-crew.example.com/api/researcher"}
# }

# Export entire crew
crew = Crew(agents=[researcher, writer], tasks=[...])
cards = crew_to_agentcards(crew, base_url="https://my-crew.example.com/api")
```

## AgentCard schema highlights

- `agent_id`: 26-char Crockford Base32 ULID — globally unique
- `capabilities[].id`: dot-namespaced (`senior_research_analyst`, `tool.web_search`)
- `pricing.base_cost_joules`: Landauer thermodynamic floor (k_B × 300K × ln2)
- `metadata.pacr:trust_tier`: `untrusted | basic | established | verified | banned`

## Checklist

- [x] Zero new mandatory dependencies
- [x] CrewAI `Agent.role` → primary capability id (normalised to lowercase_underscore)
- [x] Each tool in `agent.tools` → separate `tool.*` capability
- [x] `crew_to_agentcards()` auto-generates URL slugs from roles
- [x] Round-trip: `agentcard_to_agent()` reconstructs a valid CrewAI Agent
- [x] Apache 2.0 license (compatible with CrewAI MIT license)
- [x] All tests pass with mock objects

## References

- AgentCard spec: https://github.com/kwailapt/AgentCard
- JSON Schema: https://github.com/kwailapt/AgentCard/blob/main/schema.json
- `agentcard-adapters` PyPI package: `pip install agentcard-adapters[crewai]`
