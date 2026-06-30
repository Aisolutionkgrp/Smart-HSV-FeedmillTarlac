"""
core/zone_manager.py
─────────────────────
Polygon-based zone detection with velocity prediction.

Features:
  - Check if person center is inside a zone polygon
  - Predict if person WILL enter zone within N frames (prediction trigger)
  - Return ZoneStatus per person per frame
"""

import logging
import numpy as np
from dataclasses import dataclass, field

from shapely.geometry import Point, Polygon

from core.detector import PersonDetection

logger = logging.getLogger(__name__)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class ZoneConfig:
    zone_id: str
    name: str
    polygon: list[tuple[int, int]]      # pixel coordinates [[x,y], ...]
    risk_level: str                     # RED / ORANGE / YELLOW
    predict_frames: int = 15            # how many frames ahead to predict


@dataclass
class ZoneHit:
    zone: ZoneConfig
    person: PersonDetection
    is_inside: bool                     # currently inside
    is_predicted: bool                  # predicted to enter soon
    predicted_frames: int = 0           # frames until entry (if predicted)


@dataclass
class ZoneCheckResult:
    hits: list[ZoneHit] = field(default_factory=list)

    @property
    def any_hit(self) -> bool:
        return len(self.hits) > 0

    @property
    def inside_hits(self) -> list[ZoneHit]:
        return [h for h in self.hits if h.is_inside]

    @property
    def predicted_hits(self) -> list[ZoneHit]:
        return [h for h in self.hits if h.is_predicted and not h.is_inside]


# ── Zone Manager ──────────────────────────────────────────────────────────────

class ZoneManager:
    """
    Manages polygon zones for a single site/camera.
    Supports both inside-check and velocity-based prediction.
    """

    # Minimum speed (px/frame) to attempt prediction
    _MIN_SPEED_FOR_PREDICTION = 1.5

    def __init__(self, zones: list[ZoneConfig]):
        self._zones = zones
        # Pre-build shapely polygons for fast point-in-polygon
        self._polys: dict[str, Polygon] = {
            z.zone_id: Polygon(z.polygon) for z in zones
        }
        logger.info(f"ZoneManager loaded {len(zones)} zones: "
                    f"{[z.zone_id for z in zones]}")

    # ── Public ────────────────────────────────────────────────────────────────

    def check(self, persons: list[PersonDetection]) -> ZoneCheckResult:
        """
        Check all persons against all zones.
        Returns ZoneCheckResult with every (person, zone) hit.
        """
        result = ZoneCheckResult()

        for person in persons:
            for zone in self._zones:
                poly = self._polys[zone.zone_id]
                pt = Point(person.center)

                is_inside = poly.contains(pt)
                is_predicted, pred_frames = False, 0

                if not is_inside:
                    is_predicted, pred_frames = self._predict(
                        person, poly, zone.predict_frames
                    )

                if is_inside or is_predicted:
                    result.hits.append(ZoneHit(
                        zone=zone,
                        person=person,
                        is_inside=is_inside,
                        is_predicted=is_predicted,
                        predicted_frames=pred_frames,
                    ))
                    logger.debug(
                        f"Zone hit: person={person.track_id} "
                        f"zone={zone.zone_id} "
                        f"inside={is_inside} predicted={is_predicted}"
                    )

        return result

    def draw_zones(self, frame: np.ndarray) -> np.ndarray:
        """Draw zone polygons — tactical HUD style."""
        import cv2

        COLOR_MAP = {
            "RED":    (40,  40,  220),
            "ORANGE": (30, 140, 255),
            "YELLOW": (20, 200, 220),
            "GREEN":  (80, 200,  80),
        }

        overlay = frame.copy()

        for zone in self._zones:
            pts = np.array(zone.polygon, dtype=np.int32)
            color = COLOR_MAP.get(zone.risk_level, (180, 180, 180))

            # Very subtle fill
            cv2.fillPoly(overlay, [pts], color)
            cv2.addWeighted(overlay, 0.06, frame, 0.94, 0, frame)
            overlay = frame.copy()

            # Dashed-style border — draw segments
            n = len(zone.polygon)
            for i in range(n):
                p1 = tuple(zone.polygon[i])
                p2 = tuple(zone.polygon[(i + 1) % n])
                cv2.line(frame, p1, p2, color, 1, cv2.LINE_AA)

            # Zone label — small pill style
            cx = int(np.mean([p[0] for p in zone.polygon]))
            cy = int(np.mean([p[1] for p in zone.polygon]))

            label = zone.name
            tw, th = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)[0]
            pad = 5
            cv2.rectangle(frame,
                (cx - tw//2 - pad, cy - th - pad),
                (cx + tw//2 + pad, cy + pad),
                (10, 10, 10), -1)
            cv2.rectangle(frame,
                (cx - tw//2 - pad, cy - th - pad),
                (cx + tw//2 + pad, cy + pad),
                color, 1)
            cv2.putText(frame, label,
                (cx - tw//2, cy),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA)

        return frame

    # ── Private ───────────────────────────────────────────────────────────────

    def _predict(
        self,
        person: PersonDetection,
        poly: Polygon,
        max_frames: int,
    ) -> tuple[bool, int]:
        """
        Walk velocity vector forward up to max_frames.
        Return (True, frames_until_entry) if person will enter polygon.
        """
        if person.speed < self._MIN_SPEED_FOR_PREDICTION:
            return False, 0

        vx, vy = person.velocity
        cx, cy = person.center

        for f in range(1, max_frames + 1):
            future_pt = Point(cx + vx * f, cy + vy * f)
            if poly.contains(future_pt):
                logger.debug(
                    f"Prediction: person={person.track_id} will enter "
                    f"zone in {f} frames"
                )
                return True, f

        return False, 0