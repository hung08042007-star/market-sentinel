import os
import tempfile
import pytest
from src.domain.models import ProductItem, StockStatus
from src.repository.sqlite import SQLiteProductRepository


@pytest.fixture
def temp_repo():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name
    repo = SQLiteProductRepository(db_path=db_path)
    yield repo
    repo.close()
    if os.path.exists(db_path):
        os.remove(db_path)


def test_sqlite_upsert_and_get(temp_repo):
    item = ProductItem(
        sku="sku-001",
        title="Test Mechanical Keyboard",
        current_price=89.99,
        original_price=110.00,
        currency="USD",
        stock_status=StockStatus.IN_STOCK,
        rating=4.5,
        url="https://example.com/keyboard",
    )
    temp_repo.upsert_product(item)

    fetched = temp_repo.get_product("sku-001")
    assert fetched is not None
    assert fetched.sku == "sku-001"
    assert fetched.title == "Test Mechanical Keyboard"
    assert fetched.current_price == 89.99
    assert fetched.original_price == 110.00
    assert fetched.stock_status == StockStatus.IN_STOCK
    assert fetched.rating == 4.5


def test_sqlite_price_history_and_wal(temp_repo):
    item = ProductItem(
        sku="sku-001",
        title="Test Mechanical Keyboard",
        current_price=99.00,
        currency="USD",
        stock_status=StockStatus.IN_STOCK,
        url="https://example.com/keyboard",
    )
    temp_repo.upsert_product(item)

    temp_repo.record_snapshot("sku-001", 99.00, StockStatus.IN_STOCK)
    temp_repo.record_snapshot("sku-001", 89.99, StockStatus.IN_STOCK)
    temp_repo.record_snapshot("sku-001", 79.99, StockStatus.LOW_STOCK)

    history = temp_repo.get_price_history("sku-001", limit=10)
    assert len(history) == 3
    # Check ordered by recorded_at DESC
    assert history[0]["price"] == 79.99
    assert history[0]["stock_status"] == "LOW_STOCK"
    assert history[2]["price"] == 99.00


def test_sqlite_list_products(temp_repo):
    item1 = ProductItem(sku="s1", title="Alpha", current_price=10.0, url="https://ex.com/1")
    item2 = ProductItem(sku="s2", title="Beta", current_price=20.0, url="https://ex.com/2")
    temp_repo.upsert_product(item1)
    temp_repo.upsert_product(item2)

    products = temp_repo.list_products()
    assert len(products) == 2
    assert [p.sku for p in products] == ["s1", "s2"]
