#!/usr/bin/env python3
"""
Test script for the new hybrid premium-based trailing stop strategy
Focus on the 73.4 → 146.75 scenario from data/1107/put
"""

import pandas as pd
import sys
import os

# Add the current directory to Python path
sys.path.append('.')

from option_tools.option_trade_executor import execute_hybrid_premium_trade, load_trade_config

def test_73_4_to_146_75_scenario():
    """Test the specific scenario: Entry 73.4, High 146.75 at 11:09"""
    
    print("=" * 60)
    print("TESTING HYBRID PREMIUM STRATEGY")
    print("Scenario: 73.4 entry → 146.75 high (99.7% potential profit)")
    print("=" * 60)
    
    # Load the actual put data
    try:
        put_data = pd.read_csv('data/1107/put/put_out.csv')
        put_data['datetime'] = pd.to_datetime(put_data['datetime'])
        put_data.set_index('datetime', inplace=True)
        
        # Add ATR calculation
        put_data.ta.atr(length=5, append=True, col_names=('ATR_5',))
        
        print(f"✓ Loaded put data: {len(put_data)} bars")
        
        # Find the entry time (9:46) and get trade data from that point
        entry_time = pd.Timestamp('2025-07-11 09:46:00')
        if entry_time not in put_data.index:
            print(f"❌ Entry time {entry_time} not found in data")
            return
            
        trade_data = put_data.loc[entry_time:]
        entry_price = 73.4  # From the data
        
        print(f"✓ Entry time: {entry_time}")
        print(f"✓ Entry price: {entry_price}")
        print(f"✓ Trade data length: {len(trade_data)} bars")
        
        # Load trade configuration
        trade_config = load_trade_config()
        hybrid_config = trade_config['HYBRID_PREMIUM']
        
        print(f"✓ Loaded config - Strategy: {trade_config['STRATEGY_TYPE']}")
        print(f"✓ Trailing method: {hybrid_config['TRAILING_METHOD']}")
        print(f"✓ Hybrid logic: {hybrid_config['HYBRID_LOGIC']}")
        
        # Test the hybrid premium trade execution
        print("\n" + "-" * 40)
        print("EXECUTING HYBRID PREMIUM TRADE")
        print("-" * 40)
        
        result = execute_hybrid_premium_trade(
            trade_data=trade_data,
            entry_price=entry_price,
            hybrid_config=hybrid_config,
            entry_time=entry_time,
            trade_type="Put"
        )
        
        if result:
            print("\n" + "=" * 40)
            print("TRADE RESULT")
            print("=" * 40)
            for key, value in result.items():
                print(f"{key:15}: {value}")
            
            # Calculate what we captured vs potential
            entry_price_num = float(result['Entry Price'])
            exit_price_num = float(result['Exit Price'])
            highest_high_num = float(result['Highest High'])
            
            actual_profit = ((exit_price_num - entry_price_num) / entry_price_num) * 100
            potential_profit = ((highest_high_num - entry_price_num) / entry_price_num) * 100
            capture_ratio = (actual_profit / potential_profit) * 100 if potential_profit > 0 else 0
            
            print("\n" + "=" * 40)
            print("PERFORMANCE ANALYSIS")
            print("=" * 40)
            print(f"Entry Price:      {entry_price_num:.2f}")
            print(f"Highest High:     {highest_high_num:.2f}")
            print(f"Exit Price:       {exit_price_num:.2f}")
            print(f"Potential Profit: {potential_profit:.1f}%")
            print(f"Actual Profit:    {actual_profit:.1f}%")
            print(f"Capture Ratio:    {capture_ratio:.1f}%")
            
            # Compare with old result (13.81%)
            old_profit = 13.81
            improvement = actual_profit - old_profit
            print(f"\nOld Strategy:     {old_profit:.1f}%")
            print(f"New Strategy:     {actual_profit:.1f}%")
            print(f"Improvement:      +{improvement:.1f}%")
            
            if actual_profit > 30:
                print("🎉 SUCCESS: Captured >30% profit!")
            elif actual_profit > old_profit:
                print("✅ IMPROVEMENT: Better than old strategy")
            else:
                print("⚠️  NEEDS TUNING: Similar to old strategy")
                
        else:
            print("❌ Trade execution failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_different_trailing_methods():
    """Test different trailing methods on the same scenario"""
    
    print("\n" + "=" * 60)
    print("TESTING DIFFERENT TRAILING METHODS")
    print("=" * 60)
    
    methods = ['PERCENTAGE_ONLY', 'ATR_ONLY', 'HYBRID']
    
    for method in methods:
        print(f"\n--- Testing {method} ---")
        
        # Modify config for this test
        trade_config = load_trade_config()
        trade_config['HYBRID_PREMIUM']['TRAILING_METHOD'] = method
        
        # Run the same scenario
        try:
            put_data = pd.read_csv('data/1107/put/put_out.csv')
            put_data['datetime'] = pd.to_datetime(put_data['datetime'])
            put_data.set_index('datetime', inplace=True)
            put_data.ta.atr(length=5, append=True, col_names=('ATR_5',))
            
            entry_time = pd.Timestamp('2025-07-11 09:46:00')
            trade_data = put_data.loc[entry_time:]
            entry_price = 73.4
            
            result = execute_hybrid_premium_trade(
                trade_data=trade_data,
                entry_price=entry_price,
                hybrid_config=trade_config['HYBRID_PREMIUM'],
                entry_time=entry_time,
                trade_type="Put"
            )
            
            if result:
                actual_profit = ((float(result['Exit Price']) - entry_price) / entry_price) * 100
                print(f"{method:15}: {actual_profit:.1f}% profit, Exit: {result['Exit Reason']}")
            else:
                print(f"{method:15}: Failed")
                
        except Exception as e:
            print(f"{method:15}: Error - {e}")

if __name__ == "__main__":
    # Test the main scenario
    test_73_4_to_146_75_scenario()
    
    # Test different methods
    test_different_trailing_methods()
    
    print("\n" + "=" * 60)
    print("TESTING COMPLETE")
    print("=" * 60)
