# option_tools/index_trade_executor.py
# Strategy-aware index trade executor that respects config.yaml TRADE_STRATEGY setting

import pandas as pd
import numpy as np
import os
from datetime import time
try:
    import pandas_ta as ta
except ImportError:
    import sys
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas_ta"])
    import pandas_ta as ta

from .simple_trade_config import load_simple_trade_config

def execute_index_trades_simple(signals_df, prices_df, signal_col, trade_type, config, output_dir, output_filename):
    """
    Execute index trades using SIMPLE strategy (two-phase stop-loss system).
    """
    simple_trade_config = load_simple_trade_config()
    
    last_entry_hour, last_entry_minute = map(int, config['LAST_ENTRY_TIME'].split(':'))
    last_entry_time = time(last_entry_hour, last_entry_minute)

    signals_df['datetime'] = pd.to_datetime(signals_df['datetime'])
    prices_df['datetime'] = pd.to_datetime(prices_df['datetime'])
    prices_df.set_index('datetime', inplace=True)

    # Calculate indicators needed for simple strategy
    atr_period = simple_trade_config['INDICATORS']['ATR_PERIOD']
    swing_low_period = simple_trade_config['INDICATORS']['SWING_LOW_PERIOD']
    
    prices_df[f'ATR_{atr_period}'] = ta.atr(prices_df['high'], prices_df['low'], prices_df['close'], length=atr_period)
    prices_df['low_swing'] = prices_df['low'].rolling(window=swing_low_period).min().shift(1)

    valid_signals = signals_df[signals_df[signal_col] == 1].copy()
    
    trade_results = []
    current_trade_exit_time = None

    print(f"   Processing {len(valid_signals)} index signals for {trade_type} using SIMPLE strategy (Two-Phase SL)")

    for index, signal in valid_signals.iterrows():
        if signal['datetime'].time() > last_entry_time:
            continue

        if current_trade_exit_time is not None and signal['datetime'] <= current_trade_exit_time:
            continue

        entry_time = signal['datetime'] + pd.Timedelta(minutes=1)
        if entry_time not in prices_df.index:
            continue

        entry_bar_index = prices_df.index.get_loc(entry_time)
        trade_data = prices_df.iloc[entry_bar_index:].reset_index()

        if trade_data.empty or pd.isna(trade_data.iloc[0]['low_swing']):
            continue

        entry_price = trade_data.iloc[0]['open']
        if not isinstance(entry_price, (int, float)) or entry_price <= 0:
            continue

        print(f"   Executing index trade: Entry at {entry_time}, Price: {entry_price}")

        result = execute_simple_index_trade(trade_data, entry_price, simple_trade_config)
        
        final_result = {
            'Entry Time': entry_time,
            'Entry Price': f"{entry_price:.2f}",
            **result,
            'Trade Type': f"{trade_type} Index (Simple Strategy)",
        }
        
        trade_results.append(final_result)
        current_trade_exit_time = pd.to_datetime(final_result['Exit Time'])
        print(f"   Index trade completed: Exit at {current_trade_exit_time}, P/L: {final_result['P/L']}")

    df_results = pd.DataFrame(trade_results)
    
    if not df_results.empty:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_filename)
        
        if os.path.exists(output_path):
            existing_df = pd.read_csv(output_path)
            combined_df = pd.concat([existing_df, df_results], ignore_index=True)
            combined_df.to_csv(output_path, index=False)
            print(f"  ✓ Appended {len(df_results)} index trades to {output_path}")
        else:
            df_results.to_csv(output_path, index=False)
            print(f"  ✓ Saved {len(df_results)} index trades to {output_path}")
    else:
        print(f"  ℹ️ No valid index trades found for {trade_type}")
    
    return df_results

def execute_index_trades_complex(signals_df, prices_df, signal_col, trade_type, config, output_dir, output_filename):
    """
    Execute index trades using COMPLEX strategy (original slabbed ATR trailing stop loss).
    This maintains the original logic from tools/trade_executor.py
    """
    # --- Strategy Parameters (from original trade_executor.py) ---
    FIXED_STOP_LOSS_PERCENT = 8.0  # Increased from 6% to 8%
    STALL_BAR_COUNT = 20  # Increased from 14 to 20 bars
    SLAB_THRESHOLDS = [15.0, 30.0, 45.0, 70.0]  # More granular profit bands
    SLAB_MULTIPLIERS = [3.0, 2.5, 2.0, 3.5]  # Much tighter for explosive moves

    last_entry_hour, last_entry_minute = map(int, config['LAST_ENTRY_TIME'].split(':'))
    last_entry_time = time(last_entry_hour, last_entry_minute)

    signals_df['datetime'] = pd.to_datetime(signals_df['datetime'])
    prices_df['datetime'] = pd.to_datetime(prices_df['datetime'])
    prices_df.set_index('datetime', inplace=True)

    prices_df.ta.atr(length=5, append=True, col_names=('ATR_5',))

    valid_signals = signals_df[signals_df[signal_col] == 1].copy()
    
    trade_results = []

    print(f"   Processing {len(valid_signals)} index signals for {trade_type} using COMPLEX strategy (Slabbed ATR)")

    for index, signal in valid_signals.iterrows():
        if signal['datetime'].time() > last_entry_time:
            continue

        entry_time = signal['datetime'] + pd.Timedelta(minutes=1)
        if entry_time not in prices_df.index:
            continue

        entry_bar_index = prices_df.index.get_loc(entry_time)
        trade_data = prices_df.iloc[entry_bar_index:]

        if trade_data.empty:
            continue

        entry_price = trade_data.iloc[0]['open']
        entry_atr = trade_data.iloc[0]['ATR_5']

        if pd.isna(entry_atr):
            continue

        initial_stop_loss = entry_price * (1 - (FIXED_STOP_LOSS_PERCENT / 100.0))
        breakeven_target = entry_price + (2.5 * entry_atr)  # Increased from 1.5x to 2.5x ATR

        current_stop_loss = initial_stop_loss
        highest_high_since_entry = entry_price
        bar_of_highest_high = 0
        is_breakeven_achieved = False
        exit_reason = "In Progress"
        exit_price = 0.0
        exit_time = None

        for i in range(1, len(trade_data)):
            current_bar = trade_data.iloc[i]
            bars_since_entry = i

            if current_bar['low'] <= current_stop_loss:
                exit_price = current_stop_loss
                exit_time = current_bar.name
                exit_reason = "Trailing SL" if is_breakeven_achieved else "Initial SL"
                break

            if not is_breakeven_achieved and current_bar['high'] >= breakeven_target:
                is_breakeven_achieved = True
                current_stop_loss = entry_price

            if current_bar['high'] > highest_high_since_entry:
                highest_high_since_entry = current_bar['high']
                bar_of_highest_high = i

            if is_breakeven_achieved:
                current_profit_percent = ((highest_high_since_entry - entry_price) / entry_price) * 100
                
                if current_profit_percent >= SLAB_THRESHOLDS[3]:  # >= 70%
                    atr_multiplier = SLAB_MULTIPLIERS[3]  # 3.5x ATR (mega moves)
                elif current_profit_percent >= SLAB_THRESHOLDS[2]:  # >= 45%
                    atr_multiplier = SLAB_MULTIPLIERS[2]  # 2.0x ATR (VERY TIGHT!)
                elif current_profit_percent >= SLAB_THRESHOLDS[1]:  # >= 30%
                    atr_multiplier = SLAB_MULTIPLIERS[1]  # 2.5x ATR (tight)
                elif current_profit_percent >= SLAB_THRESHOLDS[0]:  # >= 15%
                    atr_multiplier = SLAB_MULTIPLIERS[0]  # 3.0x ATR (normal)
                else:  # < 15%
                    atr_multiplier = SLAB_MULTIPLIERS[0]  # 3.0x ATR (normal)

                current_atr = current_bar['ATR_5']
                if not pd.isna(current_atr):
                    trailing_stop_target = highest_high_since_entry - (atr_multiplier * current_atr)
                    current_stop_loss = max(trailing_stop_target, current_stop_loss)

            if (bars_since_entry - bar_of_highest_high) > STALL_BAR_COUNT:
                exit_price = current_bar['close']
                exit_time = current_bar.name
                exit_reason = "Stall Exit"
                break
        
        if exit_reason == "In Progress":
            exit_price = trade_data.iloc[-1]['close']
            exit_time = trade_data.iloc[-1].name
            exit_reason = "End of Data"

        profit_loss = exit_price - entry_price
        trade_results.append({
            "Entry Time": entry_time,
            "Entry Price": f"{entry_price:.2f}",
            "Exit Time": exit_time,
            "Exit Price": f"{exit_price:.2f}",
            "P/L": f"{profit_loss:.2f}",
            "Exit Reason": exit_reason,
            "Trade Type": f"{trade_type} Index (Complex Strategy)"
        })

    df_results = pd.DataFrame(trade_results)
    
    # --- Save results to file ---
    if not df_results.empty:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_filename)
        df_results.to_csv(output_path, index=False)
        print(f"  ✓ Saved {len(df_results)} index trades to {output_path}")
    
    return df_results

def execute_simple_index_trade(trade_data, entry_price, config):
    """
    Execute a single index trade using the simple two-phase stop-loss system.
    Adapted from option_tools/simple_trade_executor.py for index trades.
    """
    # State variables for the trade
    highest_price = entry_price
    is_trailing_active = False
    
    # Phase 1: Initial Fixed Stop-Loss
    fixed_sl_percent = config['STOP_LOSS']['INITIAL_FIXED_SL_PERCENT']
    swing_low_period = config['INDICATORS']['SWING_LOW_PERIOD']
    
    # Calculate initial stop loss
    fixed_stop_from_percent = entry_price * (1 - fixed_sl_percent / 100)
    swing_low = trade_data.iloc[0]['low_swing']
    fixed_stop_loss = min(fixed_stop_from_percent, swing_low)
    
    stop_level = fixed_stop_loss
    trailing_stop = 0  # Not used until trailing is active

    exit_time = None
    exit_price = None
    exit_reason = 'In Progress'

    atr_col = f"ATR_{config['INDICATORS']['ATR_PERIOD']}"

    for idx, bar in trade_data.iloc[1:].iterrows():
        current_price = bar['close']
        current_profit_pct = ((current_price - entry_price) / entry_price) * 100

        # Phase 2 Activation Check
        if not is_trailing_active and current_profit_pct >= config['STOP_LOSS']['TRAILING_ACTIVATION_PROFIT_PERCENT']:
            is_trailing_active = True
            highest_price = bar['high']
            trailing_stop = stop_level  # Initialize trailing stop
            exit_reason = 'Trailing Activated' # Mark this change in status

        # Update stop_level based on the active phase
        if is_trailing_active:
            highest_price = max(highest_price, bar['high'])
            atr_val = bar[atr_col]
            profit_for_multiplier = ((highest_price - entry_price) / entry_price) * 100
            atr_multiplier = get_atr_multiplier_simple(profit_for_multiplier, config['STOP_LOSS']['ATR_MULTIPLIERS'])
            
            new_trailing_stop = highest_price - (atr_val * atr_multiplier)
            
            # Ratchet Rule: Only move stop up
            if new_trailing_stop > trailing_stop:
                trailing_stop = new_trailing_stop
            
            stop_level = trailing_stop

        # Final Exit Condition Check
        if bar['low'] <= stop_level:
            exit_price = stop_level
            exit_time = bar['datetime']
            exit_reason = 'Trailing SL Hit' if is_trailing_active else 'Fixed SL Hit'
            break

    # If trade is still open at the end of data, exit at the last close
    if exit_reason == 'In Progress' or exit_reason == 'Trailing Activated':
        exit_price = trade_data.iloc[-1]['close']
        exit_time = trade_data.iloc[-1]['datetime']
        exit_reason = 'End of Data'

    pl = exit_price - entry_price
    pl_pct = (pl / entry_price) * 100 if entry_price > 0 else 0

    return {
        'Exit Time': exit_time,
        'Exit Price': f"{exit_price:.2f}",
        'P/L': f"{pl:.2f}",
        'P/L %': f"{pl_pct:.2f}%",
        'Exit Reason': exit_reason,
    }

def get_atr_multiplier_simple(profit_pct, multipliers_config):
    """Get the correct ATR multiplier based on the current profit for simple strategy."""
    for tier in multipliers_config:
        if profit_pct < tier['profit_threshold']:
            return tier['multiplier']
    return multipliers_config[-1]['multiplier']
