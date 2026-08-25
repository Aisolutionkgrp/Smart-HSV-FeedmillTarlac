# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

HSV Safety Vision — AI-powered factory safety monitoring. YOLO11-pose (person detection/tracking) +
Gemini 2.5 Vision (PPE/hazard analysis) detect PPE violations and hazards in real time, with automated
Telegram alerts and a live Next.js dashboard. Target deployment hardware is a Jetson Orin (aarch64,
JetPack 6.x / CUDA 12.6); development happens on Windows/x86 too.

## Commands

Backend (Python, managed with `uv`):

```bash
uv sync                              # install deps (auto-selects Jetson torch wheel on aarch64, PyPI elsewhere)
uv run python main.py --site robot_zone   # run the app (starts FastAPI + frame loop + periodic scanner)
uv run python main.py --site robot_zone --rtsp rtsp://...   # override the site's camera RTSP URL
uv run ruff check .                  # lint
uv run ruff format .                 # format
uv run pytest                        # run all tests
uv run pytest tests/test_gemini.py   # run a single test file
uv run pytest tests/test_gemini.py::test_name -v   # run a single test
```

Backend requires Redis + Postgres running first: `docker compose up -d`.

Dashboard (Next.js, in `dashboard/`):

```bash
npm run dev      # dev server
npm run build
npm run start
```

Web preview once running: `http://localhost:8000/preview/robot_zone`.

## Architecture

### Process/thread layout (`main.py`)

Single process, three concurrent execution contexts:
1. **Main thread** — blocking `FrameProcessor.run()` loop (see below). CUDA is deliberately
   initialized here *first*, before any thread is spawned — on Jetson, if a background thread
   touches CUDA/TensorRT first, the primary context binds to that thread and YOLO's later
   TensorRT engine load in the main thread fails ("CUDA initialization failure: error 100").
2. **Background thread** — `uvicorn` serving `api/main.py` (REST API + MJPEG preview).
3. **Background thread** — `PeriodicScanner` running APScheduler inside its own asyncio event
   loop (must be started from inside a running coroutine, not before `loop.run_forever()`).

### Per-frame pipeline (`pipeline/frame_processor.py`)

```
StreamReader (RTSP) → Detector (YOLO11-pose + ByteTrack) → ZoneManager.check()
  → annotate → push_frame() (MJPEG buffer) → if zone hit & cooldown allows → site.on_zone_hit()
  → Gemini analysis → save snapshot → Telegram alert → save_event() (Postgres)
```

- `core/detector.py` filters non-human detections using bbox size/aspect-ratio, keypoint count,
  and an anatomical-plausibility check (shoulder above hip above knee above ankle, by Y coord) —
  YOLO can otherwise latch onto machinery. It also estimates per-track velocity/heading from a
  5-frame keypoint history (used for zone prediction).
- `core/zone_manager.py` does point-in-polygon (Shapely) *and* velocity-based prediction: it walks
  each person's velocity vector forward up to `predict_frames` and flags a "predicted" hit if the
  extrapolated position enters a zone before they're physically inside it.
- Cooldown (`core/cooldown_manager.py`) is keyed **per zone**, not per person track ID — ByteTrack
  IDs can reset when a track is lost, so per-track cooldown would fail to throttle repeat Gemini
  calls for the same physical person.
- `FrameProcessor` keeps its own persistent asyncio event loop for the whole process lifetime
  (`self._loop`) so async DB/Telegram calls don't break SQLAlchemy's async engine, which binds its
  connection pool to whichever loop first used it.

### Periodic scan (`pipeline/periodic_scanner.py`)

Every `periodic_interval_minutes` (config per site), scans the latest frame kept updated by
`FrameProcessor.update_frame()`, regardless of zone occupancy — `site.on_periodic()` lets Gemini
judge actual risk from image context rather than zone membership. Always writes a DB event; sends
Telegram only when `risk_level == "RED"`.

### Site plugin pattern (`sites/`)

`sites/base_site.py` defines `BaseSite` (ABC) — subclasses implement `on_zone_hit()` (event-driven)
and `on_periodic()` (scheduled). `BaseSite._load()` parses a site's `config.yaml`: zones (pixel
polygons + risk level + `predict_frames`), `camera_rtsp` (with `${ENV_VAR}` substitution against
`.env`), `logic` knobs (`cooldown_seconds`, `periodic_interval_minutes`, `prediction_enabled`), and
`ppe_required`.

`sites/robot_zone/site.py` (`RobotZoneSite`) is the only implemented site. Both `on_zone_hit()` and
`on_periodic()` funnel into a shared `_run_analysis()` that runs two Gemini calls per invocation:
- **Prompt A** (per detected person, cropped + full frame) — PPE/behavior check against
  `ppe_required`; does not ask Gemini for a bbox (YOLO's is more accurate).
- **Prompt B** (always, full frame) — general environment hazards, *with* bbox in the response.

Results are merged; overall risk is the worst level across all hazards (`RED > ORANGE > YELLOW >
GREEN`). Note: `sites/robot_zone/logic_event.py` and `logic_periodic.py` are empty — despite the
names implying split-out logic, everything lives inline in `site.py`.

Adding a new site: create `sites/<name>/config.yaml` + `sites/<name>/site.py` subclassing
`BaseSite`, then register it in `main.py`'s `load_site()`. `sites/loading_zone/` and
`sites/pellet_mill/` exist as empty scaffolding for this.

### Database (`db/`)

`SafetyEvent` (1) → (N) `SafetyHazard`, `AlertLog`; `CorrectiveAction` is schema-only, reserved for
a future AI-remediation-agent feature and not currently written to.

`db/database.py` uses `NullPool` deliberately: FastAPI's event loop and `FrameProcessor`'s own
event loop both create `asyncpg` connections from separate threads, and pooled connections can't
cross event loops — `NullPool` opens a fresh connection per use instead of reusing one bound to a
different loop.

### API (`api/`)

`api/main.py` is the actual mounted app (`/preview/{site_id}`, `/stream/{site_id}` MJPEG,
`/api/events`, `/api/events/{id}`, `/api/events/{id}/image`, `/api/stats`, `/health`). It imports
`push_frame`/`_gen_mjpeg` from `api/preview.py` but does *not* mount `api/preview.py`'s own `app`
object — that second `FastAPI()` instance in `preview.py` is vestigial, don't add routes to it.
`api/routes/*.py` and `api/websocket.py` are empty stub files, not wired up.

### Dashboard (`dashboard/`)

Next.js App Router; polls the FastAPI REST API directly (no websocket, despite the stub). Pages:
overview (`app/page.tsx`), events list/detail (`app/events/`), live MJPEG view (`app/live/`),
analytics (`app/stats/`). `app/lib/api.ts` holds the fetch helpers.

### Known dead/duplicate files

`pipeline/event_pipeline.py` and `pipeline/periodic_pipeline.py` are byte-identical duplicates of
`event_saver.py`/`periodic_scanner.py` and are not imported anywhere; `core/tracker.py` is empty
(tracking is done inside `detector.py` via ByteTrack). Don't edit these expecting effect — check
`main.py`/`frame_processor.py` imports to confirm what's actually wired in before changing pipeline
behavior.

## Configuration

All runtime config comes from environment variables via `.env` (loaded by `config/settings.py`,
a pydantic `BaseSettings`) plus per-site `config.yaml` files. Key env vars: `YOLO_MODEL/CONF/IOU/
DEVICE/IMGSZ`, `FRAME_SKIP`, `GEMINI_API_KEY/MODEL/TIMEOUT/MAX_RETRIES`, `REDIS_HOST/PORT/DB`,
`DATABASE_URL`, per-camera `*_RTSP` vars, `TELEGRAM_BOT_TOKEN/CHAT_ID`, `API_HOST/PORT`.

## Deployment

`docker-compose.yml` runs only Redis + Postgres as containers; the app itself runs natively via
`uv run`. `deploy/hsv-backend.service` and `deploy/hsv-dashboard.service` are systemd units for the
Jetson: backend does `docker compose up -d` then `uv run python main.py --site robot_zone`;
dashboard runs `npm run start` and depends on the backend service.
