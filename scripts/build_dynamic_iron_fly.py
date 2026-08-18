import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from tradetron_builder import Strategy, SetBlock, Condition, ConditionGroup, Leg, Variable, Keyword, Rule, make_structured_description

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
                                            {"type": "value", "value": "NFO,NIFTY 50,,,,,"}
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

def get_strike_offset_ast(operator, var_name):
    # Builds AST for: Get Strike(Spot LTP) +/- Get Runtime(var_name)
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
                                            {"type": "value", "value": "NFO,NIFTY 50,,,,,"}
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

def build_dynamic_iron_fly():
    symbol = 'NIFTY 50'
    inst_id = 1855

    s = Strategy(
        name='Nifty Monthly IronFly Dynamic Hedge Inward Rollover',
        description=make_structured_description(
            name='Nifty Monthly IronFly with Margin-Optimized Entry & Dynamic Hedge Inward Rollover',
            underlying='NIFTY 50 Index',
            timeframe='Monthly Expiry Spreads',
            entry_logic='Margin-Optimized Split: S1 Entry buys long protective hedges (CE + PE) at (Get Strike +/- HedgeGap). S1 Repair Once 1 sells short ATM straddle after long hedges are filled to guarantee broker margin benefits. Entry Window: 9:20 AM to 3:15 PM IST.',
            exit_logic='Universal Exit on expiry day at 3:15 PM IST.',
            notes='<li>Margin-Optimized Entry: Long hedges bought in S1 Entry (S1 E), Short straddle sold in S1 Repair Once (S1 R1) once hedge fills are confirmed.</li><li>Dynamic Hedge Gap: Parameterized via HedgeGap variable (default 700 pts) using strikeType="Fx" AST formula.</li><li>Call Hedge Inward Roll: S2 Entry rolls Call hedge inward by Roll_Step (100 pts) when Spot crosses original Call hedge strike.</li><li>Put Hedge Inward Roll: S3 Entry rolls Put hedge inward by Roll_Step (100 pts) when Spot crosses original Put hedge strike.</li>'
        )
    )

    s.add_variable(Variable('HedgeGap', '700'))
    s.add_variable(Variable('Roll_Step', '100'))
    s.add_variable(Variable('HOLD_TILL_EXPIRY', '1'))

    inst_name_kw = Keyword('Instrument Name', 'NFO,NIFTY 50,,,,,')
    spot_ltp = Keyword('LTP', inst_name_kw)

    # ─── Set 1: Entry Hedges (S1 E) & Short Straddle (S1 R1) ─────────────────
    s1 = SetBlock(1)

    # S1 ENTRY: Buy Long Hedges (Margin Benefit Priority)
    c1_e = Condition('Entry')
    c1_e.add_rule(Rule(Keyword('Time', 'NSE'), '>=', 920))
    c1_e.add_rule(Rule(Keyword('Time', 'NSE'), '<', 1515))

    # S1 E Leg 1: Long Call Hedge
    l1_ce_hedge = Leg(symbol, 'CE', 'B', 1, strike='( Get Strike + Get Runtime(HedgeGap) )', strike_type='Fx', strike_json=get_strike_offset_ast('+', 'HedgeGap'), expiry_type='Current Month', instrument_id=inst_id)
    # S1 E Leg 2: Long Put Hedge
    l1_pe_hedge = Leg(symbol, 'PE', 'B', 1, strike='( Get Strike - Get Runtime(HedgeGap) )', strike_type='Fx', strike_json=get_strike_offset_ast('-', 'HedgeGap'), expiry_type='Current Month', instrument_id=inst_id)
    c1_e.add_leg(l1_ce_hedge)
    c1_e.add_leg(l1_pe_hedge)
    s1.add_condition(c1_e)

    # S1 REPAIR ONCE 1: Sell Short Straddle (After Long Hedges Fill)
    c1_r1 = Condition('Repair Once')
    c1_r1.add_rule(Rule(Keyword('Traded Instrument', 'Entry', 'quantity', symbol, '1', '1', '1'), '>', 0))

    # S1 R1 Leg 1: Short ATM Call
    l1_short_ce = Leg(symbol, 'CE', 'S', 1, strike='( Get Strike(Spot LTP) )', strike_type='Fx', strike_json=get_spot_atm_ast(), expiry_type='Current Month', instrument_id=inst_id)
    # S1 R1 Leg 2: Short ATM Put
    l1_short_pe = Leg(symbol, 'PE', 'S', 1, strike='( Get Strike(Spot LTP) )', strike_type='Fx', strike_json=get_spot_atm_ast(), expiry_type='Current Month', instrument_id=inst_id)
    c1_r1.add_leg(l1_short_ce)
    c1_r1.add_leg(l1_short_pe)
    s1.add_condition(c1_r1)

    s.add_set(s1)

    # ─── Set 2: Call Hedge Inward Roll ───────────────────────────────────────────
    s2 = SetBlock(2)
    c2_e = Condition('Entry')
    call_hedge_strike = Keyword('Traded Instrument', 'Entry', 'strike', symbol, '1', '1', '1')
    c2_e.add_rule(Rule(spot_ltp, '>=', call_hedge_strike))

    # Close original Call hedge (S1 E Leg 1)
    l2_close_old_call = Leg(symbol, 'CE', 'S', 1, strike='( Traded Instrument )', strike_type='Fx', strike_json=get_traded_instrument_ast(1, 1, 1), expiry_type='Current Month', instrument_id=inst_id)
    # Buy new Call hedge inward (S1 E Leg 1 - Roll_Step)
    l2_new_call = Leg(symbol, 'CE', 'B', 1, strike='( Traded Instrument - Get Runtime(Roll_Step) )', strike_type='Fx', strike_json=get_traded_instrument_offset_ast('-', 'Roll_Step', 1, 1, 1), expiry_type='Current Month', instrument_id=inst_id)
    c2_e.add_leg(l2_close_old_call)
    c2_e.add_leg(l2_new_call)
    s2.add_condition(c2_e)

    c2_r1 = Condition('Repair Once')
    c2_r1.add_rule(Rule(Keyword('Traded Instrument', 'Entry', 'quantity', symbol, '1', '1', '1'), '>', 0))
    c2_r1.add_rule(Rule(Keyword('Net Quantity', Keyword('Traded Instrument', 'Entry', '1', '2', '2')), '!=', 0))
    s2.add_condition(c2_r1)

    s.add_set(s2)

    # ─── Set 3: Put Hedge Inward Roll ────────────────────────────────────────────
    s3 = SetBlock(3)
    c3_e = Condition('Entry')
    put_hedge_strike = Keyword('Traded Instrument', 'Entry', 'strike', symbol, '1', '1', '2')
    c3_e.add_rule(Rule(spot_ltp, '<=', put_hedge_strike))

    # Close original Put hedge (S1 E Leg 2)
    l3_close_old_put = Leg(symbol, 'PE', 'S', 1, strike='( Traded Instrument )', strike_type='Fx', strike_json=get_traded_instrument_ast(1, 1, 2), expiry_type='Current Month', instrument_id=inst_id)
    # Buy new Put hedge inward (S1 E Leg 2 + Roll_Step)
    l3_new_put = Leg(symbol, 'PE', 'B', 1, strike='( Traded Instrument + Get Runtime(Roll_Step) )', strike_type='Fx', strike_json=get_traded_instrument_offset_ast('+', 'Roll_Step', 1, 1, 2), expiry_type='Current Month', instrument_id=inst_id)
    c3_e.add_leg(l3_close_old_put)
    c3_e.add_leg(l3_new_put)
    s3.add_condition(c3_e)

    c3_r1 = Condition('Repair Once')
    c3_r1.add_rule(Rule(Keyword('Traded Instrument', 'Entry', 'quantity', symbol, '1', '1', '2'), '>', 0))
    c3_r1.add_rule(Rule(Keyword('Net Quantity', Keyword('Traded Instrument', 'Entry', '1', '3', '2')), '!=', 0))
    s3.add_condition(c3_r1)

    s.add_set(s3)

    # ─── Set 4: Hold Till Expiry / Universal Exit ───────────────────────────────
    s4 = SetBlock(4)
    c4_e = Condition('Entry')
    c4_e.add_rule(Rule(Keyword('Get Runtime', 'HOLD_TILL_EXPIRY'), '>=', 1))
    c4_e.add_rule(Rule(Keyword('Days to Expiry', symbol), '<', 7))
    s4.add_condition(c4_e)

    # Universal Exit placed on LAST Set (Rule 8 compliant)
    g1 = ConditionGroup('and')
    g1.add_rule(Rule(Keyword('Get Runtime', 'HOLD_TILL_EXPIRY'), '==', 0))
    g1.add_rule(Rule(Keyword('Days to Expiry', symbol), '<', 7))

    g2 = ConditionGroup('and')
    g2.add_rule(Rule(Keyword('Get Runtime', 'HOLD_TILL_EXPIRY'), '==', 1))
    g2.add_rule(Rule(Keyword('Days to Expiry', symbol), '==', 0))

    ue_cond = Condition(ctype='Universal Exit', operator='or')
    ue_cond.add_rule(g1)
    ue_cond.add_rule(g2)
    s4.add_condition(ue_cond)

    s.add_set(s4)

    out_dir = os.path.join(os.path.dirname(__file__), '..', 'strategies')
    path = os.path.join(out_dir, 'Nifty_Monthly_IronFly_Dynamic_Hedge_Inward_Rollover.json')
    s.export(path)
    print(f'✅ Successfully generated {path}')

if __name__ == '__main__':
    build_dynamic_iron_fly()

