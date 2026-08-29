import json
from app.schemas import AgentAction
from app.detectors import pii_prescan

TOOL_CATALOG = {
    "send_email": {
        "description": "Send an email to a customer or external party",
        "reversible": False,
        "default_impact": "medium",
        "category": "communication",
        "requires_parameter_scan": True,
    },
    "issue_refund": {
        "description": "Issue a monetary refund to the customer's payment method",
        "reversible": False,
        "default_impact": "high",
        "category": "financial",
        "max_autonomous_amount": 50.0,
    },
    "transfer_funds": {
        "description": "Transfer funds between accounts",
        "reversible": False,
        "default_impact": "high",
        "category": "financial",
        "max_autonomous_amount": 0.0,
    },
    "update_customer_record": {
        "description": "Update a field on the customer's account record",
        "reversible": True,
        "default_impact": "low",
        "category": "data_mutation",
    },
    "query_user_profile": {
        "description": "Read-only lookup of customer profile",
        "reversible": True,
        "default_impact": "low",
        "category": "read_only",
    },
    "execute_system_command": {
        "description": "Execute shell or system command",
        "reversible": False,
        "default_impact": "high",
        "category": "system_admin",
    },
    "delete_database_records": {
        "description": "Permanently purge records from database",
        "reversible": False,
        "default_impact": "high",
        "category": "system_admin",
    },
}


def gate(action: AgentAction, use_case: str = "shopsmart", jurisdiction: str = "default"):
    """
    Evaluates autonomous agent tool-call execution safety.
    Checks blast radius, reversibility, tool domain, parameter payload for PII/secrets,
    and financial thresholds.
    """
    tool_info = TOOL_CATALOG.get(action.tool_name)
    risk_factors = []

    # 1. Parameter Inspection for PII / Secrets / Dangerous payload
    params_str = json.dumps(action.parameters or {})
    pii_hits, _ = pii_prescan.scan(params_str)
    if pii_hits:
        types = list(set(h["type"] for h in pii_hits))
        risk_factors.append(f"Sensitive entities in tool arguments: {', '.join(types)}")

    # 2. Reversibility & Base Impact
    reversible = action.reversible
    impact = action.estimated_impact

    if tool_info:
        reversible = tool_info["reversible"]
        category = tool_info.get("category", "general")
        
        # Financial checks
        if category == "financial":
            amount = 0.0
            for key in ["amount", "refund_amount", "sum", "value"]:
                if key in action.parameters:
                    try:
                        amount = float(action.parameters[key])
                    except (ValueError, TypeError):
                        pass
            max_auto = tool_info.get("max_autonomous_amount", 0.0)
            if amount > max_auto:
                risk_factors.append(f"Financial transaction value (${amount:.2f}) exceeds autonomous limit (${max_auto:.2f})")
    else:
        # Unknown tool
        risk_factors.append(f"Unregistered tool '{action.tool_name}' - untrusted blast radius")
        impact = "high"
        reversible = False

    # 3. Decision Determination
    if not reversible:
        risk_factors.append("Operation is irreversible (destructive or external side-effect)")

    if impact == "high" or not reversible or len(risk_factors) >= 2:
        reason = f"{action.tool_name}: Escalated for human supervisor approval. (" + "; ".join(risk_factors) + ")"
        return False, "escalate", reason

    if impact == "medium" or pii_hits:
        reason = f"{action.tool_name}: Flagged with execution telemetry. (" + "; ".join(risk_factors) + ")"
        return False, "flag", reason

    return True, "allow", f"{action.tool_name}: Approved for autonomous execution (reversible + low impact)"
