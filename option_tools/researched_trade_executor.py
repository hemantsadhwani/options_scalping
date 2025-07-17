# option_trade_executor.py
# Executes trades based on config and rules for Hybrid Premium Strategy.
# Now with signal differentiation and EMA crossover for big-moves.

import pandas as pd
import numpy as np
import yaml
import talib  # New: For EMA calculations (pip install TA-Lib if needed)

# Load config
with open('trade_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Load data (example; adapt to your paths or attached files)
prices_df = pd.read_csv('put_out.csv')
prices_df['datetime'] = pd.to_datetime(prices_df['datetime'])

# Function to determine premium tier based on entry price
def get_premium_tier(entry_price):
    for tier, params in config['PREMIUM_TIERS'].items():
        if entry_price < params['threshold']:
            return params
    return config['PREMIUM_TIERS']['HIGH']  # Fallback

# Main trade execution function (per trade)
def execute_trade(entry_time, entry_price):
    # Find entry index
    entry_idx = prices_df[prices_df['datetime'] == entry_time].index[0]
    tier = get_premium_tier(entry_price)
    
    # New: Signal Differentiation at Entry
    if config.get('SIGNAL_DIFFERENTIATION', {}).get('ENABLED', False):
        avg_window = config['SIGNAL_DIFFERENTIATION']['AVG_WINDOW_CANDLES']
        window_data = prices_df.iloc[entry_idx:entry_idx + avg_window]
        avg_stoch_k = window_data['K'].mean()
        avg_r1 = window_data['%R.1'].mean()
        is_big_move = (avg_stoch_k > config['SIGNAL_DIFFERENTIATION']['STOCH_K_THRESHOLD']) and \
                      (avg_r1 < config['SIGNAL_DIFFERENTIATION']['WILLIAMS_R1_THRESHOLD'])
    else:
        is_big_move = False
    
    # Initialize trade vars
    initial_sl = entry_price * (1 - tier['sl_percent'] / 100)
    highest_high = prices_df.iloc[entry_idx]['high']
    trailed_sl = initial_sl
    trailing_active = False
    stall_count = 0
    breakeven_delay_counter = 0
    prev_k = prices_df.iloc[entry_idx]['K']
    prev_d = prices_df.iloc[entry_idx]['D']
    prev_r = prices_df.iloc[entry_idx]['%R']
    prev_r1 = prices_df.iloc[entry_idx]['%R.1']
    
    # Loop through subsequent candles
    for i in range(entry_idx + 1, len(prices_df)):
        row = prices_df.iloc[i]
        current_high = row['high']
        current_low = row['low']
        current_close = row['close']
        current_k = row['K']
        current_d = row['D']
        current_r = row['%R']
        current_r1 = row['%R.1']
        
        # Update highest high
        highest_high = max(highest_high, current_high)
        
        # Activate trailing if qualified
        profit_pct = (highest_high - entry_price) / entry_price * 100
        if not trailing_active and profit_pct >= tier['trail_start_pct']:
            trailing_active = True
        
        # Calculate ATR for trailing (existing)
        if trailing_active:
            atr = prices_df['close'].iloc[i - config['ATR_PERIOD']:i].diff().abs().mean()  # Simple ATR approx; use talib.ATR if preferred
            trail_amount = tier['atr_mult'] * atr
            if current_k < config['STOCH_OVERSOLD']:
                trail_amount *= 0.75  # Tighten for oversold
            trailed_sl = highest_high - trail_amount
        
        # Breakeven move (existing, with delay)
        if profit_pct >= config['BREAKEVEN_MOVE_PCT']:
            breakeven_delay_counter += 1
            if breakeven_delay_counter >= tier['breakeven_delay']:
                initial_sl = max(initial_sl, entry_price)
        
        # Stall detection (existing; skip for big-moves to give room)
        if not is_big_move:
            candle_range = current_high - current_low
            if candle_range < entry_price * (config['STALL_THRESHOLD_PCT'] / 100):
                stall_count += 1
            else:
                stall_count = 0
            if stall_count >= config['STALL_CANDLES']:
                initial_sl = min(current_close, entry_price)
        
        # SL Hit Check (existing)
        current_sl = max(initial_sl, trailed_sl) if trailing_active else initial_sl
        if current_low <= current_sl:
            return {
                'exit_time': row['datetime'],
                'exit_price': current_sl,
                'exit_reason': 'SL Hit' if not trailing_active else 'Trailing SL'
            }
        
        # Technical Exits (existing; only if not big-move or low profit)
        if (prev_r1 > config['WILLIAMS28_CROSS_UNDER'] and current_r1 <= config['WILLIAMS28_CROSS_UNDER']) or \
           (profit_pct > 5 and prev_r > config['WILLIAMS9_CROSS_UNDER'] and current_r <= config['WILLIAMS9_CROSS_UNDER']):
            if not is_big_move or profit_pct < config['SIGNAL_DIFFERENTIATION']['TRAIL_MIN_PROFIT_PCT']:
                return {
                    'exit_time': row['datetime'],
                    'exit_price': current_close,
                    'exit_reason': 'Williams Exit'
                }
        
        # Quick TP (existing; skip if big-move)
        if not is_big_move and current_high >= entry_price + config['QUICK_TP_POINTS']:
            if config['USE_STOCH_FADE_FOR_TP'] and prev_k > prev_d and current_k <= current_d:
                return {
                    'exit_time': row['datetime'],
                    'exit_price': entry_price + config['QUICK_TP_POINTS'],
                    'exit_reason': 'Quick TP'
                }
        
        # New: EMA Crossover Exit for Big-Moves
        if is_big_move and config['SIGNAL_DIFFERENTIATION']['EMA_CROSS_EXIT'] and trailing_active:
            # Calculate EMAs up to current (using full history for accuracy)
            closes = prices_df['close'].iloc[:i+1].values
            ema9 = talib.EMA(closes, timeperiod=config['SIGNAL_DIFFERENTIATION']['EMA_PERIODS'][0])[-1]
            ema15 = talib.EMA(closes, timeperiod=config['SIGNAL_DIFFERENTIATION']['EMA_PERIODS'][1])[-1]
            prev_closes = prices_df['close'].iloc[:i].values
            if len(prev_closes) >= max(config['SIGNAL_DIFFERENTIATION']['EMA_PERIODS']):
                prev_ema9 = talib.EMA(prev_closes, timeperiod=config['SIGNAL_DIFFERENTIATION']['EMA_PERIODS'][0])[-1]
                prev_ema15 = talib.EMA(prev_closes, timeperiod=config['SIGNAL_DIFFERENTIATION']['EMA_PERIODS'][1])[-1]
                current_profit_pct = (current_close - entry_price) / entry_price * 100
                if (prev_ema9 <= prev_ema15) and (ema9 > ema15) and current_profit_pct > config['SIGNAL_DIFFERENTIATION']['TRAIL_MIN_PROFIT_PCT']:
                    return {
                        'exit_time': row['datetime'],
                        'exit_price': current_close,
                        'exit_reason': 'EMA Crossover Exit'
                    }
        
        # Update prev indicators
        prev_k, prev_d, prev_r, prev_r1 = current_k, current_d, current_r, current_r1
    
    # End of data
    last_row = prices_df.iloc[-1]
    return {
        'exit_time': last_row['datetime'],
        'exit_price': last_row['close'],
        'exit_reason': 'End of Data'
    }

# Example usage: Loop over trades from put_rev_v2_trades.csv and execute
trades_df = pd.read_csv('put_rev_v2_trades.csv')
trades_df['Entry Time'] = pd.to_datetime(trades_df['Entry Time'])

results = []
for _, trade in trades_df.iterrows():
    result = execute_trade(trade['Entry Time'], trade['Entry Price'])
    results.append(result)

# Save results to new CSV (e.g., improvised_trades.csv)
output_df = trades_df.copy()
output_df = output_df.join(pd.DataFrame(results))
output_df.to_csv('improvised_trades.csv', index=False)
print("Simulation complete! Check improvised_trades.csv")