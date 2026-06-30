"""
tests/test_alert.py
────────────────────
เทส Telegram alert โดยตรง ไม่ต้องรอคนเข้า zone

รัน: uv run python tests/test_alert.py --image snapshots/robot_zone/preview_latest.jpg
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

import cv2

from core.alert_manager import AlertManager


async def main(image_path: str):
    img = cv2.imread(image_path)
    if img is None:
        print(f"Cannot read: {image_path}")
        sys.exit(1)

    alert = AlertManager()

    fake_text = (
        "⚠️ *สถานการณ์*: พบพนักงานเข้าใกล้แขนกล ABB ที่กำลังทำงาน "
        "ไม่สวม PPE ครบ อาจเกิดอันตรายจากการถูกกระแทก\n\n"
        "👤 *Person 5 — PPE & Behavior*\n"
        "🔴 1. อยู่ในรัศมีแขนกล / Within robot swing radius\n"
        "🟠 2. ไม่สวมหมวกนิรภัย / No helmet\n"
        "🟠 3. ไม่สวมรองเท้านิรภัย / No safety shoes\n"
        "🟡 4. ไม่สวมเสื้อสะท้อนแสง / No reflective vest\n\n"
        "🏭 *Environment Hazards*\n"
        "🟠 1. เศษอาหารสัตว์บนพื้น / Feed material on floor\n"
        "🟡 2. การจัดการไม่เรียบร้อย / Poor housekeeping"
    )

    print("Sending Telegram alert...")
    await alert.send_alert(
        frame=img,
        text=fake_text,
        site_id="robot_zone",
        zone_id="robot_arm_zone",
        risk_level="RED",
    )
    print("Done! Check your Telegram group.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    asyncio.run(main(args.image))
