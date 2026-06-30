"""
api/preview.py
──────────────
MJPEG stream endpoint — เปิดดูใน browser ได้เลย
http://localhost:8000/preview/robot_zone
"""

import logging
import threading
import time

import cv2
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse

logger = logging.getLogger(__name__)

app = FastAPI()

# ── Frame buffer (thread-safe) ────────────────────────────────────────────────
_latest_frames: dict[str, bytes] = {}
_lock = threading.Lock()


def push_frame(site_id: str, frame) -> None:
    """Called by FrameProcessor every frame to update buffer."""
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
    with _lock:
        _latest_frames[site_id] = buf.tobytes()


def _gen_mjpeg(site_id: str):
    """Generator that yields MJPEG frames."""
    while True:
        with _lock:
            frame = _latest_frames.get(site_id)

        if frame:
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        time.sleep(0.05)  # ~20fps max


# ── Routes ────────────────────────────────────────────────────────────────────


@app.get("/preview/{site_id}")
def preview_page(site_id: str):
    """HTML page with live MJPEG embed."""
    html = f"""
    <!DOCTYPE html>
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
    </html>
    """
    return HTMLResponse(html)


@app.get("/stream/{site_id}")
def stream(site_id: str):
    """Raw MJPEG stream."""
    return StreamingResponse(
        _gen_mjpeg(site_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/health")
def health():
    return {"status": "ok", "sites": list(_latest_frames.keys())}
