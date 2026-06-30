"""
core/alert_manager.py
──────────────────────
Telegram alert manager.

ส่งเป็น 2 ข้อความแยกกัน:
1. รูปภาพ + header สั้นๆ (caption)
2. ข้อความรายละเอียดเต็ม (situation + PPE + environment)

เหตุผล: Telegram photo caption จำกัดที่ 1024 ตัวอักษร
แต่ text message ธรรมดาจำกัดที่ 4096 ตัวอักษร — ส่งแยกได้เนื้อหาครบไม่ตัด
"""

import logging
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from config.settings import settings

logger = logging.getLogger(__name__)


class AlertManager:
    """Send safety alerts via Telegram — image first, then full detail text."""

    _TEXT_LIMIT = 4096   # Telegram send_message hard limit

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
        Send annotated image first (with short header caption),
        then send the full detail text as a separate message.
        """
        header = self._build_header(site_id, zone_id, risk_level)

        # ── 1. Send image with short caption ────────────────────────────────
        try:
            img_bytes = self._encode_frame(frame)
            await self._bot.send_photo(
                chat_id=self._chat_id,
                photo=img_bytes,
                caption=header,
                parse_mode="Markdown",
            )
            logger.info(f"Telegram photo sent — zone={zone_id} risk={risk_level}")
        except Exception as e:
            logger.error(f"Telegram photo send failed: {e}")

        # ── 2. Send full detail text (chunked if needed) ───────────────────
        if text:
            try:
                for chunk in self._chunk_text(text, self._TEXT_LIMIT):
                    await self._bot.send_message(
                        chat_id=self._chat_id,
                        text=chunk,
                        parse_mode="Markdown",
                    )
                logger.info(f"Telegram detail text sent — zone={zone_id}")
            except Exception as e:
                logger.error(f"Telegram text send failed: {e}")

    async def send_text(self, text: str) -> None:
        """Send text-only message (chunked if needed)."""
        try:
            for chunk in self._chunk_text(text, self._TEXT_LIMIT):
                await self._bot.send_message(
                    chat_id=self._chat_id,
                    text=chunk,
                    parse_mode="Markdown",
                )
        except Exception as e:
            logger.error(f"Telegram send_text failed: {e}")

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _chunk_text(text: str, limit: int) -> list[str]:
        """Split long text into Telegram-safe chunks, breaking on newlines."""
        if len(text) <= limit:
            return [text]

        chunks = []
        current = ""
        for line in text.split("\n"):
            # +1 for the newline that will be added back
            if len(current) + len(line) + 1 > limit:
                if current:
                    chunks.append(current)
                current = line
            else:
                current = f"{current}\n{line}" if current else line
        if current:
            chunks.append(current)
        return chunks

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