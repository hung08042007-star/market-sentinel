"""Sentinel Service - Core orchestration layer for Market Sentinel.

Coordinates Collector, Parser, and Repository while isolating business logic
(price delta detection, outlier filtering, event triggering).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from src.collector.client import ResilientCollector
from src.domain.models import DeltaEvent, PriceDelta, ProductItem
from src.domain.parser import BaseCatalogParser, EcommerceCatalogParser
from src.repository.sqlite import SQLiteProductRepository

logger = logging.getLogger(__name__)


@dataclass
class ScanSummary:
    target_url: str
    total_found: int
    items_scraped: list[ProductItem]
    deltas_detected: list[PriceDelta]
    failed_cards_count: int
    warnings: list[str] = field(default_factory=list)
    latency_ms: float = 0.0

    @property
    def price_drops(self) -> list[PriceDelta]:
        return [d for d in self.deltas_detected if d.event == DeltaEvent.PRICE_DROP]

    @property
    def restocks(self) -> list[PriceDelta]:
        return [d for d in self.deltas_detected if d.event == DeltaEvent.RESTOCK]


class SentinelService:
    def __init__(
        self,
        repository: SQLiteProductRepository,
        collector: Optional[ResilientCollector] = None,
        parser: Optional[BaseCatalogParser] = None,
    ):
        self.repository = repository
        self.collector = collector or ResilientCollector()
        self.parser = parser or EcommerceCatalogParser()

    def scan_catalog(self, url: str) -> ScanSummary:
        """Fetch catalog, validate items, detect price/stock deltas, and record snapshots."""
        logger.info(f"Starting catalog scan for: {url}")
        fetch_res = self.collector.fetch(url)

        report = self.parser.parse(fetch_res.text, base_url=url)
        deltas: list[PriceDelta] = []

        for item in report.items:
            existing = self.repository.get_product(item.sku)
            if existing is not None:
                delta = PriceDelta.calculate(
                    product=item,
                    old_price=existing.current_price,
                    old_stock=existing.stock_status,
                )
                if delta.event != DeltaEvent.NO_CHANGE:
                    deltas.append(delta)
                    logger.info(
                        f"Delta detected [{delta.event.value}] on '{item.title}': "
                        f"{delta.old_price} -> {delta.new_price} ({delta.percentage_change}%)"
                    )

            # Persist latest state and snapshot
            self.repository.upsert_product(item)
            self.repository.record_snapshot(item.sku, item.current_price, item.stock_status)

        return ScanSummary(
            target_url=url,
            total_found=report.total_found,
            items_scraped=report.items,
            deltas_detected=deltas,
            failed_cards_count=report.failed_count,
            warnings=report.warnings,
            latency_ms=fetch_res.latency_ms,
        )
