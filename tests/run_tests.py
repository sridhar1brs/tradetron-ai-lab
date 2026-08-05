#!/usr/bin/env python3
"""
Tradetron AI Lab — Automated Regression Test Suite Runner
Executes auditor validation tests:
  1. tests/known_good/*.json -> Must PASS with 0 critical errors
  2. tests/known_bad/*.json  -> Must FAIL with specific rule violations

Usage:
  python3 Tradetron-AI-Lab/tests/run_tests.py
"""

import os
import sys
import json
import argparse

# Add scripts directory to import path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from tradetron_auditor import validate_ui_schema

GREEN  = "\033[92m"; RED  = "\033[91m"; YELLOW = "\033[93m"
CYAN   = "\033[96m"; BOLD = "\033[1m";  DIM    = "\033[2m"; RESET = "\033[0m"

def clr(t, c): return f"{c}{t}{RESET}"
def bold(t):   return f"{BOLD}{t}{RESET}"

EXPECTED_RULE_MAP = {
    "bad_rule_42_bare_instrument.json": "RULE 42",
    "bad_rule_30_no_qty_macro.json": "RULE 30",
    "bad_rule_31_string_instrument.json": "RULE 31"
}

def main():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    known_good_dir = os.path.join(test_dir, "known_good")
    known_bad_dir  = os.path.join(test_dir, "known_bad")

    print()
    print(bold(clr("╔══════════════════════════════════════════════════════════╗", CYAN)))
    print(bold(clr("║     TRADETRON AI LAB — AUTOMATED REGRESSION SUITE       ║", CYAN)))
    print(bold(clr("╚══════════════════════════════════════════════════════════╝", CYAN)))
    print()

    total_tests = 0
    passed_tests = 0

    # ── 1. Known Good Tests ───────────────────────────────────────────────────
    print(bold("🧪 TEST GROUP 1: Known Good Strategies (Must PASS)"))
    print("  " + "─" * 60)
    good_files = [f for f in sorted(os.listdir(known_good_dir)) if f.endswith(".json")]
    for fname in good_files:
        total_tests += 1
        fpath = os.path.join(known_good_dir, fname)
        with open(fpath) as f: data = json.load(f)
        errors, warnings = validate_ui_schema(data)
        if len(errors) == 0:
            passed_tests += 1
            print(f"  ✅ PASS: {fname:<45} {clr('0 errors', GREEN)}")
        else:
            print(f"  ❌ FAIL: {fname:<45} {clr(f'{len(errors)} unexpected errors', RED)}")
            for e in errors:
                print(f"     -> {e}")
    print()

    # ── 2. Known Bad Tests ────────────────────────────────────────────────────
    print(bold("🧪 TEST GROUP 2: Known Bad Strategies (Must Catch Rule Violation)"))
    print("  " + "─" * 60)
    bad_files = [f for f in sorted(os.listdir(known_bad_dir)) if f.endswith(".json")]
    for fname in bad_files:
        total_tests += 1
        fpath = os.path.join(known_bad_dir, fname)
        with open(fpath) as f: data = json.load(f)
        errors, warnings = validate_ui_schema(data)
        expected_rule = EXPECTED_RULE_MAP.get(fname, None)
        
        # Check if the expected rule violation was correctly caught
        found_expected = False
        if expected_rule:
            found_expected = any(expected_rule in err for err in errors)
        else:
            found_expected = len(errors) > 0

        if found_expected:
            passed_tests += 1
            rule_str = clr(f"caught {expected_rule}", GREEN) if expected_rule else clr("caught errors", GREEN)
            print(f"  ✅ PASS: {fname:<45} ({rule_str})")
        else:
            print(f"  ❌ FAIL: {fname:<45} {clr(f'MISSED expected {expected_rule}', RED)}")
            print(f"     Actual errors caught: {errors}")
    print()

    # ── Summary ───────────────────────────────────────────────────────────────
    print(bold("📊 REGRESSION TEST SUMMARY"))
    print("  " + "─" * 60)
    pct = (passed_tests / total_tests * 100) if total_tests else 0
    status_str = clr("ALL TESTS PASSED", GREEN) if passed_tests == total_tests else clr("TEST SUITE FAILED", RED)
    print(f"  Results : {passed_tests}/{total_tests} passed ({pct:.0f}%) — {bold(status_str)}")
    print()

    sys.exit(0 if passed_tests == total_tests else 1)

if __name__ == "__main__":
    main()
