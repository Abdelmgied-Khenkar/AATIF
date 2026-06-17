#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AATIF Eval Runner — مُقيِّم عاطف
===============================

Runs sample Arabic/English conversations end-to-end through the intent engine
and scores each turn against spec-level expectations.

Design notes
------------
- Expectations encode the SPEC (what AATIF *should* do), not current behavior,
  so genuine defects surface as failures instead of being frozen in.
- Conversations flagged "xfail" document a KNOWN bug (with owner + reason).
  They are expected to fail today; the runner reports them separately and does
  NOT count them as unexpected failures. If an xfail case starts PASSING, that
  is surfaced as "XPASS — bug fixed, remove xfail" so the eval doesn't silently
  hide a fix.
- Exit code 0 when there are no unexpected failures (and no xpass). Exit 1
  otherwise. This makes the runner CI-friendly.

Imports only `aatif_intent_engine` (runs standalone, never touches api_server).
Stdlib only.

CLI
---
    cd ~/AATIF
    python3 -m eval.eval_runner                 # run all
    python3 -m eval.eval_runner --id greeting_saudi
    python3 -m eval.eval_runner --verbose
    python3 -m eval.eval_runner --json          # machine-readable summary
"""

import argparse
import json
import os
import sys

# ── Make the AATIF root importable when run as a module or a script ──
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aatif_intent_engine import read_intent  # noqa: E402

DEFAULT_CONVERSATIONS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "sample_conversations.json")


class AATIFEvalRunner:
    """Loads sample conversations, runs them through the engine, scores results."""

    def __init__(self, conversations_path=DEFAULT_CONVERSATIONS):
        self.conversations_path = conversations_path
        with open(conversations_path, "r", encoding="utf-8") as fh:
            self.conversations = json.load(fh)

    # ── per-turn scoring ────────────────────────────────────────────
    @staticmethod
    def _check_turn(turn, reading):
        """Return (ok: bool, checks: list[dict]) for one turn vs its reading."""
        checks = []

        def record(name, ok, expected, actual):
            checks.append({"check": name, "ok": ok,
                           "expected": expected, "actual": actual})

        if "expected_decision" in turn:
            exp = turn["expected_decision"]
            act = reading.decision
            record("decision", exp == act, exp, act)

        if "expected_dialect" in turn:
            exp = turn["expected_dialect"]
            allowed = exp if isinstance(exp, list) else [exp]
            act = reading.dialect_detected
            record("dialect", act in allowed, allowed, act)

        if "expected_emotion" in turn:
            exp = turn["expected_emotion"]
            act = reading.emotional_state
            record("emotion", exp == act, exp, act)

        if "expected_load_bearing" in turn:
            exp = bool(turn["expected_load_bearing"])
            act = bool(reading.load_bearing)
            record("load_bearing", exp == act, exp, act)

        if "expected_harm_above" in turn:
            exp = float(turn["expected_harm_above"])
            act = float(reading.harm_score)
            record("harm_above", act > exp, f"> {exp}", round(act, 3))

        if "expected_ambiguity_above" in turn:
            exp = float(turn["expected_ambiguity_above"])
            act = float(reading.ambiguity_score)
            record("ambiguity_above", act > exp, f"> {exp}", round(act, 3))

        ok = all(c["ok"] for c in checks)
        return ok, checks

    # ── single conversation ─────────────────────────────────────────
    def run_single(self, conversation):
        """Process every turn; return a structured result dict."""
        cid = conversation.get("id", "?")
        # Stable per-conversation session id so multi-turn memory/hysteresis applies.
        session_id = f"eval::{cid}"
        is_xfail = bool(conversation.get("xfail", False))

        turn_results = []
        all_turns_ok = True
        for idx, turn in enumerate(conversation.get("turns", [])):
            reading = read_intent(turn["text"], session_id=session_id)
            ok, checks = self._check_turn(turn, reading)
            all_turns_ok = all_turns_ok and ok
            turn_results.append({
                "index": idx,
                "text": turn["text"],
                "ok": ok,
                "checks": checks,
                "actual": {
                    "decision": reading.decision,
                    "dialect": reading.dialect_detected,
                    "emotion": reading.emotional_state,
                    "load_bearing": reading.load_bearing,
                    "ambiguity": round(reading.ambiguity_score, 3),
                    "harm": round(reading.harm_score, 3),
                },
            })

        # Classify outcome.
        # status ∈ {PASS, FAIL, XFAIL (known bug, still failing), XPASS (bug fixed)}
        if is_xfail:
            status = "XPASS" if all_turns_ok else "XFAIL"
        else:
            status = "PASS" if all_turns_ok else "FAIL"

        return {
            "id": cid,
            "description": conversation.get("description", ""),
            "xfail": is_xfail,
            "xfail_reason": conversation.get("xfail_reason", ""),
            "passed": all_turns_ok,
            "status": status,
            "turns": turn_results,
        }

    # ── all conversations ───────────────────────────────────────────
    def run_all(self, only_id=None):
        results = []
        for conv in self.conversations:
            if only_id and conv.get("id") != only_id:
                continue
            results.append(self.run_single(conv))

        counts = {"PASS": 0, "FAIL": 0, "XFAIL": 0, "XPASS": 0}
        for r in results:
            counts[r["status"]] += 1

        unexpected = counts["FAIL"] + counts["XPASS"]
        return {
            "total": len(results),
            "passed": counts["PASS"],
            "failed": counts["FAIL"],
            "known_failures": counts["XFAIL"],
            "fixed_now_passing": counts["XPASS"],
            "unexpected": unexpected,
            "results": results,
        }

    # ── reporting (bilingual) ───────────────────────────────────────
    @staticmethod
    def print_report(summary, verbose=False):
        BADGE = {"PASS": "✅ PASS", "FAIL": "❌ FAIL",
                 "XFAIL": "🟡 XFAIL", "XPASS": "🔵 XPASS"}
        print("=" * 64)
        print(" AATIF Eval Runner — مُقيِّم عاطف")
        print("=" * 64)

        for r in summary["results"]:
            print(f"{BADGE[r['status']]}  {r['id']}  —  {r['description']}")
            if r["xfail"] and r["status"] in ("XFAIL", "XPASS"):
                print(f"        ↳ known bug / علّة معروفة: {r['xfail_reason']}")
            if verbose or r["status"] in ("FAIL", "XPASS"):
                for t in r["turns"]:
                    mark = "  ok " if t["ok"] else " !!! "
                    print(f"     [{mark}] «{t['text']}»  →  {t['actual']}")
                    for c in t["checks"]:
                        if verbose or not c["ok"]:
                            cmark = "ok" if c["ok"] else "FAIL"
                            print(f"           - {c['check']}: {cmark} "
                                  f"(expected {c['expected']}, got {c['actual']})")

        print("-" * 64)
        print(" النتيجة / Summary")
        print(f"   total / الإجمالي           : {summary['total']}")
        print(f"   passed / ناجح              : {summary['passed']}")
        print(f"   failed / فاشل (unexpected) : {summary['failed']}")
        print(f"   known bugs / علل موثّقة     : {summary['known_failures']} (XFAIL)")
        print(f"   now-fixed / أُصلِحت         : {summary['fixed_now_passing']} (XPASS)")
        print("=" * 64)
        if summary["unexpected"] == 0:
            print(" ✅ No unexpected failures. / لا أعطال غير متوقعة.")
        else:
            print(f" ❌ {summary['unexpected']} unexpected issue(s). "
                  f"/ {summary['unexpected']} مشكلة غير متوقعة.")
            if summary["fixed_now_passing"]:
                print("    (XPASS = a documented bug now passes — remove its xfail flag.)")
        print("=" * 64)


def main(argv=None):
    parser = argparse.ArgumentParser(description="AATIF eval runner")
    parser.add_argument("--id", help="run only the conversation with this id")
    parser.add_argument("--verbose", action="store_true",
                        help="show every turn and every check")
    parser.add_argument("--json", action="store_true",
                        help="print machine-readable JSON summary instead of report")
    parser.add_argument("--conversations", default=DEFAULT_CONVERSATIONS,
                        help="path to sample_conversations.json")
    args = parser.parse_args(argv)

    runner = AATIFEvalRunner(args.conversations)
    summary = runner.run_all(only_id=args.id)

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        runner.print_report(summary, verbose=args.verbose)

    return 0 if summary["unexpected"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
