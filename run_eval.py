"""Runs every eval case through every harness, grades the runs and writes
a comparison of success rate, tool order, latency and cost to results/.
"""
import json
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv(override=True)

from eval_cases import CASES, BUCKETS
from grading import grade_case
from tools import make_anthropic_client, MODEL
import harness_raw
import harness_langgraph
import harness_pydantic_ai

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# claude-haiku-4-5 list pricing, $ per million tokens (input, output)
PRICE_PER_MTOK = {"input": 1.00, "output": 5.00}


def cost_for(usage: dict) -> float:
    return (usage["input_tokens"] / 1_000_000) * PRICE_PER_MTOK["input"] + \
           (usage["output_tokens"] / 1_000_000) * PRICE_PER_MTOK["output"]


def run_one(harness_name: str, case: dict, client) -> dict:
    start = time.perf_counter()
    error = None
    try:
        if harness_name == "raw_loop":
            out = harness_raw.run(case["user_message"], client)
        elif harness_name == "langgraph":
            out = harness_langgraph.run(case["user_message"])
        elif harness_name == "pydantic_ai":
            out = harness_pydantic_ai.run(case["user_message"])
        else:
            raise ValueError(harness_name)
    except Exception as e:  # noqa: BLE001 - one bad case must not kill the run
        error = f"{type(e).__name__}: {e}"
        out = {"trace": [], "final_text": "", "usage": {"input_tokens": 0, "output_tokens": 0}}
    latency_ms = (time.perf_counter() - start) * 1000

    grade = None
    if error is None:
        grade = grade_case(case, out["trace"], out["final_text"])

    return {
        "case_id": case["id"],
        "bucket": case["bucket"],
        "harness": harness_name,
        "error": error,
        "latency_ms": latency_ms,
        "usage": out["usage"],
        "cost_usd": cost_for(out["usage"]),
        "final_text": out["final_text"],
        "trace": out["trace"],
        "grade": grade,
    }


def summarize(records: list) -> dict:
    n = len(records)
    successes = sum(1 for r in records if r["grade"] and r["grade"]["success"])
    errors = sum(1 for r in records if r["error"] is not None)
    wrong_tool = sum(1 for r in records if r["grade"] and r["grade"]["wrong_tool_order"])
    latencies = sorted(r["latency_ms"] for r in records)
    total_tokens = sum(r["usage"]["input_tokens"] + r["usage"]["output_tokens"] for r in records)
    total_cost = sum(r["cost_usd"] for r in records)

    def pctl(data, p):
        if not data:
            return 0.0
        k = (len(data) - 1) * p
        f, c = int(k), min(int(k) + 1, len(data) - 1)
        return data[f] if f == c else data[f] + (data[c] - data[f]) * (k - f)

    per_bucket = {}
    for bucket in BUCKETS:
        bucket_records = [r for r in records if r["bucket"] == bucket]
        bucket_success = sum(1 for r in bucket_records if r["grade"] and r["grade"]["success"])
        per_bucket[bucket] = {
            "n": len(bucket_records),
            "success_rate": bucket_success / len(bucket_records) if bucket_records else 0.0,
        }

    return {
        "n_cases": n,
        "task_success_rate": successes / n if n else 0.0,
        "error_rate": errors / n if n else 0.0,
        "wrong_tool_rate": wrong_tool / n if n else 0.0,
        "latency_p50_ms": pctl(latencies, 0.50),
        "latency_p95_ms": pctl(latencies, 0.95),
        "latency_mean_ms": statistics.mean(latencies) if latencies else 0.0,
        "total_tokens": total_tokens,
        "avg_tokens_per_task": total_tokens / n if n else 0.0,
        "total_cost_usd": total_cost,
        "avg_cost_per_task_usd": total_cost / n if n else 0.0,
        "per_bucket": per_bucket,
    }


def render_markdown(summaries: dict) -> str:
    lines = [
        "# Agent Harness Bench Results",
        "",
        f"Model: `{MODEL}` for all harnesses. {len(CASES)} cases across {len(BUCKETS)} buckets: "
        f"{', '.join(BUCKETS)}.",
        "",
        "## Comparison",
        "",
        "| Harness | Task Success | Wrong-Tool Rate | p50 Latency | p95 Latency | Avg Tokens/Task | Avg Cost/Task | Total Cost |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, s in summaries.items():
        lines.append(
            f"| {name} | {s['task_success_rate']:.0%} | {s['wrong_tool_rate']:.0%} | "
            f"{s['latency_p50_ms']:.0f}ms | {s['latency_p95_ms']:.0f}ms | "
            f"{s['avg_tokens_per_task']:.0f} | ${s['avg_cost_per_task_usd']:.5f} | ${s['total_cost_usd']:.4f} |"
        )

    lines += ["", "## Success rate by bucket", "", "| Harness | " + " | ".join(BUCKETS) + " |",
              "|---|" + "---|" * len(BUCKETS)]
    for name, s in summaries.items():
        row = [f"{s['per_bucket'][b]['success_rate']:.0%}" for b in BUCKETS]
        lines.append(f"| {name} | " + " | ".join(row) + " |")

    return "\n".join(lines) + "\n"


def main():
    client = make_anthropic_client()
    harnesses = ["raw_loop", "langgraph", "pydantic_ai"]

    all_records = []
    summaries = {}

    for harness_name in harnesses:
        print(f"\n=== {harness_name} ===")
        records = []
        for i, case in enumerate(CASES, 1):
            rec = run_one(harness_name, case, client)
            records.append(rec)
            all_records.append(rec)
            status = "OK " if (rec["grade"] and rec["grade"]["success"]) else "FAIL"
            err = f" ERROR={rec['error']}" if rec["error"] else ""
            print(f"  [{i:2d}/{len(CASES)}] {case['id']:6s} ({case['bucket']:16s}) {status} "
                  f"{rec['latency_ms']:6.0f}ms{err}")
        summaries[harness_name] = summarize(records)

    (RESULTS_DIR / "raw_results.json").write_text(json.dumps(all_records, indent=2), encoding="utf-8")
    (RESULTS_DIR / "summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    report = render_markdown(summaries)
    (RESULTS_DIR / "comparison.md").write_text(report, encoding="utf-8")

    print("\n" + report)
    print(f"Wrote results/raw_results.json, results/summary.json, results/comparison.md")


if __name__ == "__main__":
    main()
