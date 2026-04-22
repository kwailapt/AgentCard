# Add AgentCard v1.0 integration for A2A agent identity

## Summary

This PR adds `autogen/agentcard.py` — a bidirectional adapter between AutoGen
agents/group chats and the **AgentCard v1.0** open standard
(https://github.com/kwailapt/AgentCard).

AgentCard provides a framework-neutral JSON identity format for agent-to-agent (A2A)
communication — analogous to HTTP headers for the web.

## Motivation

Multi-agent systems built with AutoGen increasingly need to interoperate with agents
from other frameworks. Without a standard identity layer, each integration requires
custom protocols.

**AgentCard enables:**
- `AssistantAgent` → publish its capabilities as discoverable JSON
- External AgentCard → convert to AutoGen-compatible tool function + schema
- `GroupChat` → export all agents as an AgentCard registry
- `AgentCardRegistry` → resolve any peer by name during conversation

## What's included

### `autogen/agentcard.py`

| Function/Class | Description |
|---|---|
| `agent_to_agentcard(agent, agent_id, endpoint_url)` | Convert any `ConversableAgent` to AgentCard |
| `groupchat_to_agentcards(groupchat, agent_ids, base_url)` | Export all GroupChat agents |
| `agentcard_to_tool_function(card)` | Returns `(fn, schema)` — OpenAI function schema + HTTP caller |
| `AgentCardRegistry` | In-process registry for multi-agent identity resolution |

### `test/agentcard_test.py`

Full mock-based test coverage (AutoGen v0.2 + v0.4 compatible). Zero real LLM calls.

## Usage examples

### Export an AssistantAgent

```python
from autogen import AssistantAgent
from autogen.agentcard import agent_to_agentcard

assistant = AssistantAgent(
    name="assistant",
    system_message="You are a helpful AI assistant specialised in data analysis.",
    llm_config={"model": "gpt-4o", "api_key": "..."},
)

card = agent_to_agentcard(
    agent=assistant,
    agent_id="01HZQK3P8EMXR9V7T5N2W4J6C0",
    endpoint_url="https://my-autogen.example.com/api/assistant",
)
print(card.to_json(indent=2))
```

### Use a remote AgentCard as an AutoGen tool

```python
import requests
from autogen.agentcard import agentcard_to_tool_function
from agentcard_adapters.core import AgentCard

# Fetch peer's identity
card = AgentCard.from_json(requests.get("https://peer.example.com/.well-known/agentcard").text)

fn, schema = agentcard_to_tool_function(card)
assistant = AssistantAgent(
    name="orchestrator",
    llm_config={
        "model": "gpt-4o",
        "functions": [schema],  # peer's capability exposed as function
    },
)
assistant.register_for_execution(name=schema["name"])(fn)
```

### GroupChat with AgentCard registry

```python
from autogen import GroupChat, GroupChatManager
from autogen.agentcard import groupchat_to_agentcards, AgentCardRegistry

groupchat = GroupChat(agents=[assistant, researcher, coder], messages=[], max_round=20)
manager = GroupChatManager(groupchat=groupchat, llm_config={...})

cards = groupchat_to_agentcards(
    groupchat,
    agent_ids=["01HZQK3P8EMXR9V7T5N2W4J6C0", ...],
    base_url="https://my-system.example.com/api",
)

registry = AgentCardRegistry()
for card in cards:
    registry.register(card)

# During conversation — resolve a peer's identity
peer = registry.get("researcher")
fn, schema = agentcard_to_tool_function(peer)
```

## AutoGen v0.2 + v0.4 compatibility

| Feature | v0.2 (pyautogen) | v0.4+ (autogen-agentchat) |
|---------|-----------------|--------------------------|
| `function_map` → capabilities | ✅ | — |
| `_tools` list → capabilities | — | ✅ |
| `description` field | — | ✅ |
| `system_message` fallback | ✅ | ✅ |

## Checklist

- [x] Zero new mandatory dependencies (`agentcard-adapters` optional)
- [x] AutoGen v0.2 and v0.4 API surfaces both supported
- [x] `function_map` (v0.2) and `_tools` (v0.4) both extracted as capabilities
- [x] `description` preferred over `system_message` for capability description
- [x] `agentcard_to_tool_function` returns OpenAI-compatible function schema
- [x] `AgentCardRegistry` supports `function_map`-style batch registration
- [x] Round-trip serialisation verified
- [x] Apache 2.0 license (compatible with AutoGen CC-BY 4.0 license)
- [x] All 11 tests pass with mock objects

## References

- AgentCard: https://github.com/kwailapt/AgentCard
- JSON Schema: https://github.com/kwailapt/AgentCard/blob/main/schema.json
- `pip install agentcard-adapters[autogen]`
