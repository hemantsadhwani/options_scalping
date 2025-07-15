# option_tools/options_run_analytics.py

import pandas as pd
import os
from tabulate import tabulate

def get_option_signal_counts(file_path, signal_col):
    """Get signal counts for option files"""
    if not os.path.exists(file_path):
        return 0
    try:
        df = pd.read_csv(file_path)
        if signal_col in df.columns:
            return df[signal_col].sum()
    except pd.errors.EmptyDataError:
        return 0
    return 0

def get_option_trade_analytics(file_path):
    """Get trade analytics specifically for option trades"""
    if not os.path.exists(file_path):
        return 0, 0.0, 0.0
    try:
        df = pd.read_csv(file_path)
        if df.empty:
            return 0, 0.0, 0.0
        
        pnl_col = 'P/L'
        if pnl_col not in df.columns:
            return 0, 0.0, 0.0
            
        # Convert P/L to numeric, handling string format
        df[pnl_col] = pd.to_numeric(df[pnl_col], errors='coerce').fillna(0)
        
        trade_count = len(df)
        win_rate = (df[pnl_col] > 0).mean() * 100 if trade_count > 0 else 0.0
        total_pl = df[pnl_col].sum()
        
        return trade_count, win_rate, total_pl
    except pd.errors.EmptyDataError:
        return 0, 0.0, 0.0

def get_aggregated_option_trade_analytics(trades_dir, option_type):
    """Get aggregated trade analytics for all strategy files of a specific option type"""
    if option_type.lower() == 'call':
        trade_files = ['call_cont_trades.csv', 'call_rev_v1_trades.csv', 'call_rev_v2_trades.csv']
    else:  # put
        trade_files = ['put_cont_trades.csv', 'put_rev_v1_trades.csv', 'put_rev_v2_trades.csv']
    
    total_trades = 0
    total_wins = 0
    total_pl = 0.0
    
    for trade_file in trade_files:
        file_path = os.path.join(trades_dir, trade_file)
        trades, wr, pl = get_option_trade_analytics(file_path)
        total_trades += trades
        total_wins += int(trades * (wr / 100)) if trades > 0 else 0
        total_pl += pl
    
    # Calculate overall win rate
    overall_wr = (total_wins / total_trades * 100) if total_trades > 0 else 0.0
    
    return total_trades, overall_wr, total_pl

def get_strategy_specific_analytics(trades_dir, option_type):
    """Get strategy-specific trade analytics"""
    if option_type.lower() == 'call':
        strategy_files = {
            'Continuation': 'call_cont_trades.csv',
            'Reversal v1': 'call_rev_v1_trades.csv', 
            'Reversal v2': 'call_rev_v2_trades.csv'
        }
    else:  # put
        strategy_files = {
            'Continuation': 'put_cont_trades.csv',
            'Reversal v1': 'put_rev_v1_trades.csv',
            'Reversal v2': 'put_rev_v2_trades.csv'
        }
    
    strategy_data = {}
    for strategy, filename in strategy_files.items():
        file_path = os.path.join(trades_dir, filename)
        trades, wr, pl = get_option_trade_analytics(file_path)
        strategy_data[strategy] = {
            'trades': trades,
            'win_rate': wr,
            'pnl': pl
        }
    
    return strategy_data

def run_option_analysis(base_dir_prefix='', cont_signals_filename='call_cont_out.csv', rev_signals_filename='call_rev_out.csv', backtest_folder='backtest', trades_folder='trades', analytics_filename_prefix='analytics_call_', analytics_filename_prefix_put='analytics_put_'):
    """
    Run analytics specifically for option trading data.
    Processes call and put option data separately with strategy-specific columns.
    """
    data_root = './data'
    dates = sorted([d for d in os.listdir(data_root) if os.path.isdir(os.path.join(data_root, d))])

    if not dates:
        print("No date directories found in ./data.")
        return {}

    print(f"--- Generating Option Analytics Reports for {len(dates)} Dates ---")

    per_date_stats = {}
    total_trades_call = {"Continuation": 0, "Reversal v1": 0, "Reversal v2": 0}
    total_wins_call = {"Continuation": 0, "Reversal v1": 0, "Reversal v2": 0}
    total_pnl_call = {"Continuation": 0.0, "Reversal v1": 0.0, "Reversal v2": 0.0}
    total_trades_put = {"Continuation": 0, "Reversal v1": 0, "Reversal v2": 0}
    total_wins_put = {"Continuation": 0, "Reversal v1": 0, "Reversal v2": 0}
    total_pnl_put = {"Continuation": 0.0, "Reversal v1": 0.0, "Reversal v2": 0.0}

    for date in dates:
        date_dir = os.path.join(data_root, date)
        
        # Check if call and put directories exist
        call_dir = os.path.join(date_dir, 'call')
        put_dir = os.path.join(date_dir, 'put')
        
        if not (os.path.exists(call_dir) and os.path.exists(put_dir)):
            print(f"  - Skipping {date}, missing call/put directories")
            continue

        # --- CALL OPTIONS ANALYTICS ---
        call_cont_signals_file = os.path.join(call_dir, 'call_cont_out.csv')
        call_rev_signals_file = os.path.join(call_dir, 'call_rev_out.csv')
        call_trades_dir = os.path.join(call_dir, 'trades')
        
        call_analytics_data = {
            "Continuation": {},
            "Reversal v1": {},
            "Reversal v2": {}
        }

        # Call Signals
        call_analytics_data["Continuation"]['Signals'] = get_option_signal_counts(call_cont_signals_file, 'Call')
        call_analytics_data["Reversal v1"]['Signals'] = get_option_signal_counts(call_rev_signals_file, 'Call')
        call_analytics_data["Reversal v2"]['Signals'] = get_option_signal_counts(call_rev_signals_file, 'Call_v2')

        # Call Strategy-specific trades and backtest
        call_strategy_data = get_strategy_specific_analytics(call_trades_dir, 'call')
        
        for strategy in ["Continuation", "Reversal v1", "Reversal v2"]:
            trades = call_strategy_data[strategy]['trades']
            wr = call_strategy_data[strategy]['win_rate']
            pl = call_strategy_data[strategy]['pnl']
            
            call_analytics_data[strategy]['Trades (Trades/WR%/P&L)'] = f"{trades} / {wr:.2f}% / {pl:.2f}"
            call_analytics_data[strategy]['Backtest (Trades/WR%)'] = "0 / 0.00%"  # Placeholder for backtest
            
            # Accumulate totals
            total_trades_call[strategy] += trades
            total_wins_call[strategy] += int(trades * (wr / 100)) if trades > 0 else 0
            total_pnl_call[strategy] += pl

        # Call Options Report
        call_headers = ["Metric", "Continuation", "Reversal v1", "Reversal v2"]
        call_table = []
        call_metrics = ['Signals', 'Backtest (Trades/WR%)', 'Trades (Trades/WR%/P&L)']
        
        for metric in call_metrics:
            row = [metric] + [call_analytics_data[strategy][metric] for strategy in ["Continuation", "Reversal v1", "Reversal v2"]]
            call_table.append(row)
        
        call_report_str = f"--- Call Options Analytics Report for Date: {date} ---\n\n"
        call_report_str += tabulate(call_table, headers=call_headers, tablefmt="grid")
        
        # Save Call Options Report
        call_report_path = os.path.join(call_dir, f'{analytics_filename_prefix}{date}.txt')
        try:
            with open(call_report_path, 'w') as f:
                f.write(call_report_str)
            print(f"✅ Call options analytics report saved to {call_report_path}")
        except IOError as e:
            print(f"  ✗ ERROR saving call options report for {date}: {e}")

        # --- PUT OPTIONS ANALYTICS ---
        put_cont_signals_file = os.path.join(put_dir, 'put_cont_out.csv')
        put_rev_signals_file = os.path.join(put_dir, 'put_rev_out.csv')
        put_trades_dir = os.path.join(put_dir, 'trades')
        
        put_analytics_data = {
            "Continuation": {},
            "Reversal v1": {},
            "Reversal v2": {}
        }

        # Put Signals
        put_analytics_data["Continuation"]['Signals'] = get_option_signal_counts(put_cont_signals_file, 'Put')
        put_analytics_data["Reversal v1"]['Signals'] = get_option_signal_counts(put_rev_signals_file, 'Put')
        put_analytics_data["Reversal v2"]['Signals'] = get_option_signal_counts(put_rev_signals_file, 'Put_v2')

        # Put Strategy-specific trades and backtest
        put_strategy_data = get_strategy_specific_analytics(put_trades_dir, 'put')
        
        for strategy in ["Continuation", "Reversal v1", "Reversal v2"]:
            trades = put_strategy_data[strategy]['trades']
            wr = put_strategy_data[strategy]['win_rate']
            pl = put_strategy_data[strategy]['pnl']
            
            put_analytics_data[strategy]['Trades (Trades/WR%/P&L)'] = f"{trades} / {wr:.2f}% / {pl:.2f}"
            put_analytics_data[strategy]['Backtest (Trades/WR%)'] = "0 / 0.00%"  # Placeholder for backtest
            
            # Accumulate totals
            total_trades_put[strategy] += trades
            total_wins_put[strategy] += int(trades * (wr / 100)) if trades > 0 else 0
            total_pnl_put[strategy] += pl

        # Put Options Report
        put_headers = ["Metric", "Continuation", "Reversal v1", "Reversal v2"]
        put_table = []
        put_metrics = ['Signals', 'Backtest (Trades/WR%)', 'Trades (Trades/WR%/P&L)']
        
        for metric in put_metrics:
            row = [metric] + [put_analytics_data[strategy][metric] for strategy in ["Continuation", "Reversal v1", "Reversal v2"]]
            put_table.append(row)
        
        put_report_str = f"--- Put Options Analytics Report for Date: {date} ---\n\n"
        put_report_str += tabulate(put_table, headers=put_headers, tablefmt="grid")
        
        # Save Put Options Report
        put_report_path = os.path.join(put_dir, f'{analytics_filename_prefix_put}{date}.txt')
        try:
            with open(put_report_path, 'w') as f:
                f.write(put_report_str)
            print(f"✅ Put options analytics report saved to {put_report_path}")
        except IOError as e:
            print(f"  ✗ ERROR saving put options report for {date}: {e}")

        # Store per-date stats
        total_call_trades = sum(call_strategy_data[s]['trades'] for s in call_strategy_data)
        total_put_trades = sum(put_strategy_data[s]['trades'] for s in put_strategy_data)
        
        if total_call_trades > 0 or total_put_trades > 0:
            per_date_stats[date] = {
                'call_trades': total_call_trades,
                'put_trades': total_put_trades,
            }

    # --- Final Summary Report ---
    print(f"\n--- Call Options Trading Summary ---")
    for strategy in ["Continuation", "Reversal v1", "Reversal v2"]:
        wr = (total_wins_call[strategy]/total_trades_call[strategy]*100) if total_trades_call[strategy] > 0 else 0
        print(f"{strategy}: {total_trades_call[strategy]} trades, {wr:.2f}% WR, P&L: {total_pnl_call[strategy]:.2f}")
    
    print(f"\n--- Put Options Trading Summary ---")
    for strategy in ["Continuation", "Reversal v1", "Reversal v2"]:
        wr = (total_wins_put[strategy]/total_trades_put[strategy]*100) if total_trades_put[strategy] > 0 else 0
        print(f"{strategy}: {total_trades_put[strategy]} trades, {wr:.2f}% WR, P&L: {total_pnl_put[strategy]:.2f}")

    return per_date_stats
