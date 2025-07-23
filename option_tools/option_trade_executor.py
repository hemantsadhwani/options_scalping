# option_tools/option_trade_executor.py

import pandas as pd
import numpy as np
import yaml

try:
    import pandas_ta as ta
except ImportError:
    import sys
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas_ta"])
    import pandas_ta as ta

from datetime import time
import os

def load_trade_config():
    """Load trade configuration from option_tools/trade_config.yaml"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'trade_config.yaml')
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
            # Convert 'inf' string to float('inf')
            for tier in config['PREMIUM_TIERS'].values():
                if isinstance(tier['threshold'], str) and tier['threshold'].lower() == 'inf':
                    tier['threshold'] = float('inf')
            return config
    except Exception as e:
        print(f"Warning: Could not load trade_config.yaml: {e}")
        # Fallback to default values (updated to match the latest simulation config)
        return {
            'STRATEGY_TYPE': 'HYBRID_PREMIUM',
            'PREMIUM_TIERS': {
                'LOW': {'threshold': 100, 'sl_percent': 3.0, 'atr_mult': 2.5, 'breakeven_delay': 0, 'trail_start_pct': 10.0},
                'MED': {'threshold': 250, 'sl_percent': 5.0, 'atr_mult': 3.0, 'breakeven_delay': 2, 'trail_start_pct': 15.0},
                'HIGH': {'threshold': float('inf'), 'sl_percent': 7.0, 'atr_mult': 4.0, 'breakeven_delay': 2, 'trail_start_pct': 15.0}
            },
            'SL_PERCENT': 6.0,
            'BREAKEVEN_MOVE_PCT': 4.0,
            'STALL_CANDLES': 10,
            'STALL_THRESHOLD_PCT': 1.5,
            'QUICK_TP_POINTS': 12,
            'ATR_PERIOD': 5,
            'WILLIAMS28_CROSS_UNDER': -80,
            'WILLIAMS9_CROSS_UNDER': -80,
            'STOCH_OVERSOLD': 20,
            'USE_STOCH_FADE_FOR_TP': True,
            'SIGNAL_DIFFERENTIATION': {
                'ENABLED': True,
                'AVG_WINDOW_CANDLES': 3,
                'BIGMOVE_DETECTION': {
                    'THRESHOLDS': {
                        'CALL': {
                            'STOCH_K_THRESHOLD': 72,
                            'WILLIAMS_R1_THRESHOLD': -5
                        },
                        'PUT': {
                            'STOCH_K_THRESHOLD': 75,
                            'WILLIAMS_R1_THRESHOLD': -50
                        }
                    },
                    'MOMENTUM_CONFIRMATION': {
                        'ENABLED': False,
                        'MIN_CANDLE_RANGE_PCT': 1.2,
                        'CONSECUTIVE_MOVES': 1
                    }
                },
                'EMA_CROSS_EXIT': True,
                'EMA_PERIODS': [9, 15],
                'TRAIL_MIN_PROFIT_PCT': 15.0
            }
        }

def execute_option_trades(signals_df, prices_df, signal_col, trade_type, config, output_dir, output_filename):
    """
    Executes option trades based on signals using advanced trade logic with signal differentiation and EMA crossovers.
    """
    # Load trade-specific configuration
    trade_config = load_trade_config()
    
    # Get timing from main config (passed from app.py)
    last_entry_hour, last_entry_minute = map(int, config['LAST_ENTRY_TIME'].split(':'))
    last_entry_time = time(last_entry_hour, last_entry_minute)

    signals_df['datetime'] = pd.to_datetime(signals_df['datetime'])
    prices_df['datetime'] = pd.to_datetime(prices_df['datetime'])
    prices_df.set_index('datetime', inplace=True)

    # Add ATR calculation
    atr_period = trade_config.get('ATR_PERIOD', 5)
    prices_df[f'ATR_{atr_period}'] = ta.atr(prices_df['high'], prices_df['low'], prices_df['close'], length=atr_period)

    valid_signals = signals_df[signals_df[signal_col] == 1].copy()
    
    trade_results = []
    current_trade_exit_time = None  # Track when current trade exits

    print(f"   Processing {len(valid_signals)} option signals for {trade_type} using advanced strategy with signal differentiation")

    for index, signal in valid_signals.iterrows():
        if signal['datetime'].time() > last_entry_time:
            continue

        # Check if there's an active trade
        if current_trade_exit_time is not None and signal['datetime'] <= current_trade_exit_time:
            print(f"   Skipping signal at {signal['datetime']} - Active trade until {current_trade_exit_time}")
            continue

        # Execute trade on NEXT candle after signal
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

        # Check for pre-defined 'Big Move' status from the signal file
        is_big_move_from_signal = signal.get('Big Move', None)

        # Use advanced hybrid premium strategy with signal differentiation
        result = execute_advanced_hybrid_premium_trade(trade_data, entry_price, trade_config, entry_time, trade_type, next_bar_index, is_big_move_from_signal=is_big_move_from_signal)
        
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

def execute_advanced_hybrid_premium_trade(trade_data, entry_price, trade_config, entry_time, trade_type, entry_idx, is_big_move_from_signal=None):
    """Execute trade with enhanced BigMove detection, multi-stage trailing logic, and INTELLIGENT SL MANAGEMENT"""
    
    tier = get_premium_tier(entry_price, trade_config['PREMIUM_TIERS'])
    
    # PHASE 2: Enhanced SL Management - Dynamic SL based on entry conditions
    initial_sl_pct = get_dynamic_sl_percent(trade_data, entry_price, trade_config, tier)
    initial_sl = entry_price * (1 - initial_sl_pct / 100)
    
    # Enhanced BigMove Detection
    is_big_move = detect_big_move(trade_data, entry_price, trade_config, trade_type, is_big_move_from_signal)
    
    # Determine if this is an average signal (for fixed TP approach)
    is_average_signal = not is_big_move and trade_config.get('AVERAGE_SIGNAL_MANAGEMENT', {}).get('ENABLED', False)
    
    current_sl = initial_sl
    highest_high = trade_data.iloc[0]['high']
    trailed_sl = initial_sl
    
    trail_active = False
    exit_time = None
    exit_price = None
    exit_reason = 'In Progress'
    
    candle_count = 0
    stall_count = 0
    breakeven_delay_counter = 0
    entry_timestamp = pd.to_datetime(entry_time)
    
    # PHASE 2: Enhanced SL Management - Yellow Flag and Technical Exit tracking
    yellow_flag_triggered = False
    yellow_flag_time = None
    technical_exit_available = False
    sl_tightened_by_yellow_flag = False
    
    atr_col = f"ATR_{trade_config.get('ATR_PERIOD', 5)}"
    
    prev_wr28 = trade_data.iloc[0].get('%R.1', 0)
    prev_wr9 = trade_data.iloc[0].get('%R', 0)
    prev_k = trade_data.iloc[0].get('K', 50)
    prev_d = trade_data.iloc[0].get('D', 50)
    
    # Entry risk assessment for enhanced SL management
    entry_risk_level = assess_entry_risk_level(trade_data.iloc[0])
    
    print(f"Debug {entry_time} ({trade_type}): BigMove={is_big_move}, AvgSignal={is_average_signal}, EntryRisk={entry_risk_level}, InitialSL={initial_sl_pct:.1f}%")
    
    for idx, bar in trade_data.iloc[1:].iterrows():
        candle_count += 1
        current_high = bar['high']
        current_low = bar['low']
        current_close = bar['close']
        current_k = bar.get('K', 50)
        current_d = bar.get('D', 50)
        current_r = bar.get('%R', 0)
        current_r1 = bar.get('%R.1', 0)
        
        # Update highest high
        highest_high = max(highest_high, current_high)
        
        # Calculate current profit
        profit_pct = (highest_high - entry_price) / entry_price * 100
        current_profit_pct = (current_close - entry_price) / entry_price * 100
        
        # PHASE 2: ENHANCED SL MANAGEMENT - Yellow Flag Early Warning System
        if not yellow_flag_triggered:
            yellow_flags = detect_yellow_flag_conditions(
                {'K': current_k, 'D': current_d, 'williams_9': current_r, 'williams_28': current_r1},
                {'K': prev_k, 'D': prev_d, 'williams_9': prev_wr9, 'williams_28': prev_wr28},
                trade_config
            )
            
            if yellow_flags:
                yellow_flag_triggered = True
                yellow_flag_time = bar['datetime']
                print(f"🟡 YELLOW FLAG at {yellow_flag_time}: {', '.join(yellow_flags)} (Profit: {current_profit_pct:+.2f}%)")
                
                # Tighten SL based on Yellow Flag
                if not sl_tightened_by_yellow_flag:
                    tighten_pct = trade_config.get('ENHANCED_SL_MANAGEMENT', {}).get('YELLOW_FLAG_SYSTEM', {}).get('TIGHTEN_SL_PCT', 1.5)
                    tightened_sl = entry_price * (1 - (initial_sl_pct - tighten_pct) / 100)
                    current_sl = max(current_sl, tightened_sl)
                    sl_tightened_by_yellow_flag = True
                    print(f"   → SL tightened by {tighten_pct}% to {((entry_price - current_sl) / entry_price * 100):.1f}%")
        
        # PHASE 2: ENHANCED SL MANAGEMENT - Technical Exit System
        # CRITICAL FIX: Only apply technical exits to LOSING trades, NOT profitable BigMove trades
        if not technical_exit_available:
            tech_exit_signal, tech_exit_reason = check_technical_exit_conditions(
                {'K': current_k, 'D': current_d, 'williams_9': current_r, 'williams_28': current_r1},
                {'K': prev_k, 'D': prev_d, 'williams_9': prev_wr9, 'williams_28': prev_wr28},
                trade_config
            )
            
            if tech_exit_signal:
                technical_exit_available = True
                print(f"🔴 TECHNICAL EXIT SIGNAL at {bar['datetime']}: {tech_exit_reason} (Profit: {current_profit_pct:+.2f}%)")
                
                # CRITICAL FIX: Only exit on technical signals if trade is LOSING or barely profitable
                # Do NOT exit profitable BigMove trades early - let them run!
                should_exit_on_technical = False
                
                if current_profit_pct < -2.0:  # Losing trade
                    should_exit_on_technical = True
                    print(f"   → TECHNICAL EXIT: Cutting losses on losing trade")
                elif current_profit_pct < 1.0 and not is_big_move:  # Small profit on non-BigMove
                    should_exit_on_technical = True
                    print(f"   → TECHNICAL EXIT: Taking small profit on average trade")
                elif entry_risk_level == 'HIGH_RISK' and current_profit_pct < 0:  # High-risk losing trade
                    should_exit_on_technical = True
                    print(f"   → TECHNICAL EXIT: High-risk losing trade")
                else:
                    print(f"   → TECHNICAL EXIT IGNORED: Preserving profitable trade (BigMove={is_big_move}, Profit={current_profit_pct:+.2f}%)")
                
                if should_exit_on_technical:
                    exit_price = current_close
                    exit_time = bar['datetime']
                    exit_reason = f'Enhanced Technical Exit: {tech_exit_reason}'
                    break
                
                # For other cases, just tighten SL slightly
                elif not sl_tightened_by_yellow_flag and current_profit_pct < 0:
                    emergency_sl = entry_price * (1 - (initial_sl_pct - 1.0) / 100)  # Tighten by 1%
                    current_sl = max(current_sl, emergency_sl)
                    print(f"   → SL tightened by 1% due to technical signal")
        
        # Average Signal Management - Fixed TP approach
        if is_average_signal:
            fixed_tp_points = trade_config['AVERAGE_SIGNAL_MANAGEMENT'].get('FIXED_TP_POINTS', 10)
            
            # Fixed TP exit
            if current_high >= entry_price + fixed_tp_points:
                exit_price = entry_price + fixed_tp_points
                exit_time = bar['datetime']
                exit_reason = 'Fixed TP (Average Signal)'
                break
            
            # Quick breakeven for average signals
            breakeven_pct = trade_config['AVERAGE_SIGNAL_MANAGEMENT']['QUICK_EXIT_CONDITIONS'].get('BREAKEVEN_AFTER_PCT', 4.0)
            if current_profit_pct >= breakeven_pct:
                current_sl = max(current_sl, entry_price)
            
            # Quicker stall detection for average signals
            avg_stall_candles = trade_config['AVERAGE_SIGNAL_MANAGEMENT']['QUICK_EXIT_CONDITIONS'].get('STALL_CANDLES', 5)
            candle_range = current_high - current_low
            if candle_range < entry_price * (trade_config.get('STALL_THRESHOLD_PCT', 1.5) / 100):
                stall_count += 1
            else:
                stall_count = 0
            if stall_count >= avg_stall_candles:
                current_sl = max(current_sl, min(current_close, entry_price))
            
            # Williams exits for average signals
            if trade_config['AVERAGE_SIGNAL_MANAGEMENT']['QUICK_EXIT_CONDITIONS'].get('WILLIAMS_EXIT_ENABLED', True):
                williams28_cross = prev_wr28 > trade_config.get('WILLIAMS28_CROSS_UNDER', -80) and current_r1 <= trade_config.get('WILLIAMS28_CROSS_UNDER', -80)
                williams9_cross = current_profit_pct > 3 and prev_wr9 > trade_config.get('WILLIAMS9_CROSS_UNDER', -80) and current_r <= trade_config.get('WILLIAMS9_CROSS_UNDER', -80)
                
                if williams28_cross or williams9_cross:
                    exit_price = current_close
                    exit_time = bar['datetime']
                    exit_reason = 'Williams Exit (Average Signal)'
                    break
        
        # BigMove Management - Multi-stage trailing
        elif is_big_move:
            # Activate trailing based on tier settings
            if not trail_active and profit_pct >= tier['trail_start_pct']:
                trail_active = True
                print(f"Debug {entry_time}: Trailing activated at {profit_pct:.2f}% profit")
            
            # Multi-stage trailing logic
            if trail_active:
                atr_val = bar.get(atr_col, 0)
                trailing_config = get_trailing_stage_config(profit_pct, trade_config)
                
                # Time-based trailing adjustment
                minutes_elapsed = (pd.to_datetime(bar['datetime']) - entry_timestamp).total_seconds() / 60
                time_adjustment = get_time_based_adjustment(minutes_elapsed, trade_config)
                
                atr_multiplier = trailing_config['ATR_MULTIPLIER'] * time_adjustment
                min_sl_pct = trailing_config['MIN_SL_PCT']
                
                trailed_sl = highest_high - (atr_val * atr_multiplier)
                min_sl = entry_price * (1 - min_sl_pct / 100)
                
                # Profit protection logic
                protected_sl = get_profit_protection_sl(entry_price, highest_high, trade_config)
                
                trailed_sl = max(trailed_sl, min_sl, protected_sl)
                current_sl = max(current_sl, trailed_sl)
            
            # Enhanced EMA crossover exit for BigMoves
            if should_exit_on_ema_cross(trade_data, candle_count, current_profit_pct, trade_config, current_close, prev_k, prev_d, current_k, current_d):
                exit_price = current_close
                exit_time = bar['datetime']
                exit_reason = 'Enhanced EMA Exit (BigMove)'
                break
        
        # Regular trade management (neither average nor bigmove)
        else:
            # Standard trailing logic
            if not trail_active and profit_pct >= tier['trail_start_pct']:
                trail_active = True
            
            if trail_active:
                atr_val = bar.get(atr_col, 0)
                atr_multiplier = 1.0  # Standard multiplier for regular trades
                
                trailed_sl = highest_high - (atr_val * atr_multiplier)
                min_sl = entry_price * (1 - 8.0 / 100)  # 8% minimum SL
                
                trailed_sl = max(trailed_sl, min_sl)
                current_sl = max(current_sl, trailed_sl)
            
            # Standard breakeven logic
            if profit_pct >= trade_config.get('BREAKEVEN_MOVE_PCT', 4.0):
                breakeven_delay_counter += 1
                if breakeven_delay_counter >= tier['breakeven_delay']:
                    current_sl = max(current_sl, entry_price)
            
            # Standard Quick TP
            if current_high >= entry_price + trade_config.get('QUICK_TP_POINTS', 10):
                use_fade = trade_config.get('USE_STOCH_FADE_FOR_TP', False)
                if not use_fade or (prev_k > prev_d and current_k <= current_d):
                    exit_price = entry_price + trade_config.get('QUICK_TP_POINTS', 10)
                    exit_time = bar['datetime']
                    exit_reason = 'Quick TP'
                    break
        
        # SL Hit Check (common for all trade types)
        if current_low <= current_sl:
            exit_price = current_sl
            exit_time = bar['datetime']
            exit_reason = 'Trailing SL' if trail_active else 'SL Hit'
            break
        
        # Update previous indicators
        prev_wr28 = current_r1
        prev_wr9 = current_r
        prev_k = current_k
        prev_d = current_d
    
    # End of data exit
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
        'Trade Type': f"{trade_type} Option (Enhanced Hybrid Premium)",
        'Initial SL': f"{initial_sl:.2f}",
        'Final SL': f"{current_sl:.2f}",
        'Highest High': f"{highest_high:.2f}",
        'Big Move': str(is_big_move)
    }

def detect_big_move(trade_data, entry_price, trade_config, trade_type, is_big_move_from_signal=None):
    """Enhanced BigMove detection with momentum confirmation"""
    
    # Prioritize signal file if available
    if is_big_move_from_signal is not None:
        if isinstance(is_big_move_from_signal, str):
            return is_big_move_from_signal.upper() == 'TRUE'
        else:
            return bool(is_big_move_from_signal)
    
    # Check if signal differentiation is enabled
    if not trade_config.get('SIGNAL_DIFFERENTIATION', {}).get('ENABLED', False):
        return False
    
    avg_window = trade_config['SIGNAL_DIFFERENTIATION']['AVG_WINDOW_CANDLES']
    if len(trade_data) < avg_window:
        return False
    
    window_data = trade_data.iloc[:avg_window]
    
    # Primary threshold check
    avg_stoch_k = window_data['K'].mean() if 'K' in window_data.columns else 50
    avg_r1 = window_data['%R.1'].mean() if '%R.1' in window_data.columns else -50
    
    bigmove_config = trade_config['SIGNAL_DIFFERENTIATION'].get('BIGMOVE_DETECTION', {})
    thresholds = bigmove_config.get('THRESHOLDS', {})
    trade_type_upper = trade_type.upper()
    
    if trade_type_upper in thresholds:
        k_threshold = thresholds[trade_type_upper].get('STOCH_K_THRESHOLD', 78)
        r1_threshold = thresholds[trade_type_upper].get('WILLIAMS_R1_THRESHOLD', -50)
    else:
        k_threshold = 78
        r1_threshold = -50
    
    primary_condition = (avg_stoch_k > k_threshold) and (avg_r1 > r1_threshold)
    
    # Momentum confirmation
    momentum_config = bigmove_config.get('MOMENTUM_CONFIRMATION', {})
    if momentum_config.get('ENABLED', False) and primary_condition:
        # Check candle range
        min_range_pct = momentum_config.get('MIN_CANDLE_RANGE_PCT', 1.2)
        first_candle = window_data.iloc[0]
        candle_range_pct = ((first_candle['high'] - first_candle['low']) / entry_price) * 100
        
        if candle_range_pct < min_range_pct:
            return False
        
        # Check consecutive moves (if we have enough data)
        consecutive_moves = momentum_config.get('CONSECUTIVE_MOVES', 2)
        if len(window_data) >= consecutive_moves:
            moves_in_direction = 0
            for i in range(1, min(consecutive_moves + 1, len(window_data))):
                if trade_type_upper == 'CALL':
                    if window_data.iloc[i]['close'] > window_data.iloc[i-1]['close']:
                        moves_in_direction += 1
                else:  # PUT
                    if window_data.iloc[i]['close'] < window_data.iloc[i-1]['close']:  # Put options increase when underlying falls
                        moves_in_direction += 1
            
            if moves_in_direction < consecutive_moves:
                return False
    
    return primary_condition

def get_trailing_stage_config(profit_pct, trade_config):
    """Get trailing configuration based on current profit stage"""
    
    trailing_config = trade_config['SIGNAL_DIFFERENTIATION'].get('BIGMOVE_TRAILING', {})
    
    if profit_pct < trailing_config.get('STAGE1', {}).get('PROFIT_THRESHOLD', 25.0):
        return trailing_config.get('STAGE1', {
            'ATR_MULTIPLIER': 3.0,
            'MIN_SL_PCT': 8.0
        })
    elif profit_pct < trailing_config.get('STAGE2', {}).get('PROFIT_THRESHOLD', 50.0):
        return trailing_config.get('STAGE2', {
            'ATR_MULTIPLIER': 4.0,
            'MIN_SL_PCT': 15.0
        })
    else:
        return trailing_config.get('STAGE3', {
            'ATR_MULTIPLIER': 6.0,
            'MIN_SL_PCT': 25.0
        })

def get_time_based_adjustment(minutes_elapsed, trade_config):
    """Apply time-based trailing adjustments"""
    
    time_config = trade_config.get('RISK_MANAGEMENT', {}).get('TIME_BASED_TRAILING', {})
    if not time_config.get('ENABLED', False):
        return 1.0
    
    tighten_after = time_config.get('TIGHTEN_AFTER_MINUTES', 30)
    if minutes_elapsed > tighten_after:
        return time_config.get('TIGHTEN_MULTIPLIER', 0.8)
    
    return 1.0

def get_profit_protection_sl(entry_price, highest_high, trade_config):
    """Calculate profit protection stop loss"""
    
    protection_config = trade_config.get('RISK_MANAGEMENT', {}).get('PROFIT_PROTECTION', {})
    if not protection_config.get('ENABLED', False):
        return 0
    
    profit_pct = ((highest_high - entry_price) / entry_price) * 100
    protect_after_pct = protection_config.get('PROTECT_AFTER_PCT', 30.0)
    
    if profit_pct >= protect_after_pct:
        protection_level_pct = protection_config.get('PROTECTION_LEVEL_PCT', 20.0)
        protected_price = entry_price * (1 + protection_level_pct / 100)
        return protected_price
    
    return 0

def should_exit_on_ema_cross(trade_data, candle_count, current_profit_pct, trade_config, current_close, prev_k, prev_d, current_k, current_d):
    """Enhanced EMA crossover exit logic with additional filters"""
    
    ema_config = trade_config['SIGNAL_DIFFERENTIATION'].get('EMA_CROSS_EXIT', {})
    if not ema_config.get('ENABLED', False):
        return False
    
    min_profit = ema_config.get('MIN_PROFIT_PCT', 20.0)
    min_candles = ema_config.get('MIN_CANDLES_BEFORE_EXIT', 8)
    
    if current_profit_pct < min_profit or candle_count < min_candles:
        return False
    
    try:
        closes_series = trade_data['close'].iloc[:candle_count+1]
        ema_periods = ema_config.get('EMA_PERIODS', [9, 15])
        
        if len(closes_series) >= max(ema_periods):
            ema_short = ta.ema(closes_series, length=ema_periods[0]).iloc[-1]
            ema_long = ta.ema(closes_series, length=ema_periods[1]).iloc[-1]
            
            if len(closes_series) > 1:
                prev_closes_series = closes_series.iloc[:-1]
                prev_ema_short = ta.ema(prev_closes_series, length=ema_periods[0]).iloc[-1]
                prev_ema_long = ta.ema(prev_closes_series, length=ema_periods[1]).iloc[-1]
                
                # Basic bearish crossover
                bearish_cross = (prev_ema_short >= prev_ema_long) and (ema_short < ema_long)
                
                if bearish_cross:
                    # Additional confirmation filters
                    confirmation_filters = ema_config.get('CONFIRMATION_FILTERS', {})
                    
                    # Momentum weakening (Stochastic turning down)
                    if confirmation_filters.get('MOMENTUM_WEAKENING', False):
                        momentum_weak = (prev_k > prev_d and current_k <= current_d)
                        if not momentum_weak:
                            return False
                    
                    return True
        
    except Exception as e:
        pass
    
    return False

def get_dynamic_sl_percent(trade_data, entry_price, trade_config, tier):
    """Calculate dynamic SL percentage based on entry conditions"""
    
    enhanced_sl_config = trade_config.get('ENHANCED_SL_MANAGEMENT', {})
    if not enhanced_sl_config.get('ENABLED', False):
        return tier.get('sl_percent', trade_config.get('SL_PERCENT', 6.0))
    
    # Get entry candle indicators
    entry_candle = trade_data.iloc[0]
    stoch_k = entry_candle.get('K', 50)
    williams_r = entry_candle.get('%R', -50)
    
    dynamic_config = enhanced_sl_config.get('DYNAMIC_SL', {})
    
    # Determine risk level based on entry conditions
    high_risk_config = dynamic_config.get('HIGH_RISK', {})
    moderate_risk_config = dynamic_config.get('MODERATE_RISK', {})
    low_risk_config = dynamic_config.get('LOW_RISK', {})
    
    if (stoch_k > high_risk_config.get('STOCH_K_THRESHOLD', 85) and 
        williams_r > high_risk_config.get('WILLIAMS_R_THRESHOLD', -20)):
        # High risk entry - tight SL
        sl_percent = high_risk_config.get('SL_PERCENT', 3.5)
        print(f"Debug: HIGH RISK entry detected (K:{stoch_k:.1f}, %R:{williams_r:.1f}) - SL: {sl_percent}%")
        
    elif (stoch_k > moderate_risk_config.get('STOCH_K_THRESHOLD', 70) and 
          williams_r > moderate_risk_config.get('WILLIAMS_R_THRESHOLD', -50)):
        # Moderate risk entry - standard SL
        sl_percent = moderate_risk_config.get('SL_PERCENT', 5.0)
        print(f"Debug: MODERATE RISK entry detected (K:{stoch_k:.1f}, %R:{williams_r:.1f}) - SL: {sl_percent}%")
        
    else:
        # Low risk entry - relaxed SL
        sl_percent = low_risk_config.get('SL_PERCENT', 7.0)
        print(f"Debug: LOW RISK entry detected (K:{stoch_k:.1f}, %R:{williams_r:.1f}) - SL: {sl_percent}%")
    
    # Time-based adjustments
    entry_time = pd.to_datetime(trade_data.iloc[0]['datetime'])
    sl_percent = apply_time_based_sl_adjustment(sl_percent, entry_time, enhanced_sl_config)
    
    return sl_percent

def apply_time_based_sl_adjustment(sl_percent, entry_time, enhanced_sl_config):
    """Apply time-based adjustments to SL percentage"""
    
    time_config = enhanced_sl_config.get('TIME_BASED_SL', {})
    if not time_config.get('ENABLED', False):
        return sl_percent
    
    entry_hour = entry_time.hour
    entry_minute = entry_time.minute
    
    # Opening hour adjustment (9:15-10:15)
    if entry_hour == 9 or (entry_hour == 10 and entry_minute <= 15):
        reduction = time_config.get('OPENING_HOUR_REDUCTION', 1.0)
        sl_percent = max(sl_percent - reduction, 2.0)  # Minimum 2% SL
        print(f"Debug: Opening hour SL adjustment: -{reduction}% -> {sl_percent}%")
    
    # Closing hour adjustment (15:00-15:30)
    elif entry_hour == 15:
        increase = time_config.get('CLOSING_HOUR_INCREASE', 1.0)
        sl_percent = min(sl_percent + increase, 10.0)  # Maximum 10% SL
        print(f"Debug: Closing hour SL adjustment: +{increase}% -> {sl_percent}%")
    
    return sl_percent

def check_yellow_flag_conditions(current_candle, prev_candle, enhanced_sl_config):
    """Check for early warning (yellow flag) conditions"""
    
    yellow_flag_config = enhanced_sl_config.get('YELLOW_FLAG_SYSTEM', {})
    if not yellow_flag_config.get('ENABLED', False):
        return False, []
    
    warnings = []
    
    # Williams %R crossing above warning threshold
    williams_r_threshold = yellow_flag_config.get('WILLIAMS_R_CROSS', -80)
    if (prev_candle.get('%R', 0) <= williams_r_threshold and 
        current_candle.get('%R', 0) > williams_r_threshold):
        warnings.append('Williams %R momentum loss')
    
    # Stochastic momentum drop
    momentum_drop_threshold = yellow_flag_config.get('STOCH_MOMENTUM_DROP', 20)
    k_drop = prev_candle.get('K', 50) - current_candle.get('K', 50)
    if k_drop >= momentum_drop_threshold:
        warnings.append(f'Stoch K momentum drop: {k_drop:.1f}')
    
    # Both Williams indicators above danger zone
    double_reversal_threshold = yellow_flag_config.get('DOUBLE_REVERSAL', -50)
    if (current_candle.get('%R', 0) > double_reversal_threshold and 
        current_candle.get('%R.1', 0) > double_reversal_threshold):
        warnings.append('Double Williams reversal signal')
    
    return len(warnings) > 0, warnings

def check_technical_exit_conditions(current_candle, prev_candle, enhanced_sl_config):
    """Check for immediate technical exit conditions"""
    
    tech_exit_config = enhanced_sl_config.get('TECHNICAL_EXITS', {})
    if not tech_exit_config.get('ENABLED', False):
        return False, None
    
    # Immediate exit on Williams %R reversal
    williams_reversal_threshold = tech_exit_config.get('WILLIAMS_R_REVERSAL', -20)
    if current_candle.get('%R', 0) > williams_reversal_threshold:
        return True, f'Williams %R reversal: {current_candle.get("%R", 0):.1f} > {williams_reversal_threshold}'
    
    # Stochastic exhaustion
    stoch_exhaustion = tech_exit_config.get('STOCH_EXHAUSTION', 90)
    current_k = current_candle.get('K', 50)
    prev_k = prev_candle.get('K', 50)
    if current_k > stoch_exhaustion and current_k < prev_k:
        return True, f'Stochastic exhaustion: K={current_k:.1f} declining from {stoch_exhaustion}+'
    
    # Stochastic bearish crossover
    if tech_exit_config.get('STOCH_BEARISH_CROSS', False):
        current_k = current_candle.get('K', 50)
        current_d = current_candle.get('D', 50)
        prev_k = prev_candle.get('K', 50)
        prev_d = prev_candle.get('D', 50)
        
        if (prev_k >= prev_d and current_k < current_d and current_k > 70):
            return True, f'Stochastic bearish cross: K({current_k:.1f}) < D({current_d:.1f})'
    
    return False, None

def assess_entry_risk_level(entry_candle):
    """Assess entry risk level based on technical conditions - PHASE 2 Enhancement"""
    # Handle missing indicators gracefully
    k = entry_candle.get('K', 50)
    williams_9 = entry_candle.get('%R', -50)
    williams_28 = entry_candle.get('%R.1', -50)
    
    # Convert None values to defaults
    if k is None or pd.isna(k):
        k = 50
    if williams_9 is None or pd.isna(williams_9):
        williams_9 = -50
    if williams_28 is None or pd.isna(williams_28):
        williams_28 = -50
    
    # Ensure numeric values
    try:
        k = float(k)
        williams_9 = float(williams_9)
        williams_28 = float(williams_28)
    except (ValueError, TypeError):
        # Fallback to defaults if conversion fails
        k = 50
        williams_9 = -50
        williams_28 = -50
    
    if k > 85 and williams_9 > -20:
        return 'HIGH_RISK'
    elif k > 70 and williams_9 > -50:
        return 'MODERATE_RISK'
    else:
        return 'LOW_RISK'

def detect_yellow_flag_conditions(current_candle, prev_candle, trade_config):
    """PHASE 2: Detect Yellow Flag (early warning) conditions"""
    enhanced_sl_config = trade_config.get('ENHANCED_SL_MANAGEMENT', {})
    if not enhanced_sl_config.get('ENABLED', False):
        return []
    
    yellow_flag_config = enhanced_sl_config.get('YELLOW_FLAG_SYSTEM', {})
    if not yellow_flag_config.get('ENABLED', False):
        return []
    
    flags = []
    
    try:
        # Safely get values with defaults
        def safe_get(candle, key, default):
            value = candle.get(key, default)
            if value is None or pd.isna(value):
                return default
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        
        curr_k = safe_get(current_candle, 'K', 50)
        curr_d = safe_get(current_candle, 'D', 50)
        curr_wr9 = safe_get(current_candle, 'williams_9', -50)
        curr_wr28 = safe_get(current_candle, 'williams_28', -50)
        
        prev_k = safe_get(prev_candle, 'K', 50)
        prev_d = safe_get(prev_candle, 'D', 50)
        prev_wr9 = safe_get(prev_candle, 'williams_9', -50)
        prev_wr28 = safe_get(prev_candle, 'williams_28', -50)
        
        # Williams %R momentum loss (crossing above -80)
        williams_threshold = yellow_flag_config.get('WILLIAMS_R_CROSS', -80)
        if (prev_wr9 <= williams_threshold and curr_wr9 > williams_threshold):
            flags.append('Williams %R(9) momentum loss')
        
        if (prev_wr28 <= williams_threshold and curr_wr28 > williams_threshold):
            flags.append('Williams %R(28) momentum loss')
        
        # Stochastic momentum drop (K drops significantly)
        momentum_drop_threshold = yellow_flag_config.get('STOCH_MOMENTUM_DROP', 20)
        k_drop = prev_k - curr_k
        if k_drop >= momentum_drop_threshold:
            flags.append(f'Stoch K momentum drop: {k_drop:.1f} points')
        
        # Stochastic bearish crossover
        if (prev_k >= prev_d and curr_k < curr_d):
            flags.append('Stoch K/D bearish crossover')
        
        # Both Williams indicators in danger zone
        double_reversal_threshold = yellow_flag_config.get('DOUBLE_REVERSAL', -50)
        if (curr_wr9 > double_reversal_threshold and curr_wr28 > double_reversal_threshold):
            flags.append('Double Williams reversal risk')
    
    except Exception as e:
        # Log error but don't crash
        print(f"Warning: Yellow flag detection error: {e}")
    
    return flags

def check_technical_exit_conditions(current_candle, prev_candle, trade_config):
    """PHASE 2: Check for immediate technical exit conditions"""
    enhanced_sl_config = trade_config.get('ENHANCED_SL_MANAGEMENT', {})
    if not enhanced_sl_config.get('ENABLED', False):
        return False, None
    
    tech_exit_config = enhanced_sl_config.get('TECHNICAL_EXITS', {})
    if not tech_exit_config.get('ENABLED', False):
        return False, None
    
    try:
        # Safely get values with defaults
        def safe_get(candle, key, default):
            value = candle.get(key, default)
            if value is None or pd.isna(value):
                return default
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        
        curr_k = safe_get(current_candle, 'K', 50)
        curr_d = safe_get(current_candle, 'D', 50)
        curr_wr9 = safe_get(current_candle, 'williams_9', -50)
        curr_wr28 = safe_get(current_candle, 'williams_28', -50)
        
        prev_k = safe_get(prev_candle, 'K', 50)
        prev_d = safe_get(prev_candle, 'D', 50)
        prev_wr9 = safe_get(prev_candle, 'williams_9', -50)
        prev_wr28 = safe_get(prev_candle, 'williams_28', -50)
        
        # Williams %R reversal (immediate exit)
        williams_reversal_threshold = tech_exit_config.get('WILLIAMS_R_REVERSAL', -20)
        if curr_wr9 > williams_reversal_threshold:
            return True, f'Williams %R(9) reversal: {curr_wr9:.1f} > {williams_reversal_threshold}'
        
        # Stochastic exhaustion
        stoch_exhaustion = tech_exit_config.get('STOCH_EXHAUSTION', 90)
        if (curr_k > stoch_exhaustion and curr_k < prev_k):
            return True, f'Stoch exhaustion: K={curr_k:.1f} declining from {stoch_exhaustion}+'
        
        # Double reversal signal
        double_reversal_threshold = tech_exit_config.get('DOUBLE_REVERSAL', -50)
        if (curr_wr9 > double_reversal_threshold and curr_wr28 > double_reversal_threshold):
            return True, 'Double Williams reversal signal'
        
        # Extreme momentum reversal
        if (prev_k > 85 and curr_k < 70):
            return True, f'Extreme momentum reversal: K dropped from {prev_k:.1f} to {curr_k:.1f}'
        
        # Stochastic bearish crossover with high K
        if tech_exit_config.get('STOCH_BEARISH_CROSS', False):
            if (prev_k >= prev_d and curr_k < curr_d and curr_k > 70):
                return True, f'Stochastic bearish cross: K({curr_k:.1f}) < D({curr_d:.1f})'
    
    except Exception as e:
        # Log error but don't crash
        print(f"Warning: Technical exit detection error: {e}")
    
    return False, None

def get_premium_tier(entry_price, tiers):
    """Function to determine premium tier based on entry price"""
    for tier, info in tiers.items():
        if entry_price < info['threshold']:
            return info
    return tiers['HIGH']
