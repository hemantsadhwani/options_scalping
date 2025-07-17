import pandas as pd
import pandas_ta as ta

def run_final_trade_simulation():
    """
    Executes a trading simulation based on the finalized strategy.
    This version uses a 6% fixed initial stop-loss and a 14-bar stall exit rule
    to ensure high-potential trades are not exited prematurely.
    """
    # --- Final Strategy Parameters ---
    FIXED_STOP_LOSS_PERCENT = 6.0
    STALL_BAR_COUNT = 14 # Allows trades more time to develop

    # --- 1. Load and Prepare Data ---
    try:
        signals_df = pd.read_csv('ml_call_data_out.csv')
        prices_df = pd.read_csv('call_out.csv')
    except FileNotFoundError as e:
        print(f"Error: Make sure both 'ml_call_data_out.csv' and 'call_out.csv' are in the same directory. Missing file: {e.filename}")
        return

    # Convert time columns to datetime objects for proper processing
    signals_df['entry_time'] = pd.to_datetime(signals_df['entry_time'])
    prices_df['datetime'] = pd.to_datetime(prices_df['datetime'])
    prices_df.set_index('datetime', inplace=True)

    # --- 2. Calculate Technical Indicators ---
    prices_df.ta.atr(length=5, append=True, col_names=('ATR_5',))

    # --- 3. Filter for Valid Trade Signals ---
    valid_signals = signals_df[signals_df['filter_passed'] == True].copy()
    print("--- Running Finalized Simulation ---")
    print(f"Applying rules: {FIXED_STOP_LOSS_PERCENT}% fixed initial SL, {STALL_BAR_COUNT}-bar stall exit.")

    trade_results = []

    # --- 4. Main Simulation Loop ---
    for index, signal in valid_signals.iterrows():
        entry_time = signal['entry_time']
        if entry_time not in prices_df.index:
            continue

        entry_bar_index = prices_df.index.get_loc(entry_time)
        trade_data = prices_df.iloc[entry_bar_index:]

        if trade_data.empty:
            continue

        # --- Initialize Trade Variables ---
        entry_price = trade_data.iloc[0]['close']
        entry_atr = trade_data.iloc[0]['ATR_5']

        if pd.isna(entry_atr):
            continue

        initial_stop_loss = entry_price * (1 - (FIXED_STOP_LOSS_PERCENT / 100.0))
        breakeven_target = entry_price + (1.5 * entry_atr)

        current_stop_loss = initial_stop_loss
        highest_high_since_entry = entry_price
        bar_of_highest_high = 0
        is_breakeven_achieved = False
        exit_reason = "In Progress"
        exit_price = 0.0
        exit_time = None

        # --- 5. Bar-by-Bar Trade Management Loop ---
        for i in range(1, len(trade_data)):
            current_bar = trade_data.iloc[i]
            bars_since_entry = i

            if current_bar['low'] <= current_stop_loss:
                exit_price = current_stop_loss
                exit_time = current_bar.name
                exit_reason = "Trailing SL" if is_breakeven_achieved else "Initial SL"
                break

            if not is_breakeven_achieved and current_bar['high'] >= breakeven_target:
                is_breakeven_achieved = True
                current_stop_loss = entry_price

            if current_bar['high'] > highest_high_since_entry:
                highest_high_since_entry = current_bar['high']
                bar_of_highest_high = i

            if is_breakeven_achieved:
                current_atr = current_bar['ATR_5']
                if not pd.isna(current_atr):
                    trailing_stop_target = highest_high_since_entry - (2.2 * current_atr)
                    current_stop_loss = max(trailing_stop_target, current_stop_loss)

            if (bars_since_entry - bar_of_highest_high) > STALL_BAR_COUNT:
                exit_price = current_bar['close']
                exit_time = current_bar.name
                exit_reason = "Stall Exit"
                break
        
        if exit_reason == "In Progress":
            exit_price = trade_data.iloc[-1]['close']
            exit_time = trade_data.iloc[-1].name
            exit_reason = "End of Data"

        profit_loss = exit_price - entry_price
        trade_results.append({
            "Entry Time": entry_time,
            "Entry Price": f"{entry_price:.2f}",
            "Exit Time": exit_time,
            "Exit Price": f"{exit_price:.2f}",
            "P/L": f"{profit_loss:.2f}",
            "Exit Reason": exit_reason
        })

    # --- 7. Display Results ---
    if not trade_results:
        print("\nNo trades were executed based on the provided data.")
        return

    results_df = pd.DataFrame(trade_results)
    results_df['P/L'] = pd.to_numeric(results_df['P/L'])
    
    print("\n--- Individual Trade Results (Finalized Logic) ---")
    print(results_df.to_string())

    # --- 8. Calculate and Print Summary ---
    total_pl = results_df['P/L'].sum()
    winning_trades = results_df[results_df['P/L'] > 0]
    losing_trades = results_df[results_df['P/L'] <= 0]
    num_trades = len(results_df)
    win_rate = (len(winning_trades) / num_trades) * 100 if num_trades > 0 else 0

    print("\n--- Trade Simulation Summary (Finalized Logic) ---")
    print(f"Total Trades Executed: {num_trades}")
    print(f"Total Net P/L: {total_pl:.2f}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Number of Wins: {len(winning_trades)}")
    print(f"Number of Losses: {len(losing_trades)}")
    if not winning_trades.empty:
        print(f"Average Win: {winning_trades['P/L'].mean():.2f}")
    if not losing_trades.empty:
        print(f"Average Loss: {losing_trades['P/L'].mean():.2f}")
    if not winning_trades.empty and not losing_trades.empty and losing_trades['P/L'].sum() != 0:
        print(f"Profit Factor: {abs(winning_trades['P/L'].sum() / losing_trades['P/L'].sum()):.2f}")

# This makes the script runnable from the command line
if __name__ == "__main__":
    run_final_trade_simulation()