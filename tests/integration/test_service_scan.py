import os
import tempfile
import httpx
import pytest
from src.collector.client import ResilientCollector
from src.domain.models import DeltaEvent
from src.domain.parser import EcommerceCatalogParser
from src.domain.service import SentinelService
from src.repository.sqlite import SQLiteProductRepository

HTML_SCAN_1 = """
<html><body>
  <article class="product_pod">
    <h3><a href="catalogue/item-a_1/index.html" title="Item A">Item A</a></h3>
    <div class="product_price">
      <p class="price_color">£100.00</p>
      <p class="instock availability">In stock</p>
    </div>
  </article>
</body></html>
"""

HTML_SCAN_2 = """
<html><body>
  <article class="product_pod">
    <h3><a href="catalogue/item-a_1/index.html" title="Item A">Item A</a></h3>
    <div class="product_price">
      <p class="price_color">£75.00</p>
      <p class="instock availability">In stock</p>
    </div>
  </article>
</body></html>
"""


@pytest.fixture
def temp_service():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name
    repo = SQLiteProductRepository(db_path=db_path)

    # We will swap transport per test
    yield repo, db_path

    repo.close()
    if os.path.exists(db_path):
        os.remove(db_path)


def test_service_delta_detection_lifecycle(temp_service):
    repo, _ = temp_service

    current_html = HTML_SCAN_1

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=current_html)

    client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    collector = ResilientCollector(client=client, rate_limit_delay=0.0)
    service = SentinelService(repository=repo, collector=collector, parser=EcommerceCatalogParser())

    # First Scan: Baseline seeding
    summary1 = service.scan_catalog("https://example.com/catalog/")
    assert summary1.total_found == 1
    assert len(summary1.items_scraped) == 1
    assert len(summary1.deltas_detected) == 0  # No previous price to compare with

    product_stored = repo.get_product("item-a_1")
    assert product_stored is not None
    assert product_stored.current_price == 100.00

    # Second Scan: Price drop from £100.00 to £75.00
    current_html = HTML_SCAN_2
    summary2 = service.scan_catalog("https://example.com/catalog/")
    assert len(summary2.deltas_detected) == 1

    delta = summary2.deltas_detected[0]
    assert delta.event == DeltaEvent.PRICE_DROP
    assert delta.old_price == 100.00
    assert delta.new_price == 75.00
    assert delta.difference == -25.00
    assert delta.percentage_change == -25.0

    # Check price history in DB
    history = repo.get_price_history("item-a_1")
    assert len(history) == 2
    assert history[0]["price"] == 75.00
    assert history[1]["price"] == 100.00
