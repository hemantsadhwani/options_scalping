#!/usr/bin/env python3
"""
Debug script to analyze the 13:20 Call trade that should be +95.85% but is showing 0%
"""

import pandas as pd
import os
import sys
from datetime import datetime, timedelta

# Add the current directory to Python path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from option_tools.option_trade_executor import execute_hybrid_premium_trade, load_trade_config

def debug_13_20_call_trade():
    """
    Debug the specific 13:20 Call trade
    """
    print("=== Debugging 13:20 Call Trade ===")
    
    # Load data
    call_prices_df = pd.read_csv('./data/0307/call/call_out.csv')
    call_prices_df['datetime'] = pd.to_datetime(call_prices_df['datetime'])
    call_prices_df.set_index('datetime', inplace=True)
    
    # Add ATR calculation
    import pandas_ta as ta
    call_prices_df['ATR_5'] = ta.atr(call_prices_df['high'], call_prices_df['low'], call_prices_df['close'], length=5)
    
    # Entry details
    entry_time = pd.to_datetime('2025-07-03 13:20:00')
    entry_price = 101.1  # From our test results
    
    print(f"Entry Time: {entry_time}")
    print(f"Entry Price: {entry_price}")
    
    # Get trade data from entry time onwards
    if entry_time not in call_prices_df.index:
        print("❌ Entry time not found in data")
        return
    
    entry_bar_index = call_prices_df.index.get_loc(entry_time)
    trade_data = call_prices_df.iloc[entry_bar_index:].reset_index()
    
    print(f"Trade data length: {len(trade_data)} bars")
    
    # Show first few bars to understand price movement
    print("\nFirst 10 bars of trade data:")
    for i in range(min(10, len(trade_data))):
        bar = trade_data.iloc[i]
        print(f"  {bar['datetime']}: O={bar['open']:.2f}, H={bar['high']:.2f}, L={bar['low']:.2f}, C={bar['close']:.2f}, ATR={bar.get('ATR_5', 0):.2f}")
    
    # Load trade configuration
    trade_config = load_trade_config()
    hybrid_config = trade_config.get('HYBRID_PREMIUM', {})
    
    print(f"\nTrade Configuration:")
    print(f"  Strategy: {trade_config.get('STRATEGY_TYPE', 'Unknown')}")
    print(f"  Premium Tiers: {hybrid_config.get('PREMIUM_TIERS', {})}")
    
    # Execute the trade with detailed logging
    print(f"\n=== Executing Trade ===")
    result = execute_hybrid_premium_trade(
        trade_data, 
        entry_price, 
        hybrid_config, 
        entry_time, 
        'Call'
    )
    
    if result:
        print(f"\n=== Trade Result ===")
        for key, value in result.items():
            print(f"  {key}: {value}")
        
        # Analyze what went wrong
        exit_price = float(result['Exit Price'])
        exit_reason = result['Exit Reason']
        highest_high = float(result['Highest High'])
        
        print(f"\n=== Analysis ===")
        print(f"Entry: {entry_price:.2f}")
        print(f"Exit: {exit_price:.2f}")
        print(f"Highest High: {highest_high:.2f}")
        print(f"Max Potential Gain: {((highest_high - entry_price) / entry_price * 100):.2f}%")
        print(f"Exit Reason: {exit_reason}")
        
        if exit_reason == 'SL Hit' and exit_price == entry_price:
            print("❌ Trade exited at breakeven - likely moved SL to entry too early")
        elif exit_reason == 'Trailing SL':
            print("✅ Trade used trailing stop - but may have trailed too tightly")
        
        # Check if this should have been a big winner
        if highest_high > entry_price * 1.5:  # 50%+ move
            print("🚨 This should have been a big winner! Price moved significantly higher.")
            print("   Issue might be in breakeven logic or trailing stop calculation.")
    
    else:
        print("❌ Trade execution failed")

def analyze_expected_vs_actual():
    """
    Compare expected vs actual results for the 13:20 trade
    """
    print(f"\n=== Expected vs Actual Comparison ===")
    
    # Expected from tiered_simulated_trades.csv
    expected = {
        'Entry Time': '2025-07-03 13:20:00',
        'Entry Price': 101.1,  # Assuming same entry price
        'Exit Price': 198.0,   # Calculated from +95.85% gain
        'P/L %': 95.85,
        'Exit Reason': 'Trailing SL'
    }
    
    print("Expected:")
    for key, value in expected.items():
        print(f"  {key}: {value}")
    
    print("\nThis suggests the trade should have:")
    print("  1. Captured a big upward move (nearly doubled)")
    print("  2. Used trailing stop to exit")
    print("  3. NOT exited at breakeven")

if __name__ == "__main__":
    debug_13_20_call_trade()
    analyze_expected_vs_actual()
