import yaml
from app.config import POLICIES_DIR
from app.schemas import Decision

_policy_cache = {}

ACTION_ORDER = ["allow", "edit", "flag", "block", "escalate"]


def load_policy(use_case):
    if use_case in _policy_cache:
        return _policy_cache[use_case]

    path = POLICIES_DIR / f"{use_case}.yaml"
    if not path.exists():
        raise ValueError(f"No policy file for use case: {use_case}")

    with open(path) as f:
        policy = yaml.safe_load(f)

    _policy_cache[use_case] = policy
    return policy


def _raise_floor(current_action, floor_action):
    cur = ACTION_ORDER.index(current_action)
    flr = ACTION_ORDER.index(floor_action)
    if flr > cur:
        return floor_action
    return current_action


def decide(score, reasons, policy, momentum_override=False, audit=None):
    t = policy["thresholds"]
    human_above = policy.get("human_review_above", 0.7)

    if momentum_override:
        return Decision(
            action="escalate",
            final_score=score,
            reasons=reasons + ["session momentum exceeded threshold"],
            requires_human=True,
        )

    if score >= t["block_below"]:
        action = "escalate"
    elif score >= t["flag_below"]:
        action = "block"
    elif score >= t["edit_below"]:
        action = "flag"
    elif score >= t["allow_below"]:
        action = "edit"
    else:
        action = "allow"

    has_pii = any("PII" in r or "pii" in r.lower() for r in reasons)
    has_bias = any("bias" in r.lower() for r in reasons)

    is_unverifiable = False
    if audit and audit.primary_risk_type == "unverifiable":
        is_unverifiable = True

    if has_pii:
        pii_floor = policy.get("pii_action", "flag")
        old = action
        action = _raise_floor(action, pii_floor)
        if action != old:
            reasons = reasons + [f"pii_action floor: {pii_floor}"]

    if has_bias:
        bias_floor = policy.get("bias_action", "flag")
        old = action
        action = _raise_floor(action, bias_floor)
        if action != old:
            reasons = reasons + [f"bias_action floor: {bias_floor}"]

    if is_unverifiable:
        unverif_floor = policy.get("unverifiable_action", "flag")
        old = action
        action = _raise_floor(action, unverif_floor)
        if action != old:
            reasons = reasons + [f"unverifiable_action floor: {unverif_floor}"]

    return Decision(
        action=action,
        final_score=score,
        reasons=reasons,
        requires_human=score >= human_above,
    )
