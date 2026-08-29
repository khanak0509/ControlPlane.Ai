import numpy as np
from openai import OpenAI
from app.config import OPENAI_API_KEY, EMBEDDING_MODEL

client = None


def _get_client():
    global client
    if client is None and OPENAI_API_KEY:
        try:
            client = OpenAI(api_key=OPENAI_API_KEY)
        except Exception:
            client = None
    return client


TYPICAL_RESPONSES = {
    "shopsmart": [
        "You can return the item within 30 days of delivery for a full refund.",
        "Opened electronics are subject to a 10% restocking fee.",
        "Your refund will be issued within 5 to 7 business days after inspection.",
        "Gift cards and personalized items are final sale and cannot be returned.",
        "For defective items, you have up to 45 days to initiate a return.",
        "Exchanges for size or color are processed within 3 business days.",
        "Hi, I can check your order status. Could you provide your order number?",
        "That order is currently out for delivery and should arrive today.",
        "You can use any sturdy box or bag for your return shipment.",
        "Please confirm the email address associated with your order for verification.",
    ],
    "peopledesk": [
        "Full-time employees receive 18 days of annual leave per year.",
        "Sick leave absences under 3 days don't require a doctor's note.",
        "Please submit your leave request through the HR portal at least 5 business days in advance.",
        "Up to 5 unused annual leave days can be carried over to the next year.",
        "Maternity leave is 26 weeks and paternity leave is 2 weeks.",
        "Leave balances are visible only to you and your direct manager.",
        "You can file a complaint through the HR portal Employee Relations section.",
        "Our company policy strictly prohibits retaliation against anyone involved in an HR process.",
        "For absences of 3 or more consecutive days, please submit a medical certificate.",
        "Annual leave accrues on a monthly basis throughout the calendar year.",
    ],
    "creditlens": [
        "Interest rates range from 10.5% to 18% per annum based on your credit profile.",
        "Minimum eligibility requires a credit score of 700 and monthly income of Rs 25,000.",
        "The maximum loan amount is Rs 15 lakh or 10 times monthly income, whichever is lower.",
        "Processing typically takes 3 business days from complete document submission.",
        "Final approval is subject to underwriting review and cannot be confirmed by this assistant.",
        "Eligibility is based on income, credit score, age, and employment tenure only.",
        "You'll need income proof, identity proof, and address proof for personal loan application.",
        "Applicants with credit score below 700 may be referred to manual underwriting.",
        "Disbursal typically takes about 3 business days once documents are verified.",
    ],
}

_typical_embeddings = {}


def _embed(texts):
    c = _get_client()
    if not c:
        return None
    try:
        resp = c.embeddings.create(model=EMBEDDING_MODEL, input=texts)
        return [np.array(e.embedding) for e in resp.data]
    except Exception:
        return None


def _get_typical_embeddings(use_case):
    if use_case not in _typical_embeddings:
        texts = TYPICAL_RESPONSES.get(use_case, TYPICAL_RESPONSES["shopsmart"])
        embs = _embed(texts)
        if embs is not None:
            _typical_embeddings[use_case] = embs
    return _typical_embeddings.get(use_case)


def cosine_sim(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def _token_jaccard_similarity(a: str, b: str) -> float:
    set_a = set(a.lower().split())
    set_b = set(b.lower().split())
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def anomaly_score(response_text: str, use_case: str) -> float:
    """
    Computes anomaly score (0.0 = normal in-distribution response, 1.0 = highly anomalous).
    Uses embedding distance when available, falling back to lexical similarity.
    """
    if not response_text:
        return 0.0

    typical_texts = TYPICAL_RESPONSES.get(use_case, TYPICAL_RESPONSES["shopsmart"])

    try:
        typical_embs = _get_typical_embeddings(use_case)
        if typical_embs:
            resp_emb_list = _embed([response_text])
            if resp_emb_list:
                resp_emb = resp_emb_list[0]
                sims = [cosine_sim(resp_emb, t) for t in typical_embs]
                max_sim = max(sims)
                # Calibrate: responses with similarity >= 0.72 are normal in-distribution
                raw_distance = max(0.0, 1.0 - max_sim)
                calibrated = max(0.0, (raw_distance - 0.28) / 0.72)
                return round(min(1.0, calibrated), 4)
    except Exception:
        pass

    # Fallback to lexical token jaccard
    jaccard_sims = [_token_jaccard_similarity(response_text, t) for t in typical_texts]
    max_jaccard = max(jaccard_sims) if jaccard_sims else 0.5
    fallback_anomaly = max(0.0, 1.0 - (max_jaccard * 2.0))
    return round(min(0.9, fallback_anomaly), 4)
