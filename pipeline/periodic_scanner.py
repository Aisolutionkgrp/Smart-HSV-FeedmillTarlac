"""
pipeline/periodic_scanner.py
"""

import logging

import numpy as np
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core.alert_manager import AlertManager
from core.detector import DetectionResult
from pipeline.event_saver import save_event

logger = logging.getLogger(__name__)


class PeriodicScanner:
    _ALERT_RISK_LEVELS = {"RED"}

    def __init__(self, site, interval_minutes: int = 10):
        self.site = site
        self.interval_minutes = interval_minutes
        self._alert = AlertManager()
        self._scheduler = AsyncIOScheduler()
        self._latest_frame = None
        self._latest_detection = None

    def update_frame(self, frame, detection):
        self._latest_frame = frame
        self._latest_detection = detection

    def start(self) -> None:
        self._scheduler.add_job(
            self._run_scan,
            "interval",
            minutes=self.interval_minutes,
            id=f"periodic_{self.site.site_config.site_id}",
            next_run_time=None,
        )
        self._scheduler.start()
        logger.info(f"[{self.site.site_config.site_id}] Periodic scanner started — every {self.interval_minutes} min")

    def stop(self) -> None:
        self._scheduler.shutdown(wait=False)

    async def _run_scan(self) -> None:
        site_id = self.site.site_config.site_id

        if self._latest_frame is None or self._latest_detection is None:
            logger.warning(f"[{site_id}] Periodic scan skipped — no frame available")
            return

        frame = self._latest_frame.copy()
        detection = self._latest_detection

        logger.info(f"[{site_id}] Periodic scan starting — frame={detection.frame_index}")

        try:
            result = await self.site.on_periodic(frame, detection)
        except Exception as e:
            logger.error(f"[{site_id}] Periodic scan error: {e}", exc_info=True)
            return

        if not result:
            logger.info(f"[{site_id}] Periodic scan: no hazards found")
            await save_event(
                site_id=site_id, zone_id="periodic_scan", risk_level="GREEN",
                result={"hazards": []}, snapshot_path=None, alert_status="not_sent",
            )
            return

        risk_level = result.get("risk_level", "YELLOW")
        annotated_frame = result["frame"]

        snapshot_path = self._save_snapshot(annotated_frame, site_id, risk_level, detection.frame_index)

        event_id = await save_event(
            site_id=site_id, zone_id="periodic_scan", risk_level=risk_level,
            result=result, snapshot_path=snapshot_path,
            alert_status="sent" if risk_level in self._ALERT_RISK_LEVELS else "logged_only",
        )

        if risk_level in self._ALERT_RISK_LEVELS:
            try:
                await self._alert.send_alert(
                    frame=annotated_frame, text=result.get("text", ""),
                    site_id=site_id, zone_id="periodic_scan", risk_level=risk_level,
                )
                logger.warning(f"[{site_id}] Periodic RED alert sent — event_id={event_id}")
            except Exception as e:
                logger.error(f"[{site_id}] Periodic Telegram send failed: {e}")
        else:
            logger.info(f"[{site_id}] Periodic scan: {risk_level} risk — logged only (event_id={event_id}), no Telegram sent")

    @staticmethod
    def _save_snapshot(frame, site_id, risk_level, frame_index):
        import datetime
        from config.settings import settings
        import cv2

        snapshot_dir = settings.SNAPSHOT_DIR / site_id
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = snapshot_dir / f"{site_id}_periodic_{risk_level}_{ts}.jpg"
        cv2.imwrite(str(path), frame)
        logger.info(f"Periodic snapshot saved: {path}")
        return path
