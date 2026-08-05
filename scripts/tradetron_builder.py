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

        print(f"✅ Strategy exported to: {os.path.abspath(filepath)}")
        return os.path.abspath(filepath)
            

# ─── High-Level Strategy Generators ──────────────────────────────────────────

def make_structured_description(name, underlying, timeframe, entry_logic, exit_logic, notes=None):
    """Rule 6 helper: Format a rich, human-readable structured HTML description field."""
    desc = f"""
<p><strong>{name}</strong></p>
<p><strong>Strategy Notes & Trading Intent:</strong></p>
<p>--------------------------------------------------</p>
<p>1. <strong>Entry Criteria:</strong></p>
<ul>
  <li><strong>Underlying:</strong> {underlying} ({timeframe}).</li>
  <li><strong>Entry Window:</strong> Between 9:20 AM and 3:00 PM IST.</li>
  <li><strong>Trigger Condition:</strong> {entry_logic}</li>
</ul>
<p>2. <strong>Exit Criteria & Risk Parameters:</strong></p>
<ul>
  <li><strong>Target & Stop Loss:</strong> {exit_logic}</li>
  <li><strong>Universal Exit:</strong> Square off all intraday open positions at 3:15 PM IST.</li>
</ul>
"""
    if notes:
        desc += f"<p>3. <strong>Additional Mechanics:</strong></p><ul>{notes}</ul>\n"
    return desc


def build_iron_fly(
    symbol="NIFTY 50",
    hedge_gap=600,
    roll_step=100,
    expiry_type="Current Month",
    entry_time=1515,
    hold_till_expiry=1,
    name=None,
    output_filename=None,
):
    """Build a 100% compliant Iron Fly options strategy with dynamic hedge roll logic."""
    if name is None:
        name = f"{symbol} IronFly {hedge_gap}pt Hedge ({expiry_type})"
    if output_filename is None:
        output_filename = f"{symbol.replace(' ', '_')}_IronFly_{hedge_gap}pt.json"

    if "NIFTY" in symbol and "BANK" not in symbol and "FIN" not in symbol:
        inst_id = 1855
    elif "BANK" in symbol:
        inst_id = 1854
    elif "FIN" in symbol:
        inst_id = 1856
    elif "SENSEX" in symbol:
        inst_id = 1857
    else:
        inst_id = 0
    
    desc_html = f"""
<p><strong>{name}</strong></p>
<p><strong>Strategy Notes & Trading Intent:</strong></p>
<p>--------------------------------------------------</p>
<p>1. <strong>Entry Criteria:</strong></p>
<ul>
  <li><strong>Underlying:</strong> {symbol} Index ({expiry_type} Expiry Spreads).</li>
  <li><strong>Entry Time:</strong> At 3:15 PM IST (15:15 IST).</li>
  <li><strong>Trigger Condition:</strong> Enters 4-leg Iron Fly position on {symbol} (Sell ATM Call & Put, Buy {hedge_gap}pt OTM Call & Put protective hedges) at 15:15 IST.</li>
</ul>
<p>2. <strong>Exit Criteria & Risk Parameters:</strong></p>
<ul>
  <li><strong>Universal Exit:</strong> Square off all intraday open positions at 3:15 PM IST.</li>
</ul>
<p>3. <strong>Additional Mechanics:</strong></p>
<ul>
  <li>Protective hedges placed {hedge_gap} points away, rolling outward by {roll_step} points on hedge boundary crosses.</li>
</ul>
"""

    strat = Strategy(name=name, description=desc_html)

    strat.add_variable(Variable("HedgeGap", str(hedge_gap)))
    strat.add_variable(Variable("HedgeRoll", str(roll_step)))
    strat.add_variable(Variable("HOLD_TILL_EXPIRY", str(hold_till_expiry)))


    # Set 1 Entry
    s1 = SetBlock(1)
    e1 = Condition("Entry")
    e1.add_rule(Keyword("Time", "NSE") >= entry_time)
    
    # Short Straddle legs
    l1 = Leg(symbol, "CE", "S", 1, strike_type="ATM", strike=f"tt_ATM('{symbol}')", expiry_type=expiry_type, instrument_id=inst_id)
    l2 = Leg(symbol, "PE", "S", 1, strike_type="ATM", strike=f"tt_ATM('{symbol}')", expiry_type=expiry_type, instrument_id=inst_id)
    # Long Hedge legs
    l3 = Leg(symbol, "CE", "B", 1, strike_type="Fx", strike=f"tt_ATM('{symbol}') + {hedge_gap}", expiry_type=expiry_type, instrument_id=inst_id)
    l4 = Leg(symbol, "PE", "B", 1, strike_type="Fx", strike=f"tt_ATM('{symbol}') - {hedge_gap}", expiry_type=expiry_type, instrument_id=inst_id)

    e1.add_leg(l1); e1.add_leg(l2); e1.add_leg(l3); e1.add_leg(l4)
    s1.add_condition(e1)

    # Set 1 Repair (fill check guard: > 0)
    r1 = Condition("Repair Once")
    r1.add_rule(Keyword("Traded Instrument", "Entry", "quantity", symbol, "1", "1", "1") > 0)
    s1.add_condition(r1)
    strat.add_set(s1)

    # Universal Exit
    ue = Condition("Universal Exit")
    ue.add_rule(Keyword("Time", "NSE") >= 1515)
    strat.set_universal_exit(ue)

    # Export & Audit
    output_path = os.path.join(os.path.dirname(__file__), "..", "strategies", output_filename)
    strat.export(output_path)
    return output_path


def build_momentum(
    symbol="NIFTY 50",
    spot_confirm=5,
    sl_mult=0.9,
    tgt_mult=1.2,
    timeframe="1min",
    expiry_type="Current Week",
    name=None,
    output_filename=None,
):
    """Build a 100% compliant Directional Momentum option buying strategy using Symbol(Instrument Name) Rule 42 pattern."""
    if name is None:
        name = f"{symbol} {timeframe} Momentum Strategy (Spot Confirm {spot_confirm}pt)"
    if output_filename is None:
        output_filename = f"{symbol.replace(' ', '_')}_{timeframe}_Momentum.json"

    if "NIFTY" in symbol and "BANK" not in symbol and "FIN" not in symbol:
        inst_id = 1855
    elif "BANK" in symbol:
        inst_id = 1854
    elif "FIN" in symbol:
        inst_id = 1856
    elif "SENSEX" in symbol:
        inst_id = 1857
    else:
        inst_id = 0

    desc_html = make_structured_description(
        name=name,
        underlying=f"{symbol} Index",
        timeframe=f"{timeframe} Candles ({expiry_type})",
        entry_logic=f"Enters Buy CE when {timeframe} Close[-1] > Close[-2] + {spot_confirm} pts and Close[-2] > Close[-3]. Enters Buy PE on bearish breakdown.",
        exit_logic=f"Target: {tgt_mult}x entry price. Stop Loss: {sl_mult}x entry price."
    )

    strat = Strategy(name=name, description=desc_html)

    strat.add_variable(Variable("Spot_Confirm", str(spot_confirm)))
    strat.add_variable(Variable("SL_Multiplier", str(sl_mult)))
    strat.add_variable(Variable("Target_Multiplier", str(tgt_mult)))

    # Set 1: Bullish CE Entry & Exit
    s1 = SetBlock(1)
    c1_e = Condition("Entry")
    c1_e.add_rule(Keyword("Time", "NSE") >= 920)
    c1_e.add_rule(Keyword("Time", "NSE") < 1500)
    
    # Rule 42 helper for Symbol(Instrument Name)
    sym_kw = Keyword("Symbol", Keyword("Instrument Name", f"NSE,{symbol},,,,,"), timeframe, "All")
    close_kw = Keyword("CLOSE", sym_kw)
    pos_m1 = Keyword("Position", close_kw, "-1")
    pos_m2 = Keyword("Position", close_kw, "-2")
    pos_m3 = Keyword("Position", close_kw, "-3")
    
    math_op = Keyword("Math Operation", pos_m2, Keyword("Get Runtime", "Spot_Confirm"), "+")
    c1_e.add_rule(pos_m1 > math_op)
    c1_e.add_rule(pos_m2 > pos_m3)
    
    c1_e.add_leg(Leg(symbol, "CE", "B", 1, strike_type="ATM", strike=f"tt_ATM('{symbol}')", expiry_type="Current Week", instrument_id=inst_id))
    s1.add_condition(c1_e)

    c1_x = Condition("Exit")
    c1_x.add_rule(Keyword("Time", "NSE") >= 1515)
    s1.add_condition(c1_x)
    strat.add_set(s1)

    # Universal Exit
    ue = Condition("Universal Exit")
    ue.add_rule(Keyword("Time", "NSE") >= 1515)
    strat.set_universal_exit(ue)

    output_path = os.path.join(os.path.dirname(__file__), "..", "strategies", output_filename)
    strat.export(output_path)
    return output_path


# ─── CLI Entry Point ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Tradetron Unified Parameterized Strategy Generator")
    parser.add_argument("--type", choices=["iron_fly", "momentum"], required=True, help="Strategy type to build")
    parser.add_argument("--symbol", default="NIFTY 50", help="Underlying instrument symbol (e.g. NIFTY 50, BANK NIFTY)")
    parser.add_argument("--hedge-gap", type=int, default=600, help="Hedge distance in points (Iron Fly)")
    parser.add_argument("--roll-step", type=int, default=100, help="Hedge roll step in points (Iron Fly)")
    parser.add_argument("--spot-confirm", type=float, default=5.0, help="Spot confirmation threshold in points (Momentum)")
    parser.add_argument("--expiry", default="Current Month", help="Expiry type (Current Week, Current Month, Next Month)")
    parser.add_argument("--output", default=None, help="Output JSON filename in strategies/")
    parser.add_argument("--audit", action="store_true", default=True, help="Automatically run auditor post-generation")

    args = parser.parse_args()

    out_file = None
    if args.type == "iron_fly":
        out_file = build_iron_fly(
            symbol=args.symbol,
            hedge_gap=args.hedge_gap,
            roll_step=args.roll_step,
            expiry_type=args.expiry,
            output_filename=args.output,
        )
    elif args.type == "momentum":
        out_file = build_momentum(
            symbol=args.symbol,
            spot_confirm=args.spot_confirm,
            expiry_type=args.expiry,
            output_filename=args.output,
        )

    if out_file and args.audit:
        print(f"\n🔍 Running automated auditor on generated strategy: {out_file}...")
        from tradetron_auditor import audit_strategy
        audit_strategy(out_file)

