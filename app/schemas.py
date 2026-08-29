from pydantic import BaseModel
from typing import Literal


class ClaimAssessment(BaseModel):
    claim_text: str
    is_grounded: bool
    grounding_confidence: float
    contains_pii: bool
    pii_entities: list[str] = []
    bias_flag: bool
    bias_reasoning: str | None = None
    hallucination_risk: Literal["none", "low", "medium", "high"]


class ResponseAudit(BaseModel):
    claims: list[ClaimAssessment]
    primary_risk_type: Literal[
        "none", "hallucination", "privacy", "bias", "overlap", "unverifiable"
    ]
    rationale: str


class Decision(BaseModel):
    action: Literal["allow", "edit", "flag", "block", "escalate"]
    final_score: float
    reasons: list[str]
    requires_human: bool
    jurisdiction: str = "default"
    regulatory_framework: str = "Standard Enterprise Policy"


class AgentAction(BaseModel):
    tool_name: str
    parameters: dict = {}
    reversible: bool
    estimated_impact: Literal["low", "medium", "high"]


class CheckRequest(BaseModel):
    use_case: str
    session_id: str
    query: str
    response: str
    source_context: str = ""
    conversation_history: list[dict] = []
    jurisdiction: str = "default"


class CheckResponse(BaseModel):
    decision: Decision
    audit: ResponseAudit
    component_scores: dict
    modified_response: str


class AgentActionRequest(BaseModel):
    action: AgentAction
    use_case: str
    session_id: str
    jurisdiction: str = "default"


class AgentGateResponse(BaseModel):
    allowed: bool
    action: Literal["allow", "flag", "escalate"]
    reason: str
    risk_factors: list[str] = []


class FeedbackRequest(BaseModel):
    log_id: int
    verdict: Literal["correct", "false_positive", "false_negative"]
    reviewer_note: str = ""
