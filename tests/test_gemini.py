"""
tests/test_gemini.py
──────────────────────
เทส Gemini โดยตรงด้วยภาพนิ่ง ไม่ต้องมีกล้อง

รัน: uv run python tests/test_gemini.py --image path/to/image.jpg
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

import cv2

from core.gemini_client import GeminiClient
from sites.robot_zone.prompts.prompt_env import build_prompt_env
from sites.robot_zone.prompts.prompt_person import build_prompt_person


def test_with_image(image_path: str):
    img = cv2.imread(image_path)
    if img is None:
        print(f"Cannot read image: {image_path}")
        sys.exit(1)

    H, W = img.shape[:2]
    print(f"\nImage: {W}x{H}")
    print("=" * 50)

    client = GeminiClient()

    # Test Prompt B (environment) — ไม่ต้องมีคน
    print("\n[Prompt B] Environment scan...")
    prompt_b = build_prompt_env(image_wh=(W, H))
    result_b = client.analyze(prompt_b, images=[img])

    if result_b:
        hazards = result_b.get("hazards", [])
        print(f"Hazards found: {len(hazards)}")
        for h in hazards:
            print(f"  - [{h.get('risk')}] {h.get('label')}: {h.get('reason_en')}")
        print(f"\nFull JSON:\n{json.dumps(result_b, indent=2, ensure_ascii=False)}")
    else:
        print("No result from Gemini")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, help="Path to test image")
    args = parser.parse_args()
    test_with_image(args.image)
