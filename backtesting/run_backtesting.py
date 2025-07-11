# backtesting/run_backtesting.py

import pandas as pd
from datetime import time, datetime

def run_backtest(signals_df, calls_df, puts_df, date_str, config, strategy_name, call_col='Call', put_col='Put'):
    """
    Runs a backtest for a single day's data. Assumes datetime columns are pre-formatted.
    """
    strategy_type = config['STRATEGY_TYPE']
    print(f"  Running backtest for {date_str} (Strategy: {strategy_name} / Type: {strategy_type})")
    
    eod_hour, eod_minute = map(int, config['EOD_EXIT_TIME'].split(':'))
    eod_exit_time = time(eod_hour, eod_minute)

    # The dataframes are now expected to have a pre-formatted datetime column.
    # We can set the index directly.
    signals_df.set_index('datetime', inplace=True)
    calls_df.set_index('datetime', inplace=True)
    puts_df.set_index('datetime', inplace=True)

    daily_trades = []

    for timestamp, signal_row in signals_df.iterrows():
        trade_type_map = {call_col: 'Call', put_col: 'Put'}
        for signal_col, trade_type in trade_type_map.items():
            if signal_row.get(signal_col, 0) == 1:
                option_df = calls_df if trade_type == 'Call' else puts_df
                entry_row_series = option_df[option_df.index >= timestamp]
                
                if entry_row_series.empty:
                    continue
                
                entry_row = entry_row_series.iloc[0]
                entry_price = entry_row['open']

                exit_reason_text = {}
                
                if strategy_type == 'FIXED_POINTS':
                    tp_points = config['FIXED_POINTS']['TAKE_PROFIT_POINTS']
                    take_profit_price = entry_price + tp_points
                    exit_reason_text['tp'] = f"Target Profit ({tp_points} pts)"
                elif strategy_type == 'PERCENTAGE':
                    tp_percent = config['PERCENTAGE']['TAKE_PROFIT_PERCENT']
                    take_profit_price = entry_price * (1 + tp_percent / 100)
                    exit_reason_text['tp'] = f"Target Profit ({tp_percent}%)"

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
                        stop_loss_price = entry_price * (1 - 0.02)
                        exit_reason_text['sl'] = "Stop Loss (2% Fallback)"
                elif sl_config['STOP_LOSS_TYPE'] == 'FIXED':
                    sl_points = sl_config['STOP_LOSS_POINTS']
                    stop_loss_price = entry_price - sl_points
                    exit_reason_text['sl'] = f"Stop Loss ({sl_points} pts)"
                elif sl_config['STOP_LOSS_TYPE'] == 'PERCENTAGE':
                    sl_percent = sl_config['STOP_LOSS_PERCENT']
                    stop_loss_price = entry_price * (1 - sl_percent / 100)
                    exit_reason_text['sl'] = f"Stop Loss ({sl_percent}%)"

                # Trade exit logic
                exit_time, exit_price, exit_reason = None, None, None
                for exit_timestamp, option_row in option_df.loc[entry_row.name:].iterrows():
                    current_time = exit_timestamp.time()
                    
                    if option_row['high'] >= take_profit_price:
                        exit_time, exit_price, exit_reason = exit_timestamp, take_profit_price, exit_reason_text['tp']
                        break
                    elif option_row['low'] <= stop_loss_price:
                        exit_time, exit_price, exit_reason = exit_timestamp, stop_loss_price, exit_reason_text['sl']
                        break
                    elif current_time >= eod_exit_time:
                        correct_exit_price = option_df.loc[exit_timestamp, 'close']
                        exit_time, exit_price, exit_reason = exit_timestamp, correct_exit_price, "End of Day"
                        break
                
                if exit_time is None:
                    last_row = option_df.iloc[-1]
                    exit_time, exit_price, exit_reason = last_row.name, last_row['close'], "End of Data"

                pnl = exit_price - entry_price
                
                daily_trades.append({
                    'date': date_str,
                    'type': trade_type,
                    'comments': strategy_name,
                    'entry_time': entry_row.name,
                    'exit_time': exit_time,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'stop_loss_price': stop_loss_price,
                    'take_profit_price': take_profit_price,
                    'pnl': pnl,
                    'exit_reason': exit_reason
                })

    return daily_trades