# -*- coding: utf-8 -*-
"""CZ monitor daemon. Runs market / balance / transfer jobs on intervals,
writes SQLite, pushes Telegram on critical (cold wallet) / warn (deployer).

Usage (from the repo root):
  python -m bscmon.run           # long-running
  python -m bscmon.run --once    # run each job once, then exit (self-test)
"""
import sys
import time
import argparse
import threading

from . import config, db
from .notify import log
from . import jobs
from . import telegram


def _loop(name, fn, interval):
    while True:
        try:
            fn()
        except Exception as e:
            log(f"[{name}] error: {e}")
        time.sleep(interval)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="run each job once, then exit")
    args = ap.parse_args()

    db.init()
    iv = config.CFG.intervals
    specs = [
        ("market",   jobs.job_market,   iv.get("market", 60)),
        ("balance",  jobs.job_balance,  iv.get("balance", 180)),
        ("transfer", jobs.job_transfers, iv.get("transfer", 60)),
        ("funder",   jobs.job_funder,   iv.get("funder", 300)),
    ]

    if args.once:
        log("=== self-test: run each job once ===")
        jobs.job_market()
        jobs.job_balance()
        jobs.job_transfers(baseline=True)
        jobs.job_funder()
        log(f"=== done, data in {config.DB_PATH} ===")
        return

    tg = "on" if (config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID) else "off"
    log("=" * 56)
    log(f" CZ monitor started | token {config.CFG.token}")
    log(f" watching {len(config.CFG.watchlist)} wallets | Telegram: {tg}")
    log("=" * 56)

    jobs.job_transfers(baseline=True)      # set block baselines silently
    threading.Thread(target=telegram.poll_loop, name="tg", daemon=True).start()  # /start subscriptions
    threads = []
    for name, fn, interval in specs:
        t = threading.Thread(target=_loop, args=(name, fn, interval), name=name, daemon=True)
        t.start(); threads.append(t)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        log("Stopped.")


if __name__ == "__main__":
    main()
