"""
Kilo Voice Service — TTS + STT

TTS: edge-tts (Microsoft neural voices, free, no API key)
STT: Gemini Flash (if GEMINI_API_KEY set) or placeholder
"""
import asyncio
import io
import os
import logging
import base64
import httpx
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

# Default voice — Christopher is a clear, natural-sounding US male voice
DEFAULT_VOICE  = os.environ.get("KILO_VOICE", "en-US-ChristopherNeural")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
AI_BRAIN_URL   = os.environ.get("AI_BRAIN_URL", "http://kilo-ai-brain:9004")

# Voice options Kilo supports (name → edge-tts voice ID)
VOICES = {
    "kilo":        "en-US-GuyNeural",            # Kilo default voice
    "kilo-deep":   "en-US-GuyNeural",            # deeper male
    "kilo-warm":   "en-US-EricNeural",           # warmer male
    "aria":        "en-US-AriaNeural",            # professional female
    "jenny":       "en-US-JennyNeural",           # conversational female
    "default":     "en-US-GuyNeural",
}

# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        import edge_tts
        logger.info("edge-tts available — TTS ready")
    except ImportError:
        logger.warning("edge-tts not installed — TTS will fail")
    yield

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Kilo Voice Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Schemas ───────────────────────────────────────────────────────────────────

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "kilo"
    rate: Optional[str] = "+0%"    # e.g. "+10%" speeds up, "-10%" slows down
    pitch: Optional[str] = "+0Hz"  # e.g. "-5Hz" for slightly lower pitch

class STTResponse(BaseModel):
    text: str
    confidence: float
    language: str = "en"

# ── TTS ───────────────────────────────────────────────────────────────────────

async def _synthesize(text: str, voice_id: str, rate: str, pitch: str) -> bytes:
    import edge_tts
    buf = io.BytesIO()
    communicate = edge_tts.Communicate(text, voice=voice_id, rate=rate, pitch=pitch)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    data = buf.getvalue()
    if not data:
        raise RuntimeError("edge-tts returned empty audio")
    return data

@app.post("/tts")
async def text_to_speech(req: TTSRequest):
    """Convert text to speech. Returns audio/mpeg (MP3)."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    voice_id = VOICES.get(req.voice or "kilo", VOICES["kilo"])
    text = req.text[:2000]  # cap length

    try:
        audio_bytes = await _synthesize(text, voice_id, req.rate or "+0%", req.pitch or "+0Hz")
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=kilo_voice.mp3"}
        )
    except ImportError:
        raise HTTPException(status_code=503, detail="edge-tts not installed. Run: pip install edge-tts")
    except Exception as e:
        logger.error("TTS error: %s", e)
        raise HTTPException(status_code=500, detail=f"TTS failed: {e}")

@app.get("/tts")
async def text_to_speech_get(text: str, voice: str = "kilo", rate: str = "+0%", pitch: str = "+0Hz"):
    """GET version — handy for testing in browser. Returns audio/mpeg."""
    return await text_to_speech(TTSRequest(text=text, voice=voice, rate=rate, pitch=pitch))

# ── STT ───────────────────────────────────────────────────────────────────────

@app.post("/stt", response_model=STTResponse)
async def speech_to_text(audio: UploadFile = File(...)):
    """Convert speech to text. Supports WAV, MP3, OGG, M4A, WebM."""
    if GEMINI_API_KEY:
        return await _stt_gemini(audio)
    raise HTTPException(
        status_code=501,
        detail="STT requires GEMINI_API_KEY env var. Set it on the deployment."
    )

async def _stt_gemini(audio: UploadFile) -> STTResponse:
    """Use Gemini Flash to transcribe audio."""
    try:
        audio_bytes = await audio.read()
        b64 = base64.b64encode(audio_bytes).decode()
        mime = audio.content_type or "audio/webm"

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Content(parts=[
                    types.Part(inline_data=types.Blob(mime_type=mime, data=b64)),
                    types.Part(text="Transcribe this audio exactly. Return only the spoken words, no commentary."),
                ])
            ],
            config={"max_output_tokens": 500}
        )
        text = (response.text or "").strip()
        return STTResponse(text=text, confidence=0.9, language="en")
    except Exception as e:
        logger.error("Gemini STT error: %s", e)
        raise HTTPException(status_code=500, detail=f"STT failed: {e}")

# ── Voice list ────────────────────────────────────────────────────────────────

@app.get("/voices")
async def list_voices():
    """List available voice options."""
    return {
        "voices": [
            {"id": "kilo",      "name": "Kilo (default)",   "gender": "male",   "style": "clear & professional"},
            {"id": "kilo-deep", "name": "Kilo Deep",        "gender": "male",   "style": "deeper & authoritative"},
            {"id": "kilo-warm", "name": "Kilo Warm",        "gender": "male",   "style": "warmer & friendly"},
            {"id": "aria",      "name": "Aria",             "gender": "female", "style": "professional"},
            {"id": "jenny",     "name": "Jenny",            "gender": "female", "style": "conversational"},
        ],
        "default": "kilo"
    }

# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
@app.get("/status")
async def health():
    try:
        import edge_tts  # noqa
        tts_ready = True
    except ImportError:
        tts_ready = False
    return {
        "status": "ok",
        "tts_ready": tts_ready,
        "tts_provider": "edge-tts (Microsoft neural)",
        "stt_ready": bool(GEMINI_API_KEY),
        "stt_provider": "gemini-2.0-flash" if GEMINI_API_KEY else "not configured",
        "default_voice": DEFAULT_VOICE,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9008)
