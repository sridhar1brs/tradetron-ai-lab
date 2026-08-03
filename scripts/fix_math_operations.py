import json
import copy

def fix_math_operation_params(node):
    """
    Recursively scans the AST and fixes Math Operation params.
    Changes [Operand1, Operator, Operand2] to [Operand1, Operand2, Operator].
    """
    if isinstance(node, dict):
        if node.get("name") == "Math Operation" and "params" in node:
            params = node["params"]
            if len(params) == 3:
                # Check if the middle param is a simple operator value
                mid = params[1]
                if mid.get("type") == "value" and mid.get("value") in ["+", "-", "*", "/"]:
                    # Swap index 1 and 2
                    params[1], params[2] = params[2], params[1]
                    print(f"Fixed Math Operation node containing operator '{mid.get('value')}'.")
        
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                fix_math_operation_params(value)
    elif isinstance(node, list):
        for item in node:
            if isinstance(item, (dict, list)):
                fix_math_operation_params(item)

def main():
    filepath = '../strategies/momentum_strategy.json'
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    original = copy.deepcopy(data)
    
    # The condition AST strings are packed in JSON string literals. We need to unpack them, fix them, and pack them back.
    for s in data.get('sets', []):
        for c in s.get('conditions', []):
            if 'conditionJson' in c and c['conditionJson']:
                ast = json.loads(c['conditionJson'])
                fix_math_operation_params(ast)
                c['conditionJson'] = json.dumps(ast)
                
    if data != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print("Successfully fixed and saved momentum_strategy.json.")
    else:
        print("No changes were needed or made.")

if __name__ == "__main__":
    main()
