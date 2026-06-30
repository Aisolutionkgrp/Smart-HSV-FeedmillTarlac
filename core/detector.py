"""
core/detector.py
────────────────
YOLOv8s-pose wrapper with ByteTrack.

Returns structured DetectionResult per frame:
  - persons: list of PersonDetection (bbox, track_id, keypoints, velocity)
  - raw_result: ultralytics Results object (for downstream use)

Velocity / direction is estimated from keypoint displacement between frames.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np
from ultralytics import YOLO

from config.settings import settings


logger = logging.getLogger(__name__)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class Keypoints:
    """COCO 17-keypoint format (subset we care about)."""
    nose:            tuple[float, float] | None = None
    left_shoulder:   tuple[float, float] | None = None
    right_shoulder:  tuple[float, float] | None = None
    left_hip:        tuple[float, float] | None = None
    right_hip:       tuple[float, float] | None = None
    left_knee:       tuple[float, float] | None = None
    right_knee:      tuple[float, float] | None = None
    left_ankle:      tuple[float, float] | None = None
    right_ankle:     tuple[float, float] | None = None


@dataclass
class PersonDetection:
    track_id: int
    bbox: tuple[int, int, int, int]             # x1, y1, x2, y2 (pixels)
    confidence: float
    keypoints: Keypoints
    center: tuple[float, float]                 # cx, cy
    velocity: tuple[float, float] = (0.0, 0.0) # vx, vy pixels/frame
    speed: float = 0.0                          # magnitude pixels/frame
    heading_deg: float = 0.0                    # 0=right, 90=down, 180=left, 270=up


@dataclass
class DetectionResult:
    frame_index: int
    timestamp: float
    image_wh: tuple[int, int]
    persons: list[PersonDetection] = field(default_factory=list)
    raw_result: object = None                   # ultralytics Results


# ── Detector ──────────────────────────────────────────────────────────────────

class Detector:
    """
    Thin wrapper around YOLOv8s-pose + ByteTrack.
    Adds velocity estimation from track history.
    """

    _KP_MAP = {
        "nose": 0,
        "left_shoulder": 5,  "right_shoulder": 6,
        "left_hip": 11,      "right_hip": 12,
        "left_knee": 13,     "right_knee": 14,
        "left_ankle": 15,    "right_ankle": 16,
    }
    _KP_CONF_THRESHOLD = 0.4

    def __init__(self):
        logger.info(f"Loading YOLO model: {settings.YOLO_MODEL}")
        self._model = YOLO(settings.YOLO_MODEL)
        logger.info("YOLO model loaded [OK]")

        self._history: dict[int, list[tuple[float, float]]] = defaultdict(list)
        self._history_len = 5

    # ── Filter constants ──────────────────────────────────────────────────────
    # คนจริงต้องมี bbox สูงอย่างน้อย 60px และ aspect ratio ไม่แปลก
    _MIN_HEIGHT_PX = 60         # กรอง object เล็กๆ เช่น มอเตอร์
    _MAX_ASPECT_RATIO = 4.0     # กรอง object แนวนอนยาว (ไม่ใช่คน)
    _MIN_KEYPOINTS = 3          # ต้องมี keypoint อย่างน้อย 3 จุด

    # ── Public ────────────────────────────────────────────────────────────────

    def detect(self, frame: np.ndarray, frame_meta) -> DetectionResult:
        h, w = frame.shape[:2]

        results = self._model.track(
            source=frame,
            conf=settings.YOLO_CONF,
            iou=settings.YOLO_IOU,
            device=settings.YOLO_DEVICE,
            imgsz=settings.YOLO_IMGSZ,
            persist=True,
            tracker="bytetrack.yaml",
            classes=[0],
            verbose=False,
        )

        persons: list[PersonDetection] = []

        if results and results[0].boxes is not None:
            result = results[0]
            boxes = result.boxes
            kps_data = result.keypoints

            for i, box in enumerate(boxes):
                if box.id is None:
                    continue
                track_id = int(box.id.item())

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                conf = float(box.conf[0].item())
                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0

                # ── False positive filter ─────────────────────────────────
                bbox_h = y2 - y1
                bbox_w = x2 - x1
                if bbox_h < self._MIN_HEIGHT_PX:
                    logger.debug(f"Filtered: track={track_id} too small h={bbox_h}px")
                    continue
                if bbox_w > 0 and (bbox_h / bbox_w) > self._MAX_ASPECT_RATIO:
                    logger.debug(f"Filtered: track={track_id} bad aspect ratio")
                    continue

                keypoints = Keypoints()
                if kps_data is not None and i < len(kps_data.xy):
                    raw_kp = kps_data.xy[i].tolist()
                    raw_conf = kps_data.conf[i].tolist() if kps_data.conf is not None else []
                    for name, idx in self._KP_MAP.items():
                        if idx < len(raw_kp):
                            kp_conf = raw_conf[idx] if idx < len(raw_conf) else 1.0
                            if kp_conf >= self._KP_CONF_THRESHOLD:
                                setattr(keypoints, name, tuple(raw_kp[idx]))

                # Require minimum keypoints for human validation
                kp_count = sum(1 for attr in vars(keypoints).values() if attr is not None)
                if kp_count < self._MIN_KEYPOINTS:
                    logger.debug(f"Filtered: track={track_id} insufficient keypoints={kp_count}")
                    continue

                # Structural sanity check: human anatomy is vertically ordered.
                # shoulder must be above hip, hip must be above knee, etc.
                # Machinery/objects often have keypoints scattered without
                # this consistent top-to-bottom ordering.
                if not self._is_anatomically_plausible(keypoints):
                    logger.debug(f"Filtered: track={track_id} failed anatomy check")
                    continue

                vx, vy, speed, heading = self._update_velocity(track_id, cx, cy)

                persons.append(PersonDetection(
                    track_id=track_id,
                    bbox=(x1, y1, x2, y2),
                    confidence=conf,
                    keypoints=keypoints,
                    center=(cx, cy),
                    velocity=(vx, vy),
                    speed=speed,
                    heading_deg=heading,
                ))

        self._prune_history(active_ids={p.track_id for p in persons})

        return DetectionResult(
            frame_index=frame_meta.frame_index,
            timestamp=frame_meta.timestamp,
            image_wh=(w, h),
            persons=persons,
            raw_result=results[0] if results else None,
        )

    # ── Velocity helpers ──────────────────────────────────────────────────────

    def _update_velocity(
        self, track_id: int, cx: float, cy: float
    ) -> tuple[float, float, float, float]:
        history = self._history[track_id]
        history.append((cx, cy))
        if len(history) > self._history_len:
            history.pop(0)

        if len(history) < 2:
            return 0.0, 0.0, 0.0, 0.0

        vx_sum, vy_sum, w_sum = 0.0, 0.0, 0.0
        for j in range(1, len(history)):
            dx = history[j][0] - history[j - 1][0]
            dy = history[j][1] - history[j - 1][1]
            weight = float(j)
            vx_sum += dx * weight
            vy_sum += dy * weight
            w_sum += weight

        vx = vx_sum / w_sum
        vy = vy_sum / w_sum
        speed = float(np.hypot(vx, vy))
        heading = float(np.degrees(np.arctan2(vy, vx)) % 360)
        return vx, vy, speed, heading

    @staticmethod
    def _is_anatomically_plausible(kp: Keypoints) -> bool:
        """
        Check that detected keypoints follow human top-to-bottom anatomy.
        Rejects detections where e.g. "knee" keypoint is above "shoulder" —
        a strong signal the YOLO model latched onto machinery, not a person.
        Uses Y coordinate (smaller Y = higher up in image).
        """
        # Average left/right pairs where both exist, else use whichever is present
        def avg_y(*points) -> float | None:
            ys = [p[1] for p in points if p is not None]
            return sum(ys) / len(ys) if ys else None

        shoulder_y = avg_y(kp.left_shoulder, kp.right_shoulder)
        hip_y = avg_y(kp.left_hip, kp.right_hip)
        knee_y = avg_y(kp.left_knee, kp.right_knee)
        ankle_y = avg_y(kp.left_ankle, kp.right_ankle)
        nose_y = kp.nose[1] if kp.nose else None

        # Margin allows for natural pose variation (bending, crouching)
        margin = 5.0

        # nose should be above (smaller y) shoulder, if both visible
        if nose_y is not None and shoulder_y is not None:
            if nose_y > shoulder_y + margin:
                return False

        # shoulder should be above hip
        if shoulder_y is not None and hip_y is not None:
            if shoulder_y > hip_y + margin:
                return False

        # hip should be above knee
        if hip_y is not None and knee_y is not None:
            if hip_y > knee_y + margin:
                return False

        # knee should be above ankle
        if knee_y is not None and ankle_y is not None:
            if knee_y > ankle_y + margin:
                return False

        return True

    def _prune_history(self, active_ids: set[int]) -> None:
        stale = [tid for tid in self._history if tid not in active_ids]
        for tid in stale:
            del self._history[tid]