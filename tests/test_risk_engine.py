import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.schemas import ClaimAssessment, ResponseAudit
from app.risk_engine import compute_score
from app.policy_engine import decide


def _audit(hallucination_risk="none", contains_pii=False, bias_flag=False,
           pii_entities=None, risk_type="none"):
    claim = ClaimAssessment(
        claim_text="test claim",
        is_grounded=hallucination_risk == "none",
        grounding_confidence=1.0 if hallucination_risk == "none" else 0.3,
        contains_pii=contains_pii,
        pii_entities=pii_entities or [],
        bias_flag=bias_flag,
        bias_reasoning="test bias" if bias_flag else None,
        hallucination_risk=hallucination_risk,
    )
    return ResponseAudit(
        claims=[claim],
        primary_risk_type=risk_type,
        rationale="test",
    )


WEIGHTS = {
    "hallucination": 0.40,
    "privacy": 0.30,
    "bias": 0.20,
    "anomaly": 0.10,
}

POLICY = {
    "thresholds": {
        "allow_below": 0.20,
        "edit_below": 0.40,
        "flag_below": 0.60,
        "block_below": 0.80,
    },
    "human_review_above": 0.70,
    "pii_action": "edit",
}


class TestScoreFusion:
    def test_clean_response_scores_low(self):
        audit = _audit()
        score, _, _ = compute_score(audit, [], 0.1, WEIGHTS)
        assert score < 0.05, f"clean response scored {score}"

    def test_high_hallucination_scores_high(self):
        audit = _audit(hallucination_risk="high", risk_type="hallucination")
        score, components, _ = compute_score(audit, [], 0.1, WEIGHTS)
        assert score >= 0.4, f"high hallucination scored only {score}"
        assert components["hallucination_severity"] == 1.0

    def test_pii_prescan_hits_set_privacy_signal(self):
        audit = _audit()
        hits = [{"type": "EMAIL", "value": "test@test.com"}]
        score, components, reasons = compute_score(audit, hits, 0.0, WEIGHTS)
        assert components["privacy_signal"] == 1.0
        assert any("PII" in r for r in reasons)

    def test_bias_flag_sets_signal(self):
        audit = _audit(bias_flag=True, risk_type="bias")
        score, components, _ = compute_score(audit, [], 0.0, WEIGHTS)
        assert components["bias_signal"] == 1.0
        assert score >= 0.2

    def test_combined_risks_add_up(self):
        audit = _audit(hallucination_risk="high", contains_pii=True,
                       bias_flag=True, risk_type="overlap")
        hits = [{"type": "PHONE", "value": "+91 12345 67890"}]
        score, _, _ = compute_score(audit, hits, 0.5, WEIGHTS)
        assert score >= 0.9


class TestPolicyDecision:
    def test_low_score_allows(self):
        d = decide(0.10, ["all checks passed"], POLICY)
        assert d.action == "allow"
        assert not d.requires_human

    def test_medium_score_flags(self):
        d = decide(0.50, ["hallucination severity 0.6"], POLICY)
        assert d.action == "flag"

    def test_high_score_blocks(self):
        d = decide(0.70, ["hallucination severity 1.0"], POLICY)
        assert d.action == "block"
        assert d.requires_human

    def test_very_high_score_escalates(self):
        d = decide(0.85, ["multiple risks"], POLICY)
        assert d.action == "escalate"
        assert d.requires_human

    def test_momentum_override_forces_escalate(self):
        d = decide(0.10, ["all checks passed"], POLICY, momentum_override=True)
        assert d.action == "escalate"
        assert d.requires_human

    def test_pii_action_floor(self):
        d = decide(0.05, ["PII prescan: EMAIL"], POLICY)
        assert d.action == "edit"
