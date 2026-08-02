# Tradetron AI Lab & Strategy Suite

This repository contains the ground-truth structured data, AST auditor, backtesting engine, and production-ready strategies for the Tradetron algorithmic trading platform.

## 🌟 Key Features

1. **200+ Tradetron Keywords Knowledge Base (`/keywords/`):** Full offline JSON schema mapping of Tradetron keywords, visual logic, parameter signatures, and OCR ground truth.
2. **AST Strategy Auditor (`/scripts/tradetron_auditor.py`):** Traverses strategy JSONs, extracts chronological execution flows (Entry -> Repair -> Exit), and detects schema errors.
3. **1-Month Real Historical AST Backtester & Simulator (`/scripts/tradetron_simulator.py`):** Replays real 3-minute Nifty market data and calculates option pricing via Black-Scholes to compute PnL, Win Rates, and trade logs.
4. **Production Strategies (`/strategies/`):**
   * `momentum_strategy.json`: Nifty 50 OTM4 3-Minute Momentum Strategy with Spot Index Anchoring.
   * `Corrected_Iron_Fly.json`: Best practice margin-optimized Nifty Iron Fly with dynamic hedge rolling.

---

## 🚀 Usage Guide

### 1. Audit a Strategy JSON
To generate a chronological execution map and verify AST integrity:
```bash
python3 scripts/tradetron_auditor.py strategies/momentum_strategy.json
```

### 2. Run 1-Month Historical Backtest & PnL Simulation
To simulate 1 month of real historical 3-minute Nifty market data and compute Black-Scholes option PnL:
```bash
python3 scripts/tradetron_simulator.py strategies/momentum_strategy.json
```

---

## 📁 Repository Structure

- `/keywords/`: 200+ offline keyword JSON schemas.
- `/strategies/`: Production-ready Tradetron strategy JSON exports.
- `/scripts/`:
  - `tradetron_auditor.py`: Strategy execution flow auditor.
  - `tradetron_simulator.py`: Historical market data backtester & AST simulator.
  - `tradetron_builder.py`: Python AST strategy builder helper.
- `/examples/`: Reference multi-set strategy templates.
- `/limitations_and_constraints/`: Hard engine system limits and quirks.

---

## 🛠️ Requirements & Setup

```bash
# Create virtual environment & install dependencies
python3 -m venv venv
source venv/bin/activate
pip install pandas yfinance scipy requests
```
