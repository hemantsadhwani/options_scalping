import pandas as pd
from datetime import timedelta

def analyze_reversals(trade_date_str, price_file, call_file, put_file, lookback_minutes=5, proximity_pct=0.03):
    # Load data
    price_df = pd.read_csv(price_file)
    call_df = pd.read_csv(call_file)
    put_df = pd.read_csv(put_file)

    # Convert datetime columns with robust parsing
    price_df['datetime'] = pd.to_datetime(price_df['datetime'], format='%d/%m/%y %H:%M', errors='coerce')
    call_df['entry_time'] = pd.to_datetime(call_df['entry_time'], format='mixed', dayfirst=True, errors='coerce')
    put_df['entry_time'] = pd.to_datetime(put_df['entry_time'], format='mixed', dayfirst=True, errors='coerce')

    # Drop rows where date conversion failed
    price_df.dropna(subset=['datetime'], inplace=True)
    call_df.dropna(subset=['entry_time'], inplace=True)
    put_df.dropna(subset=['entry_time'], inplace=True)

    # Filter data for the specific trade date
    trade_date = pd.to_datetime(trade_date_str).date()
    price_df = price_df[price_df['datetime'].dt.date == trade_date].copy()

    if price_df.empty:
        print(f"No price data found for {trade_date_str}. Exiting.")
        return

    # Filter for reversal trades on the specified date
    call_reversals = call_df[(call_df['comments'] == 'Reversal') & (call_df['entry_time'].dt.date == trade_date)].copy()
    put_reversals = put_df[(put_df['comments'] == 'Reversal') & (put_df['entry_time'].dt.date == trade_date)].copy()

    all_reversals = pd.concat([call_reversals, put_reversals]).sort_values(by='entry_time').reset_index(drop=True)
    
    if all_reversals.empty:
        print(f"No reversal trades found for {trade_date_str}. Exiting.")
        return

    all_reversals['filter_passed'] = False

    print(f"--- Reversal Filter Analysis for {trade_date_str} (Custom One-Sided Band Logic) ---")
    print(f"Parameters: Lookback={lookback_minutes} mins, Proximity={proximity_pct}%")
    print("\n--- Detailed Filter Results ---")

    daily_level_values = price_df.iloc[0]

    for idx, trade in all_reversals.iterrows():
        trade_time = trade['entry_time']
        trade_type = trade['type']
        
        start_time = trade_time - timedelta(minutes=lookback_minutes)
        end_time = trade_time - timedelta(minutes=1)
        
        lookback_df = price_df[(price_df['datetime'] >= start_time) & (price_df['datetime'] <= end_time)]
        
        if lookback_df.empty:
            print(f"Trade at {trade_time.time()} ({trade_type}, Target: {trade['target']}) -> FAILED (No lookback data)")
            continue

        passed = False
        confirmation_details = ""

        # --- IMPLEMENTING YOUR FINAL, PRECISE RULES ---
        
        for _, candle in lookback_df.iterrows():
            if passed: break

            if trade_type == 'Call':
                price = candle['low']
                
                # Rule 1: S1/PDL Zone
                s1_val = daily_level_values.get('Daily S1')
                pdl_val = daily_level_values.get('Prev Day Low')
                if not pd.isna(s1_val) and not pd.isna(pdl_val):
                    zone_bottom = min(s1_val, pdl_val)
                    zone_top = max(s1_val, pdl_val) * (1 + proximity_pct / 100)
                    if zone_bottom <= price <= zone_top:
                        passed = True
                        confirmation_details = (f"  └─ Confirmation: Low entered 'S1/PDL Support Zone' ({zone_bottom:.2f} - {zone_top:.2f}) at {candle['datetime'].time()}")
                
                if passed: break

                # Rule 2: Pivot/TC Zone
                pivot_val = daily_level_values.get('Daily Pivot')
                tc_val = daily_level_values.get('Daily TC')
                if not pd.isna(pivot_val) and not pd.isna(tc_val):
                    zone_bottom = pivot_val
                    zone_top = tc_val * (1 + proximity_pct / 100)
                    if zone_bottom <= price <= zone_top:
                        passed = True
                        confirmation_details = (f"  └─ Confirmation: Low entered 'Pivot/TC Support Zone' ({zone_bottom:.2f} - {zone_top:.2f}) at {candle['datetime'].time()}")

            else: # Put Trade
                price = candle['high']

                # Rule 1: R1/PDH Zone
                r1_val = daily_level_values.get('Daily R1')
                pdh_val = daily_level_values.get('Prev Day High')
                if not pd.isna(r1_val) and not pd.isna(pdh_val):
                    zone_bottom = min(r1_val, pdh_val) * (1 - proximity_pct / 100)
                    zone_top = max(r1_val, pdh_val)
                    if zone_bottom <= price <= zone_top:
                        passed = True
                        confirmation_details = (f"  └─ Confirmation: High entered 'R1/PDH Resistance Zone' ({zone_bottom:.2f} - {zone_top:.2f}) at {candle['datetime'].time()}")

                if passed: break

                # Rule 2: Pivot/BC Zone
                pivot_val = daily_level_values.get('Daily Pivot')
                bc_val = daily_level_values.get('Daily BC')
                if not pd.isna(pivot_val) and not pd.isna(bc_val):
                    zone_bottom = bc_val * (1 - proximity_pct / 100)
                    zone_top = pivot_val
                    if zone_bottom <= price <= zone_top:
                        passed = True
                        confirmation_details = (f"  └─ Confirmation: High entered 'Pivot/BC Resistance Zone' ({zone_bottom:.2f} - {zone_top:.2f}) at {candle['datetime'].time()}")

        all_reversals.at[idx, 'filter_passed'] = passed
        status = "PASSED" if passed else "FAILED"
        print(f"Trade at {trade_time.time()} ({trade_type}, Target: {trade['target']}) -> {status}")
        if passed:
            print(confirmation_details)

    def print_summary(title, original_df, filtered_df):
        original_total = len(original_df)
        original_wins = original_df['target'].sum()
        original_win_rate = (original_wins / original_total * 100) if original_total > 0 else 0

        after_filter_df = filtered_df[filtered_df['filter_passed'] == True]
        after_filter_total = len(after_filter_df)
        after_filter_wins = after_filter_df['target'].sum()
        after_filter_win_rate = (after_filter_wins / after_filter_total * 100) if after_filter_total > 0 else 0
        
        print("\n" + "="*50)
        print(f"\n--- {title} Performance Summary ---")
        print(f"Original Reversal Trades: {original_total} ({original_wins} wins) -> {original_win_rate:.2f}% Win Rate")
        print(f"Trades After Filtering:   {after_filter_total} ({after_filter_wins} wins) -> {after_filter_win_rate:.2f}% Win Rate")

    filtered_puts = all_reversals[all_reversals['type'] == 'Put']
    filtered_calls = all_reversals[all_reversals['type'] == 'Call']

    print_summary("Put", put_reversals, filtered_puts)
    print_summary("Call", call_reversals, filtered_calls)
    print_summary("Combined", all_reversals, all_reversals)
    print("\n" + "="*50)


# --- Main Execution ---
TRADE_DATE = '2025-07-03'
PRICE_DATA_FILE = '../data/0307/tradeview_utc_output.csv'
CALL_TRADES_FILE = 'ml_call_data.csv'
PUT_TRADES_FILE = 'ml_put_data.csv'

analyze_reversals(TRADE_DATE, PRICE_DATA_FILE, CALL_TRADES_FILE, PUT_TRADES_FILE, proximity_pct=0.03)