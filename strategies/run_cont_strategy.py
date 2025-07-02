# nifty_option_trading/strategies/run_cont_strategy.py

import pandas as pd
import numpy as np
import os

def apply_continuation_strategy_to_directory(date_dir_path):
    """
    Applies the continuation strategy with consistent N+1 signal shifting.
    UPDATED: Implements the same N+1 logic as in run_rev_strategy.py to ensure
    signals are consistently shifted to the next candle.
    """
    input_file = os.path.join(date_dir_path, 'tradeview_utc.csv')
    output_file = os.path.join(date_dir_path, 'tradeview_utc_output.csv')

    print(f"\n--- Applying Continuation Strategy in: {date_dir_path} ---")

    if not os.path.exists(input_file):
        print(f"⚠️  Warning: Base data file '{input_file}' not found. Skipping.")
        return
    
    df = pd.read_csv(input_file, parse_dates=['datetime'])

    # --- Base Calculations ---
    df.rename(columns={'%R': 'williamsRFast', '%R.1': 'williamsRSlow', 'K': 'stochRSIK', 'D': 'stochRSID', 'Up Trend': 'supertrend_up', 'Down Trend': 'supertrend_down'}, inplace=True)
    if 'supertrend_up' in df.columns and 'supertrend_down' in df.columns:
        df['supertrend'] = df['supertrend_up'].combine_first(df['supertrend_down'])
        df['direction'] = np.where(df['supertrend_up'].notna(), -1, 1)
    else:
        print("⚠️  Warning: Supertrend columns not found. Cannot determine direction.")
        return
    
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
        # Create a new output DataFrame if the file doesn't exist
        output_df = df[['datetime', 'open', 'high', 'low', 'close', 'Daily Pivot', 'Daily BC', 'Daily TC', 
                        'Daily R1', 'Daily R2', 'Daily R3', 'Daily R4', 'Daily S1', 'Daily S2', 
                        'Daily S3', 'Daily S4', 'Prev Day High', 'Prev Day Low']].copy()
        output_df.set_index('datetime', inplace=True)
        output_df['Call'] = 0
        output_df['Put'] = 0
        output_df['Call Comments'] = ''
        output_df['Put Comments'] = ''
    
    # --- IMPROVED N+1 LOGIC: Consistent with run_rev_strategy.py ---
    # Create a mapping from index to datetime for easier reference
    index_to_datetime = dict(zip(range(len(df)), df['datetime']))
    
    # Get indices where signals are True
    call_signal_indices = df[df['callEntrySignal']].index.tolist()
    put_signal_indices = df[df['putEntrySignal']].index.tolist()
    
    # Get the next candle's datetime for each signal
    call_signal_times = []
    put_signal_times = []
    
    for idx in call_signal_indices:
        if idx + 1 < len(df):
            call_signal_times.append(index_to_datetime[idx + 1])
            print(f"Call signal at {index_to_datetime[idx]} -> Trade at {index_to_datetime[idx + 1]}")
    
    for idx in put_signal_indices:
        if idx + 1 < len(df):
            put_signal_times.append(index_to_datetime[idx + 1])
            print(f"Put signal at {index_to_datetime[idx]} -> Trade at {index_to_datetime[idx + 1]}")

    # Apply signals to the output DataFrame
    output_df.loc[call_signal_times, 'Call'] = 1
    output_df.loc[put_signal_times, 'Put'] = 1
    
    # Update comments
    for time in call_signal_times:
        if time in output_df.index:
            current_comment = output_df.loc[time, 'Call Comments']
            output_df.loc[time, 'Call Comments'] = 'Continuation' if pd.isna(current_comment) or current_comment == '' else f"{current_comment};Continuation"
    
    for time in put_signal_times:
        if time in output_df.index:
            current_comment = output_df.loc[time, 'Put Comments']
            output_df.loc[time, 'Put Comments'] = 'Continuation' if pd.isna(current_comment) or current_comment == '' else f"{current_comment};Continuation"

    output_df.to_csv(output_file, index=True)
    print(f"✅ Continuation strategy output saved to {output_file}")
    print(f"   Continuation Call signals found: {len(call_signal_times)}")
    print(f"   Continuation Put signals found: {len(put_signal_times)}")

def generate_continuation_strategies():
    base_data_dir = 'data'
    if not os.path.isdir(base_data_dir):
        print(f"❌ Error: Base directory '{base_data_dir}' not found.")
        return
    subdirectories = [d for d in os.listdir(base_data_dir) if os.path.isdir(os.path.join(base_data_dir, d))]
    if not subdirectories:
        print(f"ℹ️ No subdirectories found in '{base_data_dir}'.")
        return
    print(f"Found {len(subdirectories)} directories to process for continuation strategy: {sorted(subdirectories)}")
    for dir_name in sorted(subdirectories):
        apply_continuation_strategy_to_directory(os.path.join(base_data_dir, dir_name))
    print("\n🎉 All continuation strategies applied.")