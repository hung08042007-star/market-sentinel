import json
import os
import tempfile
from src.domain.models import DeltaEvent, PriceDelta, ProductItem
from src.notifier.exporter import DataExporter
from src.notifier.telegram import TelegramNotifier


def test_telegram_notifier_dry_run():
    notifier = TelegramNotifier(dry_run=True)
    delta = PriceDelta(
        sku="book-100",
        product_title="Fluent Python",
        old_price=59.99,
        new_price=44.99,
        difference=-15.00,
        percentage_change=-25.01,
        event=DeltaEvent.PRICE_DROP,
        currency="USD",
        url="https://example.com/fluent-python",
    )

    msg = notifier.format_delta_message(delta)
    assert "Fluent Python" in msg
    assert "GIẢM GIÁ" in msg
    assert "-25.01%" in msg

    sent = notifier.notify_deltas([delta])
    assert sent == 1


def test_data_exporter_csv_and_json():
    with tempfile.TemporaryDirectory() as td:
        csv_path = os.path.join(td, "export.csv")
        json_path = os.path.join(td, "export.json")

        items = [
            ProductItem(
                sku="sku-1",
                title="Wireless Earbuds",
                current_price=29.99,
                original_price=39.99,
                currency="USD",
                url="https://example.com/earbuds",
            )
        ]

        # CSV Export
        DataExporter.export_csv(items, csv_path)
        assert os.path.exists(csv_path)
        with open(csv_path, encoding="utf-8") as f:
            content = f.read()
            assert "Wireless Earbuds" in content
            assert "29.99" in content

        # JSON Export
        DataExporter.export_json(items, json_path)
        assert os.path.exists(json_path)
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
            assert len(data) == 1
            assert data[0]["sku"] == "sku-1"
            assert data[0]["current_price"] == 29.99
