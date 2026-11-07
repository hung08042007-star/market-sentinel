"""AI Businessman & Strategic Repricing Advisor.

Analyzes competitor price movements, decodes strategic intent,
assesses threat levels, and recommends counter-pricing & non-price defense tactics.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

import httpx

from src.domain.models import DeltaEvent, PriceDelta

logger = logging.getLogger(__name__)


@dataclass
class StrategicAdvice:
    sku: str
    product_title: str
    threat_level: str  # "CRITICAL" | "HIGH" | "MODERATE" | "LOW" | "OPPORTUNITY"
    intent_diagnosis: str
    recommended_counter_price: float
    projected_margin_pct: float
    tactical_action: str
    executive_briefing: str


class BusinessmanAdvisor:
    """The AI Commercial Strategist for Market Sentinel.

    Equipped with heuristic pricing models and optional LLM synthesis
    to transform raw scrapings into boardroom-ready commercial counter-moves.
    """

    def __init__(
        self,
        default_cost_ratio: float = 0.55,  # Estimated Cost of Goods = 55% of baseline
        min_acceptable_margin: float = 0.15,  # Floor margin: 15%
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: str = "cyber-only",
    ):
        self.default_cost_ratio = default_cost_ratio
        self.min_acceptable_margin = min_acceptable_margin
        self.api_base = api_base or os.getenv("LLM_API_BASE", "http://127.0.0.1:20128/v1")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "dummy-key")
        self.model_name = model_name

    def advise(
        self,
        delta: PriceDelta,
        cost_price: Optional[float] = None,
        use_llm: bool = False,
    ) -> StrategicAdvice:
        """Generate a strategic commercial advisory for a detected price delta."""
        # Calculate baseline cost if not provided
        estimated_cost = (
            cost_price
            if cost_price is not None
            else round(delta.old_price * self.default_cost_ratio, 2)
        )

        # Baseline heuristic calculation
        if delta.event == DeltaEvent.PRICE_DROP:
            advice = self._analyze_price_drop(delta, estimated_cost)
        elif delta.event == DeltaEvent.PRICE_HIKE:
            advice = self._analyze_price_hike(delta, estimated_cost)
        elif delta.event == DeltaEvent.RESTOCK:
            advice = self._analyze_restock(delta, estimated_cost)
        else:
            advice = self._analyze_default(delta, estimated_cost)

        # If LLM requested and reachable, enrich the executive briefing
        if use_llm:
            enriched_summary = self._call_llm_advisor(delta, advice)
            if enriched_summary:
                advice.executive_briefing = enriched_summary

        return advice

    def _analyze_price_drop(
        self, delta: PriceDelta, cost_price: float
    ) -> StrategicAdvice:
        pct_drop = abs(delta.percentage_change)
        competitor_price = delta.new_price

        # Safeguard calculation: Can we undercut by 1% while protecting floor margin?
        ideal_counter = round(competitor_price * 0.98, 2)
        floor_price = round(cost_price * (1 + self.min_acceptable_margin), 2)

        if ideal_counter >= floor_price:
            counter_price = ideal_counter
            margin = round(((counter_price - cost_price) / counter_price) * 100, 1)
            can_undercut = True
        else:
            counter_price = max(floor_price, round(competitor_price, 2))
            margin = round(((counter_price - cost_price) / counter_price) * 100, 1)
            can_undercut = False

        if pct_drop >= 20.0:
            threat = "CRITICAL"
            intent = "Xả kho cắt lỗ hoặc chiến dịch kích cầu đột ngột (Flash Sale / Liquidation)"
            if can_undercut:
                action = (
                    f"Hạ giá đối ứng về {counter_price:,.2f} {delta.currency} (thấp hơn 2%). "
                    f"Giữ biên lợi nhuận ròng {margin}%. Bật quảng cáo nhắm thẳng từ khóa sản phẩm."
                )
            else:
                action = (
                    f"KHÔNG hạ giá theo để tránh bẫy margin (Giá sàn an toàn là {floor_price:,.2f} {delta.currency}). "
                    f"Giữ giá hiện tại, tạo combo quà tặng hoặc miễn phí vận chuyển để bảo vệ doanh thu."
                )
        elif pct_drop >= 10.0:
            threat = "HIGH"
            intent = "Cạnh tranh giằng co thị phần có chủ đích (Aggressive Repricing)"
            action = (
                f"Tái định giá về {counter_price:,.2f} {delta.currency}. "
                f"Biên lợi nhuận dự kiến: {margin}%. Theo dõi lượng hàng tồn của đối thủ trong 48h tới."
            )
        else:
            threat = "MODERATE"
            intent = "Điều chỉnh biên độ nhỏ (Micro-tuning / A/B Testing)"
            action = (
                f"Tạm thời giữ nguyên giá hoặc giảm nhẹ theo {counter_price:,.2f} {delta.currency}. "
                f"Biến động dưới 10% chưa đe dọa ngay lập tức tới lượt mua."
            )

        briefing = (
            f"Đối thủ vừa cắt giảm {pct_drop:.1f}% trên mã {delta.sku}. "
            f"Đánh giá rủi ro: [{threat}]. {intent}. "
            f"Khuyến nghị phản đòn: {action}"
        )

        return StrategicAdvice(
            sku=delta.sku,
            product_title=delta.product_title,
            threat_level=threat,
            intent_diagnosis=intent,
            recommended_counter_price=counter_price,
            projected_margin_pct=margin,
            tactical_action=action,
            executive_briefing=briefing,
        )

    def _analyze_price_hike(
        self, delta: PriceDelta, cost_price: float
    ) -> StrategicAdvice:
        pct_hike = delta.percentage_change
        margin = round(((delta.old_price - cost_price) / delta.old_price) * 100, 1)

        # Competitor increased price => Opportunity to capture market or raise prices slightly
        suggested_price = round(delta.new_price * 0.95, 2)  # 5% cheaper than competitor
        new_margin = round(((suggested_price - cost_price) / suggested_price) * 100, 1)

        threat = "OPPORTUNITY"
        intent = "Đối thủ tăng biên lợi nhuận hoặc đối mặt với đứt gãy nguồn cung / cạn kho"
        action = (
            f"Cơ hội vàng: Đặt giá {suggested_price:,.2f} {delta.currency} (vừa rẻ hơn đối thủ 5% để hút toàn bộ khách, "
            f"vừa tăng biên lợi nhuận lên {new_margin}%)."
        )
        briefing = (
            f"Đối thủ tăng giá +{pct_hike:.1f}% trên {delta.sku}. "
            f"Đây là cơ hội [OPPORTUNITY]. Họ đang chịu áp lực chi phí hoặc cạn kho. "
            f"Khuyến nghị: {action}"
        )

        return StrategicAdvice(
            sku=delta.sku,
            product_title=delta.product_title,
            threat_level=threat,
            intent_diagnosis=intent,
            recommended_counter_price=suggested_price,
            projected_margin_pct=new_margin,
            tactical_action=action,
            executive_briefing=briefing,
        )

    def _analyze_restock(
        self, delta: PriceDelta, cost_price: float
    ) -> StrategicAdvice:
        threat = "HIGH"
        intent = "Đối thủ vừa tái nhập hàng thành công sau thời gian đứt hàng"
        action = "Kiểm tra lại thứ hạng hiển thị và ngân sách ads, chuẩn bị đối đầu trực tiếp về lượt click."
        margin = round(((delta.new_price - cost_price) / delta.new_price) * 100, 1)

        briefing = (
            f"Cảnh báo hàng về: Đối thủ đã restock sản phẩm {delta.sku} với giá {delta.new_price:,.2f} {delta.currency}. "
            f"Thời kỳ độc quyền hàng tạm kết thúc. {action}"
        )

        return StrategicAdvice(
            sku=delta.sku,
            product_title=delta.product_title,
            threat_level=threat,
            intent_diagnosis=intent,
            recommended_counter_price=delta.new_price,
            projected_margin_pct=margin,
            tactical_action=action,
            executive_briefing=briefing,
        )

    def _analyze_default(
        self, delta: PriceDelta, cost_price: float
    ) -> StrategicAdvice:
        margin = round(((delta.new_price - cost_price) / delta.new_price) * 100, 1)
        return StrategicAdvice(
            sku=delta.sku,
            product_title=delta.product_title,
            threat_level="LOW",
            intent_diagnosis="Biến động trạng thái thông thường",
            recommended_counter_price=delta.new_price,
            projected_margin_pct=margin,
            tactical_action="Duy trì theo dõi thụ động.",
            executive_briefing=f"Ghi nhận cập nhật trên SKU {delta.sku}.",
        )

    def _call_llm_advisor(
        self, delta: PriceDelta, base_advice: StrategicAdvice
    ) -> Optional[str]:
        """Optional zero-trust LLM call to enhance strategic advisory."""
        prompt = (
            f"Bạn là Cố vấn Chiến lược Kinh doanh E-Commerce Cấp cao.\n"
            f"Sản phẩm: {delta.product_title} (SKU: {delta.sku})\n"
            f"Sự kiện: {delta.event.value}\n"
            f"Giá cũ: {delta.old_price} {delta.currency} -> Giá mới: {delta.new_price} {delta.currency} ({delta.percentage_change:+.2f}%)\n"
            f"Mức đe dọa sơ bộ: {base_advice.threat_level}\n"
            f"Giá phản công đề xuất: {base_advice.recommended_counter_price} {delta.currency}\n\n"
            f"Hãy viết 2 câu tóm tắt điều hành (Executive Summary) sắc bén gửi trực tiếp cho Giám đốc Shop:\n"
            f"1. Giải mã tâm lý/động cơ của đối thủ.\n"
            f"2. Hành động phản công cụ thể nhất để tối ưu doanh thu và lợi nhuận."
        )

        try:
            resp = httpx.post(
                f"{self.api_base.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model_name,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Bạn là chuyên gia cố vấn thương mại điện tử thực chiến, phong cách sắc bén, đi thẳng vào hành động và lợi nhuận.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.4,
                    "max_tokens": 200,
                },
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()
                return content
        except Exception as exc:
            logger.debug(f"LLM advisor call skipped/failed (falling back to heuristic): {exc}")

        return None
