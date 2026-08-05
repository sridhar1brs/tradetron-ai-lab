#!/usr/bin/env python3
"""
Tradetron AI Lab — Audit Dashboard
Reads structured JSON audit reports from audit_reports/ and renders:
  1. Pass/Fail trend per day (sparkline)
  2. Most-frequently-fired rule violations (bug hotspots)
  3. Per-strategy health summary
  4. Recent run history

Usage:
  python3 Tradetron-AI-Lab/scripts/audit_dashboard.py                          # reads ./audit_reports/
  python3 Tradetron-AI-Lab/scripts/audit_dashboard.py --dir audit_reports
  python3 Tradetron-AI-Lab/scripts/audit_dashboard.py --strategy momentum_strategy.json
  python3 Tradetron-AI-Lab/scripts/audit_dashboard.py --violations             # show violation detail
"""

import os, json, argparse
from collections import defaultdict, Counter

GREEN  = "\033[92m"; RED  = "\033[91m"; YELLOW = "\033[93m"
CYAN   = "\033[96m"; BOLD = "\033[1m";  DIM    = "\033[2m"; RESET = "\033[0m"

def clr(t, c): return f"{c}{t}{RESET}"
def bold(t):   return f"{BOLD}{t}{RESET}"
def dim(t):    return f"{DIM}{t}{RESET}"

RULE_NAMES = {
    8:"Universal Exit placement", 9:"ConditionGroup children dict",
    10:"Condition subType/extra", 13:"Math Operation postfix order",
    17:"Spot index Current Month", 21:"Macro keyword primitives",
    24:"Positions Detail case", 25:"Traded Instrument coords",
    27:"Instrument Name 5-commas", 28:"Leg metadata completeness",
    30:"Qty macro (tt_lots/tt_value)", 31:"Instrument integer PK",
    42:"OHLC Instrument() in conditions",
}

def load_reports(report_dir):
    reports = []
    if not os.path.isdir(report_dir):
        return reports
    for day in sorted(os.listdir(report_dir)):
        dp = os.path.join(report_dir, day)
        if not os.path.isdir(dp): continue
        for fname in sorted(os.listdir(dp)):
            if not fname.endswith(".json"): continue
            try:
                with open(os.path.join(dp, fname)) as f:
                    r = json.load(f)
                r["_date"] = day
                reports.append(r)
            except: pass
    return reports

def bar(v, mx, w=20):
    if mx == 0: return dim("░" * w)
    f = int(round(v / mx * w))
    return clr("█" * f, CYAN) + dim("░" * (w - f))

def resolve_report_dir(target_dir):
    if os.path.isabs(target_dir):
        return target_dir
    # Check relative to CWD first
    cwd_path = os.path.abspath(target_dir)
    if os.path.exists(cwd_path):
        return cwd_path
    # Check relative to script dir parent
    sd = os.path.dirname(os.path.abspath(__file__))
    script_parent_path = os.path.normpath(os.path.join(sd, "..", target_dir))
    if os.path.exists(script_parent_path):
        return script_parent_path
    return cwd_path

def main():
    ap = argparse.ArgumentParser(description="Tradetron Audit Dashboard")
    ap.add_argument("--dir", default="audit_reports")
    ap.add_argument("--strategy", default=None)
    ap.add_argument("--violations", action="store_true")
    ap.add_argument("--recent", type=int, default=12)
    args = ap.parse_args()

    rd = resolve_report_dir(args.dir)
    reports = load_reports(rd)

    print()
    print(bold(clr("╔══════════════════════════════════════════════════════════╗", CYAN)))
    print(bold(clr("║     TRADETRON AI LAB — AUDIT OBSERVABILITY DASHBOARD     ║", CYAN)))
    print(bold(clr("╚══════════════════════════════════════════════════════════╝", CYAN)))
    print()

    if not reports:
        print(clr(f"  No reports found in '{rd}'. Run auditor with --json-report to start tracking.", YELLOW))
        print(dim(f"\n  Example:\n    python3 Tradetron-AI-Lab/scripts/tradetron_auditor.py Tradetron-AI-Lab/strategies/momentum_strategy.json --json-report audit_reports/\n"))
        return

    if args.strategy:
        reports = [r for r in reports if args.strategy in r.get("strategy_file", "")]
        if not reports:
            print(clr(f"  No reports for: {args.strategy}", YELLOW)); return
        print(dim(f"  Filter: {args.strategy}\n"))

    total  = len(reports)
    passed = sum(1 for r in reports if r.get("status") == "PASSED")
    pct    = passed / total * 100 if total else 0

    # ── Summary ──────────────────────────────────────────────────────────────
    print(bold("📊 OVERALL SUMMARY"))
    print(f"  Runs    : {bold(str(total))}")
    print(f"  Passed  : {clr(str(passed), GREEN)}   Failed: {clr(str(total-passed), RED)}")
    print(f"  Pass %  : {bold(f'{pct:.1f}%')}  {bar(passed, total)}")
    print()

    # ── Daily trend sparkline ────────────────────────────────────────────────
    by_day = defaultdict(list)
    for r in reports:
        by_day[r["_date"]].append(r.get("status") == "PASSED")
    if len(by_day) >= 1:
        print(bold("📈 DAILY PASS RATE TREND"))
        print(f"  {'Date':<12}  {'Runs':>5}  {'Pass%':>7}  {'Bar'}")
        print("  " + "─" * 55)
        for day in sorted(by_day):
            s = by_day[day]; n = len(s); p = sum(s)
            pp = p/n*100
            pc = GREEN if pp == 100 else (YELLOW if pp >= 50 else RED)
            print(f"  {day:<12}  {n:>5}  {clr(f'{pp:.0f}%', pc):>15}  {bar(p, n)}")
        print()

    # ── Per-strategy health ──────────────────────────────────────────────────
    by_strat = defaultdict(list)
    for r in reports: by_strat[r.get("strategy_file","?")].append(r)
    print(bold("🏥 PER-STRATEGY HEALTH"))
    print(f"  {'Strategy':<42}  {'Runs':>5}  {'Latest':>8}  {'EvalScore':>9}  {'Err':>5}  {'Warn':>5}")
    print("  " + "─" * 84)
    for strat, runs in sorted(by_strat.items()):
        lt = runs[-1]
        st = clr("PASS", GREEN) if lt.get("status") == "PASSED" else clr("FAIL", RED)
        ec = lt.get("critical_error_count", 0)
        wc = lt.get("warning_count", 0)
        es = clr(str(ec), RED) if ec else clr("0", GREEN)
        ws = clr(str(wc), YELLOW) if wc else dim("0")
        score = lt.get("semantic_score", 100)
        sc_clr = GREEN if score >= 90 else (YELLOW if score >= 75 else RED)
        score_str = clr(f"{score}%", sc_clr)
        print(f"  {strat[:40]:<42}  {len(runs):>5}  {st:>16}  {score_str:>18}  {es:>13}  {ws:>13}")
    print()

    # ── Rule hit frequency ───────────────────────────────────────────────────
    rc = Counter()
    for r in reports:
        for rn in r.get("rules_fired", []): rc[rn] += 1
    if rc:
        mx = max(rc.values())
        print(bold("🎯 RULE VIOLATION FREQUENCY (Bug Hotspots)"))
        print(f"  {'Rule':<5}  {'Description':<38}  {'Hits':>5}  Bar")
        print("  " + "─" * 72)
        for rn, cnt in rc.most_common(10):
            label = RULE_NAMES.get(rn, f"Rule {rn}")
            cs = clr(str(cnt), RED) if cnt > 2 else clr(str(cnt), YELLOW)
            print(f"  {f'R{rn}':<5}  {label:<38}  {cs:>13}  {bar(cnt, mx, 22)}")
        print()
    else:
        print(bold("🎯 RULE VIOLATION FREQUENCY"))
        print(clr("  No violations across all runs — clean slate! 🎉", GREEN))
        print()

    # ── Recent runs ──────────────────────────────────────────────────────────
    recent = reports[-args.recent:][::-1]
    print(bold(f"🕐 RECENT {len(recent)} AUDIT RUNS"))
    print(f"  {'Date':<12}  {'Strategy':<40}  {'Status':>8}  {'ms':>6}  {'Err':>5}")
    print("  " + "─" * 76)
    for r in recent:
        st = clr("PASS", GREEN) if r.get("status") == "PASSED" else clr("FAIL", RED)
        ec = r.get("critical_error_count", 0)
        es = clr(str(ec), RED) if ec else dim("0")
        ms = str(r.get("elapsed_ms", "?"))
        print(f"  {r.get('_date','?'):<12}  {r.get('strategy_file','?')[:38]:<40}  {st:>16}  {ms:>6}  {es:>13}")
    print()

    # ── Violation detail ─────────────────────────────────────────────────────
    if args.violations:
        failed = [r for r in reports if r.get("status") == "FAILED"]
        if args.strategy:
            failed = [r for r in failed if args.strategy in r.get("strategy_file", "")]
        if failed:
            print(bold(f"🔴 FAILURE DETAIL (Last {min(5, len(failed))})"))
            for r in failed[-5:][::-1]:
                print(f"\n  {bold(r.get('strategy_file','?'))} — {r.get('_date','?')}")
                for v in r.get("violations", []):
                    print(f"    {clr('❌', RED)} {v[:115]}{'...' if len(v)>115 else ''}")
        print()

    print(dim(f"  Source: {rd}  |  Total: {total} reports"))
    print()

if __name__ == "__main__":
    main()
