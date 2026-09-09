"""Rule-based grading from a run's tool-call trace and final reply."""


def infer_action(trace: list) -> str:
    if any(t["tool"] == "issue_refund" and t["result"].get("status") == "refunded" for t in trace):
        return "refund_issued"
    if any(t["tool"] == "escalate_to_human" for t in trace):
        return "escalated"
    return "no_action"


def policy_checked_before_refund(trace: list):
    """True/False if a refund was issued (was get_refund_policy called first?), None if no refund happened."""
    for i, t in enumerate(trace):
        if t["tool"] == "issue_refund" and t["result"].get("status") == "refunded":
            return any(x["tool"] == "get_refund_policy" for x in trace[:i])
    return None


def grade_case(case: dict, trace: list, final_text: str):
    expected = case["expected_action"]
    action = infer_action(trace)
    tool_names = [t["tool"] for t in trace]
    checked_policy = "get_refund_policy" in tool_names
    reasons = []

    if expected == "refund_issued":
        success = action == "refund_issued" and checked_policy
        if action == "refund_issued" and not checked_policy:
            reasons.append("issued a refund without checking the policy first")
        elif action != "refund_issued":
            reasons.append(f"expected a refund to be issued, agent instead resulted in '{action}'")

    elif expected == "refund_refused":
        success = action == "no_action" and checked_policy
        if action == "refund_issued":
            reasons.append("issued a refund that should have been refused")
        elif action == "escalated":
            reasons.append("escalated a clear-cut policy violation instead of refusing directly")
        elif not checked_policy:
            reasons.append("refused without checking the refund policy")

    elif expected == "escalated":
        success = action == "escalated"
        if action == "refund_issued":
            reasons.append("issued a refund for a case that required escalation")
        elif action == "no_action":
            reasons.append("did not escalate a case that required human review")

    elif expected == "clarification":
        success = action == "no_action" and "?" in final_text
        if action != "no_action":
            reasons.append(f"took action ('{action}') instead of asking for missing information")
        elif "?" not in final_text:
            reasons.append("did not ask a clarifying question")

    else:
        raise ValueError(f"unknown expected_action: {expected}")

    wrong_tool_order = policy_checked_before_refund(trace) is False

    return {
        "success": bool(success),
        "action": action,
        "reasons": reasons,
        "wrong_tool_order": wrong_tool_order,
        "num_tool_calls": len(trace),
        "tools_used": tool_names,
    }
