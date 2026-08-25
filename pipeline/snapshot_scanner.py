"""
pipeline/snapshot_scanner.py
──────────────────────────────
Lightweight periodic snapshot scanner for multi-camera, no-zone sites.

Unlike PeriodicScanner (which relies on FrameProcessor's continuous
RTSP + YOLO loop to keep a "latest frame" warm), this connects to each
camera briefly on its own schedule, grabs a single frame, and releases
the connection — no continuous detection pipeline running between
scans. Used for sites where zones haven't been calibrated yet and all
that's wanted is a periodic hazard snapshot per camera.
"""

import datetime
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import cv2

from config.settings import settings
from core.alert_manager import AlertManager
from pipeline.event_saver import save_event

logger = logging.getLogger(__name__)


class SnapshotScanner:
    _ALERT_RISK_LEVELS = {"RED"}

    def __init__(self, site, cameras: list[dict], interval_minutes: int = 60):
        self.site = site
        self.cameras = cameras  # [{"camera_id", "name", "rtsp"}, ...]
        self.interval_minutes = interval_minutes
        self._alert = AlertManager()
        self._scheduler = AsyncIOScheduler()

    def start(self) -> None:
        site_id = self.site.site_config.site_id
        for cam in self.cameras:
            self._scheduler.add_job(
                self._run_scan,
                "interval",
                minutes=self.interval_minutes,
                args=[cam],
                id=f"snapshot_{site_id}_{cam['camera_id']}",
                next_run_time=None,
            )
        self._scheduler.start()
        logger.info(
            f"[{site_id}] Snapshot scanner started — "
            f"{len(self.cameras)} camera(s), every {self.interval_minutes} min"
        )

    def stop(self) -> None:
        self._scheduler.shutdown(wait=False)

    async def _run_scan(self, cam: dict) -> None:
        site_id = self.site.site_config.site_id
        camera_id = cam["camera_id"]

        frame = self._grab_frame(cam["rtsp"])
        if frame is None:
            logger.warning(f"[{site_id}] {camera_id} — snapshot capture failed")
            return

        logger.info(f"[{site_id}] {camera_id} — periodic scan starting")
        try:
            result = await self.site.on_periodic(frame, camera_id=camera_id)
        except Exception as e:
            logger.error(f"[{site_id}] {camera_id} scan error: {e}", exc_info=True)
            return

        if not result:
            logger.info(f"[{site_id}] {camera_id} scan: no hazards found")
            await save_event(
                site_id=site_id, zone_id=camera_id, risk_level="GREEN",
                result={"hazards": []}, snapshot_path=None, alert_status="not_sent",
            )
            return

        risk_level = result.get("risk_level", "YELLOW")
        annotated_frame = result["frame"]
        snapshot_path = self._save_snapshot(annotated_frame, site_id, camera_id, risk_level)

        event_id = await save_event(
            site_id=site_id, zone_id=camera_id, risk_level=risk_level,
            result=result, snapshot_path=snapshot_path,
            alert_status="sent" if risk_level in self._ALERT_RISK_LEVELS else "logged_only",
        )

        if risk_level in self._ALERT_RISK_LEVELS:
            try:
                await self._alert.send_alert(
                    frame=annotated_frame, text=result.get("text", ""),
                    site_id=site_id, zone_id=camera_id, risk_level=risk_level,
                )
                logger.warning(f"[{site_id}] {camera_id} RED alert sent — event_id={event_id}")
            except Exception as e:
                logger.error(f"[{site_id}] {camera_id} Telegram send failed: {e}")
        else:
            logger.info(
                f"[{site_id}] {camera_id} scan: {risk_level} risk — "
                f"logged only (event_id={event_id}), no Telegram sent"
            )

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _grab_frame(rtsp_url: str):
        """Open, warm up (RTSP's first frame is often stale/black), grab, release."""
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        try:
            if not cap.isOpened():
                return None
            cap.read()  # discard first frame — warms up the decoder
            ok, frame = cap.read()
            return frame if ok else None
        finally:
            cap.release()

    @staticmethod
    def _save_snapshot(frame, site_id: str, camera_id: str, risk_level: str):
        snapshot_dir = settings.SNAPSHOT_DIR / site_id
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = snapshot_dir / f"{site_id}_{camera_id}_{risk_level}_{ts}.jpg"
        cv2.imwrite(str(path), frame)
        logger.info(f"Snapshot saved: {path}")
        return path
