"""
sites/base_site.py
───────────────────
Abstract base class for all sites.
Each site (robot_zone, pellet_mill, loading_zone…) subclasses this,
overrides `on_zone_hit()` and `on_periodic()` with its own logic.

Loading a site:
    site = RobotZoneSite()
    zone_result = site.zone_manager.check(persons)
    await site.on_zone_hit(frame, zone_result, detection)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging
import os
from pathlib import Path
import re

import yaml

from core.detector import DetectionResult
from core.zone_manager import ZoneConfig, ZoneManager

logger = logging.getLogger(__name__)


@dataclass
class SiteConfig:
    site_id: str
    site_name: str
    camera_rtsp: str
    resolution: tuple[int, int]
    frame_skip: int
    logic: dict
    ppe_required: list[str]
    alert: dict
    raw: dict  # full yaml dict for site-specific extras


def _resolve_env(value: str) -> str:
    """
    แทนที่ ${VAR_NAME} ใน string ด้วยค่าจาก environment variable.
    ถ้าไม่เจอ env var → คืน placeholder เดิม แล้ว log warning
    """

    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        val = os.environ.get(var_name, "")
        if not val:
            logger.warning(f"Env var '{var_name}' not set — check your .env file")
        return val

    return re.sub(r"\$\{(\w+)\}", replacer, value)


class BaseSite(ABC):
    """
    Base class for all site plugins.
    Subclasses must implement on_zone_hit() and on_periodic().
    """

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.site_config, self.zone_manager = self._load(config_path)
        logger.info(
            f"Site loaded: {self.site_config.site_id} "
            f"({len(self.zone_manager._zones)} zones) "
            f"rtsp={'✓ set' if self.site_config.camera_rtsp else '✗ MISSING'}"
        )

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    async def on_zone_hit(self, frame, zone_result, detection: DetectionResult):
        """Called when a person enters or is predicted to enter a zone."""
        ...

    @abstractmethod
    async def on_periodic(self, frame, detection: DetectionResult):
        """Called every periodic_interval_minutes for environment scan."""
        ...

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _load(config_path: Path) -> tuple[SiteConfig, ZoneManager]:
        with open(config_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        # Resolve ${ENV_VAR} in camera_rtsp
        camera_rtsp = _resolve_env(raw.get("camera_rtsp", ""))

        site_cfg = SiteConfig(
            site_id=raw["site_id"],
            site_name=raw["site_name"],
            camera_rtsp=camera_rtsp,
            resolution=tuple(raw["resolution"]),
            frame_skip=raw.get("frame_skip", 3),
            logic=raw.get("logic", {}),
            ppe_required=raw.get("ppe_required", []),
            alert=raw.get("alert", {}),
            raw=raw,
        )

        zones = [
            ZoneConfig(
                zone_id=z["zone_id"],
                name=z["name"],
                polygon=[tuple(p) for p in z["polygon"]],
                risk_level=z["risk_level"],
                predict_frames=z.get("predict_frames", 15),
            )
            for z in raw.get("zones", [])
        ]

        return site_cfg, ZoneManager(zones)
