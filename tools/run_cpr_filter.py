import pandas as pd
from datetime import timedelta

def run_cpr_filter(price_df, signals_df, trade_type_map):
    """
    Analyzes trades against price action near CPR levels to filter for high-probability reversals.
    Adds new columns to the signals_df to indicate which signals passed the filter.

    Args:
        price_df (pd.DataFrame): DataFrame with price data, including CPR levels.
        signals_df (pd.DataFrame): DataFrame with trading signals (Call, Put, Call_v2, Put_v2).
        trade_type_map (dict): A dictionary mapping signal column names to their trade type ('Call' or 'Put').
                               Example: {'Call': 'Call', 'Put': 'Put', 'Call_v2': 'Call', 'Put_v2': 'Put'}

    Returns:
        pd.DataFrame: The signals_df with added columns indicating filtered signals.
    """
    price_df['datetime'] = pd.to_datetime(price_df['datetime'], errors='coerce')
    signals_df['datetime'] = pd.to_datetime(signals_df['datetime'], errors='coerce')
    price_df.dropna(subset=['datetime'], inplace=True)
    signals_df.dropna(subset=['datetime'], inplace=True)

    trade_date = price_df['datetime'].dt.date.iloc[0]
    signals_df = signals_df[signals_df['datetime'].dt.date == trade_date].copy()

    if signals_df.empty:
        print(f"No signals found for the specified date: {trade_date}")
        return signals_df

    # Initialize output columns
    for signal_col in trade_type_map.keys():
        signals_df[f'{signal_col}_crp'] = 0

    def check_extended_zone(price, level_val, proximity_pct, level_name, trade_time):
        """Check if price is within the extended zone of a given level."""
        if pd.isna(level_val):
            return False
        zone_bottom = level_val * (1 - proximity_pct / 100)
        zone_top = level_val * (1 + proximity_pct / 100)
        is_in_zone = zone_bottom <= price <= zone_top
        
        if trade_time.strftime('%Y-%m-%d %H:%M:%S') == '2025-07-02 09:25:00':
            print(f"\nDEBUG: {level_name} Zone Check")
            print(f"Level value: {level_val:.2f}")
            print(f"Zone bottom: {zone_bottom:.2f}")
            print(f"Zone top: {zone_top:.2f}")
            print(f"Price in zone: {is_in_zone}")
        
        return is_in_zone

    daily_level_values = price_df.iloc[0]
    s1_val, pdl_val = daily_level_values.get('Daily S1'), daily_level_values.get('Prev Day Low')
    r1_val, pdh_val = daily_level_values.get('Daily R1'), daily_level_values.get('Prev Day High')
    pivot_val, tc_val, bc_val = daily_level_values.get('Daily Pivot'), daily_level_values.get('Daily TC'), daily_level_values.get('Daily BC')
    
    # Get extended levels
    r2_val = daily_level_values.get('Daily R2')
    r3_val = daily_level_values.get('Daily R3')
    r4_val = daily_level_values.get('Daily R4')
    s2_val = daily_level_values.get('Daily S2')
    s3_val = daily_level_values.get('Daily S3')
    s4_val = daily_level_values.get('Daily S4')

    for signal_col, trade_type_val in trade_type_map.items():
        # Get the rows where the current signal is active
        signal_trades = signals_df[signals_df[signal_col] == 1].copy()

        for idx, trade in signal_trades.iterrows():
            trade_time = trade['datetime']
            lookback_minutes = 5
            proximity_pct = 0.03

            # Debug print for 9:25 trade
            if trade_time.strftime('%Y-%m-%d %H:%M:%S') == '2025-07-02 09:25:00':
                print(f"\nDEBUG: Processing trade at {trade_time}")
                print(f"Signal column: {signal_col}")
                print(f"Trade type: {trade_type_val}")

            trade_lookback_start = trade_time - timedelta(minutes=lookback_minutes)
            trade_lookback_end = trade_time
            
            event_lookback_df = price_df[(price_df['datetime'] >= trade_lookback_start) & (price_df['datetime'] <= trade_lookback_end)]
            
            if event_lookback_df.empty:
                continue

            # Use price at exact trade time candle
            exact_candle = price_df[price_df['datetime'] == trade_time]
            if exact_candle.empty:
                continue

            price_is_rising = False
            price_is_falling = False
            if len(price_df) >= 2:
                # Determine trend by comparing close price lookback_minutes before trade_time and just before trade_time
                trend_lookback_start = trade_time - timedelta(minutes=lookback_minutes)
                trend_lookback_end = trade_time - timedelta(minutes=1)
                trend_df = price_df[(price_df['datetime'] >= trend_lookback_start) & (price_df['datetime'] <= trend_lookback_end)]
                if len(trend_df) >= 2:
                    price_is_rising = trend_df['close'].iloc[-1] > trend_df['close'].iloc[0]
                    price_is_falling = trend_df['close'].iloc[-1] < trend_df['close'].iloc[0]
                    
                    # Debug print for 9:25 trade
                    if trade_time.strftime('%Y-%m-%d %H:%M:%S') == '2025-07-02 09:25:00':
                        print(f"Trend analysis:")
                        print(f"Start price: {trend_df['close'].iloc[0]}")
                        print(f"End price: {trend_df['close'].iloc[-1]}")
                        print(f"Price is rising: {price_is_rising}")
                        print(f"Price is falling: {price_is_falling}")

            passed = False
            if trade_type_val == 'Call':
                price = exact_candle['low'].values[0]
                if trade_time.strftime('%Y-%m-%d %H:%M:%S') == '2025-07-02 09:25:00':
                    print(f"\nDEBUG: Call Trade Price Check")
                    print(f"Low price at 9:25: {price:.2f}")
                    print(f"S1: {s1_val:.2f}, PDL: {pdl_val:.2f}")
                    print(f"Price is rising: {price_is_rising}")
                    print(f"Price is falling: {price_is_falling}")

                # Check S1/PDL zone regardless of trend direction
                if not pd.isna(s1_val) and not pd.isna(pdl_val):
                    zone_bottom = min(s1_val, pdl_val)
                    zone_top = max(s1_val, pdl_val) * (1 + proximity_pct / 100)
                    if trade_time.strftime('%Y-%m-%d %H:%M:%S') == '2025-07-02 09:25:00':
                        print(f"\nDEBUG: S1/PDL Zone Check")
                        print(f"Zone bottom: {zone_bottom:.2f}")
                        print(f"Zone top: {zone_top:.2f}")
                        print(f"Price in zone: {zone_bottom <= price <= zone_top}")
                    if zone_bottom <= price <= zone_top:
                        passed = True

                # Check extended support zones (S2/S3/S4) regardless of trend
                if not passed:
                    for level_val, level_name in [(s2_val, 'S2'), (s3_val, 'S3'), (s4_val, 'S4')]:
                        if check_extended_zone(price, level_val, proximity_pct, level_name, trade_time):
                            if trade_time.strftime('%Y-%m-%d %H:%M:%S') == '2025-07-02 09:25:00':
                                print(f"Call Trade PASSED due to {level_name} zone")
                            passed = True
                            break

                # Check extended resistance zones (R2/R3/R4) regardless of trend
                if not passed:
                    for level_val, level_name in [(r2_val, 'R2'), (r3_val, 'R3'), (r4_val, 'R4')]:
                        if check_extended_zone(price, level_val, proximity_pct, level_name, trade_time):
                            if trade_time.strftime('%Y-%m-%d %H:%M:%S') == '2025-07-02 09:25:00':
                                print(f"Call Trade PASSED due to {level_name} zone")
                            passed = True
                            break

                # Check Pivot/TC zone regardless of trend direction
                if not passed and not pd.isna(pivot_val) and not pd.isna(tc_val):
                    zone_bottom = pivot_val
                    zone_top = tc_val * (1 + proximity_pct / 100)
                    if zone_bottom <= price <= zone_top:
                        passed = True

                # Only check R1/PDH zone if price is falling
                if not passed and price_is_falling:
                    if not pd.isna(r1_val) and not pd.isna(pdh_val):
                        zone_bottom = min(r1_val, pdh_val)
                        zone_top = max(r1_val, pdh_val) * (1 + proximity_pct / 100)
                        if zone_bottom <= price <= zone_top:
                            passed = True

            else:  # Put Trade
                price = exact_candle['high'].values[0]
                if trade_time.strftime('%Y-%m-%d %H:%M:%S') == '2025-07-02 09:25:00':
                    print(f"\nDEBUG: Put Trade Price Check")
                    print(f"High price at 9:25: {price:.2f}")
                    print(f"R1: {r1_val:.2f}, PDH: {pdh_val:.2f}")
                    print(f"Price is rising: {price_is_rising}")
                    print(f"Price is falling: {price_is_falling}")

                # Check R1/PDH zone regardless of trend direction
                if not pd.isna(r1_val) and not pd.isna(pdh_val):
                    zone_bottom = min(r1_val, pdh_val) * (1 - proximity_pct / 100)
                    zone_top = max(r1_val, pdh_val)
                    if trade_time.strftime('%Y-%m-%d %H:%M:%S') == '2025-07-02 09:25:00':
                        print(f"\nDEBUG: R1/PDH Zone Check")
                        print(f"Zone bottom: {zone_bottom:.2f}")
                        print(f"Zone top: {zone_top:.2f}")
                        print(f"Price in zone: {zone_bottom <= price <= zone_top}")
                    if zone_bottom <= price <= zone_top:
                        passed = True

                # Check extended resistance zones (R2/R3/R4) regardless of trend
                if not passed:
                    for level_val, level_name in [(r2_val, 'R2'), (r3_val, 'R3'), (r4_val, 'R4')]:
                        if check_extended_zone(price, level_val, proximity_pct, level_name, trade_time):
                            if trade_time.strftime('%Y-%m-%d %H:%M:%S') == '2025-07-02 09:25:00':
                                print(f"Put Trade PASSED due to {level_name} zone")
                            passed = True
                            break

                # Check extended support zones (S2/S3/S4) regardless of trend
                if not passed:
                    for level_val, level_name in [(s2_val, 'S2'), (s3_val, 'S3'), (s4_val, 'S4')]:
                        if check_extended_zone(price, level_val, proximity_pct, level_name, trade_time):
                            if trade_time.strftime('%Y-%m-%d %H:%M:%S') == '2025-07-02 09:25:00':
                                print(f"Put Trade PASSED due to {level_name} zone")
                            passed = True
                            break

                # Check Pivot/BC zone regardless of trend direction
                if not passed and not pd.isna(pivot_val) and not pd.isna(bc_val):
                    zone_bottom = bc_val * (1 - proximity_pct / 100)
                    zone_top = pivot_val
                    if trade_time.strftime('%Y-%m-%d %H:%M:%S') == '2025-06-30 12:25:00':
                        print(f"\nDEBUG: Pivot/BC Zone Check for 12:25 Put Trade")
                        print(f"Price is rising: {price_is_rising}")
                        print(f"Zone bottom: {zone_bottom:.2f}")
                        print(f"Zone top: {zone_top:.2f}")
                        print(f"Price in zone: {zone_bottom <= price <= zone_top}")
                    if zone_bottom <= price <= zone_top:
                        passed = True

                # Only check S1/PDL zone if price is rising
                if not passed and price_is_rising:
                    if not pd.isna(s1_val) and not pd.isna(pdl_val):
                        zone_bottom = min(s1_val, pdl_val) * (1 - proximity_pct / 100)
                        zone_top = max(s1_val, pdl_val)
                        if zone_bottom <= price <= zone_top:
                            passed = True

            if passed:
                signals_df.at[idx, f'{signal_col}_crp'] = 1

    return signals_df
