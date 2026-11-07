from src.domain.models import StockStatus
from src.domain.parser import EcommerceCatalogParser

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="row">
    <!-- Card 1: Valid book -->
    <article class="product_pod">
      <div class="image_container">
        <a href="catalogue/a-light-in-the-attic_1000/index.html"><img src="media/cache/test.jpg"></a>
      </div>
      <p class="star-rating Three"></p>
      <h3><a href="catalogue/a-light-in-the-attic_1000/index.html" title="A Light in the Attic">A Light in the ...</a></h3>
      <div class="product_price">
        <p class="price_color">£51.77</p>
        <p class="instock availability">
          <i class="icon-ok"></i> In stock
        </p>
      </div>
    </article>

    <!-- Card 2: Out of stock book -->
    <article class="product_pod">
      <div class="image_container">
        <a href="catalogue/tipping-the-velvet_999/index.html"><img src="media/cache/test2.jpg"></a>
      </div>
      <p class="star-rating One"></p>
      <h3><a href="catalogue/tipping-the-velvet_999/index.html" title="Tipping the Velvet">Tipping the Velvet</a></h3>
      <div class="product_price">
        <p class="price_color">£53.74</p>
        <p class="instock availability">
          Out of stock
        </p>
      </div>
    </article>

    <!-- Card 3: Broken card (missing price) -->
    <article class="product_pod">
      <h3><a href="catalogue/broken_1/index.html" title="Broken Item">Broken Item</a></h3>
      <div class="product_price">
        <!-- Missing price tag intentionally -->
      </div>
    </article>
  </div>
</body>
</html>
"""


def test_parser_extracts_items_and_isolates_failures():
    parser = EcommerceCatalogParser()
    report = parser.parse(SAMPLE_HTML, base_url="https://books.toscrape.com/")

    assert len(report.items) == 2
    assert report.failed_count == 1
    assert report.total_found == 3
    assert len(report.warnings) == 1
    assert "Missing price element" in report.warnings[0]

    # Verify first item
    first = report.items[0]
    assert first.title == "A Light in the Attic"
    assert first.current_price == 51.77
    assert first.currency == "GBP"
    assert first.stock_status == StockStatus.IN_STOCK
    assert first.rating == 3.0
    assert first.url == "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"

    # Verify second item
    second = report.items[1]
    assert second.title == "Tipping the Velvet"
    assert second.current_price == 53.74
    assert second.stock_status == StockStatus.OUT_OF_STOCK
    assert second.rating == 1.0
