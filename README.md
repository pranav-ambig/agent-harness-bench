# Agent Harness Bench

A small benchmark comparing three ways of running the same tool-calling agent:
a hand-written loop on the Anthropic SDK, LangGraph, and Pydantic AI.

The agent, tools, system prompt and model (`claude-haiku-4-5`) are the same in
all three. Only the orchestration code changes, and every version runs against
the same 30 eval cases.

## The agent

An order-support agent that handles refund requests. It works off two JSON
fixtures (`data/orders.json`, `data/refund_policies.json`) and has four tools:

- `get_order_status(order_id)`
- `get_refund_policy(reason_code)`
- `issue_refund(order_id, amount)`
- `escalate_to_human(order_id, reason)`

The system prompt in `tools.py` tells it to check the refund policy before
issuing a refund, escalate fraud and manager-review cases, refuse refunds that
are outside the policy window, and ask for missing details instead of guessing.

## Harnesses

| Harness | File | |
|---|---|---|
| Raw loop | `harness_raw.py` | `while stop_reason == "tool_use"` loop on the `anthropic` SDK |
| LangGraph | `harness_langgraph.py` | `StateGraph` with an agent node and a tools node |
| Pydantic AI | `harness_pydantic_ai.py` | `Agent` with `@agent.tool_plain` tools |

The tool implementations live in `tools.py` and each harness wraps them in its
own tool format, so tool behaviour is identical across all three.

I originally wanted the OpenAI Agents SDK as the third harness, but running it
against Claude goes through LiteLLM, and the two currently pin incompatible
`openai` versions. Pydantic AI supports Anthropic natively, so I used that.

## Eval

`eval_cases.py` has 30 cases in four groups:

| Group | Cases | Expected behaviour |
|---|---|---|
| `happy_path` | 8 | Refund is within the policy window, so issue it |
| `policy_violation` | 8 | Refund is outside the window, so refuse it |
| `escalation` | 7 | Fraud, manager-review policy, or an odd order state, so escalate |
| `missing_info` | 7 | Order ID or reason is missing, so ask |

`grading.py` scores each run from the tool-call trace and the final reply. It's
rule-based, so scoring is free and repeatable. Metrics are task success rate,
wrong tool order (a refund issued before the policy was checked), p50/p95
latency, tokens and cost per task.

## Setup

Requires Python 3.10+.

```bash
pip install -r requirements.txt
cp .env.example .env   # then add your API key
```

To go through a gateway instead of `api.anthropic.com`, set
`ANTHROPIC_BASE_URL` (without a trailing `/v1`). If the gateway expects a
Bearer token rather than an API key, set `ANTHROPIC_AUTH_TOKEN` instead of
`ANTHROPIC_API_KEY`. `MODEL` overrides the model id.

## Running

```bash
python run_eval.py
```

This runs every case through every harness (90 runs, a few minutes) and writes
`results/raw_results.json` (full traces), `results/summary.json` and
`results/comparison.md`.

## Results

30 cases x 3 harnesses on `claude-haiku-4-5`, one run per case. Total cost $0.44.

| Harness | Task success | Wrong tool order | p50 latency | p95 latency | Tokens/task | Cost/task |
|---|---|---|---|---|---|---|
| raw_loop | 93% | 0% | 5390ms | 6649ms | 3785 | $0.00491 |
| langgraph | 93% | 0% | 5875ms | 7550ms | 3727 | $0.00487 |
| pydantic_ai | 90% | 0% | 5545ms | 9008ms | 3606 | $0.00471 |

| Harness | happy_path | policy_violation | escalation | missing_info |
|---|---|---|---|---|
| raw_loop | 100% | 100% | 86% | 86% |
| langgraph | 100% | 100% | 71% | 100% |
| pydantic_ai | 100% | 88% | 71% | 100% |

### Notes

- Accuracy is about the same across harnesses, which is what you'd expect with
  the same model and prompt. The bigger difference is latency: the raw loop had
  the lowest p95. None of the harnesses ever refunded without checking the
  policy first.
- Every harness failed `esc05` (a refund on a cancelled order) by issuing the
  refund. The system prompt never says a cancelled order should be escalated,
  so this is a gap in the eval case rather than in the harnesses.
- On `mi07` ("not sure what category that falls under") the raw loop issued a
  refund, while LangGraph and Pydantic AI asked a clarifying question first.
- LangGraph and Pydantic AI "failed" `esc06` because they asked about a real
  mismatch (the customer says the delivery was a month late, but the order data
  says otherwise) instead of escalating straight away. That's arguably the
  better response, but the grader only checks for the expected action.
- Each case was run once, so small differences between harnesses (one case is
  about 3 points of success rate) are within run-to-run noise.

## Layout

```
tools.py                  tool implementations, tool schemas, system prompt
data/                     order and refund policy fixtures
eval_cases.py             eval cases
grading.py                grader
harness_raw.py            raw SDK loop
harness_langgraph.py      LangGraph
harness_pydantic_ai.py    Pydantic AI
run_eval.py               runs everything and writes results/
```
