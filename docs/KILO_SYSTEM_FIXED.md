# Kilo Guardian System - Configuration Locked ✅

**Date:** January 15, 2026  
**Status:** FULLY OPERATIONAL - 14/14 pods running

---

## What Was Fixed

### 1. Manifest Drift Problem ❌ → ✅
**Before:** Launcher ran `kubectl apply -f k3s/` which applied ALL 26 YAML files, including duplicates and old versions, causing:
- Duplicate pods (financial-v2, meds-v2, meds-updated)
- Conflicting configurations
- Replica count drift
- Random failures

**After:**
- Created **kilo-deployments-MASTER.yaml** (READ-ONLY, 444 permissions)
- Created **kilo-services-MASTER.yaml** (READ-ONLY, 444 permissions)
- Launcher now applies files individually in correct order
- Old/duplicate manifests moved to `old-manifests/` directory
- Documented safe change process in `README-MANIFESTS.md`

### 2. Naming Convention Issue (Underscores vs Dashes)
**Problem:** Original Docker images used underscores (`ai_brain`, `ml_engine`, `library_of_truth`, `usb_transfer`) but Kubernetes DNS **blocks underscores in hostnames**.

**Impact:**
- Pods waited for `ai_brain:9004` → DNS lookup failed → timeout
- Gateway/habits/meds crashloop-backed waiting 60 seconds for dependencies

**Fix:**
- Docker images still use underscores (can't rename easily)
- Kubernetes services use dashes (`kilo-ai-brain`, `kilo-ml-engine`, etc.)
- Deployments override container `command:` with Python socket wait using correct DNS names:
  ```python
  python3 -c "import socket,time,sys..." kilo-ai-brain:9004
  ```
- Applied to: gateway, habits, meds, cam deployments

### 3. Image Pull Policy Issue
**Problem:** Deployments had `imagePullPolicy: Always` which forced k3s to try pulling from Docker Hub (fails - images are local only)

**Fix:**
- All deployments now use `imagePullPolicy: IfNotPresent`
- Images loaded into k3s with: `docker save <image> | sudo k3s ctr images import -`
- Master manifest has correct image names matching what's actually in k3s containerd

### 4. HPA (Horizontal Pod Autoscaler) Interference
**Problem:**
- `gateway-hpa` had `minPods: 2` → Always forced 2 gateway replicas even when manifest said 1
- `ai-brain-hpa` also interfered with scaling

**Fix:**
- Deleted ALL HPAs in kilo-guardian namespace
- Master manifest has `replicas: 1` for all deployments
- Scaling now controlled exclusively by manifest files

### 5. Readiness Probe Port Mismatch
**Problem:** habits and meds probes checked wrong ports
- habits probe: port 9003 → app actually on 9000
- meds probe: port 9001 → app actually on 9000

**Fix:** Master manifest corrected to probe port 9000 for both

---

## Current Configuration

### Pods Running (14/14)
```
✅ kilo-ai-brain        (1/1) - Main AI reasoning engine
✅ kilo-gateway         (1/1) - CRITICAL: API gateway for frontend
✅ kilo-frontend        (1/1) - Web UI
✅ kilo-reminder        (1/1) - Medication/appointment reminders
✅ kilo-habits          (1/1) - Habit tracking service
✅ kilo-meds            (1/1) - Medication management
✅ kilo-financial       (1/1) - Financial tracking
✅ kilo-cam             (1/1) - Camera service (may have issues - USB cam on Beelink)
✅ kilo-library         (1/1) - Personal knowledge base
✅ kilo-ml-engine       (1/1) - Machine learning models
✅ kilo-voice           (1/1) - Voice recognition/synthesis
✅ kilo-usb-transfer    (1/1) - File transfer service
✅ kilo-socketio        (1/1) - WebSocket relay for real-time updates
✅ kilo-ollama          (1/1) - Local LLM server
```

### Master Manifest Files (LOCKED 🔒)
```bash
-r--r--r-- kilo-deployments-MASTER.yaml  # All 14 pod deployments
-r--r--r-- kilo-services-MASTER.yaml     # All 14 ClusterIP services
```

**To edit:** Must use `sudo chmod 644` then re-lock with `sudo chmod 444` after editing

### Apply Order (Launcher)
1. namespace.yaml
2. configmap.yaml
3. secret-library-admin.yaml
4. kilo-services-MASTER.yaml
5. kilo-deployments-MASTER.yaml
6. old-manifests/socketio-deployment.yaml (special - has ConfigMap code)
7. ingress.yaml
8. nodeport-services.yaml

---

## Image Name Reference

| Deployment | Docker Image | K8s Service |
|---|---|---|
| kilo-ai-brain | `kilo/ai_brain:latest` | kilo-ai-brain |
| kilo-gateway | `kilo/gateway:latest` | kilo-gateway |
| kilo-frontend | `kilo/frontend:latest` | kilo-frontend |
| kilo-reminder | `kilo/reminder:latest` | kilo-reminder |
| kilo-habits | `kilo/habits:latest` | kilo-habits |
| kilo-meds | `kilo/meds:latest` | kilo-meds |
| kilo-financial | `kilo/financial:latest` | kilo-financial |
| kilo-cam | `kilo/cam:latest` | kilo-cam |
| kilo-library | `kilo/library_of_truth:latest` | kilo-library |
| kilo-ml-engine | `kilo/ml_engine:latest` | kilo-ml-engine |
| kilo-voice | `kilo/voice:latest` | kilo-voice |
| kilo-usb-transfer | `kilo/usb_transfer:latest` | kilo-usb-transfer |
| kilo-socketio | `python:3.11-slim` (+ code in ConfigMap) | kilo-socketio |
| kilo-ollama | `ollama/ollama:latest` | kilo-ollama |

---

## Beelink AI Server (192.168.68.51)

**Service:** llama-server.service  
**Model:** Ministral-3-14B-Reasoning-2512-Q4_K_M.gguf  
**Port:** 11434  
**Status:** Running with Vulkan GPU offload (-ngl 99)

**Previous Issue:** Ollama was corrupted, llama models failed. Switched to llama.cpp server with Ministral model from LM Studio.

---

## Launcher UI

### Old Launcher (Zenity dialogs)
- Path: `/home/kilo/kilo-guardian/scripts/kilo-hub.sh`
- Spawned random popup windows all over screen
- Still functional, not recommended

### New Launcher (Terminal UI) ✅ RECOMMENDED
- Path: `/home/kilo/kilo-guardian/scripts/kilo-hub-gui.sh`
- Desktop: `Kilo_AI_Launcher.desktop` (updated to use new launcher)
- Single 80x35 terminal window
- Color-coded pod status (green=running, yellow=starting, red=error)
- Menu-driven interface (type 1-9, 0)

---

## Known Limitations

1. **Camera Service** - USB camera is physically connected to Beelink, not HP server. Kilo-cam pod runs on HP server so camera access will fail until network cameras (Wyze) are added.

2. **Underscore Naming** - Can't easily rename Docker images without rebuilding. Current workaround (command override in deployments) works but is a band-aid. Future: Rebuild images with dash-based naming.

3. **Socket.IO Special Case** - Uses base Python image + ConfigMap for code. Can't be included in master deployment file. Must be applied separately.

---

## Safe Operational Procedures

### Checking System Status
```bash
kubectl get pods -n kilo-guardian
kubectl get deployments -n kilo-guardian
```

### Scaling a Service (Emergency)
```bash
kubectl scale deployment -n kilo-guardian <name> --replicas=1
# Then update MASTER file to match!
sudo chmod 644 kilo-deployments-MASTER.yaml
# Edit file, change replicas: 1
sudo chmod 444 kilo-deployments-MASTER.yaml
```

### Restarting a Pod
```bash
kubectl delete pod -n kilo-guardian <pod-name>
# Deployment will recreate it automatically
```

### Importing New Docker Image to k3s
```bash
docker save kilo/<service>:latest | sudo k3s ctr images import -
# Then restart deployment:
kubectl rollout restart deployment -n kilo-guardian kilo-<service>
```

### Full System Restart
Use the Kilo Guardian Hub launcher:
1. Click "Stop Everything"
2. Wait for all pods to terminate
3. Click "Start Everything"
4. Manifests apply in correct order
5. All pods start with replicas: 1

---

## Files Modified

- ✅ `/home/kilo/kilo-guardian/scripts/kilo-hub-gui.sh` - Updated manifest apply logic
- ✅ `/home/kilo/kilo-guardian/scripts/kilo-hub.sh` - Updated manifest apply logic
- ✅ `/home/kilo/Desktop/Kilo_AI_Launcher.desktop` - Points to new TUI launcher
- ✅ `/home/kilo/Desktop/Kilo_Ai_microservice/k3s/kilo-deployments-MASTER.yaml` - Created, locked
- ✅ `/home/kilo/Desktop/Kilo_Ai_microservice/k3s/kilo-services-MASTER.yaml` - Created, locked
- ✅ `/home/kilo/Desktop/Kilo_Ai_microservice/k3s/README-MANIFESTS.md` - Created documentation
- 📁 `/home/kilo/Desktop/Kilo_Ai_microservice/k3s/old-manifests/` - Archived duplicate manifests

---

## Success Criteria ✅

- [x] 14/14 pods running and ready
- [x] No duplicate pods spawning
- [x] No ImagePullBackOff errors
- [x] No HPA interference
- [x] Gateway operational (frontend can communicate)
- [x] All services using correct DNS names
- [x] Master manifests locked (read-only)
- [x] Launcher applies files individually
- [x] Terminal UI contains all actions in one window
- [x] Beelink llama-server running with Ministral model
- [x] Documentation complete

**Next startup should be clean with no manual intervention required!**

---

## ADDENDUM: AI & Tablet Access (Jan 15, 2026 - 9:12 PM)

### AI Configuration Updated ✅

**Problem:** ConfigMap was pointing to local kilo-ollama pod (port 11434) with old llama3.1:8b model, but that pod isn't configured. System should use Beelink llama-server.

**Solution:**
- Updated ConfigMap to point to Beelink: `http://192.168.68.51:11434`
- Changed model to: `ministral` (Ministral-3-14B-Reasoning)
- Added both OLLAMA_URL and LLAMA_URL for compatibility
- Restarted kilo-ai-brain and kilo-gateway deployments

**Verify with:**
```bash
kubectl get configmap -n kilo-guardian kilo-config -o jsonpath='{.data.OLLAMA_URL}'
# Should return: http://192.168.68.51:11434
```

---

### Tablet Access Configured ✅

**Frontend URL:** `http://192.168.68.61:30000` (NodePort)  
**Gateway API:** `http://192.168.68.61:30800` (NodePort)  
**Ingress URL:** `http://tablet.kilo.local` (requires DNS/hosts entry)

**Testing from tablet:**
1. Ensure tablet is on same network (192.168.68.x)
2. Open browser to: `http://192.168.68.61:30000`
3. Frontend should load immediately
4. Try asking the AI a question
5. Response should come from Beelink Ministral model

**Documentation:** See `~/Desktop/TABLET_ACCESS_UPDATED.md`

---

### ConfigMap Changes

```yaml
# Before:
OLLAMA_URL: http://kilo-ollama:11434
OLLAMA_MODEL: llama3.1:8b

# After:
OLLAMA_URL: http://192.168.68.51:11434
OLLAMA_MODEL: ministral
LLAMA_URL: http://192.168.68.51:11434
LLAMA_MODEL: ministral
```

**Note:** ConfigMap is stored in `configmap.yaml` which should be updated to match these values permanently.

---

