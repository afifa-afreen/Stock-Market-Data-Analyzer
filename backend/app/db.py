import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "stock_analyzer.db"

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS symbols (
            ticker TEXT PRIMARY KEY, name TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS candles (
            ticker TEXT NOT NULL, date TEXT NOT NULL,
            open REAL, high REAL, low REAL, close REAL, adj_close REAL, volume REAL,
            PRIMARY KEY(ticker, date)
        );
        CREATE TABLE IF NOT EXISTS indicators (
            ticker TEXT NOT NULL, date TEXT NOT NULL,
            sma20 REAL, sma50 REAL, rsi14 REAL, macd REAL, macd_signal REAL,
            bb_upper REAL, bb_lower REAL, signal TEXT,
            PRIMARY KEY(ticker, date)
        );
        CREATE TABLE IF NOT EXISTS backtests (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT, strategy TEXT,
            start_date TEXT, end_date TEXT, total_return REAL, sharpe REAL,
            max_drawdown REAL, trades INTEGER, costs REAL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS portfolio_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT NOT NULL,
            side TEXT NOT NULL CHECK(side IN ('BUY','SELL')),
            quantity REAL NOT NULL, price REAL NOT NULL, trade_date TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT NOT NULL,
            alert_type TEXT NOT NULL, message TEXT NOT NULL,
            last_fired TEXT, active INTEGER DEFAULT 1
        );
        """)
