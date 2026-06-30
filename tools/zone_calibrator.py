"""
tools/zone_calibrator.py
─────────────────────────
Click วาด zone polygon บนภาพ แล้ว print พิกัดใส่ config.yaml

รัน: uv run python tools/zone_calibrator.py --image path/to/image.jpg
Controls:
  Left click  — เพิ่มจุด
  Right click — จบ zone ปัจจุบัน
  'n'         — zone ใหม่
  'u'         — undo จุดล่าสุด
  'c'         — clear zone ปัจจุบัน
  's'         — save และ print YAML
  'q'         — quit
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

ZONE_COLORS = [
    (0, 0, 255),    # RED
    (0, 128, 255),  # ORANGE
    (0, 220, 220),  # YELLOW
    (0, 255, 0),    # GREEN
    (255, 0, 255),  # MAGENTA
]
ZONE_NAMES_DEFAULT = [
    "robot_arm_zone",
    "conveyor_zone",
    "suspended_load_zone",
    "zone_4",
    "zone_5",
]


class ZoneCalibrator:
    def __init__(self, image_path: str):
        self.img_orig = cv2.imread(image_path)
        if self.img_orig is None:
            print(f"Cannot read: {image_path}")
            sys.exit(1)

        self.H, self.W = self.img_orig.shape[:2]
        print(f"Image: {self.W}x{self.H}")

        self.zones: list[list[tuple[int, int]]] = [[]]  # list of polygons
        self.current_zone = 0
        self.window = "Zone Calibrator"

        cv2.namedWindow(self.window, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window, min(self.W, 1400), min(self.H, 800))
        cv2.setMouseCallback(self.window, self._on_mouse)

    def run(self):
        print("\nControls:")
        print("  Left click  = add point")
        print("  Right click = finish current zone")
        print("  'n' = new zone")
        print("  'u' = undo last point")
        print("  'c' = clear current zone")
        print("  's' = save + print YAML")
        print("  'q' = quit\n")

        while True:
            frame = self._draw()
            cv2.imshow(self.window, frame)
            key = cv2.waitKey(20) & 0xFF

            if key == ord("q"):
                break
            elif key == ord("n"):
                self.zones.append([])
                self.current_zone = len(self.zones) - 1
                print(f"New zone {self.current_zone + 1}")
            elif key == ord("u"):
                if self.zones[self.current_zone]:
                    self.zones[self.current_zone].pop()
            elif key == ord("c"):
                self.zones[self.current_zone] = []
            elif key == ord("s"):
                self._print_yaml()

        cv2.destroyAllWindows()

    def _on_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.zones[self.current_zone].append((x, y))
        elif event == cv2.EVENT_RBUTTONDOWN:
            pts = self.zones[self.current_zone]
            if len(pts) >= 3:
                print(f"Zone {self.current_zone + 1} closed ({len(pts)} points)")

    def _draw(self) -> np.ndarray:
        frame = self.img_orig.copy()

        for zi, pts in enumerate(self.zones):
            if not pts:
                continue
            color = ZONE_COLORS[zi % len(ZONE_COLORS)]
            arr = np.array(pts, dtype=np.int32)

            # Fill semi-transparent
            overlay = frame.copy()
            if len(pts) >= 3:
                cv2.fillPoly(overlay, [arr], color)
                cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)
                cv2.polylines(frame, [arr], True, color, 2)
            else:
                cv2.polylines(frame, [arr], False, color, 2)

            # Draw points
            for pt in pts:
                cv2.circle(frame, pt, 5, color, -1)

            # Zone label
            if pts:
                cx = sum(p[0] for p in pts) // len(pts)
                cy = sum(p[1] for p in pts) // len(pts)
                name = ZONE_NAMES_DEFAULT[zi] if zi < len(ZONE_NAMES_DEFAULT) else f"zone_{zi+1}"
                cv2.putText(frame, name, (cx - 40, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Current zone indicator
        color = ZONE_COLORS[self.current_zone % len(ZONE_COLORS)]
        cv2.putText(frame, f"Drawing: Zone {self.current_zone + 1}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(frame, f"Points: {len(self.zones[self.current_zone])}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        return frame

    def _print_yaml(self):
        print("\n" + "=" * 50)
        print("# Copy this into config.yaml → zones:")
        print("=" * 50)
        for zi, pts in enumerate(self.zones):
            if len(pts) < 3:
                continue
            name = ZONE_NAMES_DEFAULT[zi] if zi < len(ZONE_NAMES_DEFAULT) else f"zone_{zi+1}"
            risk = ["RED", "ORANGE", "RED", "ORANGE", "YELLOW"][zi % 5]
            print(f"""
  - zone_id: "{name}"
    name: "{'เขตแขนกล ABB' if zi == 0 else 'เขตสายพาน' if zi == 1 else 'เขตใต้ของแขวน'}"
    risk_level: "{risk}"
    predict_frames: 20
    polygon:""")
            for x, y in pts:
                print(f"      - [{x}, {y}]")
        print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, help="Path to image")
    args = parser.parse_args()

    cal = ZoneCalibrator(args.image)
    cal.run()
