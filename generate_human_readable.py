import json

filepath = "/Users/srbalakrishnan/Algo_Lab/Tradetron_AI_KB/impot_export/Corrected_Iron_Fly.json"
with open(filepath, "r") as f:
    data = json.load(f)

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
                        param_texts.append(f"'{p.get('value', '')}'")
                    elif p.get("type") == "keyword":
                        kname = p.get('keyword', {}).get('name', '')
                        kparams = [f"'{x.get('value', '')}'" for x in p.get('keyword', {}).get('params', []) if x.get('type') == 'value']
                        param_texts.append(f"{kname} ( {', '.join(kparams)} )")
                
                if param_texts:
                    rule_text += f"{name} ( {', '.join(param_texts)} ) "
                else:
                    rule_text += f"{name} "
            parsed_rules.append(rule_text.strip())
        elif op.get("type") == "group":
            child_ast = op.get("children", op) # Fallback to op just in case
            parsed_rules.append("( " + parse_ast_to_text(child_ast) + " )")
            
    return f" {operator} ".join(parsed_rules)

out = ""
for s_idx, s in enumerate(data.get("sets", [])):
    for c_idx, c in enumerate(s.get("conditions", [])):
        ctype = c.get("type", "")
        if ctype == "Universal Exit":
            continue
        
        # Map Entry to E, Exit to Ex, Repair Once to R
        ctype_short = "E"
        if ctype == "Exit": ctype_short = "Ex"
        elif "Repair" in ctype: ctype_short = "R"
        
        c_label = f"S{s_idx+1} {ctype_short}"
        out += f"{c_label} - Condition:\n"
        
        cjson = c.get("conditionJson")
        if cjson:
            try:
                ast = json.loads(cjson)
                logic = parse_ast_to_text(ast)
                out += f"    ( {logic} )\n"
            except:
                out += "    ( Error parsing )\n"
        else:
            out += "    ( None )\n"
            
        legs = c.get("legs", [])
        if legs:
            out += f"{c_label} - Positions\n"
            out += "    Action\tUnderlying\tStrike\tType\tExpiry\tQty\tPrice\n"
            for leg in legs:
                action = "Buy" if leg.get("buySell") == "B" else "Sell"
                und = leg.get("underlyingSymbol", "NIFTY 50")
                strike_type = leg.get("strikeType", "ATM")
                strike_val = "ATM"
                if strike_type == "Fx":
                    s_ast = json.loads(leg.get("strikeJson", "{}"))
                    strike_val = "( " + parse_ast_to_text(s_ast) + " )"
                opt = leg.get("optionType", "")
                exp = leg.get("expiry", "")
                qty = leg.get("qtyDisplay", "1")
                price = ""
                out += f"    {action}\t{und}\t{strike_val}\t{opt}\t{exp}\t{qty}\t{price}\n"
    out += "\n"

# Parse Universal Exit
if len(data.get("sets", [])) > 0:
    for c in data["sets"][-1].get("conditions", []):
        if c.get("type") == "Universal Exit":
            out += "Universal Exit - Condition:\n"
            cjson = c.get("conditionJson")
            if cjson:
                try:
                    ast = json.loads(cjson)
                    logic = parse_ast_to_text(ast)
                    out += f"    ( {logic} )\n"
                except:
                    out += "    ( Error parsing )\n"
            else:
                out += "    ( None )\n"
            out += "\n"

with open("/Users/srbalakrishnan/Algo_Lab/Tradetron_AI_KB/impot_export/Corrected_Iron_Fly_Explanation.md", "w") as f:
    f.write("```text\n")
    f.write(out)
    f.write("```\n")

print("Generated readable format.")
