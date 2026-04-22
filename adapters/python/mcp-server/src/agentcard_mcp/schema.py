"""
AgentCard v1.0 JSON Schema (embedded).

Canonical source: https://github.com/kwailapt/AgentCard/blob/main/schema.json
"""

AGENTCARD_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://raw.githubusercontent.com/kwailapt/AgentCard/main/schema.json",
    "title": "AgentCard",
    "description": (
        "AgentCard v1.0 — framework-neutral identity format for agent-to-agent (A2A) "
        "communication. Analogous to HTTP headers for the agent web."
    ),
    "type": "object",
    "required": ["agent_id", "name", "version", "capabilities", "endpoint"],
    "additionalProperties": False,
    "properties": {
        "agent_id": {
            "type": "string",
            "description": "26-character Crockford Base32 ULID — globally unique causal identity.",
            "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$",
            "examples": ["01HZQK3P8EMXR9V7T5N2W4J6C0"]
        },
        "name": {
            "type": "string",
            "description": "Human-readable display name (1–128 characters).",
            "minLength": 1,
            "maxLength": 128
        },
        "version": {
            "type": "string",
            "description": "Semantic version (semver 2.0.0).",
            "pattern": (
                r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
                r"(?:-[0-9A-Za-z\-.]+)?(?:\+[0-9A-Za-z\-.]+)?$"
            ),
            "examples": ["1.0.0", "2.3.1-beta.1"]
        },
        "capabilities": {
            "type": "array",
            "description": "Ordered list of declared capabilities.",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id"],
                "additionalProperties": False,
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Dot-namespaced capability identifier (e.g. text.generate, tool.web_search).",
                        "pattern": "^[a-z0-9][a-z0-9._-]*$"
                    },
                    "description": {
                        "type": "string",
                        "description": "Human-readable capability description."
                    },
                    "input_schema": {
                        "type": "object",
                        "description": "JSON Schema for capability inputs (OpenAI function-calling compatible)."
                    },
                    "output_schema": {
                        "type": "object",
                        "description": "JSON Schema for capability outputs."
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional categorisation tags."
                    }
                }
            }
        },
        "endpoint": {
            "type": "object",
            "required": ["protocol", "url"],
            "additionalProperties": False,
            "properties": {
                "protocol": {
                    "type": "string",
                    "enum": ["http", "https", "grpc", "stdio", "mcp"],
                    "description": "Transport protocol."
                },
                "url": {
                    "type": "string",
                    "format": "uri",
                    "description": "Endpoint URL."
                },
                "auth": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "scheme": {
                            "type": "string",
                            "enum": ["none", "bearer", "api_key", "oauth2", "mtls"],
                            "default": "none"
                        },
                        "header": {"type": "string"},
                        "scopes": {"type": "array", "items": {"type": "string"}}
                    }
                }
            }
        },
        "pricing": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "base_cost_joules": {
                    "type": "number",
                    "description": (
                        "Minimum energy cost per call in joules. "
                        "Must be 0 (free) or ≥ 2.854e-21 J (Landauer floor at 300 K)."
                    ),
                    "minimum": 0
                },
                "per_token_joules": {
                    "type": "number",
                    "description": "Additional energy cost per output token.",
                    "minimum": 0
                },
                "currency_unit": {
                    "type": "string",
                    "description": "Optional ISO 4217 currency code for monetary pricing.",
                    "examples": ["USD", "EUR"]
                },
                "base_cost_currency": {
                    "type": "number",
                    "description": "Monetary base cost per call.",
                    "minimum": 0
                }
            }
        },
        "metadata": {
            "type": "object",
            "description": "Extensible metadata. Keys with 'pacr:' prefix are PACR-derived.",
            "properties": {
                "pacr:trust_tier": {
                    "type": "string",
                    "enum": ["untrusted", "basic", "established", "verified", "banned"],
                    "description": "Trust tier derived from causal return rate ρ."
                },
                "pacr:substrate_scope": {
                    "type": "string",
                    "description": "Hardware/population substrate (e.g. M1_Ultra, AWS_Graviton, UKBiobank)."
                },
                "pacr:ossification_risk": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Data bias ossification risk level."
                },
                "framework": {
                    "type": "string",
                    "description": "Agent framework (e.g. autogen, crewai, langchain, aevum)."
                },
                "created_at": {
                    "type": "string",
                    "format": "date-time"
                }
            },
            "additionalProperties": True
        },
        "goal_subscriptions": {
            "type": "array",
            "description": "Phase 12: goals this agent subscribes to (CRDT G-Set).",
            "items": {
                "type": "object",
                "required": ["goal_id"],
                "properties": {
                    "goal_id": {"type": "string"},
                    "description": {"type": "string"},
                    "priority": {"type": "number", "minimum": 0, "maximum": 1}
                }
            }
        }
    }
}
