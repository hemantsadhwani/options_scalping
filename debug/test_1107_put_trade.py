import pandas as pd
import yaml
from option_tools.option_trade_executor import execute_option_trades
import os

# Load main config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# --- Data Loading for 11/07 PUT ---
date_str = '1107'
trade_type = 'Put'
signal_col = 'Put'

try:
    signals_df = pd.read_csv(f'data/{date_str}/put/trades/put_rev_v2_trades.csv')
    prices_df = pd.read_csv(f'data/{date_str}/put/put_out.csv')
    
    # The trade executor expects a 'datetime' column
    signals_df['datetime'] = pd.to_datetime(signals_df['Entry Time'])
    # The executor expects a signal column with 1s
    signals_df[signal_col] = 1

    # --- Run the Trade Execution ---
    output_dir = 'temp_test_results'
    output_filename = f'test_results_{date_str}_{trade_type}.csv'
    
    # Clean up previous test results if they exist
    if os.path.exists(os.path.join(output_dir, output_filename)):
        os.remove(os.path.join(output_dir, output_filename))

    print(f"--- Testing {trade_type} trade for {date_str} ---")
    
    results_df = execute_option_trades(
        signals_df,
        prices_df,
        signal_col,
        trade_type,
        config,
        output_dir,
        output_filename
    )

    # --- Print Results ---
    if not results_df.empty:
        print("\n--- Trade Execution Results ---")
        print(results_df.to_string())
    else:
        print("\nNo trades were executed.")

except FileNotFoundError as e:
    print(f"Error loading data for {date_str}: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
