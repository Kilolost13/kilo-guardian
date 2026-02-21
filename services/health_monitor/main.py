from fastapi import FastAPI
import httpx
import asyncio
import logging
import ssl
import os
from datetime import datetime
from pathlib import Path

app = FastAPI(title="Kilo Health Monitor")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AI_BRAIN_URL = os.environ.get('AI_BRAIN_URL', 'http://kilo-ai-brain:9004')
NAMESPACE = 'kilo-guardian'

# In-cluster k8s credentials
TOKEN_FILE = '/var/run/secrets/kubernetes.io/serviceaccount/token'
CA_FILE = '/var/run/secrets/kubernetes.io/serviceaccount/ca.crt'
K8S_API = 'https://kubernetes.default.svc'

alert_cooldown: dict = {}
restart_cooldown: dict = {}

SERVICES = {
    'ai_brain':  'http://kilo-ai-brain:9004/health',
    'gateway':   'http://kilo-gateway:8000/health',
    'meds':      'http://kilo-meds:9000/health',
    'habits':    'http://kilo-habits:9000/health',
    'reminder':  'http://kilo-reminder:9002/health',
    'financial': 'http://kilo-financial:9005/health',
    'library':   'http://kilo-library:9006/health',
    'voice':     'http://kilo-voice:9008/health',
    'ml_engine': 'http://kilo-ml-engine:9009/health',
}

service_status: dict = {}


def _get_token() -> str:
    try:
        return Path(TOKEN_FILE).read_text().strip()
    except Exception:
        return ''


def _k8s_client() -> httpx.AsyncClient:
    token = _get_token()
    ctx = ssl.create_default_context(cafile=CA_FILE) if Path(CA_FILE).exists() else ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return httpx.AsyncClient(
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        verify=False,
        timeout=10.0
    )


def _cooldown_ok(key: str, seconds: int = 300) -> bool:
    last = alert_cooldown.get(key)
    if last and (datetime.now() - last).total_seconds() < seconds:
        return False
    alert_cooldown[key] = datetime.now()
    return True


def _restart_ok(pod_name: str) -> bool:
    last = restart_cooldown.get(pod_name)
    if last and (datetime.now() - last).total_seconds() < 600:
        return False
    restart_cooldown[pod_name] = datetime.now()
    return True


async def notify_kilo(content: str, priority: str = 'high'):
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f'{AI_BRAIN_URL}/observations',
                json={'source': 'health_monitor', 'content': content,
                      'priority': priority, 'metadata': {'auto': True}}
            )
    except Exception as e:
        logger.error(f"notify_kilo failed: {e}")


async def k8s_get_pods() -> list:
    try:
        async with _k8s_client() as client:
            r = await client.get(f'{K8S_API}/api/v1/namespaces/{NAMESPACE}/pods')
            if r.status_code == 200:
                return r.json().get('items', [])
    except Exception as e:
        logger.error(f"k8s_get_pods failed: {e}")
    return []


async def k8s_delete_pod(pod_name: str) -> bool:
    try:
        async with _k8s_client() as client:
            r = await client.delete(
                f'{K8S_API}/api/v1/namespaces/{NAMESPACE}/pods/{pod_name}',
                params={'gracePeriodSeconds': '0'}
            )
            return r.status_code in (200, 202)
    except Exception as e:
        logger.error(f"k8s_delete_pod {pod_name} failed: {e}")
        return False


async def check_pod_health() -> list:
    pods = await k8s_get_pods()
    issues = []
    for pod in pods:
        name = pod['metadata']['name']
        phase = pod.get('status', {}).get('phase', '')
        for cs in pod.get('status', {}).get('containerStatuses', []):
            restarts = cs.get('restartCount', 0)
            reason = cs.get('state', {}).get('waiting', {}).get('reason', '')
            if reason == 'CrashLoopBackOff':
                issues.append(f"{name} CrashLoopBackOff")
                if _restart_ok(name):
                    ok = await k8s_delete_pod(name)
                    action = "restarted" if ok else "restart FAILED"
                    msg = f"🔧 SELF-HEAL: {name} was CrashLoopBackOff — {action}"
                    logger.warning(msg)
                    await notify_kilo(msg, 'high')
            elif restarts > 5 and _cooldown_ok(f"{name}_restarts", 1800):
                issues.append(f"{name} {restarts} restarts")
                await notify_kilo(f"⚠️ {name} has restarted {restarts} times", 'normal')
        if phase == 'Pending' and _cooldown_ok(f"{name}_pending", 600):
            issues.append(f"{name} stuck Pending")
            await notify_kilo(f"⚠️ {name} stuck in Pending state", 'high')
    return issues


async def check_service_endpoints() -> list:
    unhealthy = []
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in SERVICES.items():
            try:
                r = await client.get(url)
                if r.status_code == 200:
                    service_status[name] = 'healthy'
                else:
                    service_status[name] = f'http_{r.status_code}'
                    if _cooldown_ok(f"{name}_http"):
                        unhealthy.append(f"{name} HTTP {r.status_code}")
            except Exception as e:
                service_status[name] = 'unreachable'
                if _cooldown_ok(f"{name}_down"):
                    unhealthy.append(f"{name} unreachable")
    return unhealthy


async def health_check_loop():
    logger.info("🔍 Kilo Health Monitor v2 — checking every 60s")
    cycle = 0
    while True:
        try:
            cycle += 1
            pod_issues = await check_pod_health()
            svc_issues = await check_service_endpoints()
            all_issues = pod_issues + svc_issues
            healthy = sum(1 for s in service_status.values() if s == 'healthy')

            if all_issues:
                summary = "; ".join(all_issues)
                logger.warning(f"⚠️  Cycle {cycle} issues: {summary}")
                if _cooldown_ok('summary', 300):
                    await notify_kilo(
                        f"⚠️ SYSTEM ISSUES: {summary}. Self-healing attempted.",
                        'high'
                    )
            else:
                logger.info(f"✅ Cycle {cycle}: {healthy}/{len(service_status)} healthy")
        except Exception as e:
            logger.error(f"Loop error: {e}")
        await asyncio.sleep(60)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(health_check_loop())


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/status")
async def status():
    return {"services": service_status, "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9011)
