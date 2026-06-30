"""
core/stream_reader.py
─────────────────────
RTSP → raw frames via GStreamer (HW decode on Jetson Orin).
Falls back to plain OpenCV if GStreamer pipeline fails.

Usage:
    reader = StreamReader(rtsp_url="rtsp://...", site_id="robot_zone")
    for frame in reader.frames():
        process(frame)
"""

import cv2
import time
import logging
import os
from dataclasses import dataclass, field
from typing import Generator, Optional

logger = logging.getLogger(__name__)


@dataclass
class FrameMeta:
    site_id: str
    camera_url: str
    frame_index: int
    timestamp: float = field(default_factory=time.time)
    width: int = 0
    height: int = 0


class StreamReader:
    """
    Wraps OpenCV VideoCapture with:
    - GStreamer HW decode pipeline (Jetson Orin)
    - Auto-reconnect on drop
    - Frame skip (process every N frames)
    """

    # GStreamer pipeline for Jetson Orin Nano (NVDEC hardware decode)
    _GSTREAMER_TEMPLATE = (
        "rtspsrc location={url} latency=100 protocols=tcp ! "
        "rtph264depay ! h264parse ! nvv4l2decoder ! "
        "nvvidconv ! video/x-raw,format=BGRx ! "
        "videoconvert ! video/x-raw,format=BGR ! "
        "appsink drop=1"
    )

    def __init__(
        self,
        rtsp_url: str,
        site_id: str,
        frame_skip: int = 3,
        reconnect_delay: float = 5.0,
        use_gstreamer: bool = True,
    ):
        self.rtsp_url = rtsp_url
        self.site_id = site_id
        self.frame_skip = frame_skip
        self.reconnect_delay = reconnect_delay
        self.use_gstreamer = use_gstreamer

        self._cap: Optional[cv2.VideoCapture] = None
        self._frame_index: int = 0
        self._running: bool = False

    # ── Public ────────────────────────────────────────────────────────────────

    def frames(self) -> Generator[tuple[object, FrameMeta], None, None]:
        """
        Yields (frame_bgr, FrameMeta) for every processed frame.
        Handles reconnect automatically.
        """
        self._running = True
        logger.info(f"[{self.site_id}] StreamReader starting → {self.rtsp_url}")

        while self._running:
            self._cap = self._open()
            if self._cap is None:
                logger.warning(f"[{self.site_id}] Connect failed — retry in {self.reconnect_delay}s")
                time.sleep(self.reconnect_delay)
                continue

            logger.info(f"[{self.site_id}] Stream connected [OK]")

            while self._running:
                ok, frame = self._cap.read()
                if not ok:
                    logger.warning(f"[{self.site_id}] Frame read failed — reconnecting…")
                    break  # outer loop will reconnect

                self._frame_index += 1

                # ── Frame skip ───────────────────────────────────────────────
                if self._frame_index % self.frame_skip != 0:
                    continue

                h, w = frame.shape[:2]
                meta = FrameMeta(
                    site_id=self.site_id,
                    camera_url=self.rtsp_url,
                    frame_index=self._frame_index,
                    timestamp=time.time(),
                    width=w,
                    height=h,
                )
                yield frame, meta

            # Clean up broken capture
            self._release()
            if self._running:
                logger.info(f"[{self.site_id}] Reconnecting in {self.reconnect_delay}s…")
                time.sleep(self.reconnect_delay)

    def stop(self) -> None:
        self._running = False
        self._release()
        logger.info(f"[{self.site_id}] StreamReader stopped.")

    # ── Private ───────────────────────────────────────────────────────────────

    def _open(self) -> Optional[cv2.VideoCapture]:
        """Try GStreamer first, fall back to plain OpenCV."""
        if self.use_gstreamer:
            cap = self._open_gstreamer()
            if cap is not None:
                return cap
            logger.warning(f"[{self.site_id}] GStreamer failed - falling back to OpenCV")

        return self._open_opencv()

    def _open_gstreamer(self) -> Optional[cv2.VideoCapture]:
        pipeline = self._GSTREAMER_TEMPLATE.format(url=self.rtsp_url)
        try:
            cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            if cap.isOpened():
                return cap
            cap.release()
        except Exception as e:
            logger.debug(f"[{self.site_id}] GStreamer error: {e}")
        return None

    def _open_opencv(self) -> Optional[cv2.VideoCapture]:
        try:
            # Force TCP + suppress HEVC warnings + larger buffer
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                "rtsp_transport;tcp|"
                "timeout;10000000|"
                "buffer_size;1048576|"
                "max_delay;500000|"
                "reorder_queue_size;0"
            )
            os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "quiet"
            cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 5)
            if cap.isOpened():
                return cap
            cap.release()
        except Exception as e:
            logger.debug(f"[{self.site_id}] OpenCV error: {e}")
        return None

    def _release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._running