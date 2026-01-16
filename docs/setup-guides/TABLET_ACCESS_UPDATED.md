# Tablet Access to Kilo Guardian - UPDATED

**Server IP:** 192.168.68.61 (HP Desktop)  
**Beelink AI:** 192.168.68.51 (AI Server)  
**Date:** January 15, 2026

---

## Quick Access for Tablet

### Option 1: Direct NodePort Access (Simplest)

From your tablet browser, go to:

```
http://192.168.68.61:30000
```

This loads the Kilo Guardian frontend directly.

**Important:** Tablet and server must be on the same network!

---

### Option 2: Ingress with DNS (Pretty URL)

**On your tablet**, add to `/etc/hosts`:
```
192.168.68.61  tablet.kilo.local
```

Then access: **http://tablet.kilo.local**

---

## Access Points

| Service | NodePort URL | Ingress URL | Description |
|---------|--------------|-------------|-------------|
| **Frontend** | http://192.168.68.61:30000 | http://tablet.kilo.local | Main UI |
| **Gateway** | http://192.168.68.61:30800 | http://kilo.local/api | Backend API |

---

## Testing from Tablet

### Check if server is reachable:
```bash
ping 192.168.68.61
```

### Test frontend is up:
```bash
curl -I http://192.168.68.61:30000
```

Should return "200 OK" with HTML content.

---

## AI Configuration (Updated)

The AI brain now connects to:
- **Server:** 192.168.68.51:11434 (Beelink)
- **Model:** Ministral-3-14B-Reasoning
- **Engine:** llama.cpp (not Ollama)

Previously used local Ollama (kilo-ollama pod) which was not configured correctly.

---

## Tablet Requirements

- **Same WiFi network** as HP server (192.168.68.x)
- **Modern browser** (Chrome, Firefox, Safari)
- **JavaScript enabled**
- **No special apps** required

---

## Troubleshooting

### Can't connect to 192.168.68.61:30000
1. Verify you're on same network:
   ```bash
   ip route | grep default
   # Should show 192.168.68.x gateway
   ```

2. Check if server is up:
   ```bash
   ping -c 3 192.168.68.61
   ```

3. Check if k3s is running on server:
   ```bash
   ssh kilo@192.168.68.61 "kubectl get pods -n kilo-guardian"
   ```

### Frontend loads but AI doesn't respond
1. Check Beelink is running:
   ```bash
   curl http://192.168.68.51:11434/health
   # Should return: {"status":"ok"}
   ```

2. Check gateway can reach AI:
   ```bash
   curl http://192.168.68.61:30800/health
   ```

---

## SSH Tunnel (Alternative Method)

If you prefer SSH tunneling:

```bash
ssh -L 3000:localhost:30000 kilo@192.168.68.61
```

Then access: http://localhost:3000 on tablet

---

Last updated: January 15, 2026
