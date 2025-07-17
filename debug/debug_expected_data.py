#!/usr/bin/env python3
"""
Debug script to understand what the expected 13:20 trade data should look like
"""

import pandas as pd
import os

def analyze_expected_trade():
    """
    Analyze the expected trade from tiered_simulated_trades.csv
    """
    print("=== Analyzing Expected Trade Data ===")
    
    # Load expected trades
    expected_df = pd.read_csv('./data/0307/trades_crp/tiered_simulated_trades.csv')
    
    # Find the 13:20 trade
    trade_13_20 = expected_df[expected_df['Entry Time'] == '2025-07-03 13:20:00']
    
    if len(trade_13_20) == 0:
        print("❌ 13:20 trade not found in expected data")
        return
    
    trade = trade_13_20.iloc[0]
    print("Expected 13:20 Trade:")
    for col in expected_df.columns:
        print(f"  {col}: {trade[col]}")
    
    # Calculate expected exit price from P/L
    entry_price = trade['Entry Price']
    pl_percent = trade['P/L %']
    expected_exit_price = entry_price * (1 + pl_percent / 100)
    
    print(f"\nCalculated Expected Exit Price: {expected_exit_price:.2f}")
    
    # Load call price data to see if this price level exists
    call_prices_df = pd.read_csv('./data/0307/call/call_out.csv')
    call_prices_df['datetime'] = pd.to_datetime(call_prices_df['datetime'])
    
    # Find the highest price after 13:20
    entry_time = pd.to_datetime('2025-07-03 13:20:00')
    after_entry = call_prices_df[call_prices_df['datetime'] >= entry_time]
    
    if len(after_entry) > 0:
        max_high = after_entry['high'].max()
        max_close = after_entry['close'].max()
        
        print(f"\nActual Price Data After Entry:")
        print(f"  Maximum High: {max_high:.2f}")
        print(f"  Maximum Close: {max_close:.2f}")
        print(f"  Expected Exit: {expected_exit_price:.2f}")
        
        if expected_exit_price > max_high:
            print("🚨 Expected exit price is HIGHER than maximum high in data!")
            print("   This suggests the expected data might be from a different source or calculation.")
        else:
            # Find when this price level was reached
            high_reached = after_entry[after_entry['high'] >= expected_exit_price]
            if len(high_reached) > 0:
                first_reach = high_reached.iloc[0]
                print(f"  Expected exit price first reached at: {first_reach['datetime']}")
                print(f"  Bar data: O={first_reach['open']:.2f}, H={first_reach['high']:.2f}, L={first_reach['low']:.2f}, C={first_reach['close']:.2f}")

def compare_all_expected_trades():
    """
    Compare all expected trades with available price data
    """
    print(f"\n=== Comparing All Expected Trades ===")
    
    expected_df = pd.read_csv('./data/0307/trades_crp/tiered_simulated_trades.csv')
    call_prices_df = pd.read_csv('./data/0307/call/call_out.csv')
    put_prices_df = pd.read_csv('./data/0307/put/put_out.csv')
    
    call_prices_df['datetime'] = pd.to_datetime(call_prices_df['datetime'])
    put_prices_df['datetime'] = pd.to_datetime(put_prices_df['datetime'])
    
    for _, trade in expected_df.iterrows():
        entry_time = pd.to_datetime(trade['Entry Time'])
        entry_price = trade['Entry Price']
        pl_percent = trade['P/L %']
        trade_type = trade['Trade Type']
        
        expected_exit_price = entry_price * (1 + pl_percent / 100)
        
        print(f"\n{trade_type} at {entry_time}:")
        print(f"  Entry: {entry_price:.2f}, Expected Exit: {expected_exit_price:.2f}, P/L: {pl_percent:.2f}%")
        
        # Choose the right price data
        if 'Call' in trade_type:
            price_data = call_prices_df
        else:
            price_data = put_prices_df
        
        # Check if expected exit price is reachable
        after_entry = price_data[price_data['datetime'] >= entry_time]
        if len(after_entry) > 0:
            max_high = after_entry['high'].max()
            min_low = after_entry['low'].min()
            
            if pl_percent > 0:  # Profit trade
                if expected_exit_price <= max_high:
                    print(f"  ✅ Expected exit price {expected_exit_price:.2f} is reachable (max high: {max_high:.2f})")
                else:
                    print(f"  ❌ Expected exit price {expected_exit_price:.2f} exceeds max high: {max_high:.2f}")
            else:  # Loss trade
                if expected_exit_price >= min_low:
                    print(f"  ✅ Expected exit price {expected_exit_price:.2f} is reachable (min low: {min_low:.2f})")
                else:
                    print(f"  ❌ Expected exit price {expected_exit_price:.2f} below min low: {min_low:.2f}")

if __name__ == "__main__":
    analyze_expected_trade()
    compare_all_expected_trades()
