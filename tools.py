"""Tool implementations, tool schemas and system prompt shared by all three harnesses.

Each harness wraps these functions in its own tool format (Anthropic tool
schema, LangChain @tool, Pydantic AI @agent.tool_plain).
"""
import json
import os
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

with open(DATA_DIR / "orders.json") as f:
    ORDERS = json.load(f)

with open(DATA_DIR / "refund_policies.json") as f:
    POLICIES = json.load(f)


SYSTEM_PROMPT = """You are a customer support agent for an online store. You have four tools:
get_order_status, get_refund_policy, issue_refund, and escalate_to_human.

Rules you must follow:
1. Never fabricate an order ID, dollar amount, or policy detail. Only use data returned by your tools.
2. Before issuing any refund, you MUST call get_refund_policy for the customer's stated reason to
   confirm eligibility. Never call issue_refund without having checked the policy first.
3. If the policy for that reason requires manager review, or the customer reports suspected fraud,
   escalate to a human with escalate_to_human instead of issuing the refund yourself.
4. If the order is outside the policy's refund window, or the order/reason isn't eligible, politely
   refuse the refund in your reply and explain why. Do not issue it and do not escalate a clear-cut
   ineligible case just to avoid saying no.
5. If the customer's message is missing information you need (e.g. no order ID, or no clear reason
   for the return), ask a clarifying question instead of guessing or proceeding with a tool call.
6. Only call issue_refund with the exact refundable amount from the order record you looked up.
7. After resolving the request (refund issued, refund refused, or escalated), reply to the customer
   concisely explaining the outcome.
"""


def make_tool_impls(trace: list, refunds: dict):
    """Return the four tool implementations, instrumented to log calls into `trace`.

    `trace` is a per-run list of {"tool", "args", "result"} records used for grading.
    `refunds` is a per-run dict (order_id -> amount) so cases don't share mutable state.
    """

    def get_order_status(order_id: str) -> dict:
        order = ORDERS.get(order_id)
        result = dict(order, order_id=order_id) if order else {"error": f"No order found with id {order_id}"}
        trace.append({"tool": "get_order_status", "args": {"order_id": order_id}, "result": result})
        return result

    def get_refund_policy(reason_code: str) -> dict:
        policy = POLICIES.get(reason_code)
        result = dict(policy, reason_code=reason_code) if policy else {
            "error": f"Unknown reason code '{reason_code}'. Valid codes: {', '.join(POLICIES.keys())}"
        }
        trace.append({"tool": "get_refund_policy", "args": {"reason_code": reason_code}, "result": result})
        return result

    def issue_refund(order_id: str, amount: float) -> dict:
        order = ORDERS.get(order_id)
        if not order:
            result = {"error": f"No order found with id {order_id}"}
        elif order_id in refunds:
            result = {"error": f"Order {order_id} has already been refunded"}
        else:
            refunds[order_id] = amount
            result = {"status": "refunded", "order_id": order_id, "amount": amount}
        trace.append({"tool": "issue_refund", "args": {"order_id": order_id, "amount": amount}, "result": result})
        return result

    def escalate_to_human(order_id: str, reason: str) -> dict:
        result = {"status": "escalated", "order_id": order_id, "reason": reason}
        trace.append({"tool": "escalate_to_human", "args": {"order_id": order_id, "reason": reason}, "result": result})
        return result

    return {
        "get_order_status": get_order_status,
        "get_refund_policy": get_refund_policy,
        "issue_refund": issue_refund,
        "escalate_to_human": escalate_to_human,
    }


# Anthropic-format tool schemas, used by the raw loop. LangGraph and Pydantic AI
# build theirs from function signatures and docstrings.
ANTHROPIC_TOOL_SCHEMAS = [
    {
        "name": "get_order_status",
        "description": "Look up an order's item, amount, delivery status, and days since delivery by order ID.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string", "description": "The order ID, e.g. ORD-1001"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "get_refund_policy",
        "description": "Look up the refund policy rules (eligibility window, auto-approval, manager requirement) for a reason code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason_code": {
                    "type": "string",
                    "description": "One of: defective, wrong_item, damaged_in_transit, not_as_described, changed_mind, duplicate_charge, late_delivery, fraud_suspected",
                }
            },
            "required": ["reason_code"],
        },
    },
    {
        "name": "issue_refund",
        "description": "Issue a refund for an order. Only call after confirming eligibility via get_refund_policy.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "The order ID to refund"},
                "amount": {"type": "number", "description": "The exact refund amount from the order record"},
            },
            "required": ["order_id", "amount"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": "Hand the case off to a human support agent, e.g. for manager-review policies or suspected fraud.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "The order ID in question"},
                "reason": {"type": "string", "description": "Why this needs human review"},
            },
            "required": ["order_id", "reason"],
        },
    },
]

MODEL = os.environ.get("MODEL", "claude-haiku-4-5")


def make_anthropic_client():
    # Picks up ANTHROPIC_API_KEY (or ANTHROPIC_AUTH_TOKEN) and ANTHROPIC_BASE_URL from the environment.
    import anthropic

    return anthropic.Anthropic()


def make_async_anthropic_client():
    import anthropic

    return anthropic.AsyncAnthropic()
