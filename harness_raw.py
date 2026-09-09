"""Harness 1: plain Anthropic SDK with a hand-written tool-use loop."""
import json

from tools import make_tool_impls, ANTHROPIC_TOOL_SCHEMAS, SYSTEM_PROMPT, MODEL

MAX_TURNS = 6


def run(user_message: str, client) -> dict:
    trace = []
    refunds = {}
    tools = make_tool_impls(trace, refunds)

    messages = [{"role": "user", "content": user_message}]
    usage = {"input_tokens": 0, "output_tokens": 0}

    for _ in range(MAX_TURNS):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=ANTHROPIC_TOOL_SCHEMAS,
            messages=messages,
        )
        usage["input_tokens"] += resp.usage.input_tokens
        usage["output_tokens"] += resp.usage.output_tokens
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            final_text = "".join(b.text for b in resp.content if b.type == "text")
            return {"trace": trace, "final_text": final_text, "usage": usage}

        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                fn = tools[block.name]
                result = fn(**block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })
        messages.append({"role": "user", "content": tool_results})

    return {"trace": trace, "final_text": "[max turns exceeded]", "usage": usage}
