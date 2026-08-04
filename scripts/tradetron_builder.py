import json
import random
import os

def generate_kid():
    return random.randint(1000, 9999)

# Mapping of human-readable expiry type to Tradetron tt_ macro
# Fix (Issue #8): Full expiry type map — no silent fallthrough to wrong expiry
EXPIRY_TYPE_MAP = {
    "Current Week":  "tt_curr_weekexpiry",
    "Next Week":     "tt_next_weekexpiry",
    "Current Month": "tt_curr_monthexpiry",
    "Next Month":    "tt_next_monthexpiry",
    "Far Month":     "tt_far_monthexpiry",
}

EXPIRY_SPEC_MAP = {
    "Current Week":  {"macro": "tt_curr_weekexpiry", "kw_name": "Current Week Expiry", "offset": "0"},
    "Next Week":     {"macro": "tt_curr_weekexpiry", "kw_name": "Current Week Expiry", "offset": "1"},
    "Current Month": {"macro": "tt_curr_monthexpiry", "kw_name": "Current Month Expiry", "offset": "0"},
    "Next Month":    {"macro": "tt_curr_monthexpiry", "kw_name": "Current Month Expiry", "offset": "1"},
    "Far Month":     {"macro": "tt_curr_monthexpiry", "kw_name": "Current Month Expiry", "offset": "2"},
}

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
    def __init__(
        self,
        instrument_symbol="NIFTY 50",
        option_type="CE",
        buy_sell="B",
        lots=1,
        strike="0",
        strike_type="ATM",
        strike_json=None,
        strike_display=None,
        expiry_type="Current Month",
        # Rule 28: exchange and instrumentType are mandatory (not None/null)
        exchange="NFO",
        instrument_id=1855,        # Rule 31: DB primary key (1855=NIFTY50, 1854=BANKNIFTY, 0=StockList)
        instrument_type="OPTIDX",  # Rule 28: "OPTIDX", "OPTSTK", "EQ", "FUT"
        product_type="NRML",
        is_overnight_protection="No",  # Rule 30: always "No" unless overnight strategy
    ):
        self.instrument_symbol = instrument_symbol
        self.option_type = option_type
        self.buy_sell = buy_sell
        self.lots = lots
        self.strike = strike
        self.strike_type = strike_type
        self.strike_json = strike_json
        self.strike_display = strike_display
        self.expiry_type = expiry_type
        self.exchange = exchange
        self.instrument_id = instrument_id
        self.instrument_type = instrument_type
        self.product_type = product_type
        self.is_overnight_protection = is_overnight_protection
        
    def to_dict(self):
        if self.expiry_type not in EXPIRY_SPEC_MAP:
            raise ValueError(
                f"Unsupported expiry_type '{self.expiry_type}'. "
                f"Valid values: {list(EXPIRY_SPEC_MAP.keys())}"
            )
        spec = EXPIRY_SPEC_MAP[self.expiry_type]

        expiry_macro_str = f"( {spec['macro']} ( '{self.instrument_symbol}', '{spec['offset']}' ) )"
        expiry_display_str = f"( {spec['kw_name']} ( '{self.instrument_symbol}', '{spec['offset']}' ) )"
        expiry_ast_obj = {
            "operator": "and",
            "operands": [
                {
                    "type": "rule",
                    "value": "builder-basic_rule_0",
                    "elements": [
                        {
                            "name": spec["kw_name"],
                            "kid": generate_kid(),
                            "params": [
                                {"type": "value", "value": self.instrument_symbol},
                                {"type": "value", "value": spec["offset"]}
                            ]
                        }
                    ]
                }
            ]
        }

        strike_disp_str = self.strike_display if self.strike_display else f"( {self.strike} )"

        return {
            # Rule 28: exchange, instrument (DB PK integer), instrumentType are mandatory
            "exchange": self.exchange,
            "instrument": self.instrument_id,
            "instrumentType": self.instrument_type,
            "underlyingSymbol": self.instrument_symbol,
            "list": 0,
            "optionType": self.option_type,
            "buySell": self.buy_sell,
            "productType": self.product_type,

            # Expiry — Full AST & Display string generation for Strike Fx binding
            "expiryType": self.expiry_type,
            "expiry": expiry_macro_str,
            "expiryJson": json.dumps(expiry_ast_obj),
            "expiryDisplay": expiry_display_str,

            # Strike — Full AST & Display string generation
            "strikeType": self.strike_type,
            "strike": self.strike,
            "strikeJson": json.dumps(self.strike_json) if self.strike_json else None,
            "strikeDisplay": strike_disp_str,

            # Quantity — Rule 30: use tt_lots() macro with literal 'INSTRUMENT', NOT symbol string
            "qty": f"tt_lots({self.lots},'INSTRUMENT','{self.option_type}')",
            "qtyType": "Lots",
            "qtyDisplay": str(self.lots),
            "qtyJson": None,
            "qtyExprDisplay": None,  # Rule 30: key must exist (prevents UI Fx greyed fallback)

            # Rule 30: market orders — all price/sl fields must be null
            "limitPrice": None,
            "limitPriceJson": None,
            "targetLimit": None,
            "targetTrigger": None,
            "sLLimit": None,
            "sLTrigger": None,
            "sLTriggerJson": None,
            "entryTrigger": None,
            "entryLimit": None,

            # Rule 30: required UI rendering fields
            "isOvernightProtectionLeg": self.is_overnight_protection,
            "tmp": 0,
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
            "subType": "None",   # Rule 10: must be string "None", NOT empty string ""
            "visible": 1,
            "legs": [l.to_dict() for l in self.legs],
            "extra": {           # Rule 10: must be object with name/variables, NOT empty array []
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
        
    def export(self, filepath, base_template_path=None):
        # Fix (Issue #11): Resolve base_strategy.json relative to THIS script file,
        # not the current working directory. This makes it runnable from any location.
        scripts_dir = os.path.dirname(os.path.abspath(__file__))

        if base_template_path is None:
            base_template_path = os.path.join(scripts_dir, "base_strategy.json")
        elif not os.path.isabs(base_template_path):
            base_template_path = os.path.join(scripts_dir, base_template_path)

        with open(base_template_path, "r") as f:
            data = json.load(f)
            
        data["name"] = self.name
        if self.description:
            data["description"] = self.description
        data["sets"] = [s.to_dict() for s in self.sets]

        # Rule 8: Universal Exit MUST be in the LAST set's conditions array
        if self.universal_exit and len(data["sets"]) > 0:
            data["sets"][-1]["conditions"].append(self.universal_exit.to_dict())
        
        if self.variables:
            data["variables"] = [v.to_dict() for v in self.variables]

        # Fix (Issue #11): Resolve output filepath relative to strategies/ dir if relative
        if not os.path.isabs(filepath):
            strategies_dir = os.path.normpath(os.path.join(scripts_dir, "..", "strategies"))
            filepath = os.path.join(strategies_dir, os.path.basename(filepath))
            
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        print(f"Strategy exported to: {os.path.abspath(filepath)}")
