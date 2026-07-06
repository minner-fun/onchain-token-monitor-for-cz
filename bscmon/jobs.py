# -*- coding: utf-8 -*-
"""Monitoring jobs for the CZ token. Three signals:
  - market:    price / liquidity / 24h-volume, wash ratio (record-only, no push)
  - balance:   watchlist balances; the 70% cold wallet dropping = CRITICAL
  - transfers: name the destination of any cold-wallet / deployer outflow
"""
import time

from . import config, db, evm, price
from .notify import emit_event, log

CFG = config.CFG
_LOGS_CHUNK = 45     # tiny ranges so even strict public nodes accept eth_getLogs (daemon scans small deltas)
_LOGS_WARNED = False  # log the "getLogs unavailable" degradation once, not every cycle


def job_market():
    m = price.market()
    if not m:
        log("market: fetch failed"); return
    ratio = (m["vol24h"] / m["liq"]) if m["liq"] else 0
    db.insert_market(int(time.time()), m["price"], m["liq"], m["vol24h"], ratio)
    thr = CFG.signals.get("wash_vol_liq_ratio", 5.0)
    # record-only info on crossing into "inflated" territory (no Telegram spam)
    was = db.get_cursor("wash_state")
    now = "inflated" if ratio >= thr else "normal"
    if now != was:
        db.set_cursor("wash_state", now)
        if now == "inflated":
            emit_event("wash_volume", "info",
                       f"Volume looks inflated: 24h vol ${m['vol24h']:,.0f} on ${m['liq']:,.0f} liquidity",
                       detail=f"turnover {ratio:.1f}x — likely wash/MM, not organic demand", push=False)
    log(f"market: ${m['price']:.6f} | liq ${m['liq']:,.0f} | vol24h ${m['vol24h']:,.0f} | {ratio:.1f}x")


def job_balance():
    ts = int(time.time())
    for w in CFG.watchlist:
        addr = w["addr"].lower()
        try:
            bal = evm.balance_of(addr)
        except Exception as e:
            log(f"balance {addr[:10]}…: {e}"); continue
        prev = db.last_balance(addr)
        db.insert_balance(addr, ts, bal)
        role, lbl = w.get("role"), w.get("label", addr)
        if prev is not None and bal < prev - 1:                      # a new outflow this cycle
            drop = prev - bal
            if role == "bunker":
                emit_event("guillotine_move", "critical",
                           f"🔴 COLD WALLET MOVED: {lbl} down {drop:,.0f} CZ",
                           detail=f"{prev:,.0f} → {bal:,.0f}. The 70% guillotine is no longer dormant — TOP EXIT SIGNAL.",
                           addr=addr)
            elif role == "deployer":
                emit_event("deployer_out", "warn",
                           f"{lbl} balance down {drop:,.0f} CZ", detail=f"{prev:,.0f} → {bal:,.0f}", addr=addr)
    log("balance: snapshot done")


def _scan_out(addr, to_block):
    ckey = f"blk:{addr}"
    cur = db.get_cursor(ckey)
    if cur is None:                       # first run: set baseline, don't replay history
        db.set_cursor(ckey, to_block); return None
    frm = int(cur) + 1
    if frm > to_block:
        return []
    hits = []
    while frm <= to_block:
        end = min(frm + _LOGS_CHUNK, to_block)
        hits.extend(evm.outgoing_transfers(addr, frm, end))
        frm = end + 1
    db.set_cursor(ckey, to_block)
    return hits


def job_transfers(baseline=False):
    try:
        to_block = evm.block_number()
    except Exception as e:
        log(f"transfers: block_number failed: {e}"); return
    for w in CFG.addrs("bunker", "deployer"):
        addr, role, lbl = w["addr"].lower(), w.get("role"), w.get("label", w["addr"])
        try:
            hits = _scan_out(addr, to_block)
        except Exception as e:
            # getLogs unsupported/limited on this RPC — the balanceOf drop signal still covers
            # the critical "cold wallet moved" case; only destination-naming is lost here.
            global _LOGS_WARNED
            if not _LOGS_WARNED:
                log(f"transfers: eth_getLogs unavailable on this RPC ({str(e)[:50]}); "
                    f"set BSC_RPC to a logs-capable endpoint to name outflow destinations. "
                    f"Balance-drop (critical) alerts remain active. Silencing further getLogs notices.")
                _LOGS_WARNED = True
            return
        if hits is None:
            log(f"transfers: baseline set for {lbl}"); continue
        for h in hits:
            dest = CFG.label(h["to"])
            if role == "bunker":
                emit_event("guillotine_move", "critical",
                           f"🔴 COLD WALLET SENT {h['amount']:,.0f} CZ → {dest}",
                           detail="The 70% guillotine is moving — TOP EXIT SIGNAL.",
                           addr=addr, tx=h["tx"])
            else:
                sev = "warn"
                where = "into the pool (selling)" if h["to"].lower() == CFG.pool else f"→ {dest}"
                emit_event("deployer_out", sev,
                           f"Deployer sent {h['amount']:,.0f} CZ {where}", addr=addr, tx=h["tx"])
    log("transfers: scan done")
