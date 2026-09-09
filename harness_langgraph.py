"""Harness 2: LangGraph. A state graph with an agent node and a tools node."""
import json
import os
from typing import Annotated, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from tools import make_tool_impls, SYSTEM_PROMPT, MODEL


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def _build_tools(trace: list, refunds: dict):
    impls = make_tool_impls(trace, refunds)

    @tool
    def get_order_status(order_id: str) -> dict:
        """Look up an order's item, amount, delivery status, and days since delivery by order ID."""
        return impls["get_order_status"](order_id)

    @tool
    def get_refund_policy(reason_code: str) -> dict:
        """Look up refund policy rules (eligibility window, auto-approval, manager requirement) for a reason code."""
        return impls["get_refund_policy"](reason_code)

    @tool
    def issue_refund(order_id: str, amount: float) -> dict:
        """Issue a refund for an order. Only call after confirming eligibility via get_refund_policy."""
        return impls["issue_refund"](order_id, amount)

    @tool
    def escalate_to_human(order_id: str, reason: str) -> dict:
        """Hand the case off to a human support agent."""
        return impls["escalate_to_human"](order_id, reason)

    return [get_order_status, get_refund_policy, issue_refund, escalate_to_human]


def _build_graph(trace: list, refunds: dict):
    tools_list = _build_tools(trace, refunds)
    tool_by_name = {t.name: t for t in tools_list}
    llm_kwargs = {}
    if os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        # ChatAnthropic has no auth_token option, so send the Bearer header directly.
        llm_kwargs = {
            "anthropic_api_key": "unused",
            "default_headers": {"Authorization": f"Bearer {os.environ['ANTHROPIC_AUTH_TOKEN']}"},
        }
    llm = ChatAnthropic(
        model=MODEL,
        max_tokens=1024,
        anthropic_api_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
        **llm_kwargs,
    ).bind_tools(tools_list)

    def agent_node(state: AgentState):
        return {"messages": [llm.invoke(state["messages"])]}

    def tool_node(state: AgentState):
        last = state["messages"][-1]
        outputs = []
        for call in last.tool_calls:
            result = tool_by_name[call["name"]].invoke(call["args"])
            outputs.append(ToolMessage(content=json.dumps(result), tool_call_id=call["id"]))
        return {"messages": outputs}

    def should_continue(state: AgentState):
        last = state["messages"][-1]
        return "tools" if getattr(last, "tool_calls", None) else END

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


def run(user_message: str) -> dict:
    trace = []
    refunds = {}
    app = _build_graph(trace, refunds)

    result = app.invoke(
        {"messages": [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_message)]},
        {"recursion_limit": 12},
    )

    final_text = result["messages"][-1].content
    usage = {"input_tokens": 0, "output_tokens": 0}
    for m in result["messages"]:
        meta = getattr(m, "usage_metadata", None)
        if meta:
            usage["input_tokens"] += meta.get("input_tokens", 0) or 0
            usage["output_tokens"] += meta.get("output_tokens", 0) or 0

    return {"trace": trace, "final_text": final_text, "usage": usage}
