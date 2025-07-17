# Test script to verify the trailing stop fix
import pandas as pd
import numpy as np
from option_tools.option_trade_executor import execute_hybrid_premium_trade

def create_test_trade_data():
    """Create test data that simulates the problematic trade"""
    
    # Create timestamps from 13:20 to 13:35 (15 minutes)
    timestamps = pd.date_range('2025-07-03 13:20:00', '2025-07-03 13:35:00', freq='1min')
    
    # Simulate the price movement from the actual trade
    # Entry: 101.1, High: 112.5, Exit: 96.72
    prices = [
        101.1,  # Entry bar (open)
        105.0,  # Start moving up
        108.0,  # Continue up
        110.0,  # Getting close to high
        112.5,  # Highest high
        111.0,  # Start retracing
        109.0,  # Continue down
        106.0,  # More down
        103.0,  # Getting close to exit
        100.0,  # Below entry
        98.0,   # Continue down
        96.5,   # Near exit level
        95.0,   # Below exit
        94.0,   # Further down
        93.0,   # End
        92.0    # End
    ]
    
    # Create OHLC data
    data = []
    for i, (ts, price) in enumerate(zip(timestamps, prices)):
        if i == 0:
            # Entry bar
            high = price + 0.5
            low = price - 0.5
            open_price = price
            close = price + 0.2
        else:
            # Simulate realistic OHLC
            prev_close = data[i-1]['close']
            open_price = prev_close
            
            if price > prev_close:  # Upward movement
                high = price
                low = min(prev_close, price - 1.0)
                close = price - 0.2
            else:  # Downward movement
                high = max(prev_close, price + 1.0)
                low = price
                close = price + 0.2
        
        # Add ATR column (simulate ATR of around 2.0)
        atr_5 = 2.0 + (i * 0.1)  # Gradually increasing ATR
        
        data.append({
            'datetime': ts,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'ATR_5': atr_5
        })
    
    df = pd.DataFrame(data)
    df.set_index('datetime', inplace=True)
    return df

def test_hybrid_premium_fix():
    """Test the hybrid premium trailing stop fix"""
    
    print("=== TESTING HYBRID PREMIUM TRAILING STOP FIX ===")
    
    # Create test data
    trade_data = create_test_trade_data()
    print(f"Created test data with {len(trade_data)} bars")
    print(f"Price range: {trade_data['low'].min():.2f} to {trade_data['high'].max():.2f}")
    
    # Test configuration (matching the actual config)
    hybrid_config = {
        'STOP_LOSS_PERCENT': 6.0,
        'TRAILING_START_PERCENT': 5.0,
        'ATR_PERIOD': 5,
        'ATR_MULTIPLIER': 2.2,
        'TRAILING_METHOD': 'HYBRID',
        'HYBRID_LOGIC': 'MIN',
        'PREMIUM_TIERS': {
            'HIGH_PREMIUM': {
                'threshold': 250,
                'profit_80_plus': 0.08, 'profit_50_plus': 0.10, 'profit_40_plus': 0.12,
                'profit_30_plus': 0.14, 'profit_20_plus': 0.16, 'profit_default': 0.04,
                'atr_80_plus': 4.0, 'atr_50_plus': 3.5, 'atr_40_plus': 3.0,
                'atr_30_plus': 2.5, 'atr_20_plus': 2.2, 'atr_default': 2.0
            },
            'MEDIUM_PREMIUM': {
                'threshold': 150,
                'profit_80_plus': 0.10, 'profit_50_plus': 0.12, 'profit_40_plus': 0.14,
                'profit_30_plus': 0.16, 'profit_20_plus': 0.18, 'profit_default': 0.08,
                'atr_80_plus': 4.5, 'atr_50_plus': 4.0, 'atr_40_plus': 3.5,
                'atr_30_plus': 3.0, 'atr_20_plus': 2.5, 'atr_default': 2.2
            },
            'LOW_PREMIUM': {
                'threshold': 0,
                'profit_80_plus': 0.15, 'profit_50_plus': 0.15, 'profit_40_plus': 0.16,
                'profit_30_plus': 0.15, 'profit_20_plus': 0.18, 'profit_default': 0.11,
                'atr_80_plus': 5.0, 'atr_50_plus': 4.5, 'atr_40_plus': 4.0,
                'atr_30_plus': 3.5, 'atr_20_plus': 3.0, 'atr_default': 2.5
            }
        }
    }
    
    # Execute the trade
    entry_price = 101.1
    entry_time = trade_data.index[0]
    
    print(f"\nExecuting trade with entry price: {entry_price}")
    
    result = execute_hybrid_premium_trade(
        trade_data, 
        entry_price, 
        hybrid_config, 
        entry_time, 
        'Call'
    )
    
    if result:
        print("\n=== TRADE RESULT ===")
        for key, value in result.items():
            print(f"{key}: {value}")
        
        # Analyze the result
        exit_price = float(result['Exit Price'])
        initial_sl = float(result['Initial SL'])
        final_sl = float(result['Final SL'])
        highest_high = float(result['Highest High'])
        
        print(f"\n=== ANALYSIS ===")
        print(f"Initial SL: {initial_sl:.2f}")
        print(f"Final SL: {final_sl:.2f}")
        print(f"Exit Price: {exit_price:.2f}")
        print(f"Highest High: {highest_high:.2f}")
        
        # Check if the trailing stop worked correctly
        expected_trail = entry_price * 0.11  # 11% trail for LOW_PREMIUM
        expected_stop = highest_high - expected_trail
        expected_final = max(expected_stop, initial_sl)
        
        print(f"\nExpected trail amount: {expected_trail:.2f}")
        print(f"Expected stop from high: {expected_stop:.2f}")
        print(f"Expected final stop: {expected_final:.2f}")
        
        if abs(final_sl - expected_final) < 0.5:
            print("✅ Trailing stop calculation appears correct")
        else:
            print("❌ Trailing stop calculation may have issues")
            print(f"Difference: {abs(final_sl - expected_final):.2f}")
    
    else:
        print("❌ Trade execution failed")

if __name__ == "__main__":
    test_hybrid_premium_fix()
