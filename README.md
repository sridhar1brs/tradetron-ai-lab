# Tradetron AI Lab & Strategy Suite

This repository contains the ground-truth structured data, AST auditor, backtesting engine, and production-ready strategies for the Tradetron algorithmic trading platform.

## 🌟 Key Features

1. **200+ Tradetron Keywords Knowledge Base (`/keywords/`):** Full offline JSON schema mapping of Tradetron keywords, visual logic, parameter signatures, and OCR ground truth.
2. **AST Strategy Auditor (`/scripts/tradetron_auditor.py`):** Traverses strategy JSONs, extracts chronological execution flows (Entry → Repair → Exit), and detects 12+ categories of schema errors.
3. **Web UI & Modal DOM Auditor (`/scripts/tradetron_web_auditor.py`):** Simulates Tradetron Web UI Vue/React modal JS rules, verifying quantity macro regex (`tt_lots(...,'INSTRUMENT',...)`), DB primary key bindings, and optional Playwright headless browser testing.
4. **Batch Strategy Validator (`/scripts/tradetron_validator.py`):** Auto-runs the auditor on ALL strategies in `strategies/` and returns pass/fail — suitable for pre-commit hooks and CI pipelines.
4. **Historical Market Data Backtester & Simulator (`/scripts/tradetron_simulator.py`):** Replays real intraday market data from 101 stocks and 14 sector indices and calculates option pricing via Black-Scholes.
5. **Production Strategies (`/strategies/`):**
   - `momentum_strategy.json`: Nifty 50 OTM 3-Minute Momentum Strategy with Spot Index Anchoring.
   - `Corrected_Iron_Fly.json`: Best-practice margin-optimized Nifty Iron Fly with dynamic hedge rolling.
   - `Stocklist_ORB_with_pyramiding_and_Trail-SL.json`: Stock F&O ORB strategy with pyramiding.

---

## 🚀 Usage Guide

### 1. Audit a Single Strategy JSON
Generate a chronological execution map and verify AST integrity:
```bash
python3 scripts/tradetron_auditor.py strategies/momentum_strategy.json
```

### 2. Run Web UI & Modal DOM Auditor
Simulate Tradetron Web UI modal JS rendering rules & macro regexes:
```bash
python3 scripts/tradetron_web_auditor.py strategies/Corrected_Iron_Fly.json
python3 scripts/tradetron_web_auditor.py --all

# Optional Playwright headless browser automation mode:
python3 scripts/tradetron_web_auditor.py --all --live
```

### 3. Batch Validate ALL Strategies
Run the AST auditor on every `.json` in `strategies/` at once:
```bash
python3 scripts/tradetron_validator.py

# Machine-readable JSON output (for CI/CD):
python3 scripts/tradetron_validator.py --json
```

### 3. Rebuild Strategies from Source
Re-generate strategy JSONs from the Python builder scripts:
```bash
cd scripts/
python3 build_momentum_strategy.py        # → strategies/momentum_strategy.json
python3 build_corrected_strategy.py       # → strategies/Corrected_Iron_Fly.json
```

### 4. Run Historical Backtest & PnL Simulation
Simulate intraday market data and compute PnL:
```bash
python3 scripts/tradetron_simulator.py strategies/momentum_strategy.json
python3 scripts/tradetron_simulator.py strategies/Stocklist_ORB_with_pyramiding_and_Trail-SL.json
```

### 5. Download Fresh Market Data
```bash
python3 scripts/download_historical_data.py
```

---

## 📁 Repository Structure

```
Tradetron-AI-Lab/
├── keywords/                   # 200+ offline Tradetron keyword JSON schemas
├── strategies/                 # Production-ready strategy JSON exports
├── examples/                   # Reference community strategy templates
├── scripts/
│   ├── tradetron_auditor.py      # Strategy execution flow auditor (single file)
│   ├── tradetron_web_auditor.py  # Web UI Vue/React modal JS & Playwright DOM auditor
│   ├── tradetron_validator.py    # Batch validator (all strategies/ at once)
│   ├── tradetron_simulator.py  # Historical market data backtester
│   ├── tradetron_builder.py    # Python AST strategy builder DSL
│   ├── build_momentum_strategy.py      # Momentum strategy builder
│   ├── build_corrected_strategy.py     # Iron Fly strategy builder
│   ├── download_historical_data.py     # Market data downloader
│   └── scratch/                # Development debug scripts (not for production)
├── limitations_and_constraints/
│   ├── best_practices.md       # Tradetron architecture best practices
│   ├── strategy_schema.md      # Strategy JSON schema documentation
│   ├── system_limits.md        # Tradetron engine hard limits
│   └── known_bugs.md           # ⭐ All confirmed engine bugs with fixes
├── position_builder/
│   └── instrument_selection.md # Complete position leg JSON schema & guide
└── logics_and_operators/
    └── comparators.md          # Condition logic operators reference
```

---

## 🛠️ Requirements & Setup

```bash
# Create virtual environment & install dependencies
python3 -m venv venv
source venv/bin/activate
pip install pandas yfinance scipy requests
```

---

## 🔑 Critical Rules Quick Reference

| Rule | Key Point |
|---|---|
| **Instrument Name (Spot)** | Always `"NFO,NIFTY 50,,,,,"` — 5 commas, no "Current Month" |
| **strikeType** | Must be `"Fx"` whenever `strikeJson` is populated |
| **instrument field** | Must be integer DB PK: `1855` (NIFTY50), `1854` (BANKNIFTY), `0` (Stocks) |
| **qty format** | `tt_lots(1,'NIFTY 50','CE')` — never plain `"1"` |
| **Universal Exit** | Must be in the LAST set's conditions array |
| **Next Month expiry** | Use `"Next Month"` + `tt_next_monthexpiry()` for monthly strategies |
| **Traded Instrument** | Always anchor subsequent rolls to Traded Instrument, never re-calculate with LTP |

See `limitations_and_constraints/known_bugs.md` for detailed documentation of all confirmed engine quirks.
