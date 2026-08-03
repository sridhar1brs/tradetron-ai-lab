from tradetron_builder import Strategy, SetBlock, Condition, Leg, ConditionGroup, Rule, Keyword, Variable
import json
import os

def get_runtime(var_name):
    return Keyword("Get Runtime", var_name)

def get_strike_ast_dynamic(operator, var_name):
    """
    Builds AST for: Get Strike(LTP of Spot NIFTY 50) +/- Get Runtime(var_name)
    Uses exact 5-comma format (NFO,NIFTY 50,,,,) per Rules 17 & 27.
    """
    return {
        "operator": "and",
        "operands": [
            {
                "type": "rule",
                "value": "builder-basic_rule_0",
                "elements": [
                    {
                        "name": "Get Strike",
                        "kid": 1000,
                        "params": [
                            {"type": "value", "value": "NIFTY 50"},
                            {"type": "keyword", "keyword": {
                                "name": "LTP", "kid": 1001, "params": [
                                    {"type": "keyword", "keyword": {
                                        "name": "Instrument Name", "kid": 1002, "params": [
                                            {"type": "value", "value": "NFO,NIFTY 50,,,,"}
                                        ]
                                    }}
                                ]
                            }}
                        ]
                    },
                    {"name": operator, "params": []},
                    {"name": "Get Runtime", "kid": 1003, "params": [{"type": "value", "value": var_name}]}
                ]
            }
        ]
    }

def get_math_operation(left_keyword, operator, right_keyword_or_str):
    if isinstance(right_keyword_or_str, str):
        right = Keyword("Number", right_keyword_or_str)
    else:
        right = right_keyword_or_str
    # Rule 13 postfix order: Operand1, Operand2, Operator
    return Keyword("Math Operation", left_keyword, right, operator)

def get_option_close(var_name, candle_index, option_type, is_ce):
    op = "+" if is_ce else "-"
    strike_json = get_strike_ast_dynamic(op, var_name)
    close_kw = Keyword("Close", 
                   Keyword("Timeframe", "3min"), 
                   Keyword("Instrument", "NIFTY 50"), 
                   Keyword("Option Type", option_type), 
                   Keyword("Expiry", "Current Week"),
                   Keyword("Strike", "Fx", strike_json))
    return Keyword("Position", close_kw, str(candle_index))

def get_spot_close(candle_index):
    close_kw = Keyword("Close",
                   Keyword("Timeframe", "3min"),
                   Keyword("Instrument", "NIFTY 50"))
    return Keyword("Position", close_kw, str(candle_index))

def get_traded_instrument(set_no, cond_no, leg_no):
    return Keyword("Traded Instrument", "Entry", "strike", "NIFTY 50", str(set_no), str(cond_no), str(leg_no))

def get_traded_instrument_ltp(set_no, cond_no, leg_no):
    return Keyword("LTP", get_traded_instrument(set_no, cond_no, leg_no))

def get_traded_instrument_entry_price(set_no, cond_no, leg_no):
    return Keyword("Traded Instrument", "Entry", "price", "NIFTY 50", str(set_no), str(cond_no), str(leg_no))


strat_desc = """
<p><strong>Nifty 50 Relaxed Momentum Test Strategy</strong></p>
<p><strong>Strategy Notes:</strong></p>
<p>---------------</p>
<p>1. <strong>Purpose:</strong> Relaxed thresholds for verification on normal market days.</p>
<p>2. <strong>Parameters:</strong></p>
<ul>
  <li>OTM_Offset: 100 points (closer to ATM for higher delta response).</li>
  <li>Jump_1: 1.03 (+3% option gain on candle -2).</li>
  <li>Jump_2: 1.05 (+5% option gain on candle -1).</li>
  <li>Spot_Confirm: 8 Nifty points move on underlying spot.</li>
  <li>SL_Multiplier: 0.9 (10% SL).</li>
  <li>Target_Multiplier: 1.2 (20% Target).</li>
</ul>
<p>3. <strong>Execution Window:</strong> 09:20 AM to 3:00 PM. Universal exit at 3:15 PM.</p>
"""

strat = Strategy("Test Momentum Strategy (Relaxed Parameters)", strat_desc)

# RELAXED PARAMETERS FOR TEST / VERIFICATION
strat.add_variable(Variable("OTM_Offset", "100"))
strat.add_variable(Variable("Jump_1", "1.03"))
strat.add_variable(Variable("Jump_2", "1.05"))
strat.add_variable(Variable("Spot_Confirm", "8"))
strat.add_variable(Variable("SL_Multiplier", "0.9"))
strat.add_variable(Variable("Target_Multiplier", "1.2"))


# ====================================================================================
# SET 1: CE RELAXED MOMENTUM
# ====================================================================================
s1 = SetBlock(1)

# S1 ENTRY
c1_entry = Condition(ctype="Entry")
c1_entry.add_rule(Rule(Keyword("Time", "NSE"), ">=", "0920"))
c1_entry.add_rule(Rule(Keyword("Time", "NSE"), "<", "1500"))

# Option momentum: Close(-1) > Close(-2) * Jump_2 (+5% jump)
c1_entry.add_rule(Rule(get_option_close("OTM_Offset", -1, "CE", True), ">", get_math_operation(get_option_close("OTM_Offset", -2, "CE", True), "*", get_runtime("Jump_2"))))
# Option momentum: Close(-2) > Close(-3) * Jump_1 (+3% jump)
c1_entry.add_rule(Rule(get_option_close("OTM_Offset", -2, "CE", True), ">", get_math_operation(get_option_close("OTM_Offset", -3, "CE", True), "*", get_runtime("Jump_1"))))

# Spot Confirmation: Close(-1) > Close(-2) + Spot_Confirm (+8 pts)
c1_entry.add_rule(Rule(get_spot_close(-1), ">", get_math_operation(get_spot_close(-2), "+", get_runtime("Spot_Confirm"))))

# Leg 1: Long CE OTM
c1_entry.add_leg(Leg(
    "NIFTY 50", "CE", "B", 1,
    strike="( Get Strike + Get Runtime(OTM_Offset) )",
    strike_type="Fx",
    strike_json=get_strike_ast_dynamic("+", "OTM_Offset"),
    expiry_type="Current Week"
))
s1.add_condition(c1_entry)

# S1 EXIT (OR logic: SL or Target)
c1_exit = Condition(ctype="Exit", operator="or")
c1_exit.add_rule(Rule(get_traded_instrument_ltp(1, 1, 1), "<=", get_math_operation(get_traded_instrument_entry_price(1, 1, 1), "*", get_runtime("SL_Multiplier"))))
c1_exit.add_rule(Rule(get_traded_instrument_ltp(1, 1, 1), ">=", get_math_operation(get_traded_instrument_entry_price(1, 1, 1), "*", get_runtime("Target_Multiplier"))))
s1.add_condition(c1_exit)

strat.add_set(s1)

# ====================================================================================
# SET 2: PE RELAXED MOMENTUM
# ====================================================================================
s2 = SetBlock(2)

# S2 ENTRY
c2_entry = Condition(ctype="Entry")
c2_entry.add_rule(Rule(Keyword("Time", "NSE"), ">=", "0920"))
c2_entry.add_rule(Rule(Keyword("Time", "NSE"), "<", "1500"))

# Option momentum: Close(-1) > Close(-2) * Jump_2 (+5% jump)
c2_entry.add_rule(Rule(get_option_close("OTM_Offset", -1, "PE", False), ">", get_math_operation(get_option_close("OTM_Offset", -2, "PE", False), "*", get_runtime("Jump_2"))))
# Option momentum: Close(-2) > Close(-3) * Jump_1 (+3% jump)
c2_entry.add_rule(Rule(get_option_close("OTM_Offset", -2, "PE", False), ">", get_math_operation(get_option_close("OTM_Offset", -3, "PE", False), "*", get_runtime("Jump_1"))))

# Spot Confirmation for PE: Close(-2) > Close(-1) + Spot_Confirm (+8 pts drop)
c2_entry.add_rule(Rule(get_spot_close(-2), ">", get_math_operation(get_spot_close(-1), "+", get_runtime("Spot_Confirm"))))

# Leg 1: Long PE OTM
c2_entry.add_leg(Leg(
    "NIFTY 50", "PE", "B", 1,
    strike="( Get Strike - Get Runtime(OTM_Offset) )",
    strike_type="Fx",
    strike_json=get_strike_ast_dynamic("-", "OTM_Offset"),
    expiry_type="Current Week"
))
s2.add_condition(c2_entry)

# S2 EXIT (OR logic: SL or Target)
c2_exit = Condition(ctype="Exit", operator="or")
c2_exit.add_rule(Rule(get_traded_instrument_ltp(2, 1, 1), "<=", get_math_operation(get_traded_instrument_entry_price(2, 1, 1), "*", get_runtime("SL_Multiplier"))))
c2_exit.add_rule(Rule(get_traded_instrument_ltp(2, 1, 1), ">=", get_math_operation(get_traded_instrument_entry_price(2, 1, 1), "*", get_runtime("Target_Multiplier"))))
s2.add_condition(c2_exit)

strat.add_set(s2)

# ====================================================================================
# UNIVERSAL EXIT
# ====================================================================================
u_exit = Condition(ctype="Universal Exit")
u_exit.add_rule(Rule(Keyword("Time", "NSE"), ">=", "1515"))
strat.set_universal_exit(u_exit)

strat.export("test_momentum_strategy.json")
print("Generated test_momentum_strategy.json successfully.")
