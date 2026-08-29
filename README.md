# ControlPlane.ai

Checks AI responses for hallucination, privacy leaks, and bias — then routes them through allow / edit / flag / block / escalate instead of treating everything the same.

## How it works

```
AI Response
    |
    v
[PII Prescan] -- regex strip before LLM sees anything
    |
    v
[LLM Judge] -- claim-level risk assessment (ResponseAudit)
    |                     |
    v                     v
[Anomaly Check]    [Risk Engine] -- deterministic score fusion
                         |
                         v
                  [Policy Engine] -- per-use-case YAML thresholds
                         |
                         v
                  [Session Tracker] -- EMA momentum for multi-turn
                         |
                         v
                    Decision: allow / edit / flag / block / escalate
                         |
                         v
                    [Audit Log]
```

The LLM only assesses risk (grounding, PII, bias per claim). It never picks the final action — that's `risk_engine.py` + `policy_engine.py`.

## Use cases

| Use Case | Domain | PII Policy | Threshold Profile |
|---|---|---|---|
| ShopSmart | E-commerce returns/refunds | edit (redact) | Standard |
| PeopleDesk | Internal HR leave assistant | flag | Moderate |
| CreditLens | Regulated lending advisor | block | Strict |

## Setup

```bash
cd controlplane-ai
pip install -r requirements.txt

cp .env.example .env
# add your OpenAI key

uvicorn app.main:app --reload

# separate terminal
streamlit run dashboard/streamlit_app.py
```

## API

### POST /check

```bash
curl -X POST http://localhost:8000/check \
  -H "Content-Type: application/json" \
  -d '{
    "use_case": "shopsmart",
    "session_id": "test-1",
    "query": "Can I return my shoes?",
    "response": "Yes, within 30 days you get a full refund in 5-7 business days.",
    "source_context": "Standard return window is 30 days. Refunds in 5-7 business days."
  }'
```

### POST /agent-action

```bash
curl -X POST http://localhost:8000/agent-action \
  -H "Content-Type: application/json" \
  -d '{
    "action": {
      "tool_name": "issue_refund",
      "parameters": {"amount": 500, "order_id": "ORD-123"},
      "reversible": false,
      "estimated_impact": "high"
    },
    "use_case": "shopsmart",
    "session_id": "agent-1"
  }'
```

### POST /feedback
Reviewer feedback on a logged decision.

### GET /audit-log
Recent audit log entries.

### GET /audit-log/stats
Action counts.

## Eval

63-row eval set in `data/eval_set.jsonl` — clean responses, hard negatives, PII leaks, hallucinations, bias, unverifiable claims, multi-turn escalation.

```bash
python scripts/run_eval.py
```

Last run: **47.6%** overall accuracy.

| Category | Correct | Total | Accuracy |
|----------|---------|-------|----------|
| Clean / Grounded | 8 | 9 | 88.9% |
| Bias | 4 | 6 | 66.7% |
| Hallucination Only | 4 | 6 | 66.7% |
| Hallucination + PII Overlap | 3 | 6 | 50.0% |
| Hard Negative | 3 | 9 | 33.3% |
| Multi-turn Escalation | 4 | 12 | 33.3% |
| Unverifiable (No Source) | 2 | 6 | 33.3% |
| PII Leak | 2 | 9 | 22.2% |

Median latency ~3.3s.

## Tests

```bash
pytest tests/test_risk_engine.py -v
```

## Stack

Python 3.11+, FastAPI, LangChain (langchain-openai), gpt-4o-mini, text-embedding-3-small, Pydantic v2, sqlite3, PyYAML, Streamlit, pytest.

## Layout

```
controlplane-ai/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   ├── detectors/
│   │   ├── pii_prescan.py
│   │   ├── unified_judge.py
│   │   └── anomaly_check.py
│   ├── risk_engine.py
│   ├── policy_engine.py
│   ├── conversation_tracker.py
│   ├── decision_actions.py
│   ├── agent_gate.py
│   ├── audit_log.py
│   └── feedback.py
├── dashboard/
│   └── streamlit_app.py
├── data/
│   ├── policies/
│   ├── source_docs/
│   └── eval_set.jsonl
├── scripts/
│   ├── generate_eval_set.py
│   └── run_eval.py
├── tests/
│   └── test_risk_engine.py
└── docs/
    └── business_proposal.md
```
