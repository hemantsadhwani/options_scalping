# nifty_option_trading/backtesting/run_analytics.py

import pandas as pd
import os

def generate_final_analytics_report():
    """
    Reads all individual backtest results, analyzes each day separately,
    and generates a comprehensive report with date-wise breakdowns.
    This version correctly filters on 'type' and 'comments' columns.
    """
    base_data_dir = 'data'
    output_dir = 'backtesting'
    report_output_file = os.path.join(output_dir, 'final_analytics_report.txt')
    
    os.makedirs(output_dir, exist_ok=True)

    all_results_dfs = []
    call_report_data = []
    put_report_data = []

    print("\n>>> STEP 5: GENERATING FINAL ANALYTICS REPORT...")
    print("  Scanning for daily backtest result files...")

    if not os.path.isdir(base_data_dir):
        print(f"❌ Error: Base data directory '{base_data_dir}' not found.")
        return

    subdirectories = sorted([d for d in os.listdir(base_data_dir) if os.path.isdir(os.path.join(base_data_dir, d))])

    for dir_name in subdirectories:
        results_file = os.path.join(base_data_dir, dir_name, 'backtest_results.csv')
        if os.path.exists(results_file):
            try:
                print(f"\n  -> Analyzing data for date: {dir_name}")
                daily_df = pd.read_csv(results_file, parse_dates=['entry_time', 'exit_time'])
                # Clean up column names just in case there are extra spaces
                daily_df.columns = daily_df.columns.str.strip()
                all_results_dfs.append(daily_df)

                def calculate_strategy_win_rate(trades_df):
                    if trades_df.empty: return 0.0
                    wins = trades_df[trades_df['exit_reason'].str.contains('Target Profit', case=False, na=False)].shape[0]
                    losses = trades_df[trades_df['exit_reason'].str.contains('Stop Loss', case=False, na=False)].shape[0]
                    total_resolved = wins + losses
                    return (wins / total_resolved) * 100 if total_resolved > 0 else 0.0

                # --- CORRECTED Daily Call Analysis ---
                # Filters on both 'type' and 'comments' columns
                call_reversal_df = daily_df[(daily_df['type'].str.strip() == 'Call') & (daily_df['comments'].str.strip() == 'Reversal')]
                call_cont_df = daily_df[(daily_df['type'].str.strip() == 'Call') & (daily_df['comments'].str.strip() == 'Continuation')]
                all_call_trades_df = pd.concat([call_reversal_df, call_cont_df])
                
                daily_call_results = {
                    'Date': dir_name,
                    'Call Reversal': len(call_reversal_df),
                    'Call continuation': len(call_cont_df),
                    'Call_Reversal_Win_%': f"{calculate_strategy_win_rate(call_reversal_df):.2f}%",
                    'Call_Cont_Win_%': f"{calculate_strategy_win_rate(call_cont_df):.2f}%",
                    'Overcall_Call_trades': len(all_call_trades_df),
                    'overall_Win_%': f"{calculate_strategy_win_rate(all_call_trades_df):.2f}%"
                }
                call_report_data.append(daily_call_results)

                # --- CORRECTED Daily Put Analysis ---
                put_reversal_df = daily_df[(daily_df['type'].str.strip() == 'Put') & (daily_df['comments'].str.strip() == 'Reversal')]
                put_cont_df = daily_df[(daily_df['type'].str.strip() == 'Put') & (daily_df['comments'].str.strip() == 'Continuation')]
                all_put_trades_df = pd.concat([put_reversal_df, put_cont_df])

                daily_put_results = {
                    'Date': dir_name,
                    'Put Reversal': len(put_reversal_df),
                    'Put continuation': len(put_cont_df),
                    'Put_Reversal_Win_%': f"{calculate_strategy_win_rate(put_reversal_df):.2f}%",
                    'Put_Cont_Win_%': f"{calculate_strategy_win_rate(put_cont_df):.2f}%",
                    'Overcall_Put_trades': len(all_put_trades_df),
                    'overall_Win_%': f"{calculate_strategy_win_rate(all_put_trades_df):.2f}%"
                }
                put_report_data.append(daily_put_results)

            except Exception as e:
                print(f"  ⚠️ Could not read or process {results_file}: {e}")

    if not all_results_dfs:
        # Handle case with no data
        return

    df = pd.concat(all_results_dfs, ignore_index=True)
    df.columns = df.columns.str.strip()

    # --- Overall Performance Calculations ---
    winning_trades = df[df['exit_reason'].str.contains('Target Profit', case=False, na=False)]
    losing_trades = df[df['exit_reason'].str.contains('Stop Loss', case=False, na=False)]
    total_trades = len(df)
    total_wins = len(winning_trades)
    total_losses = len(losing_trades)
    resolved_trades = total_wins + total_losses
    win_rate = (total_wins / resolved_trades) * 100 if resolved_trades > 0 else 0
    net_profit = df['pnl'].sum()
    profit_factor = abs(winning_trades['pnl'].sum() / losing_trades['pnl'].sum()) if losing_trades['pnl'].sum() != 0 else float('inf')
    
    # --- Create final tables from the daily results ---
    call_analytics_df = pd.DataFrame(call_report_data)
    put_analytics_df = pd.DataFrame(put_report_data)

    # --- Report Generation ---
    report_content = f"""
--- Trading Analytics Report ---

--- Overall Performance (based on Exit Reason) ---
Net Profit/Loss (All Trades): {net_profit:,.2f} points
Total Trades:                 {total_trades}
Total Wins (Target Hit):      {total_wins}
Total Losses (Stop Hit):      {total_losses}
Win Rate (Wins / [Wins+Losses]): {win_rate:.2f}%
Profit Factor:                {profit_factor:.2f}
Average PnL per Trade (All):  {df['pnl'].mean():,.2f} points

--- Call Options Analysis (Date-wise) ---
{call_analytics_df.to_string(index=False) if not call_analytics_df.empty else "No Call trades found."}

--- Put Options Analysis (Date-wise) ---
{put_analytics_df.to_string(index=False) if not put_analytics_df.empty else "No Put trades found."}

--- Exit Reason Breakdown (Overall) ---
{df['exit_reason'].value_counts().to_string()}
"""
    
    try:
        with open(report_output_file, 'w') as f:
            f.write(report_content)
        print(f"\n✅ Analytics report saved to '{report_output_file}'.")
        print(report_content)
    except Exception as e:
        print(f"❌ An error occurred while saving the analytics report: {e}")

if __name__ == '__main__':
    generate_final_analytics_report()