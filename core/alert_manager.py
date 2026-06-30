"""
core/alert_manager.py
──────────────────────
Telegram alert manager.

ส่ง:
- ภาพ annotated
- text summary (situation + PPE + environment)
- metadata (zone, risk, timestamp)
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from config.settings import settings

logger = logging.getLogger(__name__)


class AlertManager:
    """Send safety alerts via Telegram."""

    def __init__(self):
        from telegram import Bot
        self._bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        self._chat_id = settings.TELEGRAM_CHAT_ID
        logger.info("AlertManager ready — Telegram connected")

    # ── Public ────────────────────────────────────────────────────────────────

    async def send_alert(
        self,
        frame: np.ndarray,
        text: str,
        site_id: str,
        zone_id: str,
        risk_level: str,
        snapshot_path: Path | None = None,
    ) -> None:
        """
        Send annotated image + text summary to Telegram.
        """
        try:
            header = self._build_header(site_id, zone_id, risk_level)
            full_text = f"{header}\n\n{text}"

            # Encode frame to bytes
            img_bytes = self._encode_frame(frame)

            await self._bot.send_photo(
                chat_id=self._chat_id,
                photo=img_bytes,
                caption=full_text,
                parse_mode="Markdown",
            )
            logger.info(f"Telegram alert sent — zone={zone_id} risk={risk_level}")

        except Exception as e:
            logger.error(f"Telegram send failed: {e}")

    async def send_text(self, text: str) -> None:
        """Send text-only message."""
        try:
            await self._bot.send_message(
                chat_id=self._chat_id,
                text=text,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Telegram send_text failed: {e}")

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _build_header(site_id: str, zone_id: str, risk_level: str) -> str:
        risk_emoji = {"RED": "🔴", "ORANGE": "🟠", "YELLOW": "🟡"}.get(risk_level, "⚠️")
        ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        return (
            f"{risk_emoji} *Safety Alert*\n"
            f"📍 `{site_id}` → `{zone_id}`\n"
            f"🕐 {ts}"
        )

    @staticmethod
    def _encode_frame(frame: np.ndarray) -> bytes:
        """Encode BGR numpy frame to JPEG bytes."""
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return buf.tobytes()
