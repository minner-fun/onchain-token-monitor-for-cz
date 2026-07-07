# -*- coding: utf-8 -*-
"""Monitoring jobs for the CZ token. Signals:
  - market:    price / liquidity / 24h-volume, wash ratio (record-only, no push)
  - balance:   watchlist balances; the 70% cold wallet dropping = CRITICAL
  - transfers: name the destination of any cold-wallet / deployer outflow
  - funder:    network early-warning — large BNB outflows from the Binance-funded paymaster (owner-only)
"""
import time

from . import config, db, evm, price
from .notify import emit_event, log, send_telegram

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


# ---------------------------------------------------------------- funder (network early-warning)
def job_funder():
    """Watch the Binance-funded paymaster (keyless). A LARGE BNB outflow = capital being
    deployed for a new pump (LP / market-making). Cheap each cycle (one balance check); only
    deep-scans blocks when the balance actually drops. Alerts the OWNER ONLY."""
    fw = CFG.funder_watch
    if not fw:
        return
    addr = fw["addr"].lower()
    min_bnb = float(fw.get("min_bnb", 50))
    label = fw.get("label", addr[:10] + "…")
    try:
        latest = evm.block_number()
        bal = evm.get_balance(addr)
    except Exception as e:
        log(f"funder: {e}")
        return
    prev_bal, last_blk = db.get_cursor("funder_bal"), db.get_cursor("funder_block")
    if prev_bal is None or last_blk is None:        # first run: baseline, don't replay history
        db.set_cursor("funder_bal", bal)
        db.set_cursor("funder_block", latest)
        log(f"funder: baseline set (bal {bal:,.0f} BNB, block {latest})")
        return
    drop = float(prev_bal) - bal
    # routine gas-funding drift is only ~6 BNB/cycle; a drop >= min_bnb means a real large
    # outflow (Binance inflows are infrequent, so masking is rare). Only then do the block-scan.
    if drop >= min_bnb:                              # a big move happened → scan to find it
        start = int(last_blk) + 1
        if latest - start > 300:                     # cap catch-up burst
            start = latest - 300
        try:
            hits = evm.large_outflows(addr, start, latest, min_bnb)
        except Exception as e:
            log(f"funder scan: {e}"); hits = []
        owner = config.TELEGRAM_CHAT_ID
        bnb_px = price.bnb_usd() if hits else None
        for h in hits:
            uv = (h["bnb"] * bnb_px) if bnb_px else 0
            usd = f"(≈ ${uv/1e4:,.0f} 万)" if uv >= 1e4 else (f"(≈ ${uv:,.0f})" if uv else "")
            title = f"💰 {label} 大额出账 {h['bnb']:,.1f} BNB {usd} → {h['to']}"
            detail = ("可能在给新盘铺 LP / 做市资金 —— 盯这个地址,它接下来很可能发 / 拉新币。\n"
                      f"https://bscscan.com/address/{h['to']}")
            db.insert_event(int(time.time()), "funder_out", "warn", h["to"], title, detail, h["tx"])
            log(title)
            if owner:
                send_telegram(owner, f"🟠 {title}\n{detail}\ntx https://bscscan.com/tx/{h['tx']}")
        log(f"funder: balance -{drop:,.0f} BNB → scanned {latest-start+1} blocks, {len(hits)} large outflow(s)")
    db.set_cursor("funder_bal", bal)
    db.set_cursor("funder_block", latest)


# ---------------------------------------------------------------- new pools (known-deployer launch watch)
def job_new_pools():
    """Watch for new tokens launched by a known network deployer (A-signal, keyless):
    poll GeckoTerminal new_pools; for each new token, confirm its creator via GoPlus;
    if the creator is in deployer_watch, alert the owner. First run baselines (no alerts)."""
    watch = CFG.deployer_watch
    if not watch:
        return
    pools = price.new_pools()
    if not pools:
        log("newpools: none / fetch failed"); return
    baselined = db.get_cursor("newpool_baselined") == "1"
    owner = config.TELEGRAM_CHAT_ID
    checked = 0
    for p in pools:
        tok = p["token"]
        if db.token_seen(tok):
            continue
        db.mark_token(tok)
        if not baselined:                    # first run: record only, don't check/alert
            continue
        if checked >= 15:                    # cap GoPlus lookups per cycle
            continue
        creator = price.token_creator(tok); checked += 1
        if creator and creator in watch:
            name = p.get("name", "") or tok
            title = f"🎯 已知发币地址又发新盘:{name}"
            detail = (f"deployer {creator} 属于我们盯的网络。新币 {tok}\n"
                      f"https://dexscreener.com/bsc/{tok}\n"
                      f"https://gopluslabs.io/token-security/56/{tok}")
            db.insert_event(int(time.time()), "new_pool", "warn", tok, title, detail)
            log(title)
            if owner:
                send_telegram(owner, f"🟠 {title}\n{detail}")
    if not baselined:
        db.set_cursor("newpool_baselined", "1")
        log(f"newpools: baseline set ({len(pools)} pools recorded)")
    else:
        log(f"newpools: checked {checked} new token(s)")
