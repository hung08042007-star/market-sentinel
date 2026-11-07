import pytest
from src.domain.models import (
    DeltaEvent,
    PriceDelta,
    ProductItem,
    StockStatus,
    parse_currency_amount,
)


def test_parse_currency_amount_usd():
    amount, curr = parse_currency_amount("$1,299.99")
    assert amount == 1299.99
    assert curr == "USD"


def test_parse_currency_amount_gbp():
    amount, curr = parse_currency_amount("£51.77")
    assert amount == 51.77
    assert curr == "GBP"


def test_parse_currency_amount_eur():
    amount, curr = parse_currency_amount("€ 45,90")
    assert amount == 45.90
    assert curr == "EUR"


def test_parse_currency_amount_vnd():
    amount, curr = parse_currency_amount("1.500.000 ₫")
    assert amount == 1500000.0
    assert curr == "VND"


def test_parse_currency_amount_invalid():
    with pytest.raises(ValueError, match="Empty price string"):
        parse_currency_amount("")

    with pytest.raises(ValueError, match="No numeric value"):
        parse_currency_amount("Free Gift")


def test_product_item_valid():
    item = ProductItem(
        sku="book-101",
        title="  A Light in the Attic   ",
        current_price=51.77,
        original_price=60.00,
        currency="gbp",
        stock_status=StockStatus.IN_STOCK,
        rating=3.0,
        url="https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
    )
    assert item.title == "A Light in the Attic"
    assert item.currency == "GBP"
    assert item.discount_percentage == 13.72


def test_product_item_rejects_negative_price():
    with pytest.raises(ValueError):
        ProductItem(
            sku="book-102",
            title="Invalid Price Book",
            current_price=-10.0,
            url="https://example.com",
        )


def test_product_item_rejects_empty_title():
    with pytest.raises(ValueError, match="Field cannot be empty"):
        ProductItem(
            sku="book-103",
            title="   ",
            current_price=10.0,
            url="https://example.com",
        )


def test_price_delta_events():
    product = ProductItem(
        sku="sku-99",
        title="Gaming Mouse",
        current_price=45.0,
        url="https://example.com/mouse",
    )

    # 1. Price Drop
    delta_drop = PriceDelta.calculate(product, old_price=50.0)
    assert delta_drop.event == DeltaEvent.PRICE_DROP
    assert delta_drop.difference == -5.0
    assert delta_drop.percentage_change == -10.0

    # 2. Price Hike
    delta_hike = PriceDelta.calculate(product, old_price=40.0)
    assert delta_hike.event == DeltaEvent.PRICE_HIKE
    assert delta_hike.difference == 5.0
    assert delta_hike.percentage_change == 12.5

    # 3. Restock
    delta_restock = PriceDelta.calculate(
        product, old_price=45.0, old_stock=StockStatus.OUT_OF_STOCK
    )
    assert delta_restock.event == DeltaEvent.RESTOCK
    assert delta_restock.difference == 0.0

    # 4. Out of stock
    product_oos = ProductItem(
        sku="sku-99",
        title="Gaming Mouse",
        current_price=45.0,
        stock_status=StockStatus.OUT_OF_STOCK,
        url="https://example.com/mouse",
    )
    delta_oos = PriceDelta.calculate(
        product_oos, old_price=45.0, old_stock=StockStatus.IN_STOCK
    )
    assert delta_oos.event == DeltaEvent.OUT_OF_STOCK
