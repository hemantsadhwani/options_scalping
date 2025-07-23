# option_tools/simple_trade_config.py

import yaml
import os

def load_simple_trade_config():
    """Load trade configuration from option_tools/simple_trade_config.yaml"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'simple_trade_config.yaml')
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Warning: Could not load simple_trade_config.yaml: {e}")
        # Fallback to default values based on the provided rules
        return {
            'INDICATORS': {
                'ATR_PERIOD': 5,
                'SWING_LOW_PERIOD': 5,
            },
            'STOP_LOSS': {
                'INITIAL_FIXED_SL_PERCENT': 5.0,
                'TRAILING_ACTIVATION_PROFIT_PERCENT': 5.0,
                'ATR_MULTIPLIERS': [
                    {'profit_threshold': 10.0, 'multiplier': 1.8},
                    {'profit_threshold': 25.0, 'multiplier': 3.0},
                    {'profit_threshold': 9999.0, 'multiplier': 2.2},
                ],
            },
        }
