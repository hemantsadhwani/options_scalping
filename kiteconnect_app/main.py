from helper_func import (
    initialize_kiteconnect,
    get_instrument_token,
    fetch_option_ohlc,
    load_config,
    add_technical_indicators
)

# Main script execution
if __name__ == "__main__":
    # Load configuration from YAML file
    config = load_config("config.yaml")
    if config is None:
        print("Failed to load configuration. Exiting.")
        exit()

    # Extract configuration values
    trading_symbol = config.get("trading_symbol")
    no_of_days = config.get("no_of_days")
    candle_time_duration = config.get("candle_time_duration")

    # Validate the candle time duration
    valid_intervals = ['minute', '3minute', '5minute', '10minute', '15minute', '30minute', '60minute', 'day', 'week', 'month']
    if candle_time_duration not in valid_intervals:
        print(f"Error: Invalid candle time duration '{candle_time_duration}'. Valid options are: {valid_intervals}")
        exit()

    # Initialize Kite Connect
    kite = initialize_kiteconnect()
    if kite is None:
        print("Failed to initialize Kite Connect. Exiting.")
        exit()

    # Fetch the instrument token for the trading symbol
    instrument_token = get_instrument_token(kite, trading_symbol)

    if instrument_token:
        print(f"Instrument token for {trading_symbol}: {instrument_token}")

        # Fetch OHLC data
        ohlc_data = fetch_option_ohlc(kite, instrument_token, no_of_days, candle_time_duration)

        # Add technical indicators to the OHLC data
        if ohlc_data is not None:
            ohlc_data = add_technical_indicators(ohlc_data)

            # Save OHLC data with indicators to CSV
            file_name = f"{trading_symbol}_ohlc_{no_of_days}days_{candle_time_duration}.csv"
            ohlc_data.to_csv(file_name, index=False)
            print(f"OHLC data with indicators saved to {file_name}")
        else:
            print("Error: No OHLC data fetched.")
    else:
        print("Error: Instrument token not found. Exiting.")