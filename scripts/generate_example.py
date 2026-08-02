from tradetron_builder import Strategy, SetBlock, Condition, Rule, Keyword, Leg
import os

# 1. Initialize the Strategy
strategy = Strategy(name="AI Generated SMA Crossover Strategy")

# 2. Define the Entry Condition (Time >= 0915 and LTP > SMA(20))
entry_condition = Condition(ctype="Entry")
time_keyword = Keyword("Time", "NSE")
entry_condition.add_rule(time_keyword >= 915)

ltp_keyword = Keyword("LTP", "NIFTY 50")
sma_keyword = Keyword("SMA", "NIFTY 50", 20, "close")
entry_condition.add_rule(ltp_keyword > sma_keyword)

# 3. Add the Legs to trade when the Entry condition is met
call_leg = Leg(instrument_symbol="NIFTY 50", option_type="CE", buy_sell="B", lots=1, strike="ATM")
entry_condition.add_leg(call_leg)

# 4. Define the Exit Condition (LTP < SMA(20) or Time >= 1515)
# Note: In tradetron, 'OR' blocks require a different operator structure, but for simplicity we'll just use AND for now: (Time >= 1515)
exit_condition = Condition(ctype="Exit")
exit_condition.add_rule(time_keyword >= 1515)

# 5. Create a Set block and add the conditions
set_1 = SetBlock(set_number=1)
set_1.add_condition(entry_condition)
set_1.add_condition(exit_condition)

# 6. Add the set to the strategy
strategy.add_set(set_1)

# 7. Export the complete Strategy to a Tradetron importable JSON
output_path = os.path.join(os.path.dirname(__file__), "test_strategy.json")
strategy.export(output_path, base_template_path=os.path.join(os.path.dirname(__file__), "base_strategy.json"))

print(f"Successfully generated Tradetron importable Strategy at {output_path}")
