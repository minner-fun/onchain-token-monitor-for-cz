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
    "实时面板:https://cz.minner.fun/"
)


def _api(method, params, timeout=40):
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/{method}"
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=timeout) as r:
        return json.load(r)


def poll_loop():
    """Long-poll for updates; subscribe on /start. Runs as a daemon thread."""
    if not config.TELEGRAM_BOT_TOKEN:
        log("telegram: no bot token, subscription poller disabled")
        return
    offset = int(db.get_cursor("tg_offset") or 0)
    log("telegram: subscription poller started")
    while True:
        try:
            res = _api("getUpdates", {"offset": offset, "timeout": 25})
            for u in res.get("result", []):
                offset = u["update_id"] + 1
                msg = u.get("message") or u.get("my_chat_member") or {}
                chat = (msg.get("chat") or {}).get("id")
                text = (msg.get("text") or "")
                if chat and text.startswith("/start"):
                    new = db.add_subscriber(chat)
                    send_telegram(chat, WELCOME)
                    if new:
                        log(f"telegram: new subscriber {chat}")
            db.set_cursor("tg_offset", offset)
        except Exception as e:
            log(f"telegram updates: {e}")
            time.sleep(5)
