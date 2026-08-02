# Logics and Operators

Tradetron builds strategies using condition blocks. Each block is an `IF` statement that can chain multiple conditions.

## Comparators
When comparing two keywords or values, the following comparators are supported:

- `>` : Greater Than
- `<` : Less Than
- `>=` : Greater Than or Equal To
- `<=` : Less Than or Equal To
- `==` : Equal To
- `!=` : Not Equal To
- `Crosses Above` : The Left Hand Side (LHS) was previously lower than the Right Hand Side (RHS), and is now higher.
- `Crosses Below` : The LHS was previously higher than the RHS, and is now lower.

## Logical Operators
Conditions within a block can be chained using logical operators:
- `AND`: All conditions must be True.
- `OR`: At least one condition must be True.

*Note: Tradetron evaluates conditions sequentially. When mixing AND and OR, use condition groups (brackets) to ensure proper evaluation order.*

## Math Operators
Math operators can be applied to numerical return values before comparison:
- `+` (Add)
- `-` (Subtract)
- `*` (Multiply)
- `/` (Divide)

*Example:* `LTP(Instrument) > ( SMA(Close, 20) * 1.05 )`
