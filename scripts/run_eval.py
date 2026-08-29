import json
import time
import sys
from pathlib import Path
from collections import defaultdict

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
                    prev_audit, prev_hits, 0.1, policy["weights"]
                )
                conversation_tracker.update(row["session_id"], prev_score)
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

    momentum = conversation_tracker.update(row["session_id"], score)
    momentum_threshold = policy.get("momentum_escalate_above", 0.65)
    momentum_override = conversation_tracker.should_escalate(
        row["session_id"], momentum_threshold
    )

    decision = policy_engine.decide(score, reasons, policy, momentum_override, audit=audit)

    latency = (time.time() - t0) * 1000
    return decision.action, latency


def main():
    rows = []
    with open(EVAL_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    print(f"running {len(rows)} eval cases\n")

    results = []
    latencies = []
    errors = []

    for i, row in enumerate(rows):
        rid = row["id"]
        expected = row["expected_action"]
        try:
            predicted, latency = run_pipeline(row)
            results.append({
                "id": rid,
                "category": row["category"],
                "use_case": row["use_case"],
                "expected": expected,
                "predicted": predicted,
                "correct": predicted == expected,
                "latency_ms": latency,
            })
            latencies.append(latency)
            if predicted == expected:
                print(f"  {i+1}/{len(rows)} {rid} -> {predicted} ({latency:.0f}ms)")
            else:
                print(f"  {i+1}/{len(rows)} {rid} wanted {expected}, got {predicted} ({latency:.0f}ms)")
        except Exception as e:
            errors.append({"id": rid, "error": str(e)})
            print(f"  {i+1}/{len(rows)} {rid} blew up: {e}")

    print()
    print(f"done — {len(results)} ran, {len(errors)} failed")
    print()

    if not results:
        print("nothing to score")
        return

    correct = sum(1 for r in results if r["correct"])
    print(f"accuracy: {correct}/{len(results)} ({100*correct/len(results):.1f}%)\n")

    actions = sorted(set(r["expected"] for r in results) | set(r["predicted"] for r in results))
    print(f"{'action':<12} {'precision':>10} {'recall':>10} {'f1':>10} {'support':>10}")
    print("-" * 54)

    for action in actions:
        tp = sum(1 for r in results if r["predicted"] == action and r["expected"] == action)
        fp = sum(1 for r in results if r["predicted"] == action and r["expected"] != action)
        fn = sum(1 for r in results if r["predicted"] != action and r["expected"] == action)
        support = tp + fn

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        print(f"{action:<12} {precision:>10.2f} {recall:>10.2f} {f1:>10.2f} {support:>10}")

    print()
    print(f"{'category':<30} {'correct':>8} {'total':>8} {'accuracy':>10}")
    print("-" * 58)
    cats = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in results:
        cats[r["category"]]["total"] += 1
        if r["correct"]:
            cats[r["category"]]["correct"] += 1

    for cat in sorted(cats):
        c = cats[cat]
        acc = 100 * c["correct"] / c["total"] if c["total"] > 0 else 0
        print(f"{cat:<30} {c['correct']:>8} {c['total']:>8} {acc:>9.1f}%")

    latencies.sort()
    median = latencies[len(latencies)//2]
    print()
    print(f"latency — median {median:.0f}ms, p95 {latencies[int(len(latencies)*0.95)]:.0f}ms, "
          f"avg {sum(latencies)/len(latencies):.0f}ms")


if __name__ == "__main__":
    main()
