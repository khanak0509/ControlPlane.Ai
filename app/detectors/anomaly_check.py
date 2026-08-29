import numpy as np
from openai import OpenAI
from app.config import OPENAI_API_KEY, EMBEDDING_MODEL

client = None

def _get_client():
    global client
    if client is None:
        client = OpenAI(api_key=OPENAI_API_KEY)
    return client

TYPICAL_RESPONSES = {
    "shopsmart": [
        "You can return the item within 30 days of delivery for a full refund.",
        "Opened electronics are subject to a 10% restocking fee.",
        "Your refund will be issued within 5 to 7 business days after inspection.",
        "Gift cards and personalized items are final sale and cannot be returned.",
        "For defective items, you have up to 45 days to initiate a return.",
        "Exchanges for size or color are processed within 3 business days.",
    ],
    "peopledesk": [
        "Full-time employees receive 18 days of annual leave per year.",
        "Sick leave absences under 3 days don't require a doctor's note.",
        "Please submit your leave request through the HR portal at least 5 business days in advance.",
        "Up to 5 unused annual leave days can be carried over to the next year.",
        "Maternity leave is 26 weeks and paternity leave is 2 weeks.",
        "Leave balances are visible only to you and your direct manager.",
    ],
    "creditlens": [
        "Interest rates range from 10.5% to 18% per annum based on your credit profile.",
        "Minimum eligibility requires a credit score of 700 and monthly income of Rs 25,000.",
        "The maximum loan amount is Rs 15 lakh or 10 times monthly income, whichever is lower.",
        "Processing typically takes 3 business days from complete document submission.",
        "Final approval is subject to underwriting review and cannot be confirmed by this assistant.",
        "Eligibility is based on income, credit score, age, and employment tenure only.",
    ],
}

_typical_embeddings = {}


def _embed(texts):
    c = _get_client()
    resp = c.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [np.array(e.embedding) for e in resp.data]


def _get_typical_embeddings(use_case):
    if use_case not in _typical_embeddings:
        texts = TYPICAL_RESPONSES.get(use_case, TYPICAL_RESPONSES["shopsmart"])
        _typical_embeddings[use_case] = _embed(texts)
    return _typical_embeddings[use_case]


def cosine_sim(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def anomaly_score(response_text, use_case):
    resp_emb = _embed([response_text])[0]
    typical = _get_typical_embeddings(use_case)

    sims = [cosine_sim(resp_emb, t) for t in typical]
    max_sim = max(sims)

    score = 1.0 - max_sim
    return round(max(0.0, min(1.0, score)), 4)
