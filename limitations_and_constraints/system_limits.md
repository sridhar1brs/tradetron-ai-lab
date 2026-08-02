# Limitations and Constraints

To generate valid Tradetron strategies, the AI must strictly adhere to the following limitations:

## Condition Blocks
- **Maximum Conditions per Block:** A single `IF` block (Entry, Exit, Repair) cannot exceed 50 individual conditions.
- **Sets:** A single strategy can have multiple "Sets" (Set 1, Set 2, etc.), each containing its own Entry, Position Builder, Target, Stoploss, and Exit.
- **Nested Brackets:** Maximum nesting depth for condition brackets is typically 3 levels.

## Execution and Timeframes
- **Minimum Timeframe:** The smallest supported chart timeframe for indicators is `1 min`. "Tick" level data is not available for indicator calculation.
- **Execution Frequency:** Strategies can run continuously (checking conditions every second) or on specific intervals (1 min, 5 min). Indicator-based conditions typically evaluate on candle close unless explicitly configured for live tick evaluation (which may have lag).

## Variables
- **Runtime Variables:** Maximum number of runtime variables allowed per strategy is 50.
- **List Limits:** Creating lists (e.g., `List 1`, `List 2`) is restricted to specific limits (often 10-20 items depending on the tier).

## Keyword Specific Limits
- Certain keywords like `Position Detail` can only be used in Repair or Exit condition blocks, as they rely on an existing open position. They *cannot* be used in Set Entry conditions.
