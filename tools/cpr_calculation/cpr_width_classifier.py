
import pandas as pd
import numpy as np

def extract_daily_cpr_data(csv_file_path):
    """
    Extract unique daily CPR values from minute-wise trading data

    Parameters:
    -----------
    csv_file_path : str
        Path to the CSV file containing trading data

    Returns:
    --------
    pandas.DataFrame with unique daily CPR values
    """
    # Load the data
    df = pd.read_csv(csv_file_path)

    # Convert datetime column to proper datetime format
    df['datetime'] = pd.to_datetime(df['datetime'])

    # Extract date from datetime
    df['date'] = df['datetime'].dt.date

    # Extract unique daily CPR values (first occurrence of each date)
    daily_cpr = df.groupby('date').first().reset_index()

    # Keep only the relevant columns for CPR analysis
    daily_cpr = daily_cpr[['date', 'Daily Pivot', 'Daily BC', 'Daily TC']].copy()

    return daily_cpr

def classify_daily_cpr_width(df, method='percentile', narrow_threshold=0.1, wide_threshold=0.2, std_multiplier=0.5):
    """
    Classify Daily CPR width as Narrow, Wide, or Average

    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with columns ['date', 'Daily Pivot', 'Daily BC', 'Daily TC']
    method : str
        Classification method:
        - 'percentile': Uses 25th and 75th percentiles (recommended for larger datasets)
        - 'std': Uses standard deviation (good for normal distributions)
        - 'fixed': Uses fixed percentage thresholds (consistent across all datasets)
    narrow_threshold : float
        Fixed threshold for narrow CPR (used only with 'fixed' method)
    wide_threshold : float
        Fixed threshold for wide CPR (used only with 'fixed' method)
    std_multiplier : float
        Standard deviation multiplier (used only with 'std' method)

    Returns:
    --------
    pandas.DataFrame with additional columns for CPR width classification
    """

    df = df.copy()

    # Calculate CPR Width (TC - BC)
    df['CPR_Width'] = df['Daily TC'] - df['Daily BC']

    # Calculate CPR Width as percentage of Pivot (for normalization)
    df['CPR_Width_Pct'] = (df['CPR_Width'] / df['Daily Pivot']) * 100

    if method == 'percentile':
        # Method 1: Percentile-based classification
        p25 = df['CPR_Width_Pct'].quantile(0.25)
        p75 = df['CPR_Width_Pct'].quantile(0.75)

        def classify_percentile(width_pct):
            if width_pct <= p25:
                return 'Narrow'
            elif width_pct >= p75:
                return 'Wide'
            else:
                return 'Average'

        df['CPR_Classification'] = df['CPR_Width_Pct'].apply(classify_percentile)
        df['Narrow_Threshold'] = p25
        df['Wide_Threshold'] = p75

    elif method == 'std':
        # Method 2: Standard deviation-based classification
        mean_width = df['CPR_Width_Pct'].mean()
        std_width = df['CPR_Width_Pct'].std()

        narrow_thresh = mean_width - (std_multiplier * std_width)
        wide_thresh = mean_width + (std_multiplier * std_width)

        def classify_std(width_pct):
            if width_pct <= narrow_thresh:
                return 'Narrow'
            elif width_pct >= wide_thresh:
                return 'Wide'
            else:
                return 'Average'

        df['CPR_Classification'] = df['CPR_Width_Pct'].apply(classify_std)
        df['Narrow_Threshold'] = narrow_thresh
        df['Wide_Threshold'] = wide_thresh

    elif method == 'fixed':
        # Method 3: Fixed threshold classification
        def classify_fixed(width_pct):
            if width_pct <= narrow_threshold:
                return 'Narrow'
            elif width_pct >= wide_threshold:
                return 'Wide'
            else:
                return 'Average'

        df['CPR_Classification'] = df['CPR_Width_Pct'].apply(classify_fixed)
        df['Narrow_Threshold'] = narrow_threshold
        df['Wide_Threshold'] = wide_threshold

    return df

def analyze_cpr_classification(df):
    """
    Analyze and display CPR classification results
    """
    print("CPR WIDTH CLASSIFICATION ANALYSIS")
    print("=" * 50)
    print(f"Dataset: {len(df)} trading days")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")

    print(f"\nCPR Width Statistics:")
    print(f"  Mean: {df['CPR_Width'].mean():.2f} points ({df['CPR_Width_Pct'].mean():.4f}%)")
    print(f"  Std:  {df['CPR_Width'].std():.2f} points ({df['CPR_Width_Pct'].std():.4f}%)")
    print(f"  Min:  {df['CPR_Width'].min():.2f} points ({df['CPR_Width_Pct'].min():.4f}%)")
    print(f"  Max:  {df['CPR_Width'].max():.2f} points ({df['CPR_Width_Pct'].max():.4f}%)")

    print(f"\nClassification Distribution:")
    classification_counts = df['CPR_Classification'].value_counts()
    for classification, count in classification_counts.items():
        percentage = (count / len(df)) * 100
        print(f"  {classification}: {count} days ({percentage:.1f}%)")

    print(f"\nThresholds Used:")
    if 'Narrow_Threshold' in df.columns:
        print(f"  Narrow (≤): {df['Narrow_Threshold'].iloc[0]:.4f}%")
        print(f"  Wide (≥):   {df['Wide_Threshold'].iloc[0]:.4f}%")

    return classification_counts

# Main execution function
def main():
    """
    Main function to process CPR data and classify width
    """
    # Step 1: Extract daily CPR data
    print("Step 1: Extracting daily CPR data...")
    daily_cpr = extract_daily_cpr_data('tradeview_utc.csv')

    # Step 2: Classify CPR width using different methods
    print("\nStep 2: Classifying CPR width...")

    # Method 1: Fixed thresholds (recommended for consistency)
    print("\n" + "="*60)
    print("FIXED THRESHOLD METHOD (Recommended)")
    print("="*60)
    result_fixed = classify_daily_cpr_width(daily_cpr, method='fixed', 
                                          narrow_threshold=0.1, wide_threshold=0.2)
    analyze_cpr_classification(result_fixed)

    # Method 2: Percentile-based (good for relative analysis)
    print("\n" + "="*60)
    print("PERCENTILE METHOD")
    print("="*60)
    result_percentile = classify_daily_cpr_width(daily_cpr, method='percentile')
    analyze_cpr_classification(result_percentile)

    # Method 3: Standard deviation (good for normal distributions)
    print("\n" + "="*60)
    print("STANDARD DEVIATION METHOD")
    print("="*60)
    result_std = classify_daily_cpr_width(daily_cpr, method='std')
    analyze_cpr_classification(result_std)

    # Step 3: Display detailed results
    print("\n" + "="*60)
    print("DETAILED DAILY RESULTS")
    print("="*60)

    # Use fixed method as primary result
    final_result = result_fixed[['date', 'Daily Pivot', 'Daily BC', 'Daily TC', 
                               'CPR_Width', 'CPR_Width_Pct', 'CPR_Classification']].copy()

    print(final_result.round(4))

    # Step 4: Save results
    final_result.to_csv('daily_cpr_classification.csv', index=False)
    print("\n✅ Results saved to 'daily_cpr_classification.csv'")

    return final_result

# Trading insights function
def get_trading_insights(df):
    """
    Provide trading insights based on CPR classification
    """
    print("\n" + "="*60)
    print("TRADING INSIGHTS")
    print("="*60)

    narrow_days = df[df['CPR_Classification'] == 'Narrow']
    wide_days = df[df['CPR_Classification'] == 'Wide']
    average_days = df[df['CPR_Classification'] == 'Average']

    print(f"📊 NARROW CPR Days ({len(narrow_days)}):")
    print("   • Indicates consolidation/sideways movement")
    print("   • Look for breakout opportunities")
    print("   • Lower volatility expected")
    if len(narrow_days) > 0:
        print(f"   • Average width: {narrow_days['CPR_Width_Pct'].mean():.4f}%")

    print(f"\n📊 WIDE CPR Days ({len(wide_days)}):")
    print("   • Indicates high volatility/trending market")
    print("   • Strong directional moves expected")
    print("   • Good for trend-following strategies")
    if len(wide_days) > 0:
        print(f"   • Average width: {wide_days['CPR_Width_Pct'].mean():.4f}%")

    print(f"\n📊 AVERAGE CPR Days ({len(average_days)}):")
    print("   • Normal market conditions")
    print("   • Moderate volatility expected")
    print("   • Standard trading strategies applicable")
    if len(average_days) > 0:
        print(f"   • Average width: {average_days['CPR_Width_Pct'].mean():.4f}%")

if __name__ == "__main__":
    # Execute main analysis
    result = main()

    # Provide trading insights
    get_trading_insights(result)
