from fastapi import FastAPI
import httpx
import asyncio
import logging
from datetime import datetime
import os

app = FastAPI(title="Kilo Health Monitor")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Alert endpoints
SOCKETIO_URL = os.environ.get('SOCKETIO_URL', 'http://kilo-socketio:9010')
AI_BRAIN_URL = os.environ.get('AI_BRAIN_URL', 'http://kilo-ai-brain:9004')

# Service status tracking
service_status = {}
alert_cooldown = {}  # Prevent alert spam

async def send_alert(service: str, message: str, severity: str = 'warning'):
    """Send alert via Socket.IO and AI Brain observations"""

    # Check cooldown (don't alert more than once per 5 minutes)
    cooldown_key = f"{service}_{severity}"
    if cooldown_key in alert_cooldown:
        last_alert = alert_cooldown[cooldown_key]
        if (datetime.now() - last_alert).total_seconds() < 300:
            return

    alert_cooldown[cooldown_key] = datetime.now()

    logger.warning(f"🚨 ALERT: {service} - {message} ({severity})")

    # Send to Socket.IO for real-time notification
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f'{SOCKETIO_URL}/emit',
                json={
                    'event': 'system_alert',
                    'data': {
                        'service': service,
                        'message': message,
                        'severity': severity,
                        'timestamp': datetime.now().isoformat(),
                        'alert_text': f"🚨 {service}: {message}"
                    }
                }
            )
    except Exception as e:
        logger.error(f"Failed to send Socket.IO alert: {e}")

    # Send observation to AI Brain
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f'{AI_BRAIN_URL}/observations',
                json={
                    'source': 'health_monitor',
                    'content': f"🚨 SYSTEM ALERT: {service} - {message}",
                    'priority': 'high' if severity == 'critical' else 'normal',
                    'metadata': {'service': service, 'severity': severity}
                }
            )
    except Exception as e:
        logger.error(f"Failed to send AI Brain observation: {e}")

async def check_ollama_health(name: str, url: str):
    """Check if Ollama is responsive"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            start = asyncio.get_event_loop().time()
            response = await client.get(url)
            elapsed = asyncio.get_event_loop().time() - start

            if response.status_code == 200:
                if elapsed > 5.0:
                    await send_alert(
                        name,
                        f"Slow response: {elapsed:.1f}s (should be <1s)",
                        'warning'
                    )
                    return 'slow'
                return 'healthy'
            else:
                await send_alert(name, f"HTTP {response.status_code}", 'critical')
                return 'unhealthy'
    except asyncio.TimeoutError:
        await send_alert(name, "Timeout (>10s) - service may be stuck", 'critical')
        return 'timeout'
    except Exception as e:
        await send_alert(name, f"Error: {str(e)}", 'critical')
        return 'error'

async def check_ray_serve_health():
    """Check if Ray Serve is responsive with a test inference"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            start = asyncio.get_event_loop().time()
            response = await client.post(
                'http://kilo-ray-serve:8000/api/generate',
                json={'model': 'dolphin-llama3:8b', 'prompt': 'ping', 'stream': False}
            )
            elapsed = asyncio.get_event_loop().time() - start

            if response.status_code == 200:
                if elapsed > 25.0:
                    await send_alert(
                        'ray_serve',
                        f"Very slow response: {elapsed:.1f}s (expected ~15-20s)",
                        'warning'
                    )
                    return 'slow'
                logger.info(f"✅ Ray Serve healthy ({elapsed:.1f}s)")
                return 'healthy'
            else:
                await send_alert('ray_serve', f"HTTP {response.status_code}", 'critical')
                return 'unhealthy'
    except asyncio.TimeoutError:
        await send_alert('ray_serve', "Timeout (>30s) - LLM may be stuck", 'critical')
        return 'timeout'
    except Exception as e:
        await send_alert('ray_serve', f"Error: {str(e)}", 'critical')
        return 'error'

async def check_service_health(name: str, url: str):
    """Generic health check for HTTP services"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return 'healthy'
            else:
                await send_alert(name, f"HTTP {response.status_code}", 'warning')
                return 'unhealthy'
    except Exception as e:
        await send_alert(name, f"Unreachable: {str(e)}", 'critical')
        return 'error'

async def health_check_loop():
    """Main health monitoring loop"""
    logger.info("🔍 Kilo Health Monitor started - checking services every 2 minutes")

    cycle = 0
    while True:
        try:
            cycle += 1

            # Check Ollama instances
            service_status['ollama_hp'] = await check_ollama_health(
                'Ollama (HP)',
                'http://192.168.68.57:11434/api/tags'
            )
            service_status['ollama_beelink'] = await check_ollama_health(
                'Ollama (Beelink)',
                'http://192.168.68.56:11434/api/tags'
            )

            # Check Ray Serve every 3rd cycle (every 6 minutes) to avoid spam
            if cycle % 3 == 0:
                service_status['ray_serve'] = await check_ray_serve_health()

            # Check core services
            service_status['ai_brain'] = await check_service_health(
                'AI Brain',
                f'{AI_BRAIN_URL}/health'
            )
            service_status['gateway'] = await check_service_health(
                'Gateway',
                'http://kilo-gateway:8000/health'
            )

            healthy_count = sum(1 for status in service_status.values() if status == 'healthy')
            total_count = len(service_status)
            logger.info(f"✅ Health check #{cycle}: {healthy_count}/{total_count} healthy - {service_status}")

        except Exception as e:
            logger.error(f"Health check error: {e}")

        # Check every 2 minutes
        await asyncio.sleep(120)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(health_check_loop())

@app.get("/health")
async def health():
    return {"status": "ok", "monitoring": True}

@app.get("/status")
async def get_status():
    """Get current status of all monitored services"""
    return {
        'services': service_status,
        'timestamp': datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9011)
