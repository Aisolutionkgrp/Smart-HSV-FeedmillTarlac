"""
api/main.py
────────────
FastAPI app — combines preview stream + REST API
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.preview import _gen_mjpeg, push_frame  # noqa: F401
from db.crud import get_event_by_id, get_events, get_stats
from db.database import get_session, init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("FastAPI started")
    yield
    logger.info("FastAPI shutdown")


app = FastAPI(title="Safety Vision API", version="1.0.0", lifespan=lifespan)


# ── Preview (MJPEG stream) ────────────────────────────────────────────────────

@app.get("/preview/{site_id}", response_class=HTMLResponse)
def preview_page(site_id: str):
    html = f"""<!DOCTYPE html>
    <html>
    <head>
        <title>Safety Vision — {site_id}</title>
        <style>
            body {{ margin: 0; background: #111; display: flex;
                   flex-direction: column; align-items: center;
                   font-family: monospace; color: #0f0; }}
            h2 {{ margin: 10px; }}
            img {{ max-width: 100%; border: 2px solid #0f0; }}
        </style>
    </head>
    <body>
        <h2>Safety Vision — {site_id}</h2>
        <img src="/stream/{site_id}" />
    </body>
    </html>"""
    return HTMLResponse(html)


@app.get("/stream/{site_id}")
def stream(site_id: str):
    return StreamingResponse(
        _gen_mjpeg(site_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


# ── Events API ────────────────────────────────────────────────────────────────

@app.get("/api/events")
async def list_events(
    site_id: str | None = None,
    zone_id: str | None = None,
    risk_level: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
):
    events = await get_events(db, site_id=site_id, zone_id=zone_id,
                               risk_level=risk_level, limit=limit, offset=offset)
    return [_serialize_event(e) for e in events]


@app.get("/api/events/{event_id}")
async def get_event(event_id: int, db: AsyncSession = Depends(get_session)):
    event = await get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return _serialize_event(event, full=True)


@app.get("/api/events/{event_id}/image")
async def get_event_image(event_id: int, db: AsyncSession = Depends(get_session)):
    event = await get_event_by_id(db, event_id)
    if not event or not event.snapshot_path:
        raise HTTPException(status_code=404, detail="Image not found")
    path = Path(event.snapshot_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")
    return FileResponse(path, media_type="image/jpeg")


@app.get("/api/stats")
async def stats(site_id: str | None = None, db: AsyncSession = Depends(get_session)):
    return await get_stats(db, site_id=site_id)


@app.get("/health")
def health():
    return {"status": "ok"}


# ── Serializer ────────────────────────────────────────────────────────────────

def _serialize_event(event, full: bool = False) -> dict:
    data = {
        "id": event.id,
        "site_id": event.site_id,
        "zone_id": event.zone_id,
        "risk_level": event.risk_level,
        "person_track_id": event.person_track_id,
        "person_speed": event.person_speed,
        "situation_summary_th": event.situation_summary_th,
        "situation_summary_en": event.situation_summary_en,
        "snapshot_path": event.snapshot_path,
        "triggered_at": event.triggered_at.isoformat() if event.triggered_at else None,
        "hazard_count": len(event.hazards) if event.hazards else 0,
    }
    if full:
        data["hazards"] = [
            {
                "label": h.label,
                "risk": h.risk,
                "confidence": h.confidence,
                "reason_th": h.reason_th,
                "reason_en": h.reason_en,
                "actor_id": h.actor_id,
                "source": h.source,
            }
            for h in (event.hazards or [])
        ]
        data["alert_logs"] = [
            {"channel": a.channel, "status": a.status, "sent_at": a.sent_at.isoformat()}
            for a in (event.alert_logs or [])
        ]
    return data