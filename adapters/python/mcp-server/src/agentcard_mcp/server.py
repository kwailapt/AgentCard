"""
agentcard_mcp.server
====================

MCP server entry point — gives any LLM/Claude agent an AgentCard v1.0
identity layer for agent-to-agent (A2A) communication.

Start with:
    python -m agentcard_mcp          # stdio (default, for Claude Desktop)
    python -m agentcard_mcp --http   # HTTP/SSE on :8890

AgentCard standard: https://github.com/kwailapt/AgentCard
Apache 2.0. Patent non-reservation: see NOTICE.
"""

from __future__ import annotations

import json
import re
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as _e:
    raise ImportError(
        "agentcard-mcp requires the 'mcp' package. "
        "Install it with: pip install agentcard-mcp[mcp]"
    ) from _e

from .schema import AGENTCARD_SCHEMA

# ── Physics constant ──────────────────────────────────────────────────────────
LANDAUER_FLOOR_JOULES: float = 2.854e-21   # k_B × 300 K × ln(2)

# ── Crockford Base32 ──────────────────────────────────────────────────────────
_CROCKFORD = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
_SEMVER_RE = re.compile(
    r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z\-.]+)?(?:\+[0-9A-Za-z\-.]+)?$"
)
_CAP_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

# ── In-memory registry (session-scoped) ──────────────────────────────────────
_registry: dict[str, dict[str, Any]] = {}   # agent_id → raw card dict


# ── Validation helper ─────────────────────────────────────────────────────────

def _validate_card(card: dict[str, Any]) -> list[str]:
    """Return a list of validation errors (empty = valid)."""
    errors: list[str] = []

    agent_id = card.get("agent_id", "")
    if not (len(agent_id) == 26 and all(c in _CROCKFORD for c in agent_id)):
        errors.append(
            f"agent_id '{agent_id}' must be a 26-char Crockford Base32 ULID."
        )

    name = card.get("name", "")
    if not (1 <= len(name) <= 128):
        errors.append("name must be 1–128 characters.")

    version = card.get("version", "")
    if not _SEMVER_RE.match(version):
        errors.append(f"version '{version}' must be valid semver 2.0.0.")

    caps = card.get("capabilities", [])
    if not caps:
        errors.append("capabilities must have at least one entry.")
    for i, cap in enumerate(caps):
        cap_id = cap.get("id", "")
        if not _CAP_ID_RE.match(cap_id):
            errors.append(
                f"capabilities[{i}].id '{cap_id}' must match ^[a-z0-9][a-z0-9._-]*$"
            )

    ep = card.get("endpoint", {})
    if ep.get("protocol") not in ("http", "https", "grpc", "stdio", "mcp"):
        errors.append(
            f"endpoint.protocol '{ep.get('protocol')}' must be one of: "
            "http, https, grpc, stdio, mcp."
        )
    if not ep.get("url"):
        errors.append("endpoint.url is required.")

    pricing = card.get("pricing")
    if pricing is not None:
        cost = pricing.get("base_cost_joules")
        if cost is not None and cost != 0 and cost < LANDAUER_FLOOR_JOULES:
            errors.append(
                f"pricing.base_cost_joules {cost} is below the Landauer floor "
                f"({LANDAUER_FLOOR_JOULES:.3e} J at 300 K). "
                "Use 0 for free, or a physically plausible value ≥ Landauer floor."
            )

    return errors


# ── MCP Server ────────────────────────────────────────────────────────────────

mcp = FastMCP(
    "AgentCard",
    description=(
        "AgentCard v1.0 identity layer for agent-to-agent (A2A) communication. "
        "Declare your identity, resolve peers, and validate cards against the "
        "AgentCard standard. Learn more: https://github.com/kwailapt/AgentCard"
    ),
)


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def agentcard_declare(card_json: str) -> str:
    """
    Register your AgentCard identity for this session.

    Args:
        card_json: JSON string conforming to the AgentCard v1.0 schema.
                   Required fields: agent_id (26-char ULID), name, version
                   (semver), capabilities (≥1 entry with dot-namespaced id),
                   endpoint (protocol + url).

    Returns:
        Confirmation string with agent_id and name, or error details.

    Example input:
        {
          "agent_id": "01HZQK3P8EMXR9V7T5N2W4J6C0",
          "name": "WebSearchAgent",
          "version": "1.0.0",
          "capabilities": [{"id": "web.search", "description": "Search the web."}],
          "endpoint": {"protocol": "https", "url": "https://my-agent.example.com/api"}
        }
    """
    try:
        card = json.loads(card_json)
    except json.JSONDecodeError as e:
        return f"ERROR: Invalid JSON — {e}"

    errors = _validate_card(card)
    if errors:
        return "ERROR: AgentCard validation failed:\n" + "\n".join(f"  • {e}" for e in errors)

    agent_id: str = card["agent_id"]
    _registry[agent_id] = card
    name: str = card["name"]
    n_caps = len(card.get("capabilities", []))
    return (
        f"✓ AgentCard declared — agent_id={agent_id}, name='{name}', "
        f"capabilities={n_caps}, endpoint={card['endpoint']['url']}"
    )


@mcp.tool()
def agentcard_resolve(query: str) -> str:
    """
    Look up a registered agent's AgentCard by name or agent_id.

    Args:
        query: Agent name (partial match, case-insensitive) or exact 26-char
               agent_id (Crockford Base32 ULID).

    Returns:
        The matching AgentCard as pretty-printed JSON, or a not-found message.
    """
    if not _registry:
        return "Registry is empty. No agents have declared their identity yet."

    # Exact ID match
    if len(query) == 26 and all(c in _CROCKFORD for c in query.upper()):
        card = _registry.get(query.upper())
        if card:
            return json.dumps(card, indent=2)

    # Name substring match (case-insensitive)
    q_lower = query.lower()
    matches = [
        card for card in _registry.values()
        if q_lower in card.get("name", "").lower()
    ]
    if not matches:
        return f"No agent found matching '{query}'."
    if len(matches) == 1:
        return json.dumps(matches[0], indent=2)
    # Multiple matches — return summary
    summaries = [
        f"  {c['agent_id']} — {c['name']} ({len(c.get('capabilities', []))} caps)"
        for c in matches
    ]
    return (
        f"Found {len(matches)} agents matching '{query}':\n"
        + "\n".join(summaries)
        + "\nRefine your query or use the exact agent_id."
    )


@mcp.tool()
def agentcard_validate(card_json: str) -> str:
    """
    Validate a JSON string against the AgentCard v1.0 schema.

    Args:
        card_json: JSON string to validate.

    Returns:
        "VALID" with a summary, or a list of validation errors with
        suggestions for fixing them.

    Use this before sharing an AgentCard with peers or publishing to a
    registry, to catch issues like invalid ULIDs, non-semver versions,
    invalid capability ids, or sub-Landauer pricing claims.
    """
    try:
        card = json.loads(card_json)
    except json.JSONDecodeError as e:
        return f"INVALID: Cannot parse JSON — {e}"

    errors = _validate_card(card)
    if not errors:
        agent_id = card.get("agent_id", "")
        name = card.get("name", "")
        n_caps = len(card.get("capabilities", []))
        cap_ids = ", ".join(c["id"] for c in card.get("capabilities", []))
        return (
            f"VALID ✓\n"
            f"  agent_id    : {agent_id}\n"
            f"  name        : {name}\n"
            f"  version     : {card.get('version')}\n"
            f"  capabilities: {n_caps} — [{cap_ids}]\n"
            f"  endpoint    : {card.get('endpoint', {}).get('url')}"
        )
    return "INVALID ✗\n" + "\n".join(f"  • {e}" for e in errors)


@mcp.tool()
def agentcard_list() -> str:
    """
    List all AgentCards registered in this session.

    Returns:
        A formatted table of registered agents with their ids, names,
        capability counts, and endpoint URLs.
    """
    if not _registry:
        return (
            "No agents registered yet.\n"
            "Use agentcard_declare() to register an agent's identity."
        )

    lines = [f"{'agent_id':26}  {'name':30}  {'caps':5}  endpoint"]
    lines.append("-" * 90)
    for card in _registry.values():
        lines.append(
            f"{card['agent_id']:26}  "
            f"{card.get('name', '')[:30]:30}  "
            f"{len(card.get('capabilities', [])):5}  "
            f"{card.get('endpoint', {}).get('url', '')}"
        )
    lines.append(f"\nTotal: {len(_registry)} agent(s) registered.")
    return "\n".join(lines)


# ── Resources ─────────────────────────────────────────────────────────────────

@mcp.resource("agentcard://schema")
def get_schema() -> str:
    """
    The canonical AgentCard v1.0 JSON Schema.

    Use this schema to validate AgentCard documents or to generate
    AgentCard-compatible payloads. The schema is also available at:
    https://github.com/kwailapt/AgentCard/blob/main/schema.json
    """
    return json.dumps(AGENTCARD_SCHEMA, indent=2)


@mcp.resource("agentcard://registry")
def get_registry() -> str:
    """
    All AgentCards registered in this session as a JSON array.

    Returns an empty array if no agents have declared their identity yet.
    """
    return json.dumps(list(_registry.values()), indent=2)
