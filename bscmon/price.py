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


def _get_json(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def new_pools():
    """Recently created BSC pools (GeckoTerminal, keyless). Returns [{token, name}]."""
    try:
        d = _get_json("https://api.geckoterminal.com/api/v2/networks/bsc/new_pools?page=1")
    except Exception:
        return []
    out = []
    for p in (d.get("data") or []):
        base = ((((p.get("relationships") or {}).get("base_token") or {}).get("data") or {})
                .get("id") or "").replace("bsc_", "").lower()
        if base:
            out.append({"token": base, "name": (p.get("attributes") or {}).get("name", "")})
    return out


def token_creator(token):
    """The deployer/creator address of a token (GoPlus, keyless). None on failure."""
    try:
        r = _get_json(f"https://api.gopluslabs.io/api/v1/token_security/56?contract_addresses={token}")
        res = r.get("result") or {}
        info = res.get(token.lower()) or (next(iter(res.values())) if res else {})
        return (info.get("creator_address") or "").lower() or None
    except Exception:
        return None
