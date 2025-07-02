import pandas as pd
import numpy as np
import os

# --- CONFIGURATION ---
PROXIMITY_PERCENT = 0.05

def apply_zone_invalidation_filter(date_dir_path):
    """
    Applies a "Zone Invalidation" filter. A bias is set by testing a boundary
    and is invalidated once the price closes past the next pivot level.
    """
    file_path = os.path.join(date_dir_path, 'tradeview_utc_output.csv')

    print(f"\n--- Applying 'Zone Invalidation' Filter in: {date_dir_path} ---")

    if not os.path.exists(file_path):
        print(f"⚠️  Warning: '{file_path}' not found. Skipping.")
        return

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"❌ Error reading file {file_path}: {e}")
        return

    if 'Call' not in df.columns or 'Put' not in df.columns or 'high' not in df.columns or 'low' not in df.columns:
        print(f"⚠️  Warning: Missing required columns in {file_path}. Skipping.")
        return

    # --- "ZONE INVALIDATION" LOGIC ---
    ALL_PIVOT_LEVELS = [
        'Daily Pivot', 'Daily BC', 'Daily TC', 'Daily R1', 'Daily R2', 'Daily R3', 'Daily R4',
        'Daily S1', 'Daily S2', 'Daily S3', 'Daily S4', 'Prev Day High', 'Prev Day Low'
    ]
    
    existing_pivot_levels = [p for p in ALL_PIVOT_LEVELS if p in df.columns]

    df['call_filtered'] = 0
    df['put_filtered'] = 0
    df['reason'] = ''
    df['market_bias'] = 'NEUTRAL'

    print(f"Proximity zone set to: {PROXIMITY_PERCENT}%")

    # --- State Machine Variables ---
    current_market_bias = 'NEUTRAL'
    # This will store the pivot level that must be broken to reset the bias
    invalidation_level = None

    for idx, row in df.iterrows():
        close_price = row['close']
        candle_high = row['high']
        candle_low = row['low']
        
        level_values = {name: row[name] for name in existing_pivot_levels if pd.notna(row[name])}
        
        # --- 1. CHECK FOR ZONE INVALIDATION (RESET TO NEUTRAL) ---
        if current_market_bias == 'BEARISH_BIAS' and invalidation_level is not None:
            if close_price < invalidation_level:
                current_market_bias = 'NEUTRAL'
                invalidation_level = None
        elif current_market_bias == 'BULLISH_BIAS' and invalidation_level is not None:
            if close_price > invalidation_level:
                current_market_bias = 'NEUTRAL'
                invalidation_level = None

        # --- 2. CHECK FOR NEW ZONE TRIGGER (ONLY IF NEUTRAL) ---
        if current_market_bias == 'NEUTRAL':
            levels_below = {name: val for name, val in level_values.items() if val < close_price}
            levels_above = {name: val for name, val in level_values.items() if val > close_price}
            
            immediate_support_value = max(levels_below.values()) if levels_below else None
            immediate_resistance_value = min(levels_above.values()) if levels_above else None

            is_testing_resistance = False
            if immediate_resistance_value is not None:
                if (candle_high >= immediate_resistance_value * (1 - PROXIMITY_PERCENT / 100)):
                    is_testing_resistance = True
            
            is_testing_support = False
            if immediate_support_value is not None:
                if (candle_low <= immediate_support_value * (1 + PROXIMITY_PERCENT / 100)):
                    is_testing_support = True

            if is_testing_resistance:
                current_market_bias = 'BEARISH_BIAS'
                # The invalidation level is the highest pivot BELOW the one we just tested
                invalidation_level = max([v for v in level_values.values() if v < immediate_resistance_value], default=None)
            elif is_testing_support:
                current_market_bias = 'BULLISH_BIAS'
                # The invalidation level is the lowest pivot ABOVE the one we just tested
                invalidation_level = min([v for v in level_values.values() if v > immediate_support_value], default=None)

        # --- 3. APPLY THE FILTER BASED ON THE FINAL BIAS ---
        df.loc[idx, 'market_bias'] = current_market_bias
        
        if current_market_bias == 'BULLISH_BIAS' and row['Call'] == 1:
            df.loc[idx, 'call_filtered'] = 1
            df.loc[idx, 'reason'] = 'Valid in Bullish Zone'
            
        elif current_market_bias == 'BEARISH_BIAS' and row['Put'] == 1:
            df.loc[idx, 'put_filtered'] = 1
            df.loc[idx, 'reason'] = 'Valid in Bearish Zone'

    # --- Reporting and Saving ---
    original_call_count = int(df['Call'].sum())
    filtered_call_count = int(df['call_filtered'].sum())
    original_put_count = int(df['Put'].sum())
    filtered_put_count = int(df['put_filtered'].sum())

    print(f"Original Calls: {original_call_count} -> Filtered Calls: {filtered_call_count}")
    print(f"Original Puts: {original_put_count} -> Filtered Puts: {filtered_put_count}")

    filtered_calls_df = df[df['call_filtered'] == 1]
    filtered_puts_df = df[df['put_filtered'] == 1]

    if not filtered_calls_df.empty:
        print("\n  Tradable Call Signals Found:")
        print(filtered_calls_df[['datetime', 'close', 'reason']].to_string(index=False))
    
    if not filtered_puts_df.empty:
        print("\n  Tradable Put Signals Found:")
        print(filtered_puts_df[['datetime', 'close', 'reason']].to_string(index=False))

    try:
        df.to_csv(file_path, index=False)
        print(f"\n✅ Filter results saved by updating {file_path}")
    except Exception as e:
        print(f"❌ Error saving updated file {file_path}: {e}")


def main():
    base_data_dir = 'data'
    if not os.path.isdir(base_data_dir):
        print(f"❌ Error: Base directory '{base_data_dir}' not found.")
        return
    try:
        subdirectories = [d for d in os.listdir(base_data_dir) if os.path.isdir(os.path.join(base_data_dir, d))]
    except Exception as e:
        print(f"❌ Error reading directories from '{base_data_dir}': {e}")
        return
    if not subdirectories:
        print(f"ℹ️ No subdirectories found in '{base_data_dir}'. Nothing to process.")
        return
    print(f"Found {len(subdirectories)} date directories to process.")
    for dir_name in sorted(subdirectories):
        full_path = os.path.join(base_data_dir, dir_name)
        apply_zone_invalidation_filter(full_path)
    print("\n🎉 All filtering complete.")


if __name__ == "__main__":
    main()