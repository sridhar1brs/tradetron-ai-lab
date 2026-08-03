from tradetron_builder import Strategy, SetBlock, Condition, Leg, ConditionGroup, Rule, Keyword, Variable
import json

def get_spot_atm_ast():
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
                                            # Fix (Issue #2 & #3): 5 commas = 6 slots (Spot, no Current Month) per Rule 17 & 27
                                            {"type": "value", "value": "NFO,NIFTY 50,,,,"}
                                        ]
                                    }}
                                ]
                            }}
                        ]
                    }
                ]
            }
        ]
    }

def get_strike_ast(operator, var_name):
    # Builds AST for: Get Strike(LTP of Spot) +/- Get Runtime(var_name)
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
                                            # Fix (Issue #2 & #3): 5 commas = 6 slots (Spot, no Current Month) per Rule 17 & 27
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

def get_traded_instrument_ast(set_no, cond_no, leg_no):
    return {
        "operator": "and",
        "operands": [
            {
                "type": "rule",
                "value": "builder-basic_rule_0",
                "elements": [
                    {
                        "name": "Traded Instrument",
                        "kid": 1004,
                        "params": [
                            {"type": "value", "value": "Entry"},
                            {"type": "value", "value": "strike"},
                            {"type": "value", "value": "NIFTY 50"},
                            {"type": "value", "value": str(set_no)},
                            {"type": "value", "value": str(cond_no)},
                            {"type": "value", "value": str(leg_no)}
                        ]
                    }
                ]
            }
        ]
    }

def get_traded_instrument_offset_ast(operator, var_name, set_no, cond_no, leg_no):
    return {
        "operator": "and",
        "operands": [
            {
                "type": "rule",
                "value": "builder-basic_rule_0",
                "elements": [
                    {
                        "name": "Traded Instrument",
                        "kid": 1004,
                        "params": [
                            {"type": "value", "value": "Entry"},
                            {"type": "value", "value": "strike"},
                            {"type": "value", "value": "NIFTY 50"},
                            {"type": "value", "value": str(set_no)},
                            {"type": "value", "value": str(cond_no)},
                            {"type": "value", "value": str(leg_no)}
                        ]
                    },
                    {"name": operator, "params": []},
                    {"name": "Get Runtime", "kid": 1003, "params": [{"type": "value", "value": var_name}]}
                ]
            }
        ]
    }


strat_desc = """
<p><strong>Enters a 4-leg Ironfly options position on NIFTY index and actively adjusts the long protective hedges as the spot price trends.</strong></p>
<p><strong>Strategy Notes:</strong></p>
<p>---------------</p>
<p>1. <strong>Entry:</strong></p>
<ul>
  <li>Time: 3:00 PM (15:00 IST) on the first trading day after monthly expiry (usually Friday) per Rule 36.</li>
  <li>Selection: Sell ATM Call and Put for the next monthly expiry. Strike is selected where premiums are closest to being equal (price‑balanced strangle center) and must be a multiple of 100.</li>
  <li>Expected premium collected: ₹700–800.</li>
  <li>Hedges: Buy Call & Put hedges 600 points away from the straddle strike.</li>
</ul>
<p>2. <strong>Adjustments (Rolling Hedges):</strong></p>
<ul>
  <li>When spot crosses either hedge boundary (moves 600 points from center):</li>
  <ul>
    <li>Close the profit‑making buy leg (Call hedge if Nifty goes up, Put hedge if Nifty goes down).</li>
    <li>Move/roll that buy leg 100 points outward (e.g. Call strike + 100 / Put strike - 100) to lock in the profit of the long option and shift the boundary to prevent looping.</li>
  </ul>
</ul>
<p>3. <strong>Exit / Hold Till Expiry:</strong></p>
<ul>
  <li>Default Exit: Square off all positions on the Friday before the expiry week.</li>
  <li>Hold Till Expiry Mode (HOLD_TILL_EXPIRY = True):</li>
  <ul>
    <li>On the Friday before expiry week, close the current hedges.</li>
    <li>Buy new hedges much closer (100 points away).</li>
    <li>Hold this tight position and square off on Thursday (expiry day).</li>
  </ul>
</ul>
"""


strat = Strategy("Best Practice Margin Optimized Iron Fly", strat_desc)

# VARIABLES
strat.add_variable(Variable("HedgeGap", "600"))
strat.add_variable(Variable("HedgeRoll", "100"))
strat.add_variable(Variable("HOLD_TILL_EXPIRY", "1"))

# ====================================================================================
# SET 1: CORE IRON FLY (ENTRY & REPAIR SPLIT)
# ====================================================================================
s1 = SetBlock(1)

# S1 ENTRY (BUY LEGS ONLY FOR MARGIN OPTIMIZATION)
c1_entry = Condition(ctype="Entry")
# Rule 36: Entry trigger set to 1500 (3:00 PM) for optimal fill liquidity before 1515 auto-squareoff volatility
c1_entry.add_rule(Rule(Keyword("Time", "NSE"), ">=", "1500"))
# Leg 1: Long CE Hedge
c1_entry.add_leg(Leg("NIFTY 50", "CE", "B", 1, strike="( Get Strike + Get Runtime(HedgeGap) )", strike_type="Fx", strike_json=get_strike_ast("+", "HedgeGap")))
# Leg 2: Long PE Hedge
c1_entry.add_leg(Leg("NIFTY 50", "PE", "B", 1, strike="( Get Strike - Get Runtime(HedgeGap) )", strike_type="Fx", strike_json=get_strike_ast("-", "HedgeGap")))
s1.add_condition(c1_entry)

# S1 REPAIR ONCE (SELL LEGS AFTER MARGIN BENEFIT)
c1_repair = Condition(ctype="Repair Once")
# Trigger short legs only after Long legs are executed successfully (Traded Instrument Qty != 0)
c1_repair.add_rule(Rule(Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "1", "1"), "!=", "0"))
# Fix (Issue #8): Short straddle uses Next Month expiry for monthly Iron Fly
# Leg 1 (Repair): Short CE ATM — Spot-based ATM via Get Strike (Next Month expiry)
c1_repair.add_leg(Leg("NIFTY 50", "CE", "S", 1, strike="( Get Strike(Spot LTP) )", strike_type="Fx", strike_json=get_spot_atm_ast(), expiry_type="Next Month"))
# Leg 2 (Repair): Short PE ATM — Spot-based ATM via Get Strike (Next Month expiry)
c1_repair.add_leg(Leg("NIFTY 50", "PE", "S", 1, strike="( Get Strike(Spot LTP) )", strike_type="Fx", strike_json=get_spot_atm_ast(), expiry_type="Next Month"))
s1.add_condition(c1_repair)

# --- CLEAN UP BLOCKS for Set 4 Trigger ---
# If Set 4 Entry triggers, we must close the currently active wide hedges.
# We do this using Repair Once blocks in Sets 1, 2, and 3.

# Set 1 Clean Up (Original Hedges)
c1_cleanup_ce = Condition(ctype="Repair Once")
c1_cleanup_ce.add_rule(Rule(Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "4", "1"), ">", "0"))
c1_cleanup_ce.add_rule(Rule(Keyword("Net Quantity", Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "1", "1")), "!=", "0"))
c1_cleanup_ce.add_leg(Leg(buy_sell="S", option_type="CE", strike_type="Fx", strike_json=get_traded_instrument_ast(1, 1, 1)))
s1.add_condition(c1_cleanup_ce)

c1_cleanup_pe = Condition(ctype="Repair Once")
c1_cleanup_pe.add_rule(Rule(Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "4", "1"), ">", "0"))
c1_cleanup_pe.add_rule(Rule(Keyword("Net Quantity", Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "1", "2")), "!=", "0"))
c1_cleanup_pe.add_leg(Leg(buy_sell="S", option_type="PE", strike_type="Fx", strike_json=get_traded_instrument_ast(1, 1, 2)))
s1.add_condition(c1_cleanup_pe)

strat.add_set(s1)

# ====================================================================================
# SET 2: CALL HEDGE ROLL
# ====================================================================================
s2 = SetBlock(2)
c2_entry = Condition(ctype="Entry")
# Trigger: Spot crosses CE boundary (LTP > Traded Strike of S1 E Leg 1)
# Fix (Issue #3): Use Spot LTP (5 commas, no Current Month) per Rules 17 & 27
c2_entry.add_rule(Rule(Keyword("LTP", Keyword("Instrument Name", "NFO,NIFTY 50,,,,,")) , ">", Keyword("Traded Instrument", "Entry", "strike", "NIFTY 50", "1", "1", "1")))

# Sell old CE Hedge EXACTLY at its traded strike
c2_entry.add_leg(Leg("NIFTY 50", "CE", "S", 1, strike="( Traded Instrument )", strike_type="Fx", strike_json=get_traded_instrument_ast(1, 1, 1))) 
# Buy new CE Hedge at Traded Strike + HedgeRoll
c2_entry.add_leg(Leg("NIFTY 50", "CE", "B", 1, strike="( Traded Instrument + Get Runtime(HedgeRoll) )", strike_type="Fx", strike_json=get_traded_instrument_offset_ast("+", "HedgeRoll", 1, 1, 1)))
s2.add_condition(c2_entry)

# Set 2 Clean Up (Rolled CE)
c2_cleanup = Condition(ctype="Repair Once")
c2_cleanup.add_rule(Rule(Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "4", "1"), ">", "0"))
c2_cleanup.add_rule(Rule(Keyword("Net Quantity", Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "2", "2")), "!=", "0"))
c2_cleanup.add_leg(Leg(buy_sell="S", option_type="CE", strike_type="Fx", strike_json=get_traded_instrument_ast(1, 2, 2)))
s2.add_condition(c2_cleanup)

strat.add_set(s2)

# ====================================================================================
# SET 3: PUT HEDGE ROLL
# ====================================================================================
s3 = SetBlock(3)
c3_entry = Condition(ctype="Entry")
# Trigger: Spot crosses PE boundary (LTP < Traded Strike of S1 E Leg 2)
# Fix (Issue #3): Use Spot LTP (5 commas, no Current Month) per Rules 17 & 27
c3_entry.add_rule(Rule(Keyword("LTP", Keyword("Instrument Name", "NFO,NIFTY 50,,,,,")) , "<", Keyword("Traded Instrument", "Entry", "strike", "NIFTY 50", "1", "1", "2")))

# Sell old PE Hedge EXACTLY at its traded strike
c3_entry.add_leg(Leg("NIFTY 50", "PE", "S", 1, strike="( Traded Instrument )", strike_type="Fx", strike_json=get_traded_instrument_ast(1, 1, 2)))
# Buy new PE Hedge at Traded Strike - HedgeRoll
c3_entry.add_leg(Leg("NIFTY 50", "PE", "B", 1, strike="( Traded Instrument - Get Runtime(HedgeRoll) )", strike_type="Fx", strike_json=get_traded_instrument_offset_ast("-", "HedgeRoll", 1, 1, 2)))
s3.add_condition(c3_entry)

# Set 3 Clean Up (Rolled PE)
c3_cleanup = Condition(ctype="Repair Once")
c3_cleanup.add_rule(Rule(Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "4", "1"), ">", "0"))
c3_cleanup.add_rule(Rule(Keyword("Net Quantity", Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "3", "2")), "!=", "0"))
c3_cleanup.add_leg(Leg(buy_sell="S", option_type="PE", strike_type="Fx", strike_json=get_traded_instrument_ast(1, 3, 2)))
s3.add_condition(c3_cleanup)

strat.add_set(s3)

# ====================================================================================
# SET 4: HOLD TILL EXPIRY MODE (TIGHTEN HEDGES)
# ====================================================================================
s4 = SetBlock(4)
c4_entry = Condition(ctype="Entry")
c4_entry.add_rule(Rule(Keyword("Get Runtime", "HOLD_TILL_EXPIRY"), "==", "1"))
c4_entry.add_rule(Rule(Keyword("Days to Expiry", "NIFTY 50"), "<", "7"))

# Buy new tight hedges 100 points from the S1 R1 (Repair Once) straddle legs
c4_entry.add_leg(Leg("NIFTY 50", "CE", "B", 1, strike="( Straddle CE + 100 )", strike_type="Fx", strike_json=get_traded_instrument_offset_ast("+", "HedgeRoll", 1, 2, 1)))
c4_entry.add_leg(Leg("NIFTY 50", "PE", "B", 1, strike="( Straddle PE - 100 )", strike_type="Fx", strike_json=get_traded_instrument_offset_ast("-", "HedgeRoll", 1, 2, 2)))
s4.add_condition(c4_entry)
strat.add_set(s4)

# ====================================================================================
# UNIVERSAL EXIT
# ====================================================================================
# Group 1: If HOLD_TILL_EXPIRY is 0, exit on Friday (Days to Expiry < 7)
g1 = ConditionGroup("and")
g1.add_rule(Rule(Keyword("Get Runtime", "HOLD_TILL_EXPIRY"), "==", "0"))
g1.add_rule(Rule(Keyword("Days to Expiry", "NIFTY 50"), "<", "7"))

# Group 2: If HOLD_TILL_EXPIRY is 1, exit on Expiry Day (Days to Expiry == 0)
g2 = ConditionGroup("and")
g2.add_rule(Rule(Keyword("Get Runtime", "HOLD_TILL_EXPIRY"), "==", "1"))
g2.add_rule(Rule(Keyword("Days to Expiry", "NIFTY 50"), "==", "0"))

ue_cond = Condition(ctype="Universal Exit", operator="or")
ue_cond.add_rule(g1)
ue_cond.add_rule(g2)
strat.set_universal_exit(ue_cond)

# Fix (Issue #11): export() now resolves paths using __file__, no need to pass base_strategy.json path
strat.export("Corrected_Iron_Fly.json")
print("Compiled Margin-Optimized Iron Fly strategy to strategies/Corrected_Iron_Fly.json")
