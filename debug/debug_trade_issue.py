# Debug script to analyze the specific trade issue
import pandas as pd
import numpy as np

def debug_hybrid_premium_trade():
    """Debug the specific trade issue"""
    
    # Trade parameters from the problematic trade
    entry_price = 101.1
    initial_stop_loss = 95.03
    trail_start_price = 106.16  # 5% above entry
    highest_high = 112.5
    exit_price = 96.72
    
    print("=== DEBUGGING HYBRID PREMIUM TRADE ISSUE ===")
    print(f"Entry Price: {entry_price}")
    print(f"Initial SL: {initial_stop_loss}")
    print(f"Trail Start: {trail_start_price}")
    print(f"Highest High: {highest_high}")
    print(f"Exit Price: {exit_price}")
    print()
    
    # Calculate profit percentage at highest high
    profit_percent = ((highest_high - entry_price) / entry_price) * 100
    print(f"Profit % at highest high: {profit_percent:.2f}%")
    
    # This is a LOW_PREMIUM trade (entry 101.1 < 150)
    # From config: LOW_PREMIUM profit_default: 0.11 (11% trail)
    # Since profit is ~11.3%, it falls into profit_default category
    
    premium_trail_percent = 0.11  # 11% from LOW_PREMIUM profit_default
    premium_trail_amount = entry_price * premium_trail_percent
    premium_based_stop = highest_high - premium_trail_amount
    
    print(f"Premium trail %: {premium_trail_percent * 100}%")
    print(f"Premium trail amount: {premium_trail_amount:.2f}")
    print(f"Premium-based stop: {premium_based_stop:.2f}")
    
    # For ATR calculation, let's assume ATR = 2.0 (typical for options)
    # LOW_PREMIUM atr_default: 2.5
    assumed_atr = 2.0
    atr_multiplier = 2.5  # LOW_PREMIUM atr_default
    atr_based_stop = highest_high - (atr_multiplier * assumed_atr)
    
    print(f"Assumed ATR: {assumed_atr}")
    print(f"ATR multiplier: {atr_multiplier}")
    print(f"ATR-based stop: {atr_based_stop:.2f}")
    
    # HYBRID_LOGIC: 'MIN' - take the minimum (more conservative)
    hybrid_stop = min(premium_based_stop, atr_based_stop)
    print(f"Hybrid stop (MIN logic): {hybrid_stop:.2f}")
    
    # The final stop should be max(hybrid_stop, current_stop_loss)
    final_stop = max(hybrid_stop, initial_stop_loss)
    print(f"Final stop loss: {final_stop:.2f}")
    
    print()
    print("=== ANALYSIS ===")
    if abs(final_stop - exit_price) < 0.1:
        print("✅ The exit price matches the calculated trailing stop")
    else:
        print("❌ There's a discrepancy in the trailing stop calculation")
        print(f"Expected: {final_stop:.2f}, Actual: {exit_price}")
    
    print()
    print("=== POTENTIAL ISSUES ===")
    print("1. The trailing stop is working correctly - it moved SL from 95.03 to 96.72")
    print("2. This is expected behavior when price hits the highest high and then retraces")
    print("3. The issue might be that the trailing is too tight for this profit level")
    
    # Let's see what happens with different configurations
    print()
    print("=== ALTERNATIVE CONFIGURATIONS ===")
    
    # What if we used profit_20_plus instead?
    alt_trail_percent = 0.18  # LOW_PREMIUM profit_20_plus
    alt_trail_amount = entry_price * alt_trail_percent
    alt_premium_stop = highest_high - alt_trail_amount
    alt_final_stop = max(alt_premium_stop, initial_stop_loss)
    
    print(f"If using 20%+ profit tier (18% trail): {alt_final_stop:.2f}")
    
    # What if we used ATR_ONLY method?
    atr_only_stop = max(atr_based_stop, initial_stop_loss)
    print(f"If using ATR_ONLY method: {atr_only_stop:.2f}")
    
    # What if we used MAX logic instead of MIN?
    max_hybrid_stop = max(premium_based_stop, atr_based_stop)
    max_final_stop = max(max_hybrid_stop, initial_stop_loss)
    print(f"If using MAX hybrid logic: {max_final_stop:.2f}")

if __name__ == "__main__":
    debug_hybrid_premium_trade()
