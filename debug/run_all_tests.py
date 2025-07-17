import pandas as pd
import yaml
from option_tools.option_trade_executor import execute_option_trades
import os

def run_single_test(date_str, trade_type, config):
    """Helper function to run a single trade test."""
    signal_col = trade_type
    
    print(f"--- Verifying Trade: {date_str} {trade_type} ---")
    
    try:
        # Construct paths based on trade type
        trade_folder = 'call' if trade_type == 'Call' else 'put'
        
        signals_df = pd.read_csv(f'data/{date_str}/{trade_folder}/trades/{trade_folder}_rev_v2_trades.csv')
        prices_df = pd.read_csv(f'data/{date_str}/{trade_folder}/{trade_folder}_out.csv')
        
        # Prepare DataFrames
        signals_df['datetime'] = pd.to_datetime(signals_df['Entry Time'])
        signals_df[signal_col] = 1 # Ensure signal column exists
        
        # Define output
        output_dir = 'temp_test_results'
        output_filename = f'test_results_{date_str}_{trade_type}.csv'
        
        # Clean up previous results
        output_path = os.path.join(output_dir, output_filename)
        if os.path.exists(output_path):
            os.remove(output_path)
            
        # Execute the trade logic
        results_df = execute_option_trades(
            signals_df,
            prices_df,
            signal_col,
            trade_type,
            config,
            output_dir,
            output_filename
        )
        
        # Print results
        if not results_df.empty:
            print("\n--- Results ---")
            # The execution happens on the candle AFTER the signal.
            # We need to find the executed trade that corresponds to our signal of interest.
            if date_str == '1107':
                trade_time = '09:52'
            elif date_str == '1407':
                trade_time = '10:31'
            elif date_str == '1507':
                trade_time = '10:29'
            
            target_signal_time_str = f"2025-07-{date_str[:2]} {trade_time}:00"
            target_signal_dt = pd.to_datetime(target_signal_time_str)

            # Find the first trade that was executed at or after the signal time.
            trade_result = results_df[results_df['Entry Time'] >= target_signal_dt]
            
            if not trade_result.empty:
                print(trade_result.iloc[[0]].to_string()) # Print only the first matching trade
            else:
                print(f"Could not find matching executed trade for signal at {target_signal_dt}")

        else:
            print("\nNo trades were executed.")
            
    except FileNotFoundError as e:
        print(f"Error loading data: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    
    print("-" * 40 + "\n")


# --- Main Execution ---
if __name__ == "__main__":
    # Load main config
    with open('config.yaml', 'r') as f:
        main_config = yaml.safe_load(f)
        
    # Define the key trades to test
    trades_to_test = [
        ('1107', 'Put'),
        ('1407', 'Put'),
        ('1507', 'Call')
    ]
    
    # Run all tests
    for date, trade_type in trades_to_test:
        run_single_test(date, trade_type, main_config)
