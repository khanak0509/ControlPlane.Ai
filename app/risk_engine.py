from app.config import SEVERITY_MAP


def compute_score(audit, pii_hits, anomaly, weights):
    reasons = []

    max_sev = 0.0
    for claim in audit.claims:
        if claim.contains_pii and audit.primary_risk_type in ("privacy", "overlap"):
            continue
        s = SEVERITY_MAP.get(claim.hallucination_risk, 0.0)
        if s > max_sev:
            max_sev = s

    if max_sev == 0.0 and audit.primary_risk_type == "overlap":
        for claim in audit.claims:
            s = SEVERITY_MAP.get(claim.hallucination_risk, 0.0)
            if s > max_sev:
                max_sev = s

    if max_sev > 0:
        reasons.append(f"hallucination severity {max_sev:.1f}")

    privacy_signal = 0.0
    if pii_hits:
        privacy_signal = 1.0
        types = list(set(h["type"] for h in pii_hits))
        reasons.append(f"PII prescan: {', '.join(types)}")
    if any(c.contains_pii for c in audit.claims):
        privacy_signal = 1.0
        if not pii_hits:
            reasons.append("LLM judge flagged PII in claims")

    bias_signal = 0.0
    if any(c.bias_flag for c in audit.claims):
        bias_signal = 1.0
        bias_reasons = [c.bias_reasoning for c in audit.claims if c.bias_flag and c.bias_reasoning]
        if bias_reasons:
            reasons.append(f"bias: {bias_reasons[0]}")
        else:
            reasons.append("bias detected in claims")

    if anomaly > 0.5:
        reasons.append(f"anomaly score {anomaly:.2f}")

    w = weights
    score = (
        w["hallucination"] * max_sev
        + w["privacy"] * privacy_signal
        + w["bias"] * bias_signal
        + w["anomaly"] * anomaly
    )
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
