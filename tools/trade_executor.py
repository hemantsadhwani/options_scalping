import pandas as pd
try:
    import pandas_ta as ta
except ImportError:
    import sys
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas_ta"])
    import pandas_ta as ta

from datetime import time

import os

def execute_trades(signals_df, prices_df, signal_col, trade_type, config, output_dir, output_filename):
    """
    Executes trades based on signals and a slabbed ATR trailing stop loss strategy.
    """
    # --- Strategy Parameters ---
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
            "Trade Type": trade_type
        })

    df_results = pd.DataFrame(trade_results)
    
    # --- Save results to file ---
    if not df_results.empty:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_filename)
        df_results.to_csv(output_path, index=False)
        print(f"  ✓ Saved {len(df_results)} executed trades to {output_path}")
    
    return df_results
