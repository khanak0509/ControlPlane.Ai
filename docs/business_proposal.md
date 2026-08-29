# ControlPlane.ai -- Business Proposal

## The Problem

Every enterprise deploying AI assistants today faces the same gap: the AI generates a response, and it either goes straight to the user with zero oversight, or it gets routed through a binary "safe/unsafe" filter that blocks too aggressively and misses nuanced risks. Neither approach works once you're dealing with customer-facing chatbots, internal HR copilots, or regulated lending workflows where the cost of a wrong answer isn't just a bad UX -- it's a compliance violation, a privacy breach, or a discrimination complaint.

The specific failure modes I keep seeing:
- **Hallucinated policy details** that agents present as fact (wrong refund timelines, fabricated leave entitlements, implied loan approvals)
- **PII leakage** across conversation boundaries (one customer's data surfacing in another's session)
- **Bias that's hard to catch** because it's not a slur -- it's an assumption about capability tied to age, region, or return-from-leave status
- **Multi-turn social engineering** where each individual turn looks clean but the session as a whole is an escalating data extraction

Current solutions either flag everything (unusable) or miss the subtle stuff (dangerous).

## What ControlPlane.ai Does Differently

I'm building a real-time oversight layer that sits between the AI and the end user. Instead of a binary pass/fail, it routes every response through a tiered decision: **allow / edit / flag / block / escalate**.

The key architectural insight: **the LLM judges risk, but never decides the action**. A deterministic risk engine (weighted score fusion) and a per-use-case policy engine (YAML-configurable thresholds) make the final call. This means:

1. The AI assessment can evolve without changing your compliance logic
2. Different use cases get different sensitivity levels (a customer support bot tolerates more than a loan advisor)
3. The decision is auditable, explainable, and reproducible -- not a black-box LLM opinion

### Three Differentiation Pillars

**1. Claim-level decomposition, not response-level classification.**
Most safety layers score the entire response as one blob. ControlPlane breaks responses into atomic claims and assesses each one independently across grounding, PII, and bias dimensions simultaneously. A single claim can trigger multiple flags -- we don't force single-category classification.

**2. Deterministic policy separation.**
The LLM never outputs "block" or "allow." It outputs a structured risk assessment (ResponseAudit). A separate, fully deterministic engine fuses the scores using configurable weights and maps them to actions using per-use-case YAML thresholds. You can tune sensitivity for each deployment without touching the model.

**3. Session-aware escalation.**
Individual turns that look clean can be part of a social engineering sequence. ControlPlane tracks an exponential moving average of risk scores per session. Even if the current turn scores low, accumulated session momentum can force an escalation -- catching the multi-turn patterns that per-turn classifiers miss.

## How It Works (Technical)

1. **PII Prescan** -- regex-based fast pass strips emails, phone numbers, Aadhaar, credit cards, PAN before anything hits the LLM. The LLM only sees redacted text.
2. **LLM Judge** -- gpt-4o-mini with structured output decomposes the (redacted) response into claims, assessing grounding confidence, PII presence, and bias for each.
3. **Anomaly Check** -- embedding similarity against a bank of "typical" responses catches responses that are structurally unusual even if individual claims pass.
4. **Risk Engine** -- deterministic weighted fusion: `score = w_h * max_severity + w_p * privacy_signal + w_b * bias_signal + w_a * anomaly`
5. **Policy Engine** -- loads per-use-case YAML, maps the fused score to allow/edit/flag/block/escalate using threshold bands.
6. **Session Tracker** -- EMA momentum per session forces escalation when cumulative risk exceeds a threshold, even if the current turn alone is clean.
7. **Audit Log** -- every decision is logged with full component scores, creating a complete compliance trail.

## Market and Revenue Model

**Target customers:** Any enterprise deploying AI assistants in regulated or customer-facing contexts -- financial services, healthcare, HR tech, e-commerce support.

**Revenue model:** Per-check pricing (think Stripe for AI safety). Tiered by volume:
- Starter: $0.005/check up to 10K/month
- Growth: $0.003/check up to 100K/month
- Enterprise: custom pricing with SLA, on-prem deployment option

**Why now:** Every major AI deployment is hitting the "we shipped it, now legal wants oversight" phase. The market needs a solution that's more nuanced than a content filter but simpler than building your own safety stack.

## Current Status

This is a working prototype demonstrating the full pipeline across three simulated use cases:
- **ShopSmart** -- e-commerce returns/refunds chatbot
- **PeopleDesk** -- internal HR leave policy assistant
- **CreditLens** -- regulated lending decision support

The prototype includes a 63-row evaluation set covering clean responses, PII leaks, hallucinations, bias, hallucination+PII overlaps, unverifiable claims, and multi-turn escalation sequences. Each use case has its own policy configuration with different sensitivity thresholds reflecting real-world risk profiles.

## What's Next

1. **Fine-tune the judge** on domain-specific eval data to improve claim-level accuracy
2. **Add streaming support** so the check runs in parallel with token generation
3. **Build integrations** for LangChain, LlamaIndex, and direct API middleware
4. **SOC 2 compliance** for the audit log and data handling
5. **Self-hosted option** for enterprises that can't send data to external APIs
