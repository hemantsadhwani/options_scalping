
import pandas as pd
from datetime import timedelta

def run_cpr_filter(price_df, signals_df, trade_type_map):
    """
    Analyzes trades against price action near CPR levels to filter for high-probability reversals.
    This version uses two different proximity percentages: one for primary zones and a wider one for extended zones.

    Args:
    price_df (pd.DataFrame): DataFrame with price data, including CPR levels.
    signals_df (pd.DataFrame): DataFrame with trading signals (Call, Put, etc.).
    trade_type_map (dict): A dictionary mapping signal column names to their trade type ('Call' or 'Put').

    Returns:
    pd.DataFrame: The signals_df with added columns indicating filtered signals.
    """
    price_df['datetime'] = pd.to_datetime(price_df['datetime'], errors='coerce')
    signals_df['datetime'] = pd.to_datetime(signals_df['datetime'], errors='coerce')
    price_df.dropna(subset=['datetime'], inplace=True)
    signals_df.dropna(subset=['datetime'], inplace=True)

    # Initialize output columns
    for signal_col in trade_type_map.keys():
        signals_df[f'{signal_col}_crp'] = 0

    # Define the two proximity percentages as per the rules
    proximity_pct_primary = 0.03
    proximity_pct_extended = 0.06

    trade_date = price_df['datetime'].dt.date.iloc[0]
    signals_df = signals_df[signals_df['datetime'].dt.date == trade_date].copy()

    if signals_df.empty:
        print(f"No signals found for the specified date: {trade_date}")
        return signals_df

    def check_price_in_zone(candle_low, candle_high, level_val, proximity_pct, is_put_trade=False):
        """Generic function to check if candle's HIGH or LOW is within the zone of a given level."""
        if pd.isna(level_val):
            return False

        # For Put trades, the zone is typically below the level
        if is_put_trade:
            zone_bottom = level_val * (1 - proximity_pct / 100)
            zone_top = level_val
        # For Call trades, the zone is typically above the level
        else:
            zone_bottom = level_val
            zone_top = level_val * (1 + proximity_pct / 100)

        # For extended zones, the zone is on both sides of the level
        if proximity_pct == proximity_pct_extended:
            zone_bottom = level_val * (1 - proximity_pct / 100)
            zone_top = level_val * (1 + proximity_pct / 100)

        low_in_zone = zone_bottom <= candle_low <= zone_top
        high_in_zone = zone_bottom <= candle_high <= zone_top
        return low_in_zone or high_in_zone

    daily_level_values = price_df.iloc[0]
    s1_val, pdl_val = daily_level_values.get('Daily S1'), daily_level_values.get('Prev Day Low')
    r1_val, pdh_val = daily_level_values.get('Daily R1'), daily_level_values.get('Prev Day High')
    pivot_val, tc_val, bc_val = daily_level_values.get('Daily Pivot'), daily_level_values.get('Daily TC'), daily_level_values.get('Daily BC')

    extended_levels = {
        'S2': daily_level_values.get('Daily S2'), 'S3': daily_level_values.get('Daily S3'), 'S4': daily_level_values.get('Daily S4'),
        'R2': daily_level_values.get('Daily R2'), 'R3': daily_level_values.get('Daily R3'), 'R4': daily_level_values.get('Daily R4')
    }

    for signal_col, trade_type_val in trade_type_map.items():
        signal_trades = signals_df[signals_df[signal_col] == 1].copy()

        for idx, trade in signal_trades.iterrows():
            trade_time = trade['datetime']
            exact_candle = price_df[price_df['datetime'] == trade_time]
            if exact_candle.empty:
                continue

            # Trend analysis
            trend_lookback_start = trade_time - timedelta(minutes=5)
            trend_lookback_end = trade_time - timedelta(minutes=1)
            trend_df = price_df[(price_df['datetime'] >= trend_lookback_start) & (price_df['datetime'] <= trend_lookback_end)]
            price_is_rising = len(trend_df) >= 2 and trend_df['close'].iloc[-1] > trend_df['close'].iloc[0]
            price_is_falling = len(trend_df) >= 2 and trend_df['close'].iloc[-1] < trend_df['close'].iloc[0]

            passed = False
            candle_low = exact_candle['low'].values[0]
            candle_high = exact_candle['high'].values[0]

            if trade_type_val == 'Call':
                # 1. S1/PDL Zone (Primary)
                if not pd.isna(s1_val) and not pd.isna(pdl_val):
                    zone_bottom = min(s1_val, pdl_val)
                    zone_top = max(s1_val, pdl_val) * (1 + proximity_pct_primary / 100)
                    if (zone_bottom <= candle_low <= zone_top) or (zone_bottom <= candle_high <= zone_top):
                        passed = True

                # 2. Extended Zones (S2-S4, R2-R4)
                if not passed:
                    for level_val in list(extended_levels.values()):
                        if check_price_in_zone(candle_low, candle_high, level_val, proximity_pct_extended):
                            passed = True
                            break

                # 3. Pivot/TC Zone (Primary)
                if not passed and not pd.isna(pivot_val) and not pd.isna(tc_val):
                    zone_bottom = pivot_val
                    zone_top = tc_val * (1 + proximity_pct_primary / 100)
                    if (zone_bottom <= candle_low <= zone_top) or (zone_bottom <= candle_high <= zone_top):
                        passed = True

                # 4. R1/PDH Zone (Primary, conditional)
                if not passed and price_is_falling and not pd.isna(r1_val) and not pd.isna(pdh_val):
                    zone_bottom = min(r1_val, pdh_val)
                    zone_top = max(r1_val, pdh_val) * (1 + proximity_pct_primary / 100)
                    if (zone_bottom <= candle_low <= zone_top) or (zone_bottom <= candle_high <= zone_top):
                        passed = True

            else:  # Put Trade
                # 1. R1/PDH Zone (Primary)
                if not pd.isna(r1_val) and not pd.isna(pdh_val):
                    zone_bottom = min(r1_val, pdh_val) * (1 - proximity_pct_primary / 100)
                    zone_top = max(r1_val, pdh_val)
                    if zone_bottom <= candle_high <= zone_top:
                        passed = True

                # 2. Extended Zones (R2-R4, S2-S4)
                if not passed:
                    for level_val in list(extended_levels.values()):
                        if check_price_in_zone(candle_low, candle_high, level_val, proximity_pct_extended, is_put_trade=True):
                            passed = True
                            break

                # 3. Pivot/BC Zone (Primary)
                if not passed and not pd.isna(pivot_val) and not pd.isna(bc_val):
                    zone_bottom = bc_val * (1 - proximity_pct_primary / 100)
                    zone_top = pivot_val
                    if zone_bottom <= candle_high <= zone_top:
                        passed = True

                # 4. S1/PDL Zone (Primary, conditional)
                if not passed and price_is_rising and not pd.isna(s1_val) and not pd.isna(pdl_val):
                    zone_bottom = min(s1_val, pdl_val) * (1 - proximity_pct_primary / 100)
                    zone_top = max(s1_val, pdl_val)
                    if zone_bottom <= candle_high <= zone_top:
                        passed = True

            if passed:
                signals_df.at[idx, f'{signal_col}_crp'] = 1

    return signals_df
