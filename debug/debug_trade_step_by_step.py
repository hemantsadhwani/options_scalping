#!/usr/bin/env python3
"""
Step-by-step debug of the 13:20 trade to understand exactly what's happening
"""

import pandas as pd
import os
import sys

# Add the current directory to Python path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from option_tools.option_trade_executor import load_trade_config, get_premium_tier

def debug_trade_step_by_step():
    """
    Debug the trade execution step by step
    """
    print("=== Step-by-Step Trade Debug ===")
    
    # Load data
    call_prices_df = pd.read_csv('./data/0307/call/call_out.csv')
    call_prices_df['datetime'] = pd.to_datetime(call_prices_df['datetime'])
    call_prices_df.set_index('datetime', inplace=True)
    
    # Add ATR calculation
    import pandas_ta as ta
    call_prices_df['ATR_5'] = ta.atr(call_prices_df['high'], call_prices_df['low'], call_prices_df['close'], length=5)
    
    # Entry details
    entry_time = pd.to_datetime('2025-07-03 13:20:00')
    entry_price = 101.1
    
    # Get trade data
    entry_bar_index = call_prices_df.index.get_loc(entry_time)
    trade_data = call_prices_df.iloc[entry_bar_index:].reset_index()
    
    # Load configuration
    trade_config = load_trade_config()
    hybrid_config = trade_config.get('HYBRID_PREMIUM', {})
    
    # Get tier info
    tier = get_premium_tier(entry_price, hybrid_config['PREMIUM_TIERS'])
    initial_sl_pct = tier.get('sl_percent', hybrid_config.get('SL_PERCENT', 6.0))
    initial_sl = entry_price * (1 - initial_sl_pct / 100)
    
    print(f"Entry Price: {entry_price}")
    print(f"Tier: {tier}")
    print(f"Initial SL: {initial_sl:.2f} ({initial_sl_pct}%)")
    print(f"Trail Start: {tier['trail_start_pct']}%")
    print(f"Breakeven Delay: {tier['breakeven_delay']} candles")
    print(f"Breakeven Move: {hybrid_config['BREAKEVEN_MOVE_PCT']}%")
    
    # Simulate the trade execution
    current_sl = initial_sl
    highest_high = trade_data.iloc[0]['high']
    trail_active = False
    candle_count = 0
    
    atr_col = f"ATR_{hybrid_config['ATR_PERIOD']}"
    
    print(f"\n=== Candle-by-Candle Execution ===")
    
    for idx, bar in trade_data.iloc[1:].iterrows():
        candle_count += 1
        prev_highest = highest_high
        highest_high = max(highest_high, bar['high'])
        
        gain_pct = (highest_high / entry_price - 1) * 100
        
        print(f"\nCandle {candle_count}: {bar['datetime']}")
        print(f"  OHLC: {bar['open']:.2f}, {bar['high']:.2f}, {bar['low']:.2f}, {bar['close']:.2f}")
        print(f"  Highest High: {prev_highest:.2f} -> {highest_high:.2f}")
        print(f"  Gain: {gain_pct:.2f}%")
        print(f"  Current SL: {current_sl:.2f}")
        
        # Check trailing activation
        if not trail_active and gain_pct >= tier['trail_start_pct']:
            trail_active = True
            print(f"  🟢 TRAILING ACTIVATED (gain {gain_pct:.2f}% >= {tier['trail_start_pct']}%)")
        
        # Update trailing SL
        if trail_active:
            atr_val = bar.get(atr_col, 0)
            atr_multiplier = tier['atr_mult']
            if bar.get('K', 50) < hybrid_config['STOCH_OVERSOLD']:
                atr_multiplier *= 0.75
            
            trailing_sl = highest_high - (atr_val * atr_multiplier)
            old_sl = current_sl
            current_sl = max(current_sl, trailing_sl)
            if current_sl != old_sl:
                print(f"  📈 Trailing SL: {old_sl:.2f} -> {current_sl:.2f} (ATR: {atr_val:.2f}, Mult: {atr_multiplier:.2f})")
        
        # Check breakeven logic
        if not trail_active and candle_count > tier['breakeven_delay'] and gain_pct >= hybrid_config['BREAKEVEN_MOVE_PCT']:
            old_sl = current_sl
            current_sl = max(current_sl, entry_price)
            if current_sl != old_sl:
                print(f"  🔄 BREAKEVEN: SL moved to entry {current_sl:.2f} (gain {gain_pct:.2f}% >= {hybrid_config['BREAKEVEN_MOVE_PCT']}%, delay {candle_count} > {tier['breakeven_delay']})")
        
        # Check SL hit
        if bar['low'] <= current_sl:
            print(f"  🛑 SL HIT: Low {bar['low']:.2f} <= SL {current_sl:.2f}")
            print(f"  Exit Price: {current_sl:.2f}")
            print(f"  Exit Reason: {'Trailing SL' if trail_active else 'SL Hit'}")
            break
        
        # Stop after reasonable number of candles for debugging
        if candle_count >= 20:
            print(f"  ... (stopping debug after 20 candles)")
            break
    
    print(f"\n=== Expected vs Actual ===")
    print(f"Expected: Should reach 206.35 high, exit at 198.0 after 45 minutes")
    print(f"Actual: Reached {highest_high:.2f} high, exited at {current_sl:.2f} after {candle_count} minutes")

if __name__ == "__main__":
    debug_trade_step_by_step()
