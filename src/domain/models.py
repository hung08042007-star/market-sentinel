"""Domain models and schemas for Market Sentinel.

Enforces Zero-Trust data validation: raw extracted web strings are strictly
validated, parsed into typed numbers, and sanitized before reaching storage.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class StockStatus(str, Enum):
    IN_STOCK = "IN_STOCK"
    LOW_STOCK = "LOW_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    UNKNOWN = "UNKNOWN"


class DeltaEvent(str, Enum):
    PRICE_DROP = "PRICE_DROP"
    PRICE_HIKE = "PRICE_HIKE"
    RESTOCK = "RESTOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    NO_CHANGE = "NO_CHANGE"


def parse_currency_amount(raw_text: str | None) -> tuple[float, str]:
    """Parse raw currency string into (amount, currency_code).

    Handles formats:
      - "$1,299.99" -> (1299.99, "USD")
      - "£51.77" -> (51.77, "GBP")
      - "€ 45,90" -> (45.90, "EUR")
      - "1.500.000 ₫" -> (1500000.0, "VND")
      - "120.00 USD" -> (120.0, "USD")
    """
    if not raw_text:
        raise ValueError("Empty price string cannot be parsed")

    cleaned = raw_text.strip()
    detected_currency = "USD"

    # Identify currency symbol or code
    if "₫" in cleaned or "VND" in cleaned.upper():
        detected_currency = "VND"
    elif "£" in cleaned or "GBP" in cleaned.upper():
        detected_currency = "GBP"
    elif "€" in cleaned or "EUR" in cleaned.upper():
        detected_currency = "EUR"
    elif "$" in cleaned or "USD" in cleaned.upper():
        detected_currency = "USD"

    # Strip currency symbols and letters
    digits_and_seps = re.sub(r"[^\d.,]", "", cleaned)
    if not digits_and_seps:
        raise ValueError(f"No numeric value found in price text: {raw_text!r}")

    # Handle European decimal (e.g., 1.250,50 or 45,90) vs US decimal (1,250.50)
    if "," in digits_and_seps and "." in digits_and_seps:
        last_comma = digits_and_seps.rfind(",")
        last_dot = digits_and_seps.rfind(".")
        if last_comma > last_dot:
            # European format: 1.250,50 -> 1250.50
            standardized = digits_and_seps.replace(".", "").replace(",", ".")
        else:
            # Standard US format: 1,250.50 -> 1250.50
            standardized = digits_and_seps.replace(",", "")
    elif "," in digits_and_seps and "." not in digits_and_seps:
        # Could be decimal (45,90) or thousands separator for VND (1,500,000)
        parts = digits_and_seps.split(",")
        if len(parts) == 2 and len(parts[1]) in (1, 2) and detected_currency != "VND":
            standardized = digits_and_seps.replace(",", ".")
        else:
            standardized = digits_and_seps.replace(",", "")
    elif "." in digits_and_seps and "," not in digits_and_seps:
        # For VND: 1.500.000 is thousands, not decimal
        if detected_currency == "VND" and digits_and_seps.count(".") >= 1:
            standardized = digits_and_seps.replace(".", "")
        else:
            standardized = digits_and_seps
    else:
        standardized = digits_and_seps

    try:
        amount = float(standardized)
    except ValueError as exc:
        raise ValueError(f"Failed to convert normalized price {standardized!r} from {raw_text!r}") from exc

    return round(amount, 2), detected_currency


class ProductItem(BaseModel):
    sku: str = Field(..., min_length=1, max_length=128, description="Unique product identifier")
    title: str = Field(..., min_length=1, max_length=512, description="Product title")
    current_price: float = Field(..., ge=0.0, description="Current price as float")
    original_price: Optional[float] = Field(default=None, ge=0.0, description="Pre-discount price if any")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    stock_status: StockStatus = Field(default=StockStatus.IN_STOCK)
    rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    reviews_count: Optional[int] = Field(default=None, ge=0)
    url: str = Field(..., min_length=5, description="Source product URL")
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("sku", "title", mode="before")
    @classmethod
    def clean_text_field(cls, v: str) -> str:
        if isinstance(v, str):
            cleaned = " ".join(v.split()).strip()
            if not cleaned:
                raise ValueError("Field cannot be empty or whitespace only")
            return cleaned
        return v

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().upper()
        return v

    @property
    def discount_percentage(self) -> float:
        """Calculate discount percentage if original_price is available."""
        if self.original_price and self.original_price > self.current_price:
            diff = self.original_price - self.current_price
            return round((diff / self.original_price) * 100, 2)
        return 0.0


class PriceDelta(BaseModel):
    sku: str
    product_title: str
    old_price: float
    new_price: float
    difference: float
    percentage_change: float
    event: DeltaEvent
    currency: str = "USD"
    url: str
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def calculate(
        cls,
        product: ProductItem,
        old_price: float,
        old_stock: StockStatus = StockStatus.IN_STOCK,
    ) -> PriceDelta:
        diff = round(product.current_price - old_price, 2)
        pct = round((diff / old_price) * 100, 2) if old_price > 0 else 0.0

        if diff < 0:
            event = DeltaEvent.PRICE_DROP
        elif diff > 0:
            event = DeltaEvent.PRICE_HIKE
        elif old_stock == StockStatus.OUT_OF_STOCK and product.stock_status == StockStatus.IN_STOCK:
            event = DeltaEvent.RESTOCK
        elif old_stock != StockStatus.OUT_OF_STOCK and product.stock_status == StockStatus.OUT_OF_STOCK:
            event = DeltaEvent.OUT_OF_STOCK
        else:
            event = DeltaEvent.NO_CHANGE

        return cls(
            sku=product.sku,
            product_title=product.title,
            old_price=old_price,
            new_price=product.current_price,
            difference=diff,
            percentage_change=pct,
            event=event,
            currency=product.currency,
            url=product.url,
        )
