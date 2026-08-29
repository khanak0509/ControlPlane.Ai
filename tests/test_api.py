import pytest
import sys
import os
import tempfile
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from app.schemas import ClaimAssessment, ResponseAudit, CheckResponse
from app import audit_log, conversation_tracker
from app.main import app
from app.detectors import pii_prescan
from app import decision_actions


client = TestClient(app)


def _mock_audit(**kwargs):
    claim = ClaimAssessment(
        claim_text="test",
        is_grounded=True,
        grounding_confidence=0.9,
        contains_pii=False,
        pii_entities=[],
        bias_flag=False,
        bias_reasoning=None,
        hallucination_risk="none",
    )
    return ResponseAudit(
        claims=[claim],
        primary_risk_type=kwargs.get("primary_risk_type", "none"),
        rationale="ok",
    )


class TestHealthAndAgent:
    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_agent_action_escalates_refund(self):
        r = client.post("/agent-action", json={
            "action": {
                "tool_name": "issue_refund",
                "parameters": {"amount": 500},
                "reversible": False,
                "estimated_impact": "high",
            },
            "use_case": "shopsmart",
            "session_id": "test-agent",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["allowed"] is False
        assert data["action"] == "escalate"

    def test_agent_action_allows_low_impact(self):
        r = client.post("/agent-action", json={
            "action": {
                "tool_name": "update_customer_record",
                "parameters": {"field": "nickname"},
                "reversible": True,
                "estimated_impact": "low",
            },
            "use_case": "shopsmart",
            "session_id": "test-agent-2",
        })
        assert r.status_code == 200
        assert r.json()["allowed"] is True


class TestCheckResponseShape:
    @patch("app.main.anomaly_check.anomaly_score", return_value=0.1)
    @patch("app.main.unified_judge.judge")
    def test_check_returns_modified_response(self, mock_judge, mock_anomaly):
        mock_judge.return_value = _mock_audit()
        r = client.post("/check", json={
            "use_case": "shopsmart",
            "session_id": "shape-test",
            "query": "Can I return?",
            "response": "Yes within 30 days.",
            "source_context": "30 day return window.",
        })
        assert r.status_code == 200
        data = r.json()
        assert "modified_response" in data
        assert "decision" in data
        assert "component_scores" in data
        assert data["modified_response"] == "Yes within 30 days."
        parsed = CheckResponse(**data)
        assert parsed.modified_response

    @patch("app.main.anomaly_check.anomaly_score", return_value=0.1)
    @patch("app.main.unified_judge.judge")
    def test_pii_edit_redacts_in_modified_response(self, mock_judge, mock_anomaly):
        mock_judge.return_value = _mock_audit(primary_risk_type="privacy")
        text = "Contact priya@test.com for help."
        r = client.post("/check", json={
            "use_case": "shopsmart",
            "session_id": "pii-test",
            "query": "help",
            "response": text,
            "source_context": "",
        })
        assert r.status_code == 200
        modified = r.json()["modified_response"]
        assert "priya@test.com" not in modified
        assert "REDACTED" in modified


class TestAuditFeedback:
    def test_feedback_stats_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "test.db")
            with patch("app.audit_log.DB_PATH", db):
                audit_log._initialized = False
                r = client.get("/audit-log/feedback-stats")
                assert r.status_code == 200
                data = r.json()
                assert data["total_reviewed"] == 0
                assert data["correct"] == 0


class TestPiiPrescan:
    def test_finds_email_and_phone(self):
        text = "Reach Priya at priya@test.com or +91 9876543210"
        hits, redacted = pii_prescan.scan(text)
        types = {h["type"] for h in hits}
        assert "EMAIL" in types
        assert "PHONE" in types
        assert "priya@test.com" not in redacted


class TestDecisionActions:
    def test_block_replaces_text(self):
        out = decision_actions.apply("block", "secret info", [], None)
        assert "secret info" not in out
        assert "human representative" in out.lower()


class TestSessionTracker:
    def test_momentum_builds_over_turns(self):
        conversation_tracker.reset("sess-a")
        conversation_tracker.update("sess-a", 0.3)
        conversation_tracker.update("sess-a", 0.5)
        m = conversation_tracker.get_momentum("sess-a")
        assert m > 0.3
        assert conversation_tracker.get_turn_count("sess-a") == 2

    def test_escalate_needs_two_turns(self):
        conversation_tracker.reset("sess-b")
        conversation_tracker.update("sess-b", 0.9)
        assert conversation_tracker.should_escalate("sess-b", 0.5) is False
        conversation_tracker.update("sess-b", 0.9)
        assert conversation_tracker.should_escalate("sess-b", 0.5) is True
