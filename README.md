# 🧠 Kilo — Personal AI Assistant

**Privacy-First, Self-Hosted, Kubernetes-Deployed**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![K3s](https://img.shields.io/badge/K3s-Ready-326CE5.svg)](https://k3s.io/)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://reactjs.org/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB.svg)](https://www.python.org/)
[![Gemini](https://img.shields.io/badge/LLM-Gemini%202.0%20Flash-4285F4.svg)](https://ai.google.dev/)

---

## Overview

Kilo is a personal AI assistant that runs entirely on local infrastructure. It tracks health, finances, habits, and reminders — and learns your patterns over time. All data stays on your hardware.

**Access:** `http://192.168.68.57:30002/guardian/`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│            HP (192.168.68.57) — K3s Host                   │
│                  namespace: kilo-guardian                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  Frontend   │───▶│   Gateway    │───▶│   AI Brain    │  │
│  │ React :30002│    │ FastAPI :8000│    │ FastAPI :9004  │  │
│  └─────────────┘    └──────┬───────┘    │ Gemini 2.0 ⚡ │  │
│                            │            └───────────────┘  │
│                    ┌───────┼────────┐                       │
│                    ▼       ▼        ▼                       │
│              ┌─────────┐ ┌──────┐ ┌──────────┐             │
│              │  Meds   │ │Habits│ │Reminders │             │
│              │  :9000  │ │:9000 │ │  :9002   │             │
│              └─────────┘ └──────┘ └──────────┘             │
│              ┌──────────┐ ┌──────────┐ ┌─────────────────┐ │
│              │Financial │ │ Library  │ │   ML Engine     │ │
│              │  :9005   │ │  :9006   │ │ Pattern Learning│ │
│              └──────────┘ └──────────┘ └─────────────────┘ │
│              ┌──────────┐ ┌──────────────────────────────┐  │
│              │   Cam    │ │     Health Monitor           │  │
│              │IP Cams   │ │  Self-healing, 9 services    │  │
│              └──────────┘ └──────────────────────────────┘  │
│                                                             │
│  Data: SQLite PVC at /app/kilo_data/kilo_guardian.db        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│     Beelink (192.168.68.61) — Dev Box       │
│  Desktop Observer: OCR → AI Brain every 20s │
│  Sends context: emails, bills, active apps  │
└─────────────────────────────────────────────┘
```

---

## Active Services

| Service | Port | Purpose |
|---------|------|---------|
| kilo-frontend | 30002 | React UI (nginx) |
| kilo-gateway | 8000 | API router / proxy |
| kilo-ai-brain | 9004 | Gemini 2.0 Flash LLM, conversation history, function calling |
| kilo-meds | 9000 | Medication tracking, adherence, prescription OCR |
| kilo-habits | 9000 | Habit tracking, completion history, streaks |
| kilo-reminder | 9002 | Reminders with daily/weekly recurrence |
| kilo-financial | 9005 | Transactions, budgets, goals |
| kilo-library | 9006 | Library of Truth — verified knowledge base |
| kilo-ml-engine | 9009 | Pattern learning from habits/meds/financial data |
| kilo-cam | 8003 | IP camera registry, HTTP snapshots, RTSP, OCR |
| kilo-health-monitor | 9011 | Self-healing: monitors 9 services, auto-restarts CrashLoopBackOff |

---

## Key Features

### AI Brain (Gemini 2.0 Flash)
- ~1 second response time
- Multi-turn conversation with SQLite-persisted session history (survives pod restarts)
- Function calling: create reminders, query spending, check habits, search library
- Reads last 3 desktop observations for context-aware responses
- Proactive insights emitted via Socket.IO every 5 minutes

### Desktop Observation System
- Runs on Beelink (dev box) — sends OCR snapshots of active screen every 20s
- Detects emails, bill amounts, senders, code errors
- Kilo sees what you're working on and can proactively help

### ML Engine
- Learns from real data: habit streaks, dropoff days, best performance day
- Medication adherence rates over rolling 7-day window
- Month-over-month spending spikes by category (>30% triggers alert)
- Runs at startup + nightly at 2am
- Results available via `/ml/insights`

### Camera System (IP Camera Ready)
- Register cameras by URL: `POST /cam/cameras {"name": "front_door", "url": "http://cam-ip/snapshot.jpg", "type": "http"}`
- Supports HTTP snapshot URLs and RTSP streams
- Per-camera snapshot history with OCR
- No USB webcam required — waiting for WiFi IP cameras

### Self-Healing Health Monitor
- Checks all 9 microservices every 60 seconds
- Detects CrashLoopBackOff via Kubernetes API
- Auto-deletes crashed pods (triggers k8s restart)
- Notifies Kilo via observations so it can inform you

---

## Frontend Routes

| Route | Page |
|-------|------|
| `/guardian/dashboard` | Chat with Kilo |
| `/guardian/user` | User Dashboard (meds, habits, finance) |
| `/guardian/admin-panel` | Admin Dashboard (pods, metrics, topology) |
| `/guardian/admin` | Admin Login |

---

## Deployment

All services run in namespace `kilo-guardian` on HP (`192.168.68.57`).

Code is loaded via **hostPath volumes** from `/home/kilo/Desktop/Kilo_Ai_microservice/services/<name>/`.  
To deploy a code change: edit the file on HP, then restart the pod:
```bash
sudo kubectl delete pod -n kilo-guardian -l app=<service-name>
```

AI Brain `main.py` is additionally overlaid by ConfigMap `brain-main-code`. Update both:
```bash
sudo kubectl create configmap brain-main-code -n kilo-guardian \
  --from-file=main.py=services/ai_brain/main.py \
  --dry-run=client -o yaml | sudo kubectl apply -f -
sudo kubectl delete pod -n kilo-guardian -l app=kilo-ai-brain
```

---

## Data Storage

All microservices share a single SQLite database via PVC:
- **Path in pod**: `/app/kilo_data/kilo_guardian.db`
- **Tables**: `medication`, `habit`, `habit_completion`, `reminder`, `transaction`, `budget`, `goal`, `library_entry`, `observation`, `conversation_session`, `ml_pattern`
- Camera DB separate: `/app/cameras.db` (hostPath in cam service dir)

---

## Archived Services

Services that were shut down to reduce resource usage are documented in [`archive/ARCHIVE.md`](archive/ARCHIVE.md) with full restoration instructions:
- Ray cluster / KubeRay
- vLLM, Ollama k8s service
- Briefing, Drone Control, Security Monitor plugins
- kilo-guardian plugin engine, kilo-reasoning-engine
- kilo-voice, kilo-marketing, kilo-meshtastic, kilo-usb-transfer, kilo-vpn-client

---

## Docs

See [`docs/`](docs/) for:
- `CHANGELOG.md` — full history of changes
- `ARCHITECTURE.md` — detailed system design
- `DEPLOYMENT.md` — deployment procedures
- `API_DOCUMENTATION.md` — all API endpoints
- `CAMERA_SETUP_GUIDE.md` — IP camera setup when cameras arrive
