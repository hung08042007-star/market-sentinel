"""Telegram Notifier with Noise Filtering and AI Businessman Strategic Advisor integration."""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from src.advisor.businessman import BusinessmanAdvisor, StrategicAdvice
from src.domain.models import DeltaEvent, PriceDelta

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        dry_run: bool = False,
        min_drop_percent: float = 0.0,
        min_absolute_diff: float = 0.0,
        enable_ai_advisor: bool = True,
        advisor: Optional[BusinessmanAdvisor] = None,
    ):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.dry_run = dry_run or not (bot_token and chat_id)
        self.min_drop_percent = min_drop_percent
        self.min_absolute_diff = min_absolute_diff
        self.enable_ai_advisor = enable_ai_advisor
        self.advisor = advisor or (BusinessmanAdvisor() if enable_ai_advisor else None)

    def should_notify(self, delta: PriceDelta) -> bool:
        """Filter out minor pricing fluctuations according to client threshold."""
        # Always notify for restocks or out-of-stock
        if delta.event in (DeltaEvent.RESTOCK, DeltaEvent.OUT_OF_STOCK):
            return True

        if delta.event == DeltaEvent.PRICE_DROP:
            pct_change = abs(delta.percentage_change)
            abs_diff = abs(delta.old_price - delta.new_price)
            if self.min_drop_percent > 0 and pct_change < self.min_drop_percent:
                return False
            if self.min_absolute_diff > 0 and abs_diff < self.min_absolute_diff:
                return False
            return True

        if delta.event == DeltaEvent.PRICE_HIKE:
            # We notify price hikes if threshold filter permits
            pct_change = abs(delta.percentage_change)
            if self.min_drop_percent > 0 and pct_change < self.min_drop_percent:
                return False
            return True

        return False

    def format_delta_message(
        self, delta: PriceDelta, advice: Optional[StrategicAdvice] = None
    ) -> str:
        """Format a single PriceDelta + AI Briefing into an executive Telegram card."""
        if delta.event == DeltaEvent.PRICE_DROP:
            emoji = "📉 🔥 [CẢNH BÁO HẠ GIÁ]"
        elif delta.event == DeltaEvent.PRICE_HIKE:
            emoji = "📈 🚀 [ĐỐI THỦ TĂNG GIÁ]"
        elif delta.event == DeltaEvent.RESTOCK:
            emoji = "📦 ✨ [ĐỐI THỦ VỀ HÀNG]"
        elif delta.event == DeltaEvent.OUT_OF_STOCK:
            emoji = "❌ ⚠️ [ĐỐI THỦ HẾT HÀNG]"
        else:
            emoji = "ℹ️ [CẬP NHẬT BIẾN ĐỘNG]"

        lines = [
            f"<b>{emoji}</b>",
            f"<b>Sản phẩm:</b> {delta.product_title}",
            f"<b>Mã SKU:</b> <code>{delta.sku}</code>",
            f"<b>Giá cũ:</b> {delta.old_price:,.2f} {delta.currency}",
            f"<b>Giá mới:</b> {delta.new_price:,.2f} {delta.currency} ({delta.percentage_change:+.2f}%)",
        ]

        if advice:
            lines.extend(
                [
                    "──────────────────",
                    f"🧠 <b>AI Commercial Advisor ({advice.threat_level}):</b>",
                    f"• <b>Động cơ:</b> <i>{advice.intent_diagnosis}</i>",
                    f"• <b>Giá phản công đề xuất:</b> <code>{advice.recommended_counter_price:,.2f} {delta.currency}</code> (Margin ~{advice.projected_margin_pct}%)",
                    f"• <b>Kế hoạch hành động:</b> {advice.tactical_action}",
                ]
            )

        lines.append(f"🔗 <a href=\"{delta.url}\">Xem trực tiếp web đối thủ</a>")
        return "\n".join(lines)

    def notify_deltas(self, deltas: list[PriceDelta]) -> int:
        """Filter and send notifications for significant deltas. Returns count sent."""
        if not deltas:
            return 0

        sent_count = 0
        for delta in deltas:
            if not self.should_notify(delta):
                logger.info(
                    f"Delta on {delta.sku} filtered out by noise threshold (drop={delta.percentage_change:.1f}%)"
                )
                continue

            advice = None
            if self.advisor:
                try:
                    advice = self.advisor.advise(delta)
                except Exception as exc:
                    logger.warning(f"Advisor failed for {delta.sku}: {exc}")

            message = self.format_delta_message(delta, advice)
            if self.dry_run:
                logger.info(f"[DRY-RUN TELEGRAM ALERT]\n{message}")
                sent_count += 1
            else:
                try:
                    url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
                    resp = httpx.post(
                        url,
                        json={
                            "chat_id": self.chat_id,
                            "text": message,
                            "parse_mode": "HTML",
                            "disable_web_page_preview": False,
                        },
                        timeout=10.0,
                    )
                    if resp.status_code == 200:
                        sent_count += 1
                    else:
                        logger.error(f"Telegram API error {resp.status_code}: {resp.text}")
                except Exception as exc:
                    logger.error(f"Failed to dispatch Telegram alert: {exc}")

        return sent_count
