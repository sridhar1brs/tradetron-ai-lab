# Example: SMA Crossover Strategy

This example demonstrates how an AI should map a natural language prompt to a structured Tradetron definition.

## Prompt (Input)
> "Buy 1 lot of Nifty 50 ATM Call Option when the 5-minute 10 SMA crosses above the 20 SMA. Exit when it crosses below."

## AI Output (Structured Tradetron Representation)

```json
{
  "strategy_name": "Nifty SMA Crossover CE",
  "sets": [
    {
      "set_id": 1,
      "entry_condition": {
        "logic": "AND",
        "conditions": [
          {
            "lhs": "SMA(Series: Close, Period: 10, Symbol: Nifty 50, Timeframe: 5 min)",
            "comparator": "Crosses Above",
            "rhs": "SMA(Series: Close, Period: 20, Symbol: Nifty 50, Timeframe: 5 min)"
          }
        ]
      },
      "position_builder": [
        {
          "leg_id": 1,
          "exchange": "NFO",
          "action": "Buy",
          "instrument_type": "CE",
          "underlying": "NIFTY 50",
          "expiry": "Current Week",
          "strike": "ATM",
          "quantity_type": "Lots",
          "quantity_value": 1
        }
      ],
      "exit_condition": {
        "logic": "AND",
        "conditions": [
          {
            "lhs": "SMA(Series: Close, Period: 10, Symbol: Nifty 50, Timeframe: 5 min)",
            "comparator": "Crosses Below",
            "rhs": "SMA(Series: Close, Period: 20, Symbol: Nifty 50, Timeframe: 5 min)"
          }
        ]
      }
    }
  ]
}
```
