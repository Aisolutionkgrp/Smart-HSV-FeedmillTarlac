"""
pipeline/frame_processor.py
────────────────────────────
Phase 1 pipeline: RTSP → YOLO → Zone check → annotate → display/save.

Wires together:
  StreamReader → Detector → ZoneManager → visualize

Gemini integration added in Phase 3.
"""

import asyncio
import logging
import time

import cv2
import numpy as np

from api.preview import push_frame
from config.settings import settings
from core.alert_manager import AlertManager
from core.cooldown_manager import CooldownManager
from pipeline.event_saver import save_event
from core.detector import Detector, DetectionResult, PersonDetection
from core.zone_manager import ZoneCheckResult, ZoneHit
from sites.base_site import BaseSite
from core.stream_reader import StreamReader

logger = logging.getLogger(__name__)


class FrameProcessor:
    """
    Main processing loop for a single site/camera.
    Phase 1: detection + zone check + visualization only.
    """

    # Annotation colors
    _COLOR_PERSON_SAFE     = (0, 255, 0)      # green
    _COLOR_PERSON_INSIDE   = (0, 0, 255)      # red
    _COLOR_PERSON_PREDICT  = (0, 165, 255)    # orange
    _COLOR_SKELETON        = (255, 255, 0)    # yellow
    _FONT = cv2.FONT_HERSHEY_SIMPLEX

    def __init__(self, site: BaseSite, show_preview: bool = False):
        self.site = site
        self.show_preview = show_preview

        cfg = site.site_config
        self._reader = StreamReader(
            rtsp_url=cfg.camera_rtsp,
            site_id=cfg.site_id,
            frame_skip=cfg.frame_skip,
            use_gstreamer=True,
        )
        self._detector = Detector()
        self._zone_manager = site.zone_manager

        self._cooldown = CooldownManager()
        self._last_snapshot_path = None
        self._alert = AlertManager()
        self._snapshot_dir = settings.SNAPSHOT_DIR / cfg.site_id
        self._snapshot_dir.mkdir(parents=True, exist_ok=True)

        # FPS tracking
        self._fps_counter = 0
        self._fps_time = time.time()
        self._fps_display = 0.0

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Blocking main loop. Run in a thread or process."""
        site_id = self.site.site_config.site_id
        logger.info(f"[{site_id}] FrameProcessor starting...")

        for frame, meta in self._reader.frames():
            try:
                self._process_frame(frame, meta)
            except Exception as e:
                logger.error(f"[{site_id}] Frame processing error: {e}", exc_info=True)

        logger.info(f"[{site_id}] FrameProcessor stopped.")

    def stop(self) -> None:
        self._reader.stop()

    # ── Per-frame ─────────────────────────────────────────────────────────────

    def _process_frame(self, frame: np.ndarray, meta) -> None:
        # 1. Detect + track
        detection: DetectionResult = self._detector.detect(frame, meta)

        # 2. Zone check
        zone_result: ZoneCheckResult = self._zone_manager.check(detection.persons)

        # 3. Annotate frame
        annotated = self._annotate(frame.copy(), detection, zone_result)

        # 4. Update FPS counter
        self._update_fps(annotated)

        # 5. Push to web preview + save to disk every 30 frames
        push_frame(self.site.site_config.site_id, annotated)
        if self.show_preview and meta.frame_index % 30 == 0:
            preview_path = self._snapshot_dir / "preview_latest.jpg"
            cv2.imwrite(str(preview_path), annotated)

        # 6. Cooldown check + trigger site logic
        if zone_result.any_hit:
            self._handle_hits(zone_result, frame, detection, meta)

    # ── Annotation ────────────────────────────────────────────────────────────

    def _annotate(
        self,
        frame: np.ndarray,
        detection: DetectionResult,
        zone_result: ZoneCheckResult,
    ) -> np.ndarray:
        # Draw zones first (background layer)
        frame = self._zone_manager.draw_zones(frame)

        # Build lookup: track_id → list of ZoneHit
        hit_map: dict[int, list[ZoneHit]] = {}
        for hit in zone_result.hits:
            hit_map.setdefault(hit.person.track_id, []).append(hit)

        # Draw each person
        for person in detection.persons:
            hits = hit_map.get(person.track_id, [])
            frame = self._draw_person(frame, person, hits)

        # Stats overlay
        self._draw_stats(frame, detection, zone_result)

        return frame

    def _draw_person(
        self,
        frame: np.ndarray,
        person: PersonDetection,
        hits: list[ZoneHit],
    ) -> np.ndarray:
        x1, y1, x2, y2 = person.bbox

        # Choose color by status
        if any(h.is_inside for h in hits):
            color = self._COLOR_PERSON_INSIDE
            status = "! IN ZONE"
        elif hits:  # predicted
            color = self._COLOR_PERSON_PREDICT
            frames_until = min(h.predicted_frames for h in hits if h.is_predicted)
            status = f"> ZONE in {frames_until}f"
        else:
            color = self._COLOR_PERSON_SAFE
            status = "OK"

        # Bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # Label
        label = f"[{person.track_id}] {status} ({person.confidence:.2f})"
        cv2.putText(frame, label, (x1, y1 - 8), self._FONT, 0.5, color, 2)

        # Velocity arrow from center
        if person.speed > 1.5:
            cx, cy = int(person.center[0]), int(person.center[1])
            vx, vy = person.velocity
            scale = 8.0
            ex, ey = int(cx + vx * scale), int(cy + vy * scale)
            cv2.arrowedLine(frame, (cx, cy), (ex, ey), (255, 255, 0), 2, tipLength=0.3)

        # Skeleton dots (key joints)
        self._draw_skeleton(frame, person)

        return frame

    def _draw_skeleton(self, frame: np.ndarray, person: PersonDetection) -> None:
        kp = person.keypoints
        joints = [
            kp.nose, kp.left_shoulder, kp.right_shoulder,
            kp.left_hip, kp.right_hip,
            kp.left_knee, kp.right_knee,
            kp.left_ankle, kp.right_ankle,
        ]
        for joint in joints:
            if joint is not None:
                cv2.circle(frame, (int(joint[0]), int(joint[1])), 4,
                           self._COLOR_SKELETON, -1)

        # Skeleton lines: shoulder-hip, hip-knee, knee-ankle
        pairs = [
            (kp.left_shoulder, kp.left_hip),
            (kp.right_shoulder, kp.right_hip),
            (kp.left_hip, kp.left_knee),
            (kp.right_hip, kp.right_knee),
            (kp.left_knee, kp.left_ankle),
            (kp.right_knee, kp.right_ankle),
            (kp.left_shoulder, kp.right_shoulder),
            (kp.left_hip, kp.right_hip),
        ]
        for a, b in pairs:
            if a and b:
                cv2.line(frame,
                         (int(a[0]), int(a[1])),
                         (int(b[0]), int(b[1])),
                         self._COLOR_SKELETON, 1)

    def _draw_stats(
        self,
        frame: np.ndarray,
        detection: DetectionResult,
        zone_result: ZoneCheckResult,
    ) -> None:
        lines = [
            f"FPS: {self._fps_display:.1f}",
            f"Persons: {len(detection.persons)}",
            f"Zone hits: {len(zone_result.hits)}",
            f"Frame: {detection.frame_index}",
        ]
        for i, line in enumerate(lines):
            cv2.putText(frame, line, (10, 25 + i * 22),
                        self._FONT, 0.6, (255, 255, 255), 2)

    # ── FPS ───────────────────────────────────────────────────────────────────

    def _update_fps(self, frame: np.ndarray) -> None:
        self._fps_counter += 1
        elapsed = time.time() - self._fps_time
        if elapsed >= 1.0:
            self._fps_display = self._fps_counter / elapsed
            self._fps_counter = 0
            self._fps_time = time.time()

    # ── Logging ───────────────────────────────────────────────────────────────

    def _handle_hits(
        self,
        zone_result: ZoneCheckResult,
        frame: np.ndarray,
        detection: DetectionResult,
        meta,
    ) -> None:
        """Check cooldown per zone then trigger Gemini via site.on_zone_hit()."""
        site_id = self.site.site_config.site_id
        cooldown_sec = self.site.site_config.logic.get("cooldown_seconds", 60)

        triggered_zones: set[str] = set()
        for hit in zone_result.hits:
            zone_id = hit.zone.zone_id
            if zone_id in triggered_zones:
                continue

            if self._cooldown.is_allowed(site_id, zone_id, cooldown_sec):
                triggered_zones.add(zone_id)
                logger.warning(
                    f"[{site_id}] TRIGGER zone={zone_id} "
                    f"risk={hit.zone.risk_level} "
                    f"person={hit.person.track_id}"
                )
                # Run Gemini analysis in background (non-blocking)
                asyncio.get_event_loop().run_until_complete(
                    self._run_gemini(frame.copy(), zone_result, detection)
                )
            else:
                ttl = self._cooldown.ttl(site_id, zone_id)
                logger.debug(f"[{site_id}] COOLDOWN zone={zone_id} — {ttl}s left")

        self._log_hits(zone_result, meta)

    async def _run_gemini(
        self,
        frame: np.ndarray,
        zone_result: ZoneCheckResult,
        detection: DetectionResult,
    ) -> None:
        """Call site.on_zone_hit() and save annotated snapshot."""
        try:
            result = await self.site.on_zone_hit(frame, zone_result, detection)
            if result and result.get("frame") is not None:
                _hit = zone_result.hits[0] if zone_result.hits else None
                self._save_snapshot(
                    result["frame"], detection,
                    zone_id=_hit.zone.zone_id if _hit else "unknown",
                    risk_level=_hit.zone.risk_level if _hit else "UNKNOWN",
                )
                push_frame(self.site.site_config.site_id, result["frame"])
                # Print text summary to log
                if result.get("text"):
                    sep = "=" * 50
                    logger.info("\n" + sep + "\n" + result["text"] + "\n" + sep)
        except Exception as e:
            logger.error(f"Gemini analysis error: {e}", exc_info=True)

    def _save_snapshot(
        self,
        frame: np.ndarray,
        detection: DetectionResult,
        zone_id: str = "unknown",
        risk_level: str = "UNKNOWN",
    ) -> None:
        """Save annotated frame to disk."""
        import datetime
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        site_id = self.site.site_config.site_id
        filename = f"{site_id}_{zone_id}_{risk_level}_{ts}.jpg"
        path = self._snapshot_dir / filename
        cv2.imwrite(str(path), frame)
        self._last_snapshot_path = path
        logger.info(f"Snapshot saved: {path}")

    def _log_hits(self, zone_result: ZoneCheckResult, meta) -> None:
        for hit in zone_result.hits:
            tag = "INSIDE" if hit.is_inside else f"PREDICTED({hit.predicted_frames}f)"
            logger.warning(
                f"[{meta.site_id}] Person {hit.person.track_id} "
                f"— zone={hit.zone.zone_id} risk={hit.zone.risk_level} "
                f"status={tag} speed={hit.person.speed:.1f}px/f"
            )