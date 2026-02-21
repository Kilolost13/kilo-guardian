from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from starlette.responses import JSONResponse
import httpx
import os
from sqlmodel import SQLModel, Field, create_engine, Session, select
from typing import Optional
import secrets
import hashlib
import datetime
import time
import asyncio
import logging
logger = logging.getLogger(__name__)


app = FastAPI(title="Kilos API Gateway")

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# admin tokens DB (simple centralized token store for admin UI/automation)
DB_URL = os.getenv("GATEWAY_DB_URL", "sqlite:////tmp/gateway.db")
engine = create_engine(DB_URL, echo=False)


class AdminToken(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    label: Optional[str] = None
    token_hash: str
    revoked: bool = False
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


# Persistent HTTP client for proxying requests (prevents connection exhaustion)
http_client: Optional[httpx.AsyncClient] = None


@app.on_event("startup")
async def startup():
    global http_client
    try:
        SQLModel.metadata.create_all(engine)
    except Exception:
        pass
    
    # Create persistent HTTP client with connection pooling
    # This prevents "client has been closed" errors and improves performance
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(120.0, connect=10.0),  # 120s for LLM/OCR, 10s connect timeout
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        follow_redirects=True
    )
    logger.info("Gateway HTTP client initialized with connection pooling")


@app.on_event("shutdown")
async def shutdown():
    global http_client
    if http_client:
        await http_client.aclose()
        logger.info("Gateway HTTP client closed")


def _hash_token(token: str) -> str:
    """
    Hash a token using bcrypt for secure storage.
    Falls back to SHA256 if bcrypt unavailable (for backward compatibility).
    """
    try:
        import bcrypt
        # Use bcrypt for secure password hashing (with salt)
        salt = bcrypt.gensalt(rounds=12)  # 12 rounds is good balance of security/performance
        token_hash = bcrypt.hashpw(token.encode(), salt)
        return token_hash.decode('ascii')
    except ImportError:
        # Fallback to SHA256 if bcrypt not installed
        # NOTE: SHA256 without salt is less secure, install bcrypt in production
        import logging
        logging.warning("bcrypt not installed, using SHA256 (less secure). Install: pip install bcrypt")
        h = hashlib.sha256()
        h.update(token.encode())
        return h.hexdigest()


def _validate_header_token(header_token: Optional[str]) -> bool:
    """
    Validate a token against stored hashes.
    Supports both bcrypt and SHA256 hashes for backward compatibility.
    """
    if not header_token:
        return False
    try:
        # Pre-compute SHA256 hash once for efficiency
        sha256_hash = hashlib.sha256(header_token.encode()).hexdigest()
        
        with Session(engine) as sess:
            # Get all non-revoked tokens
            q = sess.exec(select(AdminToken).where(AdminToken.revoked == False))

            for token_record in q.all():
                stored_hash = token_record.token_hash

                # Check if it's a bcrypt hash (starts with $2b$)
                if stored_hash.startswith('$2b$'):
                    try:
                        import bcrypt
                        if bcrypt.checkpw(header_token.encode(), stored_hash.encode('ascii')):
                            return True
                    except ImportError:
                        pass
                else:
                    # SHA256 hash - simple comparison (use pre-computed hash)
                    if sha256_hash == stored_hash:
                        return True

            return False
    except Exception:
        return False


def _is_admin_request(request: Request) -> bool:
    """Return True if the request contains a valid admin credential.

    Accepts either a stored admin token (X-Admin-Token), or the bootstrap
    LIBRARY_ADMIN_KEY for environments still using that static key.
    """
    header = request.headers.get('x-admin-token')
    library_admin_key = os.environ.get('LIBRARY_ADMIN_KEY')

    if header and library_admin_key and header.strip() == library_admin_key.strip():
        return True

    auth_header = request.headers.get('authorization')
    if auth_header and library_admin_key and library_admin_key in auth_header:
        return True

    return _validate_header_token(header)


@app.post("/admin/tokens")
async def create_admin_token(request: Request):
    """Create a new admin token. If this is the first token ever created, allow creation without auth.
    Otherwise require X-Admin-Token header with a valid token."""
    header = request.headers.get("x-admin-token")
    # allow first token creation if DB empty
    with Session(engine) as sess:
        existing = sess.exec(select(AdminToken)).all()
        count = len(existing)
    if count > 0 and not _validate_header_token(header):
        raise HTTPException(status_code=401, detail="Unauthorized")

    new_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(new_token)
    at = AdminToken(label="generated", token_hash=token_hash)
    with Session(engine) as sess:
        sess.add(at)
        sess.commit()
        sess.refresh(at)

    return {"id": at.id, "token": new_token}


@app.get("/admin/tokens")
async def list_admin_tokens(request: Request):
    header = request.headers.get("x-admin-token")
    if not _validate_header_token(header):
        raise HTTPException(status_code=401, detail="Unauthorized")
    out = []
    with Session(engine) as sess:
        rows = sess.exec(select(AdminToken).order_by(AdminToken.created_at.desc())).all()
        for r in rows:
            out.append({"id": r.id, "label": r.label, "revoked": bool(r.revoked), "created_at": str(r.created_at)})
    return {"tokens": out}


@app.post("/admin/tokens/{token_id}/revoke")
async def revoke_admin_token(token_id: int, request: Request):
    header = request.headers.get("x-admin-token")
    if not _validate_header_token(header):
        raise HTTPException(status_code=401, detail="Unauthorized")
    with Session(engine) as sess:
        row = sess.get(AdminToken, token_id)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        row.revoked = True
        sess.add(row)
        sess.commit()
    return {"status": "ok"}


@app.post("/admin/validate")
async def validate_admin_token(payload: dict = None, request: Request = None):
    # token may be supplied via header or body {"token": "..."}
    header = request.headers.get("x-admin-token") if request is not None else None
    body_token = None
    if payload and isinstance(payload, dict):
        body_token = payload.get("token")
    token = header or body_token
    if not token or not _validate_header_token(token):
        raise HTTPException(status_code=401, detail="Invalid")
    return {"valid": True}

# Health check endpoint (alias for /health)
@app.get("/status")
async def status():
    return {"status": "ok"}

SERVICE_URLS = {
    "meds": os.getenv("MEDS_URL", "http://kilo-meds:9000"),
    "reminder": os.getenv("REMINDER_URL", "http://kilo-reminder:9002"),
    "reminders": os.getenv("REMINDER_URL", "http://kilo-reminder:9002"),
    "habits": os.getenv("HABITS_URL", "http://kilo-habits:9000"),
    "ai_brain": os.getenv("AI_BRAIN_URL", "http://kilo-ai-brain:9004"),
    "financial": os.getenv("FINANCIAL_URL", "http://kilo-financial:9005"),
    "library_of_truth": os.getenv("LIBRARY_OF_TRUTH_URL", "http://kilo-library:9006"),
    "cam": os.getenv("CAM_URL", "http://kilo-cam:9007"),
    "ml": os.getenv("ML_ENGINE_URL", "http://kilo-ml-engine:9009"),
    "voice": os.getenv("VOICE_URL", "http://kilo-voice:9008"),
    "usb": os.getenv("USB_TRANSFER_URL", "http://kilo-usb-transfer:9010"),
    "security_monitor": os.getenv("SECURITY_MONITOR_URL", "http://security-monitor:8001"),
    "drone_control": os.getenv("DRONE_CONTROL_URL", "http://drone-control:8002"),
    "briefing": os.getenv("BRIEFING_URL", "http://briefing:8003"),
    "chat": os.getenv("AI_BRAIN_URL", "http://kilo-ai-brain:9004"),
    "library": os.getenv("LIBRARY_OF_TRUTH_URL", "http://kilo-library:9006"),
}

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/agent/notify")
async def agent_notify(payload: dict):
    """
    Receive notifications from services (reminders, alerts, etc.)
    and forward to Socket.IO for real-time delivery to frontend
    """
    try:
        notification_type = payload.get("type", "generic")
        content = payload.get("content", "")
        metadata = payload.get("metadata", {})

        # Forward to Socket.IO service for real-time push to frontend
        socketio_url = os.getenv("SOCKETIO_URL", "http://kilo-socketio:9010")

        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(
                f"{socketio_url}/emit",
                json={
                    "event": "notification",
                    "data": {
                        "type": notification_type,
                        "content": content,
                        "metadata": metadata,
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                }
            )

        logger.info(f"Notification forwarded: {notification_type} - {content}")
        return {"status": "ok", "message": "Notification sent"}

    except Exception as e:
        logger.error(f"Failed to forward notification: {e}")
        return {"status": "error", "message": str(e)}


@app.get('/admin/ai_brain/metrics')
async def admin_ai_brain_metrics(request: Request):
    """Proxy ai_brain metrics to admin users only.

    Validates X-Admin-Token using the gateway's token store. Returns raw Prometheus metrics text.
    """
    if not _is_admin_request(request):
        raise HTTPException(status_code=401, detail='Unauthorized')

    service_url = SERVICE_URLS.get('ai_brain')
    if not service_url:
        raise HTTPException(status_code=404, detail='Service not found')

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{service_url.rstrip('/')}/metrics", headers={"X-Admin-Token": header})
            return Response(content=resp.content, media_type=resp.headers.get('content-type','text/plain'), status_code=resp.status_code)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=str(e))


@app.get("/admin/status")
async def admin_status():
    """Aggregate health status from all backend services + k3s + beelink"""
    import httpx
    import subprocess
    from datetime import datetime
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException

    results = {}
    
    # Check backend services
    async with httpx.AsyncClient(timeout=2.0) as client_http:
        for name, service_url in SERVICE_URLS.items():
            svc_entry = {"ok": False, "checked_at": datetime.utcnow().isoformat(), "message": None}
            health_url = f"{service_url.rstrip('/')}/health"
            try:
                resp = await client_http.get(health_url)
                svc_entry["ok"] = resp.status_code < 400
                try:
                    svc_entry["message"] = resp.json()
                except Exception:
                    svc_entry["message"] = resp.text
            except Exception as e:
                svc_entry["message"] = str(e)

            results[name] = svc_entry
        
        # Check Beelink status
        beelink_host = os.getenv("BEELINK_HOST", "192.168.68.51")
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", beelink_host],
                capture_output=True, timeout=3
            )
            beelink_online = result.returncode == 0
            results["beelink"] = {
                "ok": beelink_online,
                "checked_at": datetime.utcnow().isoformat(),
                "message": {"status": "online" if beelink_online else "offline", "host": beelink_host}
            }
            
            # Check llama.cpp if beelink is online
            if beelink_online:
                llama_url = f"http://{beelink_host}:11434/health"
                try:
                    resp = await client_http.get(llama_url)
                    results["llama"] = {
                        "ok": resp.status_code < 400,
                        "checked_at": datetime.utcnow().isoformat(),
                        "message": {"status": "running", "url": llama_url}
                    }
                except Exception:
                    results["llama"] = {"ok": False, "checked_at": datetime.utcnow().isoformat(), "message": "Not responding"}
            else:
                results["llama"] = {"ok": False, "checked_at": datetime.utcnow().isoformat(), "message": "Beelink offline"}
        except Exception as e:
            results["beelink"] = {"ok": False, "checked_at": datetime.utcnow().isoformat(), "message": str(e)}
            results["llama"] = {"ok": False, "checked_at": datetime.utcnow().isoformat(), "message": "Check failed"}
    
    # Infer k3s status from service health (simpler than K8s API which isn't accessible)
    # Count healthy services as a proxy for pod health
    services_checked = len(results)
    services_healthy = sum(1 for v in results.values() if v.get("ok", False))
    
    results["k3s"] = {
        "ok": services_healthy >= (services_checked * 0.5),  # At least 50% healthy
        "checked_at": datetime.utcnow().isoformat(),
        "message": {
            "status": "inferred_from_services",
            "services_total": services_checked,
            "services_healthy": services_healthy,
            "note": "Pod counts unavailable (K8s API not accessible from pod)"
        }
    }

    # Provide top-level boolean flags for backward compatibility
    out = {}
    all_ok = True
    for k, v in results.items():
        out[k] = bool(v.get("ok", False))
        if not v.get("ok", False):
            all_ok = False

    # Backwards-compatible aliases expected by frontend
    out["gateway"] = True
    out["reminders"] = out.get("reminder", out.get("reminders", False))
    out["finance"] = out.get("financial", out.get("finance", False))

    out["status"] = "online" if all_ok else "degraded"
    out["checked_at"] = datetime.utcnow().isoformat()
    out["details"] = results

    return out


def _parse_prometheus_metrics(text: str, service_label: str):
    """Lightweight Prometheus exposition parser for a small metric subset.

    Extracts circuit-breaker related metrics and ignores the rest to keep
    latency minimal and avoid pulling in heavy parsers.
    """
    target_metrics = {
        "cb_open": None,
        "cb_open_until": None,
        "cb_failures_total": None,
        "cb_skips_total": None,
        "cb_success_total": None,
    }

    if not text:
        return target_metrics

    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        for metric_name in list(target_metrics.keys()):
            if not line.startswith(metric_name):
                continue

            # Ensure we only capture the metric for this service label if present
            if "{" in line and f'service="{service_label}"' not in line:
                continue

            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                target_metrics[metric_name] = float(parts[-1])
            except ValueError:
                continue
    return target_metrics


@app.get("/admin/metrics/summary")
async def admin_metrics_summary(request: Request):
    """Summarize Prometheus circuit-breaker metrics from core services.

    Requires admin auth (X-Admin-Token or LIBRARY_ADMIN_KEY). Returns a small
    JSON payload so the admin UI can render a status card without parsing the
    entire exposition format.
    """
    if not _is_admin_request(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    import httpx
    from datetime import datetime

    services_to_query = {
        "meds": SERVICE_URLS.get("meds"),
        "reminder": SERVICE_URLS.get("reminder"),
        "habits": SERVICE_URLS.get("habits"),
    }

    results = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, base_url in services_to_query.items():
            entry = {"ok": False, "fetched_at": datetime.utcnow().isoformat(), "metrics": None, "message": None}
            if not base_url:
                entry["message"] = "no service url"
                results[name] = entry
                continue

            metrics_url = f"{base_url.rstrip('/')}/metrics"
            try:
                resp = await client.get(metrics_url)
                entry["ok"] = resp.status_code < 400
                if resp.status_code < 400:
                    entry["metrics"] = _parse_prometheus_metrics(resp.text, service_label=name)
                else:
                    entry["message"] = f"status {resp.status_code}"
            except Exception as e:
                entry["message"] = str(e)
            results[name] = entry

    return {"services": results, "generated_at": datetime.utcnow().isoformat()}


# Duplicate admin routes with /api prefix for compatibility with frontend
@app.get("/api/admin/status")
async def api_admin_status():
    """Alias for /admin/status to support frontend routing through /api"""
    return await admin_status()


@app.get("/api/admin/metrics/summary")
async def api_admin_metrics_summary(request: Request):
    """Alias for /admin/metrics/summary to support frontend routing through /api"""
    return await admin_metrics_summary(request)


async def _proxy(request: Request, service: str, path: str):
    service_url = SERVICE_URLS.get(service)
    if not service_url:
        raise HTTPException(status_code=404, detail="Service not found")

    url = f"{service_url}/{path}"
    headers = dict(request.headers)
    # The Host header should be the service's host, not the gateway's
    headers["host"] = service_url.split("://")[1].split(":")[0]

    # Remove content-length as we may be streaming
    headers.pop("content-length", None)

    # Use persistent HTTP client with retries for reliability
    global http_client
    if not http_client:
        raise HTTPException(status_code=503, detail="Gateway HTTP client not initialized")
    
    retries = 2
    backoff = 0.5
    last_exc = None
    
    for attempt in range(1, retries + 1):
        start_ts = time.time()
        try:
            # Check if this is a multipart/form-data request (file upload)
            content_type = request.headers.get("content-type", "")

            if "multipart/form-data" in content_type:
                # For multipart, stream the body directly to preserve boundaries
                req = http_client.build_request(
                    request.method,
                    url,
                    headers=headers,
                    params=request.query_params,
                    content=request.stream()  # Stream instead of body()
                )
            else:
                # For regular requests, use body
                req = http_client.build_request(
                    request.method,
                    url,
                    headers=headers,
                    params=request.query_params,
                    content=await request.body()
                )
            resp = await http_client.send(req, stream=True)
            elapsed = time.time() - start_ts

            # Log slow responses for ai_brain specifically
            if service == 'ai_brain' and elapsed > 3.0:
                logger.warning(f"ai_brain slow response: {request.method} {path} took {elapsed:.2f}s (attempt {attempt})")

            content_type = resp.headers.get("content-type", "application/json")
            data = await resp.aread()

            # Handle binary responses (images, PDFs, etc.)
            if content_type.startswith("image/") or content_type == "application/pdf":
                from fastapi.responses import Response as FastAPIResponse
                logger.info(f"Proxy OK: {request.method} {url} -> {resp.status_code} in {elapsed:.2f}s")
                return FastAPIResponse(content=data, media_type=content_type, status_code=resp.status_code)

            # Handle JSON responses
            import json
            try:
                parsed = json.loads(data)
                logger.info(f"Proxy OK: {request.method} {url} -> {resp.status_code} in {elapsed:.2f}s")
                return JSONResponse(content=parsed, status_code=resp.status_code)
            except Exception:
                try:
                    text_content = data.decode('utf-8')
                    logger.info(f"Proxy OK (text): {request.method} {url} -> {resp.status_code} in {elapsed:.2f}s")
                    return JSONResponse(content={"raw": text_content}, status_code=resp.status_code)
                except UnicodeDecodeError:
                    import base64
                    logger.info(f"Proxy OK (binary): {request.method} {url} -> {resp.status_code} in {elapsed:.2f}s")
                    return JSONResponse(content={"raw_base64": base64.b64encode(data).decode()}, status_code=resp.status_code)

        except httpx.RequestError as e:
            elapsed = time.time() - start_ts
            logger.error(f"Proxy request error to {service} {url} (attempt {attempt}/{retries}) after {elapsed:.2f}s: {e}")
            last_exc = e
            if attempt < retries:
                await asyncio.sleep(backoff * attempt)
                continue
            else:
                raise HTTPException(status_code=502, detail=f"Bad Gateway: {e}")
    
    # Should never reach here, but just in case
    if last_exc:
        raise HTTPException(status_code=502, detail=f"Bad Gateway: {last_exc}")


# Socket.IO support for real-time updates (optional dependency)
# NOTE: Mount Socket.IO BEFORE proxy routes so it takes precedence
try:
    import socketio
except ImportError:  # pragma: no cover - optional path for minimal installs
    socketio = None
    logger.warning("python-socketio not installed; skipping real-time updates")

if socketio:
    # Create Socket.IO server
    sio = socketio.AsyncServer(
        async_mode='asgi',
        cors_allowed_origins='*',
        logger=False,
        engineio_logger=False
    )

    # Wrap with ASGI app
    # NOTE: socketio_path must be empty because FastAPI's mount() strips the /socket.io prefix
    socket_app = socketio.ASGIApp(
        socketio_server=sio,
        socketio_path=''
    )

    # Mount Socket.IO app
    app.mount('/socket.io', socket_app)

    @sio.event
    async def connect(sid, environ):
        logger.info(f"Socket.IO client connected: {sid}")
        await sio.emit('connected', {'status': 'ok'}, room=sid)

    @sio.event
    async def disconnect(sid):
        logger.info(f"Socket.IO client disconnected: {sid}")

    @sio.event
    async def ping(sid, data):
        """Handle ping from client"""
        await sio.emit('pong', {'timestamp': time.time()}, room=sid)


    # Socket.IO emit endpoint for broadcasting events
    @app.post("/emit")
    async def emit_event(payload: dict):
        """Broadcast Socket.IO event to all connected clients"""
        if not socketio:
            return {"status": "error", "message": "Socket.IO not available"}
        
        event = payload.get("event", "message")
        data = payload.get("data", {})
        
        await sio.emit(event, data)
        logger.info(f"Broadcasted Socket.IO event: {event}")
        
        return {"status": "ok", "message": "Event broadcast"}



# ═══════════════════════════════════════════════════════════════════════════
# Kubernetes Management Endpoints
# ═══════════════════════════════════════════════════════════════════════════
import subprocess
import json

@app.get("/k8s/pods")
async def get_pods():
    """Get all pods in kilo-guardian namespace"""
    try:
        result = subprocess.run(
            ['kubectl', 'get', 'pods', '-n', 'kilo-guardian', '-o', 'json'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return []
        
        data = json.loads(result.stdout)
        pods = []
        for item in data.get('items', []):
            status = item['status'].get('phase', 'Unknown')
            if item['status'].get('containerStatuses'):
                for cs in item['status']['containerStatuses']:
                    if cs.get('state', {}).get('waiting', {}).get('reason') == 'CrashLoopBackOff':
                        status = 'CrashLoopBackOff'
            
            pods.append({
                'name': item['metadata']['name'],
                'status': status,
                'restarts': sum(cs.get('restartCount', 0) for cs in item['status'].get('containerStatuses', [])),
                'age': item['metadata'].get('creationTimestamp', ''),
                'node': item['spec'].get('nodeName', ''),
                'ready': f"{sum(1 for cs in item['status'].get('containerStatuses', []) if cs.get('ready', False))}/{len(item['status'].get('containerStatuses', []))}"
            })
        return pods
    except Exception as e:
        logger.error(f"Error getting pods: {e}")
        return []

@app.get("/k8s/nodes")
async def get_nodes():
    """Get all cluster nodes"""
    try:
        result = subprocess.run(
            ['kubectl', 'get', 'nodes', '-o', 'json'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return []
        
        data = json.loads(result.stdout)
        nodes = []
        for item in data.get('items', []):
            status = 'NotReady'
            for cond in item['status'].get('conditions', []):
                if cond['type'] == 'Ready' and cond['status'] == 'True':
                    status = 'Ready'
                    break
            
            nodes.append({
                'name': item['metadata']['name'],
                'status': status,
                'roles': ','.join([k.split('/')[-1] for k in item['metadata'].get('labels', {}).keys() if 'node-role' in k]),
                'age': item['metadata'].get('creationTimestamp', ''),
                'version': item['status'].get('nodeInfo', {}).get('kubeletVersion', ''),
                'cpu': '0%',
                'memory': '0%'
            })
        return nodes
    except Exception as e:
        logger.error(f"Error getting nodes: {e}")
        return []

@app.get("/k8s/cronjobs")
async def get_cronjobs():
    """Get all cronjobs in kilo-guardian namespace"""
    try:
        result = subprocess.run(
            ['kubectl', 'get', 'cronjobs', '-n', 'kilo-guardian', '-o', 'json'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return []
        
        data = json.loads(result.stdout)
        cronjobs = []
        for item in data.get('items', []):
            cronjobs.append({
                'name': item['metadata']['name'],
                'schedule': item['spec'].get('schedule', ''),
                'last_schedule': item['status'].get('lastScheduleTime', ''),
                'active': len(item['status'].get('active', [])),
                'suspended': item['spec'].get('suspend', False)
            })
        return cronjobs
    except Exception as e:
        logger.error(f"Error getting cronjobs: {e}")
        return []

@app.post("/k8s/pods/{pod_name}/restart")
async def restart_pod(pod_name: str):
    """Restart a pod by deleting it (k8s will recreate it)"""
    try:
        result = subprocess.run(
            ['kubectl', 'delete', 'pod', pod_name, '-n', 'kilo-guardian'],
            capture_output=True, text=True, timeout=30
        )
        return {"success": result.returncode == 0, "message": result.stdout or result.stderr}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.delete("/k8s/pods/{pod_name}")
async def delete_pod(pod_name: str):
    """Delete a pod"""
    try:
        result = subprocess.run(
            ['kubectl', 'delete', 'pod', pod_name, '-n', 'kilo-guardian', '--force', '--grace-period=0'],
            capture_output=True, text=True, timeout=30
        )
        return {"success": result.returncode == 0, "message": result.stdout or result.stderr}
    except Exception as e:
        return {"success": False, "message": str(e)}



@app.get("/observations")
async def get_observations(limit: int = 20):
    """Proxy GET /observations to kilo-ai-brain"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"http://kilo-ai-brain:9004/observations", params={"limit": limit})
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/observations")
async def post_observation(request: Request):
    """Proxy POST /observations to kilo-ai-brain"""
    try:
        body = await request.body()
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "http://kilo-ai-brain:9004/observations",
                content=body,
                headers={"Content-Type": "application/json"}
            )
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# Dedicated /chat routes that forward to ai_brain preserving the full path
@app.api_route("/chat/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_chat(request: Request, path: str):
    return await _proxy(request, "ai_brain", f"chat/{path}")

@app.api_route("/api/chat/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_api_chat(request: Request, path: str):
    return await _proxy(request, "ai_brain", f"chat/{path}")

@app.api_route("/api/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_all_api(request: Request, service: str, path: str):
    return await _proxy(request, service, path)

@app.api_route("/api/{service}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_root_api(request: Request, service: str):
    return await _proxy(request, service, "")

# NOTE: Catch-all routes enabled but exclude socket.io to allow WebSocket connections
# Frontend can call either /api/service or /service directly
@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_all(request: Request, service: str, path: str):
    # Don't proxy socket.io through this route - let it be handled separately
    if service == "socket.io":
        raise HTTPException(status_code=404, detail="Not found")
    return await _proxy(request, service, path)

@app.api_route("/{service}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_root(request: Request, service: str):
    # Don't proxy socket.io through this route - let it be handled separately
    if service == "socket.io":
        raise HTTPException(status_code=404, detail="Not found")
    return await _proxy(request, service, "")


