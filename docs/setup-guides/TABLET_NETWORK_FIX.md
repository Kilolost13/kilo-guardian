# Tablet Network Connectivity - SOLUTION

**Problem:** Tablet connected to Beelink WiFi hotspot cannot reach HP server (192.168.68.61)

**Reason:** Different networks! Beelink WiFi is isolated from main network.

---

## QUICK FIX (Recommended)

### On Your Tablet:

1. **Disconnect from Beelink WiFi**
2. **Connect to your main home/network WiFi** (same one HP server uses)
3. **Open browser to:** `http://192.168.68.61:30000`
4. **Done!** Frontend should load

---

## Alternative: SSH Tunnel (If Staying on Beelink WiFi)

### Step 1: Find Beelink Hotspot IP

On tablet, check your gateway:
```bash
ip route | grep default
# Will show something like: default via 192.168.43.1
```

That IP (e.g., 192.168.43.1) is the Beelink hotspot gateway.

### Step 2: Create SSH Tunnel

From tablet terminal:
```bash
ssh -L 3000:192.168.68.61:30000 -L 8000:192.168.68.61:30800 kilo@192.168.43.1
```

**Note:** Replace `192.168.43.1` with actual Beelink hotspot IP from Step 1.

### Step 3: Access Frontend

Open tablet browser to: `http://localhost:3000`

Keep SSH terminal open while using!

---

## Why This Happens

```
Main Router (192.168.68.x)
├── HP Server: 192.168.68.61 ← Kilo Guardian here
└── Beelink: 192.168.68.51 ← AI server here
     └── WiFi Hotspot (192.168.43.x or similar)
          └── Tablet: 192.168.43.x ← ISOLATED!
```

Beelink WiFi hotspot creates its own subnet, separate from main network.

---

## Long-Term Solution (Advanced)

Configure Beelink to bridge/route between WiFi hotspot and main network:

1. Enable IP forwarding on Beelink
2. Set up NAT rules (iptables)
3. Configure routing between interfaces

**This is complex** - easier to just connect tablet to main WiFi!

---

## Which Option Should You Choose?

| Option | Difficulty | When to Use |
|--------|-----------|-------------|
| **Main WiFi** | ⭐ Easy | You have WiFi password |
| **SSH Tunnel** | ⭐⭐ Medium | Must stay on Beelink WiFi |
| **Bridge/Route** | ⭐⭐⭐⭐⭐ Hard | Permanent solution needed |

**Recommendation:** Connect tablet to main WiFi - it's the simplest!

---

## Testing Connection

After connecting to main WiFi, test from tablet:

```bash
# Check you can reach HP server
ping 192.168.68.61

# Check frontend is accessible
curl -I http://192.168.68.61:30000

# Should return "200 OK"
```

---

Last updated: January 15, 2026
