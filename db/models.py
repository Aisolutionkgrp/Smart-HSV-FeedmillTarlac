"""
db/models.py
─────────────
SQLAlchemy ORM models for safety vision system.
"""

from datetime import datetime
from sqlalchemy import (
    Column, DateTime, Float, ForeignKey,
    Integer, String, Text, func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class SafetyEvent(Base):
    """หลัก — เกิดขึ้นทุกครั้งที่ Gemini trigger"""
    __tablename__ = "safety_events"

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    site_id              = Column(String(50), nullable=False, index=True)
    zone_id              = Column(String(50), nullable=False, index=True)
    risk_level           = Column(String(10), nullable=False)        # RED/ORANGE/YELLOW
    person_track_id      = Column(Integer, nullable=True)            # YOLO track ID
    person_speed         = Column(Float, nullable=True)              # px/frame
    situation_summary_th = Column(Text, nullable=True)
    situation_summary_en = Column(Text, nullable=True)
    snapshot_path        = Column(String(500), nullable=True)        # relative path
    triggered_at         = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    duration_seconds     = Column(Float, nullable=True)

    # Relationships
    hazards              = relationship("SafetyHazard", back_populates="event", cascade="all, delete-orphan")
    corrective_actions   = relationship("CorrectiveAction", back_populates="event", cascade="all, delete-orphan")
    alert_logs           = relationship("AlertLog", back_populates="event", cascade="all, delete-orphan")


class SafetyHazard(Base):
    """hazard แต่ละรายการจาก Gemini"""
    __tablename__ = "safety_hazards"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    event_id    = Column(Integer, ForeignKey("safety_events.id"), nullable=False, index=True)
    label       = Column(String(100), nullable=False)
    risk        = Column(String(10), nullable=False)
    confidence  = Column(Float, nullable=True)
    reason_th   = Column(Text, nullable=True)
    reason_en   = Column(Text, nullable=True)
    actor_id    = Column(String(20), nullable=True)     # person track ID ถ้ามี
    source      = Column(String(50), nullable=True)     # prompt_a / prompt_b

    event       = relationship("SafetyEvent", back_populates="hazards")


class CorrectiveAction(Base):
    """เตรียมไว้รอ AI Agent — ยังไม่ implement"""
    __tablename__ = "corrective_actions"

    id                       = Column(Integer, primary_key=True, autoincrement=True)
    event_id                 = Column(Integer, ForeignKey("safety_events.id"), nullable=False, index=True)
    recommended_action_th    = Column(Text, nullable=True)
    recommended_action_en    = Column(Text, nullable=True)
    action_type              = Column(String(20), nullable=True)     # immediate/short_term/long_term
    status                   = Column(String(20), default="pending") # pending/acknowledged/resolved
    resolved_at              = Column(DateTime(timezone=True), nullable=True)
    resolved_by              = Column(String(100), nullable=True)
    created_at               = Column(DateTime(timezone=True), server_default=func.now())

    event                    = relationship("SafetyEvent", back_populates="corrective_actions")


class AlertLog(Base):
    """log การส่ง alert"""
    __tablename__ = "alert_logs"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    event_id    = Column(Integer, ForeignKey("safety_events.id"), nullable=False, index=True)
    channel     = Column(String(20), nullable=False)    # telegram
    status      = Column(String(20), nullable=False)    # sent / failed
    sent_at     = Column(DateTime(timezone=True), server_default=func.now())
    error_msg   = Column(Text, nullable=True)

    event       = relationship("SafetyEvent", back_populates="alert_logs")
