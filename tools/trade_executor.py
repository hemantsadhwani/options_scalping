import pandas as pd
try:
    import pandas_ta as ta
except ImportError:
    import sys
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas_ta"])
    import pandas_ta as ta

def execute_trades(signals_df, prices_df, signal_col, trade_type):
    """
    Executes trades based on signals and a slabbed ATR trailing stop loss strategy.
    """
    # --- Strategy Parameters ---
    FIXED_STOP_LOSS_PERCENT = 6.0
    STALL_BAR_COUNT = 14
    SLAB_THRESHOLDS = [10.0, 20.0, 50.0] 
    SLAB_MULTIPLIERS = [1.8, 2.2, 2.5] 

    signals_df['datetime'] = pd.to_datetime(signals_df['datetime'])
    prices_df['datetime'] = pd.to_datetime(prices_df['datetime'])
    prices_df.set_index('datetime', inplace=True)

    prices_df.ta.atr(length=5, append=True, col_names=('ATR_5',))

    valid_signals = signals_df[signals_df[signal_col] == 1].copy()
    
    trade_results = []

    for index, signal in valid_signals.iterrows():
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
        breakeven_target = entry_price + (1.5 * entry_atr)

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
                
                if current_profit_percent >= SLAB_THRESHOLDS[2]:
                    atr_multiplier = SLAB_MULTIPLIERS[2]
                elif current_profit_percent >= SLAB_THRESHOLDS[1]:
                    atr_multiplier = SLAB_MULTIPLIERS[2]
                elif current_profit_percent >= SLAB_THRESHOLDS[0]:
                    atr_multiplier = SLAB_MULTIPLIERS[1]
                else:
                    atr_multiplier = SLAB_MULTIPLIERS[0]

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

    return pd.DataFrame(trade_results)
