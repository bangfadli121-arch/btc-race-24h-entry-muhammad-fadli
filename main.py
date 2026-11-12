"""Deterministic CBBTC bot for the make.fun bars-replay/v1 protocol."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars


SYMBOL = "CBBTC"
FAST_PERIOD = 60
SLOW_PERIOD = 240


class StrategyState:
    """Per-run EMA history and the highest close since the current entry."""

    def __init__(self):
        self.fast_ema = None
        self.slow_ema = None
        self.peak_close = None


strategy = StrategyState()


def update_emas(close):
    """Update fast and slow EMAs on one fresh CBBTC bar and report crossover flags."""
    if strategy.fast_ema is None:
        strategy.fast_ema = float(close)
        strategy.slow_ema = float(close)
        return False, False

    fast_before = strategy.fast_ema
    slow_before = strategy.slow_ema
    strategy.fast_ema = fast_before + (2.0 / (FAST_PERIOD + 1)) * (close - fast_before)
    strategy.slow_ema = slow_before + (2.0 / (SLOW_PERIOD + 1)) * (close - slow_before)
    crossed_up = strategy.fast_ema > strategy.slow_ema and fast_before <= slow_before
    crossed_down = strategy.fast_ema < strategy.slow_ema and fast_before >= slow_before
    return crossed_up, crossed_down


def should_take_profit(state, position):
    """Use integer quote units to check whether marked value is at least 0.8% over cost."""
    return state.value(SYMBOL, position.qty) * 1000 >= position.cost * 1008


def should_trail_exit(close):
    """Use integer close prices to check a 0.4% decline from the entry peak."""
    return close * 1000 <= strategy.peak_close * 996


def on_batch(state, batch):
    """Handle one protocol batch/bar and return at most one order; warm-up bars only build history."""
    bar = next((item for item in batch["bars"] if item["symbol"] == SYMBOL), None)
    if bar is None:
        return []

    try:
        close = int(bar["c"])
    except (KeyError, TypeError, ValueError):
        return []
    if close <= 0:
        return []
    crossed_up, crossed_down = update_emas(close)
    position = state.positions.get(SYMBOL)

    if position is None:
        strategy.peak_close = None
    else:
        strategy.peak_close = close if strategy.peak_close is None else max(strategy.peak_close, close)

    if state.warming_up:
        return []

    if position is not None:
        if should_take_profit(state, position) or should_trail_exit(close) or crossed_down:
            order = {
                "side": "sell",
                "symbol": SYMBOL,
                "qty": position.qty,
                "max_slippage_bps": 10000,
            }
            return [order]
        return []

    if crossed_up and state.cash > 0:
        return [{
            "side": "buy",
            "symbol": SYMBOL,
            "notional_quote_units": state.cash,
            "max_slippage_bps": 10000,
        }]
    return []


if __name__ == "__main__":
    # The shim handles hello, batch, bar, orders, sequence echoes, and done messages.
    makefun_bars.run(on_batch)
