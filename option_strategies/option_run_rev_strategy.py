# option_strategies/option_run_rev_strategy.py

import pandas as pd
import numpy as np
import os

def apply_reversal_strategy_to_directory_options(date_dir_path, input_filename, output_filename):
    """
    Applies the reversal strategy for option buying (long-only signals).
    For call option files: only generates Call signals (long call options)
    For put option files: only generates Put signals (long put options)
    """
    input_file_for_calcs = os.path.join(date_dir_path, input_filename)
    output_file_to_update = os.path.join(date_dir_path, output_filename)

    print(f"\n--- Applying Option Reversal Strategy in: {date_dir_path} on {input_filename} ---")

    # Check if input file exists
    if not os.path.exists(input_file_for_calcs):
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

    df = pd.read_csv(input_file_for_calcs, parse_dates=['datetime'])
    
    # Load or create the output file
    if os.path.exists(output_file_to_update):
        output_df = pd.read_csv(output_file_to_update, parse_dates=['datetime'], index_col='datetime')
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

    # --- Calculations using integer index ---
    df.rename(columns={'%R': 'williamsRFast', '%R.1': 'williamsRSlow', 'K': 'stochRSIK', 'D': 'stochRSID'}, inplace=True)
    def crossover(s1, s2): return (s1 > s2) & (s1.shift(1) <= s2.shift(1))
    def crossunder(s1, s2): return (s1 < s2) & (s1.shift(1) >= s2.shift(1))
    WAIT_BULL_BARS_WILLIAMS, WAIT_BEAR_BARS_WILLIAMS = 4, 5
    WAIT_BULL_BARS_STOCH, WAIT_BEAR_BARS_STOCH = 2, 2
    threshold_80, threshold_20 = pd.Series(-80, index=df.index), pd.Series(-20, index=df.index)
    df['williamsRFastBullishCrossover'], df['williamsRSlowBullishCrossover'] = crossover(df['williamsRFast'], threshold_80), crossover(df['williamsRSlow'], threshold_80)
    df['williamsRFastBearishCrossover'], df['williamsRSlowBearishCrossover'] = crossunder(df['williamsRFast'], threshold_20), crossunder(df['williamsRSlow'], threshold_20)
    df['williamsBearishCrossoverComplete'], df['williamsBullishCrossoverComplete'] = False, False
    df['williamsBearishCrossoverCompleteBarIndex'], df['williamsBullishCrossoverCompleteBarIndex'] = np.nan, np.nan
    bearishCrossoverDetected, bullishCrossoverDetected = False, False
    bearishCrossoverBarIndex, bullishCrossoverBarIndex = None, None
    williamsBearishCrossoverComplete, williamsBullishCrossoverComplete = False, False
    williamsBearishCrossoverCompleteBarIndex, williamsBullishCrossoverCompleteBarIndex = None, None
    
    for i in range(len(df)):
        # Only process relevant crossovers based on option type
        if is_put_option_file:
            # For put options, use BULLISH crossovers (put buying opportunities when underlying reverses up)
            if df.at[i, 'williamsRFastBullishCrossover']: 
                bullishCrossoverDetected, bullishCrossoverBarIndex, williamsBullishCrossoverComplete = True, i, False
            if bullishCrossoverDetected and df.at[i, 'williamsRSlowBullishCrossover'] and i <= bullishCrossoverBarIndex + WAIT_BULL_BARS_WILLIAMS: 
                williamsBullishCrossoverComplete, williamsBullishCrossoverCompleteBarIndex = True, i
            if bullishCrossoverDetected and i > bullishCrossoverBarIndex + WAIT_BULL_BARS_WILLIAMS and not williamsBullishCrossoverComplete: 
                bullishCrossoverDetected, bullishCrossoverBarIndex = False, None
        
        elif is_call_option_file:
            # For call options, only process bullish crossovers (call buying opportunities)
            if df.at[i, 'williamsRFastBullishCrossover']: 
                bullishCrossoverDetected, bullishCrossoverBarIndex, williamsBullishCrossoverComplete = True, i, False
            if bullishCrossoverDetected and df.at[i, 'williamsRSlowBullishCrossover'] and i <= bullishCrossoverBarIndex + WAIT_BULL_BARS_WILLIAMS: 
                williamsBullishCrossoverComplete, williamsBullishCrossoverCompleteBarIndex = True, i
            if bullishCrossoverDetected and i > bullishCrossoverBarIndex + WAIT_BULL_BARS_WILLIAMS and not williamsBullishCrossoverComplete: 
                bullishCrossoverDetected, bullishCrossoverBarIndex = False, None
        
        df.at[i, 'williamsBearishCrossoverComplete'] = williamsBearishCrossoverComplete
        df.at[i, 'williamsBearishCrossoverCompleteBarIndex'] = williamsBearishCrossoverCompleteBarIndex if williamsBearishCrossoverCompleteBarIndex is not None else np.nan
        df.at[i, 'williamsBullishCrossoverComplete'] = williamsBullishCrossoverComplete
        df.at[i, 'williamsBullishCrossoverCompleteBarIndex'] = williamsBullishCrossoverCompleteBarIndex if williamsBullishCrossoverCompleteBarIndex is not None else np.nan
    
    df['stochCallEntryCondition'] = (df['stochRSIK'] > df['stochRSID']) & (df['stochRSIK'] > 20)
    df['stochPutEntryCondition'] = (df['stochRSID'] > df['stochRSIK']) & (df['stochRSIK'] < 80)
    df['williamsStillBullish'] = (df['williamsRFast'] > -80) & (df['williamsRSlow'] > -80)
    df['williamsStillBearish'] = (df['williamsRFast'] < -20) & (df['williamsRSlow'] < -20)
    
    # Calculate crossovers based on option type
    if is_call_option_file:
        # For call options, only calculate bullish crossovers
        df['bullishCrossover'] = (
            df['williamsBullishCrossoverComplete'] & 
            df['stochCallEntryCondition'] & 
            (df.index <= df['williamsBullishCrossoverCompleteBarIndex'] + WAIT_BULL_BARS_STOCH) & 
            df['williamsStillBullish']
        )
        df['bearishCrossover'] = False  # No bearish crossovers for call options
        
        # Detect entry signals (first occurrence of crossover)
        df['callEntrySignal'] = df['bullishCrossover'] & (~df['bullishCrossover'].shift(1, fill_value=False))
        df['putEntrySignal'] = False  # No put signals for call options
        
    elif is_put_option_file:
        # For put options, use BULLISH crossovers (put buying when underlying reverses up)
        df['bullishCrossover'] = (
            df['williamsBullishCrossoverComplete'] & 
            df['stochCallEntryCondition'] &  # Use call entry condition for put buying
            (df.index <= df['williamsBullishCrossoverCompleteBarIndex'] + WAIT_BULL_BARS_STOCH) & 
            df['williamsStillBullish']  # Use bullish condition for put buying
        )
        df['bearishCrossover'] = False  # No bearish crossovers for put options
        
        # Detect entry signals (first occurrence of crossover)
        df['putEntrySignal'] = df['bullishCrossover'] & (~df['bullishCrossover'].shift(1, fill_value=False))
        df['callEntrySignal'] = False  # No call signals for put options

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

    # Save the updated output
    output_df.to_csv(output_file_to_update, index=True)
    print(f"✅ Option Reversal strategy output updated in {output_file_to_update}")
    print(f"   {signal_type} option signals found: {len(signal_times)} (Long {signal_type} options only)")

def generate_reversal_strategies_options(call_input_filename='call/call_out.csv', call_output_filename='call/call_rev_out.csv', put_input_filename='put/put_out.csv', put_output_filename='put/put_rev_out.csv'):
    """
    Generates reversal strategies specifically for option buying.
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
    
    print(f"Found {len(subdirectories)} directories to process for option reversal strategy: {sorted(subdirectories)}")
    
    for dir_name in sorted(subdirectories):
        date_dir_path = os.path.join(base_data_dir, dir_name)
        
        # Process call options
        call_input_path = os.path.join(date_dir_path, call_input_filename)
        if os.path.exists(call_input_path):
            apply_reversal_strategy_to_directory_options(date_dir_path, call_input_filename, call_output_filename)
        else:
            print(f"⚠️  Call option file not found: {call_input_path}")
        
        # Process put options
        put_input_path = os.path.join(date_dir_path, put_input_filename)
        if os.path.exists(put_input_path):
            apply_reversal_strategy_to_directory_options(date_dir_path, put_input_filename, put_output_filename)
        else:
            print(f"⚠️  Put option file not found: {put_input_path}")
    
    print("\n🎉 All option reversal strategies applied.")
