import sys
import os
sys.path.insert(0, "/app/services")

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional, List
from io import BytesIO
import pytesseract
from PIL import Image
import cv2
import numpy as np
import httpx
import sqlite3
import logging
import asyncio
import os
import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("CAM_DB", "/app/cameras.db")
AI_BRAIN_URL = os.environ.get("AI_BRAIN_URL", "http://kilo-ai-brain:9004")

# ── DB helpers ─────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cameras (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT NOT NULL UNIQUE,
            url      TEXT NOT NULL,
            type     TEXT NOT NULL DEFAULT 'http',
            location TEXT,
            enabled  INTEGER NOT NULL DEFAULT 1,
            added_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_id   INTEGER NOT NULL,
            camera_name TEXT NOT NULL,
            ocr_text    TEXT,
            alert       TEXT,
            taken_at    TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Camera DB initialized at %s", DB_PATH)

# ── Snapshot capture ──────────────────────────────────────────────────────────

async def capture_snapshot(camera_url: str, camera_type: str) -> Optional[bytes]:
    """Grab a single frame from an IP camera (HTTP snapshot or RTSP)."""
    try:
        if camera_type == "rtsp" or camera_url.startswith("rtsp://"):
            # Use OpenCV to grab one frame from RTSP
            loop = asyncio.get_event_loop()
            img_bytes = await loop.run_in_executor(None, _rtsp_snapshot, camera_url)
            return img_bytes
        else:
            # HTTP snapshot URL — just GET the image
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(camera_url)
                resp.raise_for_status()
                return resp.content
    except Exception as e:
        logger.error("Snapshot capture failed for %s: %s", camera_url, e)
        return None

def _rtsp_snapshot(url: str) -> Optional[bytes]:
    cap = cv2.VideoCapture(url)
    try:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        ret, frame = cap.read()
        if not ret:
            return None
        _, buf = cv2.imencode(".jpg", frame)
        return buf.tobytes()
    finally:
        cap.release()

async def notify_kilo(message: str, alert_type: str = "camera"):
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(f"{AI_BRAIN_URL}/observations", json={
                "content": message,
                "type": alert_type,
                "source": "cam"
            })
    except Exception:
        pass

# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Camera service ready — IP camera mode (no USB webcam required)")
    yield

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Kilo Camera Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Schemas ───────────────────────────────────────────────────────────────────

class CameraCreate(BaseModel):
    name: str
    url: str
    type: str = "http"   # "http" or "rtsp"
    location: Optional[str] = None

class CameraUpdate(BaseModel):
    url: Optional[str] = None
    type: Optional[str] = None
    location: Optional[str] = None
    enabled: Optional[bool] = None

# ── Camera CRUD ───────────────────────────────────────────────────────────────

@app.get("/cameras")
async def list_cameras():
    conn = get_db()
    rows = conn.execute("SELECT * FROM cameras ORDER BY id").fetchall()
    conn.close()
    return {"cameras": [dict(r) for r in rows]}

@app.post("/cameras", status_code=201)
async def add_camera(body: CameraCreate):
    try:
        conn = get_db()
        cursor = conn.execute(
            "INSERT INTO cameras (name, url, type, location) VALUES (?, ?, ?, ?)",
            (body.name, body.url, body.type, body.location)
        )
        cam_id = cursor.lastrowid
        conn.commit()
        conn.close()
        logger.info("Camera registered: %s (%s)", body.name, body.url)
        return {"id": cam_id, "name": body.name, "url": body.url, "type": body.type, "location": body.location}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail=f"Camera '{body.name}' already exists")

@app.put("/cameras/{cam_id}")
async def update_camera(cam_id: int, body: CameraUpdate):
    conn = get_db()
    row = conn.execute("SELECT * FROM cameras WHERE id=?", (cam_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Camera not found")
    updates = {}
    if body.url is not None: updates["url"] = body.url
    if body.type is not None: updates["type"] = body.type
    if body.location is not None: updates["location"] = body.location
    if body.enabled is not None: updates["enabled"] = 1 if body.enabled else 0
    if updates:
        set_clause = ", ".join(f"{k}=?" for k in updates)
        conn.execute(f"UPDATE cameras SET {set_clause} WHERE id=?", (*updates.values(), cam_id))
        conn.commit()
    conn.close()
    return {"id": cam_id, "updated": list(updates.keys())}

@app.delete("/cameras/{cam_id}")
async def delete_camera(cam_id: int):
    conn = get_db()
    row = conn.execute("SELECT name FROM cameras WHERE id=?", (cam_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Camera not found")
    name = row["name"]
    conn.execute("DELETE FROM cameras WHERE id=?", (cam_id,))
    conn.commit()
    conn.close()
    return {"deleted": name}

# ── Snapshot endpoints ────────────────────────────────────────────────────────

@app.get("/cameras/{cam_id}/snapshot")
async def get_snapshot(cam_id: int, ocr: bool = False):
    """Grab a live frame from the camera. Optionally run OCR."""
    conn = get_db()
    row = conn.execute("SELECT * FROM cameras WHERE id=?", (cam_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Camera not found")
    if not row["enabled"]:
        raise HTTPException(status_code=503, detail="Camera is disabled")

    img_bytes = await capture_snapshot(row["url"], row["type"])
    if img_bytes is None:
        raise HTTPException(status_code=503, detail=f"Failed to capture from {row['name']}")

    ocr_text = None
    if ocr:
        try:
            img = Image.open(BytesIO(img_bytes))
            ocr_text = pytesseract.image_to_string(img).strip()
        except Exception as e:
            logger.warning("OCR failed: %s", e)

    # Save snapshot record
    conn = get_db()
    conn.execute(
        "INSERT INTO snapshots (camera_id, camera_name, ocr_text) VALUES (?, ?, ?)",
        (cam_id, row["name"], ocr_text)
    )
    conn.commit()
    conn.close()

    if ocr_text and len(ocr_text) > 20:
        asyncio.create_task(notify_kilo(
            f"Camera '{row['name']}' detected text: {ocr_text[:200]}", "camera_ocr"
        ))

    if ocr:
        return JSONResponse({"camera": row["name"], "ocr_text": ocr_text, "has_image": True})

    return StreamingResponse(BytesIO(img_bytes), media_type="image/jpeg")

@app.get("/cameras/{cam_id}/snapshots")
async def list_snapshots(cam_id: int, limit: int = 20):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM snapshots WHERE camera_id=? ORDER BY id DESC LIMIT ?",
        (cam_id, limit)
    ).fetchall()
    conn.close()
    return {"snapshots": [dict(r) for r in rows]}

@app.get("/cameras/all/check")
async def check_all_cameras():
    """Ping all enabled cameras and return status."""
    conn = get_db()
    cams = conn.execute("SELECT * FROM cameras WHERE enabled=1").fetchall()
    conn.close()
    results = []
    for cam in cams:
        img = await capture_snapshot(cam["url"], cam["type"])
        results.append({
            "id": cam["id"],
            "name": cam["name"],
            "location": cam["location"],
            "online": img is not None
        })
    return {"cameras": results, "checked_at": datetime.datetime.now().isoformat()}

# ── OCR upload (keep existing functionality) ──────────────────────────────────

@app.post("/ocr")
async def ocr_image(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")
    try:
        img_bytes = await file.read()
        img = Image.open(BytesIO(img_bytes))
        try:
            text = pytesseract.image_to_string(img)
        except Exception:
            text = ""
        if text.strip():
            asyncio.create_task(notify_kilo(
                f"OCR upload: {len(text)} characters extracted", "camera_ocr"
            ))
        return {"text": text.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {e}")

# ── Health / Status ───────────────────────────────────────────────────────────

@app.get("/health")
@app.get("/status")
async def health():
    conn = get_db()
    cam_count = conn.execute("SELECT COUNT(*) FROM cameras WHERE enabled=1").fetchone()[0]
    conn.close()
    return {
        "status": "ok",
        "mode": "ip_camera",
        "cameras_registered": cam_count,
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.get("/activity")
async def activity():
    """Legacy endpoint — returns whether any camera was checked recently."""
    conn = get_db()
    row = conn.execute(
        "SELECT taken_at FROM snapshots ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row:
        ts = datetime.datetime.fromisoformat(row["taken_at"])
        age = (datetime.datetime.now() - ts).total_seconds()
        active = age < 300
    else:
        active = False
    return {
        "sees_user": active,
        "last_activity": row["taken_at"] if row else None,
        "timestamp": datetime.datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
