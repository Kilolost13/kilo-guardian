# Kilo Archive

Services and infrastructure that have been shut down to save resources.
Code is preserved here for reference. Each entry explains what it was, why it was shut down,
and what you'd need to do to bring it back.

---

## Ray Cluster (Distributed LLM inference)
**Shut down**: 2026-02-21
**What it was**: KubeRay operator running a Ray head pod on HP and a worker pod on Beelink. 
Ray Serve was used to load-balance LLM inference across both machines.
**Why archived**: CPU inference (~51s per response) was too slow for real use. 
Replaced by Gemini 2.0 Flash API (~1s response). 
**To restore**: Install KubeRay operator, deploy RayCluster manifest in k3s/old-manifests/. 
Would need a GPU node or a fast enough model to make it worthwhile.
**Resources that existed**: kilo-ray-head deployment, kilo-ray-serve NodePort 30800, 
kilo-ray-worker on Beelink, ~/scripts/deploy-ray-serve.sh on HP.

---

## vLLM Service
**Shut down**: 2026-02-21  
**What it was**: vLLM server deployment (NodePort 30950/30951) intended for faster local LLM inference.
**Why archived**: Never got a working model loaded. Gemini API is faster and easier.
**To restore**: Deploy with a GPU node. Manifest was in k3s/old-manifests/.

---

## Ollama k8s Service (kilo-ollama)
**Shut down**: 2026-02-21
**What it was**: A k8s ClusterIP service pointing at the HP host's Ollama process (port 11434).
**Why archived**: Gemini replaced Ollama as the primary LLM. 
HP host still has Ollama installed and running via systemctl (tinyllama model).
**To restore**:  a simple ExternalName or ClusterIP service pointing at 
192.168.68.57:11434. AI Brain env var OLLAMA_URL can be set to point at it as fallback.
**Note**: Ollama still runs on HP host (● ollama.service - Ollama Service
     Loaded: loaded (/etc/systemd/system/ollama.service; enabled; preset: enabled)
    Drop-In: /etc/systemd/system/ollama.service.d
             └─cpu-limit.conf, override.conf
     Active: active (running) since Wed 2026-02-18 16:56:00 CST; 3 days ago
   Main PID: 208433 (ollama)
      Tasks: 22 (limit: 25982)
     Memory: 106.6M (peak: 9.6G)
        CPU: 18min 55.877s
     CGroup: /system.slice/ollama.service
             └─208433 /usr/local/bin/ollama serve

Feb 21 14:25:48 pop-os ollama[208433]: [GIN] 2026/02/21 - 14:25:48 | 404 |       7.635µs |   192.168.68.57 | GET      "/health"
Feb 21 14:26:06 pop-os ollama[208433]: [GIN] 2026/02/21 - 14:26:06 | 404 |       8.716µs |   192.168.68.57 | GET      "/health"
Feb 21 14:26:36 pop-os ollama[208433]: [GIN] 2026/02/21 - 14:26:36 | 404 |       7.674µs |   192.168.68.57 | GET      "/health"
Feb 21 14:33:41 pop-os ollama[208433]: [GIN] 2026/02/21 - 14:33:41 | 404 |       5.049µs |   192.168.68.57 | GET      "/health"
Feb 21 14:34:34 pop-os ollama[208433]: [GIN] 2026/02/21 - 14:34:34 | 404 |        5.17µs |   192.168.68.57 | GET      "/health"
Feb 21 14:36:17 pop-os ollama[208433]: [GIN] 2026/02/21 - 14:36:17 | 404 |        5.41µs |   192.168.68.57 | GET      "/health"
Feb 21 14:39:44 pop-os ollama[208433]: [GIN] 2026/02/21 - 14:39:44 | 404 |        5.24µs |   192.168.68.57 | GET      "/health"
Feb 21 14:42:18 pop-os ollama[208433]: [GIN] 2026/02/21 - 14:42:18 | 404 |       4.298µs |   192.168.68.57 | GET      "/health"
Feb 21 14:54:50 pop-os ollama[208433]: [GIN] 2026/02/21 - 14:54:50 | 404 |       5.361µs |   192.168.68.57 | GET      "/health"
Feb 21 14:55:57 pop-os ollama[208433]: [GIN] 2026/02/21 - 14:55:57 | 404 |       4.098µs |   192.168.68.57 | GET      "/health"). Just no k8s service for it.

---

## Briefing Plugin
**Shut down**: 2026-02-21
**What it was**: Plugin (port 8003) that injected spending/briefing data into LLM prompts.
**Why archived**: Caused bugs — pre-injecting financial data prevented Gemini function calling 
from fetching fresh/filtered data. Spending queries returned stale totals regardless of date range.
**To restore**: Source in services/gateway/briefing/ or kilo-plugins/. 
Re-enable by deploying briefing deployment + adding route to gateway SERVICE_URLS.

---

## Drone Control Plugin
**Shut down**: 2026-02-21
**What it was**: Plugin (port 8002) for controlling a drone. Had 2 restarts, was idle.
**Why archived**: No drone connected. Consuming a pod slot on Beelink.
**To restore**: Source in ~/Desktop/kilo-plugins/drone-control/. 
Deploy as a deployment in kilo-guardian namespace.

---

## Security Monitor Plugin  
**Shut down**: 2026-02-21
**What it was**: Plugin (port 8001/8005) for security monitoring. Duplicate pods existed 
(security-monitor + kilo-security-monitor).
**Why archived**: Not connected to anything. Idle resource.
**To restore**: Source in ~/Desktop/kilo-plugins/security-monitor/. 
Deploy as deployment in kilo-guardian namespace.

---

## kilo-guardian (Plugin Engine)
**Shut down**: 2026-02-21
**What it was**: The original monolithic guardian service (port 8001) that served as a plugin engine.
**Why archived**: Replaced by individual microservices. Kept running as a legacy artifact.
**To restore**: The guardian:v6 image still exists on HP. Can deploy with any service code.

---

## kilo-reasoning-engine
**Shut down**: 2026-02-21
**What it was**: A placeholder deployment for a planned reasoning/deliberation system.
**Why archived**: Was an empty shell — health check returned OK but no logic implemented.
AI Brain now handles reasoning directly through Gemini function calling.
**To restore**: Build out a proper reasoning service, deploy with guardian:v6 image.

---

## kilo-socketio (standalone)
**Shut down**: 2026-02-21
**What it was**: A standalone Socket.IO relay service (port 9010).
**Why archived**: Duplicate functionality. The Gateway already mounts Socket.IO at /socket.io 
and has a /emit endpoint. Two socket servers caused confusion.
**To restore**: If gateway socket.io ever gets removed, deploy socketio-relay/main.py 
with a ClusterIP service at port 9010.

---

## kilo-marketing
**Shut down**: 2026-02-21
**What it was**: Static marketing/landing page (NodePort 30100).
**Why archived**: Not needed while system is in development.
**To restore**: Deploy with nginx image serving public/marketing.html from frontend build.

---

## kilo-meshtastic
**Shut down**: 2026-02-21
**What it was**: Placeholder for Meshtastic radio mesh network integration.
**Why archived**: Never implemented. No Meshtastic hardware connected.
**To restore**: Build a FastAPI service that interfaces with Meshtastic Python library.
Useful for off-grid/emergency communication.

---

## kilo-usb-transfer
**Shut down**: 2026-02-21
**What it was**: Service for transferring files via USB between machines.
**Why archived**: Nothing was using it.
**To restore**: Source in services/usb_transfer/. Deploy with guardian:v6 image, port 9010.

---

## kilo-voice
**Shut down**: 2026-02-21
**What it was**: Voice input/output service (port 9008). Intended for speech-to-text and TTS.
**Why archived**: Nothing was connected. No microphone/speaker integration built.
**To restore**: Source in services/voice/. Would need Whisper for STT and a TTS library.
Consider running on Beelink which has audio hardware.

---

## kilo-vpn-client
**Shut down**: 2026-02-21
**What it was**: VPN client pod (WireGuard or OpenVPN).
**Why archived**: Unclear what VPN server it was connecting to. Consuming resources.
**To restore**: Re-deploy with proper VPN config/secrets. Use k8s Secret for credentials.
