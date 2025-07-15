import pandas as pd
import os
from tabulate import tabulate

def get_signal_counts(file_path, signal_col):
    if not os.path.exists(file_path):
        return 0
    try:
        df = pd.read_csv(file_path)
        if signal_col in df.columns:
            return df[signal_col].sum()
    except pd.errors.EmptyDataError:
        return 0
    return 0

def get_trade_analytics(file_path):
    if not os.path.exists(file_path):
        return 0, 0.0, 0.0
    try:
        df = pd.read_csv(file_path)
        if df.empty:
            return 0, 0.0, 0.0
        
        pnl_col = 'pnl' if 'pnl' in df.columns else 'P/L'
        df[pnl_col] = pd.to_numeric(df[pnl_col], errors='coerce').fillna(0)
        
        trade_count = len(df)
        win_rate = (df[pnl_col] > 0).mean() * 100 if trade_count > 0 else 0.0
        total_pl = df[pnl_col].sum()
        
        return trade_count, win_rate, total_pl
    except pd.errors.EmptyDataError:
        return 0, 0.0, 0.0

def run_analysis(base_dir_prefix='', cont_signals_filename='tradeview_cont_output.csv', rev_signals_filename='tradeview_rev_output.csv', backtest_folder='backtest', backtest_crp_folder='backtest_crp', trades_folder='trades', trades_crp_folder='trades_crp', analytics_filename_prefix='analytics_'):
    data_root = './data'
    dates = sorted([d for d in os.listdir(data_root) if os.path.isdir(os.path.join(data_root, d))])

    if not dates:
        print("No date directories found in ./data.")
        return

    print(f"--- Generating Analytics Reports for {len(dates)} Dates ---")

    per_date_stats = {}
    total_trades_cpr = {"Continuation": 0, "Reversal v1": 0, "Reversal v2": 0}
    total_wins_cpr = {"Continuation": 0, "Reversal v1": 0, "Reversal v2": 0}
    total_pnl_cpr = {"Continuation": 0.0, "Reversal v1": 0.0, "Reversal v2": 0.0}

    for date in dates:
        date_dir = os.path.join(data_root, date, base_dir_prefix)
        
        # --- File Paths ---
        cont_signals_file = os.path.join(date_dir, cont_signals_filename)
        rev_signals_file = os.path.join(date_dir, rev_signals_filename)

        # --- Data Collection ---
        analytics_data = {
            "Continuation": {},
            "Reversal v1": {},
            "Reversal v2": {}
        }

        # Signal Counts
        for strat, key, file in [("Continuation", "cont", cont_signals_file), 
                                 ("Reversal v1", "rev", rev_signals_file), 
                                 ("Reversal v2", "rev_v2", rev_signals_file)]:
            call_col = 'Call' if strat == "Continuation" or strat == "Reversal v1" else 'Call_v2'
            put_col = 'Put' if strat == "Continuation" or strat == "Reversal v1" else 'Put_v2'
            
            analytics_data[strat]['Signals (Call/Put)'] = f"{get_signal_counts(file, call_col)} / {get_signal_counts(file, put_col)}"
            analytics_data[strat]['CPR Signals (Call/Put)'] = f"{get_signal_counts(file, f'{call_col}_crp')} / {get_signal_counts(file, f'{put_col}_crp')}"

        # Store raw numeric values for calculations
        raw_trades_data = {}
        
        # Backtest & Trade Execution Stats
        for strat_name, strat_key in [("Continuation", "cont"), ("Reversal v1", "rev"), ("Reversal v2", "rev_v2")]:
        # Backtest Raw
            trades, wr, _ = get_trade_analytics(os.path.join(date_dir, backtest_folder, f'backtest_results_{strat_key}.csv'))
            analytics_data[strat_name]['Backtest Raw (Trades/WR%)'] = f"{trades} / {wr:.2f}%"
            
            # Backtest CPR
            trades, wr, _ = get_trade_analytics(os.path.join(date_dir, backtest_crp_folder, f'backtest_results_{strat_key}.csv'))
            analytics_data[strat_name]['Backtest CPR (Trades/WR%)'] = f"{trades} / {wr:.2f}%"

            # Determine the correct trade file key
            trade_file_key = 'rev_v1' if strat_key == 'rev' else strat_key

            # Trades Raw
            trades, wr, pl = get_trade_analytics(os.path.join(date_dir, trades_folder, f'{trade_file_key}_trades.csv'))
            analytics_data[strat_name]['Trades Raw (Trades/WR%/P&L)'] = f"{trades} / {wr:.2f}% / {pl:.2f}"

            # Trades CPR - Store both formatted string and raw values
            trades_cpr, wr_cpr, pl_cpr = get_trade_analytics(os.path.join(date_dir, trades_crp_folder, f'{trade_file_key}_trades.csv'))
            analytics_data[strat_name]['Trades CPR (Trades/WR%/P&L)'] = f"{trades_cpr} / {wr_cpr:.2f}% / {pl_cpr:.2f}"
            
            # Store raw numeric values for calculations
            raw_trades_data[strat_name] = {
                'trades': trades_cpr,
                'wr': wr_cpr,
                'pl': pl_cpr
            }
            
            # Accumulate totals for the final summary
            total_trades_cpr[strat_name] += trades_cpr
            total_wins_cpr[strat_name] += int(trades_cpr * (wr_cpr / 100))
            total_pnl_cpr[strat_name] += pl_cpr

        # --- Formatting ---
        headers = ["Metric", "Continuation", "Reversal v1", "Reversal v2"]
        table = []
        metrics = [
            'Signals (Call/Put)', 'CPR Signals (Call/Put)', 
            'Backtest Raw (Trades/WR%)', 'Backtest CPR (Trades/WR%)',
            'Trades Raw (Trades/WR%/P&L)', 'Trades CPR (Trades/WR%/P&L)'
        ]
        for metric in metrics:
            row = [metric] + [analytics_data[strat][metric] for strat in ["Continuation", "Reversal v1", "Reversal v2"]]
            table.append(row)
        
        # --- CPR Width Calculation ---
        cpr_width = "N/A"
        try:
            utc_df = pd.read_csv(os.path.join(date_dir, 'tradeview_utc.csv'))
            if not utc_df.empty:
                daily_tc = utc_df['Daily TC'].iloc[0]
                daily_bc = utc_df['Daily BC'].iloc[0]
                if pd.notna(daily_tc) and pd.notna(daily_bc):
                    cpr_width = f"{daily_tc - daily_bc:.2f}"
        except FileNotFoundError:
            pass # File might not exist, width will remain "N/A"

        # Store raw stats for the date, only if there are any trades
        total_trades_for_date = raw_trades_data['Continuation']['trades'] + raw_trades_data['Reversal v1']['trades'] + raw_trades_data['Reversal v2']['trades']
        if total_trades_for_date > 0:
            per_date_stats[date] = {
                'cpr_width': cpr_width,
                'cont_trades': raw_trades_data['Continuation']['trades'], 
                'cont_wins': int(raw_trades_data['Continuation']['trades'] * (raw_trades_data['Continuation']['wr'] / 100)), 
                'cont_pnl': raw_trades_data['Continuation']['pl'],
                'rev1_trades': raw_trades_data['Reversal v1']['trades'], 
                'rev1_wins': int(raw_trades_data['Reversal v1']['trades'] * (raw_trades_data['Reversal v1']['wr'] / 100)), 
                'rev1_pnl': raw_trades_data['Reversal v1']['pl'],
                'rev2_trades': raw_trades_data['Reversal v2']['trades'], 
                'rev2_wins': int(raw_trades_data['Reversal v2']['trades'] * (raw_trades_data['Reversal v2']['wr'] / 100)), 
                'rev2_pnl': raw_trades_data['Reversal v2']['pl'],
            }
            
        report_str = f"--- Analytics Report for Date: {date} ---\n\n"
        report_str += tabulate(table, headers=headers, tablefmt="grid")
        
        # --- Save to File ---
        report_path = os.path.join(date_dir, f'{analytics_filename_prefix}{date}.txt')
        try:
            with open(report_path, 'w') as f:
                f.write(report_str)
            print(f"✅ Analytics report saved to {report_path}")
        except IOError as e:
            print(f"  ✗ ERROR saving report for {date}: {e}")

    # --- Final Summary Report ---
    # Return the raw per-date stats and the totals
    return per_date_stats
