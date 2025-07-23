# app.py (Final Corrected Version)

from tools.run_cpr_filter import run_cpr_filter
from tools.run_cpr_filter_wide_band import run_cpr_filter_wide_band
from run_analytics import run_analysis
from tools.clean_data_dir import clean_generated_files
from strategies import (
    generate_continuation_strategies,
    generate_reversal_strategies,
    generate_reversal_strategies_v2
)
from option_strategies import (
    generate_continuation_strategies_options,
    generate_reversal_strategies_options,
    generate_reversal_strategies_v2_options
)
from option_tools import execute_option_trades, execute_index_trades, run_option_analysis, run_option_backtest, run_combined_option_backtest
from run_process_data import run_process_data
import yaml
import pandas as pd
import os
import traceback
from tabulate import tabulate

# --- Step Controllers ---
# Control which steps of the backtesting pipeline to execute
run_cleanup = True          # Step 0: Clean generated files from previous runs
run_step_1 = True          # Step 1: Process raw data and generate indicators
run_step_2 = False          # Step 2: Generate continuation signals for index
run_step_3 = True          # Step 3: Generate first reversal signals for index
run_step_4 = False        # Step 4: Generate second reversal signals for index
run_step_5 = True          # Step 5: Apply CPR filter to index signals for Index
run_step_6 = True          # Step 6: Execute trades on index signals (raw) for Index
run_step_7 = True          # Step 7: Execute trades on CPR-filtered index signals for Index
run_step_8 = True           # Step 8: Process call/put option data (signals & backtest) for Option
run_step_9 = True          # Step 9: Process put option data (now combined with step 9) for Option
run_step_10 = True          # Step 10: Execute option trades (call & put) for Option
run_step_11 = True  # Step 11: Generate comprehensive analytics reports

def load_config():
    """Load configuration from config.yaml"""
    try:
        with open('config.yaml', 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Error loading config.yaml: {e}")
        return None

def main():
    """
    Main function to run the complete backtesting pipeline.
    """
    config = load_config()
    if not config:
        print("Error: Could not load configuration. Exiting.")
        return

    data_root = './data'
    if not os.path.exists(data_root):
        print(f"Error: Data directory '{data_root}' not found.")
        return

    dates = sorted([d for d in os.listdir(data_root) if os.path.isdir(os.path.join(data_root, d))])

    if not dates:
        print("No date directories (DDMM) found in ./data folder.")
        return

    print(f"Found data for dates: {dates}")
    print(f"EOD exit time: {config['EOD_EXIT_TIME']}")
    print(f"Last entry time: {config['LAST_ENTRY_TIME']}")
    print("Trade execution parameters loaded from option_tools/trade_config.yaml")

    if run_cleanup:
        print("\n--- Running Step 0: Cleanup ---")
        clean_generated_files()
        print("Cleanup finished.\n")

    if run_step_1:
        print("\n--- Running Step 1: Process Raw Data ---")
        run_process_data()
        print("Step 1 finished.\n")

    if run_step_2:
        print("\n--- Running Step 2: Generate Continuation Signals ---")
        generate_continuation_strategies()
        print("Step 2 finished.\n")

    if run_step_3:
        print("\n--- Running Step 3: Generate First Reversal Signals ---")
        generate_reversal_strategies()
        print("Step 3 finished.\n")

    if run_step_4:
        print("\n--- Running Step 4: Generate Second Reversal Signals ---")
        generate_reversal_strategies_v2()
        print("Step 4 finished.\n")


    if run_step_5:
        print("\n--- Running Step 5: Run CPR Filter ---")
        for date in dates:
            print(f"\n--- Processing Date: {date} ---")
            try:
                price_data_file = f"./data/{date}/tradeview_utc.csv"
                if not os.path.exists(price_data_file):
                    print(f"  - Skipping {date}, missing price data file.")
                    continue

                price_df = pd.read_csv(price_data_file, encoding='utf-8-sig')
                daily_tc = price_df['Daily TC'].iloc[0]
                daily_bc = price_df['Daily BC'].iloc[0]
                cpr_width = daily_tc - daily_bc if pd.notna(daily_tc) and pd.notna(daily_bc) else 0
                filter_func = run_cpr_filter_wide_band if cpr_width > 50 else run_cpr_filter
                print(f"  Using {'wide' if cpr_width > 50 else 'standard'} band CPR filter (CPR width: {cpr_width:.2f})")

                # --- Process Reversal Signals ---
                rev_signals_file = f"./data/{date}/tradeview_rev_output.csv"
                if os.path.exists(rev_signals_file):
                    rev_signals_df = pd.read_csv(rev_signals_file, encoding='utf-8-sig')
                    
                    # Dynamically create the trade type map based on existing columns
                    trade_type_map_rev = {}
                    if 'Call' in rev_signals_df.columns: trade_type_map_rev['Call'] = 'Call'
                    if 'Put' in rev_signals_df.columns: trade_type_map_rev['Put'] = 'Put'
                    if 'Call_v2' in rev_signals_df.columns: trade_type_map_rev['Call_v2'] = 'Call'
                    if 'Put_v2' in rev_signals_df.columns: trade_type_map_rev['Put_v2'] = 'Put'

                    if trade_type_map_rev:
                        print(f"  - Applying CPR filter to reversal signals: {list(trade_type_map_rev.keys())}")
                        rev_signals_df_filtered = filter_func(price_df.copy(), rev_signals_df, trade_type_map_rev)
                        rev_signals_df_filtered.to_csv(rev_signals_file, index=False)
                    else:
                        print("  - No reversal signal columns found to filter.")
                else:
                    print(f"  - Skipping reversal signals, file not found.")

                # --- Process Continuation Signals ---
                cont_signals_file = f"./data/{date}/tradeview_cont_output.csv"
                if os.path.exists(cont_signals_file):
                    cont_signals_df = pd.read_csv(cont_signals_file, encoding='utf-8-sig')
                    
                    # Dynamically create the trade type map
                    trade_type_map_cont = {}
                    if 'Call' in cont_signals_df.columns: trade_type_map_cont['Call'] = 'Call'
                    if 'Put' in cont_signals_df.columns: trade_type_map_cont['Put'] = 'Put'

                    if trade_type_map_cont:
                        print(f"  - Applying CPR filter to continuation signals: {list(trade_type_map_cont.keys())}")
                        cont_signals_df_filtered = filter_func(price_df.copy(), cont_signals_df, trade_type_map_cont)
                        cont_signals_df_filtered.to_csv(cont_signals_file, index=False)
                    else:
                        print("  - No continuation signal columns found to filter.")
                else:
                    print(f"  - Skipping continuation signals, file not found.")

            except Exception as e:
                print(f"  ✗ ERROR processing {date} in Step 5: {str(e)}")
                traceback.print_exc()
        print("\nStep 5 finished.\n")

    if run_step_6:
        print("\n--- Running Step 6: Execute Trades ---")
        for date in dates:
            trades_dir = f"./data/{date}/trades"
            try:
                calls_file = f"./data/{date}/call/call_out.csv"
                puts_file = f"./data/{date}/put/put_out.csv"

                if not all(os.path.exists(f) for f in [calls_file, puts_file]):
                    print(f"  - Skipping {date}, missing call/put data files.")
                    continue
                
                calls_df = pd.read_csv(calls_file, encoding='utf-8-sig')
                puts_df = pd.read_csv(puts_file, encoding='utf-8-sig')

                # --- Execute Reversal Trades ---
                rev_signals_file = f"./data/{date}/tradeview_rev_output.csv"
                if os.path.exists(rev_signals_file):
                    rev_signals_df = pd.read_csv(rev_signals_file, encoding='utf-8-sig')
                    if 'Call' in rev_signals_df.columns:
                        execute_index_trades(rev_signals_df.copy(), calls_df.copy(), 'Call', 'Call', config, trades_dir, 'rev_v1_trades.csv')
                    if 'Put' in rev_signals_df.columns:
                        execute_index_trades(rev_signals_df.copy(), puts_df.copy(), 'Put', 'Put', config, trades_dir, 'rev_v1_trades.csv')
                    if 'Call_v2' in rev_signals_df.columns:
                        execute_index_trades(rev_signals_df.copy(), calls_df.copy(), 'Call_v2', 'Call', config, trades_dir, 'rev_v2_trades.csv')
                    if 'Put_v2' in rev_signals_df.columns:
                        execute_index_trades(rev_signals_df.copy(), puts_df.copy(), 'Put_v2', 'Put', config, trades_dir, 'rev_v2_trades.csv')

                # --- Execute Continuation Trades ---
                cont_signals_file = f"./data/{date}/tradeview_cont_output.csv"
                if os.path.exists(cont_signals_file):
                    cont_signals_df = pd.read_csv(cont_signals_file, encoding='utf-8-sig')
                    if 'Call' in cont_signals_df.columns:
                        execute_index_trades(cont_signals_df.copy(), calls_df.copy(), 'Call', 'Call', config, trades_dir, 'cont_trades.csv')
                    if 'Put' in cont_signals_df.columns:
                        execute_index_trades(cont_signals_df.copy(), puts_df.copy(), 'Put', 'Put', config, trades_dir, 'cont_trades.csv')

            except Exception as e:
                print(f"  ✗ ERROR processing {date} in Step 6: {str(e)}")
                traceback.print_exc()
        print("\nStep 6 finished.\n")

    if run_step_7:
        print("\n--- Running Step 7: Execute CPR-Filtered Trades ---")
        for date in dates:
            trades_dir_cpr = f"./data/{date}/trades_crp"
            try:
                calls_file = f"./data/{date}/call/call_out.csv"
                puts_file = f"./data/{date}/put/put_out.csv"

                if not all(os.path.exists(f) for f in [calls_file, puts_file]):
                    print(f"  - Skipping {date}, missing call/put data files.")
                    continue

                calls_df = pd.read_csv(calls_file, encoding='utf-8-sig')
                puts_df = pd.read_csv(puts_file, encoding='utf-8-sig')

                # --- Execute Reversal CPR Trades ---
                rev_signals_file = f"./data/{date}/tradeview_rev_output.csv"
                if os.path.exists(rev_signals_file):
                    rev_signals_df = pd.read_csv(rev_signals_file, encoding='utf-8-sig')
                    if 'Call_crp' in rev_signals_df.columns:
                        execute_index_trades(rev_signals_df.copy(), calls_df.copy(), 'Call_crp', 'Call', config, trades_dir_cpr, 'rev_v1_trades.csv')
                    if 'Put_crp' in rev_signals_df.columns:
                        execute_index_trades(rev_signals_df.copy(), puts_df.copy(), 'Put_crp', 'Put', config, trades_dir_cpr, 'rev_v1_trades.csv')
                    # No v2 for CPR filtered for now
                
                # --- Execute Continuation CPR Trades ---
                cont_signals_file = f"./data/{date}/tradeview_cont_output.csv"
                if os.path.exists(cont_signals_file):
                    cont_signals_df = pd.read_csv(cont_signals_file, encoding='utf-8-sig')
                    if 'Call_crp' in cont_signals_df.columns:
                        execute_index_trades(cont_signals_df.copy(), calls_df.copy(), 'Call_crp', 'Call', config, trades_dir_cpr, 'cont_trades.csv')
                    if 'Put_crp' in cont_signals_df.columns:
                        execute_index_trades(cont_signals_df.copy(), puts_df.copy(), 'Put_crp', 'Put', config, trades_dir_cpr, 'cont_trades.csv')

            except Exception as e:
                print(f"  ✗ ERROR processing {date} in Step 7: {str(e)}")
                traceback.print_exc()
        print("\nStep 7 finished.\n")

    if run_step_8:
        print("\n--- Running Step 8: Process Call Data (Signal Generation & Backtest) ---")
        generate_continuation_strategies_options(call_input_filename='call/call_out.csv', call_output_filename='call/call_cont_out.csv', put_input_filename='put/put_out.csv', put_output_filename='put/put_cont_out.csv')
        generate_reversal_strategies_options(call_input_filename='call/call_out.csv', call_output_filename='call/call_rev_out.csv', put_input_filename='put/put_out.csv', put_output_filename='put/put_rev_out.csv')
        generate_reversal_strategies_v2_options(call_input_filename='call/call_out.csv', call_output_filename='call/call_rev_out.csv', put_input_filename='put/put_out.csv', put_output_filename='put/put_rev_out.csv')
        
        for date in dates:
            try:
                cont_signals_file = f"./data/{date}/call/call_cont_out.csv"
                rev_signals_file = f"./data/{date}/call/call_rev_out.csv"
                calls_file = f"./data/{date}/call/call_out.csv"
                puts_file = f"./data/{date}/put/put_out.csv"
                
                required_files = [calls_file, puts_file, cont_signals_file, rev_signals_file]
                if not all(os.path.exists(f) for f in required_files):
                    print(f"  - Skipping {date} in Step 9, missing one or more required files.")
                    continue

                print(f"\n--- Backtesting Call Data for Date: {date} ---")
                calls_df = pd.read_csv(calls_file, encoding='utf-8-sig')
                calls_df['datetime'] = pd.to_datetime(calls_df['datetime'])
                puts_df = pd.read_csv(puts_file, encoding='utf-8-sig')
                puts_df['datetime'] = pd.to_datetime(puts_df['datetime'])
                cont_signals_df = pd.read_csv(cont_signals_file, encoding='utf-8-sig')
                cont_signals_df['datetime'] = pd.to_datetime(cont_signals_df['datetime'])
                rev_signals_df = pd.read_csv(rev_signals_file, encoding='utf-8-sig')
                rev_signals_df['datetime'] = pd.to_datetime(rev_signals_df['datetime'])

                # Use option-specific backtesting for call options
                trades_cont = run_option_backtest(cont_signals_df.copy(), calls_df.copy(), date, config, 'Continuation Strategy', 'Call', 'Call')
                trades_rev = run_option_backtest(rev_signals_df.copy(), calls_df.copy(), date, config, 'Reversal Strategy', 'Call', 'Call')
                trades_rev_v2 = run_option_backtest(rev_signals_df.copy(), calls_df.copy(), date, config, 'Reversal Strategy v2', 'Call', 'Call_v2')
                
                backtest_dir = f"./data/{date}/call/backtest"
                os.makedirs(backtest_dir, exist_ok=True)

                if trades_cont: pd.DataFrame(trades_cont).to_csv(f"{backtest_dir}/backtest_results_cont.csv", index=False)
                if trades_rev: pd.DataFrame(trades_rev).to_csv(f"{backtest_dir}/backtest_results_rev.csv", index=False)
                if trades_rev_v2: pd.DataFrame(trades_rev_v2).to_csv(f"{backtest_dir}/backtest_results_rev_v2.csv", index=False)

            except Exception as e:
                print(f"  ✗ ERROR processing {date} in Step 9: {str(e)}")
                traceback.print_exc()
        print("Step 8 finished.\n")

    if run_step_9:
        print("\n--- Running Step 9: Process Put Data (Signal Generation & Backtest) ---")
        # Note: Put data processing is now handled together with call data in step 9
        # using the option_strategies which process both call and put files appropriately
        print("   Put data processing is handled together with call data in step 9 using option strategies")
        
        for date in dates:
            try:
                cont_signals_file = f"./data/{date}/put/put_cont_out.csv"
                rev_signals_file = f"./data/{date}/put/put_rev_out.csv"
                calls_file = f"./data/{date}/call/call_out.csv"
                puts_file = f"./data/{date}/put/put_out.csv"
                
                required_files = [calls_file, puts_file, cont_signals_file, rev_signals_file]
                if not all(os.path.exists(f) for f in required_files):
                    print(f"  - Skipping {date} in Step 10, missing one or more required files.")
                    continue

                print(f"\n--- Backtesting Put Data for Date: {date} ---")
                calls_df = pd.read_csv(calls_file, encoding='utf-8-sig')
                calls_df['datetime'] = pd.to_datetime(calls_df['datetime'])
                puts_df = pd.read_csv(puts_file, encoding='utf-8-sig')
                puts_df['datetime'] = pd.to_datetime(puts_df['datetime'])
                cont_signals_df = pd.read_csv(cont_signals_file, encoding='utf-8-sig')
                cont_signals_df['datetime'] = pd.to_datetime(cont_signals_df['datetime'])
                rev_signals_df = pd.read_csv(rev_signals_file, encoding='utf-8-sig')
                rev_signals_df['datetime'] = pd.to_datetime(rev_signals_df['datetime'])

                # Use option-specific backtesting for put options
                trades_cont = run_option_backtest(cont_signals_df.copy(), puts_df.copy(), date, config, 'Continuation Strategy', 'Put', 'Put')
                trades_rev = run_option_backtest(rev_signals_df.copy(), puts_df.copy(), date, config, 'Reversal Strategy', 'Put', 'Put')
                trades_rev_v2 = run_option_backtest(rev_signals_df.copy(), puts_df.copy(), date, config, 'Reversal Strategy v2', 'Put', 'Put_v2')
                
                backtest_dir = f"./data/{date}/put/backtest"
                os.makedirs(backtest_dir, exist_ok=True)

                if trades_cont: pd.DataFrame(trades_cont).to_csv(f"{backtest_dir}/backtest_results_cont.csv", index=False)
                if trades_rev: pd.DataFrame(trades_rev).to_csv(f"{backtest_dir}/backtest_results_rev.csv", index=False)
                if trades_rev_v2: pd.DataFrame(trades_rev_v2).to_csv(f"{backtest_dir}/backtest_results_rev_v2.csv", index=False)

            except Exception as e:
                print(f"  ✗ ERROR processing {date} in Step 10: {str(e)}")
                traceback.print_exc()
        print("Step 9 finished.\n")

    if run_step_10:
        print("\n--- Running Step 10: Execute Trades for Call/Put Data ---")
        for date in dates:
            # Execute for Call data - Create 3 separate files
            call_trades_dir = f"./data/{date}/call/trades"
            try:
                cont_signals_file = f"./data/{date}/call/call_cont_out.csv"
                rev_signals_file = f"./data/{date}/call/call_rev_out.csv"
                calls_file = f"./data/{date}/call/call_out.csv"
                puts_file = f"./data/{date}/put/put_out.csv"

                required_files = [calls_file, puts_file, cont_signals_file, rev_signals_file]
                if not all(os.path.exists(f) for f in required_files):
                    print(f"  - Skipping Call trades for {date}, missing files.")
                else:
                    calls_df = pd.read_csv(calls_file, encoding='utf-8-sig')
                    puts_df = pd.read_csv(puts_file, encoding='utf-8-sig')
                    cont_signals_df = pd.read_csv(cont_signals_file, encoding='utf-8-sig')
                    rev_signals_df = pd.read_csv(rev_signals_file, encoding='utf-8-sig')
                    
                    # Create 3 separate call trade files
                    execute_option_trades(cont_signals_df.copy(), calls_df.copy(), 'Call', 'Call', config, call_trades_dir, 'call_cont_trades.csv')
                    execute_option_trades(rev_signals_df.copy(), calls_df.copy(), 'Call', 'Call', config, call_trades_dir, 'call_rev_v1_trades.csv')
                    execute_option_trades(rev_signals_df.copy(), calls_df.copy(), 'Call_v2', 'Call', config, call_trades_dir, 'call_rev_v2_trades.csv')
            except Exception as e:
                print(f"  ✗ ERROR processing Call trades for {date} in Step 11: {str(e)}")
                traceback.print_exc()

            # Execute for Put data - Create 3 separate files
            put_trades_dir = f"./data/{date}/put/trades"
            try:
                cont_signals_file = f"./data/{date}/put/put_cont_out.csv"
                rev_signals_file = f"./data/{date}/put/put_rev_out.csv"
                calls_file = f"./data/{date}/call/call_out.csv"
                puts_file = f"./data/{date}/put/put_out.csv"

                required_files = [calls_file, puts_file, cont_signals_file, rev_signals_file]
                if not all(os.path.exists(f) for f in required_files):
                    print(f"  - Skipping Put trades for {date}, missing files.")
                else:
                    calls_df = pd.read_csv(calls_file, encoding='utf-8-sig')
                    puts_df = pd.read_csv(puts_file, encoding='utf-8-sig')
                    cont_signals_df = pd.read_csv(cont_signals_file, encoding='utf-8-sig')
                    rev_signals_df = pd.read_csv(rev_signals_file, encoding='utf-8-sig')

                    # Create 3 separate put trade files
                    execute_option_trades(cont_signals_df.copy(), puts_df.copy(), 'Put', 'Put', config, put_trades_dir, 'put_cont_trades.csv')
                    execute_option_trades(rev_signals_df.copy(), puts_df.copy(), 'Put', 'Put', config, put_trades_dir, 'put_rev_v1_trades.csv')
                    execute_option_trades(rev_signals_df.copy(), puts_df.copy(), 'Put_v2', 'Put', config, put_trades_dir, 'put_rev_v2_trades.csv')
            except Exception as e:
                print(f"  ✗ ERROR processing Put trades for {date} in Step 11: {str(e)}")
                traceback.print_exc()
        print("\nStep 10 finished.\n")


    if run_step_11:
        print("\n--- Running Step 11: Final Analytics Report ---")
        run_analysis()
        print("Step 11 finished.\n")

    print("All selected steps completed successfully!")

if __name__ == "__main__":
    main()
