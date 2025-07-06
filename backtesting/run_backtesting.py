# backtesting/run_backtesting.py (Debug Version)

import pandas as pd
from datetime import time

def run_backtest(signals_df, calls_df, puts_df, date_str, config):
    """
    Runs a backtest for a single day's data, with extensive debugging output.
    """
    strategy_type = config['STRATEGY_TYPE']
    print(f"  Running backtest for {date_str} (Strategy: {strategy_type})")
    
    eod_hour, eod_minute = map(int, config['EOD_EXIT_TIME'].split(':'))
    eod_exit_time = time(eod_hour, eod_minute)

    signals_df.set_index('datetime', inplace=True)
    calls_df.set_index('datetime', inplace=True)
    puts_df.set_index('datetime', inplace=True)

    daily_trades = []
    trade_attempted = False # Debug flag

    for timestamp, signal_row in signals_df.iterrows():
        for trade_type in ['Call', 'Put']:
            if signal_row.get(trade_type, 0) == 1:
                
                # --- Start Debug Block ---
                if not trade_attempted:
                    print("\n  [DEBUG] ---> Found first signal to process!")
                    print(f"  [DEBUG] Signal Time: {timestamp}, Type: {trade_type}")
                # --- End Debug Block ---

                option_df = calls_df if trade_type == 'Call' else puts_df
                entry_row_series = option_df[option_df.index >= timestamp]
                
                if entry_row_series.empty:
                    if not trade_attempted: print(f"  [DEBUG] No entry found in option data at or after signal time. Skipping.")
                    continue
                
                entry_row = entry_row_series.iloc[0]
                entry_price = entry_row['open']

                if not trade_attempted:
                    print(f"  [DEBUG] Entry Row in Option DF:\n{entry_row}")
                    print(f"  [DEBUG] Entry Price (open): {entry_price}")

                # --- DYNAMIC TP/SL CALCULATION ---
                # For both Calls and Puts, you buy the option and want its price to rise.
                # So TP is always above entry, and SL is always below.
                exit_reason_text = {}
                
                # Take Profit
                if strategy_type == 'FIXED_POINTS':
                    tp_points = config['FIXED_POINTS']['TAKE_PROFIT_POINTS']
                    take_profit_price = entry_price + tp_points
                    exit_reason_text['tp'] = f"Target Profit ({tp_points} pts)"
                elif strategy_type == 'PERCENTAGE':
                    tp_percent = config['PERCENTAGE']['TAKE_PROFIT_PERCENT']
                    take_profit_price = entry_price * (1 + tp_percent / 100)
                    exit_reason_text['tp'] = f"Target Profit ({tp_percent}%)"

                # Stop Loss
                sl_config = config[strategy_type]
                if sl_config['STOP_LOSS_TYPE'] == 'SWING_LOW':
                    period = sl_config['SWING_LOW_PERIOD']
                    entry_idx = option_df.index.get_loc(entry_row.name)
                    start_idx = max(0, entry_idx - period)
                    lookback_window = option_df.iloc[start_idx:entry_idx]
                    if not lookback_window.empty:
                        stop_loss_price = lookback_window['low'].min()
                        exit_reason_text['sl'] = f"Stop Loss (Swing Low of last {period})"
                    else:
                        stop_loss_price = entry_price * (1 - 0.02) # 2% fallback
                        exit_reason_text['sl'] = "Stop Loss (2% Fallback)"
                elif sl_config['STOP_LOSS_TYPE'] == 'FIXED':
                    sl_points = sl_config['STOP_LOSS_POINTS']
                    stop_loss_price = entry_price - sl_points
                    exit_reason_text['sl'] = f"Stop Loss ({sl_points} pts)"
                elif sl_config['STOP_LOSS_TYPE'] == 'PERCENTAGE':
                    sl_percent = sl_config['STOP_LOSS_PERCENT']
                    stop_loss_price = entry_price * (1 - sl_percent / 100)
                    exit_reason_text['sl'] = f"Stop Loss ({sl_percent}%)"

                if not trade_attempted:
                    print(f"  [DEBUG] Calculated TP Price: {take_profit_price:.2f}, SL Price: {stop_loss_price:.2f}")
                    print("  [DEBUG] Starting search for exit condition...")

                # --- TRADE EXIT LOGIC ---
                exit_time, exit_price, exit_reason = None, None, None
                for exit_idx, (exit_timestamp, option_row) in enumerate(option_df.loc[entry_row.name:].iterrows()):
                    if not trade_attempted and exit_idx < 3: # Print first 3 checks
                        print(f"  [DEBUG]   - Checking {exit_timestamp}: High={option_row['high']:.2f}, Low={option_row['low']:.2f}")

                    if option_row['high'] >= take_profit_price:
                        exit_time, exit_price, exit_reason = exit_timestamp, take_profit_price, exit_reason_text['tp']
                        break
                    elif option_row['low'] <= stop_loss_price:
                        exit_time, exit_price, exit_reason = exit_timestamp, stop_loss_price, exit_reason_text['sl']
                        break
                    elif exit_timestamp.time() >= eod_exit_time:
                        exit_time, exit_price, exit_reason = exit_timestamp, option_row['close'], "End of Day"
                        break
                
                if exit_time is None:
                    last_row = option_df.iloc[-1]
                    exit_time, exit_price, exit_reason = last_row.name, last_row['close'], "End of Data"

                if not trade_attempted:
                    print(f"  [DEBUG] Exit found at {exit_time} for reason: {exit_reason}. Exit Price: {exit_price:.2f}")
                    print("  [DEBUG] <--- First signal processing finished. Turning off debug prints.")

                pnl = exit_price - entry_price
                
                daily_trades.append({
                    'date': date_str, 'type': trade_type, 'comments': signal_row.get(f'{trade_type} Comments', ''),
                    'entry_time': entry_row.name, 'exit_time': exit_time, 'entry_price': entry_price,
                    'exit_price': exit_price, 'stop_loss_price': stop_loss_price,
                    'take_profit_price': take_profit_price, 'pnl': pnl, 'exit_reason': exit_reason
                })
                
                trade_attempted = True # Mark that we've processed one trade for debugging

    return daily_trades