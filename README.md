# ControlPlane.ai

**Real-time Oversight, Safety & Governance Layer for Enterprise AI**

ControlPlane.ai evaluates generative AI responses and autonomous agent actions in real time — detecting hallucinations, privacy/PII leaks, bias, and adversarial probing before they reach a user. Rather than a rigid binary pass/fail filter, it routes outcomes through a **5-tier action matrix** (`allow` / `edit` / `flag` / `block` / `escalate`) with domain-specific policy thresholds and regulatory jurisdiction overlays.

Built for **Round 2 (Prototype Development)** of the ControlPlane.ai track.

---

## The Enterprise Challenge

Enterprises deploy generative AI across diverse applications simultaneously:
- **Customer Support Bots** (high volume, fast latency budget, standard risk)
- **Internal HR & Workplace Copilots** (internal data, employee privacy, moderate risk)
- **Regulated Decision Support / Lending Advisors** (strict compliance, zero-tolerance for fabrication)

A one-size-fits-all filter either causes massive **alert fatigue** (over-flagging legitimate responses) or introduces **severe regulatory and legal liabilities** (under-flagging subtle hallucinations and privacy disclosures). Furthermore, multi-turn interactions and autonomous agent tool calls introduce compounding blast radius risks that single-turn stateless checkers completely miss.

---

## Architectural Blueprint

```
                     AI Response or Proposed Agent Action
                                      │
                                      ▼
    ┌───────────────────────────────────────────────────────────────────┐
    │                      DETECTION & SCAN STACK                       │
    │                                                                   │
    │  [PII Prescan & Secret Scan] ──► Multi-Regex + Entity Preservation │
    │            │                     (Raw PII never sent to judge)    │
    │            ▼                                                      │
    │  [Unified LLM Judge]        ──► Atomic Claim-Level Decomposition   │
    │            │                     (Grounding / PII / Bias / Overlap)│
    │            ▼                                                      │
    │  [Embedding Anomaly Check]  ──► Cosine distance to baseline        │
    └─────────────────────────────────┬─────────────────────────────────┘
                                      │
                                      ▼
    ┌───────────────────────────────────────────────────────────────────┐
    │                   DETERMINISTIC FUSION & STATE                    │
    │                                                                   │
    │  [Risk Engine]              ──► Weighted deterministic score fusion│
    │            │                                                      │
    │            ▼                                                      │
    │  [Session Tracker]          ──► EMA Multi-Turn Momentum Tracking  │
    │            │                     (Catches progressive exfiltration)│
    │            ▼                                                      │
    │  [Policy Engine]            ──► YAML Profiles + Regulatory Overlay │
    │                                  (EU AI Act / HIPAA / DPDP / RBI)  │
    └─────────────────────────────────┬─────────────────────────────────┘
                                      │
                                      ▼
                        5-Tier Guardrail Decision
          ┌─────────────┬─────────────┬─────────────┬─────────────┐
          │    ALLOW    │    EDIT     │    FLAG     │    BLOCK    │  ESCALATE
          │ (Pass-thru) │  (Redact/   │ (Log with   │ (Contextual │ (Human-in-
          │             │   Caveat)   │  telemetry) │  fallback)  │  the-loop)
          └─────────────┴─────────────┴─────────────┴─────────────┘
                                      │
                                      ▼
    ┌───────────────────────────────────────────────────────────────────┐
    │                AUDIT TRAIL, METRICS & ACTIVE FEEDBACK             │
    │                                                                   │
    │  • Tamper-evident SQLite Audit Log (Scores, Reasons, Payloads)     │
    │  • Human-in-the-loop review queue & verdict ingestion             │
    │  • Real-time Trustworthiness Metrics (Precision, Recall, F1)       │
    │  • Self-Calibrating Threshold Recommendation Engine               │
    └───────────────────────────────────────────────────────────────────┘
```

---

## Core Technical Innovations

| Innovation | Technical Implementation | Why It Matters |
|---|---|---|
| **Atomic Claim-Level Decomposition** | `unified_judge.py` breaks responses into individual factual clauses | Blob-level scoring misses mixed truth/error sentences; claim scoring enables precision auditing |
| **Decoupled Judge from Policy** | AI judges risk factors (`ResponseAudit`); deterministic Python code (`policy_engine.py`) picks the action | Fully auditable, reproducible, and re-tunable in real time without retraining LLMs |
| **5-Tier Remediation Matrix** | `ALLOW` / `EDIT` / `FLAG` / `BLOCK` / `ESCALATE` | `EDIT` redacts PII surgically without destroying UX; `FLAG` tracks borderline drift without user interruption |
| **Multi-Turn Session Momentum** | Exponential Moving Average (EMA) session state in `conversation_tracker.py` | Catches conversational social engineering and progressive multi-turn data exfiltration |
| **Agent Action Gate** | Pre-execution tool call interception (`/agent-action`) | Evaluates blast radius, reversibility, parameter PII leaks, and financial transaction thresholds |
| **Regulatory Jurisdiction Overlays** | Dynamic regulatory profiles (`EU AI Act & GDPR`, `US HIPAA & FTC`, `India DPDP & RBI`) | Automatically adapts policy thresholds and compliance floors across global markets |
| **Active Learning & Calibration** | `/feedback` & `/audit-log/metrics` | Translates human reviewer overrides into automated threshold calibration recommendations |

---

## Supported Use Cases & Policies

| Use Case | Domain | Latency Target | Risk Tolerance | PII Handling | Default Jurisdiction |
|---|---|---|---|---|---|
| **ShopSmart** | E-commerce Customer Support | < 1.5s | Standard | `EDIT` (Surgical Redaction) | Default / US FTC |
| **PeopleDesk** | Internal HR Policy Copilot | < 2.5s | Moderate | `FLAG` / `BLOCK` | Global / GDPR |
| **CreditLens** | Regulated Loan & Underwriting Advisor | Comprehensive | Zero Tolerance | `BLOCK` / `ESCALATE` | India RBI / US FTC |

---

## Quick Start

### 1. Environment Setup

```bash
# Clone and enter directory
cd ControlPlane.Ai

# Activate virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Add your OPENAI_API_KEY to .env
```

### 2. Run API Server & Governance Dashboard

**Terminal 1 (Backend API):**
```bash
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 (Streamlit Interactive Console):**
```bash
streamlit run dashboard/streamlit_app.py
```

Open **`http://localhost:8501`** in your browser.

---

## API Reference

### `POST /check`
Performs comprehensive real-time audit on generated AI responses.

```bash
curl -X POST http://localhost:8000/check \
  -H "Content-Type: application/json" \
  -d '{
    "use_case": "shopsmart",
    "session_id": "session-101",
    "query": "I bought shoes 20 days ago, can I return them?",
    "response": "Yes, you are within the 30-day window. Refunds take 5-7 business days.",
    "source_context": "Standard return window is 30 days. Refunds in 5-7 business days.",
    "jurisdiction": "default"
  }'
```

### `POST /agent-action`
Gates autonomous AI tool calls before execution.

```bash
curl -X POST http://localhost:8000/agent-action \
  -H "Content-Type: application/json" \
  -d '{
    "action": {
      "tool_name": "issue_refund",
      "parameters": {"amount": 350.00, "customer_id": "CUST-992"},
      "reversible": false,
      "estimated_impact": "high"
    },
    "use_case": "shopsmart",
    "session_id": "agent-session-42"
  }'
```

### `POST /feedback`
Submits human-in-the-loop review verdicts (`correct`, `false_positive`, `false_negative`).

### `GET /audit-log/export`
Exports immutable compliance records in CSV or JSON format (`?format=json` or `?format=csv`).

### `GET /audit-log/metrics`
Returns system precision, recall, F1 score, false positive/negative rates, and active calibration recommendations.

### `GET /jurisdictions`
Returns active regulatory frameworks (EU AI Act, HIPAA, DPDP/RBI).

---

## Testing & Quality Assurance

Run the automated test suite:

```bash
pytest tests/ -v
```

All 28 test cases covering score fusion, policy overrides, PII redaction, session momentum, agent gating, audit exports, and API endpoints pass 100%.

Run the parallel 63-scenario evaluation benchmark:

```bash
python scripts/run_eval.py --workers 8
```

---

## Project Structure

```
ControlPlane.Ai/
├── app/
│   ├── main.py                 # FastAPI application routes & lifecycle
│   ├── config.py               # Config, paths, and severity mappings
│   ├── schemas.py              # Pydantic schemas (ClaimAssessment, Decision, ResponseAudit)
│   ├── detectors/
│   │   ├── pii_prescan.py      # Multi-regex & secret prescan engine
│   │   ├── unified_judge.py    # Atomic claim-level LLM auditor with fallback
│   │   └── anomaly_check.py    # Embedding & semantic distance detector
│   ├── risk_engine.py          # Deterministic score fusion
│   ├── policy_engine.py        # YAML loader & regulatory jurisdiction overlays
│   ├── conversation_tracker.py # Session EMA momentum tracker
│   ├── decision_actions.py     # Remediation actions (redact, caveat, fallback)
│   ├── agent_gate.py           # Tool-call interceptor & blast radius auditor
│   ├── audit_log.py            # SQLite audit log & metrics engine
│   └── feedback.py             # Human-in-the-loop feedback handler
├── dashboard/
│   └── streamlit_app.py        # 6-tab Streamlit governance console
├── data/
│   ├── policies/               # YAML policy definitions (shopsmart, peopledesk, creditlens)
│   ├── source_docs/            # Ground truth policy documents
│   └── eval_set.jsonl          # 63-scenario evaluation benchmark
├── scripts/
│   ├── run_eval.py             # Benchmark runner & metrics calculator
│   └── panel_endpoint_test.py  # End-to-end endpoint verification
├── tests/
│   ├── test_api.py             # API route tests
│   └── test_risk_engine.py     # Deterministic risk engine tests
└── docs/
    └── business_proposal.md    # Commercial proposal & market analysis
```
