from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from app.schemas import (
    CheckRequest, CheckResponse, AgentActionRequest,
    AgentGateResponse, FeedbackRequest,
)
from app.detectors import pii_prescan, unified_judge, anomaly_check
from app import risk_engine, policy_engine, conversation_tracker
from app import decision_actions, audit_log, feedback

app = FastAPI(
    title="ControlPlane.ai",
    description="AI response safety checks",
    version="0.1.0",
)


def _warm_session_from_history(session_id, use_case, history, source_context):
    if not history:
        return
    policy = policy_engine.load_policy(use_case)
    for turn in history:
        prev_hits, prev_redacted = pii_prescan.scan(turn.get("response", ""))
        try:
            prev_audit = unified_judge.judge(
                use_case=use_case,
                query=turn.get("query", ""),
                response=prev_redacted,
                source_context=source_context,
            )
            prev_score, _, _ = risk_engine.compute_score(
                prev_audit, prev_hits, 0.1, policy["weights"]
            )
            conversation_tracker.update(session_id, prev_score)
        except Exception:
            conversation_tracker.update(session_id, 0.1)


@app.post("/check", response_model=CheckResponse)
def check_response(req: CheckRequest):
    pii_hits, redacted_response = pii_prescan.scan(req.response)

    try:
        policy = policy_engine.load_policy(req.use_case)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if req.conversation_history:
        conversation_tracker.reset(req.session_id)
        _warm_session_from_history(
            req.session_id, req.use_case, req.conversation_history, req.source_context
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        audit_future = pool.submit(
            unified_judge.judge,
            use_case=req.use_case,
            query=req.query,
            response=redacted_response,
            source_context=req.source_context,
            conversation_history=req.conversation_history,
        )
        anomaly_future = pool.submit(
            anomaly_check.anomaly_score, redacted_response, req.use_case
        )
        audit = audit_future.result()
        anomaly = anomaly_future.result()

    score, components, reasons = risk_engine.compute_score(
        audit, pii_hits, anomaly, policy["weights"]
    )

    momentum = conversation_tracker.update(req.session_id, score)
    momentum_threshold = policy.get("momentum_escalate_above", 0.65)
    momentum_override = conversation_tracker.should_escalate(
        req.session_id, momentum_threshold
    )
    components["momentum"] = momentum

    decision = policy_engine.decide(score, reasons, policy, momentum_override, audit=audit)

    modified_response = decision_actions.apply(
        decision.action, req.response, pii_hits, audit
    )

    audit_log.log_decision(
        session_id=req.session_id,
        use_case=req.use_case,
        input_text=req.query,
        output_text=modified_response,
        components=components,
        action=decision.action,
        requires_human=decision.requires_human,
        reasons=decision.reasons,
    )

    return CheckResponse(
        decision=decision,
        audit=audit,
        component_scores=components,
        modified_response=modified_response,
    )


@app.post("/agent-action", response_model=AgentGateResponse)
def check_agent_action(req: AgentActionRequest):
    from app.agent_gate import gate

    allowed, gate_action, reason = gate(req.action)

    components = {
        "hallucination_severity": 0,
        "privacy_signal": 0,
        "bias_signal": 0,
        "anomaly_score": 0,
        "final_score": 0 if allowed else 0.8,
    }
    audit_log.log_decision(
        session_id=req.session_id,
        use_case=req.use_case,
        input_text=f"agent action: {req.action.tool_name}",
        output_text=reason,
        components=components,
        action=gate_action,
        requires_human=gate_action == "escalate",
        reasons=[reason],
    )

    return AgentGateResponse(allowed=allowed, action=gate_action, reason=reason)


@app.post("/feedback")
def submit_feedback(req: FeedbackRequest):
    ok = feedback.submit_feedback(req.log_id, req.verdict, req.reviewer_note)
    if not ok:
        raise HTTPException(status_code=404, detail="Log entry not found")
    return {"status": "recorded"}


@app.get("/audit-log")
def get_audit_log(limit: int = 50):
    return audit_log.get_recent(limit)


@app.get("/audit-log/stats")
def get_audit_stats():
    return audit_log.get_action_counts()


@app.get("/audit-log/feedback-stats")
def get_feedback_stats():
    return audit_log.get_feedback_counts()


@app.get("/health")
def health():
    return {"status": "ok"}
