"""
Llama Guard 3 (8B) vs AATIF — Head-to-Head Comparison
======================================================

Runs Llama Guard 3 8B on the SAME 570 blind evaluation prompts used to
evaluate AATIF, enabling a direct apple-to-apple comparison on identical
data with identical ground-truth labels.

Llama Guard 3 is called via Together AI's inference API (free tier gives
$5 credit — enough for thousands of calls).

Usage:
    # Full run (all 570 prompts)
    TOGETHER_API_KEY=xxx python benchmarks/llamaguard_comparison.py

    # Quick test (10 prompts)
    TOGETHER_API_KEY=xxx python benchmarks/llamaguard_comparison.py --dry-run

    # Custom output path
    TOGETHER_API_KEY=xxx python benchmarks/llamaguard_comparison.py \
        --output benchmarks/llamaguard_comparison_results_custom.json

    # Custom AATIF results path
    TOGETHER_API_KEY=xxx python benchmarks/llamaguard_comparison.py \
        --aatif-results benchmarks/blind_eval_results_2026-06-26.json

Architect: Abdulmjeed Ibrahim Khenkar
"""

import json
import os
import sys
import time
import argparse
import requests
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# ═══════════════════════════════════════════════════════════════
#  Configuration
# ═══════════════════════════════════════════════════════════════

TOGETHER_API_URL = "https://api.together.xyz/v1/chat/completions"
LLAMA_GUARD_MODEL = "meta-llama/Meta-Llama-Guard-3-8B"

# Retry / rate-limit settings
MAX_RETRIES = 3
INITIAL_BACKOFF = 2.0       # seconds
BACKOFF_MULTIPLIER = 2.0    # exponential
RATE_LIMIT_DELAY = 0.15     # delay between requests (seconds)


# ═══════════════════════════════════════════════════════════════
#  Load AATIF blind eval results
# ═══════════════════════════════════════════════════════════════

def load_aatif_results(path: str) -> dict:
    """Load the AATIF blind evaluation results JSON.

    Returns the full JSON dict with 'metadata', 'metrics', and 'results' keys.
    Each item in 'results' has: id, text, category, ground_truth, blocked, etc.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    n = len(data["results"])
    print(f"  Loaded {n} AATIF results from {path}")
    print(f"  Harmful: {data['metadata']['total_harmful']}, "
          f"Benign: {data['metadata']['total_benign']}")
    return data


# ═══════════════════════════════════════════════════════════════
#  Llama Guard 3 API call
# ═══════════════════════════════════════════════════════════════

def classify_with_llamaguard(text: str, api_key: str) -> dict:
    """Send a single prompt to Llama Guard 3 8B via Together AI.

    Llama Guard uses a chat format where the user message is the content
    to classify. The model responds with either "safe" or "unsafe"
    (possibly followed by a category code like S1, S2, etc.).

    Returns:
        dict with keys:
            - raw_response: str  (full model output)
            - classification: str  ("safe" or "unsafe")
            - blocked: bool  (True if classified as unsafe)
            - category_code: str or None  (e.g. "S1" if present)
            - error: str or None
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": LLAMA_GUARD_MODEL,
        "messages": [
            {"role": "user", "content": text}
        ],
        "max_tokens": 100,
        "temperature": 0.0,   # deterministic classification
        "top_p": 1.0,
    }

    backoff = INITIAL_BACKOFF
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(
                TOGETHER_API_URL,
                headers=headers,
                json=payload,
                timeout=30,
            )

            # Rate limit (429) or server error (5xx) → retry with backoff
            if resp.status_code == 429 or resp.status_code >= 500:
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                if attempt < MAX_RETRIES:
                    print(f"    [retry {attempt}/{MAX_RETRIES}] "
                          f"{resp.status_code}, waiting {backoff:.1f}s...")
                    time.sleep(backoff)
                    backoff *= BACKOFF_MULTIPLIER
                    continue
                else:
                    return {
                        "raw_response": "",
                        "classification": "error",
                        "blocked": False,
                        "category_code": None,
                        "error": last_error,
                    }

            resp.raise_for_status()
            result = resp.json()

            # Extract the model's text output
            raw = result["choices"][0]["message"]["content"].strip()

            # Parse: Llama Guard 3 outputs "safe" or "unsafe\nSX"
            raw_lower = raw.lower()
            if raw_lower.startswith("unsafe"):
                classification = "unsafe"
                blocked = True
                # Extract category code if present (e.g. "unsafe\nS1")
                lines = raw.strip().split("\n")
                category_code = lines[1].strip() if len(lines) > 1 else None
            elif raw_lower.startswith("safe"):
                classification = "safe"
                blocked = False
                category_code = None
            else:
                # Unexpected output — treat as safe to be conservative
                classification = "unknown"
                blocked = False
                category_code = None

            return {
                "raw_response": raw,
                "classification": classification,
                "blocked": blocked,
                "category_code": category_code,
                "error": None,
            }

        except requests.exceptions.Timeout:
            last_error = "Request timed out"
            if attempt < MAX_RETRIES:
                print(f"    [retry {attempt}/{MAX_RETRIES}] timeout, "
                      f"waiting {backoff:.1f}s...")
                time.sleep(backoff)
                backoff *= BACKOFF_MULTIPLIER
                continue

        except requests.exceptions.RequestException as e:
            last_error = str(e)
            if attempt < MAX_RETRIES:
                print(f"    [retry {attempt}/{MAX_RETRIES}] {e}, "
                      f"waiting {backoff:.1f}s...")
                time.sleep(backoff)
                backoff *= BACKOFF_MULTIPLIER
                continue

    return {
        "raw_response": "",
        "classification": "error",
        "blocked": False,
        "category_code": None,
        "error": last_error,
    }


# ═══════════════════════════════════════════════════════════════
#  Metric computation
# ═══════════════════════════════════════════════════════════════

def compute_metrics(results: list, system_key: str) -> dict:
    """Compute classification metrics for a system.

    Args:
        results: list of dicts, each with 'ground_truth' and
                 '{system_key}_blocked' boolean fields.
        system_key: 'aatif' or 'llamaguard'

    Returns:
        dict with TP, FP, TN, FN, accuracy, precision, recall, f1, fpr
    """
    blocked_key = f"{system_key}_blocked"

    TP = FP = TN = FN = 0

    for r in results:
        gt = r["ground_truth"]        # "harmful" or "benign"
        blocked = r[blocked_key]       # True or False

        if gt == "harmful" and blocked:
            TP += 1
        elif gt == "harmful" and not blocked:
            FN += 1
        elif gt == "benign" and blocked:
            FP += 1
        elif gt == "benign" and not blocked:
            TN += 1

    total = TP + FP + TN + FN
    accuracy = (TP + TN) / total if total > 0 else 0.0
    precision = TP / (TP + FP) if (TP + FP) > 0 else 0.0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) > 0 else 0.0)
    fpr = FP / (FP + TN) if (FP + TN) > 0 else 0.0

    return {
        "TP": TP,
        "FP": FP,
        "TN": TN,
        "FN": FN,
        "total": total,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "fpr": round(fpr, 4),
    }


def compute_per_category(results: list, system_key: str) -> dict:
    """Compute metrics broken down by category."""
    by_cat = defaultdict(list)
    for r in results:
        by_cat[r["category"]].append(r)

    cat_metrics = {}
    for cat in sorted(by_cat.keys()):
        cat_metrics[cat] = compute_metrics(by_cat[cat], system_key)
        cat_metrics[cat]["count"] = len(by_cat[cat])

    return cat_metrics


# ═══════════════════════════════════════════════════════════════
#  Pretty-print comparison table
# ═══════════════════════════════════════════════════════════════

def print_comparison_table(aatif_m: dict, lg_m: dict):
    """Print a side-by-side comparison table to stdout."""

    print("\n" + "=" * 66)
    print("  HEAD-TO-HEAD COMPARISON: AATIF vs Llama Guard 3 (8B)")
    print("=" * 66)

    header = f"{'Metric':<22} {'AATIF':>12} {'LlamaGuard3':>14} {'Delta':>10}"
    print(header)
    print("-" * 66)

    rows = [
        ("Accuracy",   "accuracy"),
        ("Precision",  "precision"),
        ("Recall",     "recall"),
        ("F1 Score",   "f1"),
        ("FPR",        "fpr"),
        ("True Pos",   "TP"),
        ("False Pos",  "FP"),
        ("True Neg",   "TN"),
        ("False Neg",  "FN"),
    ]

    for label, key in rows:
        a_val = aatif_m[key]
        l_val = lg_m[key]

        if isinstance(a_val, float):
            delta = a_val - l_val
            sign = "+" if delta > 0 else ""
            # For FPR, lower is better — flip sign for visual cue
            if key == "fpr":
                indicator = " (better)" if delta < 0 else (" (worse)" if delta > 0 else "")
            else:
                indicator = " (better)" if delta > 0 else (" (worse)" if delta < 0 else "")
            print(f"  {label:<20} {a_val:>12.4f} {l_val:>14.4f} "
                  f"{sign}{delta:>+.4f}{indicator}")
        else:
            delta = a_val - l_val
            sign = "+" if delta > 0 else ""
            print(f"  {label:<20} {a_val:>12d} {l_val:>14d} {sign}{delta:>+d}")

    print("=" * 66)


def print_category_comparison(aatif_cat: dict, lg_cat: dict):
    """Print per-category F1 comparison."""

    print("\n" + "=" * 72)
    print("  PER-CATEGORY F1 COMPARISON")
    print("=" * 72)
    header = (f"{'Category':<22} {'N':>4} "
              f"{'AATIF F1':>10} {'LG3 F1':>10} {'Delta':>10}")
    print(header)
    print("-" * 72)

    all_cats = sorted(set(list(aatif_cat.keys()) + list(lg_cat.keys())))
    for cat in all_cats:
        a = aatif_cat.get(cat, {})
        l = lg_cat.get(cat, {})
        n = a.get("count", l.get("count", 0))
        a_f1 = a.get("f1", 0.0)
        l_f1 = l.get("f1", 0.0)
        delta = a_f1 - l_f1
        sign = "+" if delta > 0 else ""
        print(f"  {cat:<22} {n:>4} {a_f1:>10.4f} {l_f1:>10.4f} "
              f"{sign}{delta:>+.4f}")

    print("=" * 72)


# ═══════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Head-to-head comparison: AATIF vs Llama Guard 3 (8B) "
                    "on the same 570 blind evaluation prompts."
    )
    parser.add_argument(
        "--aatif-results",
        default="benchmarks/blind_eval_results_2026-06-26.json",
        help="Path to AATIF blind eval results JSON "
             "(default: benchmarks/blind_eval_results_2026-06-26.json)"
    )
    parser.add_argument(
        "--output",
        default="benchmarks/llamaguard_comparison_results.json",
        help="Output path for comparison results "
             "(default: benchmarks/llamaguard_comparison_results.json)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process only 10 prompts for quick testing"
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Path to partial results file to resume from "
             "(skips already-processed prompt IDs)"
    )

    args = parser.parse_args()

    # --- API key ---
    api_key = os.environ.get("TOGETHER_API_KEY", "").strip()
    if not api_key:
        print("ERROR: Set TOGETHER_API_KEY environment variable.")
        print("  Get a free key at: https://api.together.xyz/signup")
        print("  Free tier includes $5 credit (~5000+ calls).")
        sys.exit(1)

    # --- Load AATIF results ---
    print("\n[1/4] Loading AATIF blind evaluation results...")
    aatif_data = load_aatif_results(args.aatif_results)
    all_cases = aatif_data["results"]

    if args.dry_run:
        # Take a balanced sample: 5 harmful + 5 benign
        harmful = [c for c in all_cases if c["ground_truth"] == "harmful"][:5]
        benign = [c for c in all_cases if c["ground_truth"] == "benign"][:5]
        all_cases = harmful + benign
        print(f"  --dry-run: using {len(all_cases)} prompts "
              f"({len(harmful)} harmful + {len(benign)} benign)")

    # --- Resume support ---
    already_done = {}
    if args.resume:
        print(f"\n  Resuming from {args.resume}...")
        with open(args.resume, "r") as f:
            partial = json.load(f)
        for r in partial.get("results", []):
            already_done[r["id"]] = r
        print(f"  Found {len(already_done)} already-processed prompts")

    # --- Run Llama Guard 3 on each prompt ---
    print(f"\n[2/4] Classifying {len(all_cases)} prompts with "
          f"Llama Guard 3 8B via Together AI...")
    print(f"  Model: {LLAMA_GUARD_MODEL}")
    print(f"  Rate limit delay: {RATE_LIMIT_DELAY}s between requests")

    results = []
    errors = 0
    start_time = time.time()

    for i, case in enumerate(all_cases):
        prompt_id = case["id"]
        text = case["text"]

        # Progress
        pct = (i + 1) / len(all_cases) * 100
        elapsed = time.time() - start_time
        eta = (elapsed / (i + 1)) * (len(all_cases) - i - 1) if i > 0 else 0

        # If resuming and already done, skip
        if prompt_id in already_done:
            results.append(already_done[prompt_id])
            print(f"  [{i+1:>4}/{len(all_cases)}] {pct:5.1f}% "
                  f"[{prompt_id}] SKIPPED (resumed)")
            continue

        # Call Llama Guard 3
        lg_result = classify_with_llamaguard(text, api_key)

        if lg_result["error"]:
            errors += 1
            print(f"  [{i+1:>4}/{len(all_cases)}] {pct:5.1f}% "
                  f"[{prompt_id}] ERROR: {lg_result['error'][:60]}")
        else:
            status = ("BLOCKED" if lg_result["blocked"]
                      else "PASSED")
            cat_info = (f" ({lg_result['category_code']})"
                        if lg_result["category_code"] else "")
            print(f"  [{i+1:>4}/{len(all_cases)}] {pct:5.1f}% "
                  f"ETA {eta:.0f}s "
                  f"[{prompt_id}] {status}{cat_info}")

        # Build combined result
        combined = {
            "id": prompt_id,
            "text": text,
            "category": case["category"],
            "subcategory": case.get("subcategory", ""),
            "ground_truth": case["ground_truth"],
            # AATIF result
            "aatif_decision": case["decision"],
            "aatif_blocked": case["blocked"],
            "aatif_H": case.get("H"),
            "aatif_S": case.get("S"),
            # Llama Guard 3 result
            "llamaguard_classification": lg_result["classification"],
            "llamaguard_blocked": lg_result["blocked"],
            "llamaguard_category_code": lg_result["category_code"],
            "llamaguard_raw": lg_result["raw_response"],
            "llamaguard_error": lg_result["error"],
        }
        results.append(combined)

        # Rate limit delay
        if lg_result["error"] is None:
            time.sleep(RATE_LIMIT_DELAY)

    total_time = time.time() - start_time
    print(f"\n  Done in {total_time:.1f}s "
          f"({total_time/len(all_cases):.2f}s/prompt)")
    if errors > 0:
        print(f"  WARNING: {errors} prompts had API errors "
              f"(excluded from metrics)")

    # --- Filter out errors for metric computation ---
    valid_results = [r for r in results if r["llamaguard_error"] is None]
    error_results = [r for r in results if r["llamaguard_error"] is not None]
    print(f"  Valid results: {len(valid_results)} / {len(results)}")

    # --- Compute metrics ---
    print(f"\n[3/4] Computing metrics...")

    aatif_metrics = compute_metrics(valid_results, "aatif")
    lg_metrics = compute_metrics(valid_results, "llamaguard")

    aatif_cat_metrics = compute_per_category(valid_results, "aatif")
    lg_cat_metrics = compute_per_category(valid_results, "llamaguard")

    # --- Print comparison ---
    print_comparison_table(aatif_metrics, lg_metrics)
    print_category_comparison(aatif_cat_metrics, lg_cat_metrics)

    # --- Save results ---
    print(f"\n[4/4] Saving results to {args.output}...")

    output_data = {
        "metadata": {
            "experiment": "llamaguard_comparison",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat(),
            "aatif_results_source": args.aatif_results,
            "llamaguard_model": LLAMA_GUARD_MODEL,
            "total_prompts": len(all_cases),
            "valid_prompts": len(valid_results),
            "api_errors": errors,
            "dry_run": args.dry_run,
            "runtime_seconds": round(total_time, 1),
        },
        "comparison": {
            "aatif": aatif_metrics,
            "llamaguard3": lg_metrics,
        },
        "per_category": {
            "aatif": aatif_cat_metrics,
            "llamaguard3": lg_cat_metrics,
        },
        "results": results,
        "errors": [
            {"id": r["id"], "text": r["text"][:80], "error": r["llamaguard_error"]}
            for r in error_results
        ],
    }

    # Ensure output directory exists
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"  Saved to {args.output}")

    # --- Summary for paper ---
    print("\n" + "=" * 66)
    print("  SUMMARY FOR PAPER")
    print("=" * 66)
    print(f"  Test set: {len(valid_results)} identical prompts "
          f"(blind, unseen)")
    print(f"  AATIF:         Acc={aatif_metrics['accuracy']:.1%}  "
          f"F1={aatif_metrics['f1']:.3f}  "
          f"FPR={aatif_metrics['fpr']:.1%}")
    print(f"  Llama Guard 3: Acc={lg_metrics['accuracy']:.1%}  "
          f"F1={lg_metrics['f1']:.3f}  "
          f"FPR={lg_metrics['fpr']:.1%}")

    f1_delta = aatif_metrics['f1'] - lg_metrics['f1']
    print(f"\n  F1 delta (AATIF − LG3): {f1_delta:+.3f}")
    if f1_delta > 0:
        print(f"  → AATIF outperforms Llama Guard 3 by "
              f"{abs(f1_delta):.3f} F1 points")
    elif f1_delta < 0:
        print(f"  → Llama Guard 3 outperforms AATIF by "
              f"{abs(f1_delta):.3f} F1 points")
    else:
        print(f"  → Systems tie on F1")
    print("=" * 66)


if __name__ == "__main__":
    main()
