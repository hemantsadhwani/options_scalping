# nifty_option_trading/run_process_data.py

import pandas as pd
import os
from datetime import datetime

def process_nifty_file(date_dir_path, expected_date):
    """
    Reads NSE_NIFTY.csv from a specific date directory, validates the data against
    the expected date, processes it, and saves the output in the same directory.
    """
    input_file = os.path.join(date_dir_path, 'NSE_NIFTY.csv')
    output_file = os.path.join(date_dir_path, 'tradeview_utc.csv')

    print(f"--- Processing NIFTY file for date {expected_date} ---")

    if not os.path.exists(input_file):
        print(f"⚠️  Warning: '{input_file}' not found. Skipping.")
        return

    try:
        df = pd.read_csv(input_file)
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return

    required_columns = [
        'time', 'open', 'high', 'low', 'close', 'Daily Pivot', 'Daily BC', 'Daily TC',
        'Daily R1', 'Daily R2', 'Daily R3', 'Daily R4', 'Daily S1', 'Daily S2', 
        'Daily S3', 'Daily S4', 'Prev Day High', 'Prev Day Low', 'EMA', 
        'Up Trend', 'Down Trend', 'K', 'D', '%R', '%R.1'
    ]
    
    existing_columns = [col for col in required_columns if col in df.columns]
    df_filtered = df[existing_columns].copy()

    if 'time' not in df_filtered.columns:
        print("❌ Error: 'time' column not found. Cannot process this file.")
        return
    
    df_filtered = df_filtered[df_filtered['time'] != 'time'].reset_index(drop=True)

    try:
        df_filtered['time'] = pd.to_numeric(df_filtered['time'], errors='coerce')
        df_filtered['datetime'] = pd.to_datetime(df_filtered['time'], unit='s', utc=True).dt.tz_convert('Asia/Kolkata')
    except Exception as e:
        print(f"⚠️  Warning: Could not convert timestamps: {e}")
        return

    original_rows = len(df_filtered)
    df_filtered['date_only'] = df_filtered['datetime'].dt.date
    df_filtered = df_filtered[df_filtered['date_only'] == expected_date].copy()
    validated_rows = len(df_filtered)
    
    print(f"✅ Validating NIFTY data for {expected_date}: Kept {validated_rows} of {original_rows} records.")

    if validated_rows == 0:
        print(f"⚠️  Warning: No NIFTY records found for the date {expected_date} in this file.")
        return

    df_filtered['datetime'] = df_filtered['datetime'].dt.tz_localize(None)
    df_filtered = df_filtered.drop(columns=['date_only'])
    
    numeric_columns = [col for col in df_filtered.columns if col not in ['time', 'datetime']]
    for col in numeric_columns:
        df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce')

    df_filtered = df_filtered.sort_values('datetime').reset_index(drop=True)
    
    value_columns = [col for col in df_filtered.columns if col not in ['time', 'datetime']]
    df_filtered = df_filtered.dropna(subset=value_columns, how='all')

    print(f"Final NIFTY data shape: {df_filtered.shape}")

    try:
        df_filtered.to_csv(output_file, index=False)
        print(f"✅ NIFTY data saved to {output_file}")
    except Exception as e:
        print(f"❌ Error saving file: {e}")


def process_option_file(option_dir_path, expected_date, option_type):
    """
    Processes the first raw CSV file found in a 'call' or 'put' directory,
    filters by date, selects specific columns, and saves the output.
    It now explicitly ignores files ending in '_out.csv'.
    """
    print(f"--- Processing {option_type.upper()} options in: {os.path.basename(os.path.dirname(option_dir_path))}/{option_type} ---")

    try:
        # --- THIS IS THE FIX ---
        # Only look for CSVs that are NOT the output files from a previous run.
        csv_files = [f for f in os.listdir(option_dir_path) if f.lower().endswith('.csv') and not f.lower().endswith('_out.csv')]
        if not csv_files:
            print(f"ℹ️ Info: No raw CSV file found in '{option_dir_path}'. Skipping.")
            return
        input_file = os.path.join(option_dir_path, csv_files[0])
    except Exception as e:
        print(f"❌ Error finding CSV file in {option_dir_path}: {e}")
        return

    output_file = os.path.join(option_dir_path, f'{option_type}_out.csv')

    try:
        df = pd.read_csv(input_file)
    except Exception as e:
        print(f"❌ Error reading file '{input_file}': {e}")
        return

    if 'time' not in df.columns:
        print(f"❌ Error: 'time' column not found in '{input_file}'. Cannot process.")
        return

    df = df[df['time'] != 'time'].reset_index(drop=True)
    try:
        df['time'] = pd.to_numeric(df['time'], errors='coerce')
        df['datetime'] = pd.to_datetime(df['time'], unit='s', utc=True).dt.tz_convert('Asia/Kolkata')
    except Exception as e:
        print(f"⚠️  Warning: Could not convert timestamps in '{input_file}': {e}")
        return

    original_rows = len(df)
    df['date_only'] = df['datetime'].dt.date
    df = df[df['date_only'] == expected_date].copy()
    validated_rows = len(df)

    print(f"✅ Validating {option_type.upper()} data for {expected_date}: Kept {validated_rows} of {original_rows} records.")

    if validated_rows == 0:
        print(f"⚠️  Warning: No {option_type.upper()} records found for {expected_date} in '{input_file}'.")
        return

    output_columns = ['datetime', 'open', 'high', 'low', 'close', 'K', 'D', '%R']
    
    existing_output_columns = [col for col in output_columns if col in df.columns]
    missing_cols = set(output_columns) - set(existing_output_columns)
    if missing_cols:
        print(f"⚠️  Warning: Missing required columns in '{input_file}': {', '.join(missing_cols)}")

    if 'datetime' not in existing_output_columns:
        print(f"❌ Error: 'datetime' column could not be created or is missing. Cannot proceed.")
        return

    df_out = df[existing_output_columns].copy()
    df_out['datetime'] = df_out['datetime'].dt.tz_localize(None)
    df_out = df_out.sort_values('datetime').reset_index(drop=True)

    try:
        df_out.to_csv(output_file, index=False)
        print(f"✅ {option_type.upper()} data saved to {output_file}")
    except Exception as e:
        print(f"❌ Error saving file '{output_file}': {e}")


def run_process_data():
    """
    Main function to find and process all DDMM subdirectories, including call/put options.
    """
    base_data_dir = 'data'
    
    if not os.path.isdir(base_data_dir):
        print(f"❌ Error: Base directory '{base_data_dir}' not found.")
        return

    subdirectories = [d for d in os.listdir(base_data_dir) if os.path.isdir(os.path.join(base_data_dir, d))]

    if not subdirectories:
        print(f"ℹ️ No subdirectories found in '{base_data_dir}'.")
        return

    print(f"Found {len(subdirectories)} potential directories. Processing valid DDMM folders...")
    
    current_year = datetime.now().year
    processed_count = 0

    for dir_name in sorted(subdirectories):
        if len(dir_name) == 4 and dir_name.isdigit():
            try:
                day = int(dir_name[0:2])
                month = int(dir_name[2:4])
                expected_date = datetime(current_year, month, day).date()
                
                date_dir_path = os.path.join(base_data_dir, dir_name)
                print(f"\n--- Processing directory: {date_dir_path} for date {expected_date} ---")

                process_nifty_file(date_dir_path, expected_date)

                for option_type in ['call', 'put']:
                    option_dir_path = os.path.join(date_dir_path, option_type)
                    if os.path.isdir(option_dir_path):
                        process_option_file(option_dir_path, expected_date, option_type)

                processed_count += 1

            except ValueError:
                print(f"\n⚠️  Skipping '{dir_name}': Not a valid DDMM date format.")
        else:
            print(f"\n⚠️  Skipping '{dir_name}': Does not match DDMM format.")
    
    print(f"\n🎉 All done. Processed {processed_count} directories.")