import os
import pandas as pd
import glob
from datetime import timedelta

def run_data_enrichment(data_dir, output_file):
    """
    Iterates through MMDD directories to create a single, enriched data file.
    For each directory, it:
    1. Reads the daily close value from 'close.txt'.
    2. Merges 'backtest_results.csv' with the N-1 minute data from 'tradeview_utc_output.csv'.
    3. Adds the daily close value as a new column.
    4. Combines all data and saves it to the specified output file.
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
            # 1. Read daily close value
            with open(close_file, 'r') as f:
                line = f.readline()
                day_close_value = float(line.split(':', 1)[1].strip())
            print(f"  - Read daily close value: {day_close_value}")

            # 2. Load trade and market data
            backtest_df = pd.read_csv(backtest_file)
            if backtest_df.empty:
                print("  - Warning: 'backtest_results.csv' is empty. Skipping.")
                continue
            
            market_data_df = pd.read_csv(market_data_file)

            # 3. Perform N-1 minute merge
            backtest_df['entry_time'] = pd.to_datetime(backtest_df['entry_time'])
            market_data_df['datetime'] = pd.to_datetime(market_data_df['datetime'])
            backtest_df['condition_time'] = backtest_df['entry_time'] - timedelta(minutes=1)
            
            enriched_df = pd.merge(backtest_df, market_data_df, left_on='condition_time', right_on='datetime', how='left')
            
            # 4. Add new features
            enriched_df['day_close_value'] = day_close_value
            enriched_df['source_dir'] = dir_name
            
            all_enriched_dfs.append(enriched_df)
            print(f"  - Successfully processed and enriched {len(enriched_df)} trades.")

        except Exception as e:
            print(f"  - Error: Failed to process files in {dir_name}. Reason: {e}")

    if not all_enriched_dfs:
        print("\nNo data was processed. No output file created.")
        return

    # 5. Combine all dataframes and save
    final_df = pd.concat(all_enriched_dfs, ignore_index=True)
    
    # Clean up helper columns from the merge
    final_df = final_df.drop(columns=['condition_time', 'datetime'], errors='ignore')
    
    final_df.to_csv(output_file, index=False)
    print("\n--- Enrichment Complete ---")
    print(f"Successfully created '{output_file}'")
    print(f"Final data shape: {final_df.shape}")
    print(f"Total rows from all directories: {len(final_df)}")


if __name__ == '__main__':
    # Define the relative path to the data directory.
    # This assumes the script is in 'ml_train_data' and the data is in 'data'.
    DATA_DIRECTORY = '../data' 
    
    # Define the name of the output file.
    # It will be saved in the same directory as the script.
    OUTPUT_CSV_FILE = 'ml_data_enriched.csv'

    # Run the main data enrichment function
    run_data_enrichment(DATA_DIRECTORY, OUTPUT_CSV_FILE)