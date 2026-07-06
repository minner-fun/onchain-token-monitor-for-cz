# -*- coding: utf-8 -*-
"""SQLite storage: balance snapshots, market snapshots, events, cursors, subscribers."""
import os
import time
import sqlite3
import threading

from . import config

_LOCAL = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS balance_snapshot(addr TEXT, ts INTEGER, balance REAL);
CREATE INDEX IF NOT EXISTS ix_bal ON balance_snapshot(addr, ts);
CREATE TABLE IF NOT EXISTS market_snapshot(ts INTEGER, price REAL, liq REAL, vol24h REAL, ratio REAL);
CREATE TABLE IF NOT EXISTS event(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER, type TEXT, severity TEXT,
  addr TEXT, title TEXT, detail TEXT, tx TEXT);
CREATE INDEX IF NOT EXISTS ix_evt ON event(ts);
CREATE TABLE IF NOT EXISTS cursor(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS subscriber(chat_id TEXT PRIMARY KEY, first_seen INTEGER);
"""


def conn():
    c = getattr(_LOCAL, "c", None)
    if c is None:
        os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
        c = sqlite3.connect(config.DB_PATH, timeout=30)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL;")
        _LOCAL.c = c
    return c


def init():
    conn().executescript(SCHEMA)
    conn().commit()


def insert_balance(addr, ts, bal):
    conn().execute("INSERT INTO balance_snapshot VALUES(?,?,?)", (addr, ts, bal)); conn().commit()


def last_balance(addr):
    r = conn().execute("SELECT balance FROM balance_snapshot WHERE addr=? ORDER BY ts DESC LIMIT 1",
                       (addr,)).fetchone()
    return r["balance"] if r else None


def insert_market(ts, price, liq, vol24h, ratio):
    conn().execute("INSERT INTO market_snapshot VALUES(?,?,?,?,?)", (ts, price, liq, vol24h, ratio))
    conn().commit()


def last_market():
    return conn().execute(
        "SELECT ts,price,liq,vol24h,ratio FROM market_snapshot ORDER BY ts DESC LIMIT 1").fetchone()


def insert_event(ts, type_, severity, addr, title, detail, tx=None):
    conn().execute("INSERT INTO event(ts,type,severity,addr,title,detail,tx) VALUES(?,?,?,?,?,?,?)",
                   (ts, type_, severity, addr, title, detail, tx)); conn().commit()


def get_cursor(key, default=None):
    r = conn().execute("SELECT value FROM cursor WHERE key=?", (key,)).fetchone()
    return r["value"] if r else default


def set_cursor(key, value):
    conn().execute("INSERT INTO cursor(key,value) VALUES(?,?) "
                   "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
    conn().commit()


def add_subscriber(chat_id):
    """Record a Telegram subscriber. Returns True if newly added."""
    chat_id = str(chat_id)
    existed = conn().execute("SELECT 1 FROM subscriber WHERE chat_id=?", (chat_id,)).fetchone()
    conn().execute("INSERT OR IGNORE INTO subscriber(chat_id,first_seen) VALUES(?,?)",
                   (chat_id, int(time.time())))
    conn().commit()
    return existed is None


def all_subscribers():
    return [r["chat_id"] for r in conn().execute("SELECT chat_id FROM subscriber").fetchall()]


def subscribers_detailed():
    return [(r["chat_id"], r["first_seen"]) for r in
            conn().execute("SELECT chat_id,first_seen FROM subscriber ORDER BY first_seen").fetchall()]
