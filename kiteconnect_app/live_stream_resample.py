import os
import sqlite3
import pandas as pd
from kiteconnect import KiteConnect, KiteTicker
from datetime import datetime, timedelta
import time
import threading

# --- FIX FOR DEPRECATION WARNING ---
def adapt_datetime_iso(dt_obj):
    """Adapter to convert datetime object to ISO 8601 string."""
    return dt_obj.isoformat()

def convert_timestamp_iso(ts_bytes):
    """Converter to parse ISO 8601 string from database back to datetime object."""
    return datetime.fromisoformat(ts_bytes.decode('utf-8'))

sqlite3.register_adapter(datetime, adapt_datetime_iso)
sqlite3.register_converter("timestamp", convert_timestamp_iso)
# --- END OF FIX ---


# --- Reusable Authentication Function ---
def get_kite_client():
    """Initializes and returns a KiteConnect client."""
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

# --- Database Setup ---
def setup_database(db_name, table_names):
    """Creates the DB and tables if they don't exist."""
    conn = sqlite3.connect(db_name, check_same_thread=False, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    for table in table_names:
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {table} (
            timestamp TIMESTAMP PRIMARY KEY,
            last_price REAL NOT NULL,
            volume INTEGER NOT NULL
        )
        ''')
    conn.commit()
    conn.close()
    print(f"Database '{db_name}' and tables {table_names} are ready.")

# --- Instrument Token Fetcher ---
def get_instrument_tokens(kite_client, tickers):
    """Fetches instrument tokens for a list of ticker symbols."""
    token_map = {"NIFTY 50": 256265}
    
    instruments_csv = "nfo_instruments.csv"
    if not os.path.exists(instruments_csv):
        print("Downloading NFO instruments list...")
        pd.DataFrame(kite_client.instruments("NFO")).to_csv(instruments_csv, index=False)
    
    nfo_df = pd.read_csv(instruments_csv)
    
    for ticker in tickers:
        if ticker == "NIFTY 50":
            continue
        row = nfo_df[nfo_df['tradingsymbol'] == ticker]
        if not row.empty:
            token_map[ticker] = int(row.iloc[0]['instrument_token'])
        else:
            print(f"Warning: Could not find instrument token for {ticker}")
            
    return token_map

# --- Global variables for WebSocket and DB ---
DB_NAME = "ticks.db"
db_conn = None
db_cursor = None
token_to_symbol_map = {}

# --- WebSocket Event Handlers ---
def on_ticks(ws, ticks):
    """Callback for when a new tick is received."""
    global db_cursor, db_conn
    for tick in ticks:
        try:
            symbol = token_to_symbol_map.get(tick['instrument_token'])
            if symbol:
                db_cursor.execute(f'''
                INSERT OR REPLACE INTO {symbol.replace(' ', '_')} (timestamp, last_price, volume)
                VALUES (?, ?, ?)
                ''', (tick['exchange_timestamp'], tick['last_price'], tick.get('last_quantity', 0)))
        except Exception as e:
            print(f"Error inserting tick for {symbol}: {e}")
    db_conn.commit()

def on_connect(ws, response):
    """Callback for when the WebSocket connection is established."""
    tokens_to_subscribe = list(token_to_symbol_map.keys())
    print(f"WebSocket connected. Subscribing to {len(tokens_to_subscribe)} tokens...")
    ws.subscribe(tokens_to_subscribe)
    ws.set_mode(ws.MODE_FULL, tokens_to_subscribe)

def on_close(ws, code, reason):
    """Callback for when the WebSocket connection is closed."""
    print(f"WebSocket closed. Code: {code}, Reason: {reason}")

# --- Resampling and Printing Thread ---
def resample_and_print_loop(table_names):
    """Periodically reads from DB, resamples to 1-min OHLC, and prints."""
    print("\nStarting 1-minute resampling monitor...")
    while True:
        time.sleep(60 - datetime.now().second)
        
        print("\n" + "="*40)
        print(f"Resampled OHLC Data at: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("="*40)

        conn = sqlite3.connect(DB_NAME, check_same_thread=False, detect_types=sqlite3.PARSE_DECLTYPES)
        for table in table_names:
            try:
                two_mins_ago = datetime.now() - timedelta(minutes=2)
                df = pd.read_sql_query(f"SELECT * FROM {table} WHERE timestamp >= ?", conn, params=(two_mins_ago,))
                
                if df.empty:
                    print(f"{table}: No new data in the last 2 minutes.")
                    continue

                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                
                ohlc = df['last_price'].resample('1Min').ohlc()
                
                if not ohlc.empty:
                    last_candle = ohlc.iloc[-1]
                    # *** THIS IS THE CORRECTED LINE ***
                    # We now include the candle's timestamp from its name (the index)
                    candle_time = last_candle.name.strftime('%H:%M:%S')
                    print(f"Ticker: {table} | Time: {candle_time}\n  Open: {last_candle['open']:.2f}, High: {last_candle['high']:.2f}, Low: {last_candle['low']:.2f}, Close: {last_candle['close']:.2f}\n")
                else:
                    print(f"{table}: Not enough data to form a 1-minute candle.")

            except Exception as e:
                print(f"Could not resample data for {table}. Error: {e}")
        conn.close()

# --- Main Execution Block ---
if __name__ == "__main__":
    kite = get_kite_client()
    if kite:
        tickers = ["NIFTY 50", "NIFTY25JUL25000CE", "NIFTY25JUL25100PE"]
        table_names = [t.replace(' ', '_') for t in tickers]

        setup_database(DB_NAME, table_names)

        symbol_to_token_map = get_instrument_tokens(kite, tickers)
        token_to_symbol_map = {v: k.replace(' ', '_') for k, v in symbol_to_token_map.items()}
        print(f"Found tokens: {symbol_to_token_map}")

        resampling_thread = threading.Thread(target=resample_and_print_loop, args=(table_names,), daemon=True)
        resampling_thread.start()

        kws = KiteTicker(kite.api_key, kite.access_token)
        kws.on_ticks = on_ticks
        kws.on_connect = on_connect
        kws.on_close = on_close

        try:
            print("Connecting to WebSocket...")
            db_conn = sqlite3.connect(DB_NAME, check_same_thread=False)
            db_cursor = db_conn.cursor()
            kws.connect()
        except KeyboardInterrupt:
            print("\nCtrl+C detected. Closing WebSocket and database connection...")
            kws.close()
            db_conn.close()
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            kws.close()
            db_conn.close()