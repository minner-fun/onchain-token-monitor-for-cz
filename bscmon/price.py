# -*- coding: utf-8 -*-
"""Price / liquidity / volume from DexScreener (deepest pair)."""
import json
import urllib.request

from . import config

UA = "onchain-token-monitor-for-cz"


def market(token=None):
    token = token or config.CFG.token
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            pairs = (json.load(r) or {}).get("pairs") or []
    except Exception:
        return None
    pairs = [p for p in pairs if p.get("priceUsd")]
    if not pairs:
        return None
    best = max(pairs, key=lambda p: (p.get("liquidity") or {}).get("usd", 0) or 0)
    return {
        "price": float(best["priceUsd"]),
        "liq": (best.get("liquidity") or {}).get("usd") or 0,
        "vol24h": (best.get("volume") or {}).get("h24") or 0,
        "fdv": best.get("fdv"),
    }


def bnb_usd():
    """Current BNB price in USD (Binance ticker, keyless). None on failure."""
    try:
        req = urllib.request.Request(
            "https://api.binance.com/api/v3/ticker/price?symbol=BNBUSDT",
            headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            return float((json.load(r) or {}).get("price"))
    except Exception:
        return None
