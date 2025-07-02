# This file makes the 'strategies' folder a Python package.

from .run_cont_strategy import generate_continuation_strategies
from .run_rev_strategy import generate_reversal_strategies

print("--- Strategies Package Initialized ---")