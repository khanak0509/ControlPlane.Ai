# ControlPlane.ai

Real-time oversight layer for enterprise AI — checks responses for hallucination, privacy leaks, and bias before they reach the user, then routes them through **allow / edit / flag / block / escalate** instead of a dumb pass/fail gate.

Built for **Round 2 (Prototype Development)** of the ControlPlane.ai problem track.

---

## The problem

Enterprises run AI across customer chatbots, internal HR copilots, and regulated decision tools — all at once, all with different risk tolerance. A single binary filter either blocks too much (alert fatigue) or misses the subtle stuff (compliance risk).

ControlPlane sits **between the AI and the user** as a pre-response gate. Same pipeline, different policy per use case.

---

## How it works

```
AI Response (from your chatbot / copilot)
    |
    v
[PII Prescan] ............ regex strip — raw PII never hits the LLM
    |
    v
[LLM Judge] .............. breaks response into claims, scores grounding / PII / bias per claim
    |                              |
    v                              v
[Anomaly Check]          [Risk Engine] ... weighted score fusion (deterministic)
    |                              |
    +--------------+---------------+
                   v
            [Policy Engine] ....... YAML thresholds → action (per use case)
                   |
                   v
            [Session Tracker] ..... EMA momentum across turns (multi-turn escalation)
                   |
                   v
         allow / edit / flag / block / escalate
                   |
                   v
            [Audit Log] ........... full trail for compliance
```

**Core design rule:** the LLM **assesses** risk (`ResponseAudit` — claim-level flags). It never outputs the final action. `risk_engine.py` fuses scores; `policy_engine.py` maps them to a decision using per-use-case YAML. Compliance logic stays separate from model behavior.

---

## Design decisions

| Decision | Why |
|---|---|
| Claim-level decomposition | One response can have a clean claim and a bad claim — blob scoring misses that |
| LLM assesses, code decides | Auditable, reproducible, tunable without retraining the judge |
| YAML policy per use case | ShopSmart tolerates more than CreditLens — same code, different thresholds |
| PII prescan before LLM | Never send raw phone/email/Aadhaar to OpenAI; redact first |
| 5-tier actions (not binary) | EDIT redacts PII instead of blocking the whole answer; FLAG logs without killing UX |
| Session EMA momentum | Individual turns can look fine; cumulative risk catches slow escalation |
| Agent action gate (separate) | AI agents *do* things, not just say them — irreversible actions get escalated |

---

## Assumptions (prototype scope)

- Enterprise uses foundation models via **API** — checker works at input/output layer, not inside the model
- ~3 simulated use cases running in parallel (customer support, internal HR, regulated lending)
- Ground truth arrives as optional `source_context` per request (simulates RAG / policy docs)
- Latency budget ~3–5s per check is acceptable for this prototype (not sub-100ms streaming)
- Scale target directionally: tens of thousands of checks/week — current sqlite + in-memory sessions are prototype-only
- No proprietary company data — eval set is hand-curated simulated scenarios

---

## Use cases

Three deployments, one pipeline, different policies:

| Use Case | Domain | Risk profile | PII handling | Example |
|---|---|---|---|---|
| **ShopSmart** | E-commerce returns | Standard | edit (redact) | "30-day return, refund in 5–7 days" |
| **PeopleDesk** | Internal HR leave | Moderate | flag | colleague PII in leave queries |
| **CreditLens** | Regulated lending | Strict | block | fabricated pre-approval below score min |

CreditLens thresholds are tighter — same hallucination score that gets **flagged** on ShopSmart can **block** on CreditLens. That's the point.

Policy files: `data/policies/*.yaml`

---

## Round 2 coverage

| Brief area | Status | Where in this repo |
|---|---|---|
| Multiple use cases, different risk tolerance | Done | 3 YAML policies + dashboard presets |
| Overlapping risks (hallucination + PII) | Done | `overlap` risk type, unified judge |
| No ground truth / unverifiable claims | Done | eval category + `unverifiable_action` in policy |
| Over-flag vs under-flag tradeoff | Done | 5-tier actions + tunable thresholds |
| Multi-turn compounding risk | Partial | EMA session tracker (eval: 33% on multi-turn) |
| Agent actions (not just text) | Done | `/agent-action` + agent gate tab |
| Detection: rules + embeddings + AI judge | Done | `pii_prescan`, `anomaly_check`, `unified_judge` |
| Governance + audit trail | Done | YAML policies + sqlite audit log |
| Feedback loop | Partial | `/feedback` endpoint — logs reviewer verdict, no auto-retrain yet |
| Metrics / eval | Done | 63-row eval set + `run_eval.py` |
| Regulatory / geography config | Not yet | would extend YAML with region rules |

---

## Quick start

```bash
cd controlplane-ai
pip install -r requirements.txt

cp .env.example .env
# put your OPENAI_API_KEY in .env

uvicorn app.main:app --reload

# second terminal
streamlit run dashboard/streamlit_app.py
```

Open `http://localhost:8501` — pick a preset scenario, hit **Run check**.

---

## API

### POST /check
Audit an AI response before it goes to the user.

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
Gate an agent's proposed tool call (refund, email, record update).

### POST /feedback
Reviewer marks a logged decision as correct / false positive / false negative.

### GET /audit-log · GET /audit-log/stats
Recent decisions and action distribution.

---

## Evaluation

63 hand-curated rows in `data/eval_set.jsonl` — clean responses, hard negatives, PII leaks, hallucinations, bias, overlap cases, unverifiable claims, multi-turn sequences.

```bash
python scripts/run_eval.py
```

**Last run: 47.6% overall action accuracy** — honest baseline for a prototype judge, not production-ready.

| Category | Accuracy | Notes |
|---|---|---|
| Clean / Grounded | 88.9% | pipeline mostly leaves good responses alone |
| Bias | 66.7% | reasonable for v1 |
| Hallucination Only | 66.7% | grounding works when source is provided |
| PII Leak | 22.2% | main gap — regex + judge miss subtle leaks |
| Hard Negative | 33.3% | over-flags suspicious-but-fine responses |
| Multi-turn Escalation | 33.3% | momentum logic needs tuning |

Median latency ~3.3s (gpt-4o-mini judge + embedding call).

**What we'd fix next:** tighter PII patterns, judge fine-tuning on eval data, parallel detector execution, policy threshold tuning per category.

---

## Tests

```bash
pytest tests/test_risk_engine.py -v
```

Unit tests for score fusion and policy threshold mapping — the deterministic core.

---

## Known limitations

- **Latency** — sequential pipeline, ~3s median; not built for streaming token-by-token yet
- **Accuracy** — 47.6% on eval; PII and hard-negative categories need work
- **Scale** — sqlite audit log, in-memory session store; would move to Postgres + Redis at volume
- **No batch mode** — real-time `/check` only in this prototype
- **Anomaly bank is hardcoded** — production would build from real traffic embeddings
- **Regulatory rules** — per-use-case YAML, not per-geography yet

---

## Stack

Python 3.11+ · FastAPI · LangChain (langchain-openai) · gpt-4o-mini (judge) · text-embedding-3-small (anomaly) · Pydantic v2 · sqlite3 · PyYAML · Streamlit · pytest

---

## Project layout

```
controlplane-ai/
├── app/
│   ├── main.py                 # /check and /agent-action endpoints
│   ├── config.py
│   ├── schemas.py              # ClaimAssessment, ResponseAudit, Decision
│   ├── detectors/
│   │   ├── pii_prescan.py      # regex PII before LLM
│   │   ├── unified_judge.py      # claim-level LLM judge
│   │   └── anomaly_check.py    # embedding similarity
│   ├── risk_engine.py          # deterministic score fusion
│   ├── policy_engine.py        # YAML → action
│   ├── conversation_tracker.py # session EMA
│   ├── decision_actions.py     # edit / block / escalate text
│   ├── agent_gate.py
│   ├── audit_log.py
│   └── feedback.py
├── dashboard/streamlit_app.py
├── data/
│   ├── policies/               # shopsmart, peopledesk, creditlens
│   ├── source_docs/
│   └── eval_set.jsonl
├── scripts/run_eval.py
├── tests/test_risk_engine.py
└── docs/business_proposal.md
```

More detail on market positioning and revenue model: `docs/business_proposal.md`
