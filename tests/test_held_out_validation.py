"""
AATIF Held-Out Validation Test
===============================

THIS IS HELD-OUT VALIDATION — these 56 cases were NOT used in θ=0.40
calibration (which used 54 separate cases in temperature_ab_test.py).

Purpose: report a generalizable F1 score for the gated S equation
    S = σ(w₁·I + w₂·E) · [1 − σ(α(H − θ))]
with θ=0.40, α=10, w₁=2.0, w₂=1.5 (default profile).

The test loads held_out_test_set.json (56 cases, 28 Arabic / 28 English,
30 SAFE / 26 BLOCKED) and runs each through the full AATIFEngine with
bge-m3 embeddings via Ollama.

Decision mapping:
    EXECUTE  → predicted SAFE
    CLARIFY  → predicted SAFE
    SAFE_STOP  → predicted BLOCKED
    SAFE_FREEZE → predicted BLOCKED
    hard_override (H > 0.7) → predicted BLOCKED

Requires:
    - Ollama running locally (port 11434)
    - bge-m3 model pulled (ollama pull bge-m3)

If Ollama is not available, tests skip gracefully with a message.

Architect: Abdulmjeed Ibrahim Khenkar
"""

import json
import os
import sys
import time
from collections import defaultdict

import pytest

# ── path setup ──────────────────────────────────────────────────────
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_THIS_DIR)
_ENGINE_DIR = os.path.join(_ROOT_DIR, "engine")
_BENCHMARK_DIR = os.path.join(_ROOT_DIR, "benchmarks")

if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

HELD_OUT_PATH = os.path.join(_BENCHMARK_DIR, "held_out_test_set.json")


# ── helpers ─────────────────────────────────────────────────────────

def _check_ollama():
    """Return True if Ollama is reachable on localhost:11434."""
    import urllib.request
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags",
                                     method="GET")
        with urllib.request.urlopen(req, timeout=5):
            return True
    except Exception:
        return False


def _decision_to_label(decision: str, hard_override: bool = False) -> str:
    """Map engine decision → SAFE / BLOCKED."""
    if hard_override:
        return "BLOCKED"
    if decision in ("EXECUTE", "CLARIFY"):
        return "SAFE"
    return "BLOCKED"  # SAFE_STOP, SAFE_FREEZE


def _compute_metrics(y_true: list, y_pred: list,
                     positive_label: str = "BLOCKED") -> dict:
    """
    Compute accuracy, precision, recall, F1, and confusion matrix.

    Positive class = BLOCKED (what we want to detect).
    """
    tp = fp = fn = tn = 0
    for t, p in zip(y_true, y_pred):
        if t == positive_label and p == positive_label:
            tp += 1
        elif t != positive_label and p == positive_label:
            fp += 1
        elif t == positive_label and p != positive_label:
            fn += 1
        else:
            tn += 1

    total = tp + fp + fn + tn
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) else 0.0)

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "total": total,
    }


# ── load held-out data ──────────────────────────────────────────────

def load_held_out():
    """Load and validate held_out_test_set.json."""
    with open(HELD_OUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "cases" in data, "Missing 'cases' key in held-out JSON"
    assert "metadata" in data, "Missing 'metadata' key in held-out JSON"
    assert len(data["cases"]) == data["metadata"]["size"], (
        f"Metadata says {data['metadata']['size']} cases but found "
        f"{len(data['cases'])}"
    )
    return data


# ── pytest fixtures ─────────────────────────────────────────────────

@pytest.fixture(scope="module")
def held_out_data():
    return load_held_out()


@pytest.fixture(scope="module")
def engine():
    """Initialize AATIFEngine; skip the entire module if Ollama is down."""
    if not _check_ollama():
        pytest.skip(
            "Ollama not available on localhost:11434. "
            "Start Ollama and pull bge-m3 to run held-out validation:\n"
            "  ollama serve\n"
            "  ollama pull bge-m3\n"
            "Then re-run:  pytest tests/test_held_out_validation.py -v"
        )
    try:
        from aatif_s_equation import AATIFEngine
        eng = AATIFEngine()
        return eng
    except Exception as e:
        pytest.skip(f"Cannot initialize AATIFEngine: {e}")


# ── individual case test (parametrised) ─────────────────────────────

def _case_ids():
    """Generate test IDs for parametrize without loading engine."""
    try:
        data = load_held_out()
        return [c["id"] for c in data["cases"]]
    except Exception:
        return []


def _case_params():
    try:
        data = load_held_out()
        return data["cases"]
    except Exception:
        return []


@pytest.mark.parametrize("case", _case_params(), ids=_case_ids())
def test_held_out_case(case, engine):
    """Test a single held-out case against the gated S equation."""
    result = engine.compute(
        case["text"],
        profile="default",
        equation_mode="gated",
        verbose=True,
    )

    predicted = _decision_to_label(
        result["decision"],
        result.get("hard_override", False),
    )
    expected = case["expected"]

    # Always print diagnostic info
    status = "✓" if predicted == expected else "✗"
    print(f"\n  {status} {case['id']} [{case['category']}] "
          f"H={result['H']:.3f} I={result['I']:.3f} E={result['E']:.3f} "
          f"S={result['S']:.3f} → {result['decision']} "
          f"(predicted={predicted}, expected={expected})")

    if predicted != expected:
        print(f"    Text: {case['text'][:80]}...")
        print(f"    Reasoning: {case['reasoning']}")
        if result.get("hard_override"):
            print(f"    Hard override: H={result['H']:.3f} > 0.7")

    assert predicted == expected, (
        f"{case['id']} ({case['category']}): "
        f"predicted {predicted} but expected {expected}. "
        f"H={result['H']:.3f}, I={result['I']:.3f}, E={result['E']:.3f}, "
        f"S={result['S']:.3f}, decision={result['decision']}"
    )


# ── aggregate report test ──────────────────────────────────────────

def test_held_out_aggregate_report(held_out_data, engine):
    """
    Run ALL held-out cases and produce aggregate metrics.

    THIS IS THE KEY TEST — it reports the generalizable F1 score.
    """
    cases = held_out_data["cases"]
    meta = held_out_data["metadata"]

    y_true = []
    y_pred = []
    results_log = []
    errors_by_category = defaultdict(list)
    category_counts = defaultdict(lambda: {"correct": 0, "total": 0})

    print("\n" + "=" * 78)
    print("  AATIF HELD-OUT VALIDATION REPORT")
    print("  " + "─" * 74)
    print(f"  Dataset:    {HELD_OUT_PATH}")
    print(f"  Cases:      {meta['size']}  "
          f"(AR={meta['language_split']['ar']}, "
          f"EN={meta['language_split']['en']})")
    print(f"  Labels:     SAFE={meta['label_split']['safe']}, "
          f"BLOCKED={meta['label_split']['blocked']}")
    print(f"  Equation:   S = σ(w₁·I + w₂·E) × [1 − σ(α(H − θ))]")
    print(f"  Profile:    default (θ=0.40, α=10, w₁=2.0, w₂=1.5)")
    print(f"  Embeddings: bge-m3 via Ollama")
    print(f"  NOTE:       These cases were NOT used in θ calibration")
    print("=" * 78)

    start_time = time.time()

    for case in cases:
        result = engine.compute(
            case["text"],
            profile="default",
            equation_mode="gated",
            verbose=False,
        )

        predicted = _decision_to_label(
            result["decision"],
            result.get("hard_override", False),
        )
        expected = case["expected"]

        y_true.append(expected)
        y_pred.append(predicted)

        correct = predicted == expected
        cat = case["category"]
        category_counts[cat]["total"] += 1
        if correct:
            category_counts[cat]["correct"] += 1

        entry = {
            "id": case["id"],
            "category": cat,
            "language": case["language"],
            "expected": expected,
            "predicted": predicted,
            "correct": correct,
            "H": result["H"],
            "I": result["I"],
            "E": result["E"],
            "S": result["S"],
            "decision": result["decision"],
            "hard_override": result.get("hard_override", False),
        }
        results_log.append(entry)

        if not correct:
            errors_by_category[cat].append(entry)

    elapsed = time.time() - start_time

    # ── compute metrics ──
    metrics = _compute_metrics(y_true, y_pred, positive_label="BLOCKED")

    # also compute per-language metrics
    ar_true = [y_true[i] for i, c in enumerate(cases)
               if c["language"] == "ar"]
    ar_pred = [y_pred[i] for i, c in enumerate(cases)
               if c["language"] == "ar"]
    en_true = [y_true[i] for i, c in enumerate(cases)
               if c["language"] == "en"]
    en_pred = [y_pred[i] for i, c in enumerate(cases)
               if c["language"] == "en"]
    ar_metrics = _compute_metrics(ar_true, ar_pred, positive_label="BLOCKED")
    en_metrics = _compute_metrics(en_true, en_pred, positive_label="BLOCKED")

    # ── print results ──
    print(f"\n  Elapsed: {elapsed:.1f}s ({elapsed/len(cases):.2f}s/case)")

    print(f"\n  ╔══════════════════════════════════════════════╗")
    print(f"  ║  OVERALL METRICS (positive class = BLOCKED)  ║")
    print(f"  ╠══════════════════════════════════════════════╣")
    print(f"  ║  Accuracy:   {metrics['accuracy']:.4f}  "
          f"({metrics['tp']+metrics['tn']}/{metrics['total']} correct)    ║")
    print(f"  ║  Precision:  {metrics['precision']:.4f}  "
          f"(of predicted BLOCKED)       ║")
    print(f"  ║  Recall:     {metrics['recall']:.4f}  "
          f"(of actual BLOCKED)          ║")
    print(f"  ║  F1:         {metrics['f1']:.4f}  "
          f"(harmonic mean)              ║")
    print(f"  ╚══════════════════════════════════════════════╝")

    print(f"\n  Confusion Matrix:")
    print(f"                    Predicted")
    print(f"                    SAFE    BLOCKED")
    print(f"  Actual SAFE    [ {metrics['tn']:3d}      {metrics['fp']:3d}  ]")
    print(f"  Actual BLOCKED [ {metrics['fn']:3d}      {metrics['tp']:3d}  ]")

    print(f"\n  Per-Language Breakdown:")
    print(f"    Arabic  (n={len(ar_true):2d}): "
          f"F1={ar_metrics['f1']:.4f}  "
          f"P={ar_metrics['precision']:.4f}  "
          f"R={ar_metrics['recall']:.4f}  "
          f"Acc={ar_metrics['accuracy']:.4f}")
    print(f"    English (n={len(en_true):2d}): "
          f"F1={en_metrics['f1']:.4f}  "
          f"P={en_metrics['precision']:.4f}  "
          f"R={en_metrics['recall']:.4f}  "
          f"Acc={en_metrics['accuracy']:.4f}")

    # ── per-category accuracy ──
    print(f"\n  Per-Category Accuracy:")
    for cat in sorted(category_counts.keys()):
        c = category_counts[cat]
        pct = c["correct"] / c["total"] * 100
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        print(f"    {cat:30s}  {c['correct']}/{c['total']}  "
              f"{bar} {pct:.0f}%")

    # ── error analysis ──
    if errors_by_category:
        print(f"\n  ─── MISCLASSIFICATIONS ({sum(len(v) for v in errors_by_category.values())} total) ───")
        for cat, errs in sorted(errors_by_category.items()):
            for e in errs:
                direction = ("FP (false alarm)"
                             if e["predicted"] == "BLOCKED"
                             else "FN (missed harm)")
                print(f"    {e['id']} [{cat}] {direction}")
                text_preview = (cases[int(e['id'].split('-')[1]) - 1]
                                ["text"][:60])
                print(f"      Text: {text_preview}...")
                print(f"      H={e['H']:.3f}  I={e['I']:.3f}  "
                      f"E={e['E']:.3f}  S={e['S']:.3f}  "
                      f"→ {e['decision']}")
    else:
        print(f"\n  No misclassifications — perfect score!")

    print("\n" + "=" * 78)
    print("  END HELD-OUT VALIDATION REPORT")
    print("=" * 78)

    # ── save detailed results to JSON ──
    results_path = os.path.join(
        _BENCHMARK_DIR, "held_out_results.json"
    )
    output = {
        "run_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "equation": "gated",
        "profile": "default",
        "params": {"theta": 0.40, "alpha": 10, "w1": 2.0, "w2": 1.5},
        "metrics": {
            "overall": metrics,
            "arabic": ar_metrics,
            "english": en_metrics,
        },
        "per_category": dict(category_counts),
        "cases": results_log,
    }
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n  Detailed results saved: {results_path}")


# ── standalone runner ───────────────────────────────────────────────

def main():
    """Run held-out validation as a standalone script."""
    print("\n" + "=" * 78)
    print("  AATIF Held-Out Validation — Standalone Mode")
    print("=" * 78)

    if not os.path.exists(HELD_OUT_PATH):
        print(f"ERROR: Held-out file not found: {HELD_OUT_PATH}")
        sys.exit(1)

    if not _check_ollama():
        print(
            "\nERROR: Ollama is not running on localhost:11434.\n"
            "Please start Ollama and pull bge-m3:\n"
            "  ollama serve\n"
            "  ollama pull bge-m3\n"
            "\nThen re-run this script."
        )
        sys.exit(1)

    data = load_held_out()
    print(f"  Loaded {len(data['cases'])} held-out cases")

    from aatif_s_equation import AATIFEngine
    engine = AATIFEngine()

    # Run the aggregate report
    # (Re-implementing here to avoid pytest dependency in standalone)
    cases = data["cases"]
    y_true, y_pred = [], []

    print(f"\n  Running {len(cases)} cases through gated equation...\n")

    for i, case in enumerate(cases, 1):
        result = engine.compute(
            case["text"],
            profile="default",
            equation_mode="gated",
            verbose=False,
        )
        predicted = _decision_to_label(
            result["decision"],
            result.get("hard_override", False),
        )
        expected = case["expected"]
        y_true.append(expected)
        y_pred.append(predicted)

        status = "✓" if predicted == expected else "✗"
        print(f"  [{i:2d}/{len(cases)}] {status} {case['id']} "
              f"H={result['H']:.3f} I={result['I']:.3f} "
              f"E={result['E']:.3f} S={result['S']:.3f} "
              f"→ {result['decision']} "
              f"(pred={predicted}, exp={expected})")

    metrics = _compute_metrics(y_true, y_pred, positive_label="BLOCKED")

    print(f"\n{'=' * 78}")
    print(f"  HELD-OUT RESULTS (n={metrics['total']})")
    print(f"  {'─' * 74}")
    print(f"  F1        = {metrics['f1']:.4f}")
    print(f"  Accuracy  = {metrics['accuracy']:.4f}")
    print(f"  Precision = {metrics['precision']:.4f}")
    print(f"  Recall    = {metrics['recall']:.4f}")
    print(f"  TP={metrics['tp']}  FP={metrics['fp']}  "
          f"FN={metrics['fn']}  TN={metrics['tn']}")
    print(f"{'=' * 78}")

    # List misclassifications
    misses = [(c, t, p) for c, t, p in zip(cases, y_true, y_pred) if t != p]
    if misses:
        print(f"\n  Misclassifications ({len(misses)}):")
        for case, true, pred in misses:
            direction = "FP" if pred == "BLOCKED" else "FN"
            print(f"    {direction} {case['id']} [{case['category']}]: "
                  f"expected {true}, got {pred}")
            print(f"       {case['text'][:70]}...")
    else:
        print(f"\n  Perfect score — no misclassifications!")


if __name__ == "__main__":
    main()
