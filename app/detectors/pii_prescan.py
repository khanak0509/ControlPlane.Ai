import re

PATTERNS = {
    "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "PHONE": r"(?:\+91[\s-]?)?(?:\d[\s-]?){10}",
    "AADHAAR": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
    "CREDIT_CARD": r"\b(?:\d{4}[\s-]?){3}\d{4}\b",
    "IP_ADDRESS": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "PAN": r"\b[A-Z]{5}\d{4}[A-Z]\b",
}

_compiled = {k: re.compile(v) for k, v in PATTERNS.items()}


def scan(text):
    hits = []
    redacted = text

    for pii_type, pattern in _compiled.items():
        for match in pattern.finditer(text):
            val = match.group()
            if any(h["value"] == val for h in hits):
                continue
            hits.append({"type": pii_type, "value": val})

    for hit in sorted(hits, key=lambda h: len(h["value"]), reverse=True):
        redacted = redacted.replace(hit["value"], f"[REDACTED:{hit['type']}]")

    return hits, redacted
