"""
tests/test_cooldown.py
───────────────────────
เทส CooldownManager โดยตรง ไม่ต้องมีกล้อง/RTSP

รัน: uv run python tests/test_cooldown.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from core.cooldown_manager import CooldownManager


def test_cooldown():
    cm = CooldownManager()
    site = "robot_zone"
    zone = "robot_arm_zone"

    print("\n=== CooldownManager Test ===\n")

    # 1. ครั้งแรก — ควร ALLOWED
    result = cm.is_allowed(site, zone, cooldown_seconds=5)
    print(f"[1] First call   → {'ALLOWED ✓' if result else 'BLOCKED ✗'}")
    assert result, "First call should be ALLOWED"

    # 2. ครั้งที่สอง ทันที — ควร BLOCKED
    result = cm.is_allowed(site, zone, cooldown_seconds=5)
    print(f"[2] Immediate    → {'BLOCKED ✓' if not result else 'ALLOWED ✗'}")
    assert not result, "Second call should be BLOCKED"

    # 3. ดู TTL
    ttl = cm.ttl(site, zone)
    print(f"[3] TTL          → {ttl}s remaining")
    assert ttl > 0

    # 4. รอให้ cooldown หมด
    print(f"[4] Waiting 5s for cooldown to expire...")
    time.sleep(6)

    result = cm.is_allowed(site, zone, cooldown_seconds=5)
    print(f"[5] After expire → {'ALLOWED ✓' if result else 'BLOCKED ✗'}")
    assert result, "After expiry should be ALLOWED"

    # 5. เทส reset
    cm.is_allowed(site, "conveyor_zone", cooldown_seconds=60)
    cm.reset(site, "conveyor_zone")
    result = cm.is_allowed(site, "conveyor_zone", cooldown_seconds=60)
    print(f"[6] After reset  → {'ALLOWED ✓' if result else 'BLOCKED ✗'}")
    assert result, "After reset should be ALLOWED"

    # 6. เทส status
    status = cm.status(site)
    print(f"[7] Status       → {status}")

    print("\n=== All tests passed! ===\n")


if __name__ == "__main__":
    test_cooldown()
