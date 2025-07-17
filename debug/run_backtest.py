import pandas as pd
import yaml
import os
from option_tools.option_trade_executor import execute_option_trades

def run_backtest(date_folder, signals_file, call_prices_file, put_prices_file, output_dir, output_filename):
    """
    Runs a backtest for a given date, processing both call and put signals.
    """
    print(f"--- Starting Backtest for {date_folder} ---")

    # Load main configuration
    try:
        with open('config.yaml', 'r') as file:
            config = yaml.safe_load(file)
    except Exception as e:
        print(f"Error loading config.yaml: {e}")
        # Provide a default config if main one is missing
        config = {'LAST_ENTRY_TIME': '15:00'}

    # Load data
    try:
        signals_df = pd.read_csv(signals_file)
        call_prices_df = pd.read_csv(call_prices_file)
        put_prices_df = pd.read_csv(put_prices_file)
    except FileNotFoundError as e:
        print(f"Error: Data file not found - {e}")
        return

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Clean previous output file if it exists
    output_path = os.path.join(output_dir, output_filename)
    if os.path.exists(output_path):
        os.remove(output_path)
        print(f"Removed existing trade file: {output_path}")

    # --- Execute Call Trades ---
    print("\n--- Processing Call Options ---")
    call_trades_df = execute_option_trades(
        signals_df=signals_df.copy(),
        prices_df=call_prices_df.copy(),
        signal_col='Call_crp',
        trade_type='CALL',
        config=config,
        output_dir=output_dir,
        output_filename=output_filename
    )

    # --- Execute Put Trades ---
    print("\n--- Processing Put Options ---")
    put_trades_df = execute_option_trades(
        signals_df=signals_df.copy(),
        prices_df=put_prices_df.copy(),
        signal_col='Put_v2',
        trade_type='PUT',
        config=config,
        output_dir=output_dir,
        output_filename=output_filename
    )

    # --- Analyze Results ---
    print("\n--- Backtest Analysis ---")
    if os.path.exists(output_path):
        all_trades_df = pd.read_csv(output_path)
        
        if not all_trades_df.empty:
            # Convert P/L columns to numeric for calculations
            all_trades_df['P/L'] = pd.to_numeric(all_trades_df['P/L'], errors='coerce')
            all_trades_df['P/L %'] = pd.to_numeric(all_trades_df['P/L %'].str.replace('%', ''), errors='coerce')

            total_pnl = all_trades_df['P/L'].sum()
            win_rate = (all_trades_df['P/L'] > 0).mean() * 100
            average_win_pct = all_trades_df[all_trades_df['P/L'] > 0]['P/L %'].mean()
            average_loss_pct = all_trades_df[all_trades_df['P/L'] <= 0]['P/L %'].mean()
            
            print(f"Total Trades: {len(all_trades_df)}")
            print(f"Total P/L: {total_pnl:.2f} points")
            print(f"Win Rate: {win_rate:.2f}%")
            print(f"Average Winning Trade: +{average_win_pct:.2f}%")
            print(f"Average Losing Trade: {average_loss_pct:.2f}%")
            
            print("\nExit Reasons Distribution:")
            print(all_trades_df['Exit Reason'].value_counts())
        else:
            print("No trades were executed.")
    else:
        print("No trade file was generated.")

    print(f"\n--- Backtest for {date_folder} Complete ---")
    print(f"Results saved to {output_path}")

if __name__ == '__main__':
    # Configuration for the specific backtest
    DATE_FOLDER = '1407'
    
    # Define file paths
    data_base_path = os.path.join('data', DATE_FOLDER)
    signals_file = os.path.join(data_base_path, 'tradeview_rev_output.csv')
    call_prices_file = os.path.join(data_base_path, 'call', 'call_out.csv')
    put_prices_file = os.path.join(data_base_path, 'put', 'put_out.csv')
    output_dir = os.path.join(data_base_path, 'trades_crp')
    output_filename = 'rev_v1_trades.csv'
    
    run_backtest(DATE_FOLDER, signals_file, call_prices_file, put_prices_file, output_dir, output_filename)

    print("\n--- How to Improve ---")
    print("1. Analyze the 'Exit Reasons' above. If too many trades hit 'SL Hit', consider adjusting 'sl_percent' in 'option_tools/trade_config.yaml'.")
    print("2. If 'Trailing SL' exits are leaving profit on the table, you could adjust 'atr_mult' to give more room.")
    print("3. If you have many small wins but miss large moves, review the 'trail_start_pct' and 'QUICK_TP_POINTS' to let trades run longer.")
    print("4. Experiment with one parameter at a time in 'option_tools/trade_config.yaml' and re-run this script to see the impact on P/L and Win Rate.")
