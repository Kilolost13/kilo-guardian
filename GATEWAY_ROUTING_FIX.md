# GATEWAY ROUTING - PERMANENT FIX

## Problem: Why Does The System Keep Breaking?

Your Kilo Guardian system has a **two-layer routing architecture** that BOTH layers must work correctly:

```
Browser/Tablet
    ↓
[Layer 1] Traefik Ingress (192.168.68.62:80)
    ↓
[Layer 2] Gateway Service (gateway:8000)
    ↓
Backend Services (reminder, habits, financial, etc.)
```

### The Issue

**Layer 2** (Gateway) had its catch-all routes **commented out**, which caused:
- ❌ `/reminder/reminders` → 404 Not Found
- ❌ `/habits` → 404 Not Found
- ❌ `/financial/transactions` → 404 Not Found
- ✅ `/api/reminder/reminders` → Works (but frontend doesn't use this)

## The Root Causes

### 1. Gateway Routes Were Disabled
In `services/gateway/main.py`, these routes were commented out:

```python
# COMMENTED OUT (BROKEN):
# @app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
# async def proxy_all(request: Request, service: str, path: str):
#     return await _proxy(request, service, path)
```

**Why?** The comment said "disabled to allow Socket.IO mount at /socket.io"

**Problem:** This broke ALL frontend API calls that don't use `/api/` prefix

### 2. Ingress Was Routing Everything to Frontend
The `frontend-ingress.yaml` had a catch-all `/` path that intercepted service requests:

```yaml
# BROKEN - Catches everything including API calls
- path: /
  pathType: Prefix
  backend:
    service:
      name: frontend
```

## The Permanent Solution

### 1. Gateway Routes Fixed (`services/gateway/main.py`)

**Uncommented the catch-all routes** with Socket.IO protection:

```python
@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_all(request: Request, service: str, path: str):
    # Don't proxy socket.io - let it be handled separately
    if service == "socket.io":
        raise HTTPException(status_code=404, detail="Not found")
    return await _proxy(request, service, path)
```

Now gateway accepts BOTH:
- ✅ `/reminder/reminders`
- ✅ `/api/reminder/reminders`

### 2. Ingress Routing Fixed (`frontend-ingress.yaml`)

**Created TWO separate ingresses with priorities:**

```yaml
# HIGH PRIORITY (10) - Route service calls to gateway
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: gateway-ingress
  annotations:
    traefik.ingress.kubernetes.io/router.priority: "10"
spec:
  rules:
  - http:
      paths:
      - path: /api          # API calls
      - path: /reminder     # Service calls
      - path: /habits
      - path: /financial
      - path: /ai_brain
      - path: /socket.io    # WebSockets
        # ... etc
        backend:
          service:
            name: gateway
            port:
              number: 8000

---
# LOW PRIORITY (1) - Frontend catch-all
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: frontend-ingress
  annotations:
    traefik.ingress.kubernetes.io/router.priority: "1"
spec:
  rules:
  - http:
      paths:
      - path: /static       # Static assets
      - path: /             # Everything else
        backend:
          service:
            name: frontend
            port:
              number: 3000
```

**Priority matters!** Higher priority (10) routes are checked first.

### 3. Docker Image Management

**Problem:** k3s with `imagePullPolicy: Never` doesn't see new Docker builds

**Solution:** Import images into k3s's containerd:

```bash
# After building gateway image
docker save kilo/gateway:v2 | sudo k3s ctr images import -
```

## How to Prevent This From Breaking Again

### ✅ DO:

1. **Always test API routes directly** after gateway changes:
   ```bash
   curl http://192.168.68.62/reminder/reminders
   curl http://192.168.68.62/habits
   curl http://192.168.68.62/financial/transactions
   ```

2. **Check gateway logs** for 404s:
   ```bash
   kubectl logs -f $(kubectl get pods | grep gateway | awk '{print $1}')
   ```

3. **Import new gateway images** into k3s:
   ```bash
   docker save kilo/gateway:latest | sudo k3s ctr images import -
   kubectl delete pod $(kubectl get pods | grep gateway | awk '{print $1}')
   ```

4. **Verify ingress priorities** are set correctly:
   ```bash
   kubectl get ingress -o yaml | grep priority
   ```

### ❌ DON'T:

1. **DON'T comment out the catch-all routes** in gateway/main.py without understanding the impact
2. **DON'T create catch-all ingress rules** without setting priorities
3. **DON'T expect k3s to auto-pull local images** - always import them
4. **DON'T test only with `/api/` prefix** - frontend uses direct paths

## Verification Commands

```bash
# Test all service endpoints
curl http://192.168.68.62/reminder/reminders
curl http://192.168.68.62/habits
curl http://192.168.68.62/financial/transactions
curl http://192.168.68.62/ai_brain/stats/dashboard

# Check gateway is routing correctly
kubectl logs $(kubectl get pods | grep gateway | awk '{print $1}') | grep -E "200|404"

# Verify ingress rules
kubectl get ingress
kubectl describe ingress gateway-ingress
kubectl describe ingress frontend-ingress
```

## Current Status: ✅ FIXED

All service endpoints now return proper responses:
- ✅ `/reminder/reminders` → `{"reminders":[]}`
- ✅ `/habits` → `[]`
- ✅ `/financial/transactions` → `[]`
- ✅ WebSocket at `/socket.io` → Supported

**Date Fixed:** 2026-01-22
**Commit:** 5e1edca
**Image:** kilo/gateway:v2
