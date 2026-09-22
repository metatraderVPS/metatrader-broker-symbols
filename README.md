# MetaTrader Broker Symbols

**The same instrument has a different symbol name on almost every MetaTrader broker. This is the lookup table.**

Gold is `XAUUSD` on 156 brokers, `GOLD` on others, and `XAUUSD.m`, `XAUUSD.s`, `XAUUSDp`, `XAUUSD!`, `GOLD_USD` or `XAUUSD.pro` on the rest — **44 distinct spellings across 230 brokers**. An Expert Advisor that hard-codes one of them silently fails on the others, usually as `SymbolSelect()` returning `false` or `OrderSend` erroring with no obvious cause.

This repository contains the real symbol names, read from **241 live MT4/MT5 broker servers** — not scraped from broker marketing pages, not guessed from patterns.

```
241 brokers   ·   96 instruments   ·   13,771 measured symbol names   ·   240 GMT offsets
```

| | |
|---|---|
| **Data** | [`data/symbols.csv`](data/symbols.csv) · [`data/brokers.json`](data/brokers.json) · [`data/gmt-offsets.csv`](data/gmt-offsets.csv) |
| **Use it in an EA** | [MQL5](mql5/SymbolMap.mqh) · [MQL4](mql4/SymbolMap.mqh) · [Python](python/symbol_map.py) |
| **Licence** | Data [CC BY 4.0](LICENSE) · code [MIT](LICENSE-CODE) |
| **Live/current version** | [metatrader-vps.com/broker-data/tools/symbol-map/](https://metatrader-vps.com/broker-data/tools/symbol-map/) |

---

## What is gold called in MetaTrader?

It depends entirely on the broker. Across the 230 brokers here that quote it, gold appears under **44 different symbol strings**. `XAUUSD` is the most common, on 68% of them — leaving roughly **one broker in three** using something else — and **31 of the 44 variants are used by exactly one broker**. There is no rule to infer; it is a lookup or nothing.

## Which instruments are worst?

Indices, by a wide margin. For the S&P 500 there is no majority spelling at all:

| Instrument | Brokers quoting it | Distinct symbol strings | Most common form | Share using it |
|---|---|---|---|---|
| S&P 500 | 178 | **56** | `US500` | 25% |
| DAX 40 | 149 | **57** | `GER40` | 19% |
| Dow Jones 30 | 165 | **60** | `US30` | 45% |
| Nasdaq 100 | 144 | **47** | `NAS100` | 33% |
| WTI crude | 154 | **45** | `XTIUSD` | 21% |
| Gold | 230 | **44** | `XAUUSD` | 68% |
| Silver | 221 | **45** | `XAGUSD` | 68% |
| EUR/USD | 235 | **30** | `EURUSD` | 87% |
| Bitcoin | 123 | **9** | `BTCUSD` | 86% |

If your EA trades indices and you hard-coded the symbol, it is broken on roughly 4 brokers out of 5.

## Why does my EA say "symbol not found"?

Because the symbol string your EA asks for does not exist in that broker's Market Watch. MetaTrader symbol names are case-sensitive and are not fuzzy-matched — `XAUUSD` will not resolve to `XAUUSD.m`. Brokers add suffixes to distinguish account types (`.m` micro, `.pro`, `.ecn`, `.raw`), to mark instrument families, or for legacy reasons no longer documented anywhere.

Resolve the symbol at runtime instead of hard-coding it:

```mql5
#include "SymbolMap.mqh"

string gold = ResolveSymbol("XAUUSD");   // -> "XAUUSD.m" on this broker
if(gold == "") { Print("this broker does not offer gold"); return; }
```

## What GMT offset does my broker use?

Also measured, in [`data/gmt-offsets.csv`](data/gmt-offsets.csv), for 240 brokers. **72% run UTC+3**, but 10 different offsets are in use, from UTC−4 to UTC+8:

| Offset | Brokers |
|---|---|
| UTC+3 | 172 |
| UTC+2 | 25 |
| UTC+0 | 18 |
| UTC+1 | 16 |
| UTC+8 | 3 |
| UTC+4 | 2 |
| UTC−4, UTC−3, UTC+5, UTC+7 | 1 each |

This matters more than it looks. A backtest run on the wrong offset shifts every session boundary, which quietly invalidates any strategy keyed to the London or New York open — and it fails silently, producing plausible-looking results.

## Why does my EA get error 131 (invalid volume)?

Because the minimum lot is not 0.01 everywhere. Of the brokers here quoting EUR/USD, **51 have a minimum above 0.01** — mostly 0.1, a handful 1.0. Normalise against both the minimum *and* the step before every `OrderSend`:

```mql5
double lots = NormalizeLots("XAUUSD", desired);   // clamps to min and snaps to step
```

`minLot`, `lotStep`, `digits` and `contractSize` are included per broker per symbol where the server reported them.

---

## Install

**MQL4 / MQL5** — copy the include into your project and generate the map for your broker:

```mql5
#include "SymbolMap.mqh"

int OnInit() {
   string eurusd = ResolveSymbol("EURUSD");
   string gold   = ResolveSymbol("XAUUSD");
   Print("trading ", eurusd, " and ", gold);
   return INIT_SUCCEEDED;
}
```

`SymbolMap.mqh` resolves against the live terminal first (it tries the canonical name, then every known variant from this dataset, then a suffix scan of Market Watch), so it keeps working on a broker that is not in this file at all.

**Python**

```python
from symbol_map import SymbolMap

m = SymbolMap.load()                      # reads data/brokers.json
print(m.resolve("IC Markets", "XAUUSD"))  # -> 'XAUUSD'
print(m.resolve("Exness", "XAUUSD"))      # -> 'XAUUSDm'
print(m.variants("SP500"))                # every known spelling of the S&P 500
print(m.gmt_offset("Pepperstone"))        # -> 3.0
```

**Just the data** — [`data/symbols.csv`](data/symbols.csv) is a flat 13,771-row table:

```csv
broker_slug,broker,platform,servers,gmt_offset,canonical,symbol,digits,contract_size,min_lot,lot_step
exness-sc-ltd,Exness SC Ltd,MT5,Exness-MT5Trial17,3.0,XAUUSD,XAUUSDm,3,100,0.01,0.01
```

## How this was measured

Demo accounts were opened across several hundred MT4 and MT5 brokers. For each one, the symbol list, per-symbol configuration and server clock were read directly off the live trading server through the platform API, then normalised to a canonical instrument id. Nothing here is transcribed from a broker's website.

**Caveats, stated plainly:**

- **A snapshot, not a feed.** Brokers rename symbols, add account types and change server time. This file is accurate as of its last commit; the [live tool](https://metatrader-vps.com/broker-data/tools/symbol-map/) is regenerated on a schedule.
- **Measured on demo servers.** For symbol names, lot rules and server time these match live in every case checked, but a broker can configure a live group differently.
- **Symbols vary by account type.** A broker offering standard and raw accounts may expose `XAUUSD` on one and `XAUUSD.raw` on the other. Where a broker had multiple servers, the symbols listed come from the servers named in the `servers` column.
- **Only instruments quoted by 50+ brokers are included**, so the table stays a useful cross-broker lookup rather than a dump of one-off CFDs.

Found a wrong symbol for a broker you actually trade with? [Open an issue](../../issues/new) — that is the single most useful contribution here, and corrections are merged fast. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence and attribution

Data is **[CC BY 4.0](LICENSE)** — use it commercially, redistribute it, build products on it. The only requirement is attribution: credit *MetaTrader Broker Symbols* and link back to this repository or to <https://metatrader-vps.com/broker-data/>. Code is [MIT](LICENSE-CODE).

Cite it formally with the "Cite this repository" button, or see [CITATION.cff](CITATION.cff).

## Who maintains this

Built and maintained by [metatraderVPS](https://metatrader-vps.com), which sells MetaTrader VPS hosting — that is what funds the measurement. The data and tools are free and stay free. The wider measured database (spreads, swaps, execution configuration, stops levels across the same brokers) is at [metatrader-vps.com/broker-data/](https://metatrader-vps.com/broker-data/).

---

<sub>Keywords: metatrader symbol not found · mt4 mt5 broker symbol list · what is gold called in mt4 · XAUUSD vs GOLD · SymbolSelect returns false · broker gmt offset backtesting · error 131 invalid volume · error 130 invalid stops · mql4 mql5 symbol mapping · forex broker symbol suffix</sub>
