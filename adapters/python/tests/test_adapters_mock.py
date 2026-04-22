"""
Tests for LangChain, CrewAI, and AutoGen adapters using mock objects.

Zero hard dependencies on the actual frameworks — mocks simulate
the minimal interface that each adapter inspects.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))

import pytest
from agentcard_adapters.core import AgentCard, LANDAUER_FLOOR_JOULES

VALID_ID = "01HZQK3P8EMXR9V7T5N2W4J6C0"
VALID_ID2 = "01HZQK3P8EMXR9V7T5N2W4J6C1"


# ── LangChain mocks ───────────────────────────────────────────────────────────

class MockTool:
    """Minimal mock of langchain_core.tools.BaseTool."""
    def __init__(self, name, description, args_schema=None):
        self.name = name
        self.description = description
        self.args_schema = args_schema


class MockExecutor:
    """Minimal mock of langchain.agents.AgentExecutor."""
    def __init__(self, tools=None):
        self.tools = tools or []

    def invoke(self, *args, **kwargs):
        return {"output": "mock"}


class TestLangChainAdapter:
    def _get(self):
        from agentcard_adapters.langchain_adapter import (
            tool_to_agentcard, tools_to_agentcard, AgentCardMixin,
        )
        return tool_to_agentcard, tools_to_agentcard, AgentCardMixin

    def test_single_tool_to_agentcard(self):
        tool_to_agentcard, _, _ = self._get()
        tool = MockTool("web_search", "Search the web for information.")
        card = tool_to_agentcard(tool, VALID_ID, "https://agent.example.com")
        card.validate()
        assert card.name == "web_search"
        assert card.capabilities[0].id == "web_search"
        assert card.agent_id == VALID_ID

    def test_tool_name_normalisation(self):
        tool_to_agentcard, _, _ = self._get()
        tool = MockTool("Web Search Tool!", "Searches the web.")
        card = tool_to_agentcard(tool, VALID_ID, "https://example.com")
        # Should normalise to valid capability id
        cap_id = card.capabilities[0].id
        import re
        assert re.match(r"^[a-z0-9][a-z0-9._-]*$", cap_id)

    def test_multiple_tools_to_agentcard(self):
        _, tools_to_agentcard, _ = self._get()
        tools = [
            MockTool("search", "Search the web."),
            MockTool("calculator", "Perform math calculations."),
            MockTool("code_exec", "Execute Python code."),
        ]
        card = tools_to_agentcard(tools, VALID_ID, "Research Agent",
                                   "https://example.com")
        card.validate()
        assert len(card.capabilities) == 3
        ids = [c.id for c in card.capabilities]
        assert "search" in ids
        assert "calculator" in ids
        assert "code_exec" in ids

    def test_executor_mixin_with_tools(self):
        _, _, AgentCardMixin = self._get()
        tools = [MockTool("search", "Search."), MockTool("calc", "Calculate.")]
        executor = MockExecutor(tools=tools)
        mixin = AgentCardMixin(executor, VALID_ID, "https://example.com",
                               agent_name="My Agent")
        mixin.agent_card.validate()
        assert len(mixin.agent_card.capabilities) == 2

    def test_executor_mixin_no_tools(self):
        _, _, AgentCardMixin = self._get()
        executor = MockExecutor(tools=[])
        mixin = AgentCardMixin(executor, VALID_ID, "https://example.com")
        mixin.agent_card.validate()
        # Should have at least a generic capability
        assert len(mixin.agent_card.capabilities) >= 1

    def test_latency_sets_pricing(self):
        tool_to_agentcard, _, _ = self._get()
        tool = MockTool("fast_tool", "Fast tool.")
        card = tool_to_agentcard(tool, VALID_ID, "https://example.com",
                                  estimated_latency_ms=50.0)
        assert card.pricing is not None
        assert card.pricing.estimated_latency_ms == 50.0
        assert card.pricing.base_cost_joules >= LANDAUER_FLOOR_JOULES

    def test_empty_tools_raises(self):
        _, tools_to_agentcard, _ = self._get()
        with pytest.raises(ValueError):
            tools_to_agentcard([], VALID_ID, "Agent", "https://example.com")

    def test_pydantic_v2_schema_extraction(self):
        """If tool has args_schema with model_json_schema(), extract it."""
        tool_to_agentcard, _, _ = self._get()

        class MockSchema:
            @staticmethod
            def model_json_schema():
                return {"type": "object", "properties": {"q": {"type": "string"}}}

        tool = MockTool("search_v2", "Search with schema.", args_schema=MockSchema())
        card = tool_to_agentcard(tool, VALID_ID, "https://example.com")
        cap = card.capabilities[0]
        assert cap.input_schema is not None
        assert cap.input_schema["type"] == "object"

    def test_serialisation_roundtrip(self):
        tool_to_agentcard, _, _ = self._get()
        tool = MockTool("my_tool", "A test tool.")
        card = tool_to_agentcard(tool, VALID_ID, "https://example.com")
        restored = AgentCard.from_json(card.to_json())
        assert restored.agent_id == VALID_ID
        assert restored.capabilities[0].id == card.capabilities[0].id


# ── CrewAI mocks ──────────────────────────────────────────────────────────────

class MockCrewAgent:
    """Minimal mock of crewai.Agent."""
    def __init__(self, role, goal, backstory="", tools=None):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.tools = tools or []


class MockCrewTool:
    """Minimal mock of a CrewAI BaseTool."""
    def __init__(self, name, description=""):
        self.name = name
        self.description = description or f"Tool: {name}"


class MockCrew:
    """Minimal mock of crewai.Crew."""
    def __init__(self, agents):
        self.agents = agents


class TestCrewAIAdapter:
    def _get(self):
        from agentcard_adapters.crewai_adapter import (
            agent_to_agentcard, crew_to_agentcards,
        )
        return agent_to_agentcard, crew_to_agentcards

    def test_agent_to_agentcard(self):
        agent_to_agentcard, _ = self._get()
        agent = MockCrewAgent(
            role="Senior Research Analyst",
            goal="Uncover AI developments",
            backstory="Expert in AI research.",
            tools=[MockCrewTool("web_search")],
        )
        card = agent_to_agentcard(agent, VALID_ID, "https://crew.example.com")
        card.validate()
        assert "senior_research_analyst" in [c.id for c in card.capabilities]

    def test_role_to_capability_id_normalisation(self):
        agent_to_agentcard, _ = self._get()
        agent = MockCrewAgent(role="Blog Post Writer!!", goal="Write blog posts.")
        card = agent_to_agentcard(agent, VALID_ID, "https://example.com")
        import re
        for cap in card.capabilities:
            assert re.match(r"^[a-z0-9][a-z0-9._-]*$", cap.id), f"Bad id: {cap.id}"

    def test_tool_capabilities_included(self):
        agent_to_agentcard, _ = self._get()
        agent = MockCrewAgent(
            role="Analyst",
            goal="Analyse data",
            tools=[MockCrewTool("sql_query"), MockCrewTool("data_viz")],
        )
        card = agent_to_agentcard(agent, VALID_ID, "https://example.com",
                                   include_tool_capabilities=True)
        # Primary cap + 2 tool caps
        assert len(card.capabilities) == 3
        tool_ids = [c.id for c in card.capabilities if c.id.startswith("tool.")]
        assert len(tool_ids) == 2

    def test_tool_capabilities_excluded(self):
        agent_to_agentcard, _ = self._get()
        agent = MockCrewAgent(
            role="Analyst",
            goal="Analyse data",
            tools=[MockCrewTool("tool1"), MockCrewTool("tool2")],
        )
        card = agent_to_agentcard(agent, VALID_ID, "https://example.com",
                                   include_tool_capabilities=False)
        assert len(card.capabilities) == 1

    def test_crew_to_agentcards(self):
        _, crew_to_agentcards = self._get()
        crew = MockCrew([
            MockCrewAgent("Researcher", "Research things"),
            MockCrewAgent("Writer", "Write content"),
        ])
        cards = crew_to_agentcards(
            crew,
            agent_ids=[VALID_ID, VALID_ID2],
            base_url="https://crew.example.com",
        )
        assert len(cards) == 2
        for card in cards:
            card.validate()
        assert cards[0].agent_id == VALID_ID
        assert cards[1].agent_id == VALID_ID2

    def test_crew_to_agentcards_auto_ids(self):
        """Without explicit IDs, deterministic hashes are generated."""
        _, crew_to_agentcards = self._get()
        crew = MockCrew([
            MockCrewAgent("Researcher", "Research things"),
            MockCrewAgent("Writer", "Write content"),
        ])
        cards = crew_to_agentcards(crew, base_url="https://crew.example.com")
        # Both should validate (auto-generated IDs are Crockford)
        for card in cards:
            card.validate()

    def test_empty_crew_raises(self):
        _, crew_to_agentcards = self._get()
        with pytest.raises(ValueError, match="no agents"):
            crew_to_agentcards(MockCrew([]))

    def test_tags_present(self):
        agent_to_agentcard, _ = self._get()
        agent = MockCrewAgent("Analyst", "Analyse data")
        card = agent_to_agentcard(agent, VALID_ID, "https://example.com")
        primary_cap = card.capabilities[0]
        assert primary_cap.tags is not None
        assert "crewai" in primary_cap.tags


# ── AutoGen mocks ─────────────────────────────────────────────────────────────

class MockAutoGenAgent:
    """Minimal mock of autogen.ConversableAgent."""
    def __init__(self, name, system_message="", description="",
                 function_map=None, _tools=None):
        self.name = name
        self.system_message = system_message
        self.description = description
        self.function_map = function_map or {}
        self._tools = _tools or []


class MockGroupChat:
    """Minimal mock of autogen.GroupChat."""
    def __init__(self, agents):
        self.agents = agents


class TestAutoGenAdapter:
    def _get(self):
        from agentcard_adapters.autogen_adapter import (
            agent_to_agentcard, groupchat_to_agentcards,
            agentcard_to_tool_function, AgentCardRegistry,
        )
        return (agent_to_agentcard, groupchat_to_agentcards,
                agentcard_to_tool_function, AgentCardRegistry)

    def test_agent_to_agentcard(self):
        agent_to_agentcard, *_ = self._get()
        agent = MockAutoGenAgent(
            name="assistant",
            system_message="You are a helpful AI assistant.",
            description="A helpful assistant agent.",
        )
        card = agent_to_agentcard(agent, VALID_ID, "https://autogen.example.com")
        card.validate()
        assert card.name == "assistant"
        assert card.capabilities[0].id == "assistant"

    def test_description_preferred_over_system_message(self):
        agent_to_agentcard, *_ = self._get()
        agent = MockAutoGenAgent(
            name="agent",
            system_message="Long system message...",
            description="Short description.",
        )
        card = agent_to_agentcard(agent, VALID_ID, "https://example.com")
        assert card.capabilities[0].description == "Short description."

    def test_system_message_fallback(self):
        agent_to_agentcard, *_ = self._get()
        agent = MockAutoGenAgent(name="agent", system_message="Be helpful.")
        card = agent_to_agentcard(agent, VALID_ID, "https://example.com")
        assert "Be helpful" in card.capabilities[0].description

    def test_function_map_becomes_capabilities(self):
        agent_to_agentcard, *_ = self._get()
        agent = MockAutoGenAgent(
            name="coder",
            description="A coding agent.",
            function_map={"run_code": None, "lint_code": None},
        )
        card = agent_to_agentcard(agent, VALID_ID, "https://example.com",
                                   include_function_capabilities=True)
        fn_ids = [c.id for c in card.capabilities if c.id.startswith("fn.")]
        assert "fn.run_code" in fn_ids
        assert "fn.lint_code" in fn_ids

    def test_v04_tools_become_capabilities(self):
        agent_to_agentcard, *_ = self._get()
        agent = MockAutoGenAgent(
            name="assistant",
            description="Assistant.",
            _tools=[
                {"function": {"name": "web_search",
                              "description": "Search the web.",
                              "parameters": {"type": "object"}}},
            ],
        )
        card = agent_to_agentcard(agent, VALID_ID, "https://example.com")
        fn_ids = [c.id for c in card.capabilities if c.id.startswith("fn.")]
        assert "fn.web_search" in fn_ids

    def test_groupchat_to_agentcards(self):
        _, groupchat_to_agentcards, *_ = self._get()
        gc = MockGroupChat([
            MockAutoGenAgent("assistant", description="Helpful."),
            MockAutoGenAgent("user_proxy", description="User proxy."),
        ])
        cards = groupchat_to_agentcards(
            gc,
            agent_ids=[VALID_ID, VALID_ID2],
            base_url="https://autogen.example.com",
        )
        assert len(cards) == 2
        for card in cards:
            card.validate()

    def test_empty_groupchat_raises(self):
        _, groupchat_to_agentcards, *_ = self._get()
        with pytest.raises(ValueError):
            groupchat_to_agentcards(MockGroupChat([]))

    def test_agentcard_to_tool_function_schema(self):
        *_, agentcard_to_tool_function, _ = self._get()
        from agentcard_adapters.core import AgentCard, Capability, Endpoint
        card = AgentCard(
            agent_id=VALID_ID,
            name="My Tool",
            version="1.0.0",
            capabilities=[Capability(
                id="compute.add",
                description="Add two numbers.",
                input_schema={
                    "type": "object",
                    "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                    "required": ["a", "b"],
                },
            )],
            endpoint=Endpoint(protocol="http", url="https://tool.example.com"),
        )
        fn, schema = agentcard_to_tool_function(card)
        assert schema["name"] == "compute_add"
        assert "Add two numbers" in schema["description"]
        assert callable(fn)

    def test_registry(self):
        *_, AgentCardRegistry = self._get()
        from agentcard_adapters.core import AgentCard, Capability, Endpoint

        def make_card(aid, name):
            return AgentCard(
                agent_id=aid, name=name, version="1.0.0",
                capabilities=[Capability(id="task.run", description="Run a task.")],
                endpoint=Endpoint(protocol="http", url="https://example.com"),
            )

        registry = AgentCardRegistry()
        registry.register(make_card(VALID_ID, "Assistant"))
        registry.register(make_card(VALID_ID2, "Researcher"))

        assert len(registry) == 2
        assert registry.get("assistant") is not None
        assert registry.get("researcher") is not None
        assert registry.get_by_id(VALID_ID).name == "Assistant"
        assert registry.get("nonexistent") is None

    def test_registry_tool_functions(self):
        *_, AgentCardRegistry = self._get()
        from agentcard_adapters.core import AgentCard, Capability, Endpoint

        card = AgentCard(
            agent_id=VALID_ID, name="MyAgent", version="1.0.0",
            capabilities=[Capability(id="task.run", description="Run.")],
            endpoint=Endpoint(protocol="http", url="https://example.com"),
        )
        registry = AgentCardRegistry()
        registry.register(card)
        fns = registry.all_tool_functions()
        assert len(fns) == 1
        assert all(callable(f) for f in fns.values())
