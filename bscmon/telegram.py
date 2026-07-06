# -*- coding: utf-8 -*-
"""Telegram bot updates: long-poll getUpdates, handle /start (subscribe + welcome).

Anyone who /starts the bot (e.g. via the QR / t.me link) is recorded as a subscriber
and thereafter receives the same alerts the owner gets (see notify._broadcast)."""
import json
import time
import urllib.parse
import urllib.request

from . import config, db
from .notify import send_telegram, log

WELCOME = (
    "🔪 已订阅 CZ 「The Final Form Bull」监控。\n"
    "那 7 亿冷钱包(0x28816c4c…,占总量 70%)一旦异动,我会第一时间在这里推你 🔴。\n"
    "发 /status 随时查现状 · 实时面板 https://cz.minner.fun/"
)


def _api(method, params, timeout=40):
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/{method}"
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=timeout) as r:
        return json.load(r)


def _status_text():
    """A live-ish snapshot from the latest collected data: price + the cold wallet."""
    cfg = config.CFG
    m = db.last_market()
    price = m["price"] if m else 0
    lines = ["📊 CZ「The Final Form Bull」现状"]
    if m:
        fdv = price * cfg.total_supply / 1e6
        washy = "量在刷" if (m["ratio"] or 0) >= 5 else "正常"
        lines.append(f"价格 ${price:.4f} · FDV ${fdv:,.1f}M")
        lines.append(f"流动性 ${(m['liq'] or 0)/1e6:.2f}M · 24h量 ${(m['vol24h'] or 0)/1e6:.1f}M(换手 {(m['ratio'] or 0):.0f}×,{washy})")
    bunker = next((w for w in cfg.watchlist if w.get("role") == "bunker"), None)
    if bunker:
        bal = db.last_balance(bunker["addr"].lower()) or 0
        pct = bal / cfg.total_supply * 100 if cfg.total_supply else 0
        base = bunker.get("baseline")
        moved = base is not None and bal < base - 1_000_000
        status = "🔴 已异动!铡刀开始动 —— 顶级离场信号" if moved else "✅ 静默,一枚未动"
        usd = f",≈${bal*price/1e6:.1f}M" if price else ""
        lines.append(f"🔪 冷钱包 {bal:,.0f} CZ({pct:.1f}%{usd})· {status}")
    lines.append("面板 https://cz.minner.fun/")
    return "\n".join(lines)


def poll_loop():
    """Long-poll for updates; subscribe on /start. Runs as a daemon thread."""
    if not config.TELEGRAM_BOT_TOKEN:
        log("telegram: no bot token, subscription poller disabled")
        return
    offset = int(db.get_cursor("tg_offset") or 0)
    try:
        _api("setMyCommands", {"commands": json.dumps([
            {"command": "status", "description": "查看冷钱包 + 价格现状"},
            {"command": "start", "description": "订阅铡刀异动告警"},
        ])})
    except Exception:
        pass
    log("telegram: subscription poller started")
    while True:
        try:
            res = _api("getUpdates", {"offset": offset, "timeout": 25})
            for u in res.get("result", []):
                offset = u["update_id"] + 1
                msg = u.get("message") or u.get("my_chat_member") or {}
                chat = (msg.get("chat") or {}).get("id")
                text = (msg.get("text") or "")
                if not chat:
                    continue
                if text.startswith("/start"):
                    new = db.add_subscriber(chat)
                    send_telegram(chat, WELCOME)
                    if new:
                        log(f"telegram: new subscriber {chat}")
                elif text.startswith("/status"):
                    send_telegram(chat, _status_text())
            db.set_cursor("tg_offset", offset)
        except Exception as e:
            log(f"telegram updates: {e}")
            time.sleep(5)
