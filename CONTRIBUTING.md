# Contributing

The most valuable contribution is a **correction**. If a symbol here is wrong
for a broker you actually trade with, that is a real bug and it matters more
than any feature.

## Reporting a wrong or missing symbol

[Open an issue](../../issues/new) with:

- the broker and the **exact server name** from your terminal
  (MetaTrader: *File → Open an Account*, or the status bar at bottom right)
- the instrument, and the symbol string your terminal actually shows
- MT4 or MT5, and the account type if you know it (standard / raw / ECN / cent)

Account type matters: the same broker often exposes `XAUUSD` on a standard
account and `XAUUSD.raw` on a raw one, so both can be correct at once. Where
that is the case we would rather list both than pick one.

## Adding a broker

Same as above, plus the instruments you can see. A screenshot of Market Watch
with "Show All" enabled is genuinely the easiest way to send it.

## Data conventions

- `canonical` is the plain MetaTrader-style name an EA would naively hard-code
  (`EURUSD`, `XAUUSD`, `SP500`), not an ISIN or an exchange ticker.
- `symbol` is the exact string the broker's server returns, byte for byte,
  including case and punctuation. Do not normalise it.
- Empty cells mean the server did not report that field. They are never
  guesses, and should stay empty rather than being filled with a default.
- Only instruments quoted by 50+ brokers are included, so the table stays a
  cross-broker lookup rather than a dump of one-off CFDs.

## Code

`python/symbol_map.py` has no dependencies beyond the standard library, and it
should stay that way. The MQL includes must compile under both MQL4 and MQL5
strict mode.

Run the validator before opening a PR:

```bash
python3 python/validate.py
```
