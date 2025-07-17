#!/usr/bin/env python3
"""
Test script to process CRP signals and generate rev_v1_trades.csv
This script reads Call_crp and Put_crp signals from tradeview_rev_output.csv
and processes them using the existing option_trade_executor.py
"""

import pandas as pd
import os
import sys
from datetime import datetime
import yaml

# Add the current directory to Python path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from option_tools.option_trade_executor import execute_option_trades

def load_config():
    """Load configuration from config.yaml"""
    try:
        with open('config.yaml', 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Warning: Could not load config.yaml: {e}")
        # Return default config
        return {
            'LAST_ENTRY_TIME': '14:30'
        }

def process_crp_signals(date_folder='0307'):
    """
    Process CRP signals for the specified date folder
    """
    print(f"=== Processing CRP Signals for {date_folder} ===")
    
    # Define file paths
    base_path = f"./data/{date_folder}"
    signals_file = f"{base_path}/tradeview_rev_output.csv"
    call_prices_file = f"{base_path}/call/call_out.csv"
    put_prices_file = f"{base_path}/put/put_out.csv"
    output_dir = f"{base_path}/trades_crp"
    output_file = "rev_v1_trades.csv"
    
    # Check if files exist
    for file_path in [signals_file, call_prices_file, put_prices_file]:
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return False
    
    print(f"✅ All required files found")
    
    # Load data
    print("\n--- Loading Data ---")
    signals_df = pd.read_csv(signals_file)
    call_prices_df = pd.read_csv(call_prices_file)
    put_prices_df = pd.read_csv(put_prices_file)
    
    print(f"Signals data: {len(signals_df)} rows")
    print(f"Call prices data: {len(call_prices_df)} rows")
    print(f"Put prices data: {len(put_prices_df)} rows")
    
    # Convert datetime columns
    signals_df['datetime'] = pd.to_datetime(signals_df['datetime'])
    call_prices_df['datetime'] = pd.to_datetime(call_prices_df['datetime'])
    put_prices_df['datetime'] = pd.to_datetime(put_prices_df['datetime'])
    
    # Check for CRP signal columns
    if 'Call_crp' not in signals_df.columns or 'Put_crp' not in signals_df.columns:
        print("❌ Call_crp or Put_crp columns not found in signals data")
        return False
    
    # Count signals
    call_signals = signals_df[signals_df['Call_crp'] == 1]
    put_signals = signals_df[signals_df['Put_crp'] == 1]
    
    print(f"\n--- Signal Analysis ---")
    print(f"Call CRP signals: {len(call_signals)}")
    print(f"Put CRP signals: {len(put_signals)}")
    
    if len(call_signals) > 0:
        print("Call signal times:")
        for _, signal in call_signals.iterrows():
            print(f"  {signal['datetime']}")
    
    if len(put_signals) > 0:
        print("Put signal times:")
        for _, signal in put_signals.iterrows():
            print(f"  {signal['datetime']}")
    
    # Load configuration
    config = load_config()
    
    # Clear existing output file
    output_path = os.path.join(output_dir, output_file)
    if os.path.exists(output_path):
        os.remove(output_path)
        print(f"\n--- Cleared existing {output_file} ---")
    
    # Process Call signals
    print(f"\n--- Processing Call Signals ---")
    if len(call_signals) > 0:
        call_results = execute_option_trades(
            signals_df=signals_df,
            prices_df=call_prices_df,
            signal_col='Call_crp',
            trade_type='Call',
            config=config,
            output_dir=output_dir,
            output_filename=output_file
        )
        print(f"Call trades processed: {len(call_results) if call_results is not None else 0}")
    else:
        print("No call signals to process")
    
    # Process Put signals
    print(f"\n--- Processing Put Signals ---")
    if len(put_signals) > 0:
        put_results = execute_option_trades(
            signals_df=signals_df,
            prices_df=put_prices_df,
            signal_col='Put_crp',
            trade_type='Put',
            config=config,
            output_dir=output_dir,
            output_filename=output_file
        )
        print(f"Put trades processed: {len(put_results) if put_results is not None else 0}")
    else:
        print("No put signals to process")
    
    # Load and display results
    if os.path.exists(output_path):
        results_df = pd.read_csv(output_path)
        print(f"\n--- Final Results ---")
        print(f"Total trades generated: {len(results_df)}")
        print(f"Results saved to: {output_path}")
        
        # Display trade summary
        if len(results_df) > 0:
            print("\nTrade Summary:")
            for _, trade in results_df.iterrows():
                print(f"  {trade['Entry Time']} | {trade['Trade Type']} | Entry: {trade['Entry Price']} | Exit: {trade['Exit Price']} | P/L: {trade['P/L %']} | Reason: {trade['Exit Reason']}")
        
        return True
    else:
        print("❌ No trades were generated")
        return False

def compare_with_expected(date_folder='0307'):
    """
    Compare generated results with expected tiered_simulated_trades.csv
    """
    print(f"\n=== Comparing Results ===")
    
    base_path = f"./data/{date_folder}/trades_crp"
    generated_file = f"{base_path}/rev_v1_trades.csv"
    expected_file = f"{base_path}/tiered_simulated_trades.csv"
    
    if not os.path.exists(generated_file):
        print("❌ Generated file not found")
        return
    
    if not os.path.exists(expected_file):
        print("❌ Expected file not found")
        return
    
    generated_df = pd.read_csv(generated_file)
    expected_df = pd.read_csv(expected_file)
    
    print(f"Generated trades: {len(generated_df)}")
    print(f"Expected trades: {len(expected_df)}")
    
    if len(generated_df) == len(expected_df):
        print("✅ Trade count matches!")
    else:
        print("❌ Trade count mismatch")
    
    # Compare individual trades
    print("\n--- Trade Comparison ---")
    print("Generated:")
    for _, trade in generated_df.iterrows():
        print(f"  {trade['Entry Time']} | {trade['Trade Type']} | P/L: {trade['P/L %']}")
    
    print("\nExpected:")
    for _, trade in expected_df.iterrows():
        print(f"  {trade['Entry Time']} | {trade['Trade Type']} | P/L: {trade['P/L %']}")

def debug_signal_processing(date_folder='0307'):
    """
    Debug signal processing to understand discrepancies
    """
    print(f"\n=== Debugging Signal Processing ===")
    
    base_path = f"./data/{date_folder}"
    signals_file = f"{base_path}/tradeview_rev_output.csv"
    
    if not os.path.exists(signals_file):
        print("❌ Signals file not found")
        return
    
    signals_df = pd.read_csv(signals_file)
    signals_df['datetime'] = pd.to_datetime(signals_df['datetime'])
    
    # Check all signal columns
    signal_columns = [col for col in signals_df.columns if 'Call' in col or 'Put' in col]
    print(f"Available signal columns: {signal_columns}")
    
    for col in signal_columns:
        signals = signals_df[signals_df[col] == 1]
        if len(signals) > 0:
            print(f"\n{col} signals ({len(signals)}):")
            for _, signal in signals.iterrows():
                print(f"  {signal['datetime']}")

def main():
    """Main function to run the test"""
    print("CRP Trades Test Script")
    print("=" * 50)
    
    # Process CRP signals
    success = process_crp_signals('0307')
    
    if success:
        # Compare with expected results
        compare_with_expected('0307')
    
    # Debug signal processing
    debug_signal_processing('0307')

if __name__ == "__main__":
    main()
