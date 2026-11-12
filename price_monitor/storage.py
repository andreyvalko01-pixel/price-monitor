import sqlite3
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    id          INTEGER PRIMARY KEY,
    run_at      TEXT NOT NULL,
    product_key TEXT NOT NULL,
    product     TEXT NOT NULL,
    store       TEXT NOT NULL,
    title       TEXT NOT NULL,
    price       REAL NOT NULL,
    url         TEXT
);
CREATE INDEX IF NOT EXISTS idx_prices_key ON prices (product_key, store, run_at);
"""


class PriceStorage:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def save_run(self, groups) -> str:
        run_at = datetime.now().isoformat(timespec="seconds")
        rows = [
            (run_at, g["key"], g["title"], o.store, o.title, o.price, o.url)
            for g in groups
            for o in g["offers"]
        ]
        self.conn.executemany(
            "INSERT INTO prices (run_at, product_key, product, store, title, price, url) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        self.conn.commit()
        return run_at

    def previous_price(self, key: str, store: str, before: str) -> float | None:
        row = self.conn.execute(
            "SELECT price FROM prices WHERE product_key = ? AND store = ? AND run_at < ? ORDER BY run_at DESC LIMIT 1",
            (key, store, before),
        ).fetchone()
        return row["price"] if row else None

    def close(self):
        self.conn.close()
