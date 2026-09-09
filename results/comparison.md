# Agent Harness Bench Results

Model: `claude-haiku-4-5` for all harnesses. 30 cases across 4 buckets: happy_path, policy_violation, escalation, missing_info.

## Comparison

| Harness | Task Success | Wrong-Tool Rate | p50 Latency | p95 Latency | Avg Tokens/Task | Avg Cost/Task | Total Cost |
|---|---|---|---|---|---|---|---|
| raw_loop | 93% | 0% | 5390ms | 6649ms | 3785 | $0.00491 | $0.1473 |
| langgraph | 93% | 0% | 5875ms | 7550ms | 3727 | $0.00487 | $0.1462 |
| pydantic_ai | 90% | 0% | 5545ms | 9008ms | 3606 | $0.00471 | $0.1414 |

## Success rate by bucket

| Harness | happy_path | policy_violation | escalation | missing_info |
|---|---|---|---|---|
| raw_loop | 100% | 100% | 86% | 86% |
| langgraph | 100% | 100% | 71% | 100% |
| pydantic_ai | 100% | 88% | 71% | 100% |
