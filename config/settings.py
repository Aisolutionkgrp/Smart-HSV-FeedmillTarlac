"""
Global settings — loaded once at startup.
All secrets come from environment variables / .env file.
"""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Project ──────────────────────────────────────────────
    PROJECT_NAME: str = "Factory Safety Vision"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Paths ─────────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    SNAPSHOT_DIR: Path = BASE_DIR / "snapshots"
    LOG_DIR: Path = BASE_DIR / "logs"

    # ── YOLO ──────────────────────────────────────────────────
    YOLO_MODEL: str = "yolov8s-pose.pt"
    YOLO_CONF: float = 0.65
    YOLO_IOU: float = 0.45
    YOLO_DEVICE: str = "cpu"
    YOLO_IMGSZ: int = 640
    FRAME_SKIP: int = 3

    # ── Gemini ────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash-preview-05-20"
    GEMINI_TIMEOUT: int = 30
    GEMINI_MAX_RETRIES: int = 2

    # ── Redis ─────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # ── PostgreSQL ────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/safety_db"

    # ── RTSP Credentials (per camera) ─────────────────────────
    ROBOT_ZONE_CAM1_RTSP: str = ""
    ROBOT_ZONE_CAM2_RTSP: str = ""
    PELLET_MILL_CAM1_RTSP: str = ""
    LOADING_ZONE_CAM1_RTSP: str = ""

    # ── Telegram ──────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # ── FastAPI ───────────────────────────────────────────────
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# ── Ensure runtime dirs exist ─────────────────────────────────
settings.SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
