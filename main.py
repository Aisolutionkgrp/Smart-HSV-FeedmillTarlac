"""
main.py — entry point
รัน: python main.py --site robot_zone
เปิด browser: http://localhost:8000/preview/robot_zone
"""

import argparse
import logging
import sys
import threading
from pathlib import Path

# ── Add project root to sys.path ──────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── Load .env FIRST ───────────────────────────────────────────────────────────
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env")

# ── Windows Unicode fix ───────────────────────────────────────────────────────
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# ── Ensure log dir exists ─────────────────────────────────────────────────────
(ROOT / "logs").mkdir(exist_ok=True)

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(ROOT / "logs" / "safety_vision.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def load_site(site_id: str):
    if site_id == "robot_zone":
        from sites.robot_zone.site import RobotZoneSite
        return RobotZoneSite(ROOT / "sites" / "robot_zone" / "config.yaml")
    raise ValueError(f"Unknown site: {site_id}")


def start_web_server(port: int = 8000):
    """Start FastAPI MJPEG server in background thread."""
    import uvicorn
    from api.main import app
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")


def main():
    parser = argparse.ArgumentParser(description="Factory Safety Vision System")
    parser.add_argument("--site", default="robot_zone")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--rtsp", help="Override RTSP URL")
    args = parser.parse_args()

    logger.info(f"Starting Safety Vision - site={args.site}")

    # Start web preview server in background
    web_thread = threading.Thread(
        target=start_web_server,
        args=(args.port,),
        daemon=True
    )
    web_thread.start()
    logger.info(f"Web preview: http://localhost:{args.port}/preview/{args.site}")

    # Load site + run processor
    site = load_site(args.site)
    if args.rtsp:
        site.site_config.camera_rtsp = args.rtsp

    from pipeline.frame_processor import FrameProcessor
    processor = FrameProcessor(site=site, show_preview=True)

    try:
        processor.run()
    except KeyboardInterrupt:
        logger.info("Interrupted - shutting down...")
        processor.stop()


if __name__ == "__main__":
    main()
    