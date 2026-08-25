"""
sites/pellet_mill/site.py
───────────────────────────
Pellet Mill site plugin — v1: hourly snapshot scan only.

No zone polygons defined yet (need real camera footage to calibrate them),
so event_enabled stays false in config.yaml and on_zone_hit() is unused.
pipeline/snapshot_scanner.py grabs one frame per camera every
periodic_interval_minutes and calls on_periodic() — a single Gemini call
per snapshot checking environment hazards + visible PPE together (no
separate per-person crop prompt yet, since ppe_required rules aren't
defined for this site).
"""

import logging
from pathlib import Path

from core.annotator import draw_gemini_hazards
from core.gemini_client import GeminiClient
from sites.base_site import BaseSite
from sites.pellet_mill.prompts.prompt_env import build_prompt_env

logger = logging.getLogger(__name__)


class PelletMillSite(BaseSite):

    def __init__(self, config_path: Path = Path("sites/pellet_mill/config.yaml")):
        super().__init__(config_path)
        self._gemini = GeminiClient()

    # ── Not used yet — no zones defined for this site ──────────────────────────

    async def on_zone_hit(self, frame, zone_result, detection):
        return None

    # ── Hourly snapshot scan ─────────────────────────────────────────────────

    async def on_periodic(self, frame, detection=None, camera_id: str = "") -> dict | None:
        h, w = frame.shape[:2]
        prompt = build_prompt_env(image_wh=(w, h), camera_id=camera_id)
        result = self._gemini.analyze(prompt, images=[frame])

        if not result or not result.get("hazards"):
            return None

        draw_gemini_hazards(frame, result)
        risk_level = self._worst_risk(result["hazards"])

        text_lines = [f"📷 *{camera_id}* — Environment Scan"]
        for i, h_ in enumerate(result["hazards"], 1):
            text_lines.append(f"{i}. {h_.get('reason_th', '')} / {h_.get('reason_en', '')}")

        summary = result.get("overall_summary", {})
        if summary.get("summary_th"):
            text_lines.append(f"\n📋 *Summary*\n{summary['summary_th']}")

        return {
            "hazards": result["hazards"],
            "frame": frame,
            "text": "\n".join(text_lines),
            "situation_summary": summary,
            "risk_level": risk_level,
        }

    # ── Helper ────────────────────────────────────────────────────────────────

    @staticmethod
    def _worst_risk(hazards: list[dict]) -> str:
        order = ["RED", "ORANGE", "YELLOW", "GREEN"]
        for level in order:
            if any(h.get("risk") == level for h in hazards):
                return level
        return "YELLOW"
