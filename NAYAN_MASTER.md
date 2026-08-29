# ControlPlane.ai — Master Video Presentation Script (Nayan)

**Length:** ~7–8 minutes | **Recording Tool:** OBS Studio (Record Browser Fullscreen)  
**Target Audience:** Hackathon Judges & Technical Reviewers  

### Presenter Rules
- **`[ brackets ]`** = What to do on screen — **do NOT read aloud**.
- **Plain text** = What to say with confidence, energy, and clarity.
- Keep terminal windows and `.env` files hidden. Record browser at `http://localhost:8501`.

---

## Pre-Recording Checklist (Off Camera)

1. **Terminal 1:** `source .venv/bin/activate && uvicorn app.main:app --reload --port 8000`
2. **Terminal 2:** `source .venv/bin/activate && streamlit run dashboard/streamlit_app.py`
3. **Browser:** Open `http://localhost:8501` in fullscreen.

---

## Scene Timeline & Cheat Sheet

| Time | Tab | Action / Preset | Key Message |
|---|---|---|---|
| **0:00 – 1:00** | Check Response / Title | Intro & Architecture | 5-tier action matrix, claim-level checking, decoupled policy |
| **1:00 – 1:45** | Check Response | `ShopSmart: Clean return query` | ALLOW (green), zero false alarm, output untouched |
| **1:45 – 2:35** | Check Response | `ShopSmart: PII leak` | EDIT / Redact (orange), targeted PII strip without breaking UX |
| **2:35 – 3:15** | Check Response | `PeopleDesk: Colleague PII disclosure` | Same leak type → BLOCK/ESCALATE (red) via strict HR policy |
| **3:15 – 3:55** | Check Response | `ShopSmart: Wrong refund timeline` | Hallucination claim breakdown, ground truth verification |
| **3:55 – 4:45** | Check Response / Tab 2 | `ShopSmart: Multi-turn escalation (turn 4)` | Multi-turn EMA momentum, social engineering defense |
| **4:45 – 5:25** | Check Response | `CreditLens: Fabricated approval` | Regulated finance: pre-approval fabricated → safe fallback |
| **5:25 – 6:10** | Agent Action Gate | `issue_refund` vs `update_customer_record` | Autonomous tool gating, blast radius & reversibility |
| **6:10 – 6:50** | Policy / Audit / Metrics | Regulatory Overlays & Trustworthiness | EU AI Act, active feedback loop & self-calibrating thresholds |
| **6:50 – 7:30** | Closing | Summary & Vision | Enterprise-ready Responsible AI governance layer |

---

# SCENE-BY-SCENE SCRIPT

---

### SCENE 0 · INTRODUCTION & ARCHITECTURE — 0:00 to 1:00

**`[ WHAT TO DO ON SCREEN ]`**  
- Open browser at `http://localhost:8501`.
- Have the title **ControlPlane.ai** on screen with Tab 1 (`Check Response`) active.
- Hover mouse gently over the tab bar to show the breadth: Check Response, Multi-Turn Simulator, Agent Action Gate, Policy & Governance, Audit Log, Trustworthiness.

**`[ WHAT TO SAY ]`**  
"Hello everyone, this is ControlPlane.ai — our real-time oversight and governance layer for enterprise generative AI.

In the real world, an enterprise runs AI across dozens of different applications at once — customer support bots, internal HR copilots, and regulated financial advisors. A rigid, one-size-fits-all binary filter either causes massive alert fatigue by over-blocking normal conversations, or exposes the company to severe legal liability by missing subtle hallucinations and privacy leaks.

ControlPlane sits as an intelligent gateway between foundation model APIs and the end user. We evaluate every response across hallucination, privacy, and bias using atomic claim-level decomposition, and route decisions through a five-tier action matrix: Allow, Edit, Flag, Block, and Escalate.

Most importantly, our AI judge only assesses risk. A deterministic, auditable policy engine decides the action based on use case and regulatory jurisdiction. Let’s see it live."

---

### SCENE 1 · CLEAN GROUNDED RESPONSE — 1:00 to 1:45

**`[ WHAT TO DO ON SCREEN ]`**  
1. **`[ Tab: Check Response ]`**
2. **`[ Preset dropdown ]`** → select **`ShopSmart: Clean return query`**
3. **`[ Click 'Run check' button ]`**
4. When results load, point mouse to:
   - **Decision: ALLOW** (in green)
   - **Risk Score** (~0.02 – 0.05)
   - **What the user actually sees** (Left: Original | Right: After ControlPlane)
   - Caption: "unchanged — passed through as-is"

**`[ WHAT TO SAY ]`**  
"Let’s start with a normal customer interaction. A user asks about returning a jacket bought 20 days ago. The assistant's response perfectly matches the company's 30-day return policy.

ControlPlane verifies grounding against the source documentation. The decision is ALLOW, with a risk score near zero. 

Looking at 'What the user actually sees' on the right — the response passes through completely untouched. Good responses flow through with zero friction and zero false alarms."

---

### SCENE 2 · SURGICAL PII REDACTION (EDIT TIER) — 1:45 to 2:35

**`[ WHAT TO DO ON SCREEN ]`**  
1. **`[ Preset dropdown ]`** → select **`ShopSmart: PII leak`**
2. **`[ Click 'Run check' ]`**
3. Point mouse to:
   - **Decision: EDIT or FLAG** (orange)
   - **Component Scores: Privacy = 1.00**
   - **What the user actually sees:**
     - Left box: shows raw phone number `+91 98765 43210` and email `priya.sharma94@fakemail.com`
     - Right box: shows `[REDACTED:PHONE]` and `[REDACTED:EMAIL]`

**`[ WHAT TO SAY ]`**  
"Now, let’s see what happens when the chatbot accidentally leaks another customer's personal contact info while looking up an order.

ControlPlane’s pre-scan instantly detects the phone number and email address. But notice the action: instead of killing the entire response and frustrating the user, the decision is EDIT. 

Look at the before-and-after comparison. The personal data is surgically redacted with structured tokens, while the rest of the helpful response is preserved. This solves the over-blocking dilemma: the customer gets their answer, but privacy is strictly protected."

---

### SCENE 3 · CROSS-DOMAIN POLICY ENFORCEMENT — 2:35 to 3:15

**`[ WHAT TO DO ON SCREEN ]`**  
1. **`[ Preset dropdown ]`** → select **`PeopleDesk: Colleague PII disclosure`**
2. Note that **Use case** is now **`peopledesk`** (Internal HR Copilot).
3. **`[ Click 'Run check' ]`**
4. Point mouse to:
   - **Decision: BLOCK or ESCALATE** (red)
   - **Right box:** replaced with a safe fallback message.

**`[ WHAT TO SAY ]`**  
"Now, let’s test the exact same type of PII disclosure on a different use case: PeopleDesk, our internal HR copilot. An employee asks who is out on parental leave, and the bot discloses a colleague’s personal email and phone number.

Notice what happens: on PeopleDesk, the decision escalates to BLOCK. Because HR policy has a stricter compliance floor than customer support, the entire response is intercepted and replaced with a safe fallback. 

Same pipeline, zero code changes — just a domain-specific policy configuration."

---

### SCENE 4 · ATOMIC CLAIM-LEVEL HALLUCINATION CHECK — 3:15 to 3:55

**`[ WHAT TO DO ON SCREEN ]`**  
1. **`[ Preset dropdown ]`** → select **`ShopSmart: Wrong refund timeline (hallucination)`**
2. **`[ Click 'Run check' ]`**
3. Point to:
   - **Source Context:** says '5 to 7 business days'
   - **AI Response:** claims '3 to 5 business days'
   - **Decision: BLOCK**
   - **Claim-level breakdown:** click to expand **Claim 1** and show **Hallucination risk: medium/high**.

**`[ WHAT TO SAY ]`**  
"Here, the bot claims refunds take 3 to 5 days, but official company documentation mandates 5 to 7 days.

ControlPlane doesn't just do vague sentiment scoring. It performs atomic claim-level decomposition — breaking the response down into discrete factual claims and checking each one against ground truth.

The system isolates the exact contradictory claim, flags the hallucination severity, and blocks the incorrect timeline from misleading the customer."

---

### SCENE 5 · MULTI-TURN COMPOUNDING MOMENTUM — 3:55 to 4:45

**`[ WHAT TO DO ON SCREEN ]`**  
1. **`[ Preset dropdown ]`** → select **`ShopSmart: Multi-turn escalation (turn 4)`**
2. Point out: **Session ID = `multiturn-demo`** and caption showing prior turns.
3. **`[ Click 'Run check' ]`**
4. When loaded, highlight **Momentum score (> 0.2)** in Component Scores and **Decision: ESCALATE / BLOCK**.

**`[ WHAT TO SAY ]`**  
"In the real world, attackers don't always leak data in one turn. They use progressive conversational probing.

In this scenario, over turns one, two, and three, the user slowly extracted pieces of information. Turn four attempts the final exfiltration of the account holder's name and email.

Even if an individual turn looked borderline, our Session Tracker maintains an Exponential Moving Average of session momentum. As risk compounds across turns, session momentum breaches the threshold, automatically triggering an escalation. This stops multi-turn social engineering dead in its tracks."

---

### SCENE 6 · REGULATED DECISION SUPPORT (FINANCE) — 4:45 to 5:25

**`[ WHAT TO DO ON SCREEN ]`**  
1. **`[ Preset dropdown ]`** → select **`CreditLens: Fabricated approval`**
2. Note **Use case: creditlens** (Lending Workflow).
3. **`[ Click 'Run check' ]`**
4. Point to:
   - **Decision: ESCALATE or BLOCK** (red)
   - **Right box:** Shows message held for human underwriting review, completely suppressing the fake pre-approval promise.

**`[ WHAT TO SAY ]`**  
"Our third use case is CreditLens, a regulated loan decision support assistant.

The applicant has a 680 credit score, but the bot erroneously promises a pre-approved loan of 5 lakh rupees. In regulated financial services, a hallucinated financial commitment creates massive regulatory exposure.

Under the CreditLens policy, this is flagged as a critical violation and held for human review. The user never sees the unauthorized pre-approval."

---

### SCENE 7 · AUTONOMOUS AGENT ACTION GATE — 5:25 to 6:10

**`[ WHAT TO DO ON SCREEN ]`**  
1. **`[ Click Tab: Agent Action Gate ]`**
2. **Action 1 (High Risk):**
   - Tool: `issue_refund`
   - Estimated impact: `high`
   - Reversible: **Unchecked**
   - Click **`Check Tool Action`** → Point to **Gate: ESCALATE (red)**, `Allowed: False`.
3. **Action 2 (Low Risk):**
   - Tool: `update_customer_record`
   - Impact: `low`
   - Check **`Agent claims operation is reversible`**
   - Click **`Check Tool Action`** → Point to **Gate: ALLOW (green)**, `Allowed: True`.

**`[ WHAT TO SAY ]`**  
"Modern AI agents don't just generate text — they take autonomous actions: calling APIs, executing refunds, and modifying databases.

Our Agent Action Gate intercepts proposed tool calls before execution. 

Issuing a 500-dollar refund is irreversible with high financial blast radius. ControlPlane immediately escalates it, requiring human supervisor sign-off.

On the other hand, updating a customer's nickname is low impact and reversible. ControlPlane allows it to execute autonomously. We secure the action layer, not just the chat layer."

---

### SCENE 8 · GOVERNANCE, AUDIT & SELF-CALIBRATING FEEDBACK — 6:10 to 6:50

**`[ WHAT TO DO ON SCREEN ]`**  
1. **`[ Click Tab: Policy & Governance ]`** → Briefly show the active policies and regulatory overlays (EU AI Act, HIPAA, DPDP).
2. **`[ Click Tab: Audit Log ]`** → Scroll past the action distribution chart and recent entries table.
3. Show the **Submit Human-in-the-Loop Feedback** box (type an ID, select `correct`, click Submit).
4. **`[ Click Tab: Trustworthiness & Metrics ]`** → Show Precision, Recall, and the **Active Threshold Self-Calibration** recommendations.

**`[ WHAT TO SAY ]`**  
"Every single check and tool gate creates an immutable, tamper-evident audit record.

In our Policy Studio, teams can toggle regulatory overlays like the EU AI Act and India DPDP Act to instantly adjust compliance thresholds globally.

Human reviewers can audit decisions and submit feedback — marking verdicts as correct, false positive, or false negative. Our built-in Self-Calibration Engine analyzes reviewer feedback to continuously recommend optimal policy thresholds, systematically reducing alert fatigue while maintaining enterprise safety."

---

### SCENE 9 · CONCLUSION & WINNING IMPACT — 6:50 to 7:30

**`[ WHAT TO DO ON SCREEN ]`**  
- Return to **Check Response** tab or remain on **Trustworthiness & Metrics**.
- Speak directly and authoritatively.

**`[ WHAT TO SAY ]`**  
"To summarize, ControlPlane.ai delivers a complete, production-grade Responsible AI framework:
- Claim-level risk inspection,
- A five-tier remediation matrix,
- Domain and regulatory policy decoupling,
- Multi-turn session momentum tracking,
- Autonomous agent tool gating, and
- A continuous active-learning feedback loop.

We've validated this on a sixty-three scenario benchmark across customer support, internal HR, and regulated lending. ControlPlane gives enterprises the confidence to deploy generative AI safely, responsibly, and at scale.

Thank you."

**`[ STOP RECORDING ]`**
