# Beelink WiFi - SECURE Configuration

**Your Security Concern:** Connecting tablet directly to main network exposes it to risk.

**Solution:** Beelink WiFi with RESTRICTED routing - network segmentation!

---

## Security Architecture

```
                Main Network (192.168.68.x)
                ├── HP Server (192.168.68.61)
                ├── Other devices (printers, IoT, etc.)
                └── Beelink (192.168.68.51)
                         |
                    FIREWALL ← Only ports 30000, 30800
                         |
                    WiFi Hotspot (192.168.43.x)
                         |
                    Tablet (ISOLATED)
```

**Tablet can ONLY access:**
- ✅ Port 30000 (Kilo Guardian Frontend)
- ✅ Port 30800 (Kilo Guardian Gateway API)

**Tablet CANNOT access:**
- 🚫 Other devices on main network
- 🚫 HP Server SSH (port 22)
- 🚫 HP Server Kubernetes (port 6443)
- 🚫 Any other services or IPs
- 🚫 Internet (unless Beelink has internet access)

---

## Why This Is Secure

### Network Segmentation
Tablet is on completely different subnet (192.168.43.x vs 192.168.68.x).
Even if tablet is compromised, attackers cannot reach main network.

### Firewall Protection
Beelink acts as firewall with explicit allow-list:
- Default policy: DROP (block everything)
- Only specific ports allowed through
- Return traffic (ESTABLISHED) allowed back

### Minimal Attack Surface
Tablet can only reach 2 ports on 1 IP address.
Cannot scan network, cannot probe other devices.

### Defense in Depth
Even if attacker gets through firewall somehow:
- HP Server has its own firewall
- Kubernetes network policies
- Pod security policies

---

## Setup (One-Time)

### Password Required

The script needs your **Beelink SSH password** (user: kilo):
- First prompt: Copy script to Beelink (scp)
- Second prompt: Run script on Beelink (ssh)
- Third prompt: Sudo password on Beelink (for iptables)

### Run Secure Setup

From HP server terminal:
```bash
~/scripts/setup-beelink-wifi-routing-SECURE.sh
```

**What it does:**
1. Enables IP forwarding on Beelink
2. Sets iptables default policy to DROP
3. Adds ALLOW rules for ports 30000, 30800 only
4. Sets up NAT for allowed traffic only
5. Saves rules (survives reboot)

---

## Testing Security

### From Tablet (after setup):

**Test 1: Frontend should work**
```bash
curl -I http://192.168.68.61:30000
# Should return: 200 OK
```

**Test 2: Gateway should work**
```bash
curl -I http://192.168.68.61:30800
# Should return: 200 OK or 404 (either means connection works)
```

**Test 3: SSH should be BLOCKED**
```bash
nc -zv 192.168.68.61 22
# Should timeout or connection refused
```

**Test 4: Other ports BLOCKED**
```bash
curl -I http://192.168.68.61:6443
# Should timeout - kubernetes port blocked
```

**Test 5: Ping may timeout** (ICMP not explicitly allowed)
```bash
ping 192.168.68.61
# May timeout - this is NORMAL and EXPECTED
```

---

## Security Verification

On Beelink, check firewall rules:
```bash
ssh kilo@192.168.68.51

# Check default policy (should be DROP)
sudo iptables -L FORWARD | grep "policy"

# Check allowed rules (should see ports 30000, 30800)
sudo iptables -L FORWARD -n -v

# Check NAT rules
sudo iptables -t nat -L POSTROUTING -n -v
```

---

## Comparison: Main Network vs Beelink WiFi

| Feature | Main Network | Beelink WiFi (Secure) |
|---------|--------------|----------------------|
| Access to HP Server | ✅ All ports | ✅ Only 30000, 30800 |
| Access to other devices | ✅ Full access | 🚫 Blocked |
| Access to printer | ✅ Yes | 🚫 No |
| Access to IoT devices | ✅ Yes | 🚫 No |
| Internet access | ✅ Yes | 🚫 No (unless Beelink has it) |
| Network scan possible | ✅ Yes | 🚫 No |
| Compromise impact | 🔴 High | 🟢 Isolated |

---

## Advanced: Adding More Ports

If you need to allow additional services, edit the firewall rules:

```bash
ssh kilo@192.168.68.51

# Add new allowed port (e.g., 8080)
sudo iptables -A FORWARD -s 192.168.43.0/24 -d 192.168.68.61 -p tcp --dport 8080 -j ACCEPT

# Update NAT rule
sudo iptables -t nat -R POSTROUTING 1 -s 192.168.43.0/24 -d 192.168.68.61 -p tcp -m multiport --dports 30000,30800,8080 -j MASQUERADE

# Save
sudo iptables-save | sudo tee /etc/iptables.rules
```

---

## Reverting to Open Routing

If you need to allow all traffic temporarily:

```bash
ssh kilo@192.168.68.51

# Change default policy to ACCEPT
sudo iptables -P FORWARD ACCEPT

# Clear restrictive rules
sudo iptables -F FORWARD
```

To restore secure config, re-run setup script.

---

## Best Practices

1. ✅ **Keep Beelink updated** - It's your security gateway
2. ✅ **Use strong WiFi password** - Protects access to Beelink WiFi
3. ✅ **Monitor Beelink logs** - Watch for suspicious activity
4. ✅ **Don't allow unnecessary ports** - Minimal access = safer
5. ✅ **Regular security audits** - Check iptables rules periodically

---

## Troubleshooting

### Frontend won't load
- Check firewall rules on Beelink (iptables -L FORWARD -n)
- Verify IP forwarding enabled (cat /proc/sys/net/ipv4/ip_forward)
- Check Beelink can reach HP server (ping 192.168.68.61 from Beelink)

### Too restrictive, need more access
- Add specific ports as needed (see "Adding More Ports" above)
- Don't just open everything - defeats the security purpose!

### Want to allow ping
```bash
ssh kilo@192.168.68.51
sudo iptables -A FORWARD -s 192.168.43.0/24 -d 192.168.68.61 -p icmp -j ACCEPT
```

---

**Last updated:** January 15, 2026  
**Security Level:** 🔒🔒🔒🔒🔒 HIGH (Network Segmentation + Firewall)
