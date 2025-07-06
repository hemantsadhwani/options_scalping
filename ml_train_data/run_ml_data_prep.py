# nifty_option_trading/run_ml_data_prep.py (Corrected)

import os
import pandas as pd
import glob
import numpy as np
from datetime import timedelta, time

def run_data_enrichment(data_dir, output_file):
    """
    Iterates through MMDD directories to create a single, enriched data file
    for machine learning, dropping rows with no valid target.
    """
    # Find all MMDD subdirectories
    mmdd_dirs = glob.glob(os.path.join(data_dir, '*/'))
    if not mmdd_dirs:
        print(f"Warning: No data directories found in '{data_dir}'.")
        print(f"Please ensure your structure is: {data_dir}/MMDD/your_files.csv")
        return

    all_enriched_dfs = []
    print("--- Starting Data Enrichment Process ---")

    # Sort directories to process them in a consistent order
    for dir_path in sorted(mmdd_dirs):
        dir_name = os.path.basename(os.path.normpath(dir_path))
        print(f"\nProcessing Directory: {dir_name}")

        # Define file paths for the current directory
        backtest_file = os.path.join(dir_path, 'backtest_results.csv')
        market_data_file = os.path.join(dir_path, 'tradeview_utc_output.csv')
        close_file = os.path.join(dir_path, 'close.txt')

        # Check that all three required files exist
        if not all(os.path.exists(f) for f in [backtest_file, market_data_file, close_file]):
            print(f"  - Warning: Skipping. Missing one or more required files in this directory.")
            continue

        try:
            # 1. Read previous day's close value
            with open(close_file, 'r') as f:
                line = f.readline()
                prev_day_close = float(line.split(':', 1)[1].strip())
            print(f"  - Read previous day's close value: {prev_day_close}")

            # 2. Load market data to find the 9:15 open
            market_data_df = pd.read_csv(market_data_file)
            market_data_df['datetime'] = pd.to_datetime(market_data_df['datetime'])

            # --- Market Open Type Logic ---
            open_time = time(9, 15)
            open_row = market_data_df[market_data_df['datetime'].dt.time == open_time]

            if open_row.empty:
                print(f"  - Warning: No 9:15 AM data found in {dir_name}. Skipping this directory.")
                continue

            open_at_915 = open_row['open'].iloc[0]
            price_diff = open_at_915 - prev_day_close

            if price_diff > 60:
                mkt_open_type = 'gap_up'
            elif price_diff < -60:
                mkt_open_type = 'gap_down'
            else:
                mkt_open_type = 'sideways'
            print(f"  - Market open type determined as: {mkt_open_type}")

            # 3. Load backtest data
            backtest_df = pd.read_csv(backtest_file)
            if backtest_df.empty:
                print("  - Warning: 'backtest_results.csv' is empty. Skipping.")
                continue
            
            # --- ENCODE THE TARGET VARIABLE ---
            if 'exit_reason' in backtest_df.columns:
                print("  - Encoding 'exit_reason' into 'target' column.")
                conditions = [
                    backtest_df['exit_reason'].str.contains("Target Profit", na=False),
                    backtest_df['exit_reason'].str.contains("Stop Loss", na=False)
                ]
                choices = [1, 0]
                backtest_df['target'] = np.select(conditions, choices, default=np.nan)
                
                # Drop the original 'exit_reason' column
                backtest_df = backtest_df.drop(columns=['exit_reason'])
            else:
                print("  - Warning: 'exit_reason' column not found in backtest_results.csv.")
                continue # Skip if we can't create a target

            # 4. Perform N-1 minute merge
            backtest_df['entry_time'] = pd.to_datetime(backtest_df['entry_time'])
            backtest_df['condition_time'] = backtest_df['entry_time'] - timedelta(minutes=1)
            
            enriched_df = pd.merge(backtest_df, market_data_df, left_on='condition_time', right_on='datetime', how='left')
            
            # 5. Add new features to every row for that day
            enriched_df['prev_day_close'] = prev_day_close
            enriched_df['mkt_open_type'] = mkt_open_type
            enriched_df['source_dir'] = dir_name
            
            all_enriched_dfs.append(enriched_df)
            print(f"  - Successfully processed and enriched {len(enriched_df)} trades.")

        except Exception as e:
            print(f"  - Error: Failed to process files in {dir_name}. Reason: {e}")

    if not all_enriched_dfs:
        print("\nNo data was processed. No output file created.")
        return

    # 6. Combine all dataframes
    final_df = pd.concat(all_enriched_dfs, ignore_index=True)
    
    # *** CHANGE IS HERE: Drop rows where 'target' is blank/NaN ***
    rows_before_dropping = len(final_df)
    final_df.dropna(subset=['target'], inplace=True)
    rows_after_dropping = len(final_df)
    
    if rows_before_dropping > rows_after_dropping:
        print(f"\nDropped {rows_before_dropping - rows_after_dropping} rows with no valid target (e.g., 'End of Day' exits).")
    
    # Also ensure target is an integer
    if 'target' in final_df.columns:
        final_df['target'] = final_df['target'].astype(int)
    
    # Clean up helper columns from the merge
    final_df = final_df.drop(columns=['condition_time', 'datetime'], errors='ignore')
    
    # Define the list of columns to drop as requested
    columns_to_drop = [
        'Call', 'Put', 'Call Comments', 'Put Comments', 'source_dir', 
        'entry_price', 'exit_price', 'stop_loss_price', 'take_profit_price', 
        'pnl', 'exit_time', 'date'
    ]
    
    # Drop the specified columns from the final dataframe
    final_df = final_df.drop(columns=columns_to_drop, errors='ignore')
    
    print(f"\nDropped specified columns. Final columns are: {final_df.columns.to_list()}")
    
    # 7. Save the final, cleaned dataframe
    final_df.to_csv(output_file, index=False)
    print("\n--- Enrichment Complete ---")
    print(f"Successfully created '{output_file}'")
    print(f"Final data shape: {final_df.shape}")
    print(f"Total rows from all directories: {len(final_df)}")


if __name__ == '__main__':
    # --- Define Project and Data Directories ---
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIRECTORY = os.path.join(PROJECT_ROOT, 'data') 
    
    # --- Define the NEW Output Directory and File Path ---
    OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'ml_train_data')
    OUTPUT_CSV_FILE = os.path.join(OUTPUT_DIR, 'ml_data_enriched.csv')
    
    # --- Create the output directory if it doesn't exist ---
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # --- Run the main function ---
    run_data_enrichment(DATA_DIRECTORY, OUTPUT_CSV_FILE)