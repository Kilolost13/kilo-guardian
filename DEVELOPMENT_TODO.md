# Development TODO Items

This document tracks TODO items found in the codebase that represent future enhancements and features to be implemented.

**Last Updated:** 2026-01-06

---

## Voice Service (`services/voice/main.py`)

### Speech-to-Text Integration
- **Location:** `services/voice/main.py:65`
- **Priority:** Medium
- **Description:** Implement Whisper integration for local speech-to-text
- **Context:** Currently returns placeholder response
- **Estimated Effort:** 2-3 days
- **Dependencies:** Whisper model files, local inference setup

### Text-to-Speech Integration
- **Location:** `services/voice/main.py:88`
- **Priority:** Medium
- **Description:** Implement Piper TTS integration for local text-to-speech
- **Context:** Currently returns placeholder response
- **Estimated Effort:** 2-3 days
- **Dependencies:** Piper TTS models, audio output configuration

---

## AI Brain Service (`services/ai_brain/main.py`)

### Whisper Microservice Integration
- **Location:** `services/ai_brain/main.py:422`
- **Priority:** Medium
- **Description:** Integrate with local Whisper microservice for transcription
- **Context:** Part of voice input pipeline
- **Estimated Effort:** 1-2 days
- **Dependencies:** Voice service Whisper implementation

---

## ML Engine Service (`services/ml_engine/main.py`)

### Feature Extraction Enhancement
- **Location:** `services/ml_engine/main.py:591`
- **Priority:** Low
- **Description:** Extract real features from habit completion history for predictions
- **Context:** Currently uses placeholder feature extraction
- **Estimated Effort:** 3-5 days
- **Dependencies:** Completion history data schema

---

## Camera Service (`services/cam/main.py`)

### Serial PTZ Connection
- **Location:** `services/cam/main.py:100`
- **Priority:** Low
- **Description:** Implement serial connection for PTZ camera control
- **Context:** Hardware integration for physical camera control
- **Estimated Effort:** 5-7 days
- **Dependencies:**
  - Serial communication library (pyserial)
  - PTZ camera hardware
  - Protocol documentation (VISCA, Pelco-D, etc.)
- **Notes:** Mock implementation currently in place for testing

### Network PTZ Connection (ONVIF/VISCA)
- **Location:** `services/cam/main.py:104`
- **Priority:** Low
- **Description:** Implement network connection for IP-based PTZ cameras
- **Context:** Support for ONVIF, VISCA over IP, and other network protocols
- **Estimated Effort:** 7-10 days
- **Dependencies:**
  - ONVIF library (python-onvif-zeep)
  - Network camera hardware
  - Protocol implementation
- **Notes:** Would enable remote PTZ control over network

### Hardware PTZ Control
- **Location:** `services/cam/main.py:114`
- **Priority:** Low
- **Description:** Implement actual hardware control for PTZ positioning
- **Context:** Currently uses mock hardware interface
- **Estimated Effort:** Depends on serial/network implementation
- **Dependencies:** Serial or network PTZ implementation (above items)

### Hardware Position Reading
- **Location:** `services/cam/main.py:121`
- **Priority:** Low
- **Description:** Implement actual position reading from PTZ hardware
- **Context:** Feedback loop for accurate PTZ positioning
- **Estimated Effort:** 2-3 days
- **Dependencies:** Hardware PTZ control implementation

### Hardware Stop Command
- **Location:** `services/cam/main.py:136`
- **Priority:** Low
- **Description:** Implement actual stop command for PTZ movement
- **Context:** Emergency stop and precise positioning control
- **Estimated Effort:** 1 day
- **Dependencies:** Hardware PTZ control implementation

### Multipart Image Upload
- **Location:** `services/cam/main.py:1960`
- **Priority:** Low
- **Description:** Add multipart format support for image uploads in addition to JSON
- **Context:** Currently only supports JSON metadata format
- **Estimated Effort:** 2-3 days
- **Use Case:** Direct image file uploads for external camera integration

---

## Priority Summary

### High Priority (0 items)
None currently

### Medium Priority (3 items)
1. Voice service Whisper STT integration
2. Voice service Piper TTS integration
3. AI Brain Whisper microservice integration

### Low Priority (7 items)
1. ML Engine feature extraction enhancement
2. Camera serial PTZ connection
3. Camera network PTZ connection
4. Camera hardware PTZ control
5. Camera hardware position reading
6. Camera hardware stop command
7. Camera multipart image upload

---

## Implementation Roadmap

### Phase 1: Voice Features (Estimated: 4-6 weeks)
- Implement Whisper STT in voice service
- Implement Piper TTS in voice service
- Integrate AI Brain with Whisper microservice
- **Value:** Enables full voice interaction capabilities

### Phase 2: ML Enhancements (Estimated: 1 week)
- Enhance feature extraction in ML engine
- **Value:** Improves habit prediction accuracy

### Phase 3: Hardware Integration (Estimated: 8-12 weeks)
- Implement serial PTZ connection
- Implement network PTZ connection (ONVIF/VISCA)
- Complete hardware control implementation
- Add position feedback
- Add emergency stop
- **Value:** Enables physical camera automation

### Phase 4: Media Handling (Estimated: 1 week)
- Add multipart image upload support
- **Value:** Simplifies external camera integration

---

## Notes

- All TODO items have mock/placeholder implementations in place
- System is fully functional without these enhancements
- Priority is based on user value and architectural impact
- Effort estimates assume single developer, may vary with team size
- Hardware items (PTZ) require physical equipment for testing

---

## Completion Tracking

**Total TODO Items:** 10
**Completed:** 0
**In Progress:** 0
**Planned:** 10

---

**For questions or to propose new features, open an issue in the repository.**
