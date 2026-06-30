"""
pipeline/event_saver.py
────────────────────────
Save Gemini analysis results to PostgreSQL.
Called from frame_processor after Gemini finishes.
"""

import logging
from pathlib import Path

from db.crud import create_alert_log, create_event, create_hazards
from db.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def save_event(
    site_id: str,
    zone_id: str,
    risk_level: str,
    result: dict,
    snapshot_path: Path | None = None,
    person_track_id: int | None = None,
    person_speed: float | None = None,
    alert_status: str = "sent",
) -> int | None:
    """
    Save event + hazards + alert log to DB.
    Returns event ID or None if failed.
    """
    try:
        async with AsyncSessionLocal() as db:
            # Extract situation summary from result text
            situation_th, situation_en = _extract_situation(result)

            event = await create_event(
                db=db,
                site_id=site_id,
                zone_id=zone_id,
                risk_level=risk_level,
                person_track_id=person_track_id,
                person_speed=person_speed,
                situation_summary_th=situation_th,
                situation_summary_en=situation_en,
                snapshot_path=str(snapshot_path) if snapshot_path else None,
            )

            # Save hazards
            hazards = result.get("hazards", [])
            if hazards:
                await create_hazards(db, event.id, hazards)

            # Save alert log
            await create_alert_log(db, event.id, channel="telegram", status=alert_status)

            await db.commit()
            logger.info(f"Event saved: id={event.id} zone={zone_id} hazards={len(hazards)}")
            return event.id

    except Exception as e:
        logger.error(f"DB save failed: {e}", exc_info=True)
        return None


def _extract_situation(result: dict) -> tuple[str | None, str | None]:
    """Extract situation summary from Gemini result."""
    hazards = result.get("hazards", [])

    # Look for situation_summary in result (from prompt_a)
    situation = result.get("situation_summary", {})
    if situation:
        return situation.get("summary_th"), situation.get("summary_en")

    # Fallback: use overall_summary from prompt_b
    overall = result.get("overall_summary", {})
    if overall:
        return overall.get("summary_th"), overall.get("summary_en")

    return None, None