import os
from kiteconnect import KiteConnect
from datetime import datetime, date, timedelta
import pandas as pd
import time

# --- Authentication function (reused from previous script) ---
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

def fetch_last_5min_data(instrument_token, kite_client):
    """Fetches the last 5 minutes of minute-interval data for a given token."""
    try:
        to_date = datetime.now()
        from_date = to_date - timedelta(minutes=5)
        records = kite_client.historical_data(instrument_token, from_date, to_date, "minute")
        return pd.DataFrame(records)
    except Exception as e:
        print(f"Could not fetch historical data for token {instrument_token}. Error: {e}")
        return pd.DataFrame()

# --- Main execution block ---
if __name__ == "__main__":
    kite = get_kite_client()
    
    if kite:
        # 1. Download/Load instruments data
        instruments_csv = "instruments.csv"
        if not os.path.exists(instruments_csv):
            print("Downloading instruments list...")
            pd.DataFrame(kite.instruments("NFO")).to_csv(instruments_csv, index=False)
        
        nfo_instruments = pd.read_csv(instruments_csv)
        # Convert expiry to datetime objects for comparison
        nfo_instruments['expiry'] = pd.to_datetime(nfo_instruments['expiry']).dt.date

        # 2. Find the next weekly expiry (Thursday)
        today = date.today()
        days_until_thursday = (3 - today.weekday() + 7) % 7
        expiry_date = today + timedelta(days=days_until_thursday)
        print(f"\nCalculated next expiry date: {expiry_date.strftime('%d-%b-%Y')}")

        # 3. Get the current price of Nifty 50
        try:
            ltp_data = kite.ltp('NSE:NIFTY 50')
            nifty_ltp = ltp_data['NSE:NIFTY 50']['last_price']
            print(f"Current Nifty 50 LTP: {nifty_ltp}")
        except Exception as e:
            print(f"Could not fetch Nifty LTP. Error: {e}")
            nifty_ltp = None

        if nifty_ltp:
            # 4. Calculate the closest 100-point strike price (ATM)
            atm_strike = round(nifty_ltp / 100) * 100
            print(f"At-The-Money (ATM) strike is: {atm_strike}")

            # Define the strikes we want to fetch (ITM, ATM, OTM)
            # Based on your example, you want the ATM CE and the next strike up for PE
            ce_strike = atm_strike
            pe_strike = atm_strike + 100 # As per your example for Nifty at 25040

            strikes_to_fetch = {
                "CE": ce_strike,
                "PE": pe_strike
            }

            print("\n--- Fetching Option Data ---")

            for option_type, strike_price in strikes_to_fetch.items():
                # 5. Find the option details from the instruments file
                option_row = nfo_instruments[
                    (nfo_instruments['name'] == 'NIFTY') &
                    (nfo_instruments['strike'] == strike_price) &
                    (nfo_instruments['instrument_type'] == option_type) &
                    (nfo_instruments['expiry'] == expiry_date)
                ]

                if not option_row.empty:
                    instrument = option_row.iloc[0]
                    token = instrument['instrument_token']
                    symbol = instrument['tradingsymbol']
                    
                    print(f"\nFound Ticker: {symbol}")
                    
                    # 6. Fetch and display the last 5 minutes of data
                    df_data = fetch_last_5min_data(token, kite)
                    if not df_data.empty:
                        print(df_data[['date', 'open', 'high', 'low', 'close', 'volume']].tail())
                    else:
                        print(f"No recent data found for {symbol}.")
                else:
                    print(f"\nCould not find NIFTY {expiry_date.strftime('%d%b%y').upper()} {strike_price} {option_type} in instruments list.")