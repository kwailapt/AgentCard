"""Tests for agentcard_adapters.core — zero framework dependencies."""

import json
import pytest

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))

from agentcard_adapters.core import (
    AgentCard, Capability, Endpoint, PricingModel,
    GoalSubscription, Metadata, LANDAUER_FLOOR_JOULES,
)

VALID_ID = "01HZQK3P8EMXR9V7T5N2W4J6C0"


def minimal_card(**overrides) -> AgentCard:
    defaults = dict(
        agent_id=VALID_ID,
        name="Test Agent",
        version="1.0.0",
        capabilities=[Capability(id="text.generate", description="Generate text.")],
        endpoint=Endpoint(protocol="http", url="https://example.com"),
    )
    defaults.update(overrides)
    return AgentCard(**defaults)


# ── Validation ────────────────────────────────────────────────────────────────

class TestValidation:
    def test_minimal_valid(self):
        minimal_card().validate()

    def test_rejects_short_agent_id(self):
        with pytest.raises(ValueError, match="26-character"):
            minimal_card(agent_id="SHORT").validate()

    def test_rejects_invalid_crockford(self):
        # I, L, O, U not in Crockford alphabet
        with pytest.raises(ValueError):
            minimal_card(agent_id="ILOUILOUILOUILOUILOUILOUI0").validate()

    def test_accepts_all_crockford(self):
        minimal_card(agent_id="0123456789ABCDEFGHJKMNPQRS").validate()

    def test_rejects_empty_name(self):
        with pytest.raises(ValueError, match="name"):
            minimal_card(name="").validate()

    def test_rejects_bad_semver(self):
        for bad in ("1.0", "v1.0.0", "1.0.0.0"):
            with pytest.raises(ValueError, match="semver"):
                minimal_card(version=bad).validate()

    def test_accepts_semver_with_pre_and_build(self):
        minimal_card(version="1.0.0-rc.1+sha.abc").validate()

    def test_rejects_empty_capabilities(self):
        with pytest.raises(ValueError, match="capabilities"):
            minimal_card(capabilities=[]).validate()

    def test_rejects_invalid_capability_id(self):
        with pytest.raises(ValueError, match=r"capabilities\[0\]\.id"):
            minimal_card(capabilities=[
                Capability(id="Has Spaces", description="desc")
            ]).validate()

    def test_rejects_cost_below_landauer(self):
        with pytest.raises(ValueError, match="Landauer"):
            minimal_card(pricing=PricingModel(base_cost_joules=1e-30)).validate()

    def test_accepts_zero_cost(self):
        minimal_card(pricing=PricingModel(base_cost_joules=0.0)).validate()

    def test_accepts_cost_at_landauer_floor(self):
        minimal_card(pricing=PricingModel(
            base_cost_joules=LANDAUER_FLOOR_JOULES
        )).validate()

    def test_rejects_negative_cost(self):
        with pytest.raises(ValueError):
            minimal_card(pricing=PricingModel(base_cost_joules=-1e-20)).validate()

    def test_rejects_invalid_goal_subscription_ulid(self):
        with pytest.raises(ValueError, match="ULID"):
            minimal_card(goal_subscriptions=[
                GoalSubscription(target_agent_id="SHORT", label="test")
            ]).validate()

    def test_rejects_invalid_coupling_scale(self):
        with pytest.raises(ValueError, match="coupling"):
            minimal_card(goal_subscriptions=[
                GoalSubscription(
                    target_agent_id=VALID_ID, label="test", coupling_scale=0.0
                )
            ]).validate()

    def test_accepts_valid_goal_subscription(self):
        minimal_card(goal_subscriptions=[
            GoalSubscription(target_agent_id=VALID_ID, label="goal", coupling_scale=0.5)
        ]).validate()


# ── Serialisation ─────────────────────────────────────────────────────────────

class TestSerialisation:
    def test_roundtrip_dict(self):
        card = minimal_card()
        assert AgentCard.from_dict(card.to_dict()) == card

    def test_roundtrip_json(self):
        card = minimal_card()
        assert AgentCard.from_json(card.to_json()) == card

    def test_metadata_pacr_prefix(self):
        card = minimal_card(metadata=Metadata(
            interaction_count=42,
            reputation_score=0.9,
            trust_tier="verified",
        ))
        d = card.to_dict()
        meta = d["metadata"]
        assert "pacr:interaction_count" in meta
        assert "pacr:reputation_score" in meta
        assert "pacr:trust_tier" in meta
        assert meta["pacr:interaction_count"] == 42

    def test_goal_subscriptions_roundtrip(self):
        card = minimal_card(goal_subscriptions=[
            GoalSubscription(target_agent_id=VALID_ID, label="goal", coupling_scale=0.7)
        ])
        d = card.to_dict()
        assert d["goal_subscriptions"][0]["coupling_scale"] == 0.7
        card2 = AgentCard.from_dict(d)
        assert card2.goal_subscriptions[0].coupling_scale == 0.7

    def test_pricing_omitted_when_none(self):
        card = minimal_card()
        d = card.to_dict()
        assert "pricing" not in d

    def test_json_is_valid_json(self):
        card = minimal_card()
        # Should not raise
        json.loads(card.to_json())

    def test_landauer_floor_value(self):
        # Physics constant must match k_B × 300K × ln(2)
        import math
        k_b = 1.380_649e-23
        expected = k_b * 300 * math.log(2)
        assert abs(LANDAUER_FLOOR_JOULES - expected) / expected < 0.01
