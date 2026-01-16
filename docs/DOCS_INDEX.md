# Kilo AI Documentation Structure

All documentation has been organized into logical directories for easier navigation.

## Directory Structure

```
docs/
├── certificates/               # SSL/TLS certificates for HTTPS
│   └── kilo-certificate.crt   # Self-signed certificate for tablet
│
├── session-notes/              # Session summaries and feature implementation notes
│   ├── FINANCIAL_INTEGRATION_COMPLETE.md
│   ├── SESSION_SUMMARY_2026-01-16.md
│   └── WEEKLY_SCHEDULE_WIDGET.md
│
├── setup-guides/               # Setup and configuration guides
│   ├── BEELINK_MANUAL_SETUP.txt
│   ├── BEELINK_SECURE_WIFI.md
│   ├── BEELINK_WIFI_GATEWAY.md
│   ├── HTTPS_CERTIFICATE_GUIDE.md  # Instructions for HTTPS setup
│   ├── TABLET_ACCESS_SOLUTION.md
│   ├── TABLET_ACCESS_UPDATED.md
│   ├── TABLET_NETWORK_FIX.md
│   └── TABLET_WORKING.md
│
├── ARCHIVE/                    # Historical reports and old documentation
│   ├── fix-reports/            # Bug fixes and issue resolutions
│   ├── historical-reports/     # Old status reports and audits
│   └── implementation-reports/ # Feature implementation summaries
│
├── ROADMAPS/                   # Future development plans
│   ├── INTEGRATION_ROADMAP.md
│   └── VOICE_ROADMAP.md
│
└── [Core Documentation]        # Main project docs at root level
    ├── README.md
    ├── ARCHITECTURE.md
    ├── DEPLOYMENT.md
    ├── FEATURES.md
    ├── OPERATIONS.md
    ├── QUICK_START.md
    └── ...
```

## Quick Links

### Getting Started
- [README](README.md) - Project overview
- [QUICK_START](QUICK_START.md) - Fast setup guide
- [DEPLOYMENT](DEPLOYMENT.md) - Deployment instructions

### Current Session Work (2026-01-16)
- [Session Summary](session-notes/SESSION_SUMMARY_2026-01-16.md) - Today's fixes
- [HTTPS Setup](setup-guides/HTTPS_CERTIFICATE_GUIDE.md) - Camera access via HTTPS
- [Financial Integration](session-notes/FINANCIAL_INTEGRATION_COMPLETE.md) - Bill tracking
- [Weekly Schedule Widget](session-notes/WEEKLY_SCHEDULE_WIDGET.md) - Calendar feature

### Setup Guides
- **Beelink AI Server**
  - [Manual Setup](setup-guides/BEELINK_MANUAL_SETUP.txt)
  - [Secure WiFi](setup-guides/BEELINK_SECURE_WIFI.md)
  - [WiFi Gateway](setup-guides/BEELINK_WIFI_GATEWAY.md)
  
- **Tablet Access**
  - [HTTPS Certificate Guide](setup-guides/HTTPS_CERTIFICATE_GUIDE.md) ⭐ NEW
  - [Access Solution](setup-guides/TABLET_ACCESS_SOLUTION.md)
  - [Network Fix](setup-guides/TABLET_NETWORK_FIX.md)
  - [Working Status](setup-guides/TABLET_WORKING.md)

### Technical Documentation
- [Architecture](ARCHITECTURE.md) - System design
- [API Documentation](API_DOCUMENTATION.md) - REST API reference
- [Operations](OPERATIONS.md) - Running and maintaining
- [Troubleshooting](troubleshooting.md) - Common issues

### Development
- [Developer Guide](developer_guide.md)
- [User Guide](user_guide.md)
- [Models](models.md) - Data models
- [System Data Flow](SYSTEM_DATA_FLOW.md)

## Recent Updates (2026-01-16)

1. **AI Chat Working** ✅
   - Fixed rag.py to support llama.cpp server
   - Updated to use OpenAI-compatible API endpoints
   - Connected to Beelink Ministral-3-14B model

2. **HTTPS Enabled** ✅
   - Self-signed certificate created
   - Nginx reverse proxy configured
   - Camera access now available on tablet
   - Guide: [setup-guides/HTTPS_CERTIFICATE_GUIDE.md](setup-guides/HTTPS_CERTIFICATE_GUIDE.md)

3. **Financial Integration** ✅
   - Bills auto-create reminders
   - Bills auto-create habit tracking
   - AI brain receives bill notifications
   - Pattern matches meds service

4. **Weekly Schedule Widget** ✅
   - 7-day calendar view
   - Morning/afternoon/evening sections
   - Clickable days with detail modal
   - Starts on Monday

## File Locations

- **Certificates**: `docs/certificates/`
- **Recent Work**: `docs/session-notes/`
- **Setup Guides**: `docs/setup-guides/`
- **Old Reports**: `docs/ARCHIVE/`
