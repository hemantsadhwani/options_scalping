# option_tools/option_run_backtesting.py

import pandas as pd
from datetime import time, datetime

def run_option_backtest(signals_df, option_df, date_str, config, strategy_name, option_type, signal_col='Call'):
    """
    Runs a backtest specifically for option buying strategies.
    Only processes long positions for the specified option type.
    
    Args:
        signals_df: DataFrame with signals
        option_df: DataFrame with option price data (call or put)
        date_str: Date string for identification
        config: Configuration dictionary
        strategy_name: Name of the strategy
        option_type: 'Call' or 'Put'
        signal_col: Column name to check for signals
    """
    strategy_type = config.get('TRADE_STRATEGY', 'COMPLEX')
    print(f"  Running option backtest for {date_str} ({option_type} Options - {strategy_name} / Type: {strategy_type})")
    
    eod_hour, eod_minute = map(int, config['EOD_EXIT_TIME'].split(':'))
    eod_exit_time = time(eod_hour, eod_minute)
    
    last_entry_hour, last_entry_minute = map(int, config['LAST_ENTRY_TIME'].split(':'))
    last_entry_time = time(last_entry_hour, last_entry_minute)

    # Set datetime as index
    signals_df.set_index('datetime', inplace=True)
    option_df.set_index('datetime', inplace=True)

    daily_trades = []

    # Process only the signals for the specific option type
    for timestamp, signal_row in signals_df.iterrows():
        if timestamp.time() > last_entry_time:
            continue

        # Check if there's a signal for this option type
        if signal_row.get(signal_col, 0) == 1:
            entry_row_series = option_df[option_df.index >= timestamp]
            
            if entry_row_series.empty:
                continue
            
            entry_row = entry_row_series.iloc[0]
            entry_price = entry_row['open']

            # Simplified logic to avoid dependency on old config structure
            tp_percent = 15.0  # Generous TP for options
            sl_percent = 10.0  # Generous SL for options
            
            take_profit_price = entry_price * (1 + tp_percent / 100)
            stop_loss_price = entry_price * (1 - sl_percent / 100)
            
            exit_reason_text = {
                'tp': f"Option Target Profit ({tp_percent}%)",
                'sl': f"Option Stop Loss ({sl_percent}%)"
            }

            # Trade exit logic for options
            exit_time, exit_price, exit_reason = None, None, None
            for exit_timestamp, option_row in option_df.loc[entry_row.name:].iterrows():
                current_time = exit_timestamp.time()
                
                # Check profit target first (options can move fast)
                if option_row['high'] >= take_profit_price:
                    exit_time, exit_price, exit_reason = exit_timestamp, take_profit_price, exit_reason_text['tp']
                    break
                # Check stop loss
                elif option_row['low'] <= stop_loss_price:
                    exit_time, exit_price, exit_reason = exit_timestamp, stop_loss_price, exit_reason_text['sl']
                    break
                # Check end of day
                elif current_time >= eod_exit_time:
                    correct_exit_price = option_df.loc[exit_timestamp, 'close']
                    exit_time, exit_price, exit_reason = exit_timestamp, correct_exit_price, "End of Day"
                    break
            
            # Handle end of data
            if exit_time is None:
                last_row = option_df.iloc[-1]
                exit_time, exit_price, exit_reason = last_row.name, last_row['close'], "End of Data"

            pnl = exit_price - entry_price
            pnl_percent = ((exit_price - entry_price) / entry_price) * 100
            
            daily_trades.append({
                'date': date_str,
                'type': f'{option_type} Option (Long)',
                'comments': f'{strategy_name} - Option Buying',
                'entry_time': entry_row.name,
                'exit_time': exit_time,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'stop_loss_price': stop_loss_price,
                'take_profit_price': take_profit_price,
                'pnl': pnl,
                'pnl_percent': pnl_percent,
                'exit_reason': exit_reason
            })

    print(f"    Generated {len(daily_trades)} {option_type} option trades")
    return daily_trades

def run_combined_option_backtest(call_signals_df, put_signals_df, calls_df, puts_df, date_str, config, strategy_name):
    """
    Runs backtests for both call and put options and combines results.
    """
    all_trades = []
    
    # Backtest call options
    if not call_signals_df.empty and not calls_df.empty:
        call_trades = run_option_backtest(
            call_signals_df.copy(), calls_df.copy(), date_str, config, 
            strategy_name, 'Call', 'Call'
        )
        all_trades.extend(call_trades)
    
    # Backtest put options  
    if not put_signals_df.empty and not puts_df.empty:
        put_trades = run_option_backtest(
            put_signals_df.copy(), puts_df.copy(), date_str, config,
            strategy_name, 'Put', 'Put'
        )
        all_trades.extend(put_trades)
    
    return all_trades
