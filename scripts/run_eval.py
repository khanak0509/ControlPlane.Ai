import json
import time
import sys
import argparse
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.detectors import pii_prescan, unified_judge, anomaly_check
from app import risk_engine, policy_engine, conversation_tracker


EVAL_PATH = Path(__file__).resolve().parent.parent / "data" / "eval_set.jsonl"

ACTION_ORDER = {"allow": 0, "edit": 1, "flag": 2, "block": 3, "escalate": 4}


def run_pipeline(row):
    conversation_tracker.reset(row["session_id"])

    if row.get("conversation_history"):
        for turn in row["conversation_history"]:
            prev_hits, prev_redacted = pii_prescan.scan(turn.get("response", ""))
            try:
                prev_audit = unified_judge.judge(
                    use_case=row["use_case"],
                    query=turn.get("query", ""),
                    response=prev_redacted,
                    source_context=row.get("source_context", ""),
                )
                policy = policy_engine.load_policy(row["use_case"])
                prev_score, _, _ = risk_engine.compute_score(
                    prev_audit, prev_hits, 0.05, policy["weights"]
                )
                prev_privacy = any(not h.get("self_disclosed") for h in prev_hits) or any(
                    c.contains_pii for c in prev_audit.claims
                )
                conversation_tracker.update(row["session_id"], prev_score, privacy_hit=prev_privacy)
            except Exception:
                conversation_tracker.update(row["session_id"], 0.1)

    t0 = time.time()

    pii_hits, redacted = pii_prescan.scan(row["response"])
    policy = policy_engine.load_policy(row["use_case"])

    audit = unified_judge.judge(
        use_case=row["use_case"],
        query=row["query"],
        response=redacted,
        source_context=row.get("source_context", ""),
        conversation_history=row.get("conversation_history"),
    )

    anomaly = anomaly_check.anomaly_score(redacted, row["use_case"])

    score, components, reasons = risk_engine.compute_score(
        audit, pii_hits, anomaly, policy["weights"]
    )

    privacy_hit = any(not h.get("self_disclosed") for h in pii_hits) or any(
        c.contains_pii for c in audit.claims
    )
    momentum = conversation_tracker.update(row["session_id"], score, privacy_hit=privacy_hit)
    momentum_threshold = policy.get("momentum_escalate_above", 0.65)
    momentum_override = conversation_tracker.should_escalate(
        row["session_id"], momentum_threshold
    )

    decision = policy_engine.decide(score, reasons, policy, momentum_override, audit=audit)

    latency = (time.time() - t0) * 1000
    return decision.action, latency


def evaluate_single(i, total, row):
    rid = row["id"]
    expected = row["expected_action"]
    try:
        predicted, latency = run_pipeline(row)
        is_correct = predicted == expected
        status = "->" if is_correct else f"wanted {expected}, got"
        print(f"  {i+1}/{total} {rid} {status} {predicted} ({latency:.0f}ms)", flush=True)
        return {
            "id": rid,
            "category": row["category"],
            "use_case": row["use_case"],
            "expected": expected,
            "predicted": predicted,
            "correct": is_correct,
            "latency_ms": latency,
        }
    except Exception as e:
        print(f"  {i+1}/{total} {rid} error: {e}", flush=True)
        return {"id": rid, "error": str(e), "correct": False, "latency_ms": 0}


def main():
    parser = argparse.ArgumentParser(description="Run ControlPlane Evaluation Benchmark")
    parser.add_argument("--workers", type=int, default=6, help="Parallel worker threads (default: 6)")
    args = parser.parse_args()

    rows = []
    with open(EVAL_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    print(f"Running {len(rows)} evaluation benchmark cases with {args.workers} workers...\n", flush=True)

    results = []
    t_start = time.time()

    if args.workers > 1:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_idx = {
                executor.submit(evaluate_single, i, len(rows), row): i
                for i, row in enumerate(rows)
            }
            for future in as_completed(future_to_idx):
                res = future.result()
                if "error" not in res:
                    results.append(res)
    else:
        for i, row in enumerate(rows):
            res = evaluate_single(i, len(rows), row)
            if "error" not in res:
                results.append(res)

    total_time = time.time() - t_start
    print(f"\nDone — {len(results)} evaluated in {total_time:.1f}s\n", flush=True)

    if not results:
        print("No results to score.", flush=True)
        return

    correct = sum(1 for r in results if r["correct"])
    print(f"Overall Accuracy: {correct}/{len(results)} ({100*correct/len(results):.1f}%)\n", flush=True)

    actions = sorted(set(r["expected"] for r in results) | set(r["predicted"] for r in results))
    print(f"{'Action':<12} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Support':>10}", flush=True)
    print("-" * 54, flush=True)

    for action in actions:
        tp = sum(1 for r in results if r["predicted"] == action and r["expected"] == action)
        fp = sum(1 for r in results if r["predicted"] == action and r["expected"] != action)
        fn = sum(1 for r in results if r["predicted"] != action and r["expected"] == action)
        support = tp + fn

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        print(f"{action:<12} {precision:>10.2f} {recall:>10.2f} {f1:>10.2f} {support:>10}", flush=True)

    print(flush=True)
    print(f"{'Category':<30} {'Correct':>8} {'Total':>8} {'Accuracy':>10}", flush=True)
    print("-" * 58, flush=True)
    cats = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in results:
        cats[r["category"]]["total"] += 1
        if r["correct"]:
            cats[r["category"]]["correct"] += 1

    for cat in sorted(cats):
        c = cats[cat]
        acc = 100 * c["correct"] / c["total"] if c["total"] > 0 else 0
        print(f"{cat:<30} {c['correct']:>8} {c['total']:>8} {acc:>9.1f}%", flush=True)

    latencies = [r["latency_ms"] for r in results if r.get("latency_ms")]
    if latencies:
        latencies.sort()
        median = latencies[len(latencies)//2]
        p95 = latencies[int(len(latencies)*0.95)]
        avg = sum(latencies)/len(latencies)
        print(f"\nLatency: median {median:.0f}ms | p95 {p95:.0f}ms | avg {avg:.0f}ms", flush=True)


if __name__ == "__main__":
    main()
