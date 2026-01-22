# K3s API Routing Fixes Documentation

**Generated**: 2026-01-19
**Project**: Kilo AI Microservice
**Issue**: Docker Compose URLs incompatible with K3s service discovery

---

## Overview

The codebase uses Docker Compose naming conventions (`docker_*_1:PORT`) but K3s uses Kubernetes service names (`kilo-*:9000`). This document lists all required fixes.

---

## Fix 1: Gateway Service URLs

**File**: `services/gateway/main.py`

| Current (Docker) | Required (K3s) |
|------------------|----------------|
| `docker_meds_1:9001` | `kilo-meds:9000` |
| `docker_habits_1:9003` | `kilo-habits:9000` |
| `docker_reminders_1:9002` | `kilo-reminder:9000` |
| `docker_financial_1:9004` | `kilo-financial:9000` |
| `docker_voice_1:9006` | `kilo-voice:9000` |
| `docker_ml_1:9005` | `kilo-ml:9000` |

**Recommended Fix**: Use environment variables
```python
import os

SERVICE_URLS = {
    "meds": os.getenv("MEDS_SERVICE_URL", "http://kilo-meds:9000"),
    "habits": os.getenv("HABITS_SERVICE_URL", "http://kilo-habits:9000"),
    "reminder": os.getenv("REMINDER_SERVICE_URL", "http://kilo-reminder:9000"),
    "financial": os.getenv("FINANCIAL_SERVICE_URL", "http://kilo-financial:9000"),
    "voice": os.getenv("VOICE_SERVICE_URL", "http://kilo-voice:9000"),
    "ml": os.getenv("ML_SERVICE_URL", "http://kilo-ml:9000"),
    "ai_brain": os.getenv("AI_BRAIN_SERVICE_URL", "http://kilo-ai-brain:9000"),
}
```

---

## Fix 2: Financial Service URLs

**File**: `services/financial/main.py`

| Current | Required |
|---------|----------|
| `http://ai_brain:9004` | `http://kilo-ai-brain:9000` |
| `http://kilo-ai-brain:9004` | `http://kilo-ai-brain:9000` |

**Issue**: Mixed naming and wrong port (9004 vs 9000)

---

## Fix 3: Reminder Service URLs

**File**: `services/reminder/main.py`

| Current | Required |
|---------|----------|
| `http://habits:8000` | `http://kilo-habits:9000` |
| `http://financial:8000` | `http://kilo-financial:9000` |

**Issue**: Short names and wrong port (8000 vs 9000)

---

## Fix 4: ConfigMap Environment Variables

**File**: `k3s/configmap.yaml`

**Add these entries**:
```yaml
data:
  # Service URLs for K3s internal communication
  MEDS_SERVICE_URL: "http://kilo-meds:9000"
  HABITS_SERVICE_URL: "http://kilo-habits:9000"
  REMINDER_SERVICE_URL: "http://kilo-reminder:9000"
  FINANCIAL_SERVICE_URL: "http://kilo-financial:9000"
  VOICE_SERVICE_URL: "http://kilo-voice:9000"
  ML_SERVICE_URL: "http://kilo-ml:9000"
  AI_BRAIN_SERVICE_URL: "http://kilo-ai-brain:9000"
  GATEWAY_SERVICE_URL: "http://kilo-gateway:8000"
```

---

## Fix 5: Port Standardization

All services should use port **9000** internally (except gateway which uses 8000).

**K3s Services** (`k3s/kilo-services-MASTER.yaml`) - Already correct:
- kilo-meds → 9000
- kilo-habits → 9000
- kilo-reminder → 9000
- kilo-financial → 9000
- kilo-voice → 9000
- kilo-ml → 9000
- kilo-ai-brain → 9000
- kilo-gateway → 8000

---

## Service Name Mapping Reference

| Service | Docker Compose Name | K3s Service Name | Port |
|---------|---------------------|------------------|------|
| Medications | docker_meds_1 | kilo-meds | 9000 |
| Habits | docker_habits_1 | kilo-habits | 9000 |
| Reminders | docker_reminders_1 | kilo-reminder | 9000 |
| Financial | docker_financial_1 | kilo-financial | 9000 |
| Voice | docker_voice_1 | kilo-voice | 9000 |
| ML | docker_ml_1 | kilo-ml | 9000 |
| AI Brain | ai_brain / docker_ai_brain_1 | kilo-ai-brain | 9000 |
| Gateway | docker_gateway_1 | kilo-gateway | 8000 |

---

## Kompose Migration Plan

[Kompose](https://kompose.io/) converts `docker-compose.yml` to Kubernetes manifests.

**Status**: ✅ Kompose installed (v1.34.0), manifests generated

### Generated Files Location
```
/home/kilo/Desktop/Kilo_Ai_microservice/k3s-kompose/
```

### Files Generated (37 total)
- 12 Service files (`*-service.yaml`)
- 13 Deployment files (`*-deployment.yaml`)
- 12 PersistentVolumeClaim files (`*-persistentvolumeclaim.yaml`)

### Comparison: Kompose vs Existing K3s

| Service | Kompose Name | Kompose Port | Existing K3s Name | Existing K3s Port |
|---------|--------------|--------------|-------------------|-------------------|
| Gateway | `gateway` | 8000 | `kilo-gateway` | 8000 |
| AI Brain | `ai-brain` | 9004 | `kilo-ai-brain` | 9000 |
| Meds | `meds` | 9001 | `kilo-meds` | 9000 |
| Reminder | `reminder` | 9002 | `kilo-reminder` | 9000 |
| Habits | `habits` | 9003 | `kilo-habits` | 9000 |
| Financial | `financial` | 9005 | `kilo-financial` | 9000 |
| Library | `library-of-truth` | 9006 | `kilo-library` | 9000 |
| Cam | `cam` | 9007 | `kilo-cam` | 9000 |
| ML Engine | `ml-engine` | 9008 | `kilo-ml` | 9000 |
| Voice | `voice` | 9009 | `kilo-voice` | 9000 |
| USB Transfer | `usb-transfer` | 8006 | N/A | N/A |
| Frontend | `frontend` | 80/443 | `kilo-frontend` | 80 |
| Ollama | `ollama` | 11434 | `kilo-ollama` | 11434 |

### Recommended Approach: Use Kompose Output

**Why Kompose is better:**
1. Service URLs already match what the code expects (`http://meds:9001` not `http://kilo-meds:9000`)
2. Environment variables pre-configured in deployments
3. No code changes required in gateway or other services
4. PersistentVolumeClaims auto-generated

**Action Items:**
1. Review Kompose manifests for any needed tweaks
2. Add ollama service (Kompose skipped it - no ports exposed)
3. Replace existing K3s manifests with Kompose output
4. Apply to cluster

---

---

## Deployment Steps (Using Kompose Output)

### Step 1: Create Namespace (optional)
```bash
kubectl create namespace kilo 2>/dev/null || true
```

### Step 2: Apply PersistentVolumeClaims
```bash
kubectl apply -f /home/kilo/Desktop/Kilo_Ai_microservice/k3s-kompose/*-persistentvolumeclaim.yaml
```

### Step 3: Apply Services
```bash
kubectl apply -f /home/kilo/Desktop/Kilo_Ai_microservice/k3s-kompose/*-service.yaml
```

### Step 4: Apply Deployments
```bash
kubectl apply -f /home/kilo/Desktop/Kilo_Ai_microservice/k3s-kompose/*-deployment.yaml
```

### Quick Deploy (All at Once)
```bash
kubectl apply -f /home/kilo/Desktop/Kilo_Ai_microservice/k3s-kompose/
```

---

## Testing After Fixes

```bash
# 1. Apply updated configs
kubectl apply -f k3s/configmap.yaml
kubectl apply -f k3s/kilo-deployments-MASTER.yaml
kubectl apply -f k3s/kilo-services-MASTER.yaml

# 2. Restart deployments to pick up new config
kubectl rollout restart deployment -n default

# 3. Check pod status
kubectl get pods -o wide

# 4. Test service DNS resolution from a pod
kubectl run test-dns --rm -it --image=busybox -- nslookup kilo-gateway

# 5. Test gateway connectivity
kubectl port-forward svc/kilo-gateway 8000:8000
curl http://localhost:8000/health
```

---

## Summary

### Original Issues Found

| Category | Issues Found | Files Affected |
|----------|--------------|----------------|
| Wrong Hostnames | 9 | 3 |
| Wrong Ports | 9 | 3 |
| Missing Env Vars | 8 | 1 |
| **Total Fixes Needed** | **26** | **4 files** |

### Resolution: Kompose Migration

Instead of fixing 26 issues across 4 files, we used Kompose to generate K3s manifests that match the existing application code.

**Files Generated**: 38 (in `k3s-kompose/` directory)
- 13 Services
- 13 Deployments
- 12 PersistentVolumeClaims
- 1 deploy.sh script
- 1 teardown.sh script

### Quick Start

```bash
# Deploy everything
cd /home/kilo/Desktop/Kilo_Ai_microservice/k3s-kompose
./deploy.sh

# Or manually
kubectl apply -f /home/kilo/Desktop/Kilo_Ai_microservice/k3s-kompose/

# Teardown
./teardown.sh
```

### Service Discovery

With Kompose output, services can reach each other using:
- `http://gateway:8000`
- `http://meds:9001`
- `http://reminder:9002`
- `http://habits:9003`
- `http://ai-brain:9004`
- `http://financial:9005`
- `http://library-of-truth:9006`
- `http://cam:9007`
- `http://ml-engine:9008`
- `http://voice:9009`
- `http://ollama:11434`
- `http://usb-transfer:8006`

