# app.py (Final Corrected Version)

from tools.run_s1r1_crp_filter import filter_signals_in_cpr_band_improved
from tools.run_cpr_filter import run_cpr_filter
from tools.trade_executor import execute_trades
from tools.run_analytics import run_analysis
from tools.clean_data_dir import clean_generated_files
from strategies import (
    generate_continuation_strategies,
    generate_reversal_strategies,
    generate_reversal_strategies_v2
)
from run_process_data import run_process_data
from backtesting.run_backtesting import run_backtest
import yaml
import pandas as pd
import os
import traceback

# --- Step Controllers ---
run_cleanup = True      # Step 0: Clean up generated files
run_step_1 = True       # Step 1: Process raw data
run_step_2 = True       # Step 2: Generate continuation signals
run_step_3 = True       # Step 3: Generate first reversal signals
run_step_3_2 = True     # Step 3.2: Generate second reversal signals
run_step_temp = True    # Step Temp: Filter CPR band signals
run_step_4 = True        # Step 4: Run backtest on raw signals
run_step_5 = True        # Step 5: Run CPR filter on raw signals
run_step_6 = True        # Step 6: Run backtest on CPR-filtered signals
run_step_7 = True        # Step 7: Execute trades on raw signals
run_step_8 = True        # Step 8: Execute trades on CPR-filtered signals
run_final_analytics = True # Step 9: Generate final analytics report

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
    print(f"Using strategy type: {config['STRATEGY_TYPE']}")
    print(f"EOD exit time: {config['EOD_EXIT_TIME']}")
    print(f"Last entry time: {config['LAST_ENTRY_TIME']}")

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

    if run_step_3_2:
        print("\n--- Running Step 3.2: Generate Second Reversal Signals ---")
        generate_reversal_strategies_v2()
        print("Step 3.2 finished.\n")

    if run_step_temp:
        print("\n--- Running Step: Filter CPR Band Signals ---")
        for date in dates:
            date_dir_path = f"./data/{date}"
            filter_signals_in_cpr_band_improved(date_dir_path)
        print("CPR Filtering finished.\n")

    if run_step_4:
        print("\n--- Running Step 4: Run Backtest ---")
        
        for date in dates:
            cont_signals_file = f"./data/{date}/tradeview_cont_output.csv"
            rev_signals_file = f"./data/{date}/tradeview_rev_output.csv"
            calls_file = f"./data/{date}/call/call_out.csv"
            puts_file = f"./data/{date}/put/put_out.csv"
            
            required_files = [calls_file, puts_file, cont_signals_file, rev_signals_file]
            if all(os.path.exists(f) for f in required_files):
                print(f"\n--- Processing Date: {date} ---")
                try:
                    # Read all required CSVs using the proven robust method
                    calls_df = pd.read_csv(calls_file, encoding='utf-8-sig')
                    calls_df['datetime'] = pd.to_datetime(calls_df['datetime'])
                    
                    puts_df = pd.read_csv(puts_file, encoding='utf-8-sig')
                    puts_df['datetime'] = pd.to_datetime(puts_df['datetime'])
                    
                    cont_signals_df = pd.read_csv(cont_signals_file, encoding='utf-8-sig')
                    cont_signals_df['datetime'] = pd.to_datetime(cont_signals_df['datetime'])
                    
                    rev_signals_df = pd.read_csv(rev_signals_file, encoding='utf-8-sig')
                    rev_signals_df['datetime'] = pd.to_datetime(rev_signals_df['datetime'])

                    # --- Run all three backtests ---
                    
                    # 1. Continuation Strategy
                    trades_cont = run_backtest(cont_signals_df, calls_df.copy(), puts_df.copy(), date, config, strategy_name='Continuation Strategy')
                    
                    # 2. Reversal Strategy
                    trades_rev = run_backtest(rev_signals_df.copy(), calls_df.copy(), puts_df.copy(), date, config, strategy_name='Reversal Strategy')
                    
                    # 3. Reversal Strategy v2
                    rev_signals_df_v2 = rev_signals_df.copy()
                    trades_rev_v2 = run_backtest(rev_signals_df_v2, calls_df.copy(), puts_df.copy(), date, config, strategy_name='Reversal Strategy v2', call_col='Call_v2', put_col='Put_v2')
                    
                    # --- Save all results ---

                    backtest_dir = f"./data/{date}/backtest"
                    os.makedirs(backtest_dir, exist_ok=True)

                    if trades_cont:
                        cont_results_file = f"{backtest_dir}/backtest_results_cont.csv"
                        pd.DataFrame(trades_cont).to_csv(cont_results_file, index=False)
                        print(f"  ✓ Saved {len(trades_cont)} continuation trades to {cont_results_file}")

                    if trades_rev:
                        rev_results_file = f"{backtest_dir}/backtest_results_rev.csv"
                        pd.DataFrame(trades_rev).to_csv(rev_results_file, index=False)
                        print(f"  ✓ Saved {len(trades_rev)} reversal trades to {rev_results_file}")

                    if trades_rev_v2:
                        rev_v2_results_file = f"{backtest_dir}/backtest_results_rev_v2.csv"
                        pd.DataFrame(trades_rev_v2).to_csv(rev_v2_results_file, index=False)
                        print(f"  ✓ Saved {len(trades_rev_v2)} reversal v2 trades to {rev_v2_results_file}")                   
                    
                    if not (trades_cont or trades_rev or trades_rev_v2):
                        print(f"  - No trades found for {date}")
                
                except Exception as e:
                    print(f"  ✗ ERROR processing {date}: {str(e)}")
                    traceback.print_exc()
            else:
                print(f"  - Skipping {date}, missing one or more required files.")
        
        print("\nStep 4 finished.\n")

    if run_step_5:
        print("\n--- Running Step 5: Run CPR Filter ---")
        for date in dates:
            print(f"\n--- Processing Date: {date} ---")
            try:
                price_data_file = f"./data/{date}/tradeview_utc.csv"
                cont_signals_file = f"./data/{date}/tradeview_cont_output.csv"
                rev_signals_file = f"./data/{date}/tradeview_rev_output.csv"

                if not all(os.path.exists(f) for f in [price_data_file, cont_signals_file, rev_signals_file]):
                    print(f"  - Skipping {date}, missing one or more required files for CPR filtering.")
                    continue

                price_df = pd.read_csv(price_data_file, encoding='utf-8-sig')
                cont_signals_df = pd.read_csv(cont_signals_file, encoding='utf-8-sig')
                rev_signals_df = pd.read_csv(rev_signals_file, encoding='utf-8-sig')

                # Define the mapping of signal columns to trade types
                trade_type_map_rev = {'Call': 'Call', 'Put': 'Put', 'Call_v2': 'Call', 'Put_v2': 'Put'}
                trade_type_map_cont = {'Call': 'Call', 'Put': 'Put'}

                # Run filter for reversal signals
                rev_signals_df_filtered = run_cpr_filter(price_df.copy(), rev_signals_df, trade_type_map_rev)
                rev_signals_df_filtered.to_csv(rev_signals_file, index=False)
                print(f"  ✓ Saved filtered reversal signals to {rev_signals_file}")

                # Run filter for continuation signals
                cont_signals_df_filtered = run_cpr_filter(price_df.copy(), cont_signals_df, trade_type_map_cont)
                cont_signals_df_filtered.to_csv(cont_signals_file, index=False)
                print(f"  ✓ Saved filtered continuation signals to {cont_signals_file}")

            except Exception as e:
                print(f"  ✗ ERROR processing {date} in Step 5: {str(e)}")
                traceback.print_exc()
        print("\nStep 5 finished.\n")

    if run_step_6:
        print("\n--- Running Step 6: Run Backtest on CPR-Filtered Signals ---")
        
        for date in dates:
            cont_signals_file = f"./data/{date}/tradeview_cont_output.csv"
            rev_signals_file = f"./data/{date}/tradeview_rev_output.csv"
            calls_file = f"./data/{date}/call/call_out.csv"
            puts_file = f"./data/{date}/put/put_out.csv"
            
            required_files = [calls_file, puts_file, cont_signals_file, rev_signals_file]
            if all(os.path.exists(f) for f in required_files):
                print(f"\n--- Processing Date: {date} ---")
                try:
                    # Read all required CSVs
                    calls_df = pd.read_csv(calls_file, encoding='utf-8-sig')
                    calls_df['datetime'] = pd.to_datetime(calls_df['datetime'])
                    
                    puts_df = pd.read_csv(puts_file, encoding='utf-8-sig')
                    puts_df['datetime'] = pd.to_datetime(puts_df['datetime'])
                    
                    cont_signals_df = pd.read_csv(cont_signals_file, encoding='utf-8-sig')
                    cont_signals_df['datetime'] = pd.to_datetime(cont_signals_df['datetime'])
                    
                    rev_signals_df = pd.read_csv(rev_signals_file, encoding='utf-8-sig')
                    rev_signals_df['datetime'] = pd.to_datetime(rev_signals_df['datetime'])

                    # --- Run all three backtests with CPR-filtered signals ---
                    
                    # 1. Continuation Strategy (CPR)
                    trades_cont_cpr = run_backtest(cont_signals_df, calls_df.copy(), puts_df.copy(), date, config, 
                                                   strategy_name='Continuation Strategy (CPR)', call_col='Call_crp', put_col='Put_crp')
                    
                    # 2. Reversal Strategy (CPR)
                    trades_rev_cpr = run_backtest(rev_signals_df.copy(), calls_df.copy(), puts_df.copy(), date, config, 
                                                  strategy_name='Reversal Strategy (CPR)', call_col='Call_crp', put_col='Put_crp')
                    
                    # 3. Reversal Strategy v2 (CPR)
                    trades_rev_v2_cpr = run_backtest(rev_signals_df.copy(), calls_df.copy(), puts_df.copy(), date, config, 
                                                     strategy_name='Reversal Strategy v2 (CPR)', call_col='Call_v2_crp', put_col='Put_v2_crp')
                    
                    # --- Save all results ---

                    backtest_dir = f"./data/{date}/backtest_crp"
                    os.makedirs(backtest_dir, exist_ok=True)

                    if trades_cont_cpr:
                        cont_results_file = f"{backtest_dir}/backtest_results_cont.csv"
                        pd.DataFrame(trades_cont_cpr).to_csv(cont_results_file, index=False)
                        print(f"  ✓ Saved {len(trades_cont_cpr)} CPR continuation trades to {cont_results_file}")

                    if trades_rev_cpr:
                        rev_results_file = f"{backtest_dir}/backtest_results_rev.csv"
                        pd.DataFrame(trades_rev_cpr).to_csv(rev_results_file, index=False)
                        print(f"  ✓ Saved {len(trades_rev_cpr)} CPR reversal trades to {rev_results_file}")

                    if trades_rev_v2_cpr:
                        rev_v2_results_file = f"{backtest_dir}/backtest_results_rev_v2.csv"
                        pd.DataFrame(trades_rev_v2_cpr).to_csv(rev_v2_results_file, index=False)
                        print(f"  ✓ Saved {len(trades_rev_v2_cpr)} CPR reversal v2 trades to {rev_v2_results_file}")
                    
                    if not (trades_cont_cpr or trades_rev_cpr or trades_rev_v2_cpr):
                        print(f"  - No CPR-filtered trades found for {date}")
                
                except Exception as e:
                    print(f"  ✗ ERROR processing {date} in Step 6: {str(e)}")
                    traceback.print_exc()
            else:
                print(f"  - Skipping {date}, missing one or more required files.")
        
        print("\nStep 6 finished.\n")

    if run_step_7:
        print("\n--- Running Step 7: Execute Trades ---")
        for date in dates:
            print(f"\n--- Processing Date: {date} ---")
            try:
                cont_signals_file = f"./data/{date}/tradeview_cont_output.csv"
                rev_signals_file = f"./data/{date}/tradeview_rev_output.csv"
                calls_file = f"./data/{date}/call/call_out.csv"
                puts_file = f"./data/{date}/put/put_out.csv"

                required_files = [calls_file, puts_file, cont_signals_file, rev_signals_file]
                if not all(os.path.exists(f) for f in required_files):
                    print(f"  - Skipping {date}, missing one or more required files for trade execution.")
                    continue

                calls_df = pd.read_csv(calls_file, encoding='utf-8-sig')
                puts_df = pd.read_csv(puts_file, encoding='utf-8-sig')
                cont_signals_df = pd.read_csv(cont_signals_file, encoding='utf-8-sig')
                rev_signals_df = pd.read_csv(rev_signals_file, encoding='utf-8-sig')

                all_trades = []

                # Execute trades for reversal signals
                rev_v1_call_trades = execute_trades(rev_signals_df.copy(), calls_df.copy(), 'Call', 'Call')
                all_trades.append(rev_v1_call_trades)
                rev_v1_put_trades = execute_trades(rev_signals_df.copy(), puts_df.copy(), 'Put', 'Put')
                all_trades.append(rev_v1_put_trades)

                # Execute trades for reversal v2 signals
                rev_v2_call_trades = execute_trades(rev_signals_df.copy(), calls_df.copy(), 'Call_v2', 'Call')
                all_trades.append(rev_v2_call_trades)
                rev_v2_put_trades = execute_trades(rev_signals_df.copy(), puts_df.copy(), 'Put_v2', 'Put')
                all_trades.append(rev_v2_put_trades)

                # Execute trades for continuation signals
                cont_call_trades = execute_trades(cont_signals_df.copy(), calls_df.copy(), 'Call', 'Call')
                all_trades.append(cont_call_trades)
                cont_put_trades = execute_trades(cont_signals_df.copy(), puts_df.copy(), 'Put', 'Put')
                all_trades.append(cont_put_trades)

                # Combine and save results
                if all_trades:
                    final_trades_df = pd.concat(all_trades)
                    trades_dir = f"./data/{date}/trades"
                    os.makedirs(trades_dir, exist_ok=True)
                    
                    # Save different sets of trades
                    pd.concat([rev_v1_call_trades, rev_v1_put_trades]).to_csv(f"{trades_dir}/rev_v1_trades.csv", index=False)
                    pd.concat([rev_v2_call_trades, rev_v2_put_trades]).to_csv(f"{trades_dir}/rev_v2_trades.csv", index=False)
                    pd.concat([cont_call_trades, cont_put_trades]).to_csv(f"{trades_dir}/cont_trades.csv", index=False)
                    
                    print(f"  ✓ Saved executed trades to {trades_dir}")
                else:
                    print(f"  - No trades executed for {date}")

            except Exception as e:
                print(f"  ✗ ERROR processing {date} in Step 7: {str(e)}")
                traceback.print_exc()
        print("\nStep 7 finished.\n")

    if run_step_8:
        print("\n--- Running Step 8: Execute CPR-Filtered Trades ---")
        for date in dates:
            print(f"\n--- Processing Date: {date} ---")
            try:
                cont_signals_file = f"./data/{date}/tradeview_cont_output.csv"
                rev_signals_file = f"./data/{date}/tradeview_rev_output.csv"
                calls_file = f"./data/{date}/call/call_out.csv"
                puts_file = f"./data/{date}/put/put_out.csv"

                required_files = [calls_file, puts_file, cont_signals_file, rev_signals_file]
                if not all(os.path.exists(f) for f in required_files):
                    print(f"  - Skipping {date}, missing one or more required files for trade execution.")
                    continue

                calls_df = pd.read_csv(calls_file, encoding='utf-8-sig')
                puts_df = pd.read_csv(puts_file, encoding='utf-8-sig')
                cont_signals_df = pd.read_csv(cont_signals_file, encoding='utf-8-sig')
                rev_signals_df = pd.read_csv(rev_signals_file, encoding='utf-8-sig')

                all_trades = []

                # Execute trades for reversal signals (CPR)
                rev_v1_call_trades = execute_trades(rev_signals_df.copy(), calls_df.copy(), 'Call_crp', 'Call')
                all_trades.append(rev_v1_call_trades)
                rev_v1_put_trades = execute_trades(rev_signals_df.copy(), puts_df.copy(), 'Put_crp', 'Put')
                all_trades.append(rev_v1_put_trades)

                # Execute trades for reversal v2 signals (CPR)
                rev_v2_call_trades = execute_trades(rev_signals_df.copy(), calls_df.copy(), 'Call_v2_crp', 'Call')
                all_trades.append(rev_v2_call_trades)
                rev_v2_put_trades = execute_trades(rev_signals_df.copy(), puts_df.copy(), 'Put_v2_crp', 'Put')
                all_trades.append(rev_v2_put_trades)

                # Execute trades for continuation signals (CPR)
                cont_call_trades = execute_trades(cont_signals_df.copy(), calls_df.copy(), 'Call_crp', 'Call')
                all_trades.append(cont_call_trades)
                cont_put_trades = execute_trades(cont_signals_df.copy(), puts_df.copy(), 'Put_crp', 'Put')
                all_trades.append(cont_put_trades)

                # Combine and save results
                if all_trades:
                    final_trades_df = pd.concat(all_trades)
                    trades_dir = f"./data/{date}/trades_crp"
                    os.makedirs(trades_dir, exist_ok=True)
                    
                    pd.concat([rev_v1_call_trades, rev_v1_put_trades]).to_csv(f"{trades_dir}/rev_v1_trades.csv", index=False)
                    pd.concat([rev_v2_call_trades, rev_v2_put_trades]).to_csv(f"{trades_dir}/rev_v2_trades.csv", index=False)
                    pd.concat([cont_call_trades, cont_put_trades]).to_csv(f"{trades_dir}/cont_trades.csv", index=False)
                    
                    print(f"  ✓ Saved executed CPR-filtered trades to {trades_dir}")
                else:
                    print(f"  - No CPR-filtered trades executed for {date}")

            except Exception as e:
                print(f"  ✗ ERROR processing {date} in Step 8: {str(e)}")
                traceback.print_exc()
        print("\nStep 8 finished.\n")

    if run_final_analytics:
        print("\n--- Running Step 9: Generate Final Analytics Report ---")
        run_analysis()
        print("Step 9 finished.\n")

    print("All selected steps completed successfully!")

if __name__ == "__main__":
    main()