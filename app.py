# nifty_option_trading/app.py (With Integrated Cleanup Step)

import os
import pandas as pd
import yaml
from datetime import time

# --- Core Imports ---
from run_process_data import run_process_data
from strategies.run_cont_strategy import generate_continuation_strategies
from strategies.run_rev_strategy import generate_reversal_strategies
from backtesting.run_backtesting import run_backtest
from backtesting.run_analytics import generate_final_analytics_report

# *** CHANGE: Import the cleanup function ***
from tools.clean_data_dir import clean_generated_files

# --- Step Controllers ---
# Set run_cleanup to True to ensure a fresh run every time
run_cleanup = True    # <<< Your suggestion is implemented here
run_step_1 = True    # Process Raw Data
run_step_2 = True    # Generate Continuation Strategy Signals
run_step_3 = True    # Generate Reversal Strategy Signals
run_step_4 = True    # Run Backtest
run_step_5 = True    # Generate Final Analytics Report

def main():
    """
    Main entry point to run the entire trading analysis pipeline.
    """
    print("--- Starting Trading Application Pipeline ---")

    # Load configuration from a YAML file
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print("FATAL ERROR: config.yaml not found. Please ensure it exists.")
        return

    last_entry_time_str = config.get('LAST_ENTRY_TIME', '15:00')
    last_entry_hour, last_entry_minute = map(int, last_entry_time_str.split(':'))
    last_entry_time = time(last_entry_hour, last_entry_minute)
    
    # *** CHANGE: Call the cleanup function at the very beginning ***
    if run_cleanup:
        print("\n>>> STEP 0: CLEANING PREVIOUSLY GENERATED FILES...")
        clean_generated_files()
        print("-" * 50)

    if run_step_1:
        print("\n>>> STEP 1: PROCESSING RAW DATA FILES...")
        run_process_data()
        print("-" * 50)

    if run_step_2:
        print("\n>>> STEP 2: GENERATING CONTINUATION STRATEGIES...")
        generate_continuation_strategies()
        print("-" * 50)

    if run_step_3:
        print("\n>>> STEP 3: GENERATING REVERSAL STRATEGIES...")
        generate_reversal_strategies()
        print("-" * 50)

    if run_step_4:
        print("\n>>> STEP 4: RUNNING BACKTEST...")
        print(f"INFO: EOD exit is {config.get('EOD_EXIT_TIME', '15:29')}. New trades will not be entered after {last_entry_time}.")
        base_data_dir = 'data'
        dates = [d for d in os.listdir(base_data_dir) if os.path.isdir(os.path.join(base_data_dir, d))]
        total_trades = 0
        for date_str in sorted(dates):
            print(f"\n--- Processing date: {date_str} ---")
            date_dir = os.path.join(base_data_dir, date_str)
            signals_file = os.path.join(date_dir, 'tradeview_utc_output.csv')
            calls_file = os.path.join(date_dir, 'call', 'call_out.csv')
            puts_file = os.path.join(date_dir, 'put', 'put_out.csv')

            if not all(os.path.exists(f) for f in [signals_file, calls_file, puts_file]):
                print(f"  [SKIP] Skipping {date_str}, missing one or more data files.")
                continue

            signals_df = pd.read_csv(signals_file, parse_dates=['datetime'])
            calls_df = pd.read_csv(calls_file, parse_dates=['datetime'])
            puts_df = pd.read_csv(puts_file, parse_dates=['datetime'])

            original_signal_count = len(signals_df[(signals_df['Call'] == 1) | (signals_df['Put'] == 1)])
            signals_df = signals_df[signals_df['datetime'].dt.time < last_entry_time]
            filtered_signal_count = len(signals_df[(signals_df['Call'] == 1) | (signals_df['Put'] == 1)])
            
            if original_signal_count > filtered_signal_count:
                print(f"  [FILTER] Ignored {original_signal_count - filtered_signal_count} signals occurring after {last_entry_time}.")

            daily_trades_list = run_backtest(signals_df, calls_df, puts_df, date_str, config)
            
            if daily_trades_list:
                daily_trades_df = pd.DataFrame(daily_trades_list)
                output_path = os.path.join(date_dir, "backtest_results.csv")
                daily_trades_df.to_csv(output_path, index=False)
                print(f"  [SUCCESS] Found {len(daily_trades_df)} trades. Results saved to {output_path}")
                total_trades += len(daily_trades_df)
            else:
                print(f"  [INFO] No trades were executed for {date_str}.")

        print("-" * 50)
        print(f"\nBacktest complete. A total of {total_trades} trades were found across all dates.")
        print("-" * 50)

    if run_step_5:
        print("\n>>> STEP 5: GENERATING FINAL ANALYTICS REPORT...")
        generate_final_analytics_report()
        print("-" * 50)

    print("\n--- Trading Application Pipeline Finished ---")

if __name__ == "__main__":
    main()