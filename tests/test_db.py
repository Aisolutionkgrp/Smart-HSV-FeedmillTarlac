"""
tests/test_db.py
─────────────────
เทส save event ลง PostgreSQL โดยตรง

รัน: uv run python tests/test_db.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from db.database import init_db
from pipeline.event_saver import save_event


async def main():
    print("Initializing DB...")
    await init_db()
    print("DB initialized [OK]")

    print("\nSaving test event...")
    event_id = await save_event(
        site_id="robot_zone",
        zone_id="robot_arm_zone",
        risk_level="RED",
        result={
            "hazards": [
                {
                    "label": "ppe_missing_helmet",
                    "risk": "ORANGE",
                    "confidence": 0.9,
                    "reason_th": "ไม่สวมหมวกนิรภัย",
                    "reason_en": "No helmet detected",
                    "actor_id": "1",
                    "source": "prompt_a",
                },
                {
                    "label": "person_within_robot_swing_radius",
                    "risk": "RED",
                    "confidence": 0.95,
                    "reason_th": "อยู่ในรัศมีแขนกล",
                    "reason_en": "Within robot swing radius",
                    "actor_id": "1",
                    "source": "prompt_a",
                },
            ],
            "situation_summary": {
                "summary_th": "พบพนักงานเข้าใกล้แขนกล ABB โดยไม่สวม PPE ครบ",
                "summary_en": "Worker detected near ABB robot arm without full PPE",
            },
        },
        snapshot_path=Path("snapshots/robot_zone/test.jpg"),
        person_track_id=1,
        person_speed=5.5,
        alert_status="sent",
    )

    if event_id:
        print(f"Event saved! ID={event_id}")
        print(f"\nCheck: http://localhost:8000/api/events")
        print(f"Check: http://localhost:8000/api/events/{event_id}")
    else:
        print("Save failed!")


if __name__ == "__main__":
    asyncio.run(main())