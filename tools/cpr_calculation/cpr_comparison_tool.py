
import pandas as pd
import numpy as np

def compare_cpr_values(csv_file_path):
    """
    Compare TradeView CPR values with our calculated CPR values

    Args:
        csv_file_path (str): Path to the CSV file containing both TradeView and calculated CPR values

    Returns:
        dict: Comparison results and statistics
    """

    # Load the data
    df = pd.read_csv(csv_file_path)

    # Define the column mappings for comparison
    comparisons = {
        'Central Pivot': ('Daily Pivot', 'CPR_CP'),
        'Bottom Central': ('Daily BC', 'CPR_BC'), 
        'Top Central': ('Daily TC', 'CPR_TC'),
        'Resistance 1': ('Daily R1', 'CPR_R1'),
        'Resistance 2': ('Daily R2', 'CPR_R2'),
        'Resistance 3': ('Daily R3', 'CPR_R3'),
        'Support 1': ('Daily S1', 'CPR_S1'),
        'Support 2': ('Daily S2', 'CPR_S2'),
        'Support 3': ('Daily S3', 'CPR_S3'),
        'Previous High': ('Prev Day High', 'CPR_Prev_High'),
        'Previous Low': ('Prev Day Low', 'CPR_Prev_Low')
    }

    print("=== CPR VALUES COMPARISON REPORT ===\n")
    print(f"Dataset: {len(df)} rows")
    if 'datetime' in df.columns:
        print(f"Date range: {df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}")
    print("\n" + "="*80)

    # Create comparison results
    results = []
    max_pct_diff = 0

    for level_name, (tv_col, our_col) in comparisons.items():
        if tv_col not in df.columns or our_col not in df.columns:
            print(f"⚠️  Skipping {level_name}: Missing columns {tv_col} or {our_col}")
            continue

        # Calculate differences
        diff = df[tv_col] - df[our_col]
        abs_diff = np.abs(diff)

        # Calculate percentage difference
        pct_diff = (abs_diff / df[tv_col]) * 100
        max_pct_this_level = pct_diff.max()
        max_pct_diff = max(max_pct_diff, max_pct_this_level)

        # Statistics
        perfect_matches = (abs_diff < 0.01).sum()
        close_matches = (abs_diff < 0.1).sum()
        very_close_matches = (abs_diff < 1.0).sum()

        print(f"\n{level_name}:")
        print(f"  Max difference: {abs_diff.max():.2f} points ({max_pct_this_level:.4f}%)")
        print(f"  Mean difference: {abs_diff.mean():.2f} points ({pct_diff.mean():.4f}%)")
        print(f"  Perfect matches (< 0.01): {perfect_matches}/{len(df)} ({perfect_matches/len(df)*100:.1f}%)")
        print(f"  Close matches (< 0.1): {close_matches}/{len(df)} ({close_matches/len(df)*100:.1f}%)")

        results.append({
            'level': level_name,
            'max_abs_diff': abs_diff.max(),
            'mean_abs_diff': abs_diff.mean(),
            'max_pct_diff': max_pct_this_level,
            'mean_pct_diff': pct_diff.mean(),
            'perfect_matches': perfect_matches,
            'close_matches': close_matches,
            'total_rows': len(df)
        })

    # Overall assessment
    print("\n" + "="*80)
    print("OVERALL ASSESSMENT:")

    if max_pct_diff < 0.1:
        status = "🎉 PERFECT!"
        message = "All differences are < 0.1% - Your calculations are spot-on!"
    elif max_pct_diff < 0.5:
        status = "🎉 EXCELLENT!"
        message = "All differences are < 0.5% - This is AWESOME for trading!"
    elif max_pct_diff < 1.0:
        status = "✅ VERY GOOD!"
        message = "All differences are < 1.0% - This is great for trading!"
    else:
        status = "⚠️  NEEDS REVIEW"
        message = "Some differences exceed 1% - might need fine-tuning."

    print(f"{status} Maximum difference: {max_pct_diff:.4f}%")
    print(f"{message}")

    if max_pct_diff < 1.0:
        print("\n✅ Your CPR calculations are highly accurate and suitable for professional trading!")
        print("✅ Minor differences are likely due to rounding or precision variations.")
        print("✅ This level of accuracy is MORE than sufficient for trading purposes!")

    return {
        'max_percentage_difference': max_pct_diff,
        'status': status,
        'message': message,
        'detailed_results': results,
        'is_trading_ready': max_pct_diff < 1.0
    }

# Example usage:
if __name__ == "__main__":
    # Replace with your CSV file path
    results = compare_cpr_values('tradeview_utc.csv')

    # You can access the results programmatically:
    print(f"\nProgrammatic Results:")
    print(f"Trading Ready: {results['is_trading_ready']}")
    print(f"Max Difference: {results['max_percentage_difference']:.4f}%")
