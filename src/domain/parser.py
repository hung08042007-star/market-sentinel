"""HTML Parsers with Zero-Trust error containment.

Extracts structured product data from e-commerce catalog markup,
gracefully isolates malformed HTML cards, and logs parse anomalies.
"""

from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.domain.models import ProductItem, StockStatus, parse_currency_amount

logger = logging.getLogger(__name__)

RATING_MAP = {
    "one": 1.0,
    "two": 2.0,
    "three": 3.0,
    "four": 4.0,
    "five": 5.0,
}


class ParseReport:
    def __init__(self, items: list[ProductItem], failed_count: int, warnings: list[str]):
        self.items = items
        self.failed_count = failed_count
        self.warnings = warnings

    @property
    def total_found(self) -> int:
        return len(self.items) + self.failed_count


class BaseCatalogParser(ABC):
    @abstractmethod
    def parse(self, html_content: str, base_url: str = "") -> ParseReport:
        """Parse raw HTML content into a ParseReport containing validated ProductItems."""
        pass


class EcommerceCatalogParser(BaseCatalogParser):
    """Resilient parser capable of extracting catalog products.

    Handles Books to Scrape structure and standard e-commerce card patterns.
    """

    def parse(self, html_content: str, base_url: str = "") -> ParseReport:
        soup = BeautifulSoup(html_content, "lxml")
        items: list[ProductItem] = []
        warnings: list[str] = []
        failed_count = 0

        # Try finding standard card containers
        cards = soup.select("article.product_pod")
        if not cards:
            cards = soup.select(".product-card, .product-item, .card-product")

        for idx, card in enumerate(cards, start=1):
            try:
                item = self._extract_card(card, base_url, index=idx)
                items.append(item)
            except Exception as exc:
                failed_count += 1
                warn_msg = f"Card #{idx} failed extraction: {exc}"
                logger.warning(warn_msg)
                warnings.append(warn_msg)

        return ParseReport(items=items, failed_count=failed_count, warnings=warnings)

    def _extract_card(self, card: Any, base_url: str, index: int) -> ProductItem:
        # 1. Title and link
        title_tag = card.select_one("h3 a, h2 a, .product-title a, a.product-link")
        if not title_tag:
            # Fallback to plain h3 or h2 if not linked
            title_tag = card.select_one("h3, h2, .product-title")
            if not title_tag:
                raise ValueError("Missing title element in product card")

        title = title_tag.get("title") or title_tag.get_text(strip=True)
        if not title:
            raise ValueError("Empty title string in product card")

        relative_url = title_tag.get("href", "")
        full_url = urljoin(base_url, relative_url) if base_url else relative_url

        # 2. Price extraction
        price_tag = card.select_one("p.price_color, .price, .product-price, .current-price")
        if not price_tag:
            raise ValueError("Missing price element in product card")

        raw_price = price_tag.get_text(strip=True)
        current_price, currency = parse_currency_amount(raw_price)

        # 3. Stock status
        stock_status = StockStatus.IN_STOCK
        stock_tag = card.select_one("p.instock, .stock-status, .availability")
        if stock_tag:
            stock_text = stock_tag.get_text(strip=True).lower()
            if "out of stock" in stock_text or "hết hàng" in stock_text:
                stock_status = StockStatus.OUT_OF_STOCK
            elif "in stock" in stock_text or "còn hàng" in stock_text:
                stock_status = StockStatus.IN_STOCK
            elif "low stock" in stock_text or "sắp hết" in stock_text:
                stock_status = StockStatus.LOW_STOCK

        # 4. Rating extraction
        rating = None
        rating_tag = card.select_one(".star-rating, [class*='star-rating']")
        if rating_tag:
            class_names = rating_tag.get("class", [])
            for c in class_names:
                c_clean = c.lower().strip()
                if c_clean in RATING_MAP:
                    rating = RATING_MAP[c_clean]
                    break

        # 5. SKU generation (stable from URL path or Title hash)
        if full_url:
            parts = [p for p in full_url.rstrip("/").split("/") if p]
            # Strip index or filename if generic
            if parts and parts[-1].split(".")[0].lower() in ("index", "default", "item", "product"):
                clean_path = parts[-2] if len(parts) >= 2 else parts[-1]
            else:
                clean_path = parts[-1].replace(".html", "").replace(".htm", "") if parts else ""
            sku = clean_path if len(clean_path) >= 3 else hashlib.sha256(full_url.encode()).hexdigest()[:12]
        else:
            sku = hashlib.sha256(f"{title}-{index}".encode()).hexdigest()[:12]

        return ProductItem(
            sku=sku,
            title=title,
            current_price=current_price,
            currency=currency,
            stock_status=stock_status,
            rating=rating,
            url=full_url or f"urn:item:{sku}",
        )
