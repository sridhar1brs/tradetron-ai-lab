#!/usr/bin/env python3
"""
Tradetron Keyword/Builder Drift Linter

Statically scans every builder script under scripts/ (Keyword(...) DSL calls
and raw AST dict literals like {"name": ..., "params": [...]}) and cross-checks
each referenced keyword name against the offline knowledge base in keywords/.

Catches two classes of drift discovered manually during the 2026-08 audit:
  1. A keyword name used in a builder script that has no corresponding
     keywords/*.json file at all (the KB has a gap).
  2. A builder call site passing a different number of params than the
     keyword's documented "parameters" schema (possible copy-paste drift,
     e.g. the "Rule 39"/Current Month mismatch found in
     build_corrected_strategy.py and build_dynamic_iron_fly.py).

Param-count mismatches are reported as warnings only (many keywords are
variadic or have optional trailing params), missing keywords are errors.

Usage:
    python3 scripts/check_keyword_drift.py
    python3 scripts/check_keyword_drift.py --json
"""
import ast
import glob
import json
import os
import re
import sys
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
KEYWORDS_DIR = os.path.join(ROOT_DIR, "keywords")

# Builder scripts to scan — excludes scratch/ (throwaway) and this repo's own
# test/dev fixtures which intentionally exercise malformed keyword usage.
BUILDER_GLOBS = [
    os.path.join(SCRIPT_DIR, "tradetron_builder.py"),
    os.path.join(SCRIPT_DIR, "build_*.py"),
]

def slugify(name):
    """Normalize a keyword's display name to match keywords/*.json filenames."""
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")

def load_keyword_kb():
    """Return {slug: {"file": path, "param_count": int, "display_name": str}}."""
    kb = {}
    for path in sorted(glob.glob(os.path.join(KEYWORDS_DIR, "*.json"))):
        try:
            data = json.load(open(path))
        except Exception:
            continue
        name = data.get("name", "")
        if not name:
            continue
        params = data.get("parameters", [])
        kb[slugify(name)] = {
            "file": os.path.basename(path),
            "param_count": len(params),
            "display_name": name,
        }
    return kb

def _const_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None

def find_keyword_usages(filepath):
    """Return list of (keyword_name, param_count, lineno) found via static AST scan."""
    usages = []
    try:
        tree = ast.parse(open(filepath).read(), filename=filepath)
    except Exception:
        return usages

    for node in ast.walk(tree):
        # Pattern 1: Keyword("Name", p1, p2, ...) DSL constructor calls
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Keyword":
            if node.args:
                name = _const_str(node.args[0])
                if name:
                    usages.append((name, len(node.args) - 1, node.lineno))

        # Pattern 2: raw AST dict literals {"name": "...", "params": [...]}
        elif isinstance(node, ast.Dict):
            name = None
            param_count = None
            for k, v in zip(node.keys, node.values):
                key = _const_str(k)
                if key == "name":
                    name = _const_str(v)
                elif key == "params" and isinstance(v, ast.List):
                    param_count = len(v.elts)
            if name and param_count is not None:
                usages.append((name, param_count, node.lineno))

    return usages

def run_lint(json_mode=False):
    kb = load_keyword_kb()
    errors = []
    warnings = []
    scanned_files = []

    filepaths = set()
    for pattern in BUILDER_GLOBS:
        filepaths.update(glob.glob(pattern))

    for filepath in sorted(filepaths):
        rel = os.path.relpath(filepath, ROOT_DIR)
        scanned_files.append(rel)
        for name, param_count, lineno in find_keyword_usages(filepath):
            slug = slugify(name)
            entry = kb.get(slug)
            if entry is None:
                errors.append(f"[MISSING KEYWORD] {rel}:{lineno} uses '{name}' — no keywords/*.json file documents this keyword.")
                continue
            # Skip count check for bare/variadic keywords (0 documented params,
            # or the operator/comparator pseudo-keywords used by Rule()).
            if entry["param_count"] > 0 and param_count != entry["param_count"]:
                warnings.append(
                    f"[PARAM COUNT DRIFT] {rel}:{lineno} calls '{name}' with {param_count} param(s), "
                    f"but {entry['file']} documents {entry['param_count']}. Verify this isn't stale/copy-pasted."
                )

    result = {
        "scanned_files": scanned_files,
        "errors": errors,
        "warnings": warnings,
        "status": "PASSED" if not errors else "FAILED",
    }

    if json_mode:
        print(json.dumps(result, indent=2))
    else:
        print("=" * 60)
        print(" TRADETRON KEYWORD/BUILDER DRIFT LINTER")
        print("=" * 60)
        print(f"Scanned {len(scanned_files)} builder file(s), {len(kb)} known keywords.\n")
        if errors:
            print("Errors:")
            for e in errors:
                print(f"  ❌ {e}")
        if warnings:
            print("Warnings:")
            for w in warnings:
                print(f"  ⚠️  {w}")
        if not errors and not warnings:
            print("✅ No drift detected — all builder keyword usages match the keyword KB.")
        print(f"\nStatus: {'✅ PASSED' if not errors else '❌ FAILED'} ({len(errors)} error(s), {len(warnings)} warning(s))")

    return result["status"] == "PASSED"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lint builder scripts for keyword drift against keywords/*.json")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()
    ok = run_lint(json_mode=args.json)
    sys.exit(0 if ok else 1)
