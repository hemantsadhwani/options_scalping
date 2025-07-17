import pandas as pd

def load_data():
    trades_path = './data/1107/put/trades/put_rev_v2_trades.csv'
    price_path = './data/1107/put/put_out.csv'
    
    trades_df = pd.read_csv(trades_path, parse_dates=['Entry Time', 'Exit Time'])
    price_df = pd.read_csv(price_path, parse_dates=['datetime'])
    price_df.set_index('datetime', inplace=True)
    
    return trades_df, price_df

def analyze_trades(trades_df, price_df):
    debug_records = []
    
    for idx, trade in trades_df.iterrows():
        entry_time = trade['Entry Time']
        exit_time = trade['Exit Time']
        entry_price = trade['Entry Price']
        exit_price = trade['Exit Price']
        exit_reason = trade['Exit Reason']
        pl = trade['P/L']
        pl_pct = trade['P/L %']
        
        # Extract price and indicator data during trade duration
        trade_data = price_df.loc[entry_time:exit_time]
        
        # Basic stats for research
        max_high = trade_data['high'].max() if not trade_data.empty else None
        min_low = trade_data['low'].min() if not trade_data.empty else None
        avg_k = trade_data['K'].mean() if not trade_data.empty else None
        avg_d = trade_data['D'].mean() if not trade_data.empty else None
        avg_wr9 = trade_data['%R'].mean() if not trade_data.empty else None
        avg_wr28 = trade_data['%R.1'].mean() if not trade_data.empty else None
        
        debug_records.append({
            'Entry Time': entry_time,
            'Exit Time': exit_time,
            'Entry Price': entry_price,
            'Exit Price': exit_price,
            'P/L': pl,
            'P/L %': pl_pct,
            'Exit Reason': exit_reason,
            'Max High During Trade': max_high,
            'Min Low During Trade': min_low,
            'Avg Stoch K': avg_k,
            'Avg Stoch D': avg_d,
            'Avg Williams %R9': avg_wr9,
            'Avg Williams %R28': avg_wr28,
            'Trade Duration (minutes)': (exit_time - entry_time).total_seconds() / 60.0
        })
    
    debug_df = pd.DataFrame(debug_records)
    debug_output_path = './option_tools/debug_trade_analysis_output.csv'
    debug_df.to_csv(debug_output_path, index=False)
    print(f"Debug analysis saved to {debug_output_path}")

def main():
    trades_df, price_df = load_data()
    analyze_trades(trades_df, price_df)

if __name__ == '__main__':
    main()
