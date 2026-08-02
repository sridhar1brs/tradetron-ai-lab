import json
import random

def generate_kid():
    return random.randint(1000, 9999)

class Keyword:
    def __init__(self, name, *params):
        self.name = name
        self.kid = generate_kid()
        self.params = []
        for p in params:
            if isinstance(p, Keyword):
                self.params.append({
                    "type": "keyword",
                    "keyword": p.to_dict()
                })
            else:
                self.params.append({
                    "type": "value",
                    "value": str(p)
                })
                
    def to_dict(self):
        return {
            "name": self.name,
            "kid": self.kid,
            "params": self.params
        }
        
    def __gt__(self, other): return Rule(self, ">", other)
    def __lt__(self, other): return Rule(self, "<", other)
    def __ge__(self, other): return Rule(self, ">=", other)
    def __le__(self, other): return Rule(self, "<=", other)
    def __eq__(self, other): return Rule(self, "==", other)
    
class Operator:
    def __init__(self, name):
        self.name = name
        self.params = []
        
    def to_dict(self):
        return {
            "name": self.name,
            "params": self.params
        }

class Rule:
    def __init__(self, left, op, right):
        self.left = left if isinstance(left, Keyword) else Keyword("Number", left)
        self.op = Operator(op)
        self.right = right if isinstance(right, Keyword) else Keyword("Number", right)
        
    def to_dict(self, index):
        return {
            "type": "rule",
            "value": f"builder-basic_rule_{index}",
            "elements": [
                self.left.to_dict(),
                self.op.to_dict(),
                self.right.to_dict()
            ]
        }

class ConditionGroup:
    def __init__(self, operator="and"):
        self.operator = operator
        self.rules = []
    
    def add_rule(self, rule):
        self.rules.append(rule)
        
    def to_dict(self, index):
        return {
            "type": "group",
            "value": f"builder-basic_group_{index}",
            "children": {
                "operator": self.operator,
                "operands": [r.to_dict(i) for i, r in enumerate(self.rules)]
            }
        }

class Leg:
    def __init__(self, instrument_symbol="NIFTY 50", option_type="CE", buy_sell="B", lots=1, strike="ATM", strike_type="Strike", strike_json=None, strike_display=None, expiry_type="Current Month"):
        self.instrument_symbol = instrument_symbol
        self.option_type = option_type
        self.buy_sell = buy_sell
        self.lots = lots
        self.strike = strike
        self.strike_type = strike_type
        self.strike_json = strike_json
        self.strike_display = strike_display
        self.expiry_type = expiry_type
        
    def to_dict(self):
        expiry_func = "tt_curr_weekexpiry" if self.expiry_type == "Current Week" else "tt_curr_monthexpiry"
        return {
            "instrument": 1855,
            "list": 0,
            "optionType": self.option_type,
            "expiryType": self.expiry_type,
            "expiry": f"{expiry_func}('{self.instrument_symbol}')",
            "expiryJson": None,
            "expiryDisplay": None,
            "strikeType": self.strike_type,
            "strike": self.strike,
            "strikeJson": json.dumps(self.strike_json) if self.strike_json else None,
            "strikeDisplay": self.strike_display,
            "qty": f"tt_lots({self.lots},'INSTRUMENT','{self.option_type}')",
            "qtyType": "Lots",
            "qtyDisplay": str(self.lots),
            "qtyJson": None,
            "buySell": self.buy_sell,
            "productType": "NRML",
            "underlyingSymbol": self.instrument_symbol,
            # Advanced fields observed from complex JSONs:
            "targetLimit": None,
            "targetTrigger": None,
            "sLLimit": None,
            "sLTrigger": None
        }

class Condition:
    def __init__(self, ctype="Entry", operator="and"):
        # Valid ctypes: Entry, Exit, Universal Exit, Repair Once, Repair Continuous
        self.type = ctype
        self.operator = operator
        self.rules = []
        self.legs = []
        
    def add_rule(self, rule):
        # Can be a single Rule or a ConditionGroup for OR logic
        self.rules.append(rule)
        
    def add_leg(self, leg):
        self.legs.append(leg)
        
    def to_dict(self):
        condition_json = {
            "operator": self.operator,
            "operands": [r.to_dict(i) for i, r in enumerate(self.rules)]
        }
        
        return {
            "type": self.type,
            "conditionValue": None,
            "conditionJson": json.dumps(condition_json),
            "conditionDisplay": None,
            "subType": "None",
            "visible": 1,
            "legs": [l.to_dict() for l in self.legs],
            "extra": {
                "name": None,
                "variables": []
            }
        }

class SetBlock:
    def __init__(self, set_number=1):
        self.set_number = set_number
        self.conditions = []
        
    def add_condition(self, condition):
        self.conditions.append(condition)
        
    def to_dict(self):
        return {
            "list": 0,
            "name": None,
            "conditions": [c.to_dict() for c in self.conditions]
        }

class Variable:
    def __init__(self, name, value_str):
        self.name = name
        self.value_str = str(value_str)
        
    def to_dict(self):
        var_json = {
            "operator": "and",
            "operands": [
                {
                    "type": "rule",
                    "value": "builder-basic_rule_0",
                    "elements": [
                        {
                            "name": "Number",
                            "kid": generate_kid(),
                            "params": [
                                {"type": "value", "value": self.value_str}
                            ]
                        }
                    ]
                }
            ]
        }
        return {
            "variableName": self.name,
            "value": f"( tt_Number ( '{self.value_str}' )  )",
            "display": f"( Number ( '{self.value_str}' )  )",
            "json": json.dumps(var_json)
        }

class Strategy:
    def __init__(self, name="AI Generated Strategy", description=""):
        self.name = name
        self.description = description
        self.sets = []
        self.variables = []
        self.universal_exit = None
        
    def add_set(self, s):
        self.sets.append(s)
        
    def add_variable(self, v):
        self.variables.append(v)
        
    def set_universal_exit(self, condition):
        self.universal_exit = condition
        
    def export(self, filepath, base_template_path="base_strategy.json"):
        with open(base_template_path, "r") as f:
            data = json.load(f)
            
        data["name"] = self.name
        if self.description:
            data["description"] = self.description
        data["sets"] = [s.to_dict() for s in self.sets]
        if self.universal_exit and len(data["sets"]) > 0:
            data["sets"][-1]["conditions"].append(self.universal_exit.to_dict())
        
        if self.variables:
            data["variables"] = [v.to_dict() for v in self.variables]
            
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
