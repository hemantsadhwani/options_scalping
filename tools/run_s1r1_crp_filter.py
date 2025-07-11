import pandas as pd
import os

def filter_signals_in_cpr_band_improved(date_dir_path: str):
    """
    Filters signals in both continuation and reversal output files to keep only those within the CPR band.
    Modifies the original files in-place by setting filtered signals to 0.

    The CPR Band is defined as:
    - Top of zone = max(Daily R1, Prev Day High)
    - Bottom of zone = min(Daily S1, Prev Day Low)
    
    Args:
        date_dir_path (str): Path to the date directory containing the strategy output files.
    """
    cont_file = os.path.join(date_dir_path, 'tradeview_cont_output.csv')
    rev_file = os.path.join(date_dir_path, 'tradeview_rev_output.csv')
    
    print(f"\n--- CPR Band Filtering for {os.path.basename(date_dir_path)} ---")
    
    total_original_calls = 0
    total_original_puts = 0
    total_filtered_calls = 0
    total_filtered_puts = 0
    
    # Process continuation file
    if os.path.exists(cont_file):
        print(f"Processing continuation file: {cont_file}")
        cont_stats = process_file_for_cpr_filtering(cont_file, ['Call', 'Put'])
        total_original_calls += cont_stats['original_calls']
        total_original_puts += cont_stats['original_puts']
        total_filtered_calls += cont_stats['filtered_calls']
        total_filtered_puts += cont_stats['filtered_puts']
    else:
        print(f"Continuation file not found: {cont_file}")
    
    # Process reversal file
    if os.path.exists(rev_file):
        print(f"Processing reversal file: {rev_file}")
        rev_stats = process_file_for_cpr_filtering(rev_file, ['Call', 'Put', 'Call_v2', 'Put_v2'])
        total_original_calls += rev_stats['original_calls']
        total_original_puts += rev_stats['original_puts']
        total_filtered_calls += rev_stats['filtered_calls']
        total_filtered_puts += rev_stats['filtered_puts']
    else:
        print(f"Reversal file not found: {rev_file}")
    
    # Print combined analytics
    calls_dropped = total_original_calls - total_filtered_calls
    puts_dropped = total_original_puts - total_filtered_puts
    calls_dropped_pct = (calls_dropped / total_original_calls * 100) if total_original_calls > 0 else 0
    puts_dropped_pct = (puts_dropped / total_original_puts * 100) if total_original_puts > 0 else 0
    
    print(f"Combined Results for {os.path.basename(date_dir_path)}:")
    print(f"  Original: {total_original_calls} calls, {total_original_puts} puts")
    print(f"  Dropped: {calls_dropped} calls ({calls_dropped_pct:.1f}%), {puts_dropped} puts ({puts_dropped_pct:.1f}%)")
    print(f"  Remaining: {total_filtered_calls} calls, {total_filtered_puts} puts")

def process_file_for_cpr_filtering(file_path: str, signal_columns: list):
    """
    Process a single file for CPR filtering.
    
    Args:
        file_path (str): Path to the file to process
        signal_columns (list): List of signal columns to filter
    
    Returns:
        dict: Statistics about the filtering process
    """
    # Read the file
    df = pd.read_csv(file_path)
    
    # Ensure required columns exist
    required_cols = ['Daily R1', 'Prev Day High', 'Daily S1', 'Prev Day Low', 'close']
    if not all(col in df.columns for col in required_cols):
        print(f"Error: File {file_path} must contain the following columns: {required_cols}")
        return {'original_calls': 0, 'original_puts': 0, 'filtered_calls': 0, 'filtered_puts': 0}
    
    # Check which signal columns actually exist in the file
    existing_signal_cols = [col for col in signal_columns if col in df.columns]
    if not existing_signal_cols:
        print(f"Warning: No signal columns found in {file_path}")
        return {'original_calls': 0, 'original_puts': 0, 'filtered_calls': 0, 'filtered_puts': 0}
    
    # Count original signals
    original_calls = sum(df[col].sum() for col in existing_signal_cols if 'Call' in col)
    original_puts = sum(df[col].sum() for col in existing_signal_cols if 'Put' in col)
    
    # Calculate CPR band boundaries
    df['Top_Zone'] = df[['Daily R1', 'Prev Day High']].max(axis=1)
    df['Bottom_Zone'] = df[['Daily S1', 'Prev Day Low']].min(axis=1)
    
    # Define the condition for when a signal should be dropped (outside the band)
    condition_to_drop = (df['close'] > df['Top_Zone']) | (df['close'] < df['Bottom_Zone'])
    
    # Filter signals - set signal columns to 0 if condition is met
    df.loc[condition_to_drop, existing_signal_cols] = 0
    
    # Count filtered signals
    filtered_calls = sum(df[col].sum() for col in existing_signal_cols if 'Call' in col)
    filtered_puts = sum(df[col].sum() for col in existing_signal_cols if 'Put' in col)
    
    # Drop temporary helper columns
    df_to_save = df.drop(columns=['Top_Zone', 'Bottom_Zone'])
    
    # Save the filtered file back (in-place modification)
    df_to_save.to_csv(file_path, index=False)
    
    calls_dropped = original_calls - filtered_calls
    puts_dropped = original_puts - filtered_puts
    calls_dropped_pct = (calls_dropped / original_calls * 100) if original_calls > 0 else 0
    puts_dropped_pct = (puts_dropped / original_puts * 100) if original_puts > 0 else 0
    
    print(f"  {os.path.basename(file_path)}: {existing_signal_cols}")
    print(f"    Dropped: {calls_dropped} calls ({calls_dropped_pct:.1f}%), {puts_dropped} puts ({puts_dropped_pct:.1f}%)")
    
    return {
        'original_calls': original_calls,
        'original_puts': original_puts,
        'filtered_calls': filtered_calls,
        'filtered_puts': filtered_puts
    }

# Legacy function for backward compatibility
def filter_signals_in_cpr_band(input_file: str, output_file: str):
    """
    Legacy function - now redirects to the improved version.
    Extracts date directory from input_file path and uses the new method.
    """
    date_dir_path = os.path.dirname(input_file)
    filter_signals_in_cpr_band_improved(date_dir_path)
