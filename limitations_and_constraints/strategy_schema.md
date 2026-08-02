# Tradetron Strategy JSON Schema

Tradetron allows the export and import of full strategies in a highly structured `.json` format. Because this JSON relies on stringified JSON properties (Abstract Syntax Trees) and randomly generated node identifiers (`kid`), manual creation is highly prone to syntax failures. 

To bridge this gap, an AI builder utility (`scripts/tradetron_builder.py`) should always be used to generate these JSON files programmatically.

## 1. Top-Level Structure

A valid Tradetron JSON strategy contains metadata, default strategy parameters, and an array of `sets`. 

```json
{
  "_format": "2.0",
  "name": "Strategy Name",
  "description": "Strategy Description",
  "tags": [],
  "variables": [],
  "sets": [
    // Array of Set Blocks
  ],
  "capitalRequired": 50000,
  "currency": "INR",
  // ... various global execution settings
}
```

## 2. Sets and Conditions

Strategies are broken down into **Sets**. Each Set contains **Conditions** (Entry, Repair, Exit) and each Entry condition contains **Legs**.

```json
{
  "list": 0,
  "name": null,
  "conditions": [
    {
      "type": "Entry", // Or "Exit", "Universal Exit"
      "conditionJson": "{ ... stringified AST ... }",
      "visible": 1,
      "legs": [
        // Array of Position Legs to trade if condition is met
      ]
    }
  ]
}
```

## 3. The `conditionJson` Abstract Syntax Tree (AST)

The core logic of any strategy (e.g., `LTP > SMA`) is NOT stored as normal JSON. Instead, Tradetron requires it to be serialized into a **stringified JSON string** stored in the `conditionJson` property.

If you deserialize `conditionJson`, the AST looks like this:

```json
{
  "operator": "and",
  "operands": [
    {
      "type": "rule",
      "value": "builder-basic_rule_0",
      "elements": [
        {
          "name": "LTP",
          "kid": 3829, // Randomly assigned Keyword ID node
          "params": [
            { "type": "value", "value": "NIFTY 50" }
          ]
        },
        {
          "name": ">",
          "params": []
        },
        {
          "name": "SMA",
          "kid": 2856,
          "params": [
            { "type": "value", "value": "NIFTY 50" },
            { "type": "value", "value": "20" },
            { "type": "value", "value": "close" }
          ]
        }
      ]
    }
  ]
}
```

### Critical Rules for the AST:
1. **Keyword Node IDs (`kid`)**: Every single keyword node in the AST must have a `kid` property. This is a randomly generated 4-digit integer (e.g., `3829`). Tradetron's frontend relies on these unique IDs to draw the condition builder blocks.
2. **Keyword Nesting**: Keywords can be nested inside other keywords. For example, `Round(ATM_SPOT("NIFTY 50"))`. In this case, the `params` array will contain an object with `"type": "keyword"` instead of `"type": "value"`.
3. **Stringification**: The final AST must be strictly stringified and escaped (`"{\"operator\":\"and\"...}"`) before being placed in the top-level JSON file.

## 4. Position Legs

Legs describe the actual instruments to trade when a condition is met.

```json
{
  "instrument": 1855, // 1855 = NIFTY 50
  "list": 0,
  "optionType": "CE",
  "buySell": "B",
  "strikeType": "Fx",
  "strike": "( tt_round ( tt_ATM_SPOT ( 'NIFTY 50', '4' ) , '100' )  )",
  "strikeJson": "{ ... stringified AST just like conditionJson ... }",
  "qty": "tt_lots(1,'INSTRUMENT','CE')",
  "qtyType": "Lots",
  "productType": "NRML",
  "underlyingSymbol": "NIFTY 50"
}
```

*Note: If `strikeType` is set to "Fx" (Formula), it must also provide a `strikeJson` AST and a stringified formula in `strike`.*
