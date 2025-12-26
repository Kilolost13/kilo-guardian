# Kilo AI Memory Assistant - Deployment Guide

**Version:** 1.0.0
**Target Audience:** System administrators, DevOps engineers, end users
**Last Updated:** December 2025

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Hardware Requirements](#hardware-requirements)
3. [Software Prerequisites](#software-prerequisites)
4. [Installation Steps](#installation-steps)
5. [Configuration](#configuration)
6. [First Run](#first-run)
7. [Tablet Setup](#tablet-setup)
8. [Maintenance](#maintenance)
9. [Troubleshooting](#troubleshooting)
10. [Backup & Restore](#backup--restore)

---

## Quick Start

**Total Setup Time:** 30-45 minutes

```bash
# 1. Clone repository
git clone git@github.com:Kilolost13/old_hacksaw_fingers.git
cd old_hacksaw_fingers

# 2. Set admin key
export LIBRARY_ADMIN_KEY=your-secure-key-here

# 3. Start services
cd infra/docker
docker-compose up -d

# 4. Wait for models to download (~5-10 minutes first time)
docker-compose logs -f ollama

# 5. Access UI
# Open browser: http://localhost:3000
```

---

## Hardware Requirements

### Recommended Hardware

**Beelink SER7 Mini PC** (Tested Configuration)
- **CPU:** AMD Ryzen 7 6800H (8 cores, 16 threads, 3.2-4.7 GHz)
- **RAM:** 16GB DDR5-4800
- **Storage:** 512GB NVMe SSD
- **GPU:** AMD Radeon 780M integrated
- **Connectivity:** WiFi 6E, Bluetooth 5.2, Gigabit Ethernet
- **Ports:** 4x USB 3.2, 2x USB-C, 2x HDMI
- **Power:** 19V/65W adapter
- **Price:** ~$500 USD

**Why Beelink SER7?**
- ✅ Sufficient power for LLM inference (Llama 3.1 8B)
- ✅ Compact form factor (fits anywhere)
- ✅ Low power consumption (~20-40W typical)
- ✅ Silent operation (fanless option available)
- ✅ Affordable compared to enterprise hardware

### Minimum Requirements

- **CPU:** 4 cores (Intel i5-8th gen or AMD Ryzen 5 3000 series)
- **RAM:** 8GB (16GB recommended)
- **Storage:** 256GB SSD (512GB recommended)
- **GPU:** Integrated graphics sufficient
- **Network:** WiFi or Ethernet (for initial setup only)

### Tablet (Optional but Recommended)

- **Screen:** 8-10 inches
- **OS:** Android 10+ or iPad OS
- **Network:** WiFi (local network only, internet not required)
- **Recommendation:** Amazon Fire HD 10 (~$150)

---

## Software Prerequisites

### Operating System

**Recommended:** Ubuntu 22.04 LTS Server or Desktop

**Also Supported:**
- Debian 12
- Ubuntu 20.04 LTS
- Pop!_OS 22.04

**Installation:**
1. Download Ubuntu 22.04 LTS ISO from ubuntu.com
2. Create bootable USB with Rufus (Windows) or dd (Linux)
3. Install Ubuntu on Beelink SER7
4. Choose "Minimal installation" to save space
5. Enable automatic updates during setup

### Docker & Docker Compose

**Docker Engine:**
```bash
# Update package index
sudo apt update

# Install dependencies
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Add Docker GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Add user to docker group (avoid sudo)
sudo usermod -aG docker $USER

# Log out and log back in for group change to take effect
```

**Docker Compose:**
```bash
# Download Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Make executable
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker-compose --version
```

### Git

```bash
sudo apt install -y git
git --version
```

---

## Installation Steps

### Step 1: Clone Repository

```bash
# Navigate to home directory
cd ~

# Clone repository
git clone git@github.com:Kilolost13/old_hacksaw_fingers.git

# Navigate to project directory
cd old_hacksaw_fingers

# Check structure
ls -la
```

Expected output:
```
services/      - 12 microservices
frontend/      - React UI
infra/         - Docker configs
docs/          - Documentation
data/          - Static assets
shared/        - Common code
scripts/       - Utility scripts
```

---

### Step 2: Configure Environment

**Set Admin Key** (Required for Library of Truth service):

```bash
# Generate secure key (or use your own)
export LIBRARY_ADMIN_KEY=$(openssl rand -hex 32)

# Save to .env file for persistence
echo "LIBRARY_ADMIN_KEY=$LIBRARY_ADMIN_KEY" > infra/docker/.env

# Verify
cat infra/docker/.env
```

**Optional Configuration:**

Create `infra/docker/.env` with additional settings:

```bash
# Admin key (required)
LIBRARY_ADMIN_KEY=your-secure-key-here

# Ollama model (optional, default: llama3.1:8b-instruct-q5_K_M)
OLLAMA_MODEL=llama3.1:8b-instruct-q5_K_M

# Resource limits (optional)
OLLAMA_NUM_PARALLEL=2
OLLAMA_MAX_LOADED_MODELS=2
OLLAMA_KEEP_ALIVE=5m

# Network mode (optional, default: false for air-gapped)
ALLOW_NETWORK=false

# Voice providers (optional)
STT_PROVIDER=whisper
TTS_PROVIDER=piper
```

---

### Step 3: Build Docker Images

```bash
# Navigate to docker directory
cd infra/docker

# Pull base images (if internet available)
docker-compose pull

# Build all services (first time: 10-15 minutes)
LIBRARY_ADMIN_KEY=$LIBRARY_ADMIN_KEY docker-compose build

# Monitor build progress
docker-compose build --progress=plain
```

**Build Time Estimate:**
- Frontend (Node.js build): ~5-8 minutes
- AI Brain (Python deps): ~2-3 minutes
- Other services: ~1 minute each

---

### Step 4: Download AI Models

**Option A: Download During First Startup (Recommended)**

```bash
# Start Ollama service only
docker-compose up -d ollama

# Wait for Ollama to be ready
docker-compose logs -f ollama

# Download Llama 3.1 8B model (~4.7GB, 5-10 minutes on fast connection)
docker exec -it docker_ollama_1 ollama pull llama3.1:8b-instruct-q5_K_M

# Verify download
docker exec -it docker_ollama_1 ollama list
```

**Option B: Pre-download Models (Offline Preparation)**

If preparing for air-gapped deployment:

```bash
# On internet-connected machine:
# 1. Download model files
ollama pull llama3.1:8b-instruct-q5_K_M

# 2. Export model directory
docker cp docker_ollama_1:/root/.ollama ./ollama_models

# 3. Transfer to USB drive

# On air-gapped machine:
# 1. Copy from USB to volume
docker volume create ollama_models
docker run --rm -v ollama_models:/data -v $(pwd)/ollama_models:/backup alpine sh -c "cp -r /backup/* /data/"
```

---

### Step 5: Start All Services

```bash
# Navigate to docker directory (if not already there)
cd infra/docker

# Start all services
LIBRARY_ADMIN_KEY=$LIBRARY_ADMIN_KEY docker-compose up -d

# Verify all services are running
docker-compose ps

# Expected output: All services in "Up" state
```

**Service Startup Order:**
1. Ollama (LLM)
2. AI Brain (waits for Ollama)
3. Gateway (waits for AI Brain)
4. Other services (parallel)
5. Frontend (last)

**Total Startup Time:** 30-60 seconds

---

### Step 6: Verify Installation

```bash
# Check service health
docker-compose ps

# All services should show "Up (healthy)" or "Up"

# Check logs for errors
docker-compose logs --tail=50

# Test API Gateway
curl http://localhost:8000/status

# Expected response:
# {"status":"healthy","services":{...}}

# Test AI Brain
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, are you working?"}'

# Expected response:
# {"response": "Hello! Yes, I'm working..."}
```

---

## Configuration

### Network Configuration

**Local Network Only (Default):**
- Frontend accessible at: `http://<beelink-ip>:3000`
- API Gateway at: `http://<beelink-ip>:8000`
- HTTPS (self-signed): `https://<beelink-ip>:3443`

**Find Beelink IP:**
```bash
hostname -I | awk '{print $1}'
# or
ip addr show | grep "inet " | grep -v 127.0.0.1
```

**Configure Firewall (if enabled):**
```bash
# Allow HTTP (3000) and HTTPS (3443) for frontend
sudo ufw allow 3000/tcp
sudo ufw allow 3443/tcp

# Allow API Gateway (8000)
sudo ufw allow 8000/tcp

# Reload firewall
sudo ufw reload
```

---

### Service Configuration

**Customize docker-compose.yml:**

```yaml
services:
  ai_brain:
    environment:
      - OLLAMA_MODEL=llama3.1:8b-instruct-q5_K_M  # Change model
      - STT_PROVIDER=whisper  # or 'none' to disable
      - TTS_PROVIDER=piper    # or 'none' to disable
```

**Resource Limits:**

Add to docker-compose.yml for resource-constrained systems:

```yaml
services:
  ai_brain:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
```

---

## First Run

### Step 1: Access Frontend

1. Open browser on tablet or laptop
2. Navigate to: `http://<beelink-ip>:3000`
3. You should see the Kilo AI Dashboard

**Troubleshooting Access:**
- Check firewall rules: `sudo ufw status`
- Verify frontend is running: `docker-compose ps frontend`
- Check logs: `docker-compose logs frontend`

---

### Step 2: Initial Setup

**Set Admin Password (Optional):**

```bash
# Access AI Brain container
docker exec -it docker_ai_brain_1 bash

# Set admin password (for future use)
python -c "from passlib.hash import bcrypt; print(bcrypt.hash('your-password'))"

# Exit container
exit
```

---

### Step 3: Add First Medication

1. Navigate to "Medications" page
2. Click "Add Medication"
3. Fill in details:
   - Name: Lisinopril
   - Dosage: 10mg
   - Frequency: Once daily
   - Prescribing Doctor: Dr. Smith
4. Click "Save"

**Alternative: Use OCR**
1. Click "Scan Prescription"
2. Upload prescription image
3. Review extracted details
4. Confirm and save

---

### Step 4: Create First Habit

1. Navigate to "Habits" page
2. Click "New Habit"
3. Fill in:
   - Name: Morning Exercise
   - Type: Exercise
   - Frequency: Daily
   - Target Duration: 30 minutes
   - Reminder Time: 08:00 AM
4. Click "Create"

---

### Step 5: Test Chat

1. Navigate to Dashboard
2. Click "Chat with Kilo"
3. Type: "What medications am I taking?"
4. Verify response references the medication you added

---

## Tablet Setup

### Android Tablet

**Step 1: Connect to WiFi**
1. Connect tablet to same network as Beelink
2. Test connectivity: Open browser, go to `http://<beelink-ip>:3000`

**Step 2: Create Home Screen Shortcut**
1. Open Chrome browser
2. Navigate to `http://<beelink-ip>:3000`
3. Tap menu (three dots) → "Add to Home screen"
4. Name: "Kilo AI"
5. Tap "Add"

**Step 3: Enable Kiosk Mode (Optional)**

Install Fully Kiosk Browser (for locked-down tablet):
1. Download from Google Play Store
2. Open app → Settings
3. Set "Autostart URL": `http://<beelink-ip>:3000`
4. Enable "Kiosk Mode"
5. Configure as default launcher

**Recommended Settings:**
- Disable sleep during use
- Enable "Guided Access" (iOS) or "Screen Pinning" (Android)
- Set brightness to 50-70%

---

### iPad

**Step 1: Connect to WiFi**
1. Settings → WiFi → Connect to network
2. Open Safari, navigate to `http://<beelink-ip>:3000`

**Step 2: Add to Home Screen**
1. Tap Share icon
2. "Add to Home Screen"
3. Name: "Kilo AI"
4. Tap "Add"

**Step 3: Enable Guided Access (Kiosk Mode)**
1. Settings → Accessibility → Guided Access
2. Turn on Guided Access
3. Set passcode
4. Open Kilo AI app
5. Triple-click home button → Start Guided Access

---

## Maintenance

### Regular Maintenance Tasks

**Weekly:**
- Check disk space: `df -h`
- Review logs for errors: `docker-compose logs --tail=100`

**Monthly:**
- Backup database (see Backup & Restore section)
- Update Docker images (if internet available)
- Clean up old Docker images: `docker system prune -a`

**Quarterly:**
- Review and update admin key
- Check for Kilo AI updates
- Test backup restoration

---

### Updating the System

**Update Docker Images:**

```bash
cd infra/docker

# Pull latest images (requires internet)
git pull origin main
docker-compose pull

# Rebuild services
LIBRARY_ADMIN_KEY=$LIBRARY_ADMIN_KEY docker-compose build

# Restart services
docker-compose down
LIBRARY_ADMIN_KEY=$LIBRARY_ADMIN_KEY docker-compose up -d
```

**Update LLM Model:**

```bash
# Pull newer model
docker exec -it docker_ollama_1 ollama pull llama3.1:8b-instruct-q6_K

# Update docker-compose.yml OLLAMA_MODEL variable

# Restart AI Brain
docker-compose restart ai_brain
```

---

### Monitoring

**Check Service Status:**
```bash
docker-compose ps
```

**View Logs:**
```bash
# All services
docker-compose logs --tail=100 -f

# Specific service
docker-compose logs -f ai_brain

# Search logs for errors
docker-compose logs | grep ERROR
```

**Resource Usage:**
```bash
# Docker stats
docker stats

# System resources
htop  # or 'top'
```

---

## Troubleshooting

### Services Won't Start

**Problem:** `docker-compose up` fails

**Solutions:**
1. Check Docker is running: `sudo systemctl status docker`
2. Verify disk space: `df -h` (need at least 10GB free)
3. Check LIBRARY_ADMIN_KEY is set: `echo $LIBRARY_ADMIN_KEY`
4. View logs: `docker-compose logs`

---

### AI Brain Not Responding

**Problem:** Chat returns errors or timeouts

**Diagnose:**
```bash
# Check AI Brain logs
docker-compose logs ai_brain

# Check Ollama logs
docker-compose logs ollama

# Test Ollama directly
docker exec -it docker_ollama_1 ollama run llama3.1:8b-instruct-q5_K_M "Hello"
```

**Solutions:**
1. Restart AI Brain: `docker-compose restart ai_brain`
2. Download model if missing: `docker exec -it docker_ollama_1 ollama pull llama3.1:8b-instruct-q5_K_M`
3. Increase memory limit in docker-compose.yml

---

### Frontend Not Accessible

**Problem:** Cannot access http://localhost:3000

**Diagnose:**
```bash
# Check frontend is running
docker-compose ps frontend

# Check logs
docker-compose logs frontend

# Test from Beelink directly
curl http://localhost:3000
```

**Solutions:**
1. Restart frontend: `docker-compose restart frontend`
2. Rebuild frontend: `docker-compose build frontend`
3. Check firewall: `sudo ufw status`

---

### Out of Memory Errors

**Problem:** Services crashing with OOM errors

**Solutions:**
1. Reduce Ollama parallel requests in docker-compose.yml:
   ```yaml
   environment:
     - OLLAMA_NUM_PARALLEL=1  # Down from 2
   ```
2. Use smaller LLM model:
   ```yaml
   environment:
     - OLLAMA_MODEL=tinyllama  # 1.1B instead of 8B
   ```
3. Add swap space:
   ```bash
   sudo fallocate -l 8G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

---

### Database Corruption

**Problem:** SQLite database errors

**Diagnose:**
```bash
# Check database integrity
docker exec -it docker_ai_brain_1 sqlite3 /data/memories.db "PRAGMA integrity_check;"
```

**Solutions:**
1. Restore from backup (see Backup & Restore)
2. Rebuild database:
   ```bash
   docker exec -it docker_ai_brain_1 bash
   cd /data
   sqlite3 memories.db ".dump" > backup.sql
   mv memories.db memories.db.old
   sqlite3 memories.db < backup.sql
   exit
   ```

---

## Backup & Restore

### Manual Backup

**Backup All Data:**

```bash
# Create backup directory
mkdir -p ~/kilo_backups/$(date +%Y%m%d)

# Backup Docker volumes
docker run --rm -v gateway_data:/data -v ~/kilo_backups/$(date +%Y%m%d):/backup alpine tar czf /backup/gateway_data.tar.gz -C /data .
docker run --rm -v ai_brain_data:/data -v ~/kilo_backups/$(date +%Y%m%d):/backup alpine tar czf /backup/ai_brain_data.tar.gz -C /data .
docker run --rm -v library_data:/data -v ~/kilo_backups/$(date +%Y%m%d):/backup alpine tar czf /backup/library_data.tar.gz -C /data .
docker run --rm -v meds_data:/data -v ~/kilo_backups/$(date +%Y%m%d):/backup alpine tar czf /backup/meds_data.tar.gz -C /data .
docker run --rm -v habits_data:/data -v ~/kilo_backups/$(date +%Y%m%d):/backup alpine tar czf /backup/habits_data.tar.gz -C /data .
docker run --rm -v financial_data:/data -v ~/kilo_backups/$(date +%Y%m%d):/backup alpine tar czf /backup/financial_data.tar.gz -C /data .
docker run --rm -v ollama_models:/data -v ~/kilo_backups/$(date +%Y%m%d):/backup alpine tar czf /backup/ollama_models.tar.gz -C /data .

# List backups
ls -lh ~/kilo_backups/$(date +%Y%m%d)
```

---

### Automated Backup Script

**Create backup script:**

```bash
cat > ~/backup_kilo.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=~/kilo_backups/$(date +%Y%m%d)
mkdir -p $BACKUP_DIR

echo "Starting Kilo AI backup..."

docker run --rm -v gateway_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/gateway_data.tar.gz -C /data .
docker run --rm -v ai_brain_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/ai_brain_data.tar.gz -C /data .
docker run --rm -v library_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/library_data.tar.gz -C /data .
docker run --rm -v meds_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/meds_data.tar.gz -C /data .
docker run --rm -v habits_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/habits_data.tar.gz -C /data .
docker run --rm -v financial_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/financial_data.tar.gz -C /data .

echo "Backup complete: $BACKUP_DIR"
ls -lh $BACKUP_DIR
EOF

chmod +x ~/backup_kilo.sh
```

**Schedule daily backups:**

```bash
# Add to crontab (2 AM daily)
(crontab -l 2>/dev/null; echo "0 2 * * * ~/backup_kilo.sh") | crontab -
```

---

### Restore from Backup

**Restore All Data:**

```bash
# Stop services
cd infra/docker
docker-compose down

# Restore volumes
BACKUP_DATE=20251225  # Change to your backup date
docker run --rm -v gateway_data:/data -v ~/kilo_backups/$BACKUP_DATE:/backup alpine sh -c "cd /data && tar xzf /backup/gateway_data.tar.gz"
docker run --rm -v ai_brain_data:/data -v ~/kilo_backups/$BACKUP_DATE:/backup alpine sh -c "cd /data && tar xzf /backup/ai_brain_data.tar.gz"
docker run --rm -v library_data:/data -v ~/kilo_backups/$BACKUP_DATE:/backup alpine sh -c "cd /data && tar xzf /backup/library_data.tar.gz"
docker run --rm -v meds_data:/data -v ~/kilo_backups/$BACKUP_DATE:/backup alpine sh -c "cd /data && tar xzf /backup/meds_data.tar.gz"
docker run --rm -v habits_data:/data -v ~/kilo_backups/$BACKUP_DATE:/backup alpine sh -c "cd /data && tar xzf /backup/habits_data.tar.gz"
docker run --rm -v financial_data:/data -v ~/kilo_backups/$BACKUP_DATE:/backup alpine sh -c "cd /data && tar xzf /backup/financial_data.tar.gz"

# Restart services
LIBRARY_ADMIN_KEY=$LIBRARY_ADMIN_KEY docker-compose up -d
```

---

### USB Backup (Air-Gapped Systems)

**Backup to USB:**

```bash
# Mount USB drive
sudo mount /dev/sdb1 /mnt/usb

# Run backup to USB
BACKUP_DIR=/mnt/usb/kilo_backup_$(date +%Y%m%d)
mkdir -p $BACKUP_DIR

# Copy backup archives
cp ~/kilo_backups/$(date +%Y%m%d)/* $BACKUP_DIR/

# Unmount
sudo umount /mnt/usb
```

**Restore from USB:**

```bash
# Mount USB
sudo mount /dev/sdb1 /mnt/usb

# Copy to local
cp -r /mnt/usb/kilo_backup_20251225 ~/kilo_backups/

# Follow restore steps above

# Unmount
sudo umount /mnt/usb
```

---

## Advanced Topics

### Running on Older Hardware

**For systems with < 16GB RAM:**

Use lighter configuration:

```yaml
# docker-compose.yml modifications
services:
  ai_brain:
    environment:
      - OLLAMA_MODEL=tinyllama  # 1.1GB instead of 4.7GB
      - LLM_PROVIDER=ollama
      - OLLAMA_NUM_PARALLEL=1   # Reduce from 2

  # Disable camera if not needed
  # cam:
  #   ...  (comment out entire service)
```

---

### Multi-User Setup (Planned)

Future releases will support multiple users. Prepare by:

1. Using separate data volumes per user
2. Implementing user authentication
3. Partitioning data by user_id

---

### Production Hardening

For deployment in clinical settings:

1. **Enable HTTPS only:**
   ```yaml
   frontend:
     ports:
       - "3443:443"  # Remove port 80
   ```

2. **Set strong admin key:**
   ```bash
   export LIBRARY_ADMIN_KEY=$(openssl rand -base64 48)
   ```

3. **Enable audit logging:**
   Configure centralized logging for all services

4. **Restrict network access:**
   ```bash
   sudo ufw default deny incoming
   sudo ufw allow from 192.168.1.0/24 to any port 3443
   ```

5. **Regular security updates:**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

---

## Summary

**Deployment Checklist:**

- [ ] Hardware acquired (Beelink SER7 + tablet)
- [ ] Ubuntu 22.04 LTS installed
- [ ] Docker & Docker Compose installed
- [ ] Repository cloned
- [ ] LIBRARY_ADMIN_KEY set
- [ ] Docker images built
- [ ] Ollama model downloaded
- [ ] Services started and healthy
- [ ] Frontend accessible
- [ ] Tablet configured
- [ ] First medication/habit added
- [ ] Chat tested
- [ ] Backup script configured

**Support Resources:**

- **Documentation:** `docs/` directory
- **GitHub Issues:** https://github.com/Kilolost13/old_hacksaw_fingers/issues
- **Email:** support@kilo-ai.com (planned)

---

**Deployment Complete!** 🎉

Kilo AI is now running and ready to assist with health management. Refer to the User Guide for daily operation instructions.

**Last Updated:** December 2025
**Version:** 1.0.0
**Maintained by:** Kilo AI Team
