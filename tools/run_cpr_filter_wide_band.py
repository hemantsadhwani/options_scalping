import pandas as pd
import numpy as np

def run_cpr_filter_wide_band(price_df, signals_df, trade_type_map, proximity_pct=0.04):
    """
    Applies CPR filtering for wide CPR bands (>50) with separate S1/PDL and R1/PDH zones.
    
    Args:
        price_df: DataFrame with price data and CPR levels
        signals_df: DataFrame with trading signals
        trade_type_map: Dictionary mapping signal columns to trade types
        proximity_pct: Percentage for zone width (default 3%)
    
    Returns:
        DataFrame with added CPR filter columns
    """
    
    # Ensure datetime columns are properly formatted
    price_df['datetime'] = pd.to_datetime(price_df['datetime'])
    signals_df['datetime'] = pd.to_datetime(signals_df['datetime'])
    
    # Get CPR levels from the first row
    daily_level_values = price_df.iloc[0]
    s1_val = daily_level_values.get('Daily S1')
    pdl_val = daily_level_values.get('Prev Day Low')
    r1_val = daily_level_values.get('Daily R1')
    pdh_val = daily_level_values.get('Prev Day High')
    pivot_val = daily_level_values.get('Daily Pivot')
    tc_val = daily_level_values.get('Daily TC')
    bc_val = daily_level_values.get('Daily BC')
    
    # Extended levels
    r2_val = daily_level_values.get('Daily R2')
    r3_val = daily_level_values.get('Daily R3')
    r4_val = daily_level_values.get('Daily R4')
    s2_val = daily_level_values.get('Daily S2')
    s3_val = daily_level_values.get('Daily S3')
    s4_val = daily_level_values.get('Daily S4')
    
    # Initialize CPR filter columns
    for signal_col in trade_type_map.keys():
        signals_df[f'{signal_col}_crp'] = 0
    
    print(f"Processing {len(signals_df)} signals with wide band CPR filter...")
    
    for idx, signal_row in signals_df.iterrows():
        for signal_col, trade_type in trade_type_map.items():
            if signal_row[signal_col] == 1:
                trade_time = signal_row['datetime']
                
                # Find the exact candle for this signal
                exact_candle = price_df[price_df['datetime'] == trade_time]
                if exact_candle.empty:
                    continue
                
                passed = False
                
                if trade_type == 'Call':
                    candle_low = exact_candle['low'].values[0]
                    candle_high = exact_candle['high'].values[0]
                    
                    # Pivot/TC Support Zone (only check LOW for this primary zone)
                    if not passed and not pd.isna(pivot_val) and not pd.isna(tc_val):
                        zone_bottom = pivot_val
                        zone_top = tc_val * (1 + proximity_pct / 100)
                        if zone_bottom <= candle_low <= zone_top:
                            passed = True
                    
                    # All other levels treated as extended zones (PDL/S1/S2/S3/S4/PDH/R1/R2/R3/R4)
                    # Check both HIGH and LOW for these zones
                    if not passed:
                        extended_levels = [pdl_val, s1_val, s2_val, s3_val, s4_val, pdh_val, r1_val, r2_val, r3_val, r4_val]
                        level_names = ['PDL', 'S1', 'S2', 'S3', 'S4', 'PDH', 'R1', 'R2', 'R3', 'R4']
                        
                        for level_val, level_name in zip(extended_levels, level_names):
                            if not pd.isna(level_val):
                                zone_bottom = level_val * (1 - proximity_pct / 100)
                                zone_top = level_val * (1 + proximity_pct / 100)
                                # Check both LOW and HIGH for Call trades in extended zones
                                if (zone_bottom <= candle_low <= zone_top) or (zone_bottom <= candle_high <= zone_top):
                                    passed = True
                                    break
                
                else:  # Put Trade
                    candle_low = exact_candle['low'].values[0]
                    candle_high = exact_candle['high'].values[0]
                    
                    # Pivot/BC Resistance Zone (only check HIGH for this primary zone)
                    if not passed and not pd.isna(pivot_val) and not pd.isna(bc_val):
                        zone_bottom = bc_val * (1 - proximity_pct / 100)
                        zone_top = pivot_val
                        if zone_bottom <= candle_high <= zone_top:
                            passed = True
                    
                    # All other levels treated as extended zones (PDL/S1/S2/S3/S4/PDH/R1/R2/R3/R4)
                    # Check both HIGH and LOW for these zones
                    if not passed:
                        extended_levels = [pdl_val, s1_val, s2_val, s3_val, s4_val, pdh_val, r1_val, r2_val, r3_val, r4_val]
                        level_names = ['PDL', 'S1', 'S2', 'S3', 'S4', 'PDH', 'R1', 'R2', 'R3', 'R4']
                        
                        for level_val, level_name in zip(extended_levels, level_names):
                            if not pd.isna(level_val):
                                zone_bottom = level_val * (1 - proximity_pct / 100)
                                zone_top = level_val * (1 + proximity_pct / 100)
                                # Check both HIGH and LOW for Put trades in extended zones
                                if (zone_bottom <= candle_high <= zone_top) or (zone_bottom <= candle_low <= zone_top):
                                    passed = True
                                    break
                
                if passed:
                    signals_df.at[idx, f'{signal_col}_crp'] = 1
    
    return signals_df
