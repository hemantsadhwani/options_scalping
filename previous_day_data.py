import os
import pandas as pd
import re

# The base directory where all the date-stamped folders are located.
base_data_dir = 'data'

print(f"Starting processing in base directory: {base_data_dir}")

# Check if the base data directory exists.
if not os.path.isdir(base_data_dir):
    print(f"Error: Base directory '{base_data_dir}' not found.")
    exit()

# Loop through each item in the base data directory.
for date_folder in os.listdir(base_data_dir):
    # Construct the full path to the potential date folder.
    current_dir_path = os.path.join(base_data_dir, date_folder)

    # Process only if it's a directory.
    if os.path.isdir(current_dir_path):
        print(f"\n--- Processing directory: {current_dir_path} ---")

        # Define the full paths for the input and output files.
        csv_file = os.path.join(current_dir_path, 'NSE_NIFTY.csv')
        close_file = os.path.join(current_dir_path, 'close.txt')
        output_file = os.path.join(current_dir_path, 'previous_day_data.txt')

        # Check if both required source files exist in the directory.
        if not os.path.exists(csv_file) or not os.path.exists(close_file):
            print(f"Skipping: Required file(s) not found in {current_dir_path}")
            continue

        try:
            # 1 & 2: Read NSE_NIFTY.csv and get previous day's high and low.
            df = pd.read_csv(csv_file)
            # Taking the last row for the most recent data in the file.
            prev_day_high = df['Prev Day High'].iloc[-1]
            prev_day_low = df['Prev Day Low'].iloc[-1]

            # 3: Read close.txt to get the close price.
            with open(close_file, 'r') as f:
                content = f.read()
                match = re.search(r'close:\s*([\d.]+)', content)
                if match:
                    close_price = match.group(1)
                else:
                    print(f"Warning: 'close:' value not found in {close_file}. Skipping.")
                    continue
            
            # 4: Construct previous_day_data.txt in the specified format.
            with open(output_file, 'w') as f:
                f.write(f"high: {prev_day_high}\n")
                f.write(f"low: {prev_day_low}\n")
                f.write(f"close: {close_price}\n")
            
            print(f"Successfully created: {output_file}")

        except Exception as e:
            print(f"An error occurred while processing {current_dir_path}: {e}")

print("\n--- All directories processed. ---")