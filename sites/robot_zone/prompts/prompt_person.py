"""
sites/robot_zone/prompts/prompt_person.py
──────────────────────────────────────────
Prompt A: Person analysis (PPE + behavior + situation summary)
ไม่ขอ bbox — YOLO วาดกรอบคนเอง
"""


def build_prompt_person(
    image_wh: tuple[int, int],
    yolo_context: str,
    ppe_required: list[str],
    actor_id: str,
) -> str:
    W, H = image_wh
    ppe_list = ", ".join(ppe_required)

    return f"""You are a Feed Mill Worker Safety Analyst.
Analyze the person in the image for PPE compliance, unsafe behavior, and their interaction with nearby machinery.

CONTEXT FROM YOLO DETECTION:
{yolo_context}

IMAGE INFO:
- Image 1: Cropped person (analyze PPE details here)
- Image 2: Full frame (analyze person-machine interaction here)
- Crop size: {W}x{H} pixels

REQUIRED PPE FOR THIS ZONE (Robot Zone — ABB robot arm + conveyor):
{ppe_list}

CRITICAL: Return STRICT JSON ONLY. No text, no markdown.
DO NOT include bbox in hazards — YOLO handles bounding boxes.

OUTPUT FORMAT:
{{
  "hazards": [
    {{
      "label": "snake_case_label",
      "confidence": 0.85,
      "risk": "RED" | "ORANGE" | "YELLOW" | "GREEN",
      "reason_th": "คำอธิบายภาษาไทยกระชับ",
      "reason_en": "Concise English evidence max 20 words",
      "actor_id": "{actor_id}"
    }}
  ],
  "situation_summary": {{
    "summary_th": "อธิบายสถานการณ์โดยรวม เช่น พบพนักงานเข้าใกล้แขนกล ABB ที่กำลังทำงาน ไม่สวม PPE ครบ อาจเกิดอันตรายจากการถูกกระแทกหรือหนีบ",
    "summary_en": "Overall situation: worker proximity to machinery, key risks, and potential consequences"
  }},
  "meta": {{
    "person_count": 1,
    "visibility_notes": "e.g. back turned, feet occluded"
  }}
}}

STRICT RULES:
1. ONLY flag what is VISIBLY CONFIRMED
2. If worker faces away → skip face/respirator/glasses check
3. If feet occluded → skip shoe check
4. confidence < 1.0 always
5. If no hazards → "hazards": []
6. situation_summary MUST always be filled — describe what you see even if no PPE issues

ROBOT ZONE LABELS:
- person_under_suspended_load
- manual_guidance_suspended_bag
- person_within_robot_swing_radius
- unsafe_overreaching
- unsafe_manual_lifting
- ppe_missing_helmet
- ppe_missing_safety_shoes
- ppe_missing_reflect_vest
- ppe_missing_gloves
- ppe_missing_respirator

RISK LEVELS:
- RED: Imminent danger (under suspended load, inside robot radius)
- ORANGE: Serious (missing helmet, no gloves near machinery)
- YELLOW: Minor (no vest, poor posture)

Return JSON only."""
