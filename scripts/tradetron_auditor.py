import json
import argparse
import sys

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
                
                # Check if param has nested keyword
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
            parsed_rules.append("(" + parse_ast_to_text(op) + ")")
            
    return f" {operator} ".join(parsed_rules)

def audit_strategy(filepath):
    print(f"=== STRATEGY AUDIT: {filepath} ===\n")
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return

    print(f"Strategy Name: {data.get('name', 'Unknown')}")
    print(f"Capital Required: {data.get('capitalRequired', 0)}")
    
    desc = data.get("description", "")
    if not desc or desc.strip() == "" or desc.strip() == "<p></p>" or desc == "AI Generated Strategy":
        print(f"\n[WARNING] Strategy is missing a descriptive metadata field (description is blank or generic)!")
    else:
        print(f"\nDescription Length: {len(desc)} chars (Present)")
        
    variables = data.get("variables", [])
    if variables:
        print(f"\n--- GLOBAL VARIABLES ---")
        for v in variables:
            v_name = v.get("variableName", "Unknown")
            v_val = v.get("value", "")
            if not v_val or v_val.strip() == "":
                print(f"  [WARNING] Variable '{v_name}' is missing 'value' initialization!")
            else:
                print(f"  {v_name}: {v_val}")
    print("")

    for s_idx, s in enumerate(data.get("sets", [])):
        print(f"--- SET {s_idx + 1} ---")
        for c in s.get("conditions", []):
            ctype = c.get("type", "Unknown")
            print(f"  -> [{ctype.upper()} CONDITION]")
            
            cjson = c.get("conditionJson")
            if cjson:
                try:
                    ast = json.loads(cjson)
                    logic = parse_ast_to_text(ast)
                    print(f"       Logic: {logic}")
                except Exception as e:
                    print(f"       Logic: [Error parsing AST: {e}]")
            else:
                print("       Logic: [None]")
                
            legs = c.get("legs", [])
            if legs:
                print(f"       Legs ({len(legs)}):")
                for l_idx, leg in enumerate(legs):
                    bs = "BUY" if leg.get("buySell", "B") == "B" else "SELL"
                    opt = leg.get("optionType", "Unknown")
                    strike = leg.get("strikeType", "")
                    if strike == "Fx":
                        strike = leg.get("strikeDisplay", "Formula")
                    qty = leg.get("qtyDisplay", "1")
                    print(f"         {l_idx+1}. {bs} {opt} (Qty: {qty}, Strike: {strike})")
            else:
                print("       Legs: [None]")
        print("")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit a Tradetron Strategy JSON")
    parser.add_argument("filepath", help="Path to the .json strategy file")
    args = parser.parse_args()
    audit_strategy(args.filepath)
