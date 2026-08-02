# Tradetron AI Best Practices

When writing or modifying Tradetron strategies, the AI must strictly adhere to the following best practices derived from professional options trading architecture.

## 1. Dynamic Variables over Hardcoding
**Rule**: Never hardcode static values (like `600`, `100`, `920`) inside Complex Strike FX formulas or Condition logic if it can be parameterized.
**Reason**: Strategies require constant tweaking. If `600` is hardcoded across 4 sets and 8 legs, changing the boundary offset requires an exhaustive refactor. 
**Implementation**: Always initialize a `Variable` globally (e.g., `HedgeGap = 600`). Then, inside the AST, use the `Get Runtime` keyword (`{"name": "Get Runtime", "params": [{"type": "value", "value": "HedgeGap"}]}`) to dynamically reference it.

## 2. Margin-Optimized Leg Sequencing (Condition Splitting)
**Rule**: When entering a multi-leg spread with both Long (Buy) and Short (Sell) legs, placing them in the same Position Builder can sometimes trigger the Sell leg first, resulting in huge margin blocks by the broker. To guarantee margin benefits, physically split the execution into two conditions:
- Place all **Buy (Long Hedge)** orders in the **Entry (e.g., S1 E)** condition.
- Place all **Short (Sell)** orders in a **Repair Once (e.g., S1 R1)** condition (triggering off the same entry logic or verifying the entry legs exist).
**Reason**: Brokerages charge massive margin requirements for naked short positions. By splitting the logic into `Entry` and `Repair Once`, the system strictly forces the broker to recognize the purchased long legs before attempting to margin-check the naked shorts.
**Implementation**: Never bundle Buys and Sells in the same Entry condition if margin is a concern. Put Buys in `S1 E` and Sells in `S1 R1`. *(Note: This rule is only applicable when the sell order has an accompanied buy order acting as a hedge, like an Iron Fly. Naked short strategies do not require this split.)*

## 3. Descriptive Meta-data
**Rule**: For every strategy JSON that is built or generated, ALWAYS populate the `description` field with real, actionable information about the strategy.
**Reason**: Tradetron lists can get cluttered. Having a blank description or generic "AI Generated Strategy" makes it impossible for the user to remember what the architecture does without reading the JSON.
**Implementation**: Update the JSON generator to dynamically accept and inject HTML `<p>` tags outlining the Entry, Adjustment, and Exit logic into the `description` key at the root of the JSON.

## 4. Variable Initialization
**Rule**: When initializing global Variables, ensure the `value` and `display` fields are assigned actual values.
**Reason**: Leaving `value` blank or defining them with complex Condition blocks (`Number == Number`) causes Tradetron UI to fail to render the inputs.
**Implementation**: Initialize Variables simply with their actual base string (e.g., `( tt_Number ( '600' ) )`).

## 5. Custom Strike Formulas (`strikeType`)
**Rule**: Whenever a leg requires a dynamically calculated strike price via a custom AST formula, the `strikeType` must be `"Fx"`.
**Reason**: If the `strikeType` is left as `"ATM"` or `"Strike"`, the Tradetron backend completely ignores the formula embedded in `strikeJson` and executes a hardcoded default strike.
**Implementation**: Explicitly set `"strikeType": "Fx"` in the JSON whenever `strikeJson` is populated.


## 6. Strategy Description Detail

6. **Strategy Description Detail**: Every generated strategy JSON must include a comprehensive, human‑readable `description` field that outlines the trading intent, entry criteria, adjustment/roll logic, and exit conditions. Use the following template as a guide:

Enters a 4‑leg Ironfly options position on NIFTY index and actively adjusts the long protective hedges as the spot price trends.

Strategy Notes:
---------------
1. Entry:
   - Time: 3:15 PM (15:15 IST) on the first trading day after monthly expiry (usually Friday).
   - Selection: Sell ATM Call and Put for the next monthly expiry. Strike is selected where premiums are closest to being equal (price‑balanced strangle center) and must be a multiple of 100.
   - Expected premium collected: ₹700–800.
   - Hedges: Buy Call & Put hedges 600 points away from the straddle strike.
2. Adjustments (Rolling Hedges):
   - When spot crosses either hedge boundary (moves 600 points from center):
     - Close the profit‑making buy leg (Call hedge if Nifty goes up, Put hedge if Nifty goes down).
     - Move/roll that buy leg 100 points outward (e.g. Call strike + 100 / Put strike - 100) to lock in the profit of the long option and shift the boundary to prevent looping.
3. Exit / Hold Till Expiry:
   - Default Exit: Square off all positions on the Friday before the expiry week.
   - Hold Till Expiry Mode (HOLD_TILL_EXPIRY = True):
     - On the Friday before expiry week, close the current hedges.
     - Buy new hedges much closer (100 points away).
     - Hold this tight position and square off on Thursday (expiry day).


## 7. Strict Temporal Strike Anchoring (Traded Instrument vs LTP)
 
   - **Rule**: Whenever a strategy rolls, adjusts, or closes a leg in a subsequent Set or Condition, the `strike` formula MUST reference the exact `Traded Instrument` of the original entry leg (e.g., `Traded Instrument(Entry, strike, ...)`).
   - **Reason**: The `LTP` (Last Traded Price) keyword evaluates the *current* spot price at the exact moment the block triggers. If `LTP` is used to calculate the strike of a leg that was opened hours or days ago, it will point to a completely different, wrong strike due to price drift. 
   - **Implementation**: `LTP` is only permitted for calculating the strike of the very first, initial Entry. All subsequent adjustments must mathematically anchor to `Traded Instrument`.

