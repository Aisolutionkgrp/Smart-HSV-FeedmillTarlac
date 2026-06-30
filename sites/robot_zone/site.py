"""
sites/robot_zone/site.py
─────────────────────────
Robot Zone site plugin.

Logic 1 (event):    person enters zone → analyze immediately
Logic 2 (periodic): every N minutes → scan environment + any person in frame
                     (regardless of zone) — Gemini decides actual risk

bbox คน  → YOLO (แม่น)
bbox อื่น → Gemini Prompt B (สภาพแวดล้อม)
Gemini Prompt A → วิเคราะห์ PPE/behavior เท่านั้น ไม่ขอ bbox
"""

import logging
from pathlib import Path

from core.annotator import draw_gemini_hazards, draw_person_box
from core.detector import DetectionResult, PersonDetection
from core.gemini_client import GeminiClient
from core.zone_manager import ZoneCheckResult
from sites.base_site import BaseSite
from sites.robot_zone.prompts.prompt_env import build_prompt_env
from sites.robot_zone.prompts.prompt_person import build_prompt_person

logger = logging.getLogger(__name__)

RISK_EMOJI = {"RED": "🔴", "ORANGE": "🟠", "YELLOW": "🟡", "GREEN": "🟢"}


class RobotZoneSite(BaseSite):

    def __init__(self, config_path: Path = Path("sites/robot_zone/config.yaml")):
        super().__init__(config_path)
        self._gemini = GeminiClient()

    # ── Logic 1: Event-triggered ──────────────────────────────────────────────

    async def on_zone_hit(
        self,
        frame,
        zone_result: ZoneCheckResult,
        detection: DetectionResult,
    ) -> dict | None:
        """Person entered zone — analyze that specific person + environment."""
        persons = [hit.person for hit in (zone_result.inside_hits or zone_result.hits[:1])]
        zone_context = zone_result.hits[0].zone if zone_result.hits else None

        return await self._run_analysis(
            frame=frame,
            detection=detection,
            persons=persons,
            zone_context=zone_context,
            label_prefix="EVENT",
        )

    # ── Logic 2: Periodic scan ────────────────────────────────────────────────

    async def on_periodic(
        self,
        frame,
        detection: DetectionResult,
    ) -> dict | None:
        """
        Every N minutes — scan environment AND any person visible in frame,
        regardless of which zone (or no zone) they're in.
        Gemini decides actual risk from context (e.g. "not near robot arm = safe").
        """
        # ทุกคนที่ YOLO detect เจอในเฟรม ไม่ว่าจะอยู่ zone ไหน
        persons = detection.persons

        return await self._run_analysis(
            frame=frame,
            detection=detection,
            persons=persons,
            zone_context=None,   # ไม่ผูกกับ zone เฉพาะ ให้ Gemini ประเมินเอง
            label_prefix="PERIODIC",
        )

    # ── Shared analysis logic ────────────────────────────────────────────────

    async def _run_analysis(
        self,
        frame,
        detection: DetectionResult,
        persons: list[PersonDetection],
        zone_context,
        label_prefix: str,
    ) -> dict | None:
        W, H = detection.image_wh
        all_hazards = []
        text_lines = []
        situation = {}

        # ── Prompt A: per person (if any detected) ─────────────────────────
        for person in persons:
            x1, y1, x2, y2 = person.bbox
            pad = 0.15
            pw, ph = x2 - x1, y2 - y1
            cx1 = max(0, x1 - int(pw * pad))
            cy1 = max(0, y1 - int(ph * pad))
            cx2 = min(W, x2 + int(pw * pad))
            cy2 = min(H, y2 + int(ph * pad))
            crop = frame[cy1:cy2, cx1:cx2].copy()
            ch, cw = crop.shape[:2]

            if zone_context:
                yolo_context = (
                    f"YOLO detected person ID={person.track_id} "
                    f"at zone={zone_context.zone_id} risk={zone_context.risk_level} "
                    f"speed={person.speed:.1f}px/frame"
                )
            else:
                yolo_context = (
                    f"YOLO detected person ID={person.track_id} "
                    f"speed={person.speed:.1f}px/frame. "
                    f"This is a periodic scan — assess actual proximity to "
                    f"machinery/hazards from the image itself, not from zone assumption."
                )

            prompt_a = build_prompt_person(
                image_wh=(cw, ch),
                yolo_context=yolo_context,
                ppe_required=self.site_config.ppe_required,
                actor_id=str(person.track_id),
            )

            result_a = self._gemini.analyze(prompt_a, images=[crop, frame])

            if result_a and result_a.get("hazards"):
                worst_risk = self._worst_risk(result_a["hazards"])
                draw_person_box(frame, (x1, y1, x2, y2), person.track_id, worst_risk, person.speed)
                all_hazards.extend(result_a["hazards"])
                logger.info(
                    f"[robot_zone] {label_prefix} Prompt A: {len(result_a['hazards'])} hazards "
                    f"for person {person.track_id}"
                )

                person_situation = result_a.get("situation_summary", {})
                if person_situation.get("summary_th"):
                    situation = person_situation  # keep last for DB
                    text_lines.append(f"⚠️ *สถานการณ์*: {person_situation['summary_th']}")
                    text_lines.append("")

                text_lines.append(f"👤 *Person {person.track_id} — PPE & Behavior*")
                for i, h in enumerate(result_a["hazards"], 1):
                    emoji = RISK_EMOJI.get(h.get("risk", "YELLOW"), "🟡")
                    text_lines.append(
                        f"{emoji} {i}. {h.get('reason_th', '')} / {h.get('reason_en', '')}"
                    )
            elif result_a is not None:
                # Gemini analyzed but found no hazard — person is safe, log it
                logger.info(
                    f"[robot_zone] {label_prefix} Prompt A: person {person.track_id} — no hazard"
                )

        # ── Prompt B: environment (always runs) ────────────────────────────
        prompt_b = build_prompt_env(image_wh=(W, H))
        result_b = self._gemini.analyze(prompt_b, images=[frame])

        if result_b and result_b.get("hazards"):
            draw_gemini_hazards(frame, result_b)
            all_hazards.extend(result_b["hazards"])
            logger.info(f"[robot_zone] {label_prefix} Prompt B: {len(result_b['hazards'])} env hazards")

            text_lines.append(f"\n🏭 *Environment Hazards*")
            for i, h in enumerate(result_b["hazards"], 1):
                emoji = RISK_EMOJI.get(h.get("risk", "YELLOW"), "🟡")
                text_lines.append(
                    f"{emoji} {i}. {h.get('reason_th', '')} / {h.get('reason_en', '')}"
                )

            summary = result_b.get("overall_summary", {})
            if summary.get("summary_th") and not situation:
                situation = summary

            if summary.get("summary_th"):
                text_lines.append(f"\n📋 *Summary*\n{summary['summary_th']}")

        if all_hazards:
            return {
                "hazards": all_hazards,
                "frame": frame,
                "text": "\n".join(text_lines),
                "situation_summary": situation,
                "risk_level": self._worst_risk(all_hazards),
            }

        return None

    # ── Helper ────────────────────────────────────────────────────────────────

    @staticmethod
    def _worst_risk(hazards: list[dict]) -> str:
        order = ["RED", "ORANGE", "YELLOW", "GREEN"]
        for level in order:
            if any(h.get("risk") == level for h in hazards):
                return level
        return "YELLOW"