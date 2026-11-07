from src.advisor.businessman import BusinessmanAdvisor
from src.domain.models import DeltaEvent, PriceDelta


def test_businessman_advises_critical_price_drop():
    advisor = BusinessmanAdvisor()
    delta = PriceDelta(
        sku="book-997",
        product_title="Sharp Objects",
        old_price=59.99,
        new_price=47.82,
        difference=-12.17,
        percentage_change=-20.29,
        event=DeltaEvent.PRICE_DROP,
        currency="GBP",
        url="https://books.toscrape.com/sharp-objects",
    )

    advice = advisor.advise(delta)
    assert advice.threat_level == "CRITICAL"
    assert "Xả kho" in advice.intent_diagnosis or "kích cầu" in advice.intent_diagnosis
    assert advice.recommended_counter_price < 47.82  # Counter price undercuts competitor
    assert advice.projected_margin_pct > 15.0  # Floor margin protected
    assert "Sharp Objects" in advice.product_title


def test_businessman_advises_price_hike_opportunity():
    advisor = BusinessmanAdvisor()
    delta = PriceDelta(
        sku="book-942",
        product_title="The Past Never Ends",
        old_price=45.00,
        new_price=56.50,
        difference=11.50,
        percentage_change=25.56,
        event=DeltaEvent.PRICE_HIKE,
        currency="GBP",
        url="https://books.toscrape.com/the-past-never-ends",
    )

    advice = advisor.advise(delta)
    assert advice.threat_level == "OPPORTUNITY"
    assert "Cơ hội" in advice.tactical_action
    assert advice.recommended_counter_price == 53.67
    assert advice.projected_margin_pct > 40.0


def test_businessman_protects_cost_floor_margin():
    # If client gives explicit high cost_price, counter price must not breach floor margin
    advisor = BusinessmanAdvisor(min_acceptable_margin=0.20)
    delta = PriceDelta(
        sku="book-loss-leader",
        product_title="Underpriced Trap",
        old_price=100.0,
        new_price=40.0,
        difference=-60.0,
        percentage_change=-60.0,
        event=DeltaEvent.PRICE_DROP,
        currency="GBP",
        url="https://example.com/trap",
    )

    # Cost is $50. Floor margin is $50 * 1.20 = $60.
    # Competitor sells at $40. Undercutting to $39.20 would lose money!
    advice = advisor.advise(delta, cost_price=50.0)
    assert advice.threat_level == "CRITICAL"
    assert advice.recommended_counter_price >= 60.0  # Floor price enforced!
    assert "KHÔNG hạ giá" in advice.tactical_action
