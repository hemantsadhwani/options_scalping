# option_tools/simple_trade_executor.py

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

def get_atr_multiplier(profit_pct, multipliers_config):
    """Get the correct ATR multiplier based on the current profit."""
    for tier in multipliers_config:
        if profit_pct < tier['profit_threshold']:
            return tier['multiplier']
    return multipliers_config[-1]['multiplier']

def execute_trade(trade_data, entry_price, config):
    """
    Executes a single trade based on the two-phase stop-loss system.
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
            atr_val = bar['atr']
            profit_for_multiplier = ((highest_price - entry_price) / entry_price) * 100
            atr_multiplier = get_atr_multiplier(profit_for_multiplier, config['STOP_LOSS']['ATR_MULTIPLIERS'])
            
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

def execute_option_trades(signals_df, prices_df, signal_col, trade_type, config, output_dir, output_filename):
    """
    Executes option trades based on signals using the two-phase stop-loss strategy.
    """
    simple_trade_config = load_simple_trade_config()
    atr_period = simple_trade_config['INDICATORS']['ATR_PERIOD']
    swing_low_period = simple_trade_config['INDICATORS']['SWING_LOW_PERIOD']

    last_entry_hour, last_entry_minute = map(int, config['LAST_ENTRY_TIME'].split(':'))
    last_entry_time = time(last_entry_hour, last_entry_minute)

    signals_df['datetime'] = pd.to_datetime(signals_df['datetime'])
    prices_df['datetime'] = pd.to_datetime(prices_df['datetime'])
    
    # Pre-calculate indicators
    prices_df['atr'] = ta.atr(prices_df['high'], prices_df['low'], prices_df['close'], length=atr_period)
    prices_df['low_swing'] = prices_df['low'].rolling(window=swing_low_period).min().shift(1) # Shift to get prior swing low
    prices_df.set_index('datetime', inplace=True)

    valid_signals = signals_df[signals_df[signal_col] == 1].copy()
    
    trade_results = []
    current_trade_exit_time = None

    print(f"   Processing {len(valid_signals)} option signals for {trade_type} using Two-Phase SL strategy")

    for index, signal in valid_signals.iterrows():
        if signal['datetime'].time() > last_entry_time:
            continue

        if current_trade_exit_time is not None and signal['datetime'] <= current_trade_exit_time:
            continue

        signal_time = signal['datetime']
        
        try:
            signal_bar_index = prices_df.index.get_loc(signal_time)
        except KeyError:
            continue
        
        next_bar_index = signal_bar_index + 1
        if next_bar_index >= len(prices_df):
            continue
        
        entry_time = prices_df.index[next_bar_index]
        trade_data = prices_df.iloc[next_bar_index:].reset_index()

        if trade_data.empty or pd.isna(trade_data.iloc[0]['low_swing']):
            continue # Skip if no swing low data is available

        entry_price = trade_data.iloc[0]['open']
        if not isinstance(entry_price, (int, float)) or entry_price <= 0:
            continue

        print(f"   Executing trade: Entry at {entry_time}, Price: {entry_price}")

        result = execute_trade(trade_data, entry_price, simple_trade_config)
        
        final_result = {
            'Entry Time': entry_time,
            'Entry Price': f"{entry_price:.2f}",
            **result,
            'Trade Type': f"{trade_type} Option (Two-Phase SL)",
        }
        
        trade_results.append(final_result)
        current_trade_exit_time = pd.to_datetime(final_result['Exit Time'])
        print(f"   Trade completed: Exit at {current_trade_exit_time}, P/L: {final_result['P/L %']}")

    df_results = pd.DataFrame(trade_results)
    
    if not df_results.empty:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_filename)
        
        if os.path.exists(output_path):
            existing_df = pd.read_csv(output_path)
            combined_df = pd.concat([existing_df, df_results], ignore_index=True)
            combined_df.to_csv(output_path, index=False)
            print(f"  ✓ Appended {len(df_results)} option trades to {output_path}")
        else:
            df_results.to_csv(output_path, index=False)
            print(f"  ✓ Saved {len(df_results)} option trades to {output_path}")
    else:
        print(f"  ℹ️ No valid option trades found for {trade_type}")
    
    return df_results
