"""
core/cooldown_manager.py
─────────────────────────
Zone-based cooldown manager backed by Redis.

ทำไมนับต่อ zone ไม่ใช่ต่อ person ID:
- ByteTrack อาจ reset ID เมื่อ track หาย
- คนเดิมกลับมาจะได้ ID ใหม่ → cooldown ไม่ทำงาน
- Zone-based: ถ้า zone นั้นยังมีคนอยู่ → ไม่ยิง Gemini ซ้ำ

Key format: cooldown:{site_id}:{zone_id}
TTL: cooldown_seconds (default 60)
"""

import logging

import redis

from config.settings import settings

logger = logging.getLogger(__name__)


class CooldownManager:
    """
    Redis-backed zone cooldown.
    Thread-safe — Redis operations are atomic.
    """

    _KEY_PREFIX = "cooldown"

    def __init__(self):
        self._client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=3,
        )
        self._verify_connection()

    # ── Public ────────────────────────────────────────────────────────────────

    def is_allowed(self, site_id: str, zone_id: str, cooldown_seconds: int = 60) -> bool:
        """
        Returns True if Gemini call is allowed (not in cooldown).
        Automatically sets cooldown if allowed.
        """
        key = self._key(site_id, zone_id)

        # SET key EX ttl NX → set only if not exists (atomic)
        result = self._client.set(key, "1", ex=cooldown_seconds, nx=True)

        if result:
            logger.info(f"[cooldown] ALLOWED {site_id}:{zone_id} — cooldown {cooldown_seconds}s set")
            return True

        ttl = self._client.ttl(key)
        logger.debug(f"[cooldown] BLOCKED {site_id}:{zone_id} — {ttl}s remaining")
        return False

    def reset(self, site_id: str, zone_id: str) -> None:
        """Force reset cooldown for a zone (e.g. person left zone)."""
        key = self._key(site_id, zone_id)
        self._client.delete(key)
        logger.debug(f"[cooldown] RESET {site_id}:{zone_id}")

    def ttl(self, site_id: str, zone_id: str) -> int:
        """Return remaining cooldown seconds (-1 if not set, -2 if key missing)."""
        return self._client.ttl(self._key(site_id, zone_id))

    def status(self, site_id: str) -> dict[str, int]:
        """Return cooldown status for all zones of a site."""
        pattern = f"{self._KEY_PREFIX}:{site_id}:*"
        keys = self._client.keys(pattern)
        return {k.split(":")[-1]: self._client.ttl(k) for k in keys}

    # ── Private ───────────────────────────────────────────────────────────────

    def _key(self, site_id: str, zone_id: str) -> str:
        return f"{self._KEY_PREFIX}:{site_id}:{zone_id}"

    def _verify_connection(self) -> None:
        try:
            self._client.ping()
            logger.info("CooldownManager connected to Redis [OK]")
        except redis.ConnectionError as e:
            logger.error(f"Redis connection failed: {e}")
            raise
