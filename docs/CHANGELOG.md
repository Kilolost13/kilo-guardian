## [2026-02-21] — Camera, ML Engine, Archival & Major System Fixes

### Added
- **IP Camera module (kilo-cam)**: Completely rewritten. Removed USB webcam dependency. Now supports HTTP snapshot URLs and RTSP streams via SQLite camera registry. Endpoints: `/cameras` CRUD, `/cameras/{id}/snapshot`, `/cameras/{id}/snapshot?ocr=true`, `/cameras/all/check`. Ready to register real WiFi IP cameras when purchased.
- **ML Engine (kilo-ml-engine)**: New real-data pattern learning from habits, meds, and financial microservices. Detects habit streaks/dropoffs, medication adherence rates, and month-over-month spending spikes (>30%). Saves `pattern_cache.json` to PVC. Runs at startup and nightly at 2am. Endpoints: `/insights`, `/learn`, `/predict/habit/{id}`.
- **Session memory persistence**: Conversation history now survives pod restarts via `conversation_session` SQLite table. Loaded on startup, pruned to last N turns per user.
- **Proactive Socket.IO insights**: Background loop generates Gemini insights every 5 minutes from recent desktop observations. Emits `insight_generated` event to Dashboard via gateway `/emit`.
- **Self-healing health monitor (kilo-health-monitor)**: Checks 9 microservices via HTTP, uses k8s REST API (in-cluster token) to detect CrashLoopBackOff pods and auto-delete for restart. Notifies Kilo via `/observations`.
- **Desktop observation integration**: Desktop observer on Beelink posts OCR detections to AI Brain every 20 seconds. Last 3 observations injected into Gemini prompt context so Kilo sees what Kyle is working on.
- **Enhanced reminder parser**: Context-aware parsing with pronoun resolution (detects bills from observations), flexible date parsing ("march 1st", "when I get paid", "first of next month").
- **Gemini function calling date filtering**: Spending queries now filter by date range. Default: current month only. Categories broken down per query.
- **Archive directory**: `archive/ARCHIVE.md` documents all 13 retired services with restoration notes (Ray cluster, vLLM, Ollama k8s, Briefing, Drone Control, Security Monitor, etc.).
- **Admin dashboard K8s endpoints**: `/k8s/pods`, `/k8s/nodes`, `/k8s/cronjobs`, pod restart/delete via gateway.
- **Node CPU/memory metrics**: Gateway calls `kubectl top nodes`, parses real percentages (was hardcoded 0%).
- **Gateway chat routing**: Dedicated `/chat/{path:path}` routes before catch-all so `/chat/llm` proxies correctly to AI Brain.

### Changed
- **LLM backend**: Switched from Ray Serve / Ollama CPU inference (~51s) to **Gemini 2.0 Flash** (~1s response time). Ollama kept as fallback.
- **Architecture streamlined**: Removed 11 dead deployments and 16 dead services. Active pods reduced from 22 to 11. Simplified service map.
- **kilo-cam deployment**: Removed `/dev/video0` device mount. Now mounts only the code hostPath.

### Fixed
- Gateway catch-all route ordering: K8s routes moved before `/{service}/{path:path}` pattern
- `@app.on_event("startup")` not firing: moved session init into `lifespan` context manager
- ML Engine financial parsing: handles both `list` and `{"transactions": [...]}` response formats
- Health monitor 422 error: added `type` field to `/observations` POST body
- `kubectl` not found in pod: switched to k8s REST API calls via httpx
- Syntax errors from literal newlines in f-strings: use `chr(10)` and string concatenation
- AI Brain `/chat/llm` routing through nginx/gateway

### Archived (not deleted, see archive/ARCHIVE.md)
- Ray cluster (KubeRay), vLLM, Ollama k8s service, Briefing plugin, Drone Control plugin, Security Monitor plugin, kilo-guardian plugin engine, kilo-reasoning-engine, kilo-socketio, kilo-marketing, kilo-meshtastic, kilo-usb-transfer, kilo-voice, kilo-vpn-client


# Changelog

## [Unreleased]

### Added
- Consolidated frontend improvements: tightened TypeScript types, fixed ESLint hook warnings, added CI workflow, merged enhanced Dashboard & Tablet UI features. (See PR #1)

### Fixed
- Jest/ESM issues for unit tests and runtime stability (regenerator-runtime added, axios transform); guarded DOM calls in tests.

### Notes
- Production build succeeds with non-blocking TypeScript parser warnings (consider pinning TS if desired).

---

Released commits:
- Merge PR #1 — "frontend: tighten types, fix ESLint hooks, add CI & integrate UI enhancements" (merged 2025-12-24)
