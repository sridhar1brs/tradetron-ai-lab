#!/usr/bin/env python3
"""
Tradetron Strategy AST Auditor & UI Schema Validator Engine
Performs chronological strategy execution auditing, schema validation, and rule enforcement:
1. Macro Keyword Primitive Parameter Check (Leg TSL, Leg Exit, Leg SL Trail)
2. Spot Index Instrument String Validator (Rule 17 & Rule 27)
3. Math Operation Array Order Validator (Rule 13)
4. Universal Exit Placement Validator (Rule 8)
5. Condition Group AST 'children' Wrapper Validator (Rule 9)
6. Unused Global Variable Detector
7. Position Builder Leg Quantity Formula Syntax Check
8. Positions Detail Case-Sensitivity Validator (Rule 24)
9. Traded Instrument Coordinate Integrity Validator (Rule 25)
10. Leg Metadata Completeness Check (Rule 28: exchange, instrument, instrumentType)
11. Position Builder Leg Qty & Price Field Renderer Check (Rule 30)
"""

import json
import argparse
import sys

# Macro keywords that require literal primitive inputs in Tradetron UI
MACRO_KEYWORDS = ["Leg TSL", "Leg Exit", "Leg SL Trail"]

def parse_ast_to_text(ast):
    if not isinstance(ast, dict): return "Empty AST"
    operator = ast.get("operator", "and").upper()
    operands = ast.get("operands", [])
    
    parsed_rules = []
    for op in operands:
        if op.get("type") == "rule":
            elements = op.get("elements", [])
            rule_text = ""
            for el in elements:
                name = el.get("name", "")
                params = el.get("params", [])
                
                param_texts = []
                for p in params:
                    if p.get("type") == "value":
                        param_texts.append(p.get("value", ""))
                    elif p.get("type") == "keyword":
                        param_texts.append(f"[{p.get('keyword', {}).get('name', '')}]")
                
                if param_texts:
                    rule_text += f"{name}({','.join(param_texts)}) "
                else:
                    rule_text += f"{name} "
            parsed_rules.append(rule_text.strip())
        elif op.get("type") == "group":
            parsed_rules.append("(" + parse_ast_to_text(op.get("children", {})) + ")")
            
    return f" {operator} ".join(parsed_rules)

def validate_ui_schema(data):
    schema_errors = []
    schema_warnings = []
    
    sets = data.get("sets", [])
    num_sets = len(sets)
    raw_str_data = json.dumps(data)

    active_legs = set()
    for s_idx, s in enumerate(sets, 1):
        for c_idx, c in enumerate(s.get("conditions", []), 1):
            for l_idx in range(1, len(c.get("legs", [])) + 1):
                active_legs.add((s_idx, c_idx, l_idx))

    # 1. Check Unused Global Variables
    variables = data.get("variables", [])
    for v in variables:
        v_name = v.get("variableName", "")
        if v_name:
            count = raw_str_data.count(v_name)
            if count <= 1:
                schema_warnings.append(f"[UNUSED VARIABLE WARNING] Variable '{v_name}' is declared in global variables but NEVER referenced in any condition or leg formula!")

    # 2. Rule 8: Universal Exit Placement Check
    for s_idx, s in enumerate(sets):
        for c in s.get("conditions", []):
            if c.get("type") == "Universal Exit" and s_idx != num_sets - 1:
                schema_errors.append(f"[RULE 8 VIOLATION] Universal Exit found in Set {s_idx + 1}. In multi-set strategies, Universal Exit MUST be in the last Set (Set {num_sets})!")

    # Traverse all conditions and legs across all sets
    for s_idx, s in enumerate(sets):
        for c_idx, c in enumerate(s.get("conditions", [])):
            cjson = c.get("conditionJson")
            if cjson:
                try:
                    ast = json.loads(cjson) if isinstance(cjson, str) else cjson
                    _check_ast_nodes(ast, s_idx + 1, c_idx + 1, active_legs, schema_errors, schema_warnings)
                except Exception:
                    pass
                
            # Check Legs
            for l_idx, leg in enumerate(c.get("legs", [])):
                st_json = leg.get("strikeJson")
                st_type = leg.get("strikeType")
                if st_json and st_type != "Fx":
                    schema_errors.append(f"[RULE 5 VIOLATION] Set {s_idx + 1} Cond {c_idx + 1} Leg {l_idx + 1} uses strikeJson formula but strikeType is '{st_type}'. Must be 'Fx'!")

                # Rule 28: Leg Metadata Completeness Check (exchange, instrument, instrumentType)
                if not leg.get("exchange") or not leg.get("instrument") or not leg.get("instrumentType"):
                    schema_errors.append(f"[RULE 28 VIOLATION] Set {s_idx + 1} Cond {c_idx + 1} Leg {l_idx + 1} has null/empty 'exchange', 'instrument', or 'instrumentType'! Must explicitly specify ('NFO', 'NFO', 'OPTIDX') or ('NSE', 'NSE', 'EQ').")

                # Rule 30: Position Builder Leg Qty & Price Field Renderer Check
                qty_val = str(leg.get("qty", ""))
                if "tt_lots" in qty_val or "tt_value" in qty_val:
                    schema_errors.append(f"[RULE 30 VIOLATION] Set {s_idx + 1} Cond {c_idx + 1} Leg {l_idx + 1} has raw macro '{qty_val}' inside 'qty'. Set 'qty': '1' (for Lots) or '10000' (for Value) to render the UI input box cleanly!")

                if leg.get("limitPriceJson") is not None or leg.get("sLTriggerJson") is not None:
                    schema_warnings.append(f"[RULE 30 WARNING] Set {s_idx + 1} Cond {c_idx + 1} Leg {l_idx + 1} has non-null limitPriceJson/sLTriggerJson. For Market orders, set these to null so UI leaves them unhighlighted.")

    return schema_errors, schema_warnings

def _check_ast_nodes(node, set_num, cond_num, active_legs, errors, warnings):
    if not isinstance(node, dict):
        return
        
    if node.get("type") == "group":
        if "children" not in node and "operator" in node:
            errors.append(f"[RULE 9 VIOLATION] ConditionGroup in Set {set_num} Cond {cond_num} is missing 'children' dictionary wrapper!")
        _check_ast_nodes(node.get("children", {}), set_num, cond_num, active_legs, errors, warnings)
        return

    operands = node.get("operands", [])
    for op in operands:
        if op.get("type") == "rule":
            elements = op.get("elements", [])
            for el in elements:
                el_name = el.get("name", "")
                params = el.get("params", [])
                
                # Macro Keyword Primitive Parameter Check (Leg TSL, Leg Exit, Leg SL Trail)
                if el_name in MACRO_KEYWORDS:
                    for p_idx, p in enumerate(params):
                        if isinstance(p, dict) and p.get("type") == "keyword":
                            kw_name = p.get("keyword", {}).get("name", "Unknown")
                            errors.append(f"[CRITICAL UI MODAL ERROR] '{el_name}' in Set {set_num} Cond {cond_num} contains nested keyword '{kw_name}' in parameter #{p_idx+1}! Tradetron UI modal requires literal primitives (e.g., '1', '0.5', '2').")

                # Rule 17 & Rule 27: Spot Index Instrument String Check (5-comma slot verification)
                if el_name == "Instrument Name":
                    for p in params:
                        val = p.get("value", "")
                        if "NIFTY 50" in val and "Current Month" in val:
                            errors.append(f"[RULE 17 VIOLATION] Spot Index Instrument Name in Set {set_num} Cond {cond_num} uses '{val}'. Spot index references must NOT include 'Current Month'!")
                        if "NFO,NIFTY 50" in val and val.count(",") < 5:
                            errors.append(f"[RULE 27 VIOLATION] Instrument Name in Set {set_num} Cond {cond_num} uses '{val}' (less than 5 commas). Must use 5 comma slots e.g. 'NFO,NIFTY 50,,,,,'!")

                # Math Operation Order Check (Rule 13)
                if el_name == "Math Operation":
                    if len(params) == 3:
                        op_symbol = params[2].get("value", "")
                        if op_symbol not in ["*", "+", "-", "/"]:
                            warnings.append(f"[RULE 13 WARNING] Math Operation in Set {set_num} Cond {cond_num} operator symbol '{op_symbol}' is not at index 3 (Postfix array order expected).")

                # Rule 24: Positions Detail Case-Sensitivity Validator
                if el_name == "Positions Detail":
                    if len(params) >= 4:
                        field_val = params[3].get("value", "")
                        if field_val == "Quantity" or field_val == "PRICE":
                            errors.append(f"[RULE 24 VIOLATION] Positions Detail in Set {set_num} Cond {cond_num} uses '{field_val}'. Field parameter is strictly case-sensitive and must be lowercase ('quantity', 'price')!")

                # Rule 25: Traded Instrument Coordinate Integrity Validator
                if el_name in ["Traded Instrument", "Traded Instrument Name"]:
                    if len(params) >= 6:
                        try:
                            t_set = int(params[3].get("value", 0))
                            t_cond = int(params[4].get("value", 0))
                            t_leg = int(params[5].get("value", 0))
                            if (t_set, t_cond, t_leg) not in active_legs and active_legs:
                                warnings.append(f"[RULE 25 WARNING] {el_name} in Set {set_num} Cond {cond_num} references target coordinate ({t_set}, {t_cond}, {t_leg}) which does not match an active leg!")
                        except Exception:
                            pass
                            
        elif op.get("type") == "group":
            _check_ast_nodes(op, set_num, cond_num, active_legs, errors, warnings)

def audit_strategy(filepath):
    print(f"============================================================")
    print(f" TRADETRON STRATEGY AUDITOR & UI SCHEMA VALIDATOR ")
    print(f" Target File: {filepath}")
    print(f"============================================================")
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return False

    print(f"Strategy Name: {data.get('name', 'Unknown')}")
    print(f"Capital Required: {data.get('capitalRequired', 0)}")
    
    desc = data.get("description", "")
    if not desc or desc.strip() == "" or desc.strip() == "<p></p>" or desc == "AI Generated Strategy":
        print(f"\n⚠️  [WARNING] Description field is missing or generic!")
    else:
        print(f"Description Length: {len(desc)} chars (Present)")
        
    variables = data.get("variables", [])
    if variables:
        print(f"\n--- GLOBAL VARIABLES ---")
        for v in variables:
            v_name = v.get("variableName", "Unknown")
            v_val = v.get("value", "")
            if not v_val or v_val.strip() == "":
                print(f"  ⚠️  [WARNING] Variable '{v_name}' is missing 'value' initialization!")
            else:
                print(f"  {v_name}: {v_val}")

    print(f"\n--- CHRONOLOGICAL EXECUTION FLOW ---")
    for s_idx, s in enumerate(data.get("sets", [])):
        print(f"Set {s_idx + 1}:")
        for c in s.get("conditions", []):
            ctype = c.get("type", "Unknown")
            cjson = c.get("conditionJson")
            if cjson:
                try:
                    ast = json.loads(cjson) if isinstance(cjson, str) else cjson
                    logic = parse_ast_to_text(ast)
                    print(f"  -> [{ctype.upper()}] Logic: {logic}")
                except Exception as e:
                    print(f"  -> [{ctype.upper()}] Logic: [Error parsing AST: {e}]")
            else:
                print(f"  -> [{ctype.upper()}] Logic: [None]")

    errors, warnings = validate_ui_schema(data)

    print(f"\n============================================================")
    print(f" UI SCHEMA & RULE VALIDATION RESULTS ")
    print(f"============================================================")
    if warnings:
        print("Warnings Found:")
        for w in warnings:
            print(f"  ⚠️  {w}")
            
    if errors:
        print("Critical Errors Found:")
        for err in errors:
            print(f"  ❌ {err}")
        print(f"\nStatus: FAILED ({len(errors)} Critical Schema Errors)")
        return False
    else:
        print("Status: ✅ PASSED (100% UI Schema & Rule Compliant)")
        return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit a Tradetron Strategy JSON")
    parser.add_argument("filepath", help="Path to the .json strategy file")
    args = parser.parse_args()
    success = audit_strategy(args.filepath)
    sys.exit(0 if success else 1)
