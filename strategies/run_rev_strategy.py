import pandas as pd
import numpy as np
import os

def apply_reversal_strategy_to_directory(date_dir_path):
    """
    Applies the reversal strategy with consistent signal shifting.
    """
    input_file_for_calcs = os.path.join(date_dir_path, 'tradeview_utc.csv')
    output_file_to_update = os.path.join(date_dir_path, 'tradeview_rev_output.csv')

    print(f"\n--- Applying Reversal Strategy in: {date_dir_path} ---")

    # Check if input file exists
    if not os.path.exists(input_file_for_calcs):
        print(f"⚠️  Warning: Missing input file in {date_dir_path}. Skipping.")
        return

    df = pd.read_csv(input_file_for_calcs, parse_dates=['datetime'])
    
    # Load or create the output file
    if os.path.exists(output_file_to_update):
        output_df = pd.read_csv(output_file_to_update, parse_dates=['datetime'], index_col='datetime')
    else:
        # Create new output file if it doesn't exist (without comments columns)
        output_df = df[['datetime', 'open', 'high', 'low', 'close', 'Daily Pivot', 'Daily BC', 'Daily TC', 
                        'Daily R1', 'Daily R2', 'Daily R3', 'Daily R4', 'Daily S1', 'Daily S2', 
                        'Daily S3', 'Daily S4', 'Prev Day High', 'Prev Day Low']].copy()
        output_df.set_index('datetime', inplace=True)
        output_df['Call'] = 0
        output_df['Put'] = 0

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
        if df.at[i, 'williamsRFastBearishCrossover']: 
            bearishCrossoverDetected, bearishCrossoverBarIndex, williamsBearishCrossoverComplete = True, i, False
        if bearishCrossoverDetected and df.at[i, 'williamsRSlowBearishCrossover'] and i <= bearishCrossoverBarIndex + WAIT_BEAR_BARS_WILLIAMS: 
            williamsBearishCrossoverComplete, williamsBearishCrossoverCompleteBarIndex = True, i
        if bearishCrossoverDetected and i > bearishCrossoverBarIndex + WAIT_BEAR_BARS_WILLIAMS and not williamsBearishCrossoverComplete: 
            bearishCrossoverDetected, bearishCrossoverBarIndex = False, None
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
    
    # Calculate bullish and bearish crossovers
    df['bullishCrossover'] = (
        df['williamsBullishCrossoverComplete'] & 
        df['stochCallEntryCondition'] & 
        (df.index <= df['williamsBullishCrossoverCompleteBarIndex'] + WAIT_BULL_BARS_STOCH) & 
        df['williamsStillBullish']
    )
    
    df['bearishCrossover'] = (
        df['williamsBearishCrossoverComplete'] & 
        df['stochPutEntryCondition'] & 
        (df.index <= df['williamsBearishCrossoverCompleteBarIndex'] + WAIT_BEAR_BARS_STOCH) & 
        df['williamsStillBearish']
    )
    
    # Detect entry signals (first occurrence of crossover)
    df['callEntrySignal'] = df['bullishCrossover'] & (~df['bullishCrossover'].shift(1, fill_value=False))
    df['putEntrySignal'] = df['bearishCrossover'] & (~df['bearishCrossover'].shift(1, fill_value=False))

    # --- CORRECTED SIGNAL TIMING LOGIC ---
    # Create a mapping from index to datetime for easier reference
    index_to_datetime = dict(zip(range(len(df)), df['datetime']))
    
    # Get indices where signals are True
    call_signal_indices = df[df['callEntrySignal']].index.tolist()
    put_signal_indices = df[df['putEntrySignal']].index.tolist()
    
    # Get the current candle's datetime for each signal
    call_signal_times = []
    put_signal_times = []
    
    for idx in call_signal_indices:
        call_signal_times.append(index_to_datetime[idx])
        print(f"Call signal at {index_to_datetime[idx]} -> Trade at {index_to_datetime[idx]}")
    
    for idx in put_signal_indices:
        put_signal_times.append(index_to_datetime[idx])
        print(f"Put signal at {index_to_datetime[idx]} -> Trade at {index_to_datetime[idx]}")

    # Apply signals to the output DataFrame
    output_df.loc[call_signal_times, 'Call'] = 1
    output_df.loc[put_signal_times, 'Put'] = 1

    # Save the updated output
    output_df.to_csv(output_file_to_update, index=True)
    print(f"✅ Reversal strategy output updated in {output_file_to_update}")
    print(f"   Reversal Call signals found: {len(call_signal_times)}")
    print(f"   Reversal Put signals found: {len(put_signal_times)}")

def generate_reversal_strategies():
    base_data_dir = 'data'
    if not os.path.isdir(base_data_dir):
        print(f"❌ Error: Base directory '{base_data_dir}' not found.")
        return
    subdirectories = [d for d in os.listdir(base_data_dir) if os.path.isdir(os.path.join(base_data_dir, d))]
    if not subdirectories:
        print(f"ℹ️ No subdirectories found in '{base_data_dir}'.")
        return
    print(f"Found {len(subdirectories)} directories to process for reversal strategy: {sorted(subdirectories)}")
    for dir_name in sorted(subdirectories):
        apply_reversal_strategy_to_directory(os.path.join(base_data_dir, dir_name))
    print("\n🎉 All reversal strategies applied.")
