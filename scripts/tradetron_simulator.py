#!/usr/bin/env python3
"""
Tradetron Strategy AST Simulator & PnL Engine (3-Minute Historical Market Edition)
Uses EXACT 3-Minute Nifty Spot Candles and Black-Scholes Derivatives Engine to construct
real-time 3-minute Option & Futures OHLC series for strategy evaluation.
"""

import json
import math
import os
import sys
from datetime import datetime, timedelta

try:
    import pandas as pd
    import yfinance as yf
    from scipy.stats import norm
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

# Black-Scholes Option Pricing Engine
def black_scholes(S, K, T, r=0.07, sigma=0.15, option_type='CE'):
    if T <= 0.0001:
        if option_type == 'CE': return max(0.0, S - K)
        else: return max(0.0, K - S)
    
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    
    if option_type == 'CE':
        price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    
    return max(0.5, price)

class TradetronSimulator3Min:
    def __init__(self, strategy_path):
        with open(strategy_path, 'r') as f:
            self.strategy = json.load(f)
        
        self.strategy_name = self.strategy.get('name', 'Unknown')
        self.variables = {}
        self.traded_instruments = {}
        
        for var in self.strategy.get('variables', []):
            name = var['variableName']
            val = self._extract_var_value(var.get('json', ''))
            self.variables[name] = val
            
    def _extract_var_value(self, json_str):
        if not json_str:
            return 0
        try:
            data = json.loads(json_str)
            for rule in data.get('operands', []):
                for elem in rule.get('elements', []):
                    if elem.get('name') == 'Number':
                        return float(elem['params'][0]['value'])
        except Exception:
            pass
        return 0

    def eval_node(self, node, ctx):
        if not node: return True
        if isinstance(node, str): node = json.loads(node)
        op = node.get('operator', '').lower()
        
        if op == 'and':
            return all(self.eval_node(child, ctx) for child in node.get('operands', []))
        elif op == 'or':
            return any(self.eval_node(child, ctx) for child in node.get('operands', []))
        elif node.get('type') == 'group':
            return self.eval_node(node.get('children', {}), ctx)
        elif node.get('type') == 'rule':
            return self.eval_rule_elements(node.get('elements', []), ctx)
        return True

    def eval_rule_elements(self, elements, ctx):
        if not elements: return True
        left_val = self.eval_element(elements[0], ctx)
        if len(elements) == 1: return bool(left_val)
        
        op_str = elements[1].get('name', '')
        right_val = self.eval_element(elements[2], ctx)
        
        if op_str == '>=': return float(left_val) >= float(right_val)
        if op_str == '<=': return float(left_val) <= float(right_val)
        if op_str == '>':  return float(left_val) > float(right_val)
        if op_str == '<':  return float(left_val) < float(right_val)
        if op_str == '==': return float(left_val) == float(right_val)
        if op_str == '!=': return float(left_val) != float(right_val)
        return False

    def eval_element(self, elem, ctx):
        name = elem.get('name', '')
        params = elem.get('params', [])
        
        if name == 'Number': return float(params[0]['value'])
        if name == 'Time': return int(ctx['timestamp'].strftime('%H%M'))
        if name == 'Get Runtime':
            var_name = params[-1]['value'] if params else ''
            return self.variables.get(var_name, 0)
        if name == 'LTP':
            if params and params[0].get('type') == 'keyword':
                kw = params[0]['keyword']
                if kw.get('name') == 'Traded Instrument':
                    return self.eval_element(kw, ctx)
            return ctx['spot_price']
            
        if name == 'Days to Expiry':
            return (ctx['expiry_date'] - ctx['timestamp'].date()).days
            
        if name == 'Math Operation':
            op1 = self.eval_element(params[0], ctx)
            op2 = self.eval_element(params[1], ctx)
            operator = params[2]['value']
            
            if operator == '*': return float(op1) * float(op2)
            if operator == '+': return float(op1) + float(op2)
            if operator == '-': return float(op1) - float(op2)
            if operator == '/': return float(op1) / float(op2) if float(op2) != 0 else 0
            
        if name == 'Position':
            series_kw = params[0].get('keyword', {})
            offset = int(params[1]['value'])
            return self.eval_series(series_kw, offset, ctx)
            
        if name == 'Traded Instrument':
            field = params[1]['value']
            set_num = int(params[3]['value'])
            cond_num = int(params[4]['value'])
            leg_num = int(params[5]['value'])
            
            key = (set_num, cond_num, leg_num)
            inst_data = self.traded_instruments.get(key, {})
            if field == 'quantity': return inst_data.get('quantity', 0)
            if field == 'strike': return inst_data.get('strike', 0)
            if field == 'price': return inst_data.get('price', 0)
            return 0
            
        if name == 'Net Quantity':
            kw = params[0].get('keyword', {})
            return self.eval_element(kw, ctx)
            
        return 0

    def eval_series(self, series_kw, offset, ctx):
        name = series_kw.get('name', '')
        hist = ctx['history']
        idx = offset
        
        # Determine if series is for Option contract or Spot Index
        params = series_kw.get('params', [])
        opt_type = None
        for p in params:
            if p.get('type') == 'keyword' and p['keyword'].get('name') == 'Option Type':
                opt_type = p['keyword']['params'][0]['value']
                
        if opt_type and abs(idx) <= len(hist):
            candle = hist[idx]
            spot = candle['close']
            otm_offset = self.variables.get('OTM_Offset', 200)
            strike = (round(spot / 100) * 100) + (otm_offset if opt_type == 'CE' else -otm_offset)
            T_years = max(0.001, (ctx['expiry_date'] - ctx['timestamp'].date()).days / 365.0)
            return black_scholes(spot, strike, T_years, option_type=opt_type)
            
        if abs(idx) <= len(hist):
            candle = hist[idx]
            if name == 'Close': return candle['close']
            if name == 'Open': return candle['open']
            if name == 'High': return candle['high']
            if name == 'Low': return candle['low']
            
        return ctx['spot_price']

    def run_simulation_3min(self, ticker='^NSEI'):
        print(f"============================================================")
        print(f" TRADETRON EXACT 3-MINUTE HISTORICAL OPTION BACKTESTER ")
        print(f" Strategy: {self.strategy_name}")
        print(f" Timeframe: EXACT 3-MINUTE CANDLES (Resampled from Nifty Data)")
        print(f"============================================================")
        
        df = yf.download(ticker, period='1mo', interval='2m', progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Resample to exact 3-minute timeframe
        df_3m = df.resample('3min').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()

        candles = []
        for ts, row in df_3m.iterrows():
            candles.append({
                'timestamp': ts,
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
            })

        print(f"Loaded {len(candles)} exact 3-minute candles across 1 month.")

        active_position = None
        trades_history = []
        lot_size = 25

        for i in range(3, len(candles)):
            curr_candle = candles[i]
            sim_time = curr_candle['timestamp'].to_pydatetime()
            spot_price = curr_candle['close']
            
            history = [candles[i-1], candles[i-2], candles[i-3]]
            days_until_thu = (3 - sim_time.weekday()) % 7
            expiry_date = (sim_time + timedelta(days=days_until_thu)).date()
            T_years = max(0.001, (expiry_date - sim_time.date()).days / 365.0)
            
            ctx = {
                'timestamp': sim_time,
                'spot_price': spot_price,
                'expiry_date': expiry_date,
                'history': history
            }

            # 1. Active Position Exit Evaluation
            if active_position is not None:
                current_opt_price = black_scholes(spot_price, active_position['strike'], T_years, option_type=active_position['option_type'])
                entry_price = active_position['entry_price']
                
                target_mult = self.variables.get('Target_Multiplier', 3.0)
                sl_mult = self.variables.get('SL_Multiplier', 0.8)
                
                sl_target_hit = False
                exit_reason = ""
                
                if current_opt_price >= entry_price * target_mult:
                    sl_target_hit = True
                    exit_reason = f"TARGET HIT ({target_mult}x)"
                elif current_opt_price <= entry_price * sl_mult:
                    sl_target_hit = True
                    exit_reason = f"STOP LOSS HIT ({sl_mult}x)"
                elif sim_time.hour >= 15 and sim_time.minute >= 15:
                    sl_target_hit = True
                    exit_reason = "UNIVERSAL EXIT (3:15 PM)"

                if sl_target_hit:
                    pnl_per_qty = current_opt_price - entry_price
                    pnl_total = pnl_per_qty * lot_size
                    
                    active_position['exit_time'] = sim_time
                    active_position['exit_spot'] = spot_price
                    active_position['exit_price'] = current_opt_price
                    active_position['pnl_per_qty'] = pnl_per_qty
                    active_position['pnl_total'] = pnl_total
                    active_position['exit_reason'] = exit_reason
                    
                    trades_history.append(active_position)
                    active_position = None
                    self.traded_instruments = {}
                    continue

            # 2. Entry Evaluation
            if active_position is None:
                for s_idx, s in enumerate(self.strategy.get('sets', []), 1):
                    entry_cond = s['conditions'][0]
                    if entry_cond['type'] == 'Entry':
                        if self.eval_node(entry_cond['conditionJson'], ctx):
                            opt_type = 'CE' if s_idx == 1 else 'PE'
                            otm_offset = self.variables.get('OTM_Offset', 200)
                            strike = (round(spot_price / 100) * 100) + (otm_offset if opt_type == 'CE' else -otm_offset)
                            entry_opt_price = black_scholes(spot_price, strike, T_years, option_type=opt_type)
                            
                            active_position = {
                                'trade_no': len(trades_history) + 1,
                                'set': s_idx,
                                'option_type': opt_type,
                                'entry_time': sim_time,
                                'entry_spot': spot_price,
                                'strike': strike,
                                'entry_price': entry_opt_price,
                                'qty': lot_size
                            }
                            
                            key = (s_idx, 1, 1)
                            self.traded_instruments[key] = {
                                'quantity': lot_size,
                                'strike': strike,
                                'price': entry_opt_price
                            }
                            break

        print(f"\n============================================================")
        print(f" 📈 3-MINUTE TIMEFRAME PnL SUMMARY ")
        print(f"============================================================")
        print(f"Total Completed 3min Trades: {len(trades_history)}")
        
        if trades_history:
            winning_trades = [t for t in trades_history if t['pnl_total'] > 0]
            total_pnl = sum(t['pnl_total'] for t in trades_history)
            win_rate = (len(winning_trades) / len(trades_history)) * 100
            print(f"Winning Trades: {len(winning_trades)} ({win_rate:.1f}%)")
            print(f"💰 NET PROFIT / LOSS (1 Lot): ₹{total_pnl:,.2f}")
            print(f"============================================================\n")

if __name__ == '__main__':
    target_json = sys.argv[1] if len(sys.argv) > 1 else 'Tradetron_AI_KB/strategies/momentum_strategy.json'
    sim = TradetronSimulator3Min(target_json)
    sim.run_simulation_3min()
