"""
core/annotator.py
──────────────────
Draw Gemini JSON hazard results onto a frame.
Style: Tactical HUD / Industrial Safety — premium look
"""

import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Risk level colors (BGR) — desaturated professional palette
RISK_COLORS = {
    "RED":    (40,  40,  220),   # deep red
    "ORANGE": (30, 140, 255),    # amber-orange
    "YELLOW": (20, 200, 220),    # cyan-yellow
    "GREEN":  (80, 200,  80),    # muted green
}

# Semi-transparent fill alpha per risk
RISK_ALPHA = {
    "RED": 0.12,
    "ORANGE": 0.08,
    "YELLOW": 0.06,
    "GREEN": 0.05,
}

FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_MONO = cv2.FONT_HERSHEY_PLAIN


def draw_gemini_hazards(
    frame: np.ndarray,
    gemini_result: dict,
    offset_xy: tuple[int, int] = (0, 0),
) -> np.ndarray:
    hazards = gemini_result.get("hazards", [])
    if not hazards:
        return frame

    h, w = frame.shape[:2]
    ox, oy = offset_xy

    for i, hazard in enumerate(hazards):
        bbox = hazard.get("bbox")
        if not bbox or len(bbox) != 4:
            continue

        risk = hazard.get("risk", "YELLOW")
        label = hazard.get("label", "unknown")
        reason = hazard.get("reason_en", "")
        confidence = hazard.get("confidence", 0.0)
        color = RISK_COLORS.get(risk, RISK_COLORS["YELLOW"])

        x1, y1, x2, y2 = _resolve_bbox(bbox, w, h, ox, oy)
        if x1 >= x2 or y1 >= y2:
            continue

        # Semi-transparent fill
        _draw_filled_rect(frame, x1, y1, x2, y2, color, RISK_ALPHA.get(risk, 0.08))

        # Corner bracket style border (tactical HUD look)
        _draw_corner_brackets(frame, x1, y1, x2, y2, color, risk)

        # Hazard index badge (top-left corner)
        _draw_badge(frame, i + 1, x1, y1, color)

        # Label panel
        label_clean = label.replace("_", " ")
        conf_text = f"{confidence:.0%}"
        _draw_label_panel(frame, label_clean, conf_text, reason, x1, y1, x2, color, risk)

    return frame


def draw_person_box(
    frame: np.ndarray,
    bbox: tuple[int, int, int, int],
    track_id: int,
    risk_level: str,
    speed: float = 0.0,
) -> np.ndarray:
    """Draw YOLO person bbox with tactical HUD style."""
    x1, y1, x2, y2 = bbox
    color = RISK_COLORS.get(risk_level, RISK_COLORS["YELLOW"])

    # Semi-transparent fill
    _draw_filled_rect(frame, x1, y1, x2, y2, color, 0.10)

    # Corner brackets — thicker for person
    _draw_corner_brackets(frame, x1, y1, x2, y2, color, risk_level, thickness=2)

    # Person ID tag (top-center)
    tag = f"P{track_id} | {risk_level}"
    tw, th = cv2.getTextSize(tag, FONT, 0.5, 1)[0]
    cx = (x1 + x2) // 2
    tx = cx - tw // 2

    # Tag background
    pad = 4
    cv2.rectangle(frame, (tx - pad, y1 - th - pad * 2), (tx + tw + pad, y1), (10, 10, 10), -1)
    cv2.rectangle(frame, (tx - pad, y1 - th - pad * 2), (tx + tw + pad, y1), color, 1)
    cv2.putText(frame, tag, (tx, y1 - pad), FONT, 0.5, color, 1, cv2.LINE_AA)

    # Speed indicator (bottom-right if moving)
    if speed > 2.0:
        spd_text = f"{speed:.1f} px/f"
        cv2.putText(frame, spd_text, (x2 - 60, y2 - 6), FONT, 0.38,
                    (180, 180, 180), 1, cv2.LINE_AA)

    return frame


def crop_person(
    frame: np.ndarray,
    bbox: tuple[int, int, int, int],
    padding: float = 0.15,
) -> tuple[np.ndarray, tuple[int, int]]:
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = bbox
    pad_x = int((x2 - x1) * padding)
    pad_y = int((y2 - y1) * padding)
    cx1 = max(0, x1 - pad_x)
    cy1 = max(0, y1 - pad_y)
    cx2 = min(w, x2 + pad_x)
    cy2 = min(h, y2 + pad_y)
    return frame[cy1:cy2, cx1:cx2].copy(), (cx1, cy1)


# ── Drawing helpers ───────────────────────────────────────────────────────────

def _draw_filled_rect(frame, x1, y1, x2, y2, color, alpha):
    overlay = frame.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


def _draw_corner_brackets(frame, x1, y1, x2, y2, color, risk, thickness=1):
    """Draw corner brackets instead of full rectangle — tactical look."""
    bw = min(20, (x2 - x1) // 4)   # bracket width
    bh = min(20, (y2 - y1) // 4)   # bracket height
    t = 2 if risk == "RED" else thickness

    corners = [
        # top-left
        [(x1, y1 + bh), (x1, y1), (x1 + bw, y1)],
        # top-right
        [(x2 - bw, y1), (x2, y1), (x2, y1 + bh)],
        # bottom-left
        [(x1, y2 - bh), (x1, y2), (x1 + bw, y2)],
        # bottom-right
        [(x2 - bw, y2), (x2, y2), (x2, y2 - bh)],
    ]
    for pts in corners:
        for j in range(len(pts) - 1):
            cv2.line(frame, pts[j], pts[j + 1], color, t, cv2.LINE_AA)


def _draw_badge(frame, index, x1, y1, color):
    """Numbered badge at top-left corner."""
    r = 10
    cx, cy = x1 + r, y1 + r
    cv2.circle(frame, (cx, cy), r, (10, 10, 10), -1)
    cv2.circle(frame, (cx, cy), r, color, 1, cv2.LINE_AA)
    txt = str(index)
    tw = cv2.getTextSize(txt, FONT, 0.4, 1)[0][0]
    cv2.putText(frame, txt, (cx - tw // 2, cy + 4), FONT, 0.4, color, 1, cv2.LINE_AA)


def _draw_label_panel(frame, label, conf, reason, x1, y1, x2, color, risk):
    """Label panel above the bbox."""
    main_text = f"{label}  {conf}"
    tw, th = cv2.getTextSize(main_text, FONT, 0.44, 1)[0]
    panel_w = max(tw + 16, x2 - x1)
    panel_h = th + 6

    py1 = max(0, y1 - panel_h - 2)
    py2 = y1 - 2

    # Panel background
    cv2.rectangle(frame, (x1, py1), (x1 + panel_w, py2), (10, 10, 10), -1)
    cv2.rectangle(frame, (x1, py1), (x1 + panel_w, py2), color, 1)

    # Left accent bar
    cv2.rectangle(frame, (x1, py1), (x1 + 3, py2), color, -1)

    # Label text
    cv2.putText(frame, main_text, (x1 + 8, py2 - 3), FONT, 0.44, color, 1, cv2.LINE_AA)

    # Reason (small, below label)
    if reason and y1 > 40:
        short = reason[:55] + "…" if len(reason) > 55 else reason
        cv2.putText(frame, short, (x1 + 4, y1 + 14), FONT, 0.35,
                    (160, 160, 160), 1, cv2.LINE_AA)


def _resolve_bbox(bbox, w, h, ox, oy):
    x1, y1, x2, y2 = bbox
    if all(0.0 <= v <= 1.0 for v in [x1, y1, x2, y2]):
        x1, y1, x2, y2 = int(x1*w), int(y1*h), int(x2*w), int(y2*h)
    else:
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    return x1 + ox, y1 + oy, x2 + ox, y2 + oy