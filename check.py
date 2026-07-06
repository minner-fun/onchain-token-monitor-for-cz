# -*- coding: utf-8 -*-
"""Live on-chain check for the CZ token on BSC.

Reads config.yaml, then for each watched wallet queries its live token balance
straight from a BSC RPC node (balanceOf), and pulls price/liquidity/volume from
DexScreener. Prints a status board and flags the two things that matter:
  - has the 70% "cold wallet" (guillotine) moved?
  - is 24h volume absurd relative to liquidity (inflated / wash volume)?

No API key needed. Usage:
  python check.py
"""
import json
import sys
import urllib.request

try:
    import yaml
except ImportError:
    sys.exit("pip install pyyaml requests")

DEFAULT_RPC = "https://bsc-dataseed.binance.org"
BALANCEOF_SELECTOR = "0x70a08231"   # balanceOf(address)
UA = "Mozilla/5.0 (onchain-token-monitor-for-cz)"


def _rpc(rpc_url, method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(rpc_url, data=body,
                                 headers={"Content-Type": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r).get("result")


def balance_of(rpc_url, token, holder, decimals):
    data = BALANCEOF_SELECTOR + holder.lower().replace("0x", "").rjust(64, "0")
    res = _rpc(rpc_url, "eth_call", [{"to": token, "data": data}, "latest"])
    return int(res, 16) / (10 ** decimals) if res and res != "0x" else 0.0


def dexscreener(token):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        pairs = (json.load(r) or {}).get("pairs") or []
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


def main():
    with open("config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    a = cfg["asset"]
    rpc = cfg.get("rpc") or DEFAULT_RPC
    token, dec, supply = a["token"], a.get("decimals", 18), a["total_supply"]

    print(f"\n=== {a['symbol']} ({a['name']}) · BSC ===")
    print(f"token {token}")

    m = dexscreener(token)
    if m:
        ratio = (m["vol24h"] / m["liq"]) if m["liq"] else 0
        print(f"price ${m['price']:.6f} | liq ${m['liq']:,.0f} | vol24h ${m['vol24h']:,.0f} | FDV ${m['fdv']:,.0f}" if m["fdv"]
              else f"price ${m['price']:.6f} | liq ${m['liq']:,.0f} | vol24h ${m['vol24h']:,.0f}")
        thr = cfg.get("signals", {}).get("wash_vol_liq_ratio", 5.0)
        flag = "  <-- INFLATED: volume can't be organic at this ratio" if ratio >= thr else ""
        print(f"vol/liq turnover: {ratio:.1f}x{flag}")

    print("\nwatched wallets (live balanceOf):")
    for w in cfg.get("watchlist", []):
        bal = balance_of(rpc, token, w["addr"], dec)
        pct = bal / supply * 100
        line = f"  {w['label']:<28} {bal:>16,.0f}  ({pct:5.2f}%)  {w['addr']}"
        base = w.get("baseline")
        role = w.get("role")
        if role == "bunker" and base is not None:
            drop = base - bal
            if drop > cfg.get("signals", {}).get("cold_wallet_drop", 1_000_000):
                line += f"\n     🔴 GUILLOTINE MOVED: down {drop:,.0f} from baseline {base:,.0f} — TOP EXIT SIGNAL"
            else:
                line += "\n     ✅ still dormant (guillotine intact)"
        elif role == "deployer":
            line += "\n     (distributed its 74% genesis allocation: 70% to the cold wallet, rest sold into the pool)"
        elif role in ("wash", "support"):
            line += "\n     (DEX trader — churns through the pool, holds ~0 by design; watched for trading activity, not balance)"
        print(line)
    print()


if __name__ == "__main__":
    main()
