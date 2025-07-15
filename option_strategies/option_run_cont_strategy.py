# option_strategies/option_run_cont_strategy.py

import pandas as pd
import numpy as np
import os

def apply_continuation_strategy_to_directory_options(date_dir_path, input_filename, output_filename):
    """
    Applies the continuation strategy for option buying (long-only signals).
    For call option files: only generates Call signals (long call options)
    For put option files: only generates Put signals (long put options)
    """
    input_file = os.path.join(date_dir_path, input_filename)
    output_file = os.path.join(date_dir_path, output_filename)

    print(f"\n--- Applying Option Continuation Strategy in: {date_dir_path} on {input_filename}---")

    if not os.path.exists(input_file):
        print(f"⚠️  Warning: Base data file '{input_file}' not found. Skipping.")
        return
    
    # Detect option type from filename
    is_call_option_file = 'call_out.csv' in input_filename
    is_put_option_file = 'put_out.csv' in input_filename
    
    if not (is_call_option_file or is_put_option_file):
        print(f"⚠️  Warning: This strategy is only for call_out.csv or put_out.csv files. Skipping {input_filename}")
        return
    
    option_type = 'Call' if is_call_option_file else 'Put'
    print(f"   📈 Option Buying Mode: {option_type} options - Long only signals")
    
    df = pd.read_csv(input_file, parse_dates=['datetime'])

    # --- Base Calculations ---
    # For options, we use the option's own price data and indicators, not index trend data
    df.rename(columns={'%R': 'williamsRFast', '%R.1': 'williamsRSlow', 'K': 'stochRSIK', 'D': 'stochRSID'}, inplace=True)
    
    # For options, we determine direction based on the option's own price movement
    # Simple trend determination: if close > open, uptrend (direction = -1), else downtrend (direction = 1)
    df['direction'] = np.where(df['close'] > df['open'], -1, 1)
    
    def crossover(s1, s2): return (s1 > s2) & (s1.shift(1) <= s2.shift(1))
    def crossunder(s1, s2): return (s1 < s2) & (s1.shift(1) >= s2.shift(1))
    
    # --- Pre-calculate event markers ---
    df['williams_fast_put_trigger'] = crossunder(df['williamsRFast'], pd.Series(-20, index=df.index))
    df['williams_fast_put_reversal'] = crossover(df['williamsRFast'], pd.Series(-20, index=df.index))
    df['stoch_put_confirmation'] = crossunder(df['stochRSIK'], pd.Series(80, index=df.index))
    df['williams_fast_call_trigger'] = crossover(df['williamsRFast'], pd.Series(-80, index=df.index))
    df['williams_fast_call_reversal'] = crossunder(df['williamsRFast'], pd.Series(-80, index=df.index))
    df['stoch_call_confirmation'] = crossover(df['stochRSIK'], pd.Series(20, index=df.index))
    
    # --- Initialize State Machines ---
    WAIT_BARS = 4
    df['putEntrySignal'] = False
    df['callEntrySignal'] = False
    put_state, put_trigger_bar_index = 'WAITING_FOR_TRIGGER', -1
    call_state, call_trigger_bar_index = 'WAITING_FOR_TRIGGER', -1

    for i in range(len(df)):
        # Only process the relevant option type signals
        if is_put_option_file:
            # --- Put State Machine ---
            if put_state == 'WAITING_FOR_TRIGGER':
                if df.at[i, 'williams_fast_put_trigger'] and df.at[i, 'direction'] == 1:
                    put_state = 'WAITING_FOR_CONFIRMATION'
                    put_trigger_bar_index = i
            elif put_state == 'WAITING_FOR_CONFIRMATION':
                if i > put_trigger_bar_index + WAIT_BARS or df.at[i, 'williams_fast_put_reversal']:
                    put_state = 'WAITING_FOR_TRIGGER'
                elif df.at[i, 'stoch_put_confirmation']:
                    if df.at[i, 'williamsRSlow'] < -60:
                        df.at[i, 'putEntrySignal'] = True
                        put_state = 'WAITING_FOR_TRIGGER'
        
        elif is_call_option_file:
            # --- Call State Machine ---
            if call_state == 'WAITING_FOR_TRIGGER':
                if df.at[i, 'williams_fast_call_trigger'] and df.at[i, 'direction'] == -1:
                    call_state = 'WAITING_FOR_CONFIRMATION'
                    call_trigger_bar_index = i
            elif call_state == 'WAITING_FOR_CONFIRMATION':
                if i > call_trigger_bar_index + WAIT_BARS or df.at[i, 'williams_fast_call_reversal']:
                    call_state = 'WAITING_FOR_TRIGGER'
                elif df.at[i, 'stoch_call_confirmation']:
                    if df.at[i, 'williamsRSlow'] > -40:
                        df.at[i, 'callEntrySignal'] = True
                        call_state = 'WAITING_FOR_TRIGGER'

    # --- Create Output DataFrame ---
    # Check if output file exists, if not create a new DataFrame
    if os.path.exists(output_file):
        output_df = pd.read_csv(output_file, parse_dates=['datetime'], index_col='datetime')
    else:
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
            output_df['Call'] = 0  # Only Call column for call option files
        elif is_put_option_file:
            output_df['Put'] = 0   # Only Put column for put option files
    
    # --- Signal Processing ---
    # Create a mapping from index to datetime for easier reference
    index_to_datetime = dict(zip(range(len(df)), df['datetime']))
    
    # Get indices where signals are True and process only the relevant option type
    signal_times = []
    signal_type = ''
    
    if is_call_option_file:
        call_signal_indices = df[df['callEntrySignal']].index.tolist()
        for idx in call_signal_indices:
            signal_times.append(index_to_datetime[idx])
            print(f"Call signal at {index_to_datetime[idx]} -> Long Call Option Trade")
        
        # Apply only call signals
        output_df.loc[signal_times, 'Call'] = 1
        signal_type = 'Call'
        
    elif is_put_option_file:
        put_signal_indices = df[df['putEntrySignal']].index.tolist()
        for idx in put_signal_indices:
            signal_times.append(index_to_datetime[idx])
            print(f"Put signal at {index_to_datetime[idx]} -> Long Put Option Trade")
        
        # Apply only put signals
        output_df.loc[signal_times, 'Put'] = 1
        signal_type = 'Put'

    output_df.to_csv(output_file, index=True)
    print(f"✅ Option Continuation strategy output saved to {output_file}")
    print(f"   {signal_type} option signals found: {len(signal_times)} (Long {signal_type} options only)")

def generate_continuation_strategies_options(call_input_filename='call/call_out.csv', call_output_filename='call/call_cont_out.csv', put_input_filename='put/put_out.csv', put_output_filename='put/put_cont_out.csv'):
    """
    Generates continuation strategies specifically for option buying.
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
    
    print(f"Found {len(subdirectories)} directories to process for option continuation strategy: {sorted(subdirectories)}")
    
    for dir_name in sorted(subdirectories):
        date_dir_path = os.path.join(base_data_dir, dir_name)
        
        # Process call options
        call_input_path = os.path.join(date_dir_path, call_input_filename)
        if os.path.exists(call_input_path):
            apply_continuation_strategy_to_directory_options(date_dir_path, call_input_filename, call_output_filename)
        else:
            print(f"⚠️  Call option file not found: {call_input_path}")
        
        # Process put options
        put_input_path = os.path.join(date_dir_path, put_input_filename)
        if os.path.exists(put_input_path):
            apply_continuation_strategy_to_directory_options(date_dir_path, put_input_filename, put_output_filename)
        else:
            print(f"⚠️  Put option file not found: {put_input_path}")
    
    print("\n🎉 All option continuation strategies applied.")
