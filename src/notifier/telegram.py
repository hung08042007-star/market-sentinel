"""Telegram Notifier with Markdown formatting and Dry-Run support."""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from src.domain.models import DeltaEvent, PriceDelta

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        dry_run: bool = False,
    ):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.dry_run = dry_run or not (bot_token and chat_id)

    def format_delta_message(self, delta: PriceDelta) -> str:
        """Format a single PriceDelta into a readable Telegram notification."""
        if delta.event == DeltaEvent.PRICE_DROP:
            emoji = "📉 🔥 [GIẢM GIÁ]"
        elif delta.event == DeltaEvent.PRICE_HIKE:
            emoji = "📈 ⚠️ [TĂNG GIÁ]"
        elif delta.event == DeltaEvent.RESTOCK:
            emoji = "📦 ✨ [HÀNG VỀ KHO]"
        elif delta.event == DeltaEvent.OUT_OF_STOCK:
            emoji = "❌ ⚠️ [HẾT HÀNG]"
        else:
            emoji = "ℹ️ [CẬP NHẬT]"

        lines = [
            f"<b>{emoji}</b>",
            f"<b>Sản phẩm:</b> {delta.product_title}",
            f"<b>Mã SKU:</b> <code>{delta.sku}</code>",
            f"<b>Giá cũ:</b> {delta.old_price:,.2f} {delta.currency}",
            f"<b>Giá mới:</b> {delta.new_price:,.2f} {delta.currency} ({delta.percentage_change:+.2f}%)",
            f"<b>Link:</b> <a href=\"{delta.url}\">Xem sản phẩm</a>",
        ]
        return "\n".join(lines)

    def notify_deltas(self, deltas: list[PriceDelta]) -> int:
        """Send notification for all significant deltas. Returns count sent."""
        if not deltas:
            return 0

        sent_count = 0
        for delta in deltas:
            # We notify on price drops, restocks, or price hikes
            if delta.event not in (DeltaEvent.PRICE_DROP, DeltaEvent.RESTOCK, DeltaEvent.PRICE_HIKE):
                continue

            message = self.format_delta_message(delta)
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
