"""SQLite Repository for Market Sentinel.

Persists current product catalog state and historical price time-series.
Enforces WAL mode, busy timeout, and parameterized queries for security.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.domain.models import ProductItem, StockStatus


class SQLiteProductRepository:
    def __init__(self, db_path: str = "data/sentinel.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        with self._conn:
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA busy_timeout=5000;")
            self._conn.execute("PRAGMA foreign_keys=ON;")

            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    sku TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    current_price REAL NOT NULL,
                    original_price REAL,
                    currency TEXT NOT NULL,
                    stock_status TEXT NOT NULL,
                    rating REAL,
                    reviews_count INTEGER,
                    url TEXT NOT NULL,
                    last_scraped_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)

            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sku TEXT NOT NULL,
                    price REAL NOT NULL,
                    stock_status TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    FOREIGN KEY (sku) REFERENCES products(sku) ON DELETE CASCADE
                );
            """)

            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_sku_time
                ON price_history(sku, recorded_at);
            """)

    def get_product(self, sku: str) -> Optional[ProductItem]:
        cursor = self._conn.execute(
            "SELECT * FROM products WHERE sku = ?", (sku,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        return ProductItem(
            sku=row["sku"],
            title=row["title"],
            current_price=row["current_price"],
            original_price=row["original_price"],
            currency=row["currency"],
            stock_status=StockStatus(row["stock_status"]),
            rating=row["rating"],
            reviews_count=row["reviews_count"],
            url=row["url"],
            captured_at=datetime.fromisoformat(row["last_scraped_at"]),
        )

    def upsert_product(self, item: ProductItem) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO products (
                    sku, title, current_price, original_price, currency,
                    stock_status, rating, reviews_count, url, last_scraped_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(sku) DO UPDATE SET
                    title = excluded.title,
                    current_price = excluded.current_price,
                    original_price = excluded.original_price,
                    currency = excluded.currency,
                    stock_status = excluded.stock_status,
                    rating = excluded.rating,
                    reviews_count = excluded.reviews_count,
                    url = excluded.url,
                    last_scraped_at = excluded.last_scraped_at;
                """,
                (
                    item.sku,
                    item.title,
                    item.current_price,
                    item.original_price,
                    item.currency,
                    item.stock_status.value,
                    item.rating,
                    item.reviews_count,
                    item.url,
                    now_iso,
                    now_iso,
                ),
            )

    def record_snapshot(self, sku: str, price: float, stock: StockStatus) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO price_history (sku, price, stock_status, recorded_at)
                VALUES (?, ?, ?, ?);
                """,
                (sku, price, stock.value, now_iso),
            )

    def get_price_history(self, sku: str, limit: int = 30) -> list[dict]:
        cursor = self._conn.execute(
            """
            SELECT price, stock_status, recorded_at
            FROM price_history
            WHERE sku = ?
            ORDER BY recorded_at DESC
            LIMIT ?;
            """,
            (sku, limit),
        )
        return [
            {
                "price": row["price"],
                "stock_status": row["stock_status"],
                "recorded_at": row["recorded_at"],
            }
            for row in cursor.fetchall()
        ]

    def list_products(self) -> list[ProductItem]:
        cursor = self._conn.execute("SELECT * FROM products ORDER BY title ASC;")
        items = []
        for row in cursor.fetchall():
            items.append(
                ProductItem(
                    sku=row["sku"],
                    title=row["title"],
                    current_price=row["current_price"],
                    original_price=row["original_price"],
                    currency=row["currency"],
                    stock_status=StockStatus(row["stock_status"]),
                    rating=row["rating"],
                    reviews_count=row["reviews_count"],
                    url=row["url"],
                    captured_at=datetime.fromisoformat(row["last_scraped_at"]),
                )
            )
        return items

    def close(self) -> None:
        self._conn.close()
