from tradetron_builder import Strategy, SetBlock, Condition, Leg, ConditionGroup, Rule, Keyword, Variable
import json
import os

def get_select_expiry_kw(expiry_kind="month", offset=0):
    return Keyword("Select Expiry", expiry_kind, str(offset))

def get_find_strike_ast_delta(expiry_kind="month", offset=0, delta_val=0.5, option_type="CE"):
    return {
        "operator": "and",
        "operands": [
            {
                "type": "rule",
                "value": "builder-basic_rule_0",
                "elements": [
                    {
                        "name": "Find Strike",
                        "kid": 1000,
                        "params": [
                            {"type": "value", "value": "NIFTY 50"},
                            {
                                "type": "keyword",
                                "keyword": get_select_expiry_kw(expiry_kind, offset).to_dict()
                            },
                            {"type": "value", "value": "delta"},
                            {
                                "type": "keyword",
                                "keyword": Keyword("Number", str(delta_val)).to_dict()
                            },
                            {"type": "value", "value": option_type},
                            {"type": "value", "value": "any"}
                        ]
                    }
                ]
            }
        ]
    }

def get_find_strike_ast_offset(operator, var_name, expiry_kind="month", offset=0, delta_val=0.5, option_type="CE"):
    base_find_strike = {
        "name": "Find Strike",
        "kid": 1001,
        "params": [
            {"type": "value", "value": "NIFTY 50"},
            {
                "type": "keyword",
                "keyword": get_select_expiry_kw(expiry_kind, offset).to_dict()
            },
            {"type": "value", "value": "delta"},
            {
                "type": "keyword",
                "keyword": Keyword("Number", str(delta_val)).to_dict()
            },
            {"type": "value", "value": option_type},
            {"type": "value", "value": "any"}
        ]
    }

    return {
        "operator": "and",
        "operands": [
            {
                "type": "rule",
                "value": "builder-basic_rule_0",
                "elements": [
                    {
                        "name": "Find Strike",
                        "kid": 1000,
                        "params": [
                            {"type": "value", "value": "NIFTY 50"},
                            {
                                "type": "keyword",
                                "keyword": get_select_expiry_kw(expiry_kind, offset).to_dict()
                            },
                            {"type": "value", "value": "strike"},
                            {
                                "type": "keyword",
                                "keyword": {
                                    "name": "Math Operation",
                                    "kid": 1002,
                                    "params": [
                                        {"type": "keyword", "keyword": base_find_strike},
                                        {
                                            "type": "keyword",
                                            "keyword": Keyword("Get Runtime", var_name).to_dict()
                                        },
                                        {"type": "value", "value": operator}
                                    ]
                                }
                            },
                            {"type": "value", "value": option_type},
                            {"type": "value", "value": "any"}
                        ]
                    }
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
<p><strong>Nifty 50 Monthly Iron Fly Strategy with Find Strike & Dynamic Hedge Rollovers</strong></p>
<p><strong>Strategy Notes:</strong></p>
<p>---------------</p>
<p>1. <strong>Entry (Margin-Optimized Split):</strong></p>
<ul>
  <li>Time: 09:20 AM IST.</li>
  <li>Selection: Current Month Expiry ATM Straddle and protective hedges via Find Strike.</li>
  <li>Hedges: Buy Call & Put hedges 600 points away.</li>
</ul>
<p>2. <strong>Adjustments (Rolling Hedges):</strong></p>
<ul>
  <li>When spot crosses either hedge boundary, roll hedge 100 points outward.</li>
</ul>
<p>3. <strong>Exit:</strong> Universal Exit on expiry or specified hold mode.</p>
"""

strat = Strategy("Nifty Monthly IronFly FindStrike with Hedge Rollover", strat_desc)

# VARIABLES
strat.add_variable(Variable("HedgeGap", "600"))
strat.add_variable(Variable("HedgeRoll", "100"))
strat.add_variable(Variable("HOLD_TILL_EXPIRY", "1"))

# ====================================================================================
# SET 1: CORE IRON FLY (BUY HEDGES FIRST, SHORT STRADDLE IN REPAIR ONCE)
# ====================================================================================
s1 = SetBlock(1)

# S1 ENTRY (09:20 AM IST Entry)
c1_entry = Condition(ctype="Entry")
c1_entry.add_rule(Rule(Keyword("Time", "NSE"), ">=", "0920"))

# Leg 1: Long CE Hedge via Find Strike (Current Month Expiry)
c1_entry.add_leg(Leg(
    "NIFTY 50", "CE", "B", 1,
    strike="( Find Strike ( NIFTY 50, Select Expiry(month, 0), strike, Find Strike(ATM CE) + Get Runtime(HedgeGap), CE, any ) )",
    strike_type="Fx",
    strike_json=get_find_strike_ast_offset("+", "HedgeGap", expiry_kind="month", offset=0, delta_val=0.5, option_type="CE"),
    expiry_type="Current Month"
))

# Leg 2: Long PE Hedge via Find Strike (Current Month Expiry)
c1_entry.add_leg(Leg(
    "NIFTY 50", "PE", "B", 1,
    strike="( Find Strike ( NIFTY 50, Select Expiry(month, 0), strike, Find Strike(ATM PE) - Get Runtime(HedgeGap), PE, any ) )",
    strike_type="Fx",
    strike_json=get_find_strike_ast_offset("-", "HedgeGap", expiry_kind="month", offset=0, delta_val=-0.5, option_type="PE"),
    expiry_type="Current Month"
))
s1.add_condition(c1_entry)

# S1 REPAIR ONCE (SHORT STRADDLE LEGS AFTER MARGIN BENEFIT)
c1_repair = Condition(ctype="Repair Once")
c1_repair.add_rule(Rule(Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "1", "1"), ">", "0"))

# Leg 1 (Repair): Short CE ATM via Find Strike (Current Month Expiry)
c1_repair.add_leg(Leg(
    "NIFTY 50", "CE", "S", 1,
    strike="( Find Strike ( NIFTY 50, Select Expiry(month, 0), delta, 0.5, CE, any ) )",
    strike_type="Fx",
    strike_json=get_find_strike_ast_delta(expiry_kind="month", offset=0, delta_val=0.5, option_type="CE"),
    expiry_type="Current Month"
))

# Leg 2 (Repair): Short PE ATM via Find Strike (Current Month Expiry)
c1_repair.add_leg(Leg(
    "NIFTY 50", "PE", "S", 1,
    strike="( Find Strike ( NIFTY 50, Select Expiry(month, 0), delta, -0.5, PE, any ) )",
    strike_type="Fx",
    strike_json=get_find_strike_ast_delta(expiry_kind="month", offset=0, delta_val=-0.5, option_type="PE"),
    expiry_type="Current Month"
))
s1.add_condition(c1_repair)

# --- CLEAN UP BLOCKS for Set 4 Trigger ---
c1_cleanup_ce = Condition(ctype="Repair Once")
c1_cleanup_ce.add_rule(Rule(Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "4", "1"), ">", "0"))
c1_cleanup_ce.add_rule(Rule(Keyword("Net Quantity", Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "1", "1")), "!=", "0"))
c1_cleanup_ce.add_leg(Leg(buy_sell="S", option_type="CE", strike_type="Fx", strike_json=get_traded_instrument_ast(1, 1, 1), expiry_type="Current Month"))
s1.add_condition(c1_cleanup_ce)

c1_cleanup_pe = Condition(ctype="Repair Once")
c1_cleanup_pe.add_rule(Rule(Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "4", "1"), ">", "0"))
c1_cleanup_pe.add_rule(Rule(Keyword("Net Quantity", Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "1", "2")), "!=", "0"))
c1_cleanup_pe.add_leg(Leg(buy_sell="S", option_type="PE", strike_type="Fx", strike_json=get_traded_instrument_ast(1, 1, 2), expiry_type="Current Month"))
s1.add_condition(c1_cleanup_pe)

strat.add_set(s1)

# ====================================================================================
# SET 2: CALL HEDGE ROLL
# ====================================================================================
s2 = SetBlock(2)
c2_entry = Condition(ctype="Entry")
c2_entry.add_rule(Rule(Keyword("LTP", Keyword("Instrument Name", "NFO,NIFTY 50,Current Month,,,,")), ">", Keyword("Traded Instrument", "Entry", "strike", "NIFTY 50", "1", "1", "1")))

c2_entry.add_leg(Leg("NIFTY 50", "CE", "S", 1, strike="( Traded Instrument )", strike_type="Fx", strike_json=get_traded_instrument_ast(1, 1, 1), expiry_type="Current Month")) 
c2_entry.add_leg(Leg("NIFTY 50", "CE", "B", 1, strike="( Traded Instrument + Get Runtime(HedgeRoll) )", strike_type="Fx", strike_json=get_traded_instrument_offset_ast("+", "HedgeRoll", 1, 1, 1), expiry_type="Current Month"))
s2.add_condition(c2_entry)

c2_cleanup = Condition(ctype="Repair Once")
c2_cleanup.add_rule(Rule(Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "4", "1"), ">", "0"))
c2_cleanup.add_rule(Rule(Keyword("Net Quantity", Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "2", "2")), "!=", "0"))
c2_cleanup.add_leg(Leg(buy_sell="S", option_type="CE", strike_type="Fx", strike_json=get_traded_instrument_ast(1, 2, 2), expiry_type="Current Month"))
s2.add_condition(c2_cleanup)

strat.add_set(s2)

# ====================================================================================
# SET 3: PUT HEDGE ROLL
# ====================================================================================
s3 = SetBlock(3)
c3_entry = Condition(ctype="Entry")
c3_entry.add_rule(Rule(Keyword("LTP", Keyword("Instrument Name", "NFO,NIFTY 50,Current Month,,,,")), "<", Keyword("Traded Instrument", "Entry", "strike", "NIFTY 50", "1", "1", "2")))

c3_entry.add_leg(Leg("NIFTY 50", "PE", "S", 1, strike="( Traded Instrument )", strike_type="Fx", strike_json=get_traded_instrument_ast(1, 1, 2), expiry_type="Current Month"))
c3_entry.add_leg(Leg("NIFTY 50", "PE", "B", 1, strike="( Traded Instrument - Get Runtime(HedgeRoll) )", strike_type="Fx", strike_json=get_traded_instrument_offset_ast("-", "HedgeRoll", 1, 1, 2), expiry_type="Current Month"))
s3.add_condition(c3_entry)

c3_cleanup = Condition(ctype="Repair Once")
c3_cleanup.add_rule(Rule(Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "4", "1"), ">", "0"))
c3_cleanup.add_rule(Rule(Keyword("Net Quantity", Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "3", "2")), "!=", "0"))
c3_cleanup.add_leg(Leg(buy_sell="S", option_type="PE", strike_type="Fx", strike_json=get_traded_instrument_ast(1, 3, 2), expiry_type="Current Month"))
s3.add_condition(c3_cleanup)

strat.add_set(s3)

# ====================================================================================
# SET 4: HOLD TILL EXPIRY MODE (TIGHTEN HEDGES)
# ====================================================================================
s4 = SetBlock(4)
c4_entry = Condition(ctype="Entry")
c4_entry.add_rule(Rule(Keyword("Get Runtime", "HOLD_TILL_EXPIRY"), "==", "1"))
c4_entry.add_rule(Rule(Keyword("Days to Expiry", "NIFTY 50"), "<", "7"))

c4_entry.add_leg(Leg("NIFTY 50", "CE", "B", 1, strike="( Straddle CE + 100 )", strike_type="Fx", strike_json=get_traded_instrument_offset_ast("+", "HedgeRoll", 1, 2, 1), expiry_type="Current Month"))
c4_entry.add_leg(Leg("NIFTY 50", "PE", "B", 1, strike="( Straddle PE - 100 )", strike_type="Fx", strike_json=get_traded_instrument_offset_ast("-", "HedgeRoll", 1, 2, 2), expiry_type="Current Month"))
s4.add_condition(c4_entry)
strat.add_set(s4)

# ====================================================================================
# UNIVERSAL EXIT
# ====================================================================================
g1 = ConditionGroup("and")
g1.add_rule(Rule(Keyword("Get Runtime", "HOLD_TILL_EXPIRY"), "==", "0"))
g1.add_rule(Rule(Keyword("Days to Expiry", "NIFTY 50"), "<", "7"))

g2 = ConditionGroup("and")
g2.add_rule(Rule(Keyword("Get Runtime", "HOLD_TILL_EXPIRY"), "==", "1"))
g2.add_rule(Rule(Keyword("Days to Expiry", "NIFTY 50"), "==", "0"))

ue_cond = Condition(ctype="Universal Exit", operator="or")
ue_cond.add_rule(g1)
ue_cond.add_rule(g2)
strat.set_universal_exit(ue_cond)

# Standardized Naming
strat.export("Nifty_Monthly_IronFly_FindStrike_with_Hedge_Rollover.json")
strat.export("Find_Strike_Iron_Fly.json")
print("Compiled Nifty_Monthly_IronFly_FindStrike_with_Hedge_Rollover.json successfully")
