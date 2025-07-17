#!/usr/bin/env python3
"""
Test Enhanced SL Management System - Phase 2 Validation
Tests the new Yellow Flag and Technical Exit systems on historical SL hit trades
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime

# Add option_tools to path
sys.path.append('option_tools')
from option_trade_executor import (
    execute_option_trades, 
    assess_entry_risk_level,
    detect_yellow_flag_conditions,
    check_technical_exit_conditions,
    load_trade_config
)

def test_enhanced_sl_on_historical_trades():
    """Test enhanced SL system on the 9 historical SL hit trades"""
    
    print("🧪 TESTING ENHANCED SL MANAGEMENT SYSTEM - PHASE 2 VALIDATION")
    print("=" * 80)
    
    # Load enhanced trade configuration
    trade_config = load_trade_config()
    
    # Historical SL hit trades from our analysis
    test_trades = [
        # 1407 Put trades
        {'date': '1407', 'type': 'put', 'entry_time': '10:11', 'exit_time': '10:12', 'entry_price': 102.75, 'exit_price': 96.58, 'highest_high': 104.4, 'bigmove': False},
        {'date': '1407', 'type': 'put', 'entry_time': '12:25', 'exit_time': '12:33', 'entry_price': 125.05, 'exit_price': 117.55, 'highest_high': 128.55, 'bigmove': True},
        {'date': '1407', 'type': 'put', 'entry_time': '12:38', 'exit_time': '12:40', 'entry_price': 122.95, 'exit_price': 115.57, 'highest_high': 123.75, 'bigmove': False},
        {'date': '1407', 'type': 'put', 'entry_time': '14:37', 'exit_time': '14:38', 'entry_price': 117.45, 'exit_price': 110.4, 'highest_high': 118.25, 'bigmove': False},
        {'date': '1407', 'type': 'put', 'entry_time': '15:11', 'exit_time': '15:12', 'entry_price': 97.35, 'exit_price': 91.51, 'highest_high': 98.25, 'bigmove': False},
        
        # 1507 Call trades  
        {'date': '1507', 'type': 'call', 'entry_time': '13:03', 'exit_time': '13:11', 'entry_price': 169.75, 'exit_price': 159.56, 'highest_high': 173.5, 'bigmove': True},
        {'date': '1507', 'type': 'call', 'entry_time': '13:49', 'exit_time': '14:02', 'entry_price': 148.25, 'exit_price': 139.35, 'highest_high': 149.4, 'bigmove': True},
        
        # 1107 Put trades
        {'date': '1107', 'type': 'put', 'entry_time': '12:53', 'exit_time': '14:12', 'entry_price': 126.6, 'exit_price': 119.0, 'highest_high': 140.95, 'bigmove': True},
        {'date': '1107', 'type': 'put', 'entry_time': '14:21', 'exit_time': '14:39', 'entry_price': 131.3, 'exit_price': 123.42, 'highest_high': 134.9, 'bigmove': False},
    ]
    
    total_old_loss = 0
    total_new_loss = 0
    improvements = []
    
    for i, trade in enumerate(test_trades, 1):
        print(f"\n{'=' * 60}")
        print(f"TEST {i}/9: {trade['date']} {trade['type'].upper()} {trade['entry_time']}-{trade['exit_time']}")
        print(f"Original: Entry {trade['entry_price']}, Exit {trade['exit_price']} (-6.00%)")
        print(f"{'=' * 60}")
        
        # Simulate enhanced SL management
        result = simulate_enhanced_sl_trade(trade, trade_config)
        
        if result:
            old_loss_pct = -6.0  # All original trades were -6% SL hits
            new_loss_pct = result['final_loss_pct']
            improvement = old_loss_pct - new_loss_pct
            
            total_old_loss += abs(old_loss_pct)
            total_new_loss += abs(new_loss_pct)
            improvements.append(improvement)
            
            print(f"📊 RESULTS:")
            print(f"   Original Loss: {old_loss_pct:.2f}%")
            print(f"   Enhanced Loss: {new_loss_pct:.2f}%")
            print(f"   Improvement: {improvement:+.2f}%")
            print(f"   Risk Level: {result['entry_risk_level']}")
            print(f"   Dynamic SL: {result['dynamic_sl_pct']:.1f}%")
            
            if result['yellow_flags']:
                print(f"   🟡 Yellow Flags: {len(result['yellow_flags'])} detected")
                for flag in result['yellow_flags']:
                    print(f"      → {flag['time']}: {', '.join(flag['flags'])}")
            
            if result['technical_exits']:
                print(f"   🔴 Technical Exits: {len(result['technical_exits'])} detected")
                for exit in result['technical_exits']:
                    print(f"      → {exit['time']}: {exit['reason']}")
            
            if result['exit_reason'].startswith('Enhanced'):
                print(f"   ✅ ENHANCED EXIT: {result['exit_reason']}")
            else:
                print(f"   ❌ Still SL Hit: {result['exit_reason']}")
    
    # Summary
    print(f"\n{'=' * 80}")
    print("🎯 PHASE 2 VALIDATION SUMMARY")
    print("=" * 80)
    
    total_improvement = sum(improvements)
    avg_improvement = np.mean(improvements)
    successful_improvements = len([imp for imp in improvements if imp > 0])
    
    print(f"📊 PERFORMANCE METRICS:")
    print(f"   Total Original Loss: {total_old_loss:.2f}%")
    print(f"   Total Enhanced Loss: {total_new_loss:.2f}%")
    print(f"   Total Improvement: {total_improvement:+.2f}%")
    print(f"   Average Improvement per Trade: {avg_improvement:+.2f}%")
    print(f"   Successful Improvements: {successful_improvements}/9 trades ({successful_improvements/9*100:.1f}%)")
    
    overall_improvement_pct = (total_improvement / total_old_loss) * 100
    print(f"   🚀 OVERALL IMPROVEMENT: {overall_improvement_pct:.1f}% reduction in SL losses")
    
    print(f"\n🎯 VALIDATION RESULTS:")
    if overall_improvement_pct > 30:
        print(f"   ✅ EXCELLENT: Enhanced SL system shows significant improvement!")
        print(f"   ✅ Ready for live deployment with monitoring")
    elif overall_improvement_pct > 15:
        print(f"   ✅ GOOD: Enhanced SL system shows meaningful improvement")
        print(f"   ⚠️  Consider additional fine-tuning before deployment")
    else:
        print(f"   ⚠️  NEEDS WORK: Enhancement needs further optimization")
        print(f"   🔧 Review configuration parameters and logic")
    
    return {
        'total_improvement': total_improvement,
        'avg_improvement': avg_improvement,
        'success_rate': successful_improvements / 9,
        'overall_improvement_pct': overall_improvement_pct
    }

def simulate_enhanced_sl_trade(trade, trade_config):
    """Simulate enhanced SL management on a historical trade"""
    
    # Load price data
    price_file = f"data/{trade['date']}/{trade['type'].lower()}/{trade['type'].lower()}_out.csv"
    
    try:
        df = pd.read_csv(price_file)
        df['datetime'] = pd.to_datetime(df['datetime'])
        
        # Filter data between entry and exit
        entry_dt = pd.to_datetime(f"2025-07-{trade['date'][:2]} {trade['entry_time']}")
        exit_dt = pd.to_datetime(f"2025-07-{trade['date'][:2]} {trade['exit_time']}")
        
        trade_data = df[(df['datetime'] >= entry_dt) & (df['datetime'] <= exit_dt)].copy()
        
        if trade_data.empty:
            return None
        
        # Simulate enhanced SL management
        entry_price = trade['entry_price']
        entry_candle = trade_data.iloc[0]
        
        # Entry risk assessment
        entry_risk_level = assess_entry_risk_level(entry_candle)
        
        # Dynamic SL calculation
        dynamic_sl_pct = get_dynamic_sl_percent_for_test(entry_candle, trade_config, entry_risk_level)
        dynamic_sl = entry_price * (1 - dynamic_sl_pct / 100)
        
        # Track enhanced SL management
        current_sl = dynamic_sl
        yellow_flags = []
        technical_exits = []
        exit_price = None
        exit_time = None
        exit_reason = 'SL Hit'
        
        prev_candle = None
        
        for idx, row in trade_data.iterrows():
            current_candle = {
                'K': row.get('K', 50),
                'D': row.get('D', 50),
                'williams_9': row.get('%R', -50),
                'williams_28': row.get('%R.1', -50)
            }
            
            current_profit_pct = ((row['close'] - entry_price) / entry_price) * 100
            
            # Yellow Flag detection
            if prev_candle is not None:
                flags = detect_yellow_flag_conditions(current_candle, prev_candle, trade_config)
                if flags:
                    yellow_flags.append({
                        'time': row['datetime'].strftime('%H:%M'),
                        'flags': flags,
                        'profit': current_profit_pct
                    })
                    
                    # Tighten SL on Yellow Flag
                    tighten_pct = trade_config.get('ENHANCED_SL_MANAGEMENT', {}).get('YELLOW_FLAG_SYSTEM', {}).get('TIGHTEN_SL_PCT', 1.5)
                    tightened_sl = entry_price * (1 - (dynamic_sl_pct - tighten_pct) / 100)
                    current_sl = max(current_sl, tightened_sl)
                
                # Technical Exit detection
                tech_exit_signal, tech_exit_reason = check_technical_exit_conditions(current_candle, prev_candle, trade_config)
                if tech_exit_signal:
                    technical_exits.append({
                        'time': row['datetime'].strftime('%H:%M'),
                        'reason': tech_exit_reason,
                        'profit': current_profit_pct
                    })
                    
                    # Exit immediately on technical signal if profitable or high-risk entry
                    if entry_risk_level == 'HIGH_RISK' or current_profit_pct > 0:
                        exit_price = row['close']
                        exit_time = row['datetime']
                        exit_reason = f'Enhanced Technical Exit: {tech_exit_reason}'
                        break
            
            # Check SL hit
            if row['low'] <= current_sl:
                exit_price = current_sl
                exit_time = row['datetime']
                exit_reason = 'Enhanced SL Hit'
                break
            
            prev_candle = current_candle
        
        # If no exit found, use end of data
        if exit_price is None:
            exit_price = trade_data.iloc[-1]['close']
            exit_time = trade_data.iloc[-1]['datetime']
            exit_reason = 'End of Data'
        
        final_loss_pct = ((exit_price - entry_price) / entry_price) * 100
        
        return {
            'entry_risk_level': entry_risk_level,
            'dynamic_sl_pct': dynamic_sl_pct,
            'final_loss_pct': final_loss_pct,
            'exit_reason': exit_reason,
            'yellow_flags': yellow_flags,
            'technical_exits': technical_exits
        }
        
    except Exception as e:
        print(f"Error simulating {trade['date']} {trade['type']}: {e}")
        return None

def get_dynamic_sl_percent_for_test(entry_candle, trade_config, entry_risk_level):
    """Calculate dynamic SL percentage for testing"""
    
    enhanced_sl_config = trade_config.get('ENHANCED_SL_MANAGEMENT', {})
    if not enhanced_sl_config.get('ENABLED', False):
        return 6.0  # Default SL
    
    dynamic_config = enhanced_sl_config.get('DYNAMIC_SL', {})
    
    if entry_risk_level == 'HIGH_RISK':
        return dynamic_config.get('HIGH_RISK', {}).get('SL_PERCENT', 3.5)
    elif entry_risk_level == 'MODERATE_RISK':
        return dynamic_config.get('MODERATE_RISK', {}).get('SL_PERCENT', 5.0)
    else:
        return dynamic_config.get('LOW_RISK', {}).get('SL_PERCENT', 7.0)

if __name__ == "__main__":
    try:
        # Test enhanced SL system
        results = test_enhanced_sl_on_historical_trades()
        
        print(f"\n{'=' * 80}")
        print("🎯 PHASE 2 IMPLEMENTATION STATUS")
        print("=" * 80)
        
        if results['overall_improvement_pct'] > 30:
            print("✅ PHASE 2 COMPLETE: Enhanced SL Management System validated!")
            print("🚀 Ready to proceed with Phase 3: Live Testing & Monitoring")
        else:
            print("⚠️  PHASE 2 NEEDS REFINEMENT: Continue optimization")
            print("🔧 Review parameters and add additional logic")
        
        print(f"\n📋 NEXT STEPS:")
        print(f"1. 📊 Monitor live performance with enhanced SL system")
        print(f"2. 📝 Update ENHANCED_TRADING_SYSTEM_SUMMARY_FOR_SL.md with results")
        print(f"3. 🔧 Fine-tune parameters based on live performance")
        print(f"4. 📈 Implement Phase 3: Advanced features (volatility adjustment, etc.)")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
