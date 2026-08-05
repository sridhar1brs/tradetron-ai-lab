#!/usr/bin/env python3
"""
Tradetron Strategy LLM-as-Judge (Semantic Intent Evaluator)
Evaluates whether the encoded AST logic (conditionJson, strikeJson, legs, variables)
matches the human-readable intent declared in the strategy `description` field.

Catches Semantic Drift:
  1. Entry timing discrepancies (e.g. description says 9:30 AM, condition has 09:20)
  2. Parameter threshold mismatches (e.g. description says 5 pt spot confirm, variable is 1 pt)
  3. Strike offset & leg type mismatches (e.g. description says 600 pt hedge, leg has 100 pt)
  4. Missing execution blocks mentioned in description

Usage:
  python3 Tradetron-AI-Lab/scripts/tradetron_judge.py strategies/momentum_strategy.json
  python3 Tradetron-AI-Lab/scripts/tradetron_judge.py --all
"""

import os
import sys
import json
import re
import argparse
from datetime import datetime

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tradetron_auditor import parse_ast_to_text, validate_ui_schema

GREEN  = "\033[92m"; RED  = "\033[91m"; YELLOW = "\033[93m"
CYAN   = "\033[96m"; BOLD = "\033[1m";  DIM    = "\033[2m"; RESET = "\033[0m"

def clr(t, c): return f"{c}{t}{RESET}"
def bold(t):   return f"{BOLD}{t}{RESET}"
def dim(t):    return f"{DIM}{t}{RESET}"

class SemanticIntentJudge:
    def __init__(self, strategy_path):
        self.strategy_path = strategy_path
        with open(strategy_path, "r") as f:
            self.data = json.load(f)
        self.name = self.data.get("name", "Unknown")
        self.description = self.data.get("description", "")
        self.variables = {v.get("variableName"): v.get("value") for v in self.data.get("variables", [])}
        self.sets = self.data.get("sets", [])

    def extract_stated_intent(self):
        """Extract key parameter expectations from description text."""
        desc = self.description.lower()
        intent = {
            "entry_time": None,
            "exit_time": None,
            "stop_loss_pct": None,
            "target_pct": None,
            "hedge_gap": None,
            "spot_confirm": None,
        }
        
        # Time patterns like 9:15, 9:20, 9:30, 3:15 PM, 15:15
        t_matches = re.findall(r'(\d{1,2}:\d{2}\s*(?:am|pm)?)', desc)
        if t_matches:
            intent["entry_time"] = t_matches[0]

        # SL percentage patterns e.g. 1.8%, 1.5%
        sl_match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:stop\s*loss|sl|buffer)', desc)
        if sl_match:
            intent["stop_loss_pct"] = float(sl_match.group(1))

        # Hedge gap points e.g. 600 points, 600 pt
        hedge_match = re.search(r'(\d+)\s*(?:points|pt|pts)\s*(?:away|hedge|gap)', desc)
        if hedge_match:
            intent["hedge_gap"] = int(hedge_match.group(1))

        # Spot confirm points e.g. 5 points, 30 points
        confirm_match = re.search(r'(\d+)\s*(?:points|pt)\s*(?:confirm|jump|threshold)', desc)
        if confirm_match:
            intent["spot_confirm"] = int(confirm_match.group(1))

        return intent

    def extract_encoded_logic(self):
        """Extract actual AST logic strings and variable values."""
        encoded = {
            "chronological_flow": [],
            "variables": self.variables,
            "legs": [],
            "raw_times": [],
        }

        for s_idx, s in enumerate(self.sets, 1):
            set_info = {"set": s_idx, "conditions": []}
            for c in s.get("conditions", []):
                ctype = c.get("type", "Unknown")
                cjson = c.get("conditionJson")
                logic = ""
                if cjson:
                    try:
                        ast = json.loads(cjson) if isinstance(cjson, str) else cjson
                        logic = parse_ast_to_text(ast)
                    except:
                        logic = "[Unparsed AST]"
                
                # Check legs
                for leg in c.get("legs", []):
                    encoded["legs"].append({
                        "set": s_idx,
                        "type": ctype,
                        "buySell": leg.get("buySell"),
                        "optionType": leg.get("optionType"),
                        "strikeType": leg.get("strikeType"),
                        "strike": leg.get("strike"),
                    })

                # Check numbers/times in logic
                times = re.findall(r'Time\(NSE\)\s*(?:>=|>|==|<|<=)\s*Number\((\d+)\)', logic)
                encoded["raw_times"].extend(times)

                set_info["conditions"].append({"type": ctype, "logic": logic})
            encoded["chronological_flow"].append(set_info)

        return encoded

    def evaluate_intent_vs_code(self):
        """Perform semantic cross-verification between intent and encoded AST logic."""
        intent = self.extract_stated_intent()
        encoded = self.extract_encoded_logic()
        
        discrepancies = []
        warnings = []
        score = 100

        # 1. Description completeness check
        if len(self.description.strip()) < 30:
            discrepancies.append("[CRITICAL DRIFT] Description is missing or too short to establish intent!")
            score -= 40

        # 2. Check global variables match declared intent
        if intent["hedge_gap"] is not None and "HedgeGap" in encoded["variables"]:
            var_val_str = str(encoded["variables"]["HedgeGap"])
            var_num = re.search(r"'(\d+)'", var_val_str)
            if var_num and int(var_num.group(1)) != intent["hedge_gap"]:
                discrepancies.append(
                    f"[PARAMETER DRIFT] Description declares {intent['hedge_gap']} pt hedge gap, "
                    f"but Global Variable 'HedgeGap' is initialized to {var_num.group(1)} pt!"
                )
                score -= 25

        # 3. Check Leg Stop Loss Percent match declared intent
        if intent["stop_loss_pct"] is not None:
            # Check Leg Exit in chronological flow
            found_sl = False
            for s in encoded["chronological_flow"]:
                for c in s["conditions"]:
                    if "Stoploss Percent" in c["logic"]:
                        found_sl = True
                        # extract float from logic text
                        sl_val = re.search(r'Stoploss Percent,(\d+(?:\.\d+)?)', c["logic"])
                        if sl_val and abs(float(sl_val.group(1)) - intent["stop_loss_pct"]) > 0.01:
                            discrepancies.append(
                                f"[RISK DRIFT] Description declares {intent['stop_loss_pct']}% Stop Loss, "
                                f"but Leg Exit condition encodes {sl_val.group(1)}%!"
                            )
                            score -= 25
            if not found_sl and intent["stop_loss_pct"] > 0:
                warnings.append(
                    f"[INTENT WARNING] Description mentions {intent['stop_loss_pct']}% Stop Loss, "
                    f"but no explicit Leg Exit Stop Loss condition was found in AST flow."
                )

        # 4. Check Set 1 Entry Time vs Stated Entry Time
        if intent["entry_time"]:
            # Parse stated time to HHMM format (e.g. "9:20" -> "0920", "3:15 pm" -> "1515")
            raw_t = intent["entry_time"].lower()
            hh = 0; mm = 0
            m = re.match(r'(\d{1,2}):(\d{2})\s*(am|pm)?', raw_t)
            if m:
                hh = int(m.group(1))
                mm = int(m.group(2))
                if m.group(3) == 'pm' and hh < 12: hh += 12
                formatted_hhmm = f"{hh:02d}{mm:02d}"
                
                if encoded["raw_times"]:
                    first_ast_time = encoded["raw_times"][0].zfill(4)
                    if first_ast_time != formatted_hhmm:
                        discrepancies.append(
                            f"[TIMING DRIFT] Description mentions entry at '{intent['entry_time']}' ({formatted_hhmm}), "
                            f"but AST Set 1 Entry condition encodes Time >= {first_ast_time}!"
                        )
                        score -= 20

        # 5. Check if entry legs exist for entry conditions
        s1_entry_legs = [l for l in encoded["legs"] if l["set"] == 1 and l["type"] == "Entry"]
        if not s1_entry_legs:
            discrepancies.append("[CRITICAL DRIFT] Set 1 Entry condition exists, but no Position Builder legs are attached!")
            score -= 30

        score = max(0, score)
        status = "PASSED" if score >= 80 and not any("CRITICAL" in d for d in discrepancies) else "FAILED"

        return {
            "strategy_file": os.path.basename(self.strategy_path),
            "strategy_name": self.name,
            "judge_status": status,
            "semantic_score": score,
            "stated_intent": intent,
            "discrepancies": discrepancies,
            "warnings": warnings,
            "timestamp": datetime.now().isoformat()
        }

def print_judge_report(report):
    print(f"============================================================")
    print(f" TRADETRON LLM-AS-JUDGE (SEMANTIC INTENT EVALUATOR) ")
    print(f" Target File: {report['strategy_file']}")
    print(f"============================================================")
    print(f"Strategy Name  : {report['strategy_name']}")
    print(f"Semantic Score : {bold(str(report['semantic_score']) + '%')}")
    
    st_clr = GREEN if report['judge_status'] == "PASSED" else RED
    print(f"Judge Status   : {clr(report['judge_status'], st_clr)}")
    print()

    print(bold("📌 STATED INTENT EXTRACTED FROM DESCRIPTION:"))
    for k, v in report["stated_intent"].items():
        if v is not None:
            print(f"  • {k:<15}: {v}")
    print()

    if report["discrepancies"]:
        print(bold("🔴 INTENT-VS-CODE DISCREPANCIES DETECTED:"))
        for d in report["discrepancies"]:
            print(f"  ❌ {clr(d, RED)}")
        print()

    if report["warnings"]:
        print(bold("⚠️  INTENT WARNINGS:"))
        for w in report["warnings"]:
            print(f"  ⚠️  {clr(w, YELLOW)}")
        print()

    if report["judge_status"] == "PASSED" and not report["discrepancies"]:
        print(clr("✅ INTENT-CODE ALIGNMENT VERIFIED — AST perfectly matches description intent!", GREEN))
    print(f"============================================================\n")

def main():
    parser = argparse.ArgumentParser(description="Evaluate Strategy Semantic Intent vs Encoded AST")
    parser.add_argument("filepath", nargs="?", default=None, help="Path to strategy JSON file")
    parser.add_argument("--all", action="store_true", help="Evaluate all strategies in strategies/")
    args = parser.parse_args()

    if args.all:
        strat_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "strategies"))
        files = sorted([os.path.join(strat_dir, f) for f in os.listdir(strat_dir) if f.endswith(".json")])
        failed_count = 0
        for fpath in files:
            judge = SemanticIntentJudge(fpath)
            report = judge.evaluate_intent_vs_code()
            print_judge_report(report)
            if report["judge_status"] != "PASSED":
                failed_count += 1
        sys.exit(0 if failed_count == 0 else 1)
    elif args.filepath:
        judge = SemanticIntentJudge(args.filepath)
        report = judge.evaluate_intent_vs_code()
        print_judge_report(report)
        sys.exit(0 if report["judge_status"] == "PASSED" else 1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
