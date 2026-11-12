# CBBTC EMA race bot

This Python 3.13 bot trades only CBBTC. Its hello/batch/orders/bar loop is handled by the vendored `makefun_bars` shim: each incoming batch updates the current bar and account state, the callback returns zero or one orders, and the shim replies once with the same sequence number.

The bot updates fast EMA(60) and slow EMA(240) from the close only when a batch contains a fresh CBBTC bar. It sends no orders during warm-up. When flat, it buys with all available cash on a fast EMA cross above the slow EMA. While holding CBBTC, it sells the whole position if marked value is at least 0.8 percent above cost, the latest close is at least 0.4 percent below the highest close since entry, or the fast EMA crosses below the slow EMA.

## Run locally

From the repository root, feed protocol JSON lines to the bot:

```sh
python3 main.py < input.ndjson > replies.ndjson
```

The input stream starts with `hello`, carries one `batch` per bar, and ends with `done`. The shim validates orders and emits one reply per batch.

## Determinism

The strategy uses only protocol-provided state and fresh bar data. It does not read the clock, environment, network, or data files; uses no randomness; and performs the two EMA calculations in a fixed order using floats. Exit thresholds use integer arithmetic. Identical inputs therefore produce identical orders and reply bytes.
