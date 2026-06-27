#!/usr/bin/env python3
"""
AATIF Fingerprint Validation — Phase 0
========================================

Tests the hypothesis: injecting a user's behavioral fingerprint as
context into AATIF's processing produces more accurate and contextually
appropriate responses than processing messages in isolation.

Methodology:
  1. Extract real conversations from the sales engine conversation log
  2. Load manually-created fingerprint profiles for each user
  3. For each message in a conversation:
     a) Run through AATIF S equation WITHOUT fingerprint (baseline)
     b) Run through AATIF S equation WITH fingerprint context
     c) Compare: did the fingerprint change the decision or scores?

What the fingerprint CAN change (Phase 0 — no engine modification):
  - Equation mode selection (classic vs gated)
  - Profile selection (default vs high_sensitivity vs relaxed)
  - Domain selection (general vs ecommerce etc.)
  - TimeSense context (previous timestamps, timezone)
  - Decision interpretation (same S, different response strategy)

What the fingerprint CANNOT change yet (future phases):
  - Anchor weighting (new anchors based on user history)
  - Dynamic theta adjustment based on user trust level
  - Conversation memory integration into H/I/E scoring

Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
License: BSL 1.1
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Path setup ──────────────────────────────────────────────
_THIS_DIR = Path(__file__).resolve().parent
_ENGINE_DIR = _THIS_DIR.parent / "engine"
_FINGERPRINT_DIR = _THIS_DIR / "fingerprints"
_SALES_ENGINE_DIR = Path("/Users/aatifsandbox/aatif-sales-engine")

sys.path.insert(0, str(_ENGINE_DIR))
sys.path.insert(0, str(_SALES_ENGINE_DIR))


# ── Conversation data loader ───────────────────────────────

@dataclass
class ConversationTurn:
    """A single turn in a conversation."""
    log_id: str
    relationship_key: str
    company_id: str
    direction: str         # "inbound" or "outbound"
    message_text: str
    message_type: str      # "identity", "followup", "demo", etc.
    timestamp: str         # ISO format
    timestamp_unix: float  # parsed unix timestamp


def load_conversation_log(path: Optional[Path] = None) -> list[ConversationTurn]:
    """Load all turns from the sales engine conversation log."""
    if path is None:
        path = _SALES_ENGINE_DIR / "conversation_log.csv"

    turns = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts_str = row.get("timestamp", "")
            try:
                dt = datetime.fromisoformat(ts_str)
                ts_unix = dt.timestamp()
            except (ValueError, TypeError):
                ts_unix = 0.0

            text = row.get("message_text", "").strip()
            if not text or text.startswith("<media:"):
                continue  # skip empty and media messages

            turns.append(ConversationTurn(
                log_id=row.get("log_id", ""),
                relationship_key=row.get("relationship_key", ""),
                company_id=row.get("company_id", ""),
                direction=row.get("direction", ""),
                message_text=text,
                message_type=row.get("message_type", ""),
                timestamp=ts_str,
                timestamp_unix=ts_unix,
            ))
    return turns


def group_conversations(turns: list[ConversationTurn]) -> dict[str, list[ConversationTurn]]:
    """Group turns by relationship_key (user identity)."""
    groups: dict[str, list[ConversationTurn]] = {}
    for t in turns:
        key = t.relationship_key
        if key not in groups:
            groups[key] = []
        groups[key].append(t)
    return groups


def select_test_conversations(
    groups: dict[str, list[ConversationTurn]],
    min_turns: int = 3,
    max_users: int = 10,
) -> dict[str, list[ConversationTurn]]:
    """Select conversations with enough turns for meaningful testing."""
    selected = {}
    for key, conv_turns in sorted(groups.items(),
                                   key=lambda x: len(x[1]), reverse=True):
        inbound = [t for t in conv_turns if t.direction == "inbound"]
        if len(inbound) >= min_turns:
            selected[key] = conv_turns
        if len(selected) >= max_users:
            break
    return selected


# ── Fingerprint loader ─────────────────────────────────────

def load_fingerprint(user_id: str) -> Optional[dict]:
    """Load a fingerprint profile for a user, if one exists.

    Looks for: fingerprints/{sanitized_user_id}.json
    """
    # Sanitize user_id for filename: owner_test@C00000 -> owner_test_C00000
    safe_name = user_id.replace("@", "_")
    path = _FINGERPRINT_DIR / f"{safe_name}.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def fingerprint_to_context(fp: dict) -> dict:
    """Convert a fingerprint into parameters for the S equation.

    This is the core of the experiment: how does user context
    translate into equation parameters?

    Phase 0 mappings (conservative — using existing engine levers):
      - comprehension_signals → profile selection
      - emotional_baseline → equation_mode preference
      - interaction pattern → conversation_id for hysteresis
    """
    context = {
        "profile": "default",
        "equation_mode": "gated",
        "domain": None,
        "conversation_id": fp.get("user_id"),
    }

    # --- Profile selection based on comprehension signals ---
    comp = fp.get("comprehension_signals", "")
    emotional = fp.get("emotional_baseline", "")

    if comp == "needs_examples" or "frustrated" in emotional or "impatient" in emotional:
        # User who gets confused needs more conservative handling
        # — lower theta catches ambiguous situations earlier
        context["profile"] = "high_sensitivity"
    elif comp == "quick_to_understand":
        # User who grasps concepts quickly can handle relaxed profile
        context["profile"] = "default"
    elif "detached" in emotional or "casual" in emotional:
        context["profile"] = "default"

    # --- Domain inference from observed patterns ---
    patterns = fp.get("observed_patterns", [])
    patterns_text = " ".join(patterns).lower()
    if "advertising" in patterns_text or "دعايه" in patterns_text or "marketing" in patterns_text:
        context["domain"] = "ecommerce"
    elif "medical" in patterns_text or "health" in patterns_text:
        context["domain"] = "healthcare"
    elif "learning" in patterns_text or "education" in patterns_text:
        context["domain"] = "education"

    # --- TimeSense enrichment ---
    active_hours = fp.get("active_hours", "")
    if "late_night" in active_hours:
        context["user_timezone"] = "Asia/Riyadh"  # Gulf users
        context["fatigue_aware"] = True
    elif "afternoon" in active_hours:
        context["user_timezone"] = "Asia/Riyadh"
        context["fatigue_aware"] = False
    else:
        context["user_timezone"] = "Asia/Riyadh"
        context["fatigue_aware"] = False

    # --- Interaction pattern for response strategy ---
    question_pattern = fp.get("typical_question_pattern", "")
    if question_pattern == "repeats_to_confirm":
        context["response_strategy"] = "simplify_and_confirm"
        context["max_response_sentences"] = 2
    elif question_pattern == "asks_once_and_moves_on":
        context["response_strategy"] = "direct_answer"
        context["max_response_sentences"] = 3
    else:
        context["response_strategy"] = "standard"
        context["max_response_sentences"] = 4

    return context


# ── Test harness ───────────────────────────────────────────

@dataclass
class ComparisonResult:
    """Result of comparing fingerprint vs no-fingerprint processing."""
    user_id: str
    message_text: str
    message_index: int
    timestamp: str

    # Baseline (no fingerprint)
    baseline_H: float
    baseline_I: float
    baseline_E: float
    baseline_S: float
    baseline_decision: str
    baseline_profile: str
    baseline_equation_mode: str

    # With fingerprint
    fp_H: float
    fp_I: float
    fp_E: float
    fp_S: float
    fp_decision: str
    fp_profile: str
    fp_equation_mode: str
    fp_domain: Optional[str]
    fp_response_strategy: str

    # Comparison
    decision_changed: bool
    S_delta: float
    quality_assessment: str  # "improved", "same", "degraded", "unknown"

    # TimeSense data (with fingerprint only)
    time_period: Optional[str]
    fatigue_risk: Optional[bool]
    interaction_gap: Optional[str]


def assess_quality(
    message: str,
    baseline_decision: str,
    fp_decision: str,
    fp_context: dict,
    conversation_history: list[ConversationTurn],
    current_index: int,
) -> str:
    """Assess whether the fingerprint-informed decision is better.

    Heuristics for Phase 0 (no human evaluation yet):
      - If user later said 'مافهمت', the prior EXECUTE should have been CLARIFY
      - If user is repeating questions, earlier EXECUTE was premature
      - If fingerprint made it MORE restrictive for a confused user: improved
      - If fingerprint made it LESS restrictive for a clear user: improved
    """
    # Look ahead in conversation for confusion signals
    confusion_signals = {"مافهمت", "ما فهمت", "مش فاهم", "ايش يعني",
                         "وضح اكتر", "مافهمتك", "بتخرف"}

    future_confused = False
    for future_turn in conversation_history[current_index + 1:current_index + 5]:
        if future_turn.direction == "inbound":
            text_lower = future_turn.message_text.lower().strip()
            if any(sig in text_lower for sig in confusion_signals):
                future_confused = True
                break

    if baseline_decision == fp_decision:
        return "same"

    # If user will be confused later and fingerprint moved toward CLARIFY
    decision_order = {"EXECUTE": 3, "CLARIFY": 2, "SAFE_STOP": 1, "SAFE_FREEZE": 0}
    baseline_level = decision_order.get(baseline_decision, 2)
    fp_level = decision_order.get(fp_decision, 2)

    if future_confused:
        if fp_level < baseline_level:
            # Fingerprint made it more cautious before confusion → good
            return "improved"
        else:
            return "degraded"

    # If user didn't get confused, being less restrictive is fine
    if fp_level > baseline_level:
        return "improved"
    elif fp_level < baseline_level:
        # More restrictive without cause — check if user pattern suggests it
        strategy = fp_context.get("response_strategy", "")
        if strategy == "simplify_and_confirm":
            return "improved"  # conservative approach for confused users
        return "degraded"

    return "unknown"


def run_comparison(
    engine,
    time_sense,
    conversations: dict[str, list[ConversationTurn]],
    max_messages_per_user: int = 15,
) -> list[ComparisonResult]:
    """Run the full comparison: baseline vs fingerprint-informed.

    For each inbound message in each conversation:
      1. Score with default settings (no fingerprint)
      2. Load fingerprint, derive context, score with fingerprint params
      3. Compare results

    Returns list of ComparisonResult for analysis.
    """
    results = []

    for user_id, turns in conversations.items():
        print(f"\n{'='*60}")
        print(f"  User: {user_id}")
        print(f"  Turns: {len(turns)}")

        # Load fingerprint
        fp = load_fingerprint(user_id)
        if fp is None:
            print(f"  [SKIP] No fingerprint found")
            continue

        fp_context = fingerprint_to_context(fp)
        print(f"  Fingerprint: profile={fp_context['profile']}, "
              f"mode={fp_context['equation_mode']}, "
              f"domain={fp_context['domain']}, "
              f"strategy={fp_context['response_strategy']}")

        # Track previous timestamp for TimeSense
        prev_timestamp = None
        msg_count = 0

        for idx, turn in enumerate(turns):
            if turn.direction != "inbound":
                # Track outbound timestamps too (for gap calculation)
                prev_timestamp = turn.timestamp_unix
                continue

            if msg_count >= max_messages_per_user:
                break

            text = turn.message_text
            print(f"\n  [{msg_count}] «{text[:50]}»")

            # ── Baseline: no fingerprint ──
            try:
                baseline = engine.compute(
                    text,
                    profile="default",
                    equation_mode="gated",  # use gated for both to make comparison fair
                )
            except Exception as e:
                print(f"    [ERROR baseline] {e}")
                prev_timestamp = turn.timestamp_unix
                continue

            # ── With fingerprint ──
            try:
                fp_result = engine.compute(
                    text,
                    profile=fp_context["profile"],
                    equation_mode=fp_context["equation_mode"],
                    domain=fp_context.get("domain"),
                    conversation_id=fp_context.get("conversation_id"),
                )
            except Exception as e:
                print(f"    [ERROR fingerprint] {e}")
                prev_timestamp = turn.timestamp_unix
                continue

            # ── TimeSense reading ──
            time_reading = None
            try:
                time_reading = time_sense.read(
                    timestamp=turn.timestamp_unix,
                    user_timezone=fp_context.get("user_timezone", "Asia/Riyadh"),
                    previous_timestamp=prev_timestamp,
                )
            except Exception:
                pass

            # ── Quality assessment ──
            quality = assess_quality(
                message=text,
                baseline_decision=baseline["decision"],
                fp_decision=fp_result["decision"],
                fp_context=fp_context,
                conversation_history=turns,
                current_index=idx,
            )

            result = ComparisonResult(
                user_id=user_id,
                message_text=text,
                message_index=msg_count,
                timestamp=turn.timestamp,
                baseline_H=baseline["H"],
                baseline_I=baseline["I"],
                baseline_E=baseline["E"],
                baseline_S=baseline["S"],
                baseline_decision=baseline["decision"],
                baseline_profile=baseline["profile"],
                baseline_equation_mode=baseline["equation_mode"],
                fp_H=fp_result["H"],
                fp_I=fp_result["I"],
                fp_E=fp_result["E"],
                fp_S=fp_result["S"],
                fp_decision=fp_result["decision"],
                fp_profile=fp_result["profile"],
                fp_equation_mode=fp_result["equation_mode"],
                fp_domain=fp_context.get("domain"),
                fp_response_strategy=fp_context.get("response_strategy", "standard"),
                decision_changed=baseline["decision"] != fp_result["decision"],
                S_delta=round(fp_result["S"] - baseline["S"], 4),
                quality_assessment=quality,
                time_period=time_reading.period if time_reading else None,
                fatigue_risk=time_reading.fatigue_risk if time_reading else None,
                interaction_gap=time_reading.interaction_gap_assessment if time_reading else None,
            )

            results.append(result)

            # Print comparison
            changed = "CHANGED" if result.decision_changed else "same"
            print(f"    Baseline: S={baseline['S']:.4f} → {baseline['decision']}")
            print(f"    FP:       S={fp_result['S']:.4f} → {fp_result['decision']} [{changed}]")
            print(f"    Quality:  {quality}")
            if time_reading:
                print(f"    Time:     {time_reading.period} | "
                      f"gap={time_reading.interaction_gap_assessment} | "
                      f"fatigue={time_reading.fatigue_risk}")

            prev_timestamp = turn.timestamp_unix
            msg_count += 1

    return results


# ── Results analysis ───────────────────────────────────────

def analyze_results(results: list[ComparisonResult]) -> dict:
    """Compute summary statistics from comparison results."""
    if not results:
        return {"error": "no results to analyze"}

    total = len(results)
    changed = sum(1 for r in results if r.decision_changed)
    improved = sum(1 for r in results if r.quality_assessment == "improved")
    degraded = sum(1 for r in results if r.quality_assessment == "degraded")
    same = sum(1 for r in results if r.quality_assessment == "same")
    unknown = sum(1 for r in results if r.quality_assessment == "unknown")

    s_deltas = [r.S_delta for r in results]
    avg_s_delta = sum(s_deltas) / len(s_deltas) if s_deltas else 0

    # Per-user breakdown
    users = {}
    for r in results:
        if r.user_id not in users:
            users[r.user_id] = {
                "total": 0, "changed": 0,
                "improved": 0, "degraded": 0,
                "profile_used": r.fp_profile,
                "domain_used": r.fp_domain,
                "strategy_used": r.fp_response_strategy,
            }
        users[r.user_id]["total"] += 1
        if r.decision_changed:
            users[r.user_id]["changed"] += 1
        if r.quality_assessment == "improved":
            users[r.user_id]["improved"] += 1
        elif r.quality_assessment == "degraded":
            users[r.user_id]["degraded"] += 1

    # TimeSense insights
    fatigue_msgs = [r for r in results if r.fatigue_risk]
    late_night_msgs = [r for r in results if r.time_period == "ليل"]

    return {
        "summary": {
            "total_messages": total,
            "decisions_changed": changed,
            "change_rate": round(changed / total, 3) if total else 0,
            "improved": improved,
            "degraded": degraded,
            "same": same,
            "unknown": unknown,
            "improvement_rate": round(improved / max(changed, 1), 3),
            "avg_S_delta": round(avg_s_delta, 4),
        },
        "per_user": users,
        "temporal": {
            "fatigue_risk_messages": len(fatigue_msgs),
            "late_night_messages": len(late_night_msgs),
        },
        "hypothesis_support": _evaluate_hypothesis(total, changed, improved, degraded),
    }


def _evaluate_hypothesis(total, changed, improved, degraded) -> dict:
    """Evaluate whether the data supports the fingerprint hypothesis."""
    if total < 5:
        verdict = "insufficient_data"
        explanation = (
            "Fewer than 5 test messages — cannot draw conclusions. "
            "Need more conversation data or lower min_turns threshold."
        )
    elif changed == 0:
        verdict = "no_effect"
        explanation = (
            "Fingerprint context produced identical decisions to baseline "
            "in all cases. The fingerprint-to-parameter mapping may need "
            "to target different levers (e.g., anchor weights, not just "
            "profile/domain selection)."
        )
    elif improved > degraded and improved / max(changed, 1) > 0.5:
        verdict = "supported"
        explanation = (
            f"Fingerprint improved decisions in {improved}/{changed} changed cases. "
            f"The hypothesis is supported at Phase 0 level — user context "
            f"demonstrably changes AATIF decisions for the better."
        )
    elif degraded > improved:
        verdict = "contradicted"
        explanation = (
            f"Fingerprint DEGRADED decisions in {degraded}/{changed} changed cases. "
            f"The fingerprint-to-parameter mapping is producing worse results. "
            f"Review the mapping logic in fingerprint_to_context()."
        )
    else:
        verdict = "inconclusive"
        explanation = (
            f"Mixed results: {improved} improved, {degraded} degraded, "
            f"{changed - improved - degraded} unknown. Need Phase 1 "
            f"(human evaluation) to determine true quality."
        )

    return {"verdict": verdict, "explanation": explanation}


# ── Main ───────────────────────────────────────────────────

def main():
    """Run Phase 0 fingerprint validation experiment."""
    print("=" * 65)
    print("  AATIF Fingerprint Validation — Phase 0")
    print("  Hypothesis: User fingerprint improves AATIF decisions")
    print("=" * 65)

    # Step 1: Load conversation data
    print("\n[1/5] Loading conversation log...")
    try:
        all_turns = load_conversation_log()
        print(f"  Loaded {len(all_turns)} turns (excluding media/empty)")
    except FileNotFoundError:
        print("  [ERROR] Conversation log not found at:")
        print(f"    {_SALES_ENGINE_DIR / 'conversation_log.csv'}")
        print("  Make sure the sales engine directory is accessible.")
        sys.exit(1)

    # Step 2: Group and select conversations
    print("\n[2/5] Selecting test conversations...")
    groups = group_conversations(all_turns)
    print(f"  Found {len(groups)} unique users")
    conversations = select_test_conversations(groups, min_turns=2)
    print(f"  Selected {len(conversations)} users with 2+ inbound messages")
    for uid, turns in conversations.items():
        inbound = sum(1 for t in turns if t.direction == "inbound")
        print(f"    {uid}: {inbound} inbound / {len(turns)} total")

    # Step 3: Check fingerprints
    print("\n[3/5] Checking fingerprint profiles...")
    fp_count = 0
    for uid in conversations:
        fp = load_fingerprint(uid)
        status = "FOUND" if fp else "MISSING"
        if fp:
            fp_count += 1
        print(f"    {uid}: {status}")
    print(f"  {fp_count}/{len(conversations)} fingerprints available")

    if fp_count == 0:
        print("\n  [ERROR] No fingerprints found. Create profiles in:")
        print(f"    {_FINGERPRINT_DIR}/")
        sys.exit(1)

    # Step 4: Initialize engine and run comparison
    print("\n[4/5] Initializing AATIF engine...")
    try:
        from aatif_s_equation import AATIFEngine
        from aatif_time_sense import TimeSense
        engine = AATIFEngine()
        time_sense = TimeSense()
    except Exception as e:
        print(f"  [ERROR] Engine initialization failed: {e}")
        print("  Make sure Ollama is running: ollama serve")
        print("  And bge-m3 is pulled: ollama pull bge-m3")
        sys.exit(1)

    print("\n  Running comparison...")
    results = run_comparison(engine, time_sense, conversations)

    # Step 5: Analyze and save results
    print(f"\n{'='*65}")
    print("  [5/5] Analysis")
    print(f"{'='*65}")

    analysis = analyze_results(results)

    # Print summary
    s = analysis.get("summary", {})
    print(f"\n  Total messages tested:  {s.get('total_messages', 0)}")
    print(f"  Decisions changed:     {s.get('decisions_changed', 0)} "
          f"({s.get('change_rate', 0)*100:.1f}%)")
    print(f"  Improved:              {s.get('improved', 0)}")
    print(f"  Degraded:              {s.get('degraded', 0)}")
    print(f"  Same:                  {s.get('same', 0)}")
    print(f"  Unknown:               {s.get('unknown', 0)}")
    print(f"  Avg S delta:           {s.get('avg_S_delta', 0):+.4f}")

    # Print hypothesis verdict
    hyp = analysis.get("hypothesis_support", {})
    print(f"\n  Hypothesis verdict:    {hyp.get('verdict', 'N/A')}")
    print(f"  {hyp.get('explanation', '')}")

    # Print temporal insights
    t = analysis.get("temporal", {})
    if t.get("fatigue_risk_messages", 0) > 0:
        print(f"\n  Fatigue-risk messages:  {t['fatigue_risk_messages']}")
    if t.get("late_night_messages", 0) > 0:
        print(f"  Late-night messages:   {t['late_night_messages']}")

    # Save results
    output_path = _THIS_DIR / "fingerprint_results.json"
    output = {
        "experiment": "fingerprint_validation_phase0",
        "timestamp": datetime.now().isoformat(),
        "analysis": analysis,
        "detailed_results": [asdict(r) for r in results],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  Results saved to: {output_path}")
    print(f"\n{'='*65}")
    print("  Phase 0 complete.")
    print(f"{'='*65}")

    return analysis


if __name__ == "__main__":
    main()
