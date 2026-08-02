#!/usr/bin/env python3
"""
Historical Market Data Fetcher for Tradetron AI Lab
Downloads historical data for Nifty 50 Index and Stock List instruments:
- Tickers: ^NSEI, INDUSINDBK.NS, RELIANCE.NS, INFY.NS, SBIN.NS, AXISBANK.NS, HDFCBANK.NS, ICICIBANK.NS
- Intervals: 1-Minute (7d per ticker with rate-limit delays), 5-Minute (60d), Daily (6 months / 180d)
- Output Directory: Tradetron-AI-Lab/data/
"""

import os
import sys
import time

try:
    import pandas as pd
    import yfinance as yf
except ImportError:
    print("Error: pandas and yfinance packages required. Install via pip.")
    sys.exit(1)

TARGET_TICKERS = {
    'NIFTY50': '^NSEI',
    'INDUSINDBK': 'INDUSINDBK.NS',
    'RELIANCE': 'RELIANCE.NS',
    'INFY': 'INFY.NS',
    'SBIN': 'SBIN.NS',
    'AXISBANK': 'AXISBANK.NS',
    'HDFCBANK': 'HDFCBANK.NS',
    'ICICIBANK': 'ICICIBANK.NS'
}

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

def download_historical_dataset():
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"============================================================")
    print(f" HISTORICAL MARKET DATA DOWNLOADER ")
    print(f" Target Directory: {DATA_DIR}")
    print(f" Instruments ({len(TARGET_TICKERS)}): {', '.join(TARGET_TICKERS.keys())}")
    print(f"============================================================")

    # 1. Sequential 1-Minute Intraday Data Fetch (with rate-limit delays)
    print("\n[1/3] Downloading 1-Minute Intraday Data (7 Days limit)...")
    for name, sym in TARGET_TICKERS.items():
        try:
            ticker_obj = yf.Ticker(sym)
            df = ticker_obj.history(period='7d', interval='1m')
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                path = os.path.join(DATA_DIR, f"{name}_1min.csv")
                df.to_csv(path)
                print(f"  ✅ Saved 1-Min Data for {name:<12}: {len(df)} rows -> {path}")
            else:
                print(f"  ⚠️  No 1-min data returned for {name}")
        except Exception as e:
            print(f"  ❌ Error downloading 1-min data for {name}: {e}")
        time.sleep(1.5)  # Avoid YFRateLimitError

    # 2. Batch Download 5-Minute Intraday Data (60 Days)
    print("\n[2/3] Downloading 5-Minute Intraday Data (60 Days)...")
    ticker_list = list(TARGET_TICKERS.values())
    try:
        df_5m = yf.download(ticker_list, period='60d', interval='5m', group_by='ticker', progress=False)
        for name, sym in TARGET_TICKERS.items():
            try:
                sub_df = df_5m[sym].dropna() if len(ticker_list) > 1 else df_5m.dropna()
                if not sub_df.empty:
                    path = os.path.join(DATA_DIR, f"{name}_5min.csv")
                    sub_df.to_csv(path)
                    print(f"  ✅ Saved 5-Min Data for {name:<12}: {len(sub_df)} rows -> {path}")
            except Exception as e:
                pass
    except Exception as e:
        print(f"  ❌ Error downloading 5-min batch: {e}")

    # 3. Batch Download Daily Data (6 Months / 180 Days)
    print("\n[3/3] Downloading Daily Data for 6 Months (180 Days)...")
    try:
        df_6mo = yf.download(ticker_list, period='6mo', interval='1d', group_by='ticker', progress=False)
        for name, sym in TARGET_TICKERS.items():
            try:
                sub_df = df_6mo[sym].dropna() if len(ticker_list) > 1 else df_6mo.dropna()
                if not sub_df.empty:
                    path = os.path.join(DATA_DIR, f"{name}_6months_daily.csv")
                    sub_df.to_csv(path)
                    print(f"  ✅ Saved 6-Month Daily Data for {name:<12}: {len(sub_df)} rows -> {path}")
            except Exception as e:
                pass
    except Exception as e:
        print(f"  ❌ Error downloading 6-month daily batch: {e}")

    print(f"\n============================================================")
    print(f" DOWNLOAD COMPLETE ")
    print(f" Total CSV Data Files in {DATA_DIR}: {len(os.listdir(DATA_DIR))} files.")
    print(f"============================================================")

if __name__ == '__main__':
    download_historical_dataset()
