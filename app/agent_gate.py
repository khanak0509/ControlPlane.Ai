from app.schemas import AgentAction


DEMO_TOOLS = {
    "send_email": {
        "description": "Send an email to a customer",
        "reversible": False,
        "default_impact": "medium",
    },
    "issue_refund": {
        "description": "Issue a monetary refund to the customer's payment method",
        "reversible": False,
        "default_impact": "high",
    },
    "update_customer_record": {
        "description": "Update a field on the customer's account record",
        "reversible": True,
        "default_impact": "low",
    },
}


def gate(action: AgentAction):
    tool_info = DEMO_TOOLS.get(action.tool_name)

    reversible = action.reversible
    impact = action.estimated_impact

    if tool_info:
        reversible = tool_info["reversible"]

    if reversible and impact == "low":
        return True, "allow", f"{action.tool_name}: reversible + low impact"

    if not reversible or impact == "high":
        return False, "escalate", (
            f"{action.tool_name}: {'irreversible' if not reversible else 'high impact'} "
            f"-- requires human approval"
        )

    return False, "flag", f"{action.tool_name}: flagged for review (impact={impact})"
