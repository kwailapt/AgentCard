"""
agentcard-mcp
=============

MCP server that gives any Claude / LLM agent an AgentCard v1.0 identity.

Tools
-----
- ``agentcard_declare``  — register your identity (stores in-session)
- ``agentcard_resolve``  — look up a peer agent by name or id
- ``agentcard_validate`` — validate any JSON string as a valid AgentCard
- ``agentcard_list``     — list all registered agents

Resources
---------
- ``agentcard://schema``   — the canonical JSON Schema (v1.0)
- ``agentcard://registry`` — all declared cards as JSON array

AgentCard standard: https://github.com/kwailapt/AgentCard
Apache 2.0. Patent non-reservation: see NOTICE.
"""

__version__ = "0.1.0"
