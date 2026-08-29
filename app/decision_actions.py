from app.detectors import pii_prescan


def apply(action, response_text, pii_hits=None, audit=None):
    if action == "allow":
        return response_text

    if action in ("edit", "flag"):
        edited = response_text
        if pii_hits:
            for hit in sorted(pii_hits, key=lambda h: len(h["value"]), reverse=True):
                edited = edited.replace(hit["value"], f"[REDACTED:{hit['type']}]")

        if action == "edit" and audit and audit.primary_risk_type in ("unverifiable", "hallucination"):
            caveat = (
                "[Note: Some claims in this response could not be verified "
                "against available source material. Please verify independently.]\n\n"
            )
            edited = caveat + edited

        return edited

    if action == "block":
        return (
            "I'm unable to provide that information as it may contain "
            "inaccuracies or sensitive content. Please contact a human "
            "representative for assistance."
        )

    if action == "escalate":
        return (
            "This response has been held for human review and will be "
            "released once a reviewer has verified its contents."
        )

    return response_text
