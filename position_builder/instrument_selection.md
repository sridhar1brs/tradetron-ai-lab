# Position Builder: Instrument Selection

The Position Builder defines *what* to trade when an Entry or Repair condition is met.

---

## Structure of a Leg

Every position added consists of a Leg with the following parameters:

1. **Exchange**: `NSE`, `NFO`, `MCX`, `CDS`
2. **Type**: `Buy` or `Sell`
3. **Instrument Type**: `OPTIDX` (Index Options), `OPTSTK` (Stock Options), `EQ` (Equity), `FUT` (Futures)
4. **Underlying**: e.g., `NIFTY 50`, `NIFTY BANK`, `RELIANCE`

---

## Required Leg JSON Schema (Full)

> [!IMPORTANT]
> All fields below are **required** in the exported JSON. Missing fields cause order routing failures or UI corruption.

```json
{
  "exchange": "NFO",
  "instrument": 1855,
  "instrumentType": "OPTIDX",
  "underlyingSymbol": "NIFTY 50",
  "list": 0,
  "optionType": "CE",
  "buySell": "B",
  "productType": "NRML",
  "expiryType": "Current Month",
  "expiry": "tt_curr_monthexpiry('NIFTY 50')",
  "expiryJson": null,
  "expiryDisplay": null,
  "strikeType": "Fx",
  "strike": "( Get Strike + Get Runtime(HedgeGap) )",
  "strikeJson": "{...AST...}",
  "strikeDisplay": null,
  "qty": "tt_lots(1,'NIFTY 50','CE')",
  "qtyType": "Lots",
  "qtyDisplay": "1",
  "qtyJson": null,
  "qtyExprDisplay": null,
  "limitPrice": null,
  "limitPriceJson": null,
  "targetLimit": null,
  "targetTrigger": null,
  "sLLimit": null,
  "sLTrigger": null,
  "sLTriggerJson": null,
  "entryTrigger": null,
  "entryLimit": null,
  "isOvernightProtectionLeg": "No",
  "tmp": 0
}
```

---

## Database Instrument Primary Key (`instrument` field)

> [!CAUTION]
> The `instrument` field MUST be an **integer** database primary key, NOT a string. Using a string causes Tradetron UI dropdowns to remain blank in the Position Builder modal.

| Underlying | `instrument` value |
|---|---|
| NIFTY 50 (Index Options) | `1855` |
| NIFTY BANK (Bank Nifty) | `1854` |
| Stock List strategies | `0` |

---

## Expiry Types and Macros

| Human-Readable | JSON `expiryType` | Expiry Macro |
|---|---|---|
| Current Week | `"Current Week"` | `tt_curr_weekexpiry('NIFTY 50')` |
| Next Week | `"Next Week"` | `tt_next_weekexpiry('NIFTY 50')` |
| Current Month | `"Current Month"` | `tt_curr_monthexpiry('NIFTY 50')` |
| Next Month | `"Next Month"` | `tt_next_monthexpiry('NIFTY 50')` |
| Far Month | `"Far Month"` | `tt_far_monthexpiry('NIFTY 50')` |

> [!WARNING]
> For monthly Iron Fly strategies, the short straddle legs should use **Next Month** expiry (`tt_next_monthexpiry`), since entry is typically done the day after current month expiry.

---

## Strike Selection

### Standard Modes
- `"strikeType": "ATM"` — Tradetron selects the At-The-Money strike automatically (based on **Futures** price by default)
- `"strikeType": "Strike"` — Use the literal value in the `strike` field

### Custom Formula Mode (`Fx`)

> [!IMPORTANT]
> If a leg uses a dynamically-calculated strike (e.g., Spot ATM + 600), you MUST set `"strikeType": "Fx"`. If left as `"ATM"` or `"Strike"`, Tradetron will **completely ignore** the `strikeJson` formula.

```json
{
  "strikeType": "Fx",
  "strike": "( Get Strike + Get Runtime(HedgeGap) )",
  "strikeJson": "{\"operator\":\"and\",\"operands\":[{\"type\":\"rule\",\"elements\":[...]}]}"
}
```

**`strikeJson` AST Root Structure** (required):
```json
{
  "operator": "and",
  "operands": [
    {
      "type": "rule",
      "value": "builder-basic_rule_0",
      "elements": [
        {"name": "Get Strike", "kid": 1000, "params": [...]},
        {"name": "+", "params": []},
        {"name": "Get Runtime", "kid": 1001, "params": [{"type": "value", "value": "HedgeGap"}]}
      ]
    }
  ]
}
```

### Spot-Based ATM (Correct Pattern)
To select strikes based on **Spot Index** LTP (not Futures), use:
```json
{
  "name": "Get Strike",
  "params": [
    {"type": "value", "value": "NIFTY 50"},
    {"type": "keyword", "keyword": {
      "name": "LTP",
      "params": [{
        "type": "keyword",
        "keyword": {
          "name": "Instrument Name",
          "params": [
            {"type": "value", "value": "NFO,NIFTY 50,,,,,"}
          ]
        }
      }]
    }}
  ]
}
```

> [!CAUTION]
> The `Instrument Name` string for **Spot** index MUST have exactly **5 commas** (`NFO,NIFTY 50,,,,,`) and NO expiry slot filled. Using `"Current Month"` fetches Futures price. Using 4 commas returns `null`.

---

## Quantity Format

| Mode | `qtyType` | `qty` format | Example |
|---|---|---|---|
| Lots | `"Lots"` | `tt_lots(N,'SYMBOL','TYPE')` | `tt_lots(1,'NIFTY 50','CE')` |
| Value | `"Value"` | `tt_value(AMOUNT,'SYMBOL','')` | `tt_value(10000,'NIFTY 50','')` |

> [!WARNING]
> Using a plain number like `"1"` for `qty` with `qtyType: "Lots"` causes the Tradetron UI to show a greyed "Clear Fx" button — the quantity appears correct but cannot be edited from the dashboard.

---

## Traded Instrument Reference (for Roll/Adjust Legs)

When a subsequent Set or Repair condition needs to close or roll a previously opened leg, reference it by coordinate `(Set, Condition, Leg)`:

```json
{
  "name": "Traded Instrument",
  "params": [
    {"type": "value", "value": "Entry"},
    {"type": "value", "value": "strike"},
    {"type": "value", "value": "NIFTY 50"},
    {"type": "value", "value": "1"},   // Set number
    {"type": "value", "value": "1"},   // Condition number (Entry=1, first Repair=1)
    {"type": "value", "value": "1"}    // Leg number
  ]
}
```

> [!IMPORTANT]
> **Always** use `Traded Instrument` for subsequent adjustments. Never use `LTP` to recalculate a strike that was set at entry — the spot will have drifted.
