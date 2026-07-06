# -*- coding: utf-8 -*-
"""Token-factory scanner — CZ operation (and any BSC deployer).

Default (no API key): check the LIVE status of the 42 tokens we traced on-chain to
the CZ factory (deployer 0x1bff8f0a…). Shows how many are already dead — the body count.

  python factory.py

Dynamic mode (any deployer, needs a free BscScan/Etherscan V2 key in BSCSCAN_API_KEY):
enumerate the tokens a deployer created, then show their status.

  BSCSCAN_API_KEY=... python factory.py --deployer 0x1bff8f0ade179dfa1beddb54fa5d7d6dc814191a
"""
import argparse
import json
import os
import sys
import time
import urllib.request

UA = "onchain-token-monitor-for-cz"
DEPLOYER = "0x1bff8f0ade179dfa1beddb54fa5d7d6dc814191a"
DEAD_LIQ_USD = 5000   # below this (or no pool) = effectively dead

# 42 tokens traced on-chain to the CZ factory (Dune: erc20_bnb.evt_transfer mints by the
# deployer, 2026-07-01 .. 07-06). Format: (first_mint_date, address). CZ is 2026-07-03.
FACTORY_TOKENS = [
    ("2026-07-01", "0xd57807139db6fcd24749f540aa4c82d43e404444"),
    ("2026-07-02", "0xf735b2f40d3c0a338eaf1123d7b27b02d00e4444"),
    ("2026-07-03", "0x7a848a5a8169aa6a2f603d056a749f924f504444"),  # CZ
    ("2026-07-04", "0x5ff44be4d5a69b849eea599b1548227a0c4f4444"),
    ("2026-07-04", "0x946b2165d92c3723541be9a438940e6594044444"),
    ("2026-07-04", "0x9a416f99c81a806528305e32dec1668f3e364444"),
    ("2026-07-04", "0x8fb310320b248617b53ae829c88628aea8e64444"),
    ("2026-07-04", "0x4ce634563bb2f72961483357dc31b4c146a24444"),
    ("2026-07-04", "0x73eb7f35500e2243ec2ede317f50d982e80c4444"),
    ("2026-07-04", "0x585ec51ae50aef76b1c4ad12e851470ebeeeffff"),
    ("2026-07-05", "0x7401e2d9c413e9661b19b4dac44dc551f7bd4444"),
    ("2026-07-05", "0x8c8b2c69d36629b4b1f9ca7aa7a392f3022a4444"),
    ("2026-07-05", "0xc29ad095f5afa6798269c31438a74b7a66d44444"),
    ("2026-07-05", "0xe10e4913206eff535214e480ee7530d70b064444"),
    ("2026-07-05", "0xaa5cfe8e2da2e3ce24b5a4e0ba27496012514444"),
    ("2026-07-05", "0x095507200edecd93f57d5a41580d004f55164444"),
    ("2026-07-05", "0x1bb502990974ef8dcd574fd11b98fda307564444"),
    ("2026-07-05", "0xe8607964dc05943af0c6827ce867207cd4364444"),
    ("2026-07-05", "0x8ca4944044545b388841227488dfea3630b84444"),
    ("2026-07-05", "0x0a10924b975b23b1eb33a7b9c72b67c7ddf64444"),
    ("2026-07-05", "0x46a5b49bfb6e922f44bc762e9df5d910a07c4444"),
    ("2026-07-05", "0xafcbc8dc616d6c94118e62c8f3fe8d774f354444"),
    ("2026-07-05", "0x4a8085a3a90d5b943f6290794ef13969293c4444"),
    ("2026-07-05", "0x0411f39fd168f6f9e6fcc58db8d8dd9ce2da4444"),
    ("2026-07-05", "0x60dd0591f933f5a3db518d457a4c12fd1cd84444"),
    ("2026-07-05", "0x6c9a85886929cda4700d252c8e01d5bcae3b4444"),
    ("2026-07-05", "0x4c5155625ccf0c8d81a216210194b4c629874444"),
    ("2026-07-05", "0x1706f1e06c69f3a8cf33cce179d5d78a5c6f4444"),
    ("2026-07-05", "0x41ea09866296bcda337cef78962e9943fa967777"),
    ("2026-07-05", "0x3cc993c95ebdb43b56e39b90960ccab24c2dffff"),
    ("2026-07-05", "0xff06b5cb8769e29c81fbe7b69265f5bad49b4444"),
    ("2026-07-06", "0x4ac2111895cc725f15e1dca542273eccf7f64444"),
    ("2026-07-06", "0x590b603334096a90ebfcfb7839ec1907e5904444"),
    ("2026-07-06", "0x0bca38bcbbf2bbda85f5eeee1602af591e774444"),
    ("2026-07-06", "0x4082691b55414476aac4d9aad69847743d2f4444"),
    ("2026-07-06", "0x29eff22806c4766841d12fd20e6151d40f784444"),
    ("2026-07-06", "0x1dd2362b4c1cad1be50dc82f264128e5f7104444"),
    ("2026-07-06", "0xb2fd11723a73a0409a342cffd9b97f2fbfff4444"),
    ("2026-07-06", "0x61396fd3db231f5f1b1c02ffcdc1f107b2b94444"),
    ("2026-07-06", "0x4047aa3a6bfc97619f71bbd3a111b46e4d864444"),
    ("2026-07-06", "0x0f2eccd7e99cbe6d5c1e9451a5f6ec93bcdf4444"),
    ("2026-07-06", "0xfb1dc96c9832a55aa1b9e808df9e2f3345ec4444"),
]


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def dexscreener(token):
    try:
        pairs = (_get(f"https://api.dexscreener.com/latest/dex/tokens/{token}") or {}).get("pairs") or []
    except Exception:
        return None
    pairs = [p for p in pairs if p.get("priceUsd")]
    if not pairs:
        return None
    best = max(pairs, key=lambda p: (p.get("liquidity") or {}).get("usd", 0) or 0)
    return {
        "symbol": best["baseToken"].get("symbol", "?"),
        "price": float(best["priceUsd"]),
        "liq": (best.get("liquidity") or {}).get("usd") or 0,
        "vol24h": (best.get("volume") or {}).get("h24") or 0,
    }


def scan(tokens):
    print(f"\nScanning {len(tokens)} tokens from factory {DEPLOYER} …\n")
    print(f"{'#':>3}  {'launched':<10} {'symbol':<10} {'liquidity':>12} {'24h vol':>12}  status  address")
    alive = 0
    rows = []
    for i, (date, addr) in enumerate(tokens, 1):
        m = dexscreener(addr)
        dead = (m is None) or (m["liq"] < DEAD_LIQ_USD)
        if not dead:
            alive += 1
        rows.append((i, date, addr, m, dead))
        time.sleep(0.12)  # be polite to the API
    # print sorted: alive first (by liq desc), then dead
    rows.sort(key=lambda r: (r[4], -( (r[3] or {}).get("liq", 0) )))
    for i, date, addr, m, dead in rows:
        tag = "💀 DEAD" if dead else "✅ alive"
        sym = (m or {}).get("symbol", "—")[:10]
        liq = f"${(m or {}).get('liq', 0):,.0f}" if m else "—"
        vol = f"${(m or {}).get('vol24h', 0):,.0f}" if m else "—"
        star = " ← CZ" if addr.lower() == "0x7a848a5a8169aa6a2f603d056a749f924f504444" else ""
        print(f"{i:>3}  {date:<10} {sym:<10} {liq:>12} {vol:>12}  {tag}  {addr}{star}")
    dead_n = len(tokens) - alive
    print(f"\nBody count: {dead_n}/{len(tokens)} already dead (liq < ${DEAD_LIQ_USD:,}), {alive} still trading.")
    print("Every one is the same template: 1B supply, ~70% parked in a cold wallet, wash-pumped, then left to rot.")


def enumerate_deployer(deployer):
    """Dynamic: list tokens a deployer created, via BscScan/Etherscan V2 (needs a key).
    Returns [(date, addr)] or None if no key / unavailable."""
    key = os.environ.get("BSCSCAN_API_KEY")
    if not key:
        print("Dynamic mode needs a free BscScan/Etherscan V2 API key:\n"
              "  BSCSCAN_API_KEY=yourkey python factory.py --deployer " + deployer + "\n"
              "Get one at https://etherscan.io/apis (works for BSC via chainid=56).\n"
              "Without a key, run `python factory.py` to scan the bundled CZ-factory list.")
        return None
    base = "https://api.etherscan.io/v2/api?chainid=56&module=account"
    found = {}
    # (a) direct CREATE txs: to is empty, contractAddress is the new token
    try:
        txs = _get(f"{base}&action=txlist&address={deployer}&startblock=0&endblock=latest&sort=asc&apikey={key}")
        for t in (txs.get("result") or []):
            if (not t.get("to")) and t.get("contractAddress"):
                found[t["contractAddress"].lower()] = t.get("timeStamp")
    except Exception as e:
        print(f"  txlist error: {e}")
    # (b) factory/CREATE2 txs: internal 'create' traces
    try:
        itx = _get(f"{base}&action=txlistinternal&address={deployer}&startblock=0&endblock=latest&sort=asc&apikey={key}")
        for t in (itx.get("result") or []):
            if t.get("type", "").startswith("create") and t.get("contractAddress"):
                found[t["contractAddress"].lower()] = t.get("timeStamp")
    except Exception as e:
        print(f"  txlistinternal error: {e}")
    out = []
    for addr, ts in found.items():
        try:
            import datetime as _dt
            d = _dt.datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d") if ts else "?"
        except Exception:
            d = "?"
        out.append((d, addr))
    out.sort()
    print(f"Enumerated {len(out)} contracts created by {deployer}.")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deployer", help="enumerate this deployer's tokens (needs BSCSCAN_API_KEY)")
    args = ap.parse_args()
    if args.deployer:
        tokens = enumerate_deployer(args.deployer)
        if not tokens:
            return
    else:
        tokens = FACTORY_TOKENS
    scan(tokens)


if __name__ == "__main__":
    main()
