import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import configparser
import os

class TechnicalIndicatorsCalculator:
    """
    Technical Indicators Calculator that appends calculated columns to the original input file
    - Implements: Supertrend, Williams %R, Stochastic RSI, Multiple EMAs, CPR
    - Modifies the original CSV by adding indicator columns
    - Creates backup of original file
    - No hardcoded dates
    - Configurable via config file
    """

    def __init__(self, config_file='indicators_config.ini'):
        self.config = configparser.ConfigParser()
        self.config_file = config_file
        self.load_config()

    def load_config(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
            print(f"✅ Loaded configuration from {self.config_file}")
        else:
            print(f"⚠️  Config file {self.config_file} not found. Using defaults.")
            self.create_default_config()

    def create_default_config(self):
        """Create default configuration"""
        self.config['DEFAULT'] = {
            'input_file': 'tradeview_utc.csv',
            'show_detailed_output': 'true',
            'show_comparison': 'true',
            'overwrite_existing_columns': 'true'
        }

        self.config['SUPERTREND'] = {
            'period': '10',
            'multiplier': '3.0'
        }

        self.config['WILLIAMS_R'] = {
            'period_1': '9',
            'period_2': '28'
        }

        self.config['STOCHASTIC_RSI'] = {
            'k_period': '3',
            'd_period': '3',
            'rsi_period': '14',
            'stoch_period': '14'
        }

        self.config['EMA'] = {
            'periods': '9,15,21'
        }

        self.config['CPR'] = {
            'calculation_method': 'tradingview_compatible'
        }

        self.config['MANUAL_DATA'] = {
            'high': '',
            'low': '',
            'close': ''
        }

    def load_data(self):
        """Load and prepare data"""
        input_file = self.config.get('DEFAULT', 'input_file', fallback='tradeview_utc.csv')

        try:
            df = pd.read_csv(input_file)
            df['datetime'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('datetime', inplace=True)

            print(f"✅ Loaded {len(df)} rows from {input_file}")
            print(f"📅 Date range: {df.index.min()} to {df.index.max()}")

            return df, input_file
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return None, None

    def calculate_atr(self, df, period=14):
        """Calculate Average True Range"""
        high = df['high']
        low = df['low']
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr

    def calculate_supertrend(self, df, period=10, multiplier=3.0):
        """Calculate Supertrend indicator - Completely fixed version"""
        atr = self.calculate_atr(df, period)

        hl2 = (df['high'] + df['low']) / 2
        close = df['close']

        # Calculate basic upper and lower bands
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)

        # Initialize arrays with NaN
        final_upper_band = pd.Series(index=df.index, dtype=float)
        final_lower_band = pd.Series(index=df.index, dtype=float)
        supertrend = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(index=df.index, dtype=int)

        # Find first valid index (where ATR is not NaN)
        first_valid_idx = atr.first_valid_index()
        if first_valid_idx is None:
            return pd.Series(index=df.index, dtype=float), pd.Series(index=df.index, dtype=float)

        first_valid_pos = df.index.get_loc(first_valid_idx)

        # Set initial values
        final_upper_band.iloc[first_valid_pos] = upper_band.iloc[first_valid_pos]
        final_lower_band.iloc[first_valid_pos] = lower_band.iloc[first_valid_pos]
        direction.iloc[first_valid_pos] = 1  # Start with uptrend
        supertrend.iloc[first_valid_pos] = final_lower_band.iloc[first_valid_pos]

        # Calculate final bands
        for i in range(first_valid_pos + 1, len(df)):
            # Calculate final upper band
            if (upper_band.iloc[i] < final_upper_band.iloc[i-1]) or (close.iloc[i-1] > final_upper_band.iloc[i-1]):
                final_upper_band.iloc[i] = upper_band.iloc[i]
            else:
                final_upper_band.iloc[i] = final_upper_band.iloc[i-1]

            # Calculate final lower band
            if (lower_band.iloc[i] > final_lower_band.iloc[i-1]) or (close.iloc[i-1] < final_lower_band.iloc[i-1]):
                final_lower_band.iloc[i] = lower_band.iloc[i]
            else:
                final_lower_band.iloc[i] = final_lower_band.iloc[i-1]

        # Calculate Supertrend and direction
        for i in range(first_valid_pos + 1, len(df)):
            # Determine direction and supertrend value
            if (supertrend.iloc[i-1] == final_upper_band.iloc[i-1]) and (close.iloc[i] <= final_upper_band.iloc[i]):
                supertrend.iloc[i] = final_upper_band.iloc[i]
                direction.iloc[i] = -1
            elif (supertrend.iloc[i-1] == final_upper_band.iloc[i-1]) and (close.iloc[i] > final_upper_band.iloc[i]):
                supertrend.iloc[i] = final_lower_band.iloc[i]
                direction.iloc[i] = 1
            elif (supertrend.iloc[i-1] == final_lower_band.iloc[i-1]) and (close.iloc[i] >= final_lower_band.iloc[i]):
                supertrend.iloc[i] = final_lower_band.iloc[i]
                direction.iloc[i] = 1
            elif (supertrend.iloc[i-1] == final_lower_band.iloc[i-1]) and (close.iloc[i] < final_lower_band.iloc[i]):
                supertrend.iloc[i] = final_upper_band.iloc[i]
                direction.iloc[i] = -1
            else:
                supertrend.iloc[i] = supertrend.iloc[i-1]
                direction.iloc[i] = direction.iloc[i-1]

        # Create up_trend and down_trend columns
        up_trend = pd.Series(index=df.index, dtype=float)
        down_trend = pd.Series(index=df.index, dtype=float)

        # Fill values based on direction
        for i in range(len(df)):
            if direction.iloc[i] == 1:
                up_trend.iloc[i] = supertrend.iloc[i]
            elif direction.iloc[i] == -1:
                down_trend.iloc[i] = supertrend.iloc[i]

        return up_trend, down_trend

    def calculate_williams_r(self, df, period=14):
        """Calculate Williams %R"""
        high_max = df['high'].rolling(window=period).max()
        low_min = df['low'].rolling(window=period).min()

        williams_r = -100 * (high_max - df['close']) / (high_max - low_min)

        return williams_r

    def calculate_rsi(self, df, period=14):
        """Calculate RSI using Wilder's smoothing method"""
        delta = df['close'].diff()

        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # Use Wilder's smoothing (similar to EMA with alpha = 1/period)
        alpha = 1.0 / period
        avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
        avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def calculate_stochastic_rsi(self, df, k_period=3, d_period=3, rsi_period=14, stoch_period=14):
        """Calculate Stochastic RSI - Improved version"""
        rsi = self.calculate_rsi(df, rsi_period)

        # Calculate Stochastic of RSI
        rsi_min = rsi.rolling(window=stoch_period).min()
        rsi_max = rsi.rolling(window=stoch_period).max()

        # Avoid division by zero
        rsi_range = rsi_max - rsi_min
        stoch_rsi = np.where(rsi_range != 0, (rsi - rsi_min) / rsi_range * 100, 50)
        stoch_rsi = pd.Series(stoch_rsi, index=df.index)

        # Calculate %K and %D using SMA instead of EMA for TradingView compatibility
        k = stoch_rsi.rolling(window=k_period).mean()
        d = k.rolling(window=d_period).mean()

        return k, d

    def calculate_ema(self, df, period=21):
        """Calculate Exponential Moving Average"""
        return df['close'].ewm(span=period, adjust=False).mean()

    def get_ema_periods(self):
        """Parse EMA periods from config"""
        periods_str = self.config.get('EMA', 'periods', fallback='9,15,21')
        try:
            periods = [int(p.strip()) for p in periods_str.split(',')]
            return periods
        except ValueError:
            print("⚠️  Invalid EMA periods in config. Using default: [9, 15, 21]")
            return [9, 15, 21]

    def get_manual_prev_day_data(self):
        """Get manual previous day data from config if available"""
        try:
            high = self.config.get('MANUAL_DATA', 'high')
            low = self.config.get('MANUAL_DATA', 'low')
            close = self.config.get('MANUAL_DATA', 'close')

            if high and low and close:
                return {
                    'high': float(high),
                    'low': float(low),
                    'close': float(close)
                }
        except:
            pass
        return None

    def estimate_prev_day_data(self, df):
        """Estimate previous day data when manual data is not provided - EXACT COPY FROM WORKING VERSION"""
        # Use existing previous day data from the first row if available
        if 'Prev Day High' in df.columns and 'Prev Day Low' in df.columns:
            first_row = df.iloc[0]
            prev_high = first_row['Prev Day High']
            prev_low = first_row['Prev Day Low']

            # Estimate close from existing pivot if available
            if 'Daily Pivot' in df.columns:
                existing_cp = first_row['Daily Pivot']
                prev_close = 3 * existing_cp - prev_high - prev_low
            else:
                prev_close = (prev_high + prev_low) / 2

            return {
                'high': prev_high,
                'low': prev_low,
                'close': prev_close,
                'source': 'existing_csv_data'
            }
        else:
            # Use first day's data as fallback
            first_date = df.index.date[0]
            first_day_data = df[df.index.date == first_date]
            return {
                'high': first_day_data['high'].max(),
                'low': first_day_data['low'].min(),
                'close': first_day_data['close'].iloc[-1],
                'source': 'first_day_fallback'
            }

    def calculate_and_append_cpr(self, df):
        """Calculate CPR and append columns to the dataframe - EXACT COPY FROM WORKING VERSION"""
        # Get manual previous day data or estimate it
        manual_data = self.get_manual_prev_day_data()
        if manual_data:
            prev_day_data = manual_data
            print(f"\n🔧 Using manual previous day data: H={prev_day_data['high']}, L={prev_day_data['low']}, C={prev_day_data['close']}")
        else:
            prev_day_data = self.estimate_prev_day_data(df)
            print(f"\n🤖 Estimated previous day data ({prev_day_data['source']}): H={prev_day_data['high']:.2f}, L={prev_day_data['low']:.2f}, C={prev_day_data['close']:.2f}")

        # Create a copy to work with
        data = df.copy()
        data['date'] = data.index.date

        # Calculate daily OHLC values
        daily_ohlc = data.groupby('date').agg({
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }).reset_index()

        # Get PREVIOUS day's OHLC values for CPR calculation
        daily_ohlc['prev_high'] = daily_ohlc['high'].shift(1)
        daily_ohlc['prev_low'] = daily_ohlc['low'].shift(1)
        daily_ohlc['prev_close'] = daily_ohlc['close'].shift(1)

        # Handle first day with previous day data
        if len(daily_ohlc) > 0:
            daily_ohlc.loc[0, 'prev_high'] = prev_day_data['high']
            daily_ohlc.loc[0, 'prev_low'] = prev_day_data['low']
            daily_ohlc.loc[0, 'prev_close'] = prev_day_data['close']

        # CPR Calculations using PREVIOUS day's data
        daily_ohlc['CPR_CP'] = (daily_ohlc['prev_high'] + daily_ohlc['prev_low'] + daily_ohlc['prev_close']) / 3
        daily_ohlc['CPR_BC'] = (daily_ohlc['prev_high'] + daily_ohlc['prev_low']) / 2
        daily_ohlc['CPR_TC'] = (2 * daily_ohlc['CPR_CP']) - daily_ohlc['CPR_BC']

        # Traditional Pivot Points
        daily_ohlc['CPR_R1'] = (2 * daily_ohlc['CPR_CP']) - daily_ohlc['prev_low']
        daily_ohlc['CPR_S1'] = (2 * daily_ohlc['CPR_CP']) - daily_ohlc['prev_high']
        daily_ohlc['CPR_R2'] = daily_ohlc['CPR_CP'] + (daily_ohlc['prev_high'] - daily_ohlc['prev_low'])
        daily_ohlc['CPR_S2'] = daily_ohlc['CPR_CP'] - (daily_ohlc['prev_high'] - daily_ohlc['prev_low'])
        daily_ohlc['CPR_R3'] = daily_ohlc['prev_high'] + 2 * (daily_ohlc['CPR_CP'] - daily_ohlc['prev_low'])
        daily_ohlc['CPR_S3'] = daily_ohlc['prev_low'] - 2 * (daily_ohlc['prev_high'] - daily_ohlc['CPR_CP'])

        # Previous Day's High and Low
        daily_ohlc['CPR_Prev_High'] = daily_ohlc['prev_high']
        daily_ohlc['CPR_Prev_Low'] = daily_ohlc['prev_low']

        # Show detailed output if configured
        if self.config.getboolean('DEFAULT', 'show_detailed_output', fallback=True):
            self.print_daily_calculations(daily_ohlc)

        # Show comparison with existing data if available and configured
        if self.config.getboolean('DEFAULT', 'show_comparison', fallback=True):
            self.compare_with_existing_cpr(df, daily_ohlc)

        # Merge daily CPR levels back to minute-level data
        cpr_columns = ['CPR_CP', 'CPR_BC', 'CPR_TC', 'CPR_R1', 'CPR_R2', 'CPR_R3', 
                       'CPR_S1', 'CPR_S2', 'CPR_S3', 'CPR_Prev_High', 'CPR_Prev_Low']

        data = data.merge(daily_ohlc[['date'] + cpr_columns], on='date', how='left')

        # Add CPR columns to original dataframe - CRITICAL: Use .values to ensure proper assignment
        for col in cpr_columns:
            df[col] = data[col].values

        return df, cpr_columns

    def print_daily_calculations(self, daily_ohlc):
        """Print detailed daily CPR calculations"""
        print("\n" + "="*80)
        print("📈 CALCULATED CPR VALUES TO BE APPENDED")
        print("="*80)

        for idx, row in daily_ohlc.iterrows():
            if not pd.isna(row['CPR_CP']):
                print(f"📅 Date: {row['date']}")
                print(f"   Previous Day: H={row['prev_high']:.2f}, L={row['prev_low']:.2f}, C={row['prev_close']:.2f}")
                print(f"   🎯 CPR: CP={row['CPR_CP']:.2f}, BC={row['CPR_BC']:.2f}, TC={row['CPR_TC']:.2f}")
                print(f"   📈 Resistance: R1={row['CPR_R1']:.2f}, R2={row['CPR_R2']:.2f}, R3={row['CPR_R3']:.2f}")
                print(f"   📉 Support: S1={row['CPR_S1']:.2f}, S2={row['CPR_S2']:.2f}, S3={row['CPR_S3']:.2f}")
                print()

    def compare_with_existing_cpr(self, df, daily_ohlc):
        """Compare calculated CPR values with existing data in CSV"""
        if 'Daily Pivot' not in df.columns:
            return

        print("\n" + "="*60)
        print("🔍 COMPARISON WITH EXISTING CPR DATA")
        print("="*60)

        # Get first available date for comparison
        first_date = daily_ohlc.iloc[0]['date']
        existing_data = df[df.index.date == first_date].iloc[0]
        calculated_data = daily_ohlc.iloc[0]

        print(f"📅 Comparing data for: {first_date}")
        print("\nExisting vs New CPR Columns:")
        print(f"  Pivot: {existing_data['Daily Pivot']:.2f} vs {calculated_data['CPR_CP']:.2f} (Diff: {abs(existing_data['Daily Pivot'] - calculated_data['CPR_CP']):.2f})")
        print(f"  BC:    {existing_data['Daily BC']:.2f} vs {calculated_data['CPR_BC']:.2f} (Diff: {abs(existing_data['Daily BC'] - calculated_data['CPR_BC']):.2f})")
        print(f"  TC:    {existing_data['Daily TC']:.2f} vs {calculated_data['CPR_TC']:.2f} (Diff: {abs(existing_data['Daily TC'] - calculated_data['CPR_TC']):.2f})")

    def calculate_and_append_indicators(self, df):
        """Calculate all indicators and append columns to the dataframe"""
        print("\n🔧 Calculating Technical Indicators...")

        # Get parameters from config
        supertrend_period = self.config.getint('SUPERTREND', 'period', fallback=10)
        supertrend_multiplier = self.config.getfloat('SUPERTREND', 'multiplier', fallback=3.0)

        williams_period_1 = self.config.getint('WILLIAMS_R', 'period_1', fallback=9)
        williams_period_2 = self.config.getint('WILLIAMS_R', 'period_2', fallback=28)

        stoch_k_period = self.config.getint('STOCHASTIC_RSI', 'k_period', fallback=3)
        stoch_d_period = self.config.getint('STOCHASTIC_RSI', 'd_period', fallback=3)
        stoch_rsi_period = self.config.getint('STOCHASTIC_RSI', 'rsi_period', fallback=14)
        stoch_stoch_period = self.config.getint('STOCHASTIC_RSI', 'stoch_period', fallback=14)

        ema_periods = self.get_ema_periods()

        # Calculate indicators
        print(f"📈 Calculating Supertrend ({supertrend_period}, {supertrend_multiplier})...")
        up_trend, down_trend = self.calculate_supertrend(df, supertrend_period, supertrend_multiplier)

        print(f"📊 Calculating Williams %R ({williams_period_1}, {williams_period_2})...")
        williams_r_1 = self.calculate_williams_r(df, williams_period_1)
        williams_r_2 = self.calculate_williams_r(df, williams_period_2)

        print(f"🎯 Calculating Stochastic RSI ({stoch_k_period}, {stoch_d_period}, {stoch_rsi_period}, {stoch_stoch_period})...")
        stoch_k, stoch_d = self.calculate_stochastic_rsi(df, stoch_k_period, stoch_d_period, stoch_rsi_period, stoch_stoch_period)

        print(f"📉 Calculating EMAs {ema_periods}...")
        emas = {}
        for period in ema_periods:
            emas[period] = self.calculate_ema(df, period)

        print(f"🎯 Calculating CPR...")
        df_with_cpr, cpr_columns = self.calculate_and_append_cpr(df)

        # Add other indicator columns to dataframe
        new_columns = []

        # Supertrend columns
        df[f'ST_Up_Trend_{supertrend_period}_{supertrend_multiplier}'] = up_trend
        df[f'ST_Down_Trend_{supertrend_period}_{supertrend_multiplier}'] = down_trend
        new_columns.extend([f'ST_Up_Trend_{supertrend_period}_{supertrend_multiplier}', 
                           f'ST_Down_Trend_{supertrend_period}_{supertrend_multiplier}'])

        # Williams %R columns
        df[f'Williams_R_{williams_period_1}'] = williams_r_1
        df[f'Williams_R_{williams_period_2}'] = williams_r_2
        new_columns.extend([f'Williams_R_{williams_period_1}', f'Williams_R_{williams_period_2}'])

        # Stochastic RSI columns
        df[f'Stoch_RSI_K_{stoch_k_period}_{stoch_d_period}_{stoch_rsi_period}_{stoch_stoch_period}'] = stoch_k
        df[f'Stoch_RSI_D_{stoch_k_period}_{stoch_d_period}_{stoch_rsi_period}_{stoch_stoch_period}'] = stoch_d
        new_columns.extend([f'Stoch_RSI_K_{stoch_k_period}_{stoch_d_period}_{stoch_rsi_period}_{stoch_stoch_period}',
                           f'Stoch_RSI_D_{stoch_k_period}_{stoch_d_period}_{stoch_rsi_period}_{stoch_stoch_period}'])

        # EMA columns
        for period in ema_periods:
            df[f'EMA_{period}'] = emas[period]
            new_columns.append(f'EMA_{period}')

        # Add CPR columns to new_columns list
        new_columns.extend(cpr_columns)

        # Show detailed output if configured
        if self.config.getboolean('DEFAULT', 'show_detailed_output', fallback=True):
            self.print_indicator_summary(df, new_columns)

        # Show comparison with existing data if available and configured
        if self.config.getboolean('DEFAULT', 'show_comparison', fallback=True):
            self.compare_with_existing(df)

        return df, new_columns

    def print_indicator_summary(self, df, new_columns):
        """Print summary of calculated indicators"""
        print("\n" + "="*80)
        print("📈 CALCULATED TECHNICAL INDICATORS SUMMARY")
        print("="*80)

        for col in new_columns:
            if col in df.columns:
                series = df[col].dropna()
                if len(series) > 0:
                    print(f"📊 {col}:")
                    print(f"   Range: {series.min():.2f} to {series.max():.2f}")
                    print(f"   Latest: {series.iloc[-1]:.2f}")
                    print(f"   Valid values: {len(series)}/{len(df)}")
                    print()

    def compare_with_existing(self, df):
        """Compare calculated values with existing data in CSV (excluding EMAs)"""
        print("\n" + "="*60)
        print("🔍 COMPARISON WITH EXISTING TRADINGVIEW DATA")
        print("="*60)

        comparisons = [
            ('Up Trend', 'ST_Up_Trend_10_3.0', 'Supertrend Up'),
            ('Down Trend', 'ST_Down_Trend_10_3.0', 'Supertrend Down'),
            ('%R', 'Williams_R_9', 'Williams %R (9)'),
            ('%R.1', 'Williams_R_28', 'Williams %R (28)'),
            ('K', 'Stoch_RSI_K_3_3_14_14', 'Stochastic RSI K'),
            ('D', 'Stoch_RSI_D_3_3_14_14', 'Stochastic RSI D'),
            ('Daily Pivot', 'CPR_CP', 'CPR Central Pivot'),
            ('Daily BC', 'CPR_BC', 'CPR Bottom Central'),
            ('Daily TC', 'CPR_TC', 'CPR Top Central'),
            ('Daily R1', 'CPR_R1', 'CPR Resistance 1'),
            ('Daily S1', 'CPR_S1', 'CPR Support 1'),
            ('Prev Day High', 'CPR_Prev_High', 'CPR Previous Day High'),
            ('Prev Day Low', 'CPR_Prev_Low', 'CPR Previous Day Low')
            # Note: EMA comparison removed as requested
        ]

        for existing_col, new_col, description in comparisons:
            if existing_col in df.columns and new_col in df.columns:
                existing_data = df[existing_col].dropna()
                new_data = df[new_col].dropna()

                if len(existing_data) > 0 and len(new_data) > 0:
                    # Find overlapping indices
                    common_indices = existing_data.index.intersection(new_data.index)
                    if len(common_indices) > 0:
                        # Take last 10 common values
                        comparison_indices = common_indices[-min(10, len(common_indices)):]

                        existing_sample = existing_data.loc[comparison_indices]
                        new_sample = new_data.loc[comparison_indices]

                        # Calculate differences
                        diff = abs(existing_sample - new_sample)
                        avg_diff = diff.mean()
                        max_diff = diff.max()

                        print(f"📊 {description}:")
                        print(f"   Average difference: {avg_diff:.4f}")
                        print(f"   Maximum difference: {max_diff:.4f}")
                        print(f"   Latest values - Existing: {existing_sample.iloc[-1]:.4f}, Calculated: {new_sample.iloc[-1]:.4f}")
                        print()

    def save_updated_file(self, df, input_file, new_columns):
        """Save the updated dataframe back to the input file"""
        try:
            # Reset index to include datetime as a column
            df_output = df.reset_index()

            # Save back to original file
            df_output.to_csv(input_file, index=False)

            print(f"\n💾 UPDATED ORIGINAL FILE: {input_file}")
            print(f"✅ Added {len(new_columns)} new indicator columns:")
            for col in new_columns:
                print(f"   📊 {col}")

            return True
        except Exception as e:
            print(f"❌ Error saving file: {e}")
            return False

    def run(self):
        """Main execution method"""
        print("="*70)
        print("🚀 TECHNICAL INDICATORS CALCULATOR - WITH CPR")
        print("="*70)

        # Load data
        df, input_file = self.load_data()
        if df is None:
            return None

        # Calculate indicators and append to dataframe
        df_updated, new_columns = self.calculate_and_append_indicators(df)

        # Save updated file
        success = self.save_updated_file(df_updated, input_file, new_columns)

        if success:
            print("\n🎉 SUCCESS!")
            print(f"📊 Original file updated with technical indicator columns")
            print(f"📁 File: {input_file}")
            print(f"📈 Total rows: {len(df_updated)}")
            print(f"🎯 New columns: {len(new_columns)}")

        return df_updated

def main():
    """Main function"""
    calculator = TechnicalIndicatorsCalculator()
    result = calculator.run()
    return result

if __name__ == "__main__":
    result = main()
