"""
Tests for agentcard-mcp server tools.

All tests use internal Python calls — no MCP transport, no network calls.
This tests the business logic directly (declare/resolve/validate/list).
"""

import json
import sys
import os

# Add the src directory so we can import agentcard_mcp without installing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Patch FastMCP before import to avoid needing 'mcp' package in tests
import types
import unittest.mock as mock

# Create a minimal FastMCP stub
class _FakeFastMCP:
    def __init__(self, name, description=""):
        self.name = name
    def tool(self):
        def decorator(fn):
            return fn
        return decorator
    def resource(self, uri):
        def decorator(fn):
            return fn
        return decorator
    def run(self, **kwargs):
        pass

_fake_mcp_module = types.ModuleType("mcp")
_fake_mcp_module.server = types.ModuleType("mcp.server")
_fake_mcp_module.server.fastmcp = types.ModuleType("mcp.server.fastmcp")
_fake_mcp_module.server.fastmcp.FastMCP = _FakeFastMCP
sys.modules["mcp"] = _fake_mcp_module
sys.modules["mcp.server"] = _fake_mcp_module.server
sys.modules["mcp.server.fastmcp"] = _fake_mcp_module.server.fastmcp

# NOW import the server module
import importlib
import agentcard_mcp.server as srv

# Re-import the actual functions (decorators were no-ops in test mode)
from agentcard_mcp.server import (
    _validate_card,
    agentcard_declare,
    agentcard_resolve,
    agentcard_validate,
    agentcard_list,
    get_schema,
    get_registry,
    _registry,
    LANDAUER_FLOOR_JOULES,
)

import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

VALID_CARD = {
    "agent_id": "01HZQK3P8EMXR9V7T5N2W4J6C0",
    "name": "TestAgent",
    "version": "1.0.0",
    "capabilities": [
        {"id": "text.generate", "description": "Generate text."},
        {"id": "tool.web_search", "description": "Search the web."},
    ],
    "endpoint": {"protocol": "https", "url": "https://test.example.com/api"},
}


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear the in-memory registry before each test."""
    _registry.clear()
    yield
    _registry.clear()


# ── _validate_card ────────────────────────────────────────────────────────────

class TestValidateCard:
    def test_valid_card_no_errors(self):
        errors = _validate_card(VALID_CARD)
        assert errors == []

    def test_invalid_ulid_wrong_length(self):
        card = {**VALID_CARD, "agent_id": "TOOSHORT"}
        errors = _validate_card(card)
        assert any("26-char" in e for e in errors)

    def test_invalid_ulid_bad_chars(self):
        # Contains 'I' which is forbidden in Crockford Base32
        card = {**VALID_CARD, "agent_id": "01IIIIIIIIIIIIIIIIIIIIIIII"}
        errors = _validate_card(card)
        assert any("26-char" in e for e in errors)

    def test_invalid_version_not_semver(self):
        card = {**VALID_CARD, "version": "not-semver"}
        errors = _validate_card(card)
        assert any("semver" in e for e in errors)

    def test_valid_prerelease_version(self):
        card = {**VALID_CARD, "version": "2.0.0-beta.1"}
        errors = _validate_card(card)
        assert errors == []

    def test_empty_capabilities(self):
        card = {**VALID_CARD, "capabilities": []}
        errors = _validate_card(card)
        assert any("capabilities" in e for e in errors)

    def test_invalid_capability_id_uppercase(self):
        card = {**VALID_CARD, "capabilities": [{"id": "Text.Generate"}]}
        errors = _validate_card(card)
        assert any("capabilities[0].id" in e for e in errors)

    def test_invalid_capability_id_starts_with_dot(self):
        card = {**VALID_CARD, "capabilities": [{"id": ".bad"}]}
        errors = _validate_card(card)
        assert any("capabilities[0].id" in e for e in errors)

    def test_valid_dotted_capability_id(self):
        card = {**VALID_CARD, "capabilities": [{"id": "a2a.identity.declare"}]}
        errors = _validate_card(card)
        assert errors == []

    def test_invalid_endpoint_protocol(self):
        card = {**VALID_CARD, "endpoint": {"protocol": "ftp", "url": "ftp://test.com"}}
        errors = _validate_card(card)
        assert any("protocol" in e for e in errors)

    def test_mcp_protocol_valid(self):
        card = {**VALID_CARD, "endpoint": {"protocol": "mcp", "url": "mcp://localhost/agent"}}
        errors = _validate_card(card)
        assert errors == []

    def test_sub_landauer_pricing_rejected(self):
        card = {**VALID_CARD, "pricing": {"base_cost_joules": 1e-30}}
        errors = _validate_card(card)
        assert any("Landauer" in e for e in errors)

    def test_zero_pricing_allowed(self):
        card = {**VALID_CARD, "pricing": {"base_cost_joules": 0}}
        errors = _validate_card(card)
        assert errors == []

    def test_above_landauer_pricing_allowed(self):
        card = {**VALID_CARD, "pricing": {"base_cost_joules": LANDAUER_FLOOR_JOULES * 10}}
        errors = _validate_card(card)
        assert errors == []

    def test_exact_landauer_floor_allowed(self):
        card = {**VALID_CARD, "pricing": {"base_cost_joules": LANDAUER_FLOOR_JOULES}}
        errors = _validate_card(card)
        assert errors == []


# ── agentcard_declare ─────────────────────────────────────────────────────────

class TestDeclare:
    def test_valid_declare_succeeds(self):
        result = agentcard_declare(json.dumps(VALID_CARD))
        assert "✓" in result
        assert "01HZQK3P8EMXR9V7T5N2W4J6C0" in result
        assert "TestAgent" in result

    def test_declare_stores_in_registry(self):
        agentcard_declare(json.dumps(VALID_CARD))
        assert "01HZQK3P8EMXR9V7T5N2W4J6C0" in _registry

    def test_invalid_json_returns_error(self):
        result = agentcard_declare("{not valid json}")
        assert "ERROR" in result
        assert "JSON" in result

    def test_invalid_card_returns_validation_errors(self):
        bad_card = {**VALID_CARD, "agent_id": "BAD"}
        result = agentcard_declare(json.dumps(bad_card))
        assert "ERROR" in result
        assert "26-char" in result

    def test_declare_overwrites_existing(self):
        agentcard_declare(json.dumps(VALID_CARD))
        updated = {**VALID_CARD, "name": "UpdatedAgent"}
        agentcard_declare(json.dumps(updated))
        assert _registry["01HZQK3P8EMXR9V7T5N2W4J6C0"]["name"] == "UpdatedAgent"


# ── agentcard_resolve ─────────────────────────────────────────────────────────

class TestResolve:
    def test_resolve_by_exact_id(self):
        agentcard_declare(json.dumps(VALID_CARD))
        result = agentcard_resolve("01HZQK3P8EMXR9V7T5N2W4J6C0")
        data = json.loads(result)
        assert data["name"] == "TestAgent"

    def test_resolve_by_name_partial(self):
        agentcard_declare(json.dumps(VALID_CARD))
        result = agentcard_resolve("test")
        data = json.loads(result)
        assert data["agent_id"] == "01HZQK3P8EMXR9V7T5N2W4J6C0"

    def test_resolve_case_insensitive(self):
        agentcard_declare(json.dumps(VALID_CARD))
        result = agentcard_resolve("TESTAGENT")
        data = json.loads(result)
        assert data["name"] == "TestAgent"

    def test_resolve_not_found(self):
        # Need a non-empty registry so we get "not found" rather than "empty"
        agentcard_declare(json.dumps(VALID_CARD))
        result = agentcard_resolve("zzz_definitely_not_here")
        assert "No agent found" in result

    def test_resolve_empty_registry(self):
        result = agentcard_resolve("anything")
        assert "empty" in result.lower()

    def test_resolve_multiple_matches_returns_summary(self):
        card1 = {**VALID_CARD, "name": "ResearchAgent"}
        card2 = {
            **VALID_CARD,
            "agent_id": "01HZQK3P8EMXR9V7T5N2W4J6C1",
            "name": "ResearchBot",
        }
        agentcard_declare(json.dumps(card1))
        agentcard_declare(json.dumps(card2))
        result = agentcard_resolve("research")
        assert "Found 2" in result


# ── agentcard_validate ────────────────────────────────────────────────────────

class TestValidateTool:
    def test_valid_card_returns_valid(self):
        result = agentcard_validate(json.dumps(VALID_CARD))
        assert result.startswith("VALID ✓")
        assert "01HZQK3P8EMXR9V7T5N2W4J6C0" in result

    def test_invalid_json_returns_invalid(self):
        result = agentcard_validate("not json")
        assert "INVALID" in result

    def test_invalid_card_returns_errors(self):
        bad = {**VALID_CARD, "version": "bad"}
        result = agentcard_validate(json.dumps(bad))
        assert "INVALID" in result
        assert "semver" in result

    def test_sub_landauer_pricing_caught(self):
        card = {**VALID_CARD, "pricing": {"base_cost_joules": 1e-100}}
        result = agentcard_validate(json.dumps(card))
        assert "INVALID" in result
        assert "Landauer" in result


# ── agentcard_list ────────────────────────────────────────────────────────────

class TestList:
    def test_empty_registry_message(self):
        result = agentcard_list()
        assert "No agents registered" in result

    def test_list_shows_declared_agent(self):
        agentcard_declare(json.dumps(VALID_CARD))
        result = agentcard_list()
        assert "01HZQK3P8EMXR9V7T5N2W4J6C0" in result
        assert "TestAgent" in result
        assert "Total: 1" in result

    def test_list_shows_capability_count(self):
        agentcard_declare(json.dumps(VALID_CARD))
        result = agentcard_list()
        assert "2" in result  # 2 capabilities


# ── Resources ─────────────────────────────────────────────────────────────────

class TestResources:
    def test_schema_resource_is_valid_json(self):
        schema = json.loads(get_schema())
        assert schema["title"] == "AgentCard"
        assert "agent_id" in schema["properties"]
        assert "capabilities" in schema["properties"]

    def test_registry_resource_empty(self):
        data = json.loads(get_registry())
        assert data == []

    def test_registry_resource_after_declare(self):
        agentcard_declare(json.dumps(VALID_CARD))
        data = json.loads(get_registry())
        assert len(data) == 1
        assert data[0]["name"] == "TestAgent"
