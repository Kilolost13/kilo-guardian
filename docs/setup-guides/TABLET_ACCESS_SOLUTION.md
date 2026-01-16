# TABLET ACCESS TO KILO GUARDIAN - FINAL SOLUTION

## Problem Summary
The tablet connects to Beelink WiFi (10.42.0.0/24) but cannot directly reach the HP server (192.168.68.61) on NodePorts due to:
1. Kube-router only allows NodePort access from LOCAL connections
2. Network routing issues between WiFi subnet and main network

## Working Solution: Beelink Proxy Services

The Beelink is running socat proxy services that forward traffic to the HP server:

### Proxy Services on Beelink (192.168.68.51)
- **kilo-frontend-proxy**: Listens on port 8080, forwards to HP:30000
- **kilo-gateway-proxy**: Listens on port 8081, forwards to HP:30800

### Tablet Access URLs
From your tablet, use these URLs:

**Frontend (main app):**
```
http://10.42.0.1:8080
```

**Gateway API (direct access if needed):**
```
http://10.42.0.1:8081
```

## How It Works

```
Tablet (10.42.0.33)
    ↓
    WiFi → Beelink (10.42.0.1)
           ↓
           socat proxy (port 8080)
              ↓
              Ethernet → HP Server (192.168.68.61)
                        ↓
                        Pod (10.42.0.2:80) via k3s routing
```

## Troubleshooting

### If frontend loads but doesn't work:
The frontend makes API calls to `/api/` which should be proxied internally by nginx.

**Check browser console** (if accessible) for errors like:
- CORS errors
- Connection refused to /api/
- WebSocket connection failures

### If it shows "connection refused":
1. Check Beelink proxy services:
   ```bash
   ssh brain_ai@192.168.68.51
   sudo systemctl status kilo-frontend-proxy
   sudo systemctl status kilo-gateway-proxy
   ```

2. Restart proxies if needed:
   ```bash
   sudo systemctl restart kilo-frontend-proxy kilo-gateway-proxy
   ```

### If page won't load at all:
1. Verify tablet IP is in WiFi subnet:
   - Should be 10.42.0.x
   - Gateway should be 10.42.0.1

2. Test connectivity:
   ```bash
   ping 10.42.0.1
   ```

## Known Limitations

1. **Socket.IO may not work** - The kilo-socketio pod is crash-looping
2. **Some features may be slow** - Double-proxy adds latency
3. **NodePort direct access doesn't work** - Must use proxy

## Security

✅ Tablet is isolated on Beelink WiFi
✅ Cannot access main network directly
✅ Only specific ports (8080, 8081) are accessible
✅ Defense in depth: even if tablet is compromised, network exposure is minimal

## System Status

**Beelink (192.168.68.51)**
- llama-server: Running (Ministral model on port 11434)
- WiFi Hotspot: Active (10.42.0.0/24)
- Proxy services: Active

**HP Server (192.168.68.61)**
- K3s: Running
- Pods: 14/14 running (13 ready, socketio failing)
- Frontend: http://192.168.68.61:30000 (internal access only)
- Gateway: http://192.168.68.61:30800 (internal access only)

Last updated: January 15, 2026
