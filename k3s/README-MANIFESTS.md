# Kilo Guardian Kubernetes Manifests

**IMPORTANT: Master manifest files are READ-ONLY to prevent configuration drift!**

## File Structure

### Core Manifests (Apply in this order)
1. **namespace.yaml** - Creates kilo-guardian namespace
2. **configmap.yaml** - Environment configuration for all services
3. **secret-library-admin.yaml** - Admin credentials
4. **kilo-services-MASTER.yaml** - All ClusterIP services (READ-ONLY)
5. **kilo-deployments-MASTER.yaml** - All pod deployments (READ-ONLY)
6. **socketio-deployment.yaml** - Special: Socket.IO with ConfigMap code
7. **ingress.yaml** - HTTP ingress rules
8. **nodeport-services.yaml** - External NodePort services

### How to Make Changes

**DO NOT directly edit MASTER files or use `kubectl apply -f k3s/`!**

The launcher applies files individually to prevent conflicts:
```bash
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secret-library-admin.yaml
kubectl apply -f kilo-services-MASTER.yaml
kubectl apply -f kilo-deployments-MASTER.yaml
kubectl apply -f ingress.yaml
kubectl apply -f nodeport-services.yaml
```

#### To modify a deployment:
1. Edit the MASTER file
2. Make it read-only again: `chmod 444 kilo-deployments-MASTER.yaml`
3. Apply only that file: `kubectl apply -f kilo-deployments-MASTER.yaml`
4. Verify: `kubectl get deployments -n kilo-guardian`

#### To scale replicas:
```bash
kubectl scale deployment -n kilo-guardian <name> --replicas=1
# Then update the MASTER file to match!
```

## Known Issues / Naming Convention Problems

### Underscore vs Dash Problem
When the system was originally created, service names used underscores (ai_brain, ml_engine, etc.) which are **blocked characters in Kubernetes DNS**. This causes connection timeouts.

**Docker Image Names (with underscores):**
- `kilo/ai_brain:latest`
- `kilo/library_of_truth:latest`
- `kilo/ml_engine:latest`
- `kilo/usb_transfer:latest`

**Kubernetes Service Names (must use dashes):**
- `kilo-ai-brain` (DNS: kilo-ai-brain.kilo-guardian.svc.cluster.local)
- `kilo-library`
- `kilo-ml-engine`
- `kilo-usb-transfer`

**The Fix:**
Wait scripts inside Docker images reference `ai_brain:9004` which fails DNS lookup.
Deployments override the container command with Python socket wait using correct DNS names:
```python
python3 -c "import socket,time,sys;h,p=sys.argv[1].split(':');..." kilo-ai-brain:9004
```

### Image Pull Policy
All deployments use `imagePullPolicy: IfNotPresent` because images are built locally and imported into k3s:
```bash
docker save kilo/gateway:latest | sudo k3s ctr images import -
```

Never use `imagePullPolicy: Always` - it will try to pull from Docker Hub and fail!

### Current Pod Count
Expected: **14 pods running**
- kilo-ai-brain
- kilo-gateway
- kilo-frontend
- kilo-reminder
- kilo-habits
- kilo-meds
- kilo-financial
- kilo-cam (may fail - USB camera on Beelink not HP server)
- kilo-library
- kilo-ml-engine
- kilo-voice
- kilo-usb-transfer
- kilo-socketio
- kilo-ollama

## Old/Archived Manifests

The `old-manifests/` directory contains deprecated files:
- deployments-and-services.yaml (replaced by MASTER files)
- more-services.yaml (merged into MASTER)
- dns-fix-deployments.yaml (fixes merged into MASTER)
- fixed-deployments.yaml (fixes merged into MASTER)
- pdbs-and-hpas.yaml (HPAs deleted - caused replica drift)

**DO NOT apply files from old-manifests directory!**

## Troubleshooting

### Duplicate pods appearing:
- Multiple manifest files defining same deployment
- Check: `kubectl get rs -n kilo-guardian | grep <service>`
- Delete old ReplicaSets: `kubectl delete rs -n kilo-guardian <name>`

### ImagePullBackOff errors:
- Image not in k3s containerd
- Check: `sudo k3s ctr images ls | grep kilo`
- Import: `docker save kilo/<name>:latest | sudo k3s ctr images import -`

### Pods not becoming Ready:
- Wrong readiness probe port (habits/meds use 9000, not 9003/9001)
- DNS timeout waiting for dependencies (ai_brain vs kilo-ai-brain)
- Check logs: `kubectl logs -n kilo-guardian <pod-name>`

### Gateway timeout issues:
- Gateway is CRITICAL - frontend needs it to talk to backend
- Must wait for kilo-ai-brain:9004 before starting
- Verify: `curl -s http://kilo-gateway.kilo-guardian:8000/health`
