# nifty_option_trading/backtesting/run_backtesting.py

import pandas as pd
import os
import json 
from datetime import time, datetime

def run_backtest_for_day(signals_df, calls_df, puts_df, date_str, config):
    """
    Runs a detailed, bar-by-bar backtest for a single day's data using an internal config object.
    """
    strategy_type = config['STRATEGY_TYPE']
    print(f"--- Running backtest for {date_str} (Strategy: {strategy_type}) ---")
    
    eod_hour, eod_minute = map(int, config['EOD_EXIT_TIME'].split(':'))
    eod_exit_time = time(eod_hour, eod_minute)

    # --- State Variables ---
    in_trade = False
    trade_type = None
    entry_price = 0
    stop_loss_price = 0
    take_profit_price = 0
    exit_reason_text = ""
    trade_details = {}
    daily_trades = []
    queued_signal = None

    signals_df.set_index('datetime', inplace=True)
    calls_df.set_index('datetime', inplace=True)
    puts_df.set_index('datetime', inplace=True)
    
    for timestamp, signal_row in signals_df.iterrows():
    
        # --- 1. CHECK FOR TRADE EXIT ---
        if in_trade:
            option_price_row = None
            try:
                if trade_type == 'Call':
                    option_price_row = calls_df.loc[timestamp]
                elif trade_type == 'Put':
                    option_price_row = puts_df.loc[timestamp]
            except KeyError:
                continue

            exit_reason = None
            exit_price = 0

            if option_price_row['high'] >= take_profit_price:
                exit_price = take_profit_price
                exit_reason = exit_reason_text['tp']
            elif option_price_row['low'] <= stop_loss_price:
                exit_price = stop_loss_price
                exit_reason = exit_reason_text['sl']
            elif timestamp.time() >= eod_exit_time:
                exit_price = option_price_row['close']
                exit_reason = "End of Day"

            if exit_reason:
                pnl = exit_price - entry_price
                trade_details.update({
                    'exit_time': timestamp,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'exit_reason': exit_reason
                })
                daily_trades.append(trade_details)
                print(f"  Exited {trade_details.get('type')} trade at {timestamp} for {exit_reason}. PnL: {pnl:.2f}")
                in_trade = False
                trade_type = None
                trade_details = {}

        # --- 2. CHECK FOR TRADE ENTRY ---
        if not in_trade:
            signal_to_action = None
            if queued_signal:
                signal_to_action = queued_signal
                print(f"  Actioning queued {signal_to_action['type']} signal from {signal_to_action['time']}.")
                queued_signal = None
            elif signal_row['Call'] == 1:
                signal_to_action = {'type': 'Call', 'time': timestamp, 'comments': signal_row.get('Call Comments', '')}
            elif signal_row['Put'] == 1:
                signal_to_action = {'type': 'Put', 'time': timestamp, 'comments': signal_row.get('Put Comments', '')}

            if signal_to_action:
                trade_type_to_enter = signal_to_action['type']
                option_df = calls_df if trade_type_to_enter == 'Call' else puts_df
                entry_row_series = option_df[option_df.index >= signal_to_action['time']]
                
                if not entry_row_series.empty:
                    entry_row = entry_row_series.iloc[0]
                    in_trade = True
                    trade_type = trade_type_to_enter
                    entry_price = entry_row['open']
                    
                    # --- DYNAMIC TP/SL CALCULATION BASED ON CONFIG ---
                    exit_reason_text = {}
                    # Calculate Take Profit
                    if strategy_type == 'FIXED_POINTS':
                        tp_points = config['FIXED_POINTS']['TAKE_PROFIT_POINTS']
                        take_profit_price = entry_price + tp_points
                        exit_reason_text['tp'] = f"Target Profit ({tp_points} pts)"
                    elif strategy_type == 'PERCENTAGE':
                        tp_percent = config['PERCENTAGE']['TAKE_PROFIT_PERCENT']
                        take_profit_price = entry_price * (1 + tp_percent / 100)
                        exit_reason_text['tp'] = f"Target Profit ({tp_percent}%)"

                    # Calculate Stop Loss
                    sl_config = config[strategy_type]
                    if sl_config['STOP_LOSS_TYPE'] == 'SWING_LOW':
                        period = sl_config['SWING_LOW_PERIOD']
                        entry_idx = option_df.index.get_loc(entry_row.name)
                        start_idx = max(0, entry_idx - period)
                        lookback_window = option_df.iloc[start_idx:entry_idx]
                        
                        if not lookback_window.empty:
                            stop_loss_price = lookback_window['low'].min()
                            exit_reason_text['sl'] = f"Stop Loss (Swing Low of last {period})"
                        else: # Fallback
                            stop_loss_price = entry_price * (1 - 2/100) # 2% fallback
                            exit_reason_text['sl'] = "Stop Loss (2% Fallback)"
                    elif sl_config['STOP_LOSS_TYPE'] == 'FIXED': # Only for FIXED_POINTS strategy
                        sl_points = sl_config['STOP_LOSS_POINTS']
                        stop_loss_price = entry_price - sl_points
                        exit_reason_text['sl'] = f"Stop Loss ({sl_points} pts)"
                    elif sl_config['STOP_LOSS_TYPE'] == 'PERCENTAGE': # Only for PERCENTAGE strategy
                        sl_percent = sl_config['STOP_LOSS_PERCENT']
                        stop_loss_price = entry_price * (1 - sl_percent / 100)
                        exit_reason_text['sl'] = f"Stop Loss ({sl_percent}%)"

                    trade_details = {
                        'date': date_str, 'type': trade_type, 'entry_time': entry_row.name,
                        'entry_price': entry_price, 'stop_loss_price': stop_loss_price,
                        'take_profit_price': take_profit_price, 'comments': signal_to_action['comments']
                    }
                    print(f"  Entered {trade_type} trade at {entry_row.name} | Price: {entry_price:.2f} | TP: {take_profit_price:.2f} | SL: {stop_loss_price:.2f}")

        # --- 3. QUEUE NEW SIGNALS IF IN TRADE ---
        elif in_trade and not queued_signal:
            if signal_row['Call'] == 1:
                queued_signal = {'type': 'Call', 'time': timestamp, 'comments': signal_row.get('Call Comments', '')}
                print(f"  In an active trade. Queued new Call signal from {timestamp}.")
            elif signal_row['Put'] == 1:
                queued_signal = {'type': 'Put', 'time': timestamp, 'comments': signal_row.get('Put Comments', '')}
                print(f"  In an active trade. Queued new Put signal from {timestamp}.")

    if not daily_trades:
        print(f"  No trades were executed for {date_str}.")
    
    return daily_trades


def run_backtest():
    """
    Main function to orchestrate backtesting.
    """
    # ==============================================================================
    # --- CONFIGURATION SETTINGS ---
    # ==============================================================================
    CONFIG = {
      "STRATEGY_TYPE": "PERCENTAGE",  # Can be "FIXED_POINTS" or "PERCENTAGE"

      "FIXED_POINTS": {
        "TAKE_PROFIT_POINTS": 12,
        "STOP_LOSS_TYPE": "SWING_LOW", # Can be "FIXED" or "SWING_LOW"
        "STOP_LOSS_POINTS": 6,
        "SWING_LOW_PERIOD": 5
      },

      "PERCENTAGE": {
        "TAKE_PROFIT_PERCENT": 7.0,
        "STOP_LOSS_TYPE": "PERCENTAGE", # Can be "PERCENTAGE" or "SWING_LOW"
        "STOP_LOSS_PERCENT": 7,
        "SWING_LOW_PERIOD": 5
      },

      "EOD_EXIT_TIME": "15:30"
    }
    # ==============================================================================
    
    base_data_dir = 'data'
    print("\n>>> STEP 4: RUNNING BACKTEST...")

    if not os.path.isdir(base_data_dir):
        print(f"❌ Error: Base data directory '{base_data_dir}' not found.")
        return

    subdirectories = sorted([d for d in os.listdir(base_data_dir) if os.path.isdir(os.path.join(base_data_dir, d))])
    total_trades_across_all_days = 0

    for dir_name in subdirectories:
        ddmm_path = os.path.join(base_data_dir, dir_name)
        signals_file = os.path.join(ddmm_path, 'tradeview_utc_output.csv')
        calls_file = os.path.join(ddmm_path, 'call', 'call_out.csv')
        puts_file = os.path.join(ddmm_path, 'put', 'put_out.csv')

        if not all(os.path.exists(f) for f in [signals_file, calls_file, puts_file]):
            print(f"  Skipping {ddmm_path}: Missing one or more required CSV files.")
            continue

        try:
            signals_df = pd.read_csv(signals_file, parse_dates=['datetime'])
            calls_df = pd.read_csv(calls_file, parse_dates=['datetime'])
            puts_df = pd.read_csv(puts_file, parse_dates=['datetime'])
            
            # Pass the internal CONFIG object to the daily backtest function
            daily_trades = run_backtest_for_day(signals_df, calls_df, puts_df, dir_name, CONFIG)
            
            if daily_trades:
                results_df = pd.DataFrame(daily_trades)
                output_path = os.path.join(ddmm_path, 'backtest_results.csv')
                
                cols_order = ['date', 'type', 'comments', 'entry_time', 'exit_time', 'entry_price', 'exit_price', 'stop_loss_price', 'take_profit_price', 'pnl', 'exit_reason']
                for col in cols_order:
                    if col not in results_df.columns:
                        results_df[col] = None
                results_df = results_df[cols_order]
                
                results_df.to_csv(output_path, index=False)
                print(f"  ✅ Backtest results for {dir_name} saved to '{output_path}'.")
                total_trades_across_all_days += len(daily_trades)

        except Exception as e:
            print(f"❌ An error occurred processing {dir_name}: {e}")

    if total_trades_across_all_days > 0:
        print(f"\n✅ Backtest complete. A total of {total_trades_across_all_days} trades were recorded.")
    else:
        print("\n⚠️ Backtest finished, but no trades were executed across all days.")