# Position Builder: Instrument Selection

The Position Builder defines *what* to trade when an Entry or Repair condition is met.

## Structure of a Leg
Every position added consists of a Leg with the following parameters:
1.  **Exchange:** `NSE`, `NFO`, `MCX`, `CDS`.
2.  **Type:** `Buy` or `Sell`.
3.  **Instrument Type:** `EQ` (Equity), `FUT` (Futures), `CE` (Call Option), `PE` (Put Option).
4.  **Underlying:** e.g., `NIFTY 50`, `BANKNIFTY`, `RELIANCE`.

## Expiry (For Derivatives)
- `Current Month`, `Next Month`, `Far Month`.
- `Current Week`, `Next Week`.

## Strike Selection (For Options)
Tradetron uses a powerful `Strike FX` feature to dynamically select strikes:
- `ATM`: At the Money.
- `ITM(x)`: In the Money by `x` strikes (e.g., `ITM1`, `ITM2`).
- `OTM(x)`: Out of the Money by `x` strikes.
- `Find Strike`: Can dynamically calculate the strike based on a formula (e.g., `LTP + 500`).

## Quantity and Sizing
- **Lots:** Standard lot multiplier (e.g., 1 lot, 2 lots).
- **Formula:** Quantity can be driven by a formula, e.g., `(Capital * Risk%) / Stoploss_Points`.
