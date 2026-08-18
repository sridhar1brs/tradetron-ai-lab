# AGENTS.md — Tradetron Strategy Generation Rulebook

This is the single authoritative, numbered rulebook for any AI or human generating,
editing, or auditing Tradetron strategy JSON in this repository. It consolidates rules
that were previously scattered across `tradetron_auditor.py`, `known_bugs.md`,
`best_practices.md`, and inline code comments (which referenced rule numbers here without
this file ever existing).

**Before writing or modifying any strategy JSON or builder code, read this file in full.**
Rule numbers match the `[RULE N VIOLATION]` / `[RULE N WARNING]` messages emitted by
`scripts/tradetron_auditor.py` and `python3 scripts/tradetron_validator.py`, so a failing
audit can be traced back to the exact rule below. Numbering has gaps — those rule numbers
were referenced historically but never independently documented; treat any gap as "not yet
formally specified," not as "safe to ignore."

---

## Rule 5 — `strikeType` Must Be `"Fx"` Whenever `strikeJson` Is Populated
If a leg uses a custom strike formula (`strikeJson`), `strikeType` MUST be `"Fx"`. If left as
`"ATM"` or `"Strike"`, Tradetron's backend ignores `strikeJson` entirely and silently falls
back to the default strike. See `limitations_and_constraints/known_bugs.md` BUG-003.
Enforced by the auditor.

## Rule 6 — Description Field Must Be Structured HTML
Every strategy `description` must contain real, structured content (`<p>`, `<ul>` HTML)
describing Entry / Adjustment / Exit logic — never blank or the literal string
"AI Generated Strategy". See `limitations_and_constraints/best_practices.md` §3 and §6 for
the template. Enforced by the auditor (warning-level).

## Rule 8 — Universal Exit Placement
In a multi-set strategy, `"type": "Universal Exit"` MUST appear only in the **last** Set's
`conditions` array. Placing it earlier corrupts the Tradetron UI rendering (the last Set
visually nests inside the Universal Exit block). See BUG-006. Enforced by the auditor.

## Rule 9 — ConditionGroup Must Have a `children` Wrapper
A `"type": "group"` node MUST wrap its nested AST in a `children` key:
`{"type": "group", "children": {"operator": "and", "operands": [...]}}`. Omitting `children`
causes a silent import parse failure. See BUG-007. Enforced by the auditor.

## Rule 10 — `subType` and `extra` Field Shapes on Conditions
Every condition object must set `"subType": "None"` (the literal **string** `"None"`, not an
empty string `""`), and `"extra"` must be an object `{"name": null, "variables": []}`, never
an empty array `[]`. Wrong shapes break UI hydration of the condition block.

## Rule 11 — `strikeJson` Root Node Must Have an Operator Wrapper
The root of a `strikeJson` AST must be `{"operator": "and", "operands": [{"type": "rule",
"elements": [...]}]}`. A bare keyword object with no `operator`/`operands` causes a Tradetron
"Invalid root operator: None" import error. Enforced by the auditor.

## Rule 13 — Math Operation Postfix Parameter Order
`Math Operation` params must be `[Operand 1, Operand 2, Operator]` (operator symbol last —
`*`, `+`, `-`, `/`). The operator must not appear in the middle of the array. Enforced by the
auditor (warning-level).

## Rule 17 — Spot Index `Instrument Name` Must NOT Include `"Current Month"` (when used for price/strike resolution)
When an `Instrument Name` feeds directly into `LTP(...)` for ATM/strike-price resolution
(e.g. `Get Strike(..., LTP(Instrument Name(...)))`, or a rollover comparison like
`LTP(Instrument Name(...)) > Traded Instrument(...)`), the expiry slot must be **empty**
(`"NFO,NIFTY 50,,,,,"`), never `"Current Month"`. Including `"Current Month"` makes
Tradetron resolve the price from the **Current Month Futures contract** instead of Spot,
which typically trades 30–80 points away from Spot — producing wrong ATM strikes. See
BUG-001. This does **not** apply to `Instrument Name` used as the candle basis inside
`Symbol(...)` for indicator/condition timeframes (e.g.
`Symbol(Instrument Name('NFO,NIFTY 50,Current Month,,,,'), '3m', 'All')`) — trading off
Futures candles there is a valid, deliberate strategy design choice. Enforced by the
auditor recursively (any nesting depth) whenever the immediate parent keyword is `LTP`,
across `conditionJson`, `strikeJson`, and `expiryJson`.

## Rule 21 — `Leg TSL` / `Leg Exit` / `Leg SL Trail` Are Single-Use Only
These keywords do not work correctly for legs that re-enter (same leg opening a second time
from the same position). If re-entry is possible, logic must explicitly block re-entry for
that leg, or the exit macro silently fails / loops.

## Rule 24 — `Positions Detail` Field Names Are Case-Sensitive
Field parameters must be lowercase: `"quantity"`, `"price"` — never `"Quantity"` or `"PRICE"`.
Wrong case makes the condition always evaluate false or crash the engine. See BUG-012.
Enforced by the auditor.

## Rule 25 — `Traded Instrument` / `Traded Instrument Name` Coordinates Must Reference an Active Leg
The `(Set, Condition, Leg)` coordinate parameters passed to these keywords must point at a
leg that actually exists somewhere in `sets[].conditions[].legs[]`. Enforced by the auditor
(warning-level).

## Rule 27 — `Instrument Name` Must Use Exactly 5 Comma Slots
Format: `Exchange,Underlying,Expiry,OptionType,Strike,<extra>` = 5 commas / 6 slots, e.g.
`"NFO,NIFTY 50,,,,,"`. Fewer commas breaks Tradetron's backend string parser and the LTP
lookup returns `null`, breaking all downstream strike calculations. See BUG-002. Enforced by
the auditor, **with the same `strikeJson`/`expiryJson` gap noted in Rule 17.**

## Rule 28 — Leg Metadata Completeness
Every leg must have non-null `exchange`, `instrument`, and non-empty `instrumentType`
(`"OPTIDX"`, `"OPTSTK"`, `"EQ"`, `"FUT"`). Missing any of these silently aborts order
generation. See BUG-004. Enforced by the auditor.

## Rule 30 — Position Builder Leg Qty & Price Field Rendering
- `qtyType: "Lots"` → `qty` MUST use `tt_lots(N,'INSTRUMENT','CE'/'PE')` (literal string
  `'INSTRUMENT'`, not the symbol name). Plain numeric strings (`"1"`) cause a greyed-out "Clear
  Fx" state in the web UI. See BUG-008.
- `qtyType: "Value"` → `qty` MUST use `tt_value(N,'INSTRUMENT','')`.
- `isOvernightProtectionLeg` must be present (`"No"` unless genuinely an overnight leg).
- For Market orders, `limitPriceJson` / `sLTriggerJson` must be `null`.
- `qtyExprDisplay` key must exist (even if `null`) to avoid UI fallback to Fx state.
See BUG-004. Enforced by the auditor.

## Rule 31 — `instrument` Must Be an Integer Database Primary Key
Never a string, never `null`. Known IDs: `1855` = NIFTY 50, `1854` = NIFTY BANK
(BANKNIFTY), `1856` = FINNIFTY, `1857` = SENSEX, `0` = Stock List strategies. A
non-integer value leaves the Position Builder modal's Exchange/Underlying dropdowns blank.
See BUG-005 and BUG-011 (an earlier `isalpha()`-based check silently missed most invalid
values — the correct check is `isinstance(value, int)`). Enforced by the auditor.

## Rule 37 — Prefer Native ATM Over Fx Strike Formulas for Index Options
`Get Strike` / `Find Strike` formulas evaluate in real time against live tick feeds; a
1-second feed latency or a comma/format mismatch can make the formula return `0`, causing
Tradetron's order generator to fall back to the **minimum available strike** on the
**furthest LEAPS expiry** in the symbol master (e.g. a 2030 12000 CE — illiquid, price 0).
Where possible, use Native ATM (`"strikeType": "ATM"`, `"strike": "tt_ATM('NIFTY 50') + N"`)
for index options — it queries the official Exchange ATM Table directly and bypasses AST
formula evaluation entirely. See BUG-015.

## Rule 42 — OHLC Keywords Must Use `Symbol(Instrument Name(...))`, Never Bare `Instrument()`
`Close()` / `Open()` / `High()` / `Low()` params must nest
`Symbol(Instrument Name('NSE,NIFTY 50,,,,,'), '1m', 'All')`. A bare `Instrument()` keyword
(or the old `Close(Timeframe(), Instrument())` pattern) resolves to `None` in the condition
engine — silently, with no import error. Enforced by the auditor (recursively, within
`conditionJson` only — see Known Gaps).

## Rule 43 — Simulator Is Not a Substitute for the Auditor
`tradetron_simulator.py` evaluates the *intended* Python-level logic for backtesting
purposes. It is NOT a structural/schema gate. `tradetron_auditor.py` /
`tradetron_validator.py` MUST pass before any strategy is considered ready for Tradetron
import — a strategy can backtest "correctly" in the simulator while still being malformed
JSON that fails to import or executes wrong in production.

## Rule 44 — Every AST Param Object Must Have a Valid `type` Key
Every object inside a keyword's `params` array must be `{"type": "keyword", "keyword": {...}}`
or `{"type": "value", "value": "..."}`. An unwrapped keyword dict (missing/invalid `type`)
causes a Tradetron import failure: "Unknown param type: None". Enforced recursively by the
auditor (within `conditionJson` only — see Known Gaps).

## Rule 46 — Timeframe Strings Must Use Tradetron's Shorthand Enum
`Symbol(...)` timeframe parameter must be one of `1m, 2m, 3m, 4m, 5m, 10m, 15m, 30m, 1h, 2h,
4h, day, week, month`. Never `"1min"`, `"3min"`, etc. — the engine requires the shorthand
form. Enforced by the auditor (within `conditionJson` only — see Known Gaps).

---

## Other Mandatory Practices (from `limitations_and_constraints/best_practices.md`)

- **Dynamic Variables over Hardcoding**: Parameterize repeated magic numbers (hedge gaps,
  offsets) as a global `Variable` and reference via `Get Runtime('VarName')`, instead of
  hardcoding the same literal across multiple legs/sets.
- **Margin-Optimized Leg Sequencing**: For spreads with both long (buy/hedge) and short
  (sell) legs, place Buys in the Entry condition and Sells in a subsequent Repair Once
  condition, so the broker recognizes the hedge before margin-checking the naked short. Not
  required for naked-short strategies with no accompanying hedge.
- **Variable Initialization**: Global `Variable.value` must always be a real initialized
  value (e.g. `( tt_Number ( '600' ) )`), never blank or a comparison expression.
- **Strict Temporal Strike Anchoring**: `LTP` may only be used to calculate the strike of the
  very first Entry. Any subsequent roll/adjustment/repair MUST anchor to
  `Traded Instrument(...)` of the original entry leg — never recompute with `LTP`, since spot
  price drift between entry and adjustment time will point to the wrong strike.

## System Limits (from `limitations_and_constraints/system_limits.md`)

- Max 50 conditions per `IF` block (Entry/Exit/Repair).
- Max ~3 levels of nested condition-group brackets.
- Minimum indicator timeframe is 1 minute (no tick-level indicator calculation).
- Max 50 runtime variables per strategy.
- `Positions Detail` (and similar position-dependent keywords) can only be used in
  Repair/Exit blocks, never in Entry — no position exists yet at Entry time.

---

## Known Gaps in Current Tooling (read before trusting a "PASSED" audit)

1. ~~`strikeJson` and `expiryJson` are not deep-audited.~~ **Fixed**: `validate_ui_schema()`
   now runs the recursive AST checks (Rules 17, 27, 42, 44, 46) on each leg's `strikeJson`
   and `expiryJson`, not just `conditionJson` — this is exactly where strike/ATM bugs like
   BUG-001, BUG-002, and BUG-015 occur. Still double-check any *new* AST-bearing field added
   in future (e.g. `qtyJson`) gets wired into the same deep check.
2. ~~Rule 17/27 `Instrument Name` check only matched top-level rule elements.~~ **Fixed**:
   `Instrument Name` is almost always nested inside `LTP(...)`/`Symbol(...)`/`Get Strike(...)`
   rather than appearing as a top-level rule element, so the original check never actually
   fired on real strategies. It is now a recursive walk (`_check_instrument_name_recursive`)
   that finds `Instrument Name` at any depth and checks Rule 17 only when the immediate
   parent is `LTP` (price/strike context). This uncovered a real, previously-undetected
   BUG-001-pattern defect in 3 of the 13 `strategies/` Iron Fly files and in the
   `tests/known_good/good_iron_fly.json` fixture (now fixed) — run
   `python3 scripts/tradetron_validator.py` to see current status of the production files.
2. **`keywords/*.json` files do not have real parameter schemas.** The `parameters` field in
   nearly every file under `keywords/` is a placeholder
   ("Extract parameters manually or update script parser"). The only guidance is unstructured,
   sometimes OCR-garbled prose in `how_to_use_markdown` / `visual_logic_extracted`. Treat
   those fields as hints, not ground truth — cross-check the actual parameter order/count
   against a working example in `strategies/` or `examples/` for that keyword before using it
   in a new formula.
3. **`tradetron_builder.py` does not read `keywords/*.json`.** Its keyword/leg construction
   logic is hand-maintained Python, independent of the `keywords/` library. Bug fixes made in
   one place are not automatically reflected in the other.
