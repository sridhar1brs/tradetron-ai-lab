from tradetron_builder import Strategy, SetBlock, Condition, Leg, ConditionGroup, Rule, Keyword, Variable
import json
import os

def get_runtime(var_name):
    return Keyword("Get Runtime", var_name)

def get_math_operation(left_keyword, operator, right_keyword_or_str):
    if isinstance(right_keyword_or_str, str):
        right = Keyword("Number", right_keyword_or_str)
    else:
        right = right_keyword_or_str
    # Rule 13 postfix order: Operand1, Operand2, Operator
    return Keyword("Math Operation", left_keyword, right, operator)

def get_spot_close(candle_index, timeframe="1min"):
    close_kw = Keyword("Close",
                   Keyword("Timeframe", timeframe),
                   Keyword("Instrument", "NIFTY 50"))
    return Keyword("Position", close_kw, str(candle_index))

def get_traded_instrument(set_no, cond_no, leg_no):
    return Keyword("Traded Instrument", "Entry", "strike", "NIFTY 50", str(set_no), str(cond_no), str(leg_no))

def get_traded_instrument_ltp(set_no, cond_no, leg_no):
    return Keyword("LTP", get_traded_instrument(set_no, cond_no, leg_no))

def get_traded_instrument_entry_price(set_no, cond_no, leg_no):
    return Keyword("Traded Instrument", "Entry", "price", "NIFTY 50", str(set_no), str(cond_no), str(leg_no))


strat_desc = """
<p><strong>Nifty 50 1-Min Fast Test Momentum Strategy (Native ATM Pattern)</strong></p>
<p><strong>Strategy Notes:</strong></p>
<p>---------------</p>
<p>1. <strong>Purpose:</strong> Ultra-fast 1-minute candle momentum triggers with 1-point Spot_Confirm threshold to test and verify condition execution instantly.</p>
<p>2. <strong>Entry Triggers:</strong></p>
<ul>
  <li>Time: 09:20 AM to 3:00 PM IST.</li>
  <li>CE Signal: Nifty Spot 1-min close shows consecutive directional momentum (Close[-1] > Close[-2] + 1 pt and Close[-2] > Close[-3]).</li>
  <li>PE Signal: Nifty Spot 1-min close shows consecutive downward momentum (Close[-1] < Close[-2] - 1 pt and Close[-2] < Close[-3]).</li>
</ul>
<p>3. <strong>Position Builder:</strong> Uses Native ATM CE / PE leg selection (strikeType: ATM, strike: tt_ATM('NIFTY 50')).</p>
<p>4. <strong>Exit Conditions:</strong> Dynamic SL (10%) and Target (20%) relative to Traded Instrument entry price.</p>
"""

strat = Strategy("Nifty 1Min Test Momentum Strategy", strat_desc)

# ULTRA-RELAXED PARAMETERS FOR INSTANT 1-MIN VERIFICATION
strat.add_variable(Variable("Spot_Confirm", "1"))
strat.add_variable(Variable("SL_Multiplier", "0.9"))
strat.add_variable(Variable("Target_Multiplier", "1.2"))

# ====================================================================================
# SET 1: CALL MOMENTUM (1-MIN CANDLES)
# ====================================================================================
s1 = SetBlock(1)

# S1 ENTRY
c1_entry = Condition(ctype="Entry")
c1_entry.add_rule(Rule(Keyword("Time", "NSE"), ">=", "0920"))
c1_entry.add_rule(Rule(Keyword("Time", "NSE"), "<", "1500"))

# Spot Directional Momentum: Close[-1] > Close[-2] + Spot_Confirm (1 pt)
c1_entry.add_rule(Rule(get_spot_close(-1, "1min"), ">", get_math_operation(get_spot_close(-2, "1min"), "+", get_runtime("Spot_Confirm"))))
# Spot Continuation: Close[-2] > Close[-3]
c1_entry.add_rule(Rule(get_spot_close(-2, "1min"), ">", get_spot_close(-3, "1min")))

# Native ATM Buy CE Leg
c1_entry.add_leg(Leg(
    "NIFTY 50", "CE", "B", 1,
    strike="tt_ATM('NIFTY 50')",
    strike_type="ATM",
    expiry_type="Current Week"
))
s1.add_condition(c1_entry)

# S1 EXIT (SL & TARGET)
c1_exit = Condition(ctype="Exit", operator="or")
c1_exit.add_rule(Rule(get_traded_instrument_ltp(1, 1, 1), "<=", get_math_operation(get_traded_instrument_entry_price(1, 1, 1), "*", get_runtime("SL_Multiplier"))))
c1_exit.add_rule(Rule(get_traded_instrument_ltp(1, 1, 1), ">=", get_math_operation(get_traded_instrument_entry_price(1, 1, 1), "*", get_runtime("Target_Multiplier"))))
s1.add_condition(c1_exit)

strat.add_set(s1)

# ====================================================================================
# SET 2: PUT MOMENTUM (1-MIN CANDLES)
# ====================================================================================
s2 = SetBlock(2)

# S2 ENTRY
c2_entry = Condition(ctype="Entry")
c2_entry.add_rule(Rule(Keyword("Time", "NSE"), ">=", "0920"))
c2_entry.add_rule(Rule(Keyword("Time", "NSE"), "<", "1500"))

# Spot Directional Momentum: Close[-1] < Close[-2] - Spot_Confirm (1 pt)
c2_entry.add_rule(Rule(get_spot_close(-1, "1min"), "<", get_math_operation(get_spot_close(-2, "1min"), "-", get_runtime("Spot_Confirm"))))
# Spot Continuation: Close[-2] < Close[-3]
c2_entry.add_rule(Rule(get_spot_close(-2, "1min"), "<", get_spot_close(-3, "1min")))

# Native ATM Buy PE Leg
c2_entry.add_leg(Leg(
    "NIFTY 50", "PE", "B", 1,
    strike="tt_ATM('NIFTY 50')",
    strike_type="ATM",
    expiry_type="Current Week"
))
s2.add_condition(c2_entry)

# S2 EXIT (SL & TARGET)
c2_exit = Condition(ctype="Exit", operator="or")
c2_exit.add_rule(Rule(get_traded_instrument_ltp(2, 1, 1), "<=", get_math_operation(get_traded_instrument_entry_price(2, 1, 1), "*", get_runtime("SL_Multiplier"))))
c2_exit.add_rule(Rule(get_traded_instrument_ltp(2, 1, 1), ">=", get_math_operation(get_traded_instrument_entry_price(2, 1, 1), "*", get_runtime("Target_Multiplier"))))
s2.add_condition(c2_exit)

# UNIVERSAL EXIT (3:15 PM IST)
ue_cond = Condition(ctype="Universal Exit")
ue_cond.add_rule(Rule(Keyword("Time", "NSE"), ">=", "1515"))
s2.add_condition(ue_cond)

strat.add_set(s2)

strat.export("Nifty_1Min_Test_Momentum_Strategy.json")
strat.export("test_momentum_strategy.json")
print("Compiled Nifty 1Min Test Momentum Strategy to strategies/Nifty_1Min_Test_Momentum_Strategy.json")
