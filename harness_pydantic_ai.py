"""Harness 3: Pydantic AI agent with typed tools."""
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider

from tools import make_tool_impls, make_async_anthropic_client, SYSTEM_PROMPT, MODEL


def _build_model() -> AnthropicModel:
    provider = AnthropicProvider(anthropic_client=make_async_anthropic_client())
    return AnthropicModel(MODEL, provider=provider)


def run(user_message: str) -> dict:
    trace = []
    refunds = {}
    impls = make_tool_impls(trace, refunds)

    agent = Agent(_build_model(), system_prompt=SYSTEM_PROMPT)

    @agent.tool_plain
    def get_order_status(order_id: str) -> dict:
        """Look up an order's item, amount, delivery status, and days since delivery by order ID."""
        return impls["get_order_status"](order_id)

    @agent.tool_plain
    def get_refund_policy(reason_code: str) -> dict:
        """Look up refund policy rules (eligibility window, auto-approval, manager requirement) for a reason code."""
        return impls["get_refund_policy"](reason_code)

    @agent.tool_plain
    def issue_refund(order_id: str, amount: float) -> dict:
        """Issue a refund for an order. Only call after confirming eligibility via get_refund_policy."""
        return impls["issue_refund"](order_id, amount)

    @agent.tool_plain
    def escalate_to_human(order_id: str, reason: str) -> dict:
        """Hand the case off to a human support agent."""
        return impls["escalate_to_human"](order_id, reason)

    result = agent.run_sync(user_message)
    u = result.usage

    return {
        "trace": trace,
        "final_text": result.output,
        "usage": {"input_tokens": u.input_tokens or 0, "output_tokens": u.output_tokens or 0},
    }
