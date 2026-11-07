"""Data Exporter (CSV / JSON) for Market Sentinel."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Sequence

from src.domain.models import ProductItem


class DataExporter:
    @staticmethod
    def export_csv(products: Sequence[ProductItem], destination: str) -> str:
        dest_path = Path(destination)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "sku",
            "title",
            "current_price",
            "original_price",
            "discount_percentage",
            "currency",
            "stock_status",
            "rating",
            "reviews_count",
            "url",
            "captured_at",
        ]

        with open(dest_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for p in products:
                writer.writerow(
                    {
                        "sku": p.sku,
                        "title": p.title,
                        "current_price": p.current_price,
                        "original_price": p.original_price or "",
                        "discount_percentage": p.discount_percentage,
                        "currency": p.currency,
                        "stock_status": p.stock_status.value,
                        "rating": p.rating if p.rating is not None else "",
                        "reviews_count": p.reviews_count if p.reviews_count is not None else "",
                        "url": p.url,
                        "captured_at": p.captured_at.isoformat(),
                    }
                )

        return str(dest_path.resolve())

    @staticmethod
    def export_json(products: Sequence[ProductItem], destination: str) -> str:
        dest_path = Path(destination)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        payload = [p.model_dump(mode="json") for p in products]
        with open(dest_path, mode="w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        return str(dest_path.resolve())
