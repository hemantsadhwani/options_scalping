# nifty_option_trading/app.py

# --- Core Imports ---
# These paths now correctly reflect our project structure.
from run_process_data import run_process_data
from strategies.run_cont_strategy import generate_continuation_strategies
from strategies.run_rev_strategy import generate_reversal_strategies
from backtesting.run_backtesting import run_backtest
from backtesting.run_analytics import generate_final_analytics_report
from tools.clean_data_dir import clean_generated_files

# --- Step Controllers ---
# Set these to True or False to control which parts of the pipeline run.
run_cleanup = True          # Set to True to delete all generated files before running.
run_step_1 = True           # Process Raw Data
run_step_2 = True           # Generate Continuation Strategy Signals
run_step_3 = True           # Generate Reversal Strategy Signals
run_step_4 = True           # Run Backtest
run_step_5 = True           # Generate Final Analytics Report

def main():
    """
    Main entry point to run the entire trading analysis pipeline.
    """
    print("--- Starting Trading Application Pipeline ---")

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
        run_backtest()
        print("-" * 50)

    if run_step_5:
        generate_final_analytics_report()
        print("-" * 50)

    print("\n--- Trading Application Pipeline Finished ---")


if __name__ == "__main__":
    main()