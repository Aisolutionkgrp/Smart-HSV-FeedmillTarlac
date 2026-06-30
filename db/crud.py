"""
db/crud.py
───────────
CRUD operations for safety vision system.
"""

import logging
from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import AlertLog, CorrectiveAction, SafetyEvent, SafetyHazard

logger = logging.getLogger(__name__)


# ── Create ────────────────────────────────────────────────────────────────────

async def create_event(
    db: AsyncSession,
    site_id: str,
    zone_id: str,
    risk_level: str,
    person_track_id: int | None = None,
    person_speed: float | None = None,
    situation_summary_th: str | None = None,
    situation_summary_en: str | None = None,
    snapshot_path: str | None = None,
) -> SafetyEvent:
    event = SafetyEvent(
        site_id=site_id,
        zone_id=zone_id,
        risk_level=risk_level,
        person_track_id=person_track_id,
        person_speed=person_speed,
        situation_summary_th=situation_summary_th,
        situation_summary_en=situation_summary_en,
        snapshot_path=snapshot_path,
    )
    db.add(event)
    await db.flush()  # get ID without commit
    return event


async def create_hazards(
    db: AsyncSession,
    event_id: int,
    hazards: list[dict],
) -> list[SafetyHazard]:
    rows = []
    for h in hazards:
        row = SafetyHazard(
            event_id=event_id,
            label=h.get("label", "unknown"),
            risk=h.get("risk", "YELLOW"),
            confidence=h.get("confidence"),
            reason_th=h.get("reason_th"),
            reason_en=h.get("reason_en"),
            actor_id=h.get("actor_id"),
            source=h.get("source"),
        )
        db.add(row)
        rows.append(row)
    return rows


async def create_alert_log(
    db: AsyncSession,
    event_id: int,
    channel: str,
    status: str,
    error_msg: str | None = None,
) -> AlertLog:
    log = AlertLog(
        event_id=event_id,
        channel=channel,
        status=status,
        error_msg=error_msg,
    )
    db.add(log)
    return log


# ── Read ──────────────────────────────────────────────────────────────────────

async def get_events(
    db: AsyncSession,
    site_id: str | None = None,
    zone_id: str | None = None,
    risk_level: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[SafetyEvent]:
    stmt = (
        select(SafetyEvent)
        .options(selectinload(SafetyEvent.hazards))
        .order_by(desc(SafetyEvent.triggered_at))
        .limit(limit)
        .offset(offset)
    )
    if site_id:
        stmt = stmt.where(SafetyEvent.site_id == site_id)
    if zone_id:
        stmt = stmt.where(SafetyEvent.zone_id == zone_id)
    if risk_level:
        stmt = stmt.where(SafetyEvent.risk_level == risk_level)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_event_by_id(
    db: AsyncSession,
    event_id: int,
) -> SafetyEvent | None:
    stmt = (
        select(SafetyEvent)
        .where(SafetyEvent.id == event_id)
        .options(
            selectinload(SafetyEvent.hazards),
            selectinload(SafetyEvent.alert_logs),
            selectinload(SafetyEvent.corrective_actions),
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_stats(db: AsyncSession, site_id: str | None = None) -> dict:
    """Daily stats for dashboard."""
    from sqlalchemy import cast, Date

    base = select(SafetyEvent)
    if site_id:
        base = base.where(SafetyEvent.site_id == site_id)

    # Total events
    total = await db.scalar(select(func.count()).select_from(base.subquery()))

    # By risk level
    risk_stmt = (
        select(SafetyEvent.risk_level, func.count().label("count"))
        .group_by(SafetyEvent.risk_level)
    )
    if site_id:
        risk_stmt = risk_stmt.where(SafetyEvent.site_id == site_id)
    risk_result = await db.execute(risk_stmt)
    by_risk = {row.risk_level: row.count for row in risk_result}

    # Today count
    today_stmt = (
        select(func.count())
        .select_from(SafetyEvent)
        .where(cast(SafetyEvent.triggered_at, Date) == func.current_date())
    )
    if site_id:
        today_stmt = today_stmt.where(SafetyEvent.site_id == site_id)
    today_count = await db.scalar(today_stmt)

    return {
        "total_events": total,
        "today_events": today_count,
        "by_risk": by_risk,
    }