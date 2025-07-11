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

def run_analysis():
    data_root = './data'
    dates = sorted([d for d in os.listdir(data_root) if os.path.isdir(os.path.join(data_root, d))])

    if not dates:
        print("No date directories found in ./data.")
        return

    print(f"--- Generating Analytics Reports for {len(dates)} Dates ---")

    for date in dates:
        date_dir = os.path.join(data_root, date)
        
        # --- File Paths ---
        cont_signals_file = os.path.join(date_dir, 'tradeview_cont_output.csv')
        rev_signals_file = os.path.join(date_dir, 'tradeview_rev_output.csv')

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

        # Backtest & Trade Execution Stats
        for strat_name, strat_key in [("Continuation", "cont"), ("Reversal v1", "rev"), ("Reversal v2", "rev_v2")]:
            # Backtest Raw
            trades, wr, _ = get_trade_analytics(os.path.join(date_dir, 'backtest', f'backtest_results_{strat_key}.csv'))
            analytics_data[strat_name]['Backtest Raw (Trades/WR%)'] = f"{trades} / {wr:.2f}%"
            
            # Backtest CPR
            trades, wr, _ = get_trade_analytics(os.path.join(date_dir, 'backtest_crp', f'backtest_results_{strat_key}.csv'))
            analytics_data[strat_name]['Backtest CPR (Trades/WR%)'] = f"{trades} / {wr:.2f}%"

            # Determine the correct trade file key
            trade_file_key = 'rev_v1' if strat_key == 'rev' else strat_key

            # Trades Raw
            trades, wr, pl = get_trade_analytics(os.path.join(date_dir, 'trades', f'{trade_file_key}_trades.csv'))
            analytics_data[strat_name]['Trades Raw (Trades/WR%/P&L)'] = f"{trades} / {wr:.2f}% / {pl:.2f}"

            # Trades CPR
            trades, wr, pl = get_trade_analytics(os.path.join(date_dir, 'trades_crp', f'{trade_file_key}_trades.csv'))
            analytics_data[strat_name]['Trades CPR (Trades/WR%/P&L)'] = f"{trades} / {wr:.2f}% / {pl:.2f}"

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
            
        report_str = f"--- Analytics Report for Date: {date} ---\n\n"
        report_str += tabulate(table, headers=headers, tablefmt="grid")
        
        # --- Save to File ---
        report_path = os.path.join(date_dir, f'analytics_{date}.txt')
        try:
            with open(report_path, 'w') as f:
                f.write(report_str)
            print(f"✅ Analytics report saved to {report_path}")
        except IOError as e:
            print(f"  ✗ ERROR saving report for {date}: {e}")

if __name__ == "__main__":
    run_analysis()

if __name__ == "__main__":
    run_analysis()
