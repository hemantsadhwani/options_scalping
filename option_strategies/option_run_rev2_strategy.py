# option_strategies/option_run_rev2_strategy.py

import pandas as pd
import numpy as np
import os

def apply_reversal_strategy_to_directory_v2_options(date_dir_path, input_filename, output_filename):
    """
    Applies the second reversal strategy for option buying (long-only signals).
    For call option files: only generates Call_v2 signals (long call options)
    For put option files: only generates Put_v2 signals (long put options)
    """
    input_file = os.path.join(date_dir_path, input_filename)
    output_file = os.path.join(date_dir_path, output_filename)

    print(f"\n--- Applying Option Reversal Strategy v2 in: {date_dir_path} on {input_filename} ---")

    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"⚠️  Warning: Missing input file in {date_dir_path}. Skipping.")
        return

    # Detect option type from filename
    is_call_option_file = 'call_out.csv' in input_filename
    is_put_option_file = 'put_out.csv' in input_filename
    
    if not (is_call_option_file or is_put_option_file):
        print(f"⚠️  Warning: This strategy is only for call_out.csv or put_out.csv files. Skipping {input_filename}")
        return
    
    option_type = 'Call' if is_call_option_file else 'Put'
    print(f"   📈 Option Buying Mode: {option_type} options - Long only signals")

    # Load the raw data with indicators
    df = pd.read_csv(input_file, parse_dates=['datetime'])
    
    # Load or create the output file
    if os.path.exists(output_file):
        # Load existing output file
        output_df = pd.read_csv(output_file, parse_dates=['datetime'], index_col='datetime')
        print(f"Loading existing output file: {output_file}")
    else:
        # Create new output file if it doesn't exist
        print(f"Creating new output file: {output_file}")
        # Define base columns and CPR-related columns
        base_cols = ['datetime', 'open', 'high', 'low', 'close']
        cpr_cols = [
            'Daily Pivot', 'Daily BC', 'Daily TC', 'Daily R1', 'Daily R2', 
            'Daily R3', 'Daily R4', 'Daily S1', 'Daily S2', 'Daily S3', 
            'Daily S4', 'Prev Day High', 'Prev Day Low'
        ]
        # Select only the columns that actually exist in the input dataframe
        existing_cols = base_cols + [col for col in cpr_cols if col in df.columns]
        
        # Create new output file with only existing columns
        output_df = df[existing_cols].copy()
        output_df.set_index('datetime', inplace=True)
        
        # Only create columns relevant to the option type
        if is_call_option_file:
            output_df['Call'] = 0      # Only Call columns for call option files
            output_df['Call_v2'] = 0
        elif is_put_option_file:
            output_df['Put'] = 0       # Only Put columns for put option files
            output_df['Put_v2'] = 0

    # Initialize v2 strategy columns for existing files (add if they don't exist)
    if is_call_option_file:
        if 'Call_v2' not in output_df.columns:
            output_df['Call_v2'] = 0
    elif is_put_option_file:
        if 'Put_v2' not in output_df.columns:
            output_df['Put_v2'] = 0

    # Ensure the required Williams %R column exists
    if '%R.1' not in df.columns:
        print(f"⚠️  Error: Williams %R (28) column '%R.1' not found in {input_file}.")
        return
        
    df.rename(columns={'%R.1': 'williamsR_28'}, inplace=True)
    
    # Initialize state flags based on option type
    crossover_80_flag = 0  # Used for both call and put options (cross above -80)
    
    # Get the datetime index from the main df to align with output_df
    df.set_index('datetime', inplace=True)

    print("Processing signals row by row...")
    for i in range(1, len(df)):
        # Get current and previous Williams %R values
        prev_wr = df['williamsR_28'].iloc[i-1]
        curr_wr = df['williamsR_28'].iloc[i]
        current_time = df.index[i]

        # Apply option-specific logic
        if is_call_option_file:
            # For call options, only process call logic (long call buying opportunities)
            # --- Call Logic ---
            # 1. Arming the signal: Cross above -80
            if crossover_80_flag == 0 and prev_wr <= -80 and curr_wr > -80:
                crossover_80_flag = 1

            # 2. Invalidation: Cross back below -80 before confirmation
            elif crossover_80_flag == 1 and prev_wr >= -80 and curr_wr < -80:
                crossover_80_flag = 0

            # 3. Entry Trigger: Cross above -50 when armed
            elif crossover_80_flag == 1 and prev_wr <= -50 and curr_wr > -50:
                # Signal on current candle
                if current_time in output_df.index:
                    output_df.loc[current_time, 'Call_v2'] = 1
                crossover_80_flag = 0
                
        elif is_put_option_file:
            # For put options, use BULLISH logic (long put buying when underlying reverses up)
            # --- Put Logic (CORRECTED) - Same as Call logic ---
            # 1. Arming the signal: Cross above -80 (bullish reversal for put buying)
            if crossover_80_flag == 0 and prev_wr <= -80 and curr_wr > -80:
                crossover_80_flag = 1

            # 2. Invalidation: Cross back below -80 before confirmation
            elif crossover_80_flag == 1 and prev_wr >= -80 and curr_wr < -80:
                crossover_80_flag = 0

            # 3. Entry Trigger: Cross above -50 when armed (confirming upward momentum for put buying)
            elif crossover_80_flag == 1 and prev_wr <= -50 and curr_wr > -50:
                # Signal on current candle
                if current_time in output_df.index:
                    output_df.loc[current_time, 'Put_v2'] = 1
                crossover_80_flag = 0

    # Save the updated output
    output_df.to_csv(output_file, index=True)
    
    # Count signals and provide appropriate output based on option type
    if is_call_option_file:
        call_count = output_df['Call_v2'].sum()
        print(f"✅ Option Reversal strategy v2 output updated in {output_file}")
        print(f"   Call option v2 signals found: {call_count} (Long Call options only)")
    elif is_put_option_file:
        put_count = output_df['Put_v2'].sum()
        print(f"✅ Option Reversal strategy v2 output updated in {output_file}")
        print(f"   Put option v2 signals found: {put_count} (Long Put options only)")

def generate_reversal_strategies_v2_options(call_input_filename='call/call_out.csv', call_output_filename='call/call_rev_out.csv', put_input_filename='put/put_out.csv', put_output_filename='put/put_rev_out.csv'):
    """
    Generates reversal strategies v2 specifically for option buying.
    Processes call and put option files separately with long-only signals.
    """
    base_data_dir = 'data'
    if not os.path.isdir(base_data_dir):
        print(f"❌ Error: Base directory '{base_data_dir}' not found.")
        return

    subdirectories = [d for d in os.listdir(base_data_dir) if os.path.isdir(os.path.join(base_data_dir, d))]
    if not subdirectories:
        print(f"ℹ️ No subdirectories found in '{base_data_dir}'.")
        return

    print(f"Found {len(subdirectories)} directories to process for option reversal strategy v2: {sorted(subdirectories)}")
    
    for dir_name in sorted(subdirectories):
        date_dir_path = os.path.join(base_data_dir, dir_name)
        
        # Process call options
        call_input_path = os.path.join(date_dir_path, call_input_filename)
        if os.path.exists(call_input_path):
            apply_reversal_strategy_to_directory_v2_options(date_dir_path, call_input_filename, call_output_filename)
        else:
            print(f"⚠️  Call option file not found: {call_input_path}")
        
        # Process put options
        put_input_path = os.path.join(date_dir_path, put_input_filename)
        if os.path.exists(put_input_path):
            apply_reversal_strategy_to_directory_v2_options(date_dir_path, put_input_filename, put_output_filename)
        else:
            print(f"⚠️  Put option file not found: {put_input_path}")
    
    print("\n🎉 All option reversal strategies v2 applied.")
