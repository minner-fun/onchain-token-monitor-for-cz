# -*- coding: utf-8 -*-
"""Minimal BSC (EVM) JSON-RPC client: balances, block height, Transfer logs.
Raw eth_call / eth_getLogs over HTTP — no web3.py dependency."""
import json
import time
import urllib.request

from . import config

UA = "onchain-token-monitor-for-cz"
BALANCEOF = "0x70a08231"   # balanceOf(address)
# keccak256("Transfer(address,address,uint256)")
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def _rpc(method, params, tries=3):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    for i in range(tries):
        try:
            req = urllib.request.Request(config.BSC_RPC, data=body,
                                         headers={"Content-Type": "application/json", "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                out = json.load(r)
            if "error" in out:
                raise RuntimeError(out["error"])
            return out.get("result")
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1.0 * (i + 1))


def _topic_addr(addr):
    return "0x" + addr.lower().replace("0x", "").rjust(64, "0")


def get_balance(addr):
    """Native BNB balance of an address."""
    r = _rpc("eth_getBalance", [addr, "latest"])
    return int(r, 16) / 1e18 if r else 0.0


def large_outflows(addr, start_block, end_block, min_bnb):
    """Scan blocks (start_block..end_block] for native transfers FROM addr >= min_bnb BNB.
    Returns [{to, bnb, tx, block}]. Best-effort (skips blocks that error)."""
    addr = addr.lower()
    out = []
    for b in range(start_block, end_block + 1):
        try:
            blk = _rpc("eth_getBlockByNumber", [hex(b), True])
        except Exception:
            continue
        for t in (blk.get("transactions") if blk else []) or []:
            if (t.get("from") or "").lower() == addr and t.get("to"):
                bnb = int(t.get("value", "0x0"), 16) / 1e18
                if bnb >= min_bnb:
                    out.append({"to": t["to"], "bnb": bnb, "tx": t.get("hash"), "block": b})
    return out


def ankr_funded_recipients(funder, from_block, min_bnb=0.1, max_pages=5, page_size=100):
    """Addresses that received BNB (value >= min_bnb) from `funder` since from_block, via the
    Ankr Advanced API. Returns (recipients_set, latest_block_seen). Needs config.ANKR_URL."""
    if not config.ANKR_URL:
        return set(), from_block
    funder = funder.lower()
    recips, latest, page_token, pages = set(), from_block, None, 0
    while pages < max_pages:
        params = {"blockchain": "bsc", "address": [funder], "fromBlock": from_block,
                  "pageSize": page_size, "descOrder": False}
        if page_token:
            params["pageToken"] = page_token
        body = json.dumps({"jsonrpc": "2.0", "method": "ankr_getTransactionsByAddress",
                           "params": params, "id": 1}).encode()
        req = urllib.request.Request(config.ANKR_URL, data=body,
                                     headers={"Content-Type": "application/json", "User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            res = (json.load(r).get("result") or {})
        for t in res.get("transactions") or []:
            latest = max(latest, int(t.get("blockNumber", "0x0"), 16))
            if (t.get("from") or "").lower() == funder and t.get("to"):
                if int(t.get("value", "0x0"), 16) / 1e18 >= min_bnb:
                    recips.add(t["to"].lower())
        page_token = res.get("nextPageToken")
        pages += 1
        if not page_token:
            break
    return recips, latest


def block_number():
    return int(_rpc("eth_blockNumber", []), 16)


def balance_of(holder, token=None, decimals=None):
    token = token or config.CFG.token
    decimals = config.CFG.decimals if decimals is None else decimals
    data = BALANCEOF + holder.lower().replace("0x", "").rjust(64, "0")
    res = _rpc("eth_call", [{"to": token, "data": data}, "latest"])
    return int(res, 16) / (10 ** decimals) if res and res != "0x" else 0.0


def outgoing_transfers(from_addr, start_block, end_block, token=None, decimals=None):
    """Transfer logs where `from_addr` is the sender, in (start_block, end_block].
    Returns [{to, amount, tx, block}]."""
    token = token or config.CFG.token
    decimals = config.CFG.decimals if decimals is None else decimals
    logs = _rpc("eth_getLogs", [{
        "address": token,
        "fromBlock": hex(start_block), "toBlock": hex(end_block),
        "topics": [TRANSFER_TOPIC, _topic_addr(from_addr)],
    }]) or []
    out = []
    for lg in logs:
        topics = lg.get("topics", [])
        if len(topics) < 3:
            continue
        to = "0x" + topics[2][-40:]
        amount = int(lg.get("data", "0x0"), 16) / (10 ** decimals)
        out.append({"to": to, "amount": amount,
                    "tx": lg.get("transactionHash"), "block": int(lg.get("blockNumber", "0x0"), 16)})
    return out
