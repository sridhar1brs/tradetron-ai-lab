# Tradetron Engine — Known Bugs & Gotchas

This document records every confirmed Tradetron engine quirk discovered through debugging. Each entry includes the root cause, detection method, and fix.

---

## BUG-001: `"Current Month"` in Spot LTP Instrument Name → Uses Futures Price

**Severity**: 🔴 Critical — Produces wrong ATM strike (~50-80 pts off)

**Symptom**: Strategy enters options at wrong strikes. Nifty 50 options selected are 50-80 points away from actual ATM on Spot index.

**Root Cause**: When `Instrument Name` includes `"Current Month"` in the expiry slot, Tradetron resolves LTP using the **Current Month Futures contract** price, not the Spot index. Futures typically trade at a premium of 30-80 points over Spot.

**Broken**:
```json
{"type": "value", "value": "NFO,NIFTY 50,Current Month,,,,"}
```

**Fixed**:
```json
{"type": "value", "value": "NFO,NIFTY 50,,,,,"}
```

**Detection**: Auditor Rule 17 checks for `"Current Month"` in Spot Index references.

**See Also**: AGENTS.md Rule 17

---

## BUG-002: Wrong Comma Count in `Instrument Name` for Spot LTP → Returns `null`

**Severity**: 🔴 Critical — Spot LTP always returns null, breaking all strike calculations

**Symptom**: Strategy either errors on import, or all Get Strike formulas return null/0 as the spot price, causing orders at incorrect strikes.

**Root Cause**: Tradetron's backend Instrument Name string parser expects **5 commas** (6 slots: `Exchange, Underlying, Expiry, OptionType, Strike, <extra>`). Using fewer commas causes the parser to fail and return `null` for the LTP lookup.

**Broken** (4 commas):
```
"NFO,NIFTY 50,,,,"
```

**Fixed** (5 commas):
```
"NFO,NIFTY 50,,,,,"
```

**Detection**: Auditor Rule 27 counts commas in `Instrument Name` strings.

**See Also**: AGENTS.md Rule 27

---

## BUG-003: `strikeType: "ATM"` With Populated `strikeJson` → Formula Completely Ignored

**Severity**: 🔴 Critical — Silent wrong behavior, strategy executes at raw ATM instead of custom formula

**Symptom**: Despite a complex custom strike formula in `strikeJson`, orders are placed at the raw ATM strike.

**Root Cause**: Tradetron's backend checks `strikeType` first. If it's `"ATM"` or `"Strike"`, it ignores `strikeJson` entirely and uses the default strike selection.

**Fixed**: Always set `"strikeType": "Fx"` when `strikeJson` is populated.

**Detection**: Auditor Rule 5 checks for `strikeJson` without `strikeType: "Fx"`.

**See Also**: AGENTS.md Rule 5

---

## BUG-004: `Leg.to_dict()` Missing Required UI Fields → Silent Order Routing Failure

**Severity**: 🔴 Critical — Tradetron's order router silently aborts order generation

**Symptom**: Strategy imports but legs do not execute, or UI shows corrupted position builder.

**Missing fields and their impacts**:

| Field | Required Value | Impact if Missing |
|---|---|---|
| `exchange` | `"NFO"` | Order router cannot determine exchange |
| `instrumentType` | `"OPTIDX"` | Cannot resolve instrument type |
| `isOvernightProtectionLeg` | `"No"` | UI rendering fallback |
| `qtyExprDisplay` | `null` | Quantity shows as Fx greyed state |
| `limitPrice` | `null` | Non-null triggers limit order mode |
| `limitPriceJson` | `null` | Same |
| `sLTriggerJson` | `null` | Same |
| `tmp` | `0` | Required UI rendering field |
| `entryTrigger` / `entryLimit` | `null` | Missing fields cause UI errors |

**Detection**: Auditor Rules 28, 30.

**See Also**: AGENTS.md Rules 28, 30

---

## BUG-005: `instrument` Field Not Integer → Tradetron UI Dropdowns Remain Blank

**Severity**: 🔴 Critical — Position Builder modal dropdowns (Exchange, Type, Underlying) stay blank

**Symptom**: After importing strategy, opening the Position Builder modal shows all top dropdowns (Exchange, Instrument, Underlying) as blank/unselected.

**Root Cause**: Tradetron uses the `instrument` integer as a database primary key to populate UI dropdowns. String values or `null` cause the dropdown lookup to return nothing.

**Known DB Primary Keys**:
- `1855` → NIFTY 50 options
- `1854` → BANK NIFTY options
- `0` → Stock list strategies

**Detection**: Auditor Rule 31 checks `instrument` is an integer and validates known values.

**See Also**: AGENTS.md Rule 31

---

## BUG-006: `Universal Exit` in First Set of Multi-Set Strategy → UI Corruption

**Severity**: 🔴 Critical — Tradetron UI renders the last Set inside the Universal Exit block

**Symptom**: In the strategy dashboard, the last Set appears visually inside the Universal Exit section. The strategy cannot be edited correctly.

**Root Cause**: Tradetron's frontend maps `Universal Exit` by position in the `sets` array. In multi-set strategies, it expects it in the LAST set's conditions.

**Fixed**: Always append Universal Exit to `sets[-1]["conditions"]`.

**Detection**: Auditor Rule 8.

**See Also**: AGENTS.md Rule 8

---

## BUG-007: `ConditionGroup` Without `"children"` Wrapper → Import Parse Error

**Severity**: 🔴 Critical — Strategy fails to import with a silent "missing children dict" error

**Symptom**: Strategy import appears to succeed but conditions are blank or incorrectly rendered.

**Broken**:
```json
{"type": "group", "operator": "and", "operands": [...]}
```

**Fixed**:
```json
{"type": "group", "children": {"operator": "and", "operands": [...]}}
```

**Detection**: Auditor Rule 9.

**See Also**: AGENTS.md Rule 9

---

## BUG-008: `qty` as Plain Number String with `qtyType: "Lots"` → Greyed-Out Fx State

**Severity**: 🟡 Important — Quantity box shows as greyed Fx override instead of numeric input

**Symptom**: Tradetron's web UI shows a greyed-out "Clear Fx" button next to the quantity field. The quantity appears to work but cannot be edited from the UI.

**Broken**: `"qty": "1"` with `"qtyType": "Lots"`

**Fixed**: `"qty": "tt_lots(1,'NIFTY 50','CE')"` — use the `tt_lots()` macro.

**Detection**: Auditor Rule 30.

**See Also**: AGENTS.md Rule 30

---

## BUG-009: `expiry_type` Fallthrough in Builder → Wrong Expiry Silently Used

**Severity**: 🟡 Important — Iron Fly or multi-month strategies trade wrong expiry contract

**Symptom**: Monthly short straddle legs execute on Current Month instead of Next Month options.

**Root Cause**: `tradetron_builder.py` original code used an if-else that defaulted any unknown expiry type to `tt_curr_monthexpiry`. Passing `"Next Month"` was silently converted to Current Month.

**Fixed**: Full expiry map with `ValueError` for unsupported values:
```python
EXPIRY_TYPE_MAP = {
    "Current Week":  "tt_curr_weekexpiry",
    "Next Week":     "tt_next_weekexpiry",
    "Current Month": "tt_curr_monthexpiry",
    "Next Month":    "tt_next_monthexpiry",
    "Far Month":     "tt_far_monthexpiry",
}
```

---

## BUG-010: `Strategy.export()` Uses Relative `base_strategy.json` Path → `FileNotFoundError`

**Severity**: 🟡 Important — Builder scripts fail when run from project root

**Symptom**: `FileNotFoundError: [Errno 2] No such file or directory: 'base_strategy.json'`

**Root Cause**: The path was resolved relative to `os.getcwd()` (the shell's current directory), not the script's location.

**Fixed**: Use `os.path.dirname(os.path.abspath(__file__))` to resolve the base template path relative to the script file, not the working directory.

---

## BUG-011: Auditor `Rule 31` Used `isalpha()` → Missed Most Invalid Instrument Values

**Severity**: 🟡 Important — Auditor gives false "PASSED" on strategies with string/null instrument IDs

**Symptom**: Auditor reports no Rule 31 violations even when `instrument` is `"NFO"`, `None`, or `"NIFTY 50"`.

**Root Cause**: `str.isalpha()` returns `False` for strings with spaces (`"NIFTY 50"`) or digits (`"1855"` as string), so they passed the check.

**Fixed**: `if not isinstance(inst_val, int)` — any non-integer instrument value is flagged.

---

## BUG-012: `Positions Detail` Field Names are Case-Sensitive

**Severity**: 🟡 Important — Condition always evaluates False or crashes Tradetron engine

**Symptom**: `Positions Detail` condition never fires even when positions exist.

**Root Cause**: Tradetron requires lowercase field names: `"quantity"` not `"Quantity"`, `"price"` not `"Price"`.

**Detection**: Auditor Rule 24.

**See Also**: AGENTS.md Rule 24

---

## BUG-013: `Leg TSL` / `Leg Exit` / `Leg SL Trail` Parameters Must Be Flat Primitives

**Severity**: 🔴 Critical — Tradetron web dashboard crashes or corrupts block on import

**Symptom**: Strategy import hangs or the block appears corrupted in the UI.

**Root Cause**: These macro keywords require flat string/numeric parameters in their `params` array. Embedding nested keyword AST objects (e.g., `Get Runtime`) inside the parameter list causes the web dashboard's JS modal parser to fail.

**Broken**: `[..., {"type": "keyword", "keyword": {"name": "Get Runtime", ...}}]`

**Fixed**: `[..., {"type": "value", "value": "1.5"}]` — always use literal primitives.

**Detection**: Auditor macro keyword primitive check.

**See Also**: AGENTS.md Rule 21

---

## BUG-014: Simulator Data Directory Mismatch

**Severity**: 🟡 Important — Simulator always reports 0 trades with empty output

**Symptom**: `tradetron_simulator.py` reports 0 stocks tested even when data exists.

**Root Cause**: `download_historical_data.py` saved files to `data/*.csv` (flat). The simulator originally read from `data/stocks/*.csv` (subdirectory). The directories never matched.

**Fixed**: Simulator now checks subdirectory first, falls back to flat `data/` dir, then tries `data/*.csv`.

---

*Last Updated: 2026-08-03*
*All bugs above are verified and fixes are implemented in the codebase.*
