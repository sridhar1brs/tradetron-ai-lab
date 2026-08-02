from tradetron_builder import Strategy, SetBlock, Condition, Leg, ConditionGroup, Rule, Keyword, Variable
import json

def get_runtime(var_name):
    return Keyword("Get Runtime", var_name)

def get_strike_ast_dynamic(operator, var_name):
    # Builds AST for: Get Strike(LTP) +/- Get Runtime(var_name)
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
                                            {"type": "value", "value": "NFO,NIFTY 50,Current Month,,,,"}
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
    # If right is string, we assume it's a Keyword("Number", right_str) if we were hardcoding,
    # but here we'll pass the keyword directly (e.g. get_runtime(...))
    if isinstance(right_keyword_or_str, str):
        right = Keyword("Number", right_keyword_or_str)
    else:
        right = right_keyword_or_str
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

def get_option_ltp(var_name, option_type, is_ce):
    op = "+" if is_ce else "-"
    strike_json = get_strike_ast_dynamic(op, var_name)
    return Keyword("LTP",
                   Keyword("Instrument Name", f"NFO,NIFTY 50,Current Week,{option_type},,Fx", strike_json))

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
<p><strong>Nifty 50 OTM4 Momentum Intraday Strategy (Fully Parameterized)</strong></p>
<p><strong>Strategy Notes:</strong></p>
<p>---------------</p>
<p>1. <strong>Entry:</strong></p>
<ul>
  <li>Time: Between 9:20 AM and 3:00 PM.</li>
  <li>Selection: Continuously monitors OTM4 (ATM +/- OTM_Offset) Call and Put options on a 3-minute timeframe.</li>
  <li>Condition: Enters long if the previous 3-min candle closed `Jump_1` higher than the one before it, and the current 3-min candle closed `Jump_2` higher than the previous one, backed by a `Spot_Confirm` underlying movement.</li>
</ul>
<p>2. <strong>Exit:</strong></p>
<ul>
  <li>Target: `Target_Multiplier` (e.g., 3.0x Entry Price).</li>
  <li>Stop Loss: `SL_Multiplier` (e.g., 0.8x Entry Price).</li>
  <li>Universal Exit: Square off all positions intraday at 3:15 PM.</li>
</ul>
"""

strat = Strategy("OTM4 3Min Momentum Strategy v2", strat_desc)

# VARIABLES (Rule #1 compliance)
strat.add_variable(Variable("OTM_Offset", "200"))
strat.add_variable(Variable("Jump_1", "1.2"))
strat.add_variable(Variable("Jump_2", "1.4"))
strat.add_variable(Variable("Spot_Confirm", "30"))
strat.add_variable(Variable("SL_Multiplier", "0.8"))
strat.add_variable(Variable("Target_Multiplier", "3.0"))


# ====================================================================================
# SET 1: CE MOMENTUM
# ====================================================================================
s1 = SetBlock(1)

# S1 ENTRY
c1_entry = Condition(ctype="Entry")
c1_entry.add_rule(Rule(Keyword("Time", "NSE"), ">=", "0920"))
c1_entry.add_rule(Rule(Keyword("Time", "NSE"), "<", "1500"))

# Close(-1) > Math Operation(Close(-2) * Get Runtime(Jump_2))
c1_entry.add_rule(Rule(get_option_close("OTM_Offset", -1, "CE", True), ">", get_math_operation(get_option_close("OTM_Offset", -2, "CE", True), "*", get_runtime("Jump_2"))))
# Close(-2) > Math Operation(Close(-3) * Get Runtime(Jump_1))
c1_entry.add_rule(Rule(get_option_close("OTM_Offset", -2, "CE", True), ">", get_math_operation(get_option_close("OTM_Offset", -3, "CE", True), "*", get_runtime("Jump_1"))))

# Spot Confirmation: Close(-1) > Math Operation(Close(-2) + Get Runtime(Spot_Confirm))
c1_entry.add_rule(Rule(get_spot_close(-1), ">", get_math_operation(get_spot_close(-2), "+", get_runtime("Spot_Confirm"))))

# Leg 1: Long CE OTM
c1_entry.add_leg(Leg("NIFTY 50", "CE", "B", 1, strike="( Get Strike + Get Runtime(OTM_Offset) )", strike_type="Fx", strike_json=get_strike_ast_dynamic("+", "OTM_Offset"), expiry_type="Current Week"))
s1.add_condition(c1_entry)

# S1 EXIT
c1_exit = Condition(ctype="Exit", operator="or")
# Leg 1 SL: LTP <= Entry Price * Get Runtime(SL_Multiplier)
c1_exit.add_rule(Rule(get_traded_instrument_ltp(1, 1, 1), "<=", get_math_operation(get_traded_instrument_entry_price(1, 1, 1), "*", get_runtime("SL_Multiplier"))))
# Leg 1 Target: LTP >= Entry Price * Get Runtime(Target_Multiplier)
c1_exit.add_rule(Rule(get_traded_instrument_ltp(1, 1, 1), ">=", get_math_operation(get_traded_instrument_entry_price(1, 1, 1), "*", get_runtime("Target_Multiplier"))))
s1.add_condition(c1_exit)

strat.add_set(s1)

# ====================================================================================
# SET 2: PE MOMENTUM
# ====================================================================================
s2 = SetBlock(2)

# S2 ENTRY
c2_entry = Condition(ctype="Entry")
c2_entry.add_rule(Rule(Keyword("Time", "NSE"), ">=", "0920"))
c2_entry.add_rule(Rule(Keyword("Time", "NSE"), "<", "1500"))

# Close(-1) > Math Operation(Close(-2) * Get Runtime(Jump_2))
c2_entry.add_rule(Rule(get_option_close("OTM_Offset", -1, "PE", False), ">", get_math_operation(get_option_close("OTM_Offset", -2, "PE", False), "*", get_runtime("Jump_2"))))
# Close(-2) > Math Operation(Close(-3) * Get Runtime(Jump_1))
c2_entry.add_rule(Rule(get_option_close("OTM_Offset", -2, "PE", False), ">", get_math_operation(get_option_close("OTM_Offset", -3, "PE", False), "*", get_runtime("Jump_1"))))

# Spot Confirmation: Close(-2) > Math Operation(Close(-1) + Get Runtime(Spot_Confirm))
c2_entry.add_rule(Rule(get_spot_close(-2), ">", get_math_operation(get_spot_close(-1), "+", get_runtime("Spot_Confirm"))))

# Leg 1: Long PE OTM
c2_entry.add_leg(Leg("NIFTY 50", "PE", "B", 1, strike="( Get Strike - Get Runtime(OTM_Offset) )", strike_type="Fx", strike_json=get_strike_ast_dynamic("-", "OTM_Offset"), expiry_type="Current Week"))
s2.add_condition(c2_entry)

# S2 EXIT
c2_exit = Condition(ctype="Exit", operator="or")
# Leg 1 SL: LTP <= Entry Price * Get Runtime(SL_Multiplier)
c2_exit.add_rule(Rule(get_traded_instrument_ltp(2, 1, 1), "<=", get_math_operation(get_traded_instrument_entry_price(2, 1, 1), "*", get_runtime("SL_Multiplier"))))
# Leg 1 Target: LTP >= Entry Price * Get Runtime(Target_Multiplier)
c2_exit.add_rule(Rule(get_traded_instrument_ltp(2, 1, 1), ">=", get_math_operation(get_traded_instrument_entry_price(2, 1, 1), "*", get_runtime("Target_Multiplier"))))
s2.add_condition(c2_exit)

strat.add_set(s2)

# ====================================================================================
# UNIVERSAL EXIT
# ====================================================================================
u_exit = Condition(ctype="Universal Exit")
u_exit.add_rule(Rule(Keyword("Time", "NSE"), ">=", "1515"))
strat.set_universal_exit(u_exit)

strat.export("../strategies/momentum_strategy.json")
print("Generated ../strategies/momentum_strategy.json successfully.")
