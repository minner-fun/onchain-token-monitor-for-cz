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


def bscscan_txlist(address, api_key, start_block=0):
    """Normal transactions for an address via Etherscan V2 (chainid=56 = BSC).
    Returns a list of tx dicts (may be empty); raises on transport error."""
    url = ("https://api.etherscan.io/v2/api?chainid=56&module=account&action=txlist"
           f"&address={address}&startblock={start_block}&endblock=99999999"
           f"&sort=asc&apikey={api_key}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        out = json.load(r)
    res = out.get("result")
    return res if isinstance(res, list) else []


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
