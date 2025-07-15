# option_tools/option_trade_executor.py

import pandas as pd
try:
    import pandas_ta as ta
except ImportError:
    import sys
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas_ta"])
    import pandas_ta as ta

from datetime import time
import os
import yaml

def load_trade_config():
    """Load trade configuration from option_tools/trade_config.yaml"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'trade_config.yaml')
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Warning: Could not load trade_config.yaml: {e}")
        # Fallback to default values (updated to match the latest simulation config)
        return {
            'STRATEGY_TYPE': 'HYBRID_PREMIUM',
            'HYBRID_PREMIUM': {
                'SL_PERCENT': 6.0,
                'PREMIUM_TIERS': {
                    'LOW': {'threshold': 100, 'sl_percent': 3.0, 'atr_mult': 2.5, 'breakeven_delay': 0, 'trail_start_pct': 10.0},
                    'MED': {'threshold': 250, 'sl_percent': 5.0, 'atr_mult': 3.0, 'breakeven_delay': 2, 'trail_start_pct': 15.0},
                    'HIGH': {'threshold': float('inf'), 'sl_percent': 7.0, 'atr_mult': 4.0, 'breakeven_delay': 2, 'trail_start_pct': 15.0}
                },
                'BREAKEVEN_MOVE_PCT': 4.0,
                'STALL_CANDLES': 10,
                'STALL_THRESHOLD_PCT': 1.5,
                'QUICK_TP_POINTS': 12,
                'ATR_PERIOD': 5,
                'WILLIAMS28_CROSS_UNDER': -80,
                'WILLIAMS9_CROSS_UNDER': -80,
                'STOCH_OVERSOLD': 20,
                'USE_STOCH_FADE_FOR_TP': True
            }
        }

def execute_option_trades(signals_df, prices_df, signal_col, trade_type, config, output_dir, output_filename):
    """
    Executes option trades based on signals using trade_config.yaml parameters.
    Focuses on HYBRID_PREMIUM strategy as per updates.
    """
    # Load trade-specific configuration
    trade_config = load_trade_config()
    strategy_type = trade_config.get('STRATEGY_TYPE', 'HYBRID_PREMIUM')
    
    # Get timing from main config (passed from app.py)
    last_entry_hour, last_entry_minute = map(int, config['LAST_ENTRY_TIME'].split(':'))
    last_entry_time = time(last_entry_hour, last_entry_minute)

    signals_df['datetime'] = pd.to_datetime(signals_df['datetime'])
    prices_df['datetime'] = pd.to_datetime(prices_df['datetime'])
    prices_df.set_index('datetime', inplace=True)

    # Add ATR calculation for HYBRID_PREMIUM strategy
    if strategy_type == 'HYBRID_PREMIUM':
        atr_period = trade_config['HYBRID_PREMIUM']['ATR_PERIOD']
        prices_df[f'ATR_{atr_period}'] = ta.atr(prices_df['high'], prices_df['low'], prices_df['close'], length=atr_period)

    valid_signals = signals_df[signals_df[signal_col] == 1].copy()
    
    trade_results = []
    current_trade_exit_time = None  # Track when current trade exits

    print(f"   Processing {len(valid_signals)} option signals for {trade_type} using {strategy_type} strategy")

    for index, signal in valid_signals.iterrows():
        if signal['datetime'].time() > last_entry_time:
            continue

        # CRITICAL FIX: Check if there's an active trade
        if current_trade_exit_time is not None and signal['datetime'] <= current_trade_exit_time:
            print(f"   Skipping signal at {signal['datetime']} - Active trade until {current_trade_exit_time}")
            continue

        # CORRECTED: Execute trade on NEXT candle after signal
        signal_time = signal['datetime']
        
        # Find the next candle after the signal
        signal_bar_index = None
        try:
            signal_bar_index = prices_df.index.get_loc(signal_time)
        except KeyError:
            print(f"   Skipping - Signal time {signal_time} not in prices_df")
            continue
        
        # Entry is on the NEXT candle after signal
        next_bar_index = signal_bar_index + 1
        if next_bar_index >= len(prices_df):
            print(f"   Skipping - No next candle available after signal at {signal_time}")
            continue
        
        entry_time = prices_df.index[next_bar_index]
        trade_data = prices_df.iloc[next_bar_index:].reset_index()  # Reset index to match simulation format

        if trade_data.empty:
            continue

        # Use the open price of the next candle as entry price
        entry_price = trade_data.iloc[0]['open']
        if not isinstance(entry_price, (int, float)):
            entry_price = float(entry_price)  # Ensure float

        print(f"   Executing trade: Entry at {entry_time}, Price: {entry_price}")

        # Use HYBRID_PREMIUM as the primary strategy
        result = execute_hybrid_premium_trade(trade_data, entry_price, trade_config.get('HYBRID_PREMIUM', {}), entry_time, trade_type)
        
        if result:
            trade_results.append(result)
            # Update the exit time to prevent overlapping trades
            current_trade_exit_time = pd.to_datetime(result['Exit Time'])
            print(f"   Trade completed: Exit at {current_trade_exit_time}, P/L: {result['P/L %']}")
        else:
            print(f"   Trade execution failed for signal at {signal['datetime']}")

    df_results = pd.DataFrame(trade_results)
    
    # --- Save results to file ---
    if not df_results.empty:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_filename)
        
        # Append to existing file if it exists, otherwise create new
        if os.path.exists(output_path):
            existing_df = pd.read_csv(output_path)
            combined_df = pd.concat([existing_df, df_results], ignore_index=True)
            combined_df.to_csv(output_path, index=False)
            print(f"  ✓ Appended {len(df_results)} option trades to {output_path}")
        else:
            df_results.to_csv(output_path, index=False)
            print(f"  ✓ Saved {len(df_results)} option trades to {output_path}")
    else:
        print(f"  ℹ️ No valid option trades found for {trade_type}")
    
    return df_results

def execute_hybrid_premium_trade(trade_data, entry_price, hybrid_config, entry_time, trade_type):
    """Execute trade with updated hybrid premium-based trailing stop (from simulation logic)"""
    
    tier = get_premium_tier(entry_price, hybrid_config['PREMIUM_TIERS'])
    initial_sl_pct = tier.get('sl_percent', hybrid_config.get('SL_PERCENT', 6.0))
    initial_sl = entry_price * (1 - initial_sl_pct / 100)
    
    current_sl = initial_sl
    highest_high = trade_data.iloc[0]['high']
    
    trail_active = False
    exit_time = None
    exit_price = None
    exit_reason = 'In Progress'
    
    candle_count = 0
    stall_count = 0
    
    atr_col = f"ATR_{hybrid_config['ATR_PERIOD']}"
    
    prev_wr28 = trade_data.iloc[0].get('%R.1', 0)
    prev_wr9 = trade_data.iloc[0].get('%R', 0)
    prev_k = trade_data.iloc[0].get('K', 50)
    prev_d = trade_data.iloc[0].get('D', 50)
    
    for idx, bar in trade_data.iloc[1:].iterrows():
        candle_count += 1
        highest_high = max(highest_high, bar['high'])
        
        # Trailing SL Logic
        if not trail_active and (highest_high / entry_price - 1) * 100 >= tier['trail_start_pct']:
            trail_active = True
        
        if trail_active:
            atr_val = bar.get(atr_col, 0)
            atr_multiplier = tier['atr_mult']
            if bar.get('K', 50) < hybrid_config['STOCH_OVERSOLD']:
                atr_multiplier *= 0.75
            
            trailing_sl = highest_high - (atr_val * atr_multiplier)
            current_sl = max(current_sl, trailing_sl)
        
        # Breakeven Logic - COMMENTED OUT FOR TESTING
        # if not trail_active and candle_count > tier['breakeven_delay'] and (highest_high / entry_price - 1) * 100 >= hybrid_config['BREAKEVEN_MOVE_PCT']:
        #     current_sl = max(current_sl, entry_price)
            
        # Stall Logic
        candle_range_pct = (bar['high'] - bar['low']) / entry_price * 100
        if candle_range_pct < hybrid_config['STALL_THRESHOLD_PCT']:
            stall_count += 1
        else:
            stall_count = 0
        
        if stall_count >= hybrid_config['STALL_CANDLES']:
            current_sl = max(current_sl, min(bar['close'], entry_price))
            
        # Exit conditions
        if bar['low'] <= current_sl:
            exit_price = current_sl
            exit_time = bar['datetime']
            exit_reason = 'Trailing SL' if trail_active else 'SL Hit'
            break
            
        # Technical Exits
        profit_pct = (bar['close'] - entry_price) / entry_price * 100
        if prev_wr28 > hybrid_config['WILLIAMS28_CROSS_UNDER'] and bar.get('%R.1', 0) <= hybrid_config['WILLIAMS28_CROSS_UNDER']:
            exit_price = bar['close']
            exit_time = bar['datetime']
            exit_reason = 'Williams28 Exit'
            break
        if profit_pct > 5 and prev_wr9 > hybrid_config['WILLIAMS9_CROSS_UNDER'] and bar.get('%R', 0) <= hybrid_config['WILLIAMS9_CROSS_UNDER']:
            exit_price = bar['close']
            exit_time = bar['datetime']
            exit_reason = 'Williams9 Exit'
            break
            
        # Quick TP
        if not trail_active and bar['high'] >= entry_price + hybrid_config['QUICK_TP_POINTS']:
            use_fade = hybrid_config.get('USE_STOCH_FADE_FOR_TP', False)
            k_val, d_val = bar.get('K', 50), bar.get('D', 50)
            
            if not use_fade or (prev_k > prev_d and k_val <= d_val):
                exit_price = entry_price + hybrid_config['QUICK_TP_POINTS']
                exit_time = bar['datetime']
                exit_reason = 'Quick TP'
                break
                
        prev_wr28 = bar.get('%R.1', prev_wr28)
        prev_wr9 = bar.get('%R', prev_wr9)
        prev_k = bar.get('K', prev_k)
        prev_d = bar.get('D', prev_d)
        
    if exit_reason == 'In Progress':
        exit_price = trade_data.iloc[-1]['close']
        exit_time = trade_data.iloc[-1]['datetime']
        exit_reason = 'End of Data'
        
    pl = exit_price - entry_price
    pl_pct = (pl / entry_price) * 100 if entry_price > 0 else 0
    
    return {
        'Entry Time': entry_time,
        'Entry Price': f"{entry_price:.2f}",
        'Exit Time': exit_time,
        'Exit Price': f"{exit_price:.2f}",
        'P/L': f"{pl:.2f}",
        'P/L %': f"{pl_pct:.2f}%",
        'Exit Reason': exit_reason,
        'Trade Type': f"{trade_type} Option (Hybrid Premium)",
        'Initial SL': f"{initial_sl:.2f}",
        'Final SL': f"{current_sl:.2f}",
        'Highest High': f"{highest_high:.2f}"
    }

def get_premium_tier(entry_price, tiers):
    for tier, info in tiers.items():
        if entry_price < info['threshold']:
            return info
    return tiers['HIGH']