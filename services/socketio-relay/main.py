"""
Simple Socket.IO relay service for Kilo AI
Provides WebSocket support for real-time frontend updates
"""
import socketio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from kilo_integration import KiloNerve
import uvicorn
from fastapi import FastAPI
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Socket.IO Relay")

# Create Socket.IO server
kilo_nerve = KiloNerve("socketio")

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25
)

# Wrap with ASGI app
socket_app = socketio.ASGIApp(
    socketio_server=sio,
    other_asgi_app=app
)

@app.get("/health")
@app.get("/status")
async def health():
    return {"status": "ok", "service": "socketio-relay"}


@app.post("/emit")
async def emit_notification(payload: dict):
    """
    Emit a notification to all connected Socket.IO clients
    Called by gateway when reminders/alerts need to be pushed to frontend
    """
    try:
        event = payload.get("event", "notification")
        data = payload.get("data", {})

        # Broadcast to all connected clients
        await sio.emit(event, data)

        logger.info(f"🔔 Broadcasted {event}: {data.get('content', '')[:50]}")
        return {"status": "ok", "message": f"Emitted {event} to all clients"}

    except Exception as e:
        logger.error(f"Failed to emit: {e}")
        return {"status": "error", "message": str(e)}

@sio.event
async def connect(sid, environ):
    """Handle client connection"""
    logger.info(f"✅ Socket.IO client connected: {sid}")
    await sio.emit('connected', {
        'status': 'ok',
        'message': 'Connected to Kilo AI',
        'timestamp': time.time()
    }, room=sid)

@sio.event
async def disconnect(sid):
    """Handle client disconnection"""
    logger.info(f"❌ Socket.IO client disconnected: {sid}")

@sio.event
async def ping(sid, data=None):
    """Handle ping from client"""
    logger.debug(f"📡 Ping from {sid}")
    await sio.emit('pong', {
        'timestamp': time.time(),
        'data': data
    }, room=sid)

@sio.event
async def subscribe(sid, channel):
    """Subscribe to a channel for updates"""
    logger.info(f"🔔 Client {sid} subscribed to {channel}")
    await sio.emit('subscribed', {
        'channel': channel,
        'timestamp': time.time()
    }, room=sid)

@sio.event
async def message(sid, data):
    """Handle generic messages"""
    logger.info(f"💬 Message from {sid}: {data}")
    await sio.emit('message_received', {
        'status': 'ok',
        'timestamp': time.time()
    }, room=sid)

if __name__ == "__main__":
    uvicorn.run(
        socket_app,
        host="0.0.0.0",
        port=9010,
        log_level="info"
    )
