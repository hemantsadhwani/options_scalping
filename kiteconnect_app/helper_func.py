import pandas as pd
import yaml
from kiteconnect import KiteConnect
from datetime import datetime, timedelta
import numpy as np
from technical_indicators import TechnicalIndicators

# Function to initialize Kite Connect API
def initialize_kiteconnect():
    """
    Initializes the Kite Connect API using the API key and access token.

    Returns:
        kite (KiteConnect): An instance of the KiteConnect API.
    """
    try:
        # Read access token and API key from files
        access_token = open("../key_secrets/access_token.txt", 'r').read().strip()
        key_secret = open("../key_secrets/api_key.txt", 'r').read().split()

        # Initialize Kite Connect
        kite = KiteConnect(api_key=key_secret[0])
        kite.set_access_token(access_token)
        return kite
    except FileNotFoundError as e:
        print(f"Error: Missing API key or access token file. {e}")
        return None
    except Exception as e:
        print(f"Error initializing Kite Connect: {e}")
        return None

# Function to fetch instrument_token for a given trading symbol
def get_instrument_token(kite, trading_symbol, segment="NFO"):
    """
    Fetches the instrument token for a given trading symbol.

    Args:
        kite (KiteConnect): An instance of the KiteConnect API.
        trading_symbol (str): The trading symbol (e.g., NIFTY24DEC23500PE).
        segment (str): The market segment (default is "NFO").

    Returns:
        int: The instrument token if found, otherwise None.
    """
    try:
        # Fetch the instruments list for the specified segment
        instruments = kite.instruments(segment)

        # Convert to DataFrame for easier filtering
        instruments_df = pd.DataFrame(instruments)

        # Filter the DataFrame for the given trading symbol
        filtered_df = instruments_df[instruments_df['tradingsymbol'] == trading_symbol]

        # Check if the trading symbol exists
        if not filtered_df.empty:
            # Return the instrument_token
            instrument_token = filtered_df.iloc[0]['instrument_token']
            return instrument_token
        else:
            print(f"Error: Trading symbol '{trading_symbol}' not found in the {segment} segment.")
            return None
    except Exception as e:
        print(f"Error fetching instrument token: {e}")
        return None

# Function to fetch OHLC data for a specific option
def fetch_option_ohlc(kite, instrument_token, no_of_days, candle_time_duration):
    """
    Fetches OHLC (Open, High, Low, Close) data for a specific option.

    Args:
        kite (KiteConnect): An instance of the KiteConnect API.
        instrument_token (int): The instrument token of the option.
        no_of_days (int): The number of days of historical data to fetch.
        candle_time_duration (str): The time interval for the data (e.g., '5min', '15min', '1hr', '1D').

    Returns:
        DataFrame: A DataFrame containing the OHLC data, or None if an error occurs.
    """
    try:
        # Calculate the date range for the last 'no_of_days' days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=no_of_days)

        # Fetch historical data
        historical_data = kite.historical_data(
            instrument_token=instrument_token,
            from_date=start_date.strftime("%Y-%m-%d %H:%M:%S"),
            to_date=end_date.strftime("%Y-%m-%d %H:%M:%S"),
            interval=candle_time_duration
        )

        # Convert to DataFrame for better readability
        df = pd.DataFrame(historical_data)
        return df
    except Exception as e:
        print(f"Error fetching OHLC data: {e}")
        return None

# Function to load configuration from YAML file
def load_config(config_file):
    """
    Loads configuration from a YAML file.

    Args:
        config_file (str): Path to the YAML configuration file.

    Returns:
        dict: A dictionary containing the configuration.
    """
    try:
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        return config
    except FileNotFoundError as e:
        print(f"Error: Configuration file not found. {e}")
        return None
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML file. {e}")
        return None

# Function to add technical indicators to OHLC data
def add_technical_indicators(ohlc_data):
    """
    Adds technical indicators (Supertrend, MACD, RSI, Williams %R) to the OHLC data.

    Args:
        ohlc_data (DataFrame): The OHLC data.

    Returns:
        DataFrame: The OHLC data with additional columns for technical indicators.
    """
    ti = TechnicalIndicators()

    # Add Supertrend (10, 3)
    ohlc_data['Supertrend(10,3)'] = ti.supertrend(ohlc_data, period=10, multiplier=3)['Supertrend']

    # Add MACD
    macd_data = ti.macd(ohlc_data)
    ohlc_data['MACD'] = macd_data['MACD']
    ohlc_data['Signal_Line'] = macd_data['Signal_Line']
    ohlc_data['MACD_Histogram'] = macd_data['MACD_Histogram']

    # Add RSI
    ohlc_data['RSI'] = ti.rsi(ohlc_data)['RSI']

    # Add Williams %R
    ohlc_data['Williams_%R'] = ti.williams_r(ohlc_data)['Williams_%R']

    return ohlc_data