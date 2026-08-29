import copy
import yaml
from app.config import POLICIES_DIR
from app.schemas import Decision

_policy_cache = {}

ACTION_ORDER = ["allow", "edit", "flag", "block", "escalate"]

REGULATORY_OVERLAYS = {
    "default": {
        "display_name": "Standard Enterprise Governance",
        "description": "Baseline organization policy with standard thresholds",
        "threshold_multiplier": 1.0,
    },
    "eu_ai_act": {
        "display_name": "EU AI Act & GDPR High-Risk Compliance",
        "description": "Strict zero-tolerance on PII exfiltration, lower tolerance on ungrounded claims, mandatory human review on high-risk output",
        "pii_floor": "block",
        "bias_floor": "escalate",
        "unverifiable_floor": "flag",
        "threshold_multiplier": 0.85,
        "human_review_delta": -0.15,
    },
    "us_hipaa_ftc": {
        "display_name": "US HIPAA & FTC Consumer Protection",
        "description": "Strict redaction of health & financial records, FTC anti-deception enforcement on unverifiable claims",
        "pii_floor": "edit",
        "bias_floor": "flag",
        "unverifiable_floor": "edit",
        "threshold_multiplier": 0.90,
        "human_review_delta": -0.10,
    },
    "in_dpdp_rbi": {
        "display_name": "India DPDP Act & RBI Fintech Governance",
        "description": "Digital Personal Data Protection compliance with financial decisioning oversight",
        "pii_floor": "edit",
        "bias_floor": "flag",
        "unverifiable_floor": "flag",
        "threshold_multiplier": 0.90,
        "human_review_delta": -0.10,
    },
}


def get_available_jurisdictions():
    """Returns metadata for all available regulatory jurisdiction overlays."""
    return [
        {
            "id": k,
            "display_name": v["display_name"],
            "description": v["description"],
        }
        for k, v in REGULATORY_OVERLAYS.items()
    ]


def load_policy(use_case: str, jurisdiction: str = "default"):
    """
    Loads base use_case policy from YAML and merges with the specified
    regulatory jurisdiction overlay.
    """
    cache_key = f"{use_case}:{jurisdiction}"
    if cache_key in _policy_cache:
        return _policy_cache[cache_key]

    path = POLICIES_DIR / f"{use_case}.yaml"
    if not path.exists():
        raise ValueError(f"No policy file for use case: {use_case}")

    with open(path) as f:
        base_policy = yaml.safe_load(f)

    policy = copy.deepcopy(base_policy)
    overlay = REGULATORY_OVERLAYS.get(jurisdiction, REGULATORY_OVERLAYS["default"])

    policy["jurisdiction"] = jurisdiction
    policy["regulatory_framework"] = overlay["display_name"]

    # Apply threshold multiplier if regulatory framework is more stringent
    mult = overlay.get("threshold_multiplier", 1.0)
    if mult != 1.0 and "thresholds" in policy:
        for k in policy["thresholds"]:
            policy["thresholds"][k] = round(policy["thresholds"][k] * mult, 4)

    # Apply regulatory floors if defined
    if "pii_floor" in overlay:
        policy["pii_action"] = _raise_floor(policy.get("pii_action", "edit"), overlay["pii_floor"])
    if "bias_floor" in overlay:
        policy["bias_action"] = _raise_floor(policy.get("bias_action", "flag"), overlay["bias_floor"])
    if "unverifiable_floor" in overlay:
        policy["unverifiable_action"] = _raise_floor(policy.get("unverifiable_action", "allow"), overlay["unverifiable_floor"])

    # Adjust human review threshold
    if "human_review_delta" in overlay:
        policy["human_review_above"] = max(0.20, policy.get("human_review_above", 0.60) + overlay["human_review_delta"])

    _policy_cache[cache_key] = policy
    return policy


def _raise_floor(current_action: str, floor_action: str) -> str:
    cur = ACTION_ORDER.index(current_action) if current_action in ACTION_ORDER else 0
    flr = ACTION_ORDER.index(floor_action) if floor_action in ACTION_ORDER else 0
    if flr > cur:
        return floor_action
    return current_action


def decide(score: float, reasons: list[str], policy: dict, momentum_override: bool = False, audit=None) -> Decision:
    t = policy["thresholds"]
    human_above = policy.get("human_review_above", 0.7)
    jurisdiction = policy.get("jurisdiction", "default")
    regulatory_framework = policy.get("regulatory_framework", "Standard Enterprise Policy")

    if momentum_override:
        return Decision(
            action="escalate",
            final_score=score,
            reasons=reasons + ["session momentum exceeded threshold"],
            requires_human=True,
            jurisdiction=jurisdiction,
            regulatory_framework=regulatory_framework,
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
    if audit and getattr(audit, "primary_risk_type", None) == "unverifiable":
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
        requires_human=score >= human_above or action in ("escalate", "block"),
        jurisdiction=jurisdiction,
        regulatory_framework=regulatory_framework,
    )
