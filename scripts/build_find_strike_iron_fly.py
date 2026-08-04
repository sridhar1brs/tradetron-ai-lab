from tradetron_builder import Strategy, SetBlock, Condition, Leg, ConditionGroup, Rule, Keyword, Variable
import json
import os

def get_select_expiry_kw(expiry_kind="month", offset=0):
    """
    Select Expiry Keyword helper:
    expiry_kind: 'month' or 'week'
    offset: 0 (Current), 1 (Next), 2 (Far)
    """
    return Keyword("Select Expiry", expiry_kind, str(offset))

def get_find_strike_ast_delta(expiry_kind="month", offset=0, delta_val=0.5, option_type="CE"):
    """
    Find Strike by Delta (0.5 for ATM CE, -0.5 for ATM PE)
    Visual Logic: Find Strike( NIFTY 50, Select Expiry(month, 0), delta, Number(0.5), CE, any )
    """
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
    """
    Find Strike with Offset (e.g. Find Strike(ATM) + HedgeGap)
    Visual Logic: Find Strike(NIFTY 50, Select Expiry(month, 0), strike, Find Strike(ATM) +/- Get Runtime(HedgeGap), CE, any)
    """
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
<p><strong>Nifty 50 Production Iron Fly Strategy using native Find Strike keyword</strong></p>
<p><strong>Strategy Notes:</strong></p>
<p>---------------</p>
<p>1. <strong>Entry (Margin-Optimized Split):</strong></p>
<ul>
  <li>Time: 3:00 PM (15:00 IST) on trading day after monthly expiry per Rule 36.</li>
  <li>Long Hedges (S1 E): Buy Call & Put hedges 600 points away using Find Strike(strike = ATM +/- HedgeGap).</li>
  <li>Short Straddle (S1 R1): Sell ATM Call & Put for Next Month expiry using Find Strike(delta = 0.5 / -0.5). Triggers strictly when Long Hedge Traded Instrument Quantity > 0 to guarantee margin benefit.</li>
</ul>
<p>2. <strong>Adjustments (Hedge Rollovers):</strong></p>
<ul>
  <li>Set 2 (Call Roll): Triggered when Nifty Spot crosses CE hedge strike. Rolls CE hedge +100 pts outward anchored to Traded Instrument.</li>
  <li>Set 3 (Put Roll): Triggered when Nifty Spot crosses PE hedge strike. Rolls PE hedge -100 pts outward anchored to Traded Instrument.</li>
</ul>
<p>3. <strong>Exit / Hold Till Expiry:</strong></p>
<ul>
  <li>Set 4: Tightens hedges when Days to Expiry < 7 and HOLD_TILL_EXPIRY = 1.</li>
  <li>Universal Exit: Appended to Set 4 per Rule 8.</li>
</ul>
"""

strat = Strategy("Production Find Strike Margin-Optimized Iron Fly", strat_desc)

# VARIABLES
strat.add_variable(Variable("HedgeGap", "600"))
strat.add_variable(Variable("HedgeRoll", "100"))
strat.add_variable(Variable("HOLD_TILL_EXPIRY", "1"))

# ====================================================================================
# SET 1: CORE IRON FLY (BUY HEDGES FIRST, SHORT STRADDLE IN REPAIR ONCE)
# ====================================================================================
s1 = SetBlock(1)

# S1 ENTRY (LONG HEDGES FIRST FOR MARGIN OPTIMIZATION)
c1_entry = Condition(ctype="Entry")
c1_entry.add_rule(Rule(Keyword("Time", "NSE"), ">=", "1500"))

# Leg 1: Long CE Hedge via Find Strike (ATM CE + HedgeGap)
c1_entry.add_leg(Leg(
    "NIFTY 50", "CE", "B", 1,
    strike="( Find Strike ( NIFTY 50, Select Expiry(month, 0), strike, Find Strike(ATM CE) + Get Runtime(HedgeGap), CE, any ) )",
    strike_type="Fx",
    strike_json=get_find_strike_ast_offset("+", "HedgeGap", expiry_kind="month", offset=0, delta_val=0.5, option_type="CE"),
    expiry_type="Next Month"
))

# Leg 2: Long PE Hedge via Find Strike (ATM PE - HedgeGap)
c1_entry.add_leg(Leg(
    "NIFTY 50", "PE", "B", 1,
    strike="( Find Strike ( NIFTY 50, Select Expiry(month, 0), strike, Find Strike(ATM PE) - Get Runtime(HedgeGap), PE, any ) )",
    strike_type="Fx",
    strike_json=get_find_strike_ast_offset("-", "HedgeGap", expiry_kind="month", offset=0, delta_val=-0.5, option_type="PE"),
    expiry_type="Next Month"
))
s1.add_condition(c1_entry)

# S1 REPAIR ONCE (SHORT STRADDLE LEGS AFTER MARGIN BENEFIT)
c1_repair = Condition(ctype="Repair Once")
# Trigger short legs strictly after Long hedge quantity > 0 (prevents premature trigger when order status is None)
c1_repair.add_rule(Rule(Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "1", "1"), ">", "0"))

# Leg 1 (Repair): Short CE ATM via Find Strike (Delta 0.5)
c1_repair.add_leg(Leg(
    "NIFTY 50", "CE", "S", 1,
    strike="( Find Strike ( NIFTY 50, Select Expiry(month, 0), delta, 0.5, CE, any ) )",
    strike_type="Fx",
    strike_json=get_find_strike_ast_delta(expiry_kind="month", offset=0, delta_val=0.5, option_type="CE"),
    expiry_type="Next Month"
))

# Leg 2 (Repair): Short PE ATM via Find Strike (Delta -0.5)
c1_repair.add_leg(Leg(
    "NIFTY 50", "PE", "S", 1,
    strike="( Find Strike ( NIFTY 50, Select Expiry(month, 0), delta, -0.5, PE, any ) )",
    strike_type="Fx",
    strike_json=get_find_strike_ast_delta(expiry_kind="month", offset=0, delta_val=-0.5, option_type="PE"),
    expiry_type="Next Month"
))
s1.add_condition(c1_repair)

# --- CLEAN UP BLOCKS for Set 4 Trigger ---
c1_cleanup_ce = Condition(ctype="Repair Once")
c1_cleanup_ce.add_rule(Rule(Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "4", "1"), ">", "0"))
c1_cleanup_ce.add_rule(Rule(Keyword("Net Quantity", Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "1", "1")), "!=", "0"))
c1_cleanup_ce.add_leg(Leg(buy_sell="S", option_type="CE", strike_type="Fx", strike_json=get_traded_instrument_ast(1, 1, 1), expiry_type="Next Month"))
s1.add_condition(c1_cleanup_ce)

c1_cleanup_pe = Condition(ctype="Repair Once")
c1_cleanup_pe.add_rule(Rule(Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "4", "1"), ">", "0"))
c1_cleanup_pe.add_rule(Rule(Keyword("Net Quantity", Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "1", "2")), "!=", "0"))
c1_cleanup_pe.add_leg(Leg(buy_sell="S", option_type="PE", strike_type="Fx", strike_json=get_traded_instrument_ast(1, 1, 2), expiry_type="Next Month"))
s1.add_condition(c1_cleanup_pe)

strat.add_set(s1)

# ====================================================================================
# SET 2: CALL HEDGE ROLL
# ====================================================================================
s2 = SetBlock(2)
c2_entry = Condition(ctype="Entry")
# Trigger: Spot crosses CE boundary (LTP > Traded Strike of S1 E Leg 1)
c2_entry.add_rule(Rule(Keyword("LTP", Keyword("Instrument Name", "NFO,NIFTY 50,,,,")), ">", Keyword("Traded Instrument", "Entry", "strike", "NIFTY 50", "1", "1", "1")))

# Sell old CE Hedge EXACTLY at its traded strike
c2_entry.add_leg(Leg("NIFTY 50", "CE", "S", 1, strike="( Traded Instrument )", strike_type="Fx", strike_json=get_traded_instrument_ast(1, 1, 1), expiry_type="Next Month")) 
# Buy new CE Hedge at Traded Strike + HedgeRoll
c2_entry.add_leg(Leg("NIFTY 50", "CE", "B", 1, strike="( Traded Instrument + Get Runtime(HedgeRoll) )", strike_type="Fx", strike_json=get_traded_instrument_offset_ast("+", "HedgeRoll", 1, 1, 1), expiry_type="Next Month"))
s2.add_condition(c2_entry)

# Set 2 Clean Up (Rolled CE)
c2_cleanup = Condition(ctype="Repair Once")
c2_cleanup.add_rule(Rule(Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "4", "1"), ">", "0"))
c2_cleanup.add_rule(Rule(Keyword("Net Quantity", Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "2", "2")), "!=", "0"))
c2_cleanup.add_leg(Leg(buy_sell="S", option_type="CE", strike_type="Fx", strike_json=get_traded_instrument_ast(1, 2, 2), expiry_type="Next Month"))
s2.add_condition(c2_cleanup)

strat.add_set(s2)

# ====================================================================================
# SET 3: PUT HEDGE ROLL
# ====================================================================================
s3 = SetBlock(3)
c3_entry = Condition(ctype="Entry")
# Trigger: Spot crosses PE boundary (LTP < Traded Strike of S1 E Leg 2)
c3_entry.add_rule(Rule(Keyword("LTP", Keyword("Instrument Name", "NFO,NIFTY 50,,,,")), "<", Keyword("Traded Instrument", "Entry", "strike", "NIFTY 50", "1", "1", "2")))

# Sell old PE Hedge EXACTLY at its traded strike
c3_entry.add_leg(Leg("NIFTY 50", "PE", "S", 1, strike="( Traded Instrument )", strike_type="Fx", strike_json=get_traded_instrument_ast(1, 1, 2), expiry_type="Next Month"))
# Buy new PE Hedge at Traded Strike - HedgeRoll
c3_entry.add_leg(Leg("NIFTY 50", "PE", "B", 1, strike="( Traded Instrument - Get Runtime(HedgeRoll) )", strike_type="Fx", strike_json=get_traded_instrument_offset_ast("-", "HedgeRoll", 1, 1, 2), expiry_type="Next Month"))
s3.add_condition(c3_entry)

# Set 3 Clean Up (Rolled PE)
c3_cleanup = Condition(ctype="Repair Once")
c3_cleanup.add_rule(Rule(Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "4", "1"), ">", "0"))
c3_cleanup.add_rule(Rule(Keyword("Net Quantity", Keyword("Traded Instrument", "Entry", "quantity", "NIFTY 50", "1", "3", "2")), "!=", "0"))
c3_cleanup.add_leg(Leg(buy_sell="S", option_type="PE", strike_type="Fx", strike_json=get_traded_instrument_ast(1, 3, 2), expiry_type="Next Month"))
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
c4_entry.add_leg(Leg("NIFTY 50", "CE", "B", 1, strike="( Straddle CE + 100 )", strike_type="Fx", strike_json=get_traded_instrument_offset_ast("+", "HedgeRoll", 1, 2, 1), expiry_type="Next Month"))
c4_entry.add_leg(Leg("NIFTY 50", "PE", "B", 1, strike="( Straddle PE - 100 )", strike_type="Fx", strike_json=get_traded_instrument_offset_ast("-", "HedgeRoll", 1, 2, 2), expiry_type="Next Month"))
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

strat.export("Find_Strike_Iron_Fly.json")
print("Compiled Production Find Strike Iron Fly strategy to strategies/Find_Strike_Iron_Fly.json")
