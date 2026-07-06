# -*- coding: utf-8 -*-
"""Events -> SQLite + console + Telegram."""
import time
import datetime as dt
import json
import urllib.request

from . import config, db

SEV_ICON = {"critical": "🔴🔴", "warn": "🟠", "info": "🟡", "ok": "🟢"}


def send_telegram(chat_id, text):
    """Send one message to one chat."""
    if not config.TELEGRAM_BOT_TOKEN:
        return
    try:
        body = json.dumps({"chat_id": chat_id, "text": text,
                           "disable_web_page_preview": True}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
            data=body, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        print(f"  (Telegram push to {chat_id} failed: {e})", flush=True)


def _broadcast(text):
    """Push to the primary chat + every /start subscriber (deduped)."""
    targets = set()
    if config.TELEGRAM_CHAT_ID:
        targets.add(str(config.TELEGRAM_CHAT_ID))
    try:
        targets.update(str(c) for c in db.all_subscribers())
    except Exception:
        pass
    for c in targets:
        send_telegram(c, text)
        time.sleep(0.05)


def emit_event(type_, severity, title, detail="", addr=None, tx=None, push=True):
    ts = int(time.time())
    db.insert_event(ts, type_, severity, addr, title, detail, tx)
    lines = [f"{SEV_ICON.get(severity, '')} {title}"]
    if detail:
        lines.append(detail)
    if tx:
        lines.append(f"https://bscscan.com/tx/{tx}")
    msg = "\n".join(lines)
    print(f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)
    if push:
        _broadcast(msg)


def log(msg):
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)
