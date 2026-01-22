# Socket.IO WebSocket Connection Fix

## Problem
Frontend was getting repeated WebSocket connection failures:
```
WebSocket connection to 'ws://localhost:30000/api/socket.io/?EIO=4&transport=websocket' failed
```

Console errors showed:
- 405 Method Not Allowed on `/api/financial/transaction`
- 502 Bad Gateway on habits and meds services
- Socket.IO WebSocket connection failures

## Root Causes

### 1. ConfigMap Service Port Mismatches (502 errors)
**Problem**: `kilo-config` ConfigMap had wrong ports:
- `HABITS_URL: http://kilo-habits:9003` (actual: 9000)
- `MEDS_URL: http://kilo-meds:9001` (actual: 9000)

**Fix**: Updated ConfigMap:
```bash
kubectl patch configmap kilo-config -n kilo-guardian --type merge \
  -p '{"data":{"HABITS_URL":"http://kilo-habits:9000","MEDS_URL":"http://kilo-meds:9000"}}'
```

### 2. Dashboard Wrong API Endpoint (405 error)
**Problem**: Dashboard.tsx line 194 used `/financial/transaction` (singular)
**Fix**: Changed to `/financial/transactions` (plural) - matches backend

### 3. Socket.IO Path Configuration (WebSocket failures)
**Problem**: Frontend configured with `path: '/api/socket.io'` but Socket.IO is mounted at `/socket.io` in gateway

**Fix**: Changed Dashboard.tsx line 156:
```typescript
path: '/socket.io',  // Changed from '/api/socket.io'
```

### 4. Socket.IO Mount Not Working (404 on /socket.io)
**Problem**: Gateway had Socket.IO mounted via `app.mount('/socket.io', socket_app)` but requests returned 404

**Root Cause**: Multiple issues:
1. Catch-all proxy routes `@app.api_route("/{service}/{path:path}")` were matching `/socket.io` paths BEFORE the mount
2. `socketio.ASGIApp(socketio_path='socket.io')` expected full paths like `/socket.io/?EIO=4` but FastAPI's `.mount('/socket.io', ...)` strips the prefix, passing only `/?EIO=4` to the sub-app

**Fixes Applied**:
1. Disabled catch-all routes without `/api` prefix (lines 522-528 commented out)
2. Changed `socketio_path='socket.io'` to `socketio_path=''` (empty) because FastAPI strips the mount prefix
3. Moved Socket.IO setup before proxy route definitions (lines 473-512) for clarity

## Gateway Code Changes

### Socket.IO ASGI App Configuration (line 491-496)
```python
# Wrap with ASGI app
# NOTE: socketio_path must be empty because FastAPI's mount() strips the /socket.io prefix
socket_app = socketio.ASGIApp(
    socketio_server=sio,
    socketio_path=''  # Changed from 'socket.io'
)
```

### Disabled Catch-All Routes (lines 522-530)
```python
# NOTE: Catch-all routes disabled to allow Socket.IO mount at /socket.io
# All services should be accessed via /api/ prefix
# @app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
# async def proxy_all(request: Request, service: str, path: str):
#     return await _proxy(request, service, path)
```

## Frontend Changes

### Dashboard.tsx
```typescript
// Line 156: Fixed Socket.IO path
const newSocket = io(process.env.REACT_APP_API_URL || window.location.origin, {
  path: '/socket.io',  // Changed from '/api/socket.io'
  transports: ['websocket', 'polling']
});

// Line 194: Fixed transactions endpoint
const txRes = await fetch(`/api/financial/transactions`);  // Changed from /transaction
```

## Deployment

Gateway uses ConfigMap override pattern:
```bash
# Update ConfigMap
kubectl create configmap gateway-code-fixed \
  --from-file=main.py=/path/to/gateway/main.py \
  -n kilo-guardian --dry-run=client -o yaml | kubectl apply -f -

# Restart gateway pod
kubectl delete pod -n kilo-guardian -l app=kilo-gateway
```

Frontend uses standard Docker build:
```bash
cd frontend/kilo-react-frontend
npm run build
docker build -t kilo/frontend:latest .
docker save kilo/frontend:latest | sudo k3s ctr images import -
kubectl delete pod -n kilo-guardian -l app=kilo-frontend
```

## Testing

```bash
# Test Socket.IO endpoint
curl -k 'https://192.168.68.61:8443/socket.io/?EIO=4&transport=polling'
# Should return: 200 OK with Socket.IO session data

# Test habits/meds services
curl -k https://192.168.68.61:8443/api/habits/
curl -k https://192.168.68.61:8443/api/meds/
# Should return: 200 OK with JSON arrays
```

## Result
✅ Socket.IO connects successfully
✅ Habits and meds APIs returning data (no more 502)
✅ Dashboard transactions endpoint working (no more 405)
✅ WebSocket real-time updates functional

## Important Notes

1. **nginx Configuration**: The `/socket.io/` location in nginx was also fixed:
   ```nginx
   location /socket.io/ {
       proxy_pass http://10.43.138.244:8000;  # No path suffix
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
       proxy_read_timeout 300s;
   }
   ```

2. **FastAPI Mount Behavior**: When using `app.mount('/path', sub_app)`:
   - FastAPI strips the `/path` prefix before passing to `sub_app`
   - Sub-app receives paths relative to the mount point
   - For Socket.IO, use `socketio_path=''` not `socketio_path='socket.io'`

3. **Route Priority**: FastAPI matches routes before mounts
   - Defined routes (including catch-alls) take precedence over `.mount()`
   - To allow mounts to work, avoid catch-all routes or exclude specific paths

4. **Frontend Socket.IO Client**: Must connect to the mount path (`/socket.io`), not through API proxy (`/api/socket.io`)

Date: 2026-01-16
