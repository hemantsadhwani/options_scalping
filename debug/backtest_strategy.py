import pandas as pd
from option_tools.option_trade_executor import TradeExecutor  # Assuming this is your class/module with rules implemented
import yaml  # If you're loading trade_config.yaml

# Load config if needed (adjust path as per your setup)
with open('./option_tools/trade_config.yaml', 'r') as file:
    config = yaml.safe_load(file)

# Initialize your trade executor with rules (assuming it takes config or rules file)
executor = TradeExecutor(config=config)  # Or pass 'trade_rules.txt' if that's how it's set up

# Load the signal CSV
signals_df = pd.read_csv('./data/1407/tradeview_rev_output.csv')
# Assuming columns: 'Timestamp', 'Call_crp', 'Put_crp' (e.g., 1 for signal, 0 for none)

# Load option data CSVs
call_data_df = pd.read_csv('./data/1407/call/call_out.csv')
put_data_df = pd.read_csv('./data/1407/put/put_out.csv')
# Assuming columns in both: 'Timestamp', 'Open', 'High', 'Low', 'Close' (for candles)

# Merge signals with option data on Timestamp (or align by index if timestamps match)
# Shift option data by 1 to get "next candle"
call_data_df['Next_Open'] = call_data_df['Open'].shift(-1)
call_data_df['Next_High'] = call_data_df['High'].shift(-1)
call_data_df['Next_Low'] = call_data_df['Low'].shift(-1)
call_data_df['Next_Close'] = call_data_df['Close'].shift(-1)

put_data_df['Next_Open'] = put_data_df['Open'].shift(-1)
put_data_df['Next_High'] = put_data_df['High'].shift(-1)
put_data_df['Next_Low'] = put_data_df['Low'].shift(-1)
put_data_df['Next_Close'] = put_data_df['Close'].shift(-1)

# Assuming signals and data have matching timestamps; merge them
merged_call_df = pd.merge(signals_df, call_data_df, on='Timestamp', how='inner')
merged_put_df = pd.merge(signals_df, put_data_df, on='Timestamp', how='inner')

# List to hold trade results
trades = []

# Simulate trades for Calls
for index, row in merged_call_df.iterrows():
    if row['Call_crp'] == 1:  # Assuming 1 means take call trade
        # Prepare candle data for executor (adjust based on your executor's input format)
        candle = {
            'timestamp': row['Timestamp'],
            'open': row['Next_Open'],
            'high': row['Next_High'],
            'low': row['Next_Low'],
            'close': row['Next_Close']
        }
        # Execute trade using your module (assuming it returns trade details like entry, exit, pnl)
        trade_result = executor.execute_trade(trade_type='call', candle_data=candle)
        trades.append({
            'Timestamp': row['Timestamp'],
            'Type': 'Call',
            'Signal': row['Call_crp'],
            'Entry_Price': trade_result.get('entry_price'),
            'Exit_Price': trade_result.get('exit_price'),
            'PnL': trade_result.get('pnl'),
            # Add more fields based on your trade_rules.txt (e.g., stop_loss_hit, target_hit)
        })

# Simulate trades for Puts (similar logic)
for index, row in merged_put_df.iterrows():
    if row['Put_crp'] == 1:  # Assuming 1 means take put trade
        candle = {
            'timestamp': row['Timestamp'],
            'open': row['Next_Open'],
            'high': row['Next_High'],
            'low': row['Next_Low'],
            'close': row['Next_Close']
        }
        trade_result = executor.execute_trade(trade_type='put', candle_data=candle)
        trades.append({
            'Timestamp': row['Timestamp'],
            'Type': 'Put',
            'Signal': row['Put_crp'],
            'Entry_Price': trade_result.get('entry_price'),
            'Exit_Price': trade_result.get('exit_price'),
            'PnL': trade_result.get('pnl'),
        })

# Convert trades to DataFrame and save to CSV
trades_df = pd.DataFrame(trades)
trades_df.to_csv('./data/1407/trades_crp/rev_v1_trades.csv', index=False)

# Basic performance metrics (to check profitability)
total_pnl = trades_df['PnL'].sum()
win_rate = (trades_df['PnL'] > 0).mean() * 100 if not trades_df.empty else 0
print(f"Total PnL: {total_pnl}")
print(f"Win Rate: {win_rate:.2f}%")
print("Trades saved to ./data/1407/trades_crp/rev_v1_trades.csv")

# To improve profitability: Example optimization (tweak thresholds from trade_rules.txt)
# Let's say your rules have a stop_loss_pct; test different values
for sl_pct in [0.5, 1.0, 1.5]:  # Experiment with values
    executor.set_stop_loss(sl_pct)  # Assuming your executor has a method to update rules
    # Re-run the simulation above and compare total_pnl
    # (You'd wrap the simulation in a function and call it here for each param)
    print(f"With SL {sl_pct}%: Total PnL = [re-run simulation]")