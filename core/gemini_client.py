"""
core/gemini_client.py
──────────────────────
Gemini Vision API wrapper.

Features:
- ส่งภาพได้หลายภาพใน 1 call (person crop + full frame)
- Parse JSON response อัตโนมัติ
- Retry on failure
- Timeout handling
"""

import base64
import json
import logging
import re
import time

import cv2
import google.generativeai as genai
import numpy as np

from config.settings import settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """Thin wrapper around Gemini Vision API."""

    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._model = genai.GenerativeModel(settings.GEMINI_MODEL)
        logger.info(f"GeminiClient ready — model={settings.GEMINI_MODEL}")

    # ── Public ────────────────────────────────────────────────────────────────

    def analyze(
        self,
        prompt: str,
        images: list[np.ndarray],
        retries: int | None = None,
    ) -> dict | None:
        """
        Send prompt + images to Gemini, return parsed JSON dict.
        Returns None if failed or uncertain.
        """
        retries = retries or settings.GEMINI_MAX_RETRIES
        parts = [prompt] + [self._encode(img) for img in images]

        for attempt in range(1, retries + 1):
            try:
                response = self._model.generate_content(
                    parts,
                    generation_config=genai.GenerationConfig(
                        temperature=0.1,        # low = more deterministic
                        max_output_tokens=8192,
                    ),
                    request_options={"timeout": settings.GEMINI_TIMEOUT},
                )
                return self._parse_json(response.text)

            except Exception as e:
                logger.warning(f"Gemini attempt {attempt}/{retries} failed: {e}")
                if attempt < retries:
                    time.sleep(1.5 * attempt)

        logger.error("Gemini: all retries exhausted")
        return None

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _encode(frame: np.ndarray) -> dict:
        """Encode numpy BGR frame → Gemini inline image part."""
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
        return {"inline_data": {"mime_type": "image/jpeg", "data": b64}}

    @staticmethod
    def _parse_json(text: str) -> dict | None:
        """
        Extract JSON from Gemini response.
        Handles markdown code fences and plain JSON.
        """
        if not text:
            return None

        # Strip markdown fences if present
        cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", text).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to find JSON block inside text
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass

        logger.warning(f"Gemini: could not parse JSON — raw: {text[:200]}")
        return None
