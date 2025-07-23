import os
from kiteconnect import KiteConnect
from datetime import datetime, date, timedelta
import pandas as pd
import time

# --- Authentication function (no changes needed here) ---
def get_kite_client():
    """
    Reads API key/secret and access token to initialize and return a KiteConnect client.
    """
    try:
        api_key_path = "./key_secrets/api_key.txt"
        with open(api_key_path, 'r') as f:
            lines = f.readlines()
            api_key = lines[0].strip()
            api_secret = lines[1].strip()

        access_token_path = "./key_secrets/access_token.txt"
        with open(access_token_path, 'r') as f:
            access_token = f.read().strip()

        kite = KiteConnect(api_key=api_key)
        kite.set_access_token(access_token)
        print("Kite client initialized successfully.")
        return kite
    except Exception as e:
        print(f"Error during authentication: {e}")
        return None

# --- Instrument token helper (no changes needed here) ---
def get_instrument_token(ticker, kite_client):
    """
    Fetches instrument token for a given ticker symbol.
    """
    instruments_csv = "instruments.csv"
    if not os.path.exists(instruments_csv):
        print("Downloading instruments list...")
        instruments = kite_client.instruments()
        pd.DataFrame(instruments).to_csv(instruments_csv, index=False)

    df = pd.read_csv(instruments_csv)
    token_row = df[(df['tradingsymbol'] == ticker) & (df['exchange'] == 'NSE')]
    if not token_row.empty:
        return token_row.iloc[0]['instrument_token']
    else:
        raise ValueError(f"Ticker {ticker} not found in NSE instruments.")

# --- NEW FUNCTION: Specifically for fetching today's data ---
def fetch_today_ohlc(ticker, interval, kite_client):
    """
    Fetches OHLC data for a given ticker from 9:15 AM today until now.
    """
    try:
        instrument_token = get_instrument_token(ticker, kite_client)
        
        # Define the time range for today
        from_date = datetime.now().replace(hour=9, minute=15, second=0, microsecond=0)
        to_date = datetime.now()

        # Check if the market has opened yet
        if to_date <= from_date:
            print("Market has not opened yet or it's before 9:15 AM.")
            return pd.DataFrame()

        print(f"Fetching data from {from_date.strftime('%Y-%m-%d %H:%M:%S')} to {to_date.strftime('%Y-%m-%d %H:%M:%S')}...")
        
        records = kite_client.historical_data(instrument_token, from_date, to_date, interval)
        return pd.DataFrame(records)

    except Exception as e:
        print(f"An error occurred in fetch_today_ohlc: {e}")
        return pd.DataFrame()

# --- Main execution block ---
if __name__ == "__main__":
    kite = get_kite_client()
    
    if kite:
        # Define parameters
        ticker_symbol = "INFY"
        time_interval = "minute"

        print(f"\nFetching today's OHLC data for {ticker_symbol}...")
        
        # Call the new, simpler function
        ohlc_today = fetch_today_ohlc(ticker_symbol, time_interval, kite)

        # Print the result
        if not ohlc_today.empty:
            print("\n--- Today's OHLC Data Fetched ---")
            print(f"Total records found: {len(ohlc_today)}")
            print("Head (first 5 rows):")
            print(ohlc_today.head())
            print("\nTail (last 5 rows):")
            print(ohlc_today.tail())
        else:
            print("\nCould not fetch today's OHLC data. Please check errors above.")