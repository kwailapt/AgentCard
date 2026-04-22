"""
agentcard_adapters.core
=======================

Pure-Python mirror of the AgentCard v1.0 schema (kwailapt/AgentCard).
Zero runtime dependencies — only stdlib ``typing`` and ``dataclasses``.

Schema invariants (enforced in ``AgentCard.validate()``):

- ``agent_id``: 26-character Crockford Base32 ULID.
- ``version``:  semver 2.0 (MAJOR.MINOR.PATCH[-pre][+build]).
- ``capabilities``: at least one entry; each ``id`` matches
  ``^[a-z0-9][a-z0-9._-]*$`` (dot-namespaced, e.g. ``text.generate``).
- ``pricing.base_cost_joules``: if non-zero, must be ≥ Landauer floor
  at 300 K: k_B × 300 × ln(2) ≈ 2.854 × 10⁻²¹ J.

Reference implementation (Rust): https://github.com/kwailapt/AgentCard
Full JSON Schema: https://github.com/kwailapt/AgentCard/blob/main/schema.json
Apache 2.0 + CC-BY 4.0 (spec). Patent non-reservation: see NOTICE.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

# ── Physics constant ──────────────────────────────────────────────────────────

#: Landauer floor at 300 K: k_B × 300 × ln(2) ≈ 2.854 × 10⁻²¹ J.
#: Any ``base_cost_joules`` strictly between 0 and this value is
#: physically impossible — it would imply erasing less than one bit.
LANDAUER_FLOOR_JOULES: float = 2.854e-21

# ── Crockford Base32 alphabet (no I, L, O, U) ────────────────────────────────
_CROCKFORD = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
_SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<pre>[0-9A-Za-z\-\.]+))?(?:\+(?P<build>[0-9A-Za-z\-\.]+))?$"
)
_CAP_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def _valid_ulid(s: str) -> bool:
    return len(s) == 26 and all(c in _CROCKFORD for c in s)


def _valid_semver(s: str) -> bool:
    return _SEMVER_RE.match(s) is not None


def _valid_cap_id(s: str) -> bool:
    return bool(s) and bool(_CAP_ID_RE.match(s))


# ── Sub-types ─────────────────────────────────────────────────────────────────

@dataclass
class Capability:
    """A single capability the agent can perform."""

    #: Machine-readable id — dot-namespaced, e.g. ``text.generate``.
    id: str
    #: Human-readable description (non-empty).
    description: str
    #: Optional semantic tags for discovery.
    tags: Optional[list[str]] = None
    #: JSON Schema for accepted input, or ``None`` for unstructured.
    input_schema: Optional[dict[str, Any]] = None
    #: JSON Schema for produced output, or ``None`` for unstructured.
    output_schema: Optional[dict[str, Any]] = None


@dataclass
class AuthConfig:
    """Authentication configuration."""

    #: One of: ``none``, ``bearer``, ``api_key``, ``oauth2``, ``mtls``.
    scheme: str
    #: Token endpoint URL (for ``oauth2``).
    token_url: Optional[str] = None
    #: Header name where the credential is sent (for ``api_key``).
    header: Optional[str] = None


@dataclass
class Endpoint:
    """How to reach this agent."""

    #: One of: ``http``, ``websocket``, ``sse``, ``grpc``, ``mcp``,
    #: ``google_a2a``, ``native``.
    protocol: str
    #: URL or address of the endpoint (non-empty).
    url: str
    #: Optional health-check endpoint.
    health_url: Optional[str] = None
    #: Authentication configuration. ``None`` means no auth required.
    auth: Optional[AuthConfig] = None


@dataclass
class PricingModel:
    """Cost model using Landauer thermodynamic units."""

    #: Base cost per request in Joules.
    #: If non-zero, must be ≥ ``LANDAUER_FLOOR_JOULES``.
    base_cost_joules: Optional[float] = None
    #: Estimated end-to-end latency in milliseconds.
    estimated_latency_ms: Optional[float] = None
    #: ISO 4217 currency code or token symbol (e.g. ``"USD"``).
    currency: Optional[str] = None
    #: Cost per request in the fiat/token currency.
    cost_per_request: Optional[float] = None


@dataclass
class EpiplexityCert:
    """Proof of structured cognitive behaviour (ε ≥ 0.7)."""

    agent_id: int
    epsilon: float
    s_t: float
    h_t: float
    issued_at_iota: int


@dataclass
class Metadata:
    """PACR-derived metadata. Fields are computed, never self-declared."""

    interaction_count: Optional[int] = None
    avg_latency_ms: Optional[float] = None
    avg_cost_joules: Optional[float] = None
    reputation_score: Optional[float] = None
    influence_rank: Optional[float] = None
    critical_score: Optional[float] = None
    #: One of: ``banned``, ``untrusted``, ``basic``, ``established``, ``verified``.
    trust_tier: Optional[str] = None
    epiplexity_cert: Optional[EpiplexityCert] = None


@dataclass
class GoalSubscription:
    """Declaration that this agent subscribes to another agent's goal field."""

    #: 26-char ULID of the target agent.
    target_agent_id: str
    #: Human-readable label for this subscription.
    label: str
    #: Coupling scale multiplier ∈ (0, 1]. Default 1.0.
    coupling_scale: float = 1.0


# ── AgentCard ─────────────────────────────────────────────────────────────────

@dataclass
class AgentCard:
    """
    AgentCard v1.0 — the self-declaration of an agent's identity,
    capabilities, and terms of interaction.

    This is to A2A what HTTP headers are to the web: a standard,
    machine-parseable capability declaration that works with any framework.

    Example
    -------
    >>> card = AgentCard(
    ...     agent_id="01HZQK3P8EMXR9V7T5N2W4J6C0",
    ...     name="My Agent",
    ...     version="1.0.0",
    ...     capabilities=[Capability(id="text.generate",
    ...                              description="Generate text from a prompt.")],
    ...     endpoint=Endpoint(protocol="http",
    ...                       url="https://agent.example.com/api"),
    ... )
    >>> card.validate()  # raises ValueError if invalid
    """

    #: Globally unique agent identifier (26-char Crockford Base32 ULID).
    agent_id: str
    #: Human-readable display name (1–128 characters).
    name: str
    #: Semantic version of this agent card (semver 2.0).
    version: str
    #: Capabilities offered by this agent (at least one required).
    capabilities: list[Capability]
    #: How to reach this agent.
    endpoint: Endpoint
    #: Optional cost model using Landauer thermodynamic units.
    pricing: Optional[PricingModel] = None
    #: Metadata derived from PACR causal ledger (read-only, computed externally).
    metadata: Optional[Metadata] = None
    #: Goal field subscriptions (Phase 12 coalition protocol).
    goal_subscriptions: list[GoalSubscription] = field(default_factory=list)

    # ── Validation ────────────────────────────────────────────────────────────

    def validate(self) -> None:
        """
        Validate all schema invariants.

        Raises
        ------
        ValueError
            If any invariant is violated. The message describes the violation.
        """
        if not _valid_ulid(self.agent_id):
            raise ValueError(
                f"agent_id must be a 26-character Crockford Base32 ULID, "
                f"got: {self.agent_id!r}"
            )
        if not self.name or len(self.name) > 128:
            raise ValueError("name must be 1–128 characters")
        if not _valid_semver(self.version):
            raise ValueError(
                f"version must be semver 2.0 (e.g. '1.0.0'), got: {self.version!r}"
            )
        if not self.capabilities:
            raise ValueError("capabilities must contain at least one entry")
        for i, cap in enumerate(self.capabilities):
            if not _valid_cap_id(cap.id):
                raise ValueError(
                    f"capabilities[{i}].id must match ^[a-z0-9][a-z0-9._-]*$, "
                    f"got: {cap.id!r}"
                )
            if not cap.description:
                raise ValueError(f"capabilities[{i}].description must not be empty")
        if not self.endpoint.url:
            raise ValueError("endpoint.url must not be empty")
        if self.pricing and self.pricing.base_cost_joules is not None:
            j = self.pricing.base_cost_joules
            if j < 0:
                raise ValueError("pricing.base_cost_joules must be >= 0")
            if 0 < j < LANDAUER_FLOOR_JOULES:
                raise ValueError(
                    f"pricing.base_cost_joules {j:.3e} J is below the Landauer "
                    f"floor at 300 K ({LANDAUER_FLOOR_JOULES:.3e} J) — "
                    f"physically implausible"
                )
        for sub in self.goal_subscriptions:
            if not _valid_ulid(sub.target_agent_id):
                raise ValueError(
                    f"GoalSubscription.target_agent_id must be a 26-char ULID"
                )
            if not (0 < sub.coupling_scale <= 1.0):
                raise ValueError("GoalSubscription.coupling_scale must be in (0, 1]")

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dict (schema.json format)."""
        d: dict[str, Any] = {
            "agent_id": self.agent_id,
            "name": self.name,
            "version": self.version,
            "capabilities": [_cap_to_dict(c) for c in self.capabilities],
            "endpoint": _endpoint_to_dict(self.endpoint),
        }
        if self.pricing:
            d["pricing"] = _pricing_to_dict(self.pricing)
        if self.metadata:
            d["metadata"] = _metadata_to_dict(self.metadata)
        if self.goal_subscriptions:
            d["goal_subscriptions"] = [
                {
                    "target_agent_id": s.target_agent_id,
                    "label": s.label,
                    "coupling_scale": s.coupling_scale,
                }
                for s in self.goal_subscriptions
            ]
        return d

    def to_json(self, **kwargs: Any) -> str:
        """Serialise to a JSON string."""
        return json.dumps(self.to_dict(), **kwargs)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "AgentCard":
        """Deserialise from a JSON-compatible dict."""
        caps = [
            Capability(
                id=c["id"],
                description=c["description"],
                tags=c.get("tags"),
                input_schema=c.get("input_schema"),
                output_schema=c.get("output_schema"),
            )
            for c in d["capabilities"]
        ]
        ep_raw = d["endpoint"]
        auth = None
        if ep_raw.get("auth"):
            a = ep_raw["auth"]
            auth = AuthConfig(
                scheme=a["scheme"],
                token_url=a.get("token_url"),
                header=a.get("header"),
            )
        ep = Endpoint(
            protocol=ep_raw["protocol"],
            url=ep_raw["url"],
            health_url=ep_raw.get("health_url"),
            auth=auth,
        )
        pricing = None
        if d.get("pricing"):
            p = d["pricing"]
            pricing = PricingModel(
                base_cost_joules=p.get("base_cost_joules"),
                estimated_latency_ms=p.get("estimated_latency_ms"),
                currency=p.get("currency"),
                cost_per_request=p.get("cost_per_request"),
            )
        metadata = None
        if d.get("metadata"):
            m = d["metadata"]
            cert = None
            if m.get("pacr:epiplexity_cert"):
                ec = m["pacr:epiplexity_cert"]
                cert = EpiplexityCert(
                    agent_id=ec["agent_id"],
                    epsilon=ec["epsilon"],
                    s_t=ec["s_t"],
                    h_t=ec["h_t"],
                    issued_at_iota=ec["issued_at_iota"],
                )
            metadata = Metadata(
                interaction_count=m.get("pacr:interaction_count"),
                avg_latency_ms=m.get("pacr:avg_latency_ms"),
                avg_cost_joules=m.get("pacr:avg_cost_joules"),
                reputation_score=m.get("pacr:reputation_score"),
                influence_rank=m.get("pacr:influence_rank"),
                critical_score=m.get("pacr:critical_score"),
                trust_tier=m.get("pacr:trust_tier"),
                epiplexity_cert=cert,
            )
        subs = [
            GoalSubscription(
                target_agent_id=s["target_agent_id"],
                label=s["label"],
                coupling_scale=s.get("coupling_scale", 1.0),
            )
            for s in d.get("goal_subscriptions", [])
        ]
        return cls(
            agent_id=d["agent_id"],
            name=d["name"],
            version=d["version"],
            capabilities=caps,
            endpoint=ep,
            pricing=pricing,
            metadata=metadata,
            goal_subscriptions=subs,
        )

    @classmethod
    def from_json(cls, s: str) -> "AgentCard":
        """Deserialise from a JSON string."""
        return cls.from_dict(json.loads(s))


# ── Private helpers ───────────────────────────────────────────────────────────

def _cap_to_dict(c: Capability) -> dict[str, Any]:
    d: dict[str, Any] = {"id": c.id, "description": c.description}
    if c.tags is not None:
        d["tags"] = c.tags
    if c.input_schema is not None:
        d["input_schema"] = c.input_schema
    if c.output_schema is not None:
        d["output_schema"] = c.output_schema
    return d


def _endpoint_to_dict(e: Endpoint) -> dict[str, Any]:
    d: dict[str, Any] = {"protocol": e.protocol, "url": e.url}
    if e.health_url:
        d["health_url"] = e.health_url
    if e.auth:
        ad: dict[str, Any] = {"scheme": e.auth.scheme}
        if e.auth.token_url:
            ad["token_url"] = e.auth.token_url
        if e.auth.header:
            ad["header"] = e.auth.header
        d["auth"] = ad
    return d


def _pricing_to_dict(p: PricingModel) -> dict[str, Any]:
    d: dict[str, Any] = {}
    if p.base_cost_joules is not None:
        d["base_cost_joules"] = p.base_cost_joules
    if p.estimated_latency_ms is not None:
        d["estimated_latency_ms"] = p.estimated_latency_ms
    if p.currency is not None:
        d["currency"] = p.currency
    if p.cost_per_request is not None:
        d["cost_per_request"] = p.cost_per_request
    return d


def _metadata_to_dict(m: Metadata) -> dict[str, Any]:
    d: dict[str, Any] = {}
    if m.interaction_count is not None:
        d["pacr:interaction_count"] = m.interaction_count
    if m.avg_latency_ms is not None:
        d["pacr:avg_latency_ms"] = m.avg_latency_ms
    if m.avg_cost_joules is not None:
        d["pacr:avg_cost_joules"] = m.avg_cost_joules
    if m.reputation_score is not None:
        d["pacr:reputation_score"] = m.reputation_score
    if m.influence_rank is not None:
        d["pacr:influence_rank"] = m.influence_rank
    if m.critical_score is not None:
        d["pacr:critical_score"] = m.critical_score
    if m.trust_tier is not None:
        d["pacr:trust_tier"] = m.trust_tier
    if m.epiplexity_cert is not None:
        ec = m.epiplexity_cert
        d["pacr:epiplexity_cert"] = {
            "agent_id": ec.agent_id,
            "epsilon": ec.epsilon,
            "s_t": ec.s_t,
            "h_t": ec.h_t,
            "issued_at_iota": ec.issued_at_iota,
        }
    return d
