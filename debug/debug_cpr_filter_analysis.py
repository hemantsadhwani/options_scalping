import pandas as pd
from datetime import datetime, timedelta

def analyze_put_trade_filtering():
    """
    Analyze why the put trade at 11:29 on 2025-07-03 is being filtered out by CPR filter
    """
    
    # Load the price data with CPR levels
    price_file = "data/0307/tradeview_rev_output.csv"
    price_df = pd.read_csv(price_file)
    
    # Convert datetime column
    price_df['datetime'] = pd.to_datetime(price_df['datetime'], errors='coerce')
    
    # Get the specific trade time
    trade_time = pd.to_datetime('2025-07-03 11:29:00')
    
    # Find the candle at trade time
    trade_candle = price_df[price_df['datetime'] == trade_time]
    
    if trade_candle.empty:
        print(f"No candle found at {trade_time}")
        return
    
    candle = trade_candle.iloc[0]
    
    print("=== PUT TRADE CPR FILTER ANALYSIS ===")
    print(f"Trade Time: {trade_time}")
    print(f"Candle Data:")
    print(f"  Open: {candle['open']:.2f}")
    print(f"  High: {candle['high']:.2f}")
    print(f"  Low: {candle['low']:.2f}")
    print(f"  Close: {candle['close']:.2f}")
    
    # Get CPR levels (they should be the same for all candles on the same day)
    daily_levels = price_df.iloc[0]
    
    r1_val = daily_levels.get('Daily R1')
    pdh_val = daily_levels.get('Prev Day High')
    pivot_val = daily_levels.get('Daily Pivot')
    bc_val = daily_levels.get('Daily BC')
    r2_val = daily_levels.get('Daily R2')
    r3_val = daily_levels.get('Daily R3')
    r4_val = daily_levels.get('Daily R4')
    s2_val = daily_levels.get('Daily S2')
    s3_val = daily_levels.get('Daily S3')
    s4_val = daily_levels.get('Daily S4')
    
    print(f"\nCPR Levels:")
    print(f"  Daily R1: {r1_val:.2f}")
    print(f"  Prev Day High: {pdh_val:.2f}")
    print(f"  Daily Pivot: {pivot_val:.2f}")
    print(f"  Daily BC: {bc_val:.2f}")
    print(f"  Daily R2: {r2_val:.2f}")
    print(f"  Daily R3: {r3_val:.2f}")
    print(f"  Daily R4: {r4_val:.2f}")
    print(f"  Daily S2: {s2_val:.2f}")
    print(f"  Daily S3: {s3_val:.2f}")
    print(f"  Daily S4: {s4_val:.2f}")
    
    proximity_pct = 0.03  # 3%
    candle_high = candle['high']
    candle_low = candle['low']
    
    print(f"\n=== PUT TRADE ZONE ANALYSIS ===")
    print(f"Candle High: {candle_high:.2f}")
    print(f"Proximity %: {proximity_pct*100}%")
    
    # Check R1/PDH Resistance Zone (Primary zone for Put trades)
    if not pd.isna(r1_val) and not pd.isna(pdh_val):
        zone_bottom = min(r1_val, pdh_val) * (1 - proximity_pct)
        zone_top = max(r1_val, pdh_val)
        in_zone = zone_bottom <= candle_high <= zone_top
        
        print(f"\n1. R1/PDH Resistance Zone:")
        print(f"   Zone Bottom: {zone_bottom:.2f}")
        print(f"   Zone Top: {zone_top:.2f}")
        print(f"   Candle High in Zone: {in_zone}")
        
        if in_zone:
            print("   ✅ PUT TRADE WOULD PASS - R1/PDH Zone")
            return True
    
    # Check Pivot/BC Resistance Zone
    if not pd.isna(pivot_val) and not pd.isna(bc_val):
        zone_bottom = bc_val * (1 - proximity_pct)
        zone_top = pivot_val
        in_zone = zone_bottom <= candle_high <= zone_top
        
        print(f"\n2. Pivot/BC Resistance Zone:")
        print(f"   Zone Bottom: {zone_bottom:.2f}")
        print(f"   Zone Top: {zone_top:.2f}")
        print(f"   Candle High in Zone: {in_zone}")
        
        if in_zone:
            print("   ✅ PUT TRADE WOULD PASS - Pivot/BC Zone")
            return True
    
    # Check Extended Resistance Zones (R2/R3/R4)
    extended_r_levels = [
        (r2_val, 'R2'),
        (r3_val, 'R3'),
        (r4_val, 'R4')
    ]
    
    print(f"\n3. Extended Resistance Zones (R2/R3/R4):")
    for level_val, level_name in extended_r_levels:
        if not pd.isna(level_val):
            zone_bottom = level_val * (1 - proximity_pct)
            zone_top = level_val * (1 + proximity_pct)
            high_in_zone = zone_bottom <= candle_high <= zone_top
            low_in_zone = zone_bottom <= candle_low <= zone_top
            in_zone = high_in_zone or low_in_zone
            
            print(f"   {level_name} Zone:")
            print(f"     Level: {level_val:.2f}")
            print(f"     Zone Bottom: {zone_bottom:.2f}")
            print(f"     Zone Top: {zone_top:.2f}")
            print(f"     High in Zone: {high_in_zone}")
            print(f"     Low in Zone: {low_in_zone}")
            print(f"     Either in Zone: {in_zone}")
            
            if in_zone:
                print(f"   ✅ PUT TRADE WOULD PASS - {level_name} Zone")
                return True
    
    # Check Extended Support Zones (S2/S3/S4)
    extended_s_levels = [
        (s2_val, 'S2'),
        (s3_val, 'S3'),
        (s4_val, 'S4')
    ]
    
    print(f"\n4. Extended Support Zones (S2/S3/S4):")
    for level_val, level_name in extended_s_levels:
        if not pd.isna(level_val):
            zone_bottom = level_val * (1 - proximity_pct)
            zone_top = level_val * (1 + proximity_pct)
            high_in_zone = zone_bottom <= candle_high <= zone_top
            low_in_zone = zone_bottom <= candle_low <= zone_top
            in_zone = high_in_zone or low_in_zone
            
            print(f"   {level_name} Zone:")
            print(f"     Level: {level_val:.2f}")
            print(f"     Zone Bottom: {zone_bottom:.2f}")
            print(f"     Zone Top: {zone_top:.2f}")
            print(f"     High in Zone: {high_in_zone}")
            print(f"     Low in Zone: {low_in_zone}")
            print(f"     Either in Zone: {in_zone}")
            
            if in_zone:
                print(f"   ✅ PUT TRADE WOULD PASS - {level_name} Zone")
                return True
    
    # Check trend direction for S1/PDL zone (secondary zone requiring rising price)
    lookback_minutes = 5
    trade_lookback_start = trade_time - timedelta(minutes=lookback_minutes)
    trade_lookback_end = trade_time - timedelta(minutes=1)
    
    trend_df = price_df[(price_df['datetime'] >= trade_lookback_start) & (price_df['datetime'] <= trade_lookback_end)]
    
    price_is_rising = False
    if len(trend_df) >= 2:
        price_is_rising = trend_df['close'].iloc[-1] > trend_df['close'].iloc[0]
        print(f"\n5. Trend Analysis:")
        print(f"   Lookback period: {trade_lookback_start} to {trade_lookback_end}")
        print(f"   Start price: {trend_df['close'].iloc[0]:.2f}")
        print(f"   End price: {trend_df['close'].iloc[-1]:.2f}")
        print(f"   Price is rising: {price_is_rising}")
    
    # Check S1/PDL zone (only if price is rising)
    s1_val = daily_levels.get('Daily S1')
    pdl_val = daily_levels.get('Prev Day Low')
    
    if not pd.isna(s1_val) and not pd.isna(pdl_val):
        zone_bottom = min(s1_val, pdl_val) * (1 - proximity_pct)
        zone_top = max(s1_val, pdl_val)
        in_zone = zone_bottom <= candle_high <= zone_top
        
        print(f"\n6. S1/PDL Resistance Zone (requires rising price):")
        print(f"   Zone Bottom: {zone_bottom:.2f}")
        print(f"   Zone Top: {zone_top:.2f}")
        print(f"   Candle High in Zone: {in_zone}")
        print(f"   Price is rising: {price_is_rising}")
        print(f"   Both conditions met: {in_zone and price_is_rising}")
        
        if in_zone and price_is_rising:
            print("   ✅ PUT TRADE WOULD PASS - S1/PDL Zone with rising price")
            return True
    
    print(f"\n❌ PUT TRADE FILTERED OUT - No CPR zone conditions met")
    
    # Check the actual signal values from the data
    put_signal = candle.get('Put', 0)
    put_v2_signal = candle.get('Put_v2', 0)
    put_crp = candle.get('Put_crp', 0)
    put_v2_crp = candle.get('Put_v2_crp', 0)
    
    print(f"\nSignal Values at {trade_time}:")
    print(f"  Put: {put_signal}")
    print(f"  Put_v2: {put_v2_signal}")
    print(f"  Put_crp: {put_crp}")
    print(f"  Put_v2_crp: {put_v2_crp}")
    
    return False

if __name__ == "__main__":
    analyze_put_trade_filtering()
