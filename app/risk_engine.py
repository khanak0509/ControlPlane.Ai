from app.config import SEVERITY_MAP


def compute_score(audit, pii_hits, anomaly, weights):
    reasons = []

    max_sev = 0.0
    for claim in audit.claims:
        # If the overall risk is pure privacy, do not count the ungrounded PII as a separate hallucination
        is_pii_claim = claim.contains_pii or ("[REDACTED:" in claim.claim_text) or any(h["value"] in claim.claim_text for h in pii_hits)
        if is_pii_claim and audit.primary_risk_type == "privacy":
            continue
        s = SEVERITY_MAP.get(claim.hallucination_risk, 0.0)
        if s > max_sev:
            max_sev = s

    if max_sev == 0.0 and audit.primary_risk_type in ("overlap", "hallucination"):
        for claim in audit.claims:
            s = SEVERITY_MAP.get(claim.hallucination_risk, 0.0)
            if s > max_sev:
                max_sev = s

    if max_sev > 0:
        reasons.append(f"hallucination severity {max_sev:.1f}")

    privacy_signal = 0.0
    non_self_hits = [h for h in pii_hits if not h.get("self_disclosed")]
    if non_self_hits:
        privacy_signal = 1.0
        types = list(set(h["type"] for h in non_self_hits))
        reasons.append(f"PII prescan: {', '.join(types)}")
    elif any(c.contains_pii for c in audit.claims):
        privacy_signal = 1.0
        reasons.append("LLM judge flagged PII in claims")

    bias_signal = 0.0
    if any(c.bias_flag for c in audit.claims):
        bias_signal = 1.0
        bias_reasons = [c.bias_reasoning for c in audit.claims if c.bias_flag and c.bias_reasoning]
        if bias_reasons:
            reasons.append(f"bias: {bias_reasons[0]}")
        else:
            reasons.append("bias detected in claims")

    benign_conversation = (
        audit.primary_risk_type in ("none", "unverifiable")
        and max_sev <= 0.3
        and privacy_signal == 0.0
        and bias_signal == 0.0
    )
    if benign_conversation:
        anomaly = 0.0
    elif anomaly > 0.4:
        reasons.append(f"anomaly score {anomaly:.2f}")

    w = weights
    score = (
        w["hallucination"] * max_sev
        + w["privacy"] * privacy_signal
        + w["bias"] * bias_signal
        + w["anomaly"] * anomaly
    )
    if non_self_hits:
        score = max(score, 0.45)
    score = round(min(score, 1.0), 4)

    if not reasons:
        reasons.append("all checks passed")

    components = {
        "hallucination_severity": max_sev,
        "privacy_signal": privacy_signal,
        "bias_signal": bias_signal,
        "anomaly_score": anomaly,
        "final_score": score,
    }

    return score, components, reasons
