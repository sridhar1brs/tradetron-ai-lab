#!/usr/bin/env python3
"""
Tradetron Strategy Batch Validator
Automatically runs the auditor on ALL strategy JSON files in the strategies/ directory.
Returns exit code 0 if all pass, 1 if any have critical errors.

Usage:
    python3 scripts/tradetron_validator.py
    python3 scripts/tradetron_validator.py --json    # Machine-readable JSON output
"""

import json
import os
import sys
import glob
import argparse

# Import auditor functions
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tradetron_auditor import audit_strategy, validate_ui_schema

def run_batch_validation(strategies_dir, json_mode=False, report_dir=None):
    json_files = sorted(glob.glob(os.path.join(strategies_dir, "*.json")))

    if not json_files:
        msg = f"No strategy JSON files found in {strategies_dir}"
        if json_mode:
            print(json.dumps({"status": "ERROR", "message": msg, "files": []}))
        else:
            print(f"⚠️  {msg}")
        return False

    results = []
    total_errors = 0
    total_warnings = 0

    if not json_mode:
        print(f"\n{'='*60}")
        print(f"  TRADETRON BATCH STRATEGY VALIDATOR")
        print(f"  Scanning: {strategies_dir}")
        print(f"  Files Found: {len(json_files)}")
        if report_dir:
            print(f"  Report Output: {report_dir}")
        print(f"{'='*60}\n")

    for filepath in json_files:
        filename = os.path.basename(filepath)
        try:
            if report_dir:
                # Use audit_strategy to generate complete chronological audit & emit report
                is_passed = audit_strategy(filepath, report_dir=report_dir)
                errors = [] if is_passed else ["Audit failed - see report"]
                warnings = []
            else:
                with open(filepath, "r") as f:
                    data = json.load(f)
                errors, warnings = validate_ui_schema(data)

            status = "PASSED" if not errors else "FAILED"
            total_errors += len(errors)
            total_warnings += len(warnings)
            results.append({
                "file": filename,
                "status": status,
                "errors": len(errors),
                "warnings": len(warnings),
                "error_details": errors,
                "warning_details": warnings
            })
            if not json_mode and not report_dir:
                icon = "✅" if not errors else "❌"
                print(f"  {icon}  {filename}")
                if errors:
                    for e in errors:
                        print(f"       ❌ {e}")
                if warnings:
                    for w in warnings:
                        print(f"       ⚠️  {w}")
        except Exception as e:
            results.append({
                "file": filename,
                "status": "ERROR",
                "errors": 1,
                "warnings": 0,
                "error_details": [f"Failed to load/parse: {e}"],
                "warning_details": []
            })
            total_errors += 1
            if not json_mode:
                print(f"  ❌  {filename} — Load Error: {e}")

    passed = [r for r in results if r["status"] == "PASSED"]
    failed = [r for r in results if r["status"] != "PASSED"]
    overall_status = "PASSED" if not failed else "FAILED"

    if json_mode:
        print(json.dumps({
            "status": overall_status,
            "total_files": len(results),
            "passed": len(passed),
            "failed": len(failed),
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "files": results
        }, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"  BATCH VALIDATION SUMMARY")
        print(f"{'='*60}")
        print(f"  Total Files   : {len(results)}")
        print(f"  ✅ Passed     : {len(passed)}")
        print(f"  ❌ Failed     : {len(failed)}")
        print(f"  Total Errors  : {total_errors}")
        print(f"  Total Warnings: {total_warnings}")
        if overall_status == "PASSED":
            print(f"\n  ✅ ALL STRATEGIES PASSED — Ready for Tradetron import.")
        else:
            print(f"\n  ❌ VALIDATION FAILED — Fix errors before importing.")
        print(f"{'='*60}\n")

    return overall_status == "PASSED"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch-validate all Tradetron strategy JSON files")
    parser.add_argument(
        "--strategies-dir",
        default=None,
        help="Path to strategies directory (default: ../strategies/ relative to this script)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as machine-readable JSON"
    )
    parser.add_argument(
        "--report-dir",
        default=None,
        help="If set, emit structured JSON audit reports to this directory"
    )
    args = parser.parse_args()

    if args.strategies_dir:
        strategies_dir = args.strategies_dir
    else:
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
        strategies_dir = os.path.normpath(os.path.join(scripts_dir, "..", "strategies"))

    success = run_batch_validation(strategies_dir, json_mode=args.json, report_dir=args.report_dir)
    sys.exit(0 if success else 1)
