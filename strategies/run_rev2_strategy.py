# strategies/run_rev2_strategy.py

import pandas as pd
import numpy as np
import os

def apply_reversal_strategy_to_directory_v2(date_dir_path):
    """
    Applies the second reversal strategy to a specific date directory.
    Creates output file if it doesn't exist, or adds v2 columns to existing file.
    """
    input_file = os.path.join(date_dir_path, 'tradeview_utc.csv')
    output_file = os.path.join(date_dir_path, 'tradeview_rev_output.csv')

    print(f"\n--- Applying Reversal Strategy v2 in: {date_dir_path} ---")

    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"⚠️  Warning: Missing input file in {date_dir_path}. Skipping.")
        return

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
        output_df = df[['datetime', 'open', 'high', 'low', 'close', 'Daily Pivot', 'Daily BC', 'Daily TC', 
                        'Daily R1', 'Daily R2', 'Daily R3', 'Daily R4', 'Daily S1', 'Daily S2', 
                        'Daily S3', 'Daily S4', 'Prev Day High', 'Prev Day Low']].copy()
        output_df.set_index('datetime', inplace=True)
        # Initialize basic Call/Put columns if creating new file
        output_df['Call'] = 0
        output_df['Put'] = 0

    # Initialize v2 strategy columns (add if they don't exist)
    if 'Call_v2' not in output_df.columns:
        output_df['Call_v2'] = 0
    if 'Put_v2' not in output_df.columns:
        output_df['Put_v2'] = 0

    # Ensure the required Williams %R column exists
    if '%R.1' not in df.columns:
        print(f"⚠️  Error: Williams %R (28) column '%R.1' not found in {input_file}.")
        return
        
    df.rename(columns={'%R.1': 'williamsR_28'}, inplace=True)
    
    # Initialize state flags
    crossover_80_flag = 0
    crossunder_20_flag = 0
    
    # Get the datetime index from the main df to align with output_df
    df.set_index('datetime', inplace=True)

    print("Processing signals row by row...")
    for i in range(1, len(df)):
        # Get current and previous Williams %R values
        prev_wr = df['williamsR_28'].iloc[i-1]
        curr_wr = df['williamsR_28'].iloc[i]
        current_time = df.index[i]
        next_time = df.index[i+1] if i+1 < len(df) else None

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

        # --- Put Logic ---
        # 1. Arming the signal: Cross below -20
        if crossunder_20_flag == 0 and prev_wr >= -20 and curr_wr < -20:
            crossunder_20_flag = 1
            # If trigger is also met on the same candle, fire signal
            if prev_wr >= -50 and curr_wr < -50:
                if current_time in output_df.index:
                    output_df.loc[current_time, 'Put_v2'] = 1
                crossunder_20_flag = 0 # Reset after firing

        # 2. Invalidation: Cross back above -20 before confirmation
        elif crossunder_20_flag == 1 and prev_wr <= -20 and curr_wr > -20:
            crossunder_20_flag = 0

        # 3. Entry Trigger: Cross below -50 when armed
        elif crossunder_20_flag == 1 and prev_wr >= -50 and curr_wr < -50:
            # Signal on current candle
            if current_time in output_df.index:
                output_df.loc[current_time, 'Put_v2'] = 1
            crossunder_20_flag = 0

    # Save the updated output
    output_df.to_csv(output_file, index=True)
    
    # Count signals
    call_count = output_df['Call_v2'].sum()
    put_count = output_df['Put_v2'].sum()
    
    print(f"✅ Reversal strategy v2 output updated in {output_file}")
    print(f"   Reversal v2 Call signals found: {call_count}")
    print(f"   Reversal v2 Put signals found: {put_count}")

def generate_reversal_strategies_v2():
    """
    Applies the second reversal strategy to all date directories.
    """
    base_data_dir = 'data'
    if not os.path.isdir(base_data_dir):
        print(f"❌ Error: Base directory '{base_data_dir}' not found.")
        return

    subdirectories = [d for d in os.listdir(base_data_dir) if os.path.isdir(os.path.join(base_data_dir, d))]
    if not subdirectories:
        print(f"ℹ️ No subdirectories found in '{base_data_dir}'.")
        return

    print(f"Found {len(subdirectories)} directories to process for reversal strategy v2: {sorted(subdirectories)}")
    
    for dir_name in sorted(subdirectories):
        apply_reversal_strategy_to_directory_v2(os.path.join(base_data_dir, dir_name))
    
    print("\n🎉 All reversal strategies v2 applied.")
