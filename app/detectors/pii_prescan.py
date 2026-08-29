import re

PATTERNS = {
    "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "PHONE": r"(?:\+?91[\s-]?)?(?:[6-9]\d{4}[\s-]?\d{5}|[6-9]\d{9})|(?:\+?1[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}|\b\d{3}[\s.-]\d{3}[\s.-]\d{4}\b",
    "AADHAAR": r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b",
    "PAN": r"\b[A-Z]{5}\d{4}[A-Z]\b",
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
    "CREDIT_CARD": r"\b(?:\d{4}[\s-]?){3}\d{4}\b|\b(?:4\d{3}|5[1-5]\d{2}|6011|3[47]\d{2})[\s-]?(?:\d{4}[\s-]?){2}\d{4}\b",
    "PASSPORT": r"\b[A-PR-WYa-pr-wy][1-9]\d\s?\d{4}[1-9]\b",
    "IP_ADDRESS": r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
    "API_KEY": r"\b(?:sk-[a-zA-Z0-9_-]{20,}|ghp_[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16}|bearer\s+[a-zA-Z0-9_\-\.]{25,})\b",
    "IBAN": r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]?){0,16}\b",
    "MEDICAL_RECORD": r"\b(?:MRN|MR#|REC|PATIENT_ID)[\s:-]?\d{6,10}\b",
}

_compiled = {k: re.compile(v, re.IGNORECASE if k == "API_KEY" else 0) for k, v in PATTERNS.items()}


def scan(text: str, user_query: str = ""):
    """
    Scans text for PII entities, returning list of detected hits and redacted text.
    If user_query is provided, hits that the user themselves provided in the query
    are tagged with self_disclosed=True so policy can distinguish conversational
    repetition from 3rd-party data exfiltration.
    """
    if not text:
        return [], ""

    hits = []
    redacted = text

    for pii_type, pattern in _compiled.items():
        for match in pattern.finditer(text):
            val = match.group().strip()
            if not val:
                continue
            if any(h["value"] == val for h in hits):
                continue

            # Check if this exact entity was in user query
            self_disclosed = bool(user_query and val in user_query)

            hits.append({
                "type": pii_type,
                "value": val,
                "start": match.start(),
                "end": match.end(),
                "self_disclosed": self_disclosed,
            })

    for hit in sorted(hits, key=lambda h: len(h["value"]), reverse=True):
        redacted = redacted.replace(hit["value"], f"[REDACTED:{hit['type']}]")

    return hits, redacted


def redact_custom(text: str, entities: list[str]) -> str:
    """Redacts arbitrary identified entity strings from text."""
    redacted = text
    for ent in sorted(entities, key=len, reverse=True):
        if ent and ent in redacted:
            redacted = redacted.replace(ent, "[REDACTED:ENTITY]")
    return redacted
