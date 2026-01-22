# KILO GUARDIAN - TABLET ACCESS GUIDE

## Your Server IP Address
**192.168.68.61**

---

## QUICK ACCESS URLS FOR YOUR TABLET

### Option 1: Direct NodePort Access (RECOMMENDED)
These URLs work from any device on your network:

**Frontend (Main Dashboard)**
```
http://192.168.68.61:30000
```

**API Gateway**
```
http://192.168.68.61:30800
```

---

## Option 2: Hostname-Based Access (Requires DNS Setup)

If you set up local DNS or edit hosts file on tablet:

```
http://tablet.kilo.local
http://kilo.local
```

### To use hostnames on tablet:
1. Edit `/etc/hosts` (Android with root) or use DNS app
2. Add line: `192.168.68.61  kilo.local tablet.kilo.local`

---

## Troubleshooting

### Can't Connect from Tablet?

1. **Check if server is on same WiFi network**
   - Server IP: 192.168.68.61
   - Tablet should be on same 192.168.68.x network

2. **Test connectivity**
   - Ping server: Use network tools app
   - Try: `http://192.168.68.61:30000`

3. **Firewall is open** ✅
   - Port 30000 (Frontend) - OPEN
   - Port 30800 (Gateway) - OPEN
   - Port 80 (Ingress) - OPEN

4. **Check if services are running**
   ```bash
   kubectl get pods -n kilo-guardian
   kubectl get svc -n kilo-guardian
   ```

---

## Service Ports Reference

| Service | Internal Port | External Port | URL |
|---------|--------------|---------------|-----|
| Frontend | 3000 | 30000 | http://192.168.68.61:30000 |
| Gateway | 8000 | 30800 | http://192.168.68.61:30800 |
| Grafana | 3000 | 30300 | http://192.168.68.61:30300 |
| Prometheus | 9090 | 30900 | http://192.168.68.61:30900 |

---

## Additional Monitoring URLs

**Grafana (System Monitoring)**
```
http://192.168.68.61:30300
```

**Prometheus (Metrics)**
```
http://192.168.68.61:30900
```

---

## Mobile Browser Tips

1. **Use Chrome or Firefox** - Best compatibility
2. **Bookmark the URL** - Save `http://192.168.68.61:30000`
3. **Enable Desktop Mode** - Better UI on tablets
4. **Check WiFi** - Must be on same network as server

---

## Still Can't Connect?

Run this diagnostic on the server:

```bash
# Check if frontend is responding
curl -I http://localhost:30000

# Check if services are in correct namespace
kubectl get svc -n kilo-guardian

# Check pod status
kubectl get pods -A | grep -E "frontend|gateway"

# Test from server
curl http://192.168.68.61:30000
```

---

## Quick Fix Commands

If services aren't responding:

```bash
# Restart frontend
kubectl rollout restart deployment/frontend -n kilo-guardian

# Restart gateway
kubectl rollout restart deployment/gateway -n kilo-guardian

# Check logs
kubectl logs -n kilo-guardian -l app=frontend
```

---

**Last Updated:** 2026-01-22
**Server IP:** 192.168.68.61
**Network:** 192.168.68.0/24
