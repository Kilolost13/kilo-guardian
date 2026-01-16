# Use Beelink WiFi to Access Kilo Guardian

**Your Smart Idea:** Use Beelink's WiFi hotspot to connect tablet, then route traffic to HP server!

---

## Why This Works

```
Tablet (192.168.43.x)
    ↓ WiFi Connection
Beelink WiFi Hotspot (192.168.43.1)
    ↓ ROUTING (we configure this!)
Beelink Main Network (192.168.68.51)
    ↓ Main Network
HP Server (192.168.68.61) ← Kilo Guardian Frontend
```

Beelink is connected to BOTH networks:
- WiFi hotspot (for tablet)
- Main network (for HP server access)

By enabling **routing** on Beelink, it becomes a gateway!

---

## Setup (One-Time)

### Option 1: Run Auto-Setup Script (Easy)

From HP server terminal:
```bash
~/scripts/setup-beelink-wifi-routing.sh
```

Enter Beelink password when prompted. Script will:
1. Enable IP forwarding on Beelink
2. Configure NAT (Network Address Translation)
3. Set up iptables routing rules
4. Make changes permanent

### Option 2: Manual Setup (If Script Fails)

SSH to Beelink from HP server:
```bash
ssh kilo@192.168.68.51
```

Then run these commands:
```bash
# Enable IP forwarding
sudo sysctl -w net.ipv4.ip_forward=1
echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.conf

# Find your WiFi interface (usually wlp* or wlan*)
ip addr | grep "192.168.43"
# Note the interface name (e.g., wlp2s0)

# Find main network interface
ip route | grep "192.168.68.0"
# Note the interface name (e.g., enp3s0)

# Set up NAT (replace <main-if> with your interface name)
sudo iptables -t nat -A POSTROUTING -o <main-if> -j MASQUERADE

# Allow forwarding
sudo iptables -A FORWARD -i <wifi-if> -o <main-if> -j ACCEPT
sudo iptables -A FORWARD -i <main-if> -o <wifi-if> -m state --state RELATED,ESTABLISHED -j ACCEPT

# Save rules
sudo iptables-save | sudo tee /etc/iptables.rules
```

---

## Testing

### From Tablet (connected to Beelink WiFi):

**Step 1:** Test basic connectivity
```bash
ping 192.168.68.61
# Should get replies!
```

**Step 2:** Test HTTP access
```bash
curl -I http://192.168.68.61:30000
# Should return "200 OK"
```

**Step 3:** Open browser
```
http://192.168.68.61:30000
```

Frontend should load!

---

## Troubleshooting

### "Destination Host Unreachable"

Check IP forwarding is enabled on Beelink:
```bash
ssh kilo@192.168.68.51 "cat /proc/sys/net/ipv4/ip_forward"
# Should return: 1
```

If returns 0, run:
```bash
ssh kilo@192.168.68.51 "sudo sysctl -w net.ipv4.ip_forward=1"
```

### "No route to host"

Check NAT rules on Beelink:
```bash
ssh kilo@192.168.68.51 "sudo iptables -t nat -L -n | grep MASQUERADE"
# Should show masquerading rules
```

### Still not working?

Verify Beelink can reach HP server:
```bash
ssh kilo@192.168.68.51 "ping -c 3 192.168.68.61"
# Should get replies
```

---

## Making It Permanent

The setup script saves iptables rules, but if Beelink reboots, you may need to:

1. Install `iptables-persistent`:
   ```bash
   ssh kilo@192.168.68.51 "sudo apt install iptables-persistent -y"
   ```

2. Save rules:
   ```bash
   ssh kilo@192.168.68.51 "sudo netfilter-persistent save"
   ```

---

## Advantages

✅ **No SSH tunnel needed** - Direct access  
✅ **Tablet stays on Beelink WiFi** - Convenient  
✅ **Works for all services** - Frontend, Gateway, AI Brain  
✅ **Automatic** - Once configured, always works  
✅ **Private** - Beelink WiFi is your personal network  

---

## Network Diagram

```
                    Internet
                        |
                   Main Router
                        |
        ┌───────────────┴───────────────┐
        |                               |
   HP Server                        Beelink
   192.168.68.61                   192.168.68.51
   (Kilo Guardian)                 (AI Server + WiFi AP)
                                        |
                                   WiFi Hotspot
                                   192.168.43.1
                                        |
                                     Tablet
                                   192.168.43.x
```

**Before:** Tablet couldn't reach HP server (different networks)  
**After:** Beelink routes between networks (acts as gateway)

---

Last updated: January 15, 2026
