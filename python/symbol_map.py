"""Resolve a canonical instrument name to a specific broker's MetaTrader symbol.

MetaTrader symbol names are case-sensitive and never fuzzy-matched, so an EA or
bot that hard-codes "XAUUSD" fails outright on a broker quoting "XAUUSD.m".
This module is a lookup over symbol names read from 221 live MT4/MT5 servers.

    from symbol_map import SymbolMap

    m = SymbolMap.load()
    m.resolve("Exness SC Ltd", "XAUUSD")   # -> 'XAUUSDm'
    m.variants("SP500")                    # every known spelling
    m.gmt_offset("IC Markets")             # -> 3.0

github.com/metatraderVPS/metatrader-broker-symbols · data CC BY 4.0, code MIT
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

_DATA = Path(__file__).resolve().parent.parent / "data"


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


@dataclass(frozen=True)
class Broker:
    slug: str
    name: str
    platform: str
    servers: tuple[str, ...]
    gmt_offset: float | None
    symbols: dict[str, dict]
    aliases: tuple[str, ...] = ()


class SymbolMap:
    """Broker -> canonical instrument -> that broker's real symbol."""

    def __init__(self, brokers: dict[str, Broker], variants: dict[str, list[str]]):
        self._brokers = brokers
        self._variants = variants
        # brokers are looked up by fuzzy name in practice ("Exness" for
        # "Exness SC Ltd"), so index every slug prefix once up front
        self._by_name = {b.slug: b for b in brokers.values()}

    @classmethod
    def load(cls, data_dir: Path | str | None = None) -> "SymbolMap":
        d = Path(data_dir) if data_dir else _DATA
        raw = json.loads((d / "brokers.json").read_text(encoding="utf-8"))
        variants = json.loads((d / "variants.json").read_text(encoding="utf-8"))
        brokers = {
            slug: Broker(
                slug=slug,
                name=v["name"],
                platform=v.get("platform", ""),
                servers=tuple(v.get("servers", ())),
                gmt_offset=v.get("gmtOffset"),
                symbols=v.get("symbols", {}),
                aliases=tuple(v.get("aliases", ())),
            )
            for slug, v in raw.items()
        }
        return cls(brokers, variants)

    # -- lookup ---------------------------------------------------------
    def find(self, name: str) -> list[Broker]:
        """Every broker matching a partial name, best match first.

        Matching is on whole slug TOKENS, never raw substrings: a substring
        search for "XM" happily matches "CXM Group", which is exactly the kind
        of silent wrong answer this library exists to prevent."""
        q = [t for t in _slug(name).split("-") if t]
        if not q:
            return []
        exact = self._by_name.get("-".join(q))
        if exact:
            return [exact]
        # brand names and server prefixes ("exness", "icmarkets") rarely match
        # the legal entity a broker registers its servers under
        for b in self._brokers.values():
            if any(_slug(a) == "-".join(q) for a in b.aliases):
                return [b]
        starts, contains = [], []
        for b in self._brokers.values():
            toks = b.slug.split("-")
            if toks[: len(q)] == q:
                starts.append(b)
            elif any(toks[i : i + len(q)] == q for i in range(1, len(toks))):
                contains.append(b)
        return starts + contains

    def broker(self, name: str) -> Broker | None:
        """The single broker matching this name, or None.

        Returns None when the name is ambiguous rather than guessing - use
        find() to see the candidates and pick one."""
        m = self.find(name)
        return m[0] if len(m) == 1 else None

    def resolve(self, broker: str, canonical: str) -> str | None:
        """This broker's symbol for the instrument, or None if not offered."""
        b = self.broker(broker)
        if not b:
            return None
        entry = b.symbols.get(canonical.upper())
        return entry["symbol"] if entry else None

    def spec(self, broker: str, canonical: str) -> dict | None:
        """digits / contractSize / minLot / lotStep, where the server reported them."""
        b = self.broker(broker)
        return b.symbols.get(canonical.upper()) if b else None

    def normalize_lots(self, broker: str, canonical: str, desired: float) -> float | None:
        """Clamp to the broker's minimum and snap to its step.

        Not doing this is the usual cause of error 131 (invalid trade volume):
        42 of the brokers here have a 0.1 minimum on EUR/USD, not 0.01."""
        sp = self.spec(broker, canonical)
        if not sp:
            return None
        step = float(sp.get("lotStep") or 0.01) or 0.01
        mn = float(sp.get("minLot") or step)
        v = int(desired / step + 1e-9) * step
        return round(max(v, mn), 8)

    def variants(self, canonical: str) -> list[str]:
        """Every spelling of this instrument seen across all measured brokers."""
        return list(self._variants.get(canonical.upper(), []))

    def gmt_offset(self, broker: str) -> float | None:
        b = self.broker(broker)
        return b.gmt_offset if b else None

    # -- iteration ------------------------------------------------------
    @property
    def brokers(self) -> Iterable[Broker]:
        return self._brokers.values()

    @property
    def instruments(self) -> list[str]:
        return sorted(self._variants)

    def __len__(self) -> int:
        return len(self._brokers)


if __name__ == "__main__":
    m = SymbolMap.load()
    print(f"{len(m)} brokers, {len(m.instruments)} instruments")
    for name in ("XM", "IC Markets", "Vantage", "Tickmill"):
        hits = m.find(name)
        if not hits:
            print(f"  {name:14} no broker matched")
            continue
        for b in hits[:2]:
            gold = m.resolve(b.name, "XAUUSD") or "-"
            off = f"UTC{b.gmt_offset:+g}" if b.gmt_offset is not None else "UTC?"
            print(f"  {name:14} -> {b.name:38} gold={gold:12} {off}")
    print(f"\n  SP500 has {len(m.variants('SP500'))} known spellings")
    print(f"  0.007 lots on a 0.01-step broker -> {m.normalize_lots('XM', 'XAUUSD', 0.007)}")
