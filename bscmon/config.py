# -*- coding: utf-8 -*-
"""Config: loads config.yaml + environment (.env) for the CZ BSC monitor."""
import os
import sys
import yaml

for _s in ("stdout", "stderr"):           # UTF-8 on Windows consoles
    try:
        getattr(sys, _s).reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.environ.get("MONITOR_CONFIG", os.path.join(ROOT, "config.yaml"))
DEFAULT_RPC = "https://bsc-dataseed.binance.org"


def _load_env():
    path = os.path.join(ROOT, ".env")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


_load_env()

BSC_RPC            = os.environ.get("BSC_RPC") or DEFAULT_RPC
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")
BSCSCAN_API_KEY    = os.environ.get("BSCSCAN_API_KEY", "")   # for funder_watch (BscScan/Etherscan V2)
DB_PATH            = os.environ.get("MONITOR_DB", os.path.join(ROOT, "data", "cz_monitor.db"))


class Config:
    def __init__(self, path=CONFIG_PATH):
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        self.asset = raw["asset"]
        self.token = self.asset["token"].lower()
        self.decimals = int(self.asset.get("decimals", 18))
        self.total_supply = float(self.asset.get("total_supply") or 0)
        self.pool = (self.asset.get("pool") or "").lower()
        self.watchlist = raw.get("watchlist", [])
        self.signals = raw.get("signals", {})
        self.intervals = raw.get("intervals", {})
        self.funder_watch = raw.get("funder_watch", {})
        self.labels = {w["addr"].lower(): w.get("label", w["addr"]) for w in self.watchlist}
        self.labels[self.pool] = "PancakeSwap pool"

    def addrs(self, *roles):
        return [w for w in self.watchlist if (not roles or w.get("role") in roles)]

    def label(self, addr):
        a = (addr or "").lower()
        return self.labels.get(a, a[:10] + "…" + a[-4:] if a else "?")


CFG = Config()
