# option_tools/__init__.py
import yaml

def load_main_config():
    """Load main configuration from config.yaml"""
    try:
        with open('config.yaml', 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Warning: Could not load config.yaml: {e}")
        return {'TRADE_STRATEGY': 'COMPLEX'}

config = load_main_config()
strategy_type = config.get('TRADE_STRATEGY', 'COMPLEX')

if strategy_type == 'SIMPLE':
    from .simple_trade_executor import execute_option_trades
    from .index_trade_executor import execute_index_trades_simple as execute_index_trades
    print("--- Using SIMPLE trading strategy for both options and index trades ---")
else:
    from .option_trade_executor import execute_option_trades
    from .index_trade_executor import execute_index_trades_complex as execute_index_trades
    print("--- Using COMPLEX trading strategy for both options and index trades ---")

from .options_run_analytics import run_option_analysis
from .option_run_backtesting import run_option_backtest, run_combined_option_backtest

__all__ = [
    'execute_option_trades',
    'execute_index_trades',
    'run_option_analysis',
    'run_option_backtest',
    'run_combined_option_backtest'
]
