# Changelog

All notable changes to Kilo Guardian will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Comprehensive logging configuration guide (`docs/LOGGING_GUIDE.md`)
- Development TODO tracking document (`DEVELOPMENT_TODO.md`)
- Production readiness audit report (`PRODUCTION_READINESS.md`)
- CHANGELOG for version tracking

### Changed
- Replaced `print()` statements with proper `logging` calls in camera service (22 occurrences)
- Replaced `print()` statements with proper `logging` calls in financial service (10 occurrences)
- Replaced `print()` statements with proper `logging` calls in meds service (1 occurrence)
- Enhanced error logging with appropriate log levels (debug, info, warning, error)

---

## [1.0.0] - 2026-01-06

### Added
- **Requirements.txt for all services** - Created dependency files for 9 previously missing services
  - Gateway: bcrypt, FastAPI, SQLModel
  - Medications: Pillow, pytesseract, OpenCV, prometheus-client
  - Habits: FastAPI, SQLModel
  - Financial: Pillow, pytesseract, PyPDF2, prometheus-fastapi-instrumentator
  - Reminder: apscheduler
  - Camera: Pillow, pytesseract, OpenCV, mediapipe
  - Library of Truth: pdfplumber, beautifulsoup4
  - SocketIO Relay: python-socketio
  - AI Brain: gTTS, tenacity, sentence-transformers
- **Production Readiness Report** - Comprehensive audit and compliance documentation
- **Enhanced .env.example** - Organized configuration with security sections and CORS settings
- **DEVELOPMENT_TODO.md** - Tracking document for all TODO items found in code

### Changed
- **CORS Configuration** - Changed from wildcard `*` to configurable `CORS_ORIGINS` environment variable
  - Updated gateway service
  - Updated camera service
  - Updated financial gateway service
  - Default: `http://localhost:3000,http://localhost:30000`
- **Database Paths** - Standardized to use `/data` instead of `/tmp` for persistence
  - Gateway: `sqlite:////data/gateway.db` (was `/tmp/gateway.db`)
  - Habits: `sqlite:////data/habits.db` (was `/tmp/habits.db`)
- **Camera Service Port** - Fixed port mismatch to align with K3s configuration
  - Changed from hardcoded `8003` to `9007` (configurable via `CAM_PORT` env var)
- **Admin Credentials** - Strengthened requirements in .env.example
  - Changed from weak `changeme-admin-REPLACE-THIS` to `GENERATE_SECURE_RANDOM_32_CHAR_STRING_HERE`
  - Added generation instructions: `openssl rand -hex 32`
- **README.md** - Corrected service count and documentation accuracy
  - Updated from "15 microservices" to "13 microservices + 2 infrastructure components"
  - Removed non-existent "Medications v2" service
  - Added Integration service to documentation
  - Updated system health message

### Fixed
- **Security Vulnerabilities**
  - CORS now restricted to specific origins instead of allowing all
  - Database persistence configured to prevent data loss on restart
  - Admin key requirements strengthened
- **Port Configuration**
  - Camera service port now matches K3s deployment configuration
  - Added environment variable override capability
- **Documentation Accuracy**
  - Fixed pod count references throughout documentation
  - Corrected service listings in README

### Removed
- Internal development file `prompt for claude` from repository root

---

## [0.9.0] - 2025-12-XX (Previous State)

### Features
- 13 fully functional microservices
- K3s-based Kubernetes deployment
- React frontend with TypeScript
- Local AI with Ollama integration
- Privacy-first architecture
- Comprehensive documentation (70+ markdown files)

### Services
1. **Gateway** - API routing and authentication
2. **Medications** - Med tracking with OCR
3. **Reminders** - Timeline and alert system
4. **Habits** - Habit tracking and analytics
5. **AI Brain** - RAG and memory search
6. **Financial** - Budget and receipt tracking
7. **Library of Truth** - Knowledge base with PDF support
8. **Camera** - Pose detection and object tracking
9. **ML Engine** - Machine learning processing
10. **Voice** - Voice input processing
11. **USB Transfer** - File transfer service
12. **SocketIO** - Real-time event relay
13. **Integration** - Service integration layer

### Infrastructure
- Frontend: React 18.3.1 with TailwindCSS
- Backend: FastAPI with Python 3.11
- Database: SQLite with SQLModel ORM
- Deployment: K3s on Pop!_OS 22.04

---

## Version History

- **1.0.0** (2026-01-06): Production-ready release with full security hardening
- **0.9.0** (2025-12-XX): Feature-complete development version

---

## Upgrade Guide

### From 0.9.x to 1.0.0

#### Required Actions

1. **Update Environment Configuration**
   ```bash
   # Copy new .env.example structure
   cp .env.example .env

   # Generate secure admin key
   ADMIN_KEY=$(openssl rand -hex 32)
   echo "LIBRARY_ADMIN_KEY=$ADMIN_KEY" >> .env

   # Configure CORS for your domain
   echo "CORS_ORIGINS=http://yourdomain.com,https://yourdomain.com" >> .env
   ```

2. **Update Service Dependencies**
   ```bash
   # For each service, install updated requirements
   cd services/gateway && pip install -r requirements.txt
   cd services/meds && pip install -r requirements.txt
   # ... repeat for all services
   ```

3. **Update Database Paths (if using custom paths)**
   ```bash
   # Ensure database paths use /data not /tmp
   echo "GATEWAY_DB_URL=sqlite:////data/gateway.db" >> .env
   echo "HABITS_DB_URL=sqlite:////data/habits.db" >> .env
   ```

4. **Rebuild Docker Images**
   ```bash
   # Rebuild all service images with new dependencies
   make build-all
   ```

5. **Apply K3s Updates**
   ```bash
   kubectl apply -f k3s/
   kubectl rollout restart deployment -n kilo-guardian
   ```

#### Breaking Changes

- **CORS Configuration**: Services no longer accept all origins by default. Must configure `CORS_ORIGINS` environment variable.
- **Camera Service Port**: Default changed from 8003 to 9007. Update any direct connections.
- **Database Paths**: Gateway and Habits services now use `/data` by default. Migrate data if needed.

#### Optional Improvements

- Configure logging level via `LOG_LEVEL` environment variable
- Review `DEVELOPMENT_TODO.md` for feature roadmap
- Set up centralized logging (see `docs/LOGGING_GUIDE.md`)

---

## Support

For questions or issues:
- Check `docs/` directory for detailed guides
- Review `PRODUCTION_READINESS.md` for deployment checklist
- Open an issue on GitHub
- Check logs: `kubectl logs -n kilo-guardian deployment/kilo-<service>`

---

**Maintained by:** Kilo Guardian Development Team
**License:** MIT
