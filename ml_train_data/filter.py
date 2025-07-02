import pandas as pd
import numpy as np

# Load the enriched data file
try:
    df = pd.read_csv("ml_data_enriched.csv")
    print("Loaded 'ml_data_enriched.csv' successfully.")
except FileNotFoundError:
    print("Error: 'ml_data_enriched.csv' not found. Please ensure it exists.")
    exit()

# --- 1. Create the Binary Target Variable ---
conditions = [
    df['exit_reason'].str.contains("Target Profit", na=False),
    df['exit_reason'].str.contains("Stop Loss", na=False)
]
outcomes = [1, 0] # 1 for Profit, 0 for Loss
df['target'] = np.select(conditions, outcomes, default=np.nan)

# Clean up rows and data type
original_rows = len(df)
df.dropna(subset=['target'], inplace=True)
df['target'] = df['target'].astype(int)
print(f"Created 'target' column. Kept {len(df)} rows out of {original_rows}.")

# --- 2. Select the Revised Feature Columns ---
# Including 'type' and 'comments', and removing 'Call' and 'Put'
feature_columns = [
    'type', 'comments',             # Added as requested
    'open', 'high', 'low', 'close',
    'Daily Pivot', 'Daily BC', 'Daily TC',
    'Daily R1', 'Daily R2', 'Daily R3', 'Daily R4',
    'Daily S1', 'Daily S2', 'Daily S3', 'Daily S4',
    'Prev Day High', 'Prev Day Low'
]

# Ensure all desired feature columns exist in the dataframe
existing_features = [col for col in feature_columns if col in df.columns]

# --- 3. Create and Save the Final DataFrame ---
final_ml_df = df[existing_features + ['target']]

output_filename = 'ml_training_data_revised.csv'
final_ml_df.to_csv(output_filename, index=False)

print(f"\nSuccessfully created '{output_filename}' with the revised features.")
print("\n### Preview of the Revised ML-Ready Data ###")
print(final_ml_df.head())
print(f"\nFinal data shape: {final_ml_df.shape}")
print(f"Columns ({final_ml_df.shape[1]}): {final_ml_df.columns.tolist()}")