# KILO Guardian AI - Pod Communication Architecture

## Critical Data Flow for AI/ML Learning

### 1. Medication Entry Flow
```
USER (Tablet) → FRONTEND → MEDS POD
                              ↓
                    ┌─────────┴─────────┐
                    ↓                   ↓
              REMINDER POD          HABITS POD
              (creates             (creates
               reminders)           habit tracker)
                    ↓                   ↓
                    └─────────┬─────────┘
                              ↓
                         AI BRAIN
                    (logs med.prescribed event)
```

**Endpoints Used:**
- Meds → Reminder: `POST /series` - Creates recurring reminder series
- Meds → Habits: `POST /med-adherence` - Creates habit tracking entry
- Meds → AI Brain: `POST /events` - Logs medication prescription

**Code Location:** `/services/meds/main.py` line ~251-270

---

### 2. Reminder Notification Flow
```
APSCHEDULER (in reminder pod)
      ↓
Creates NOTIFICATION record (sent=False)
      ↓
FRONTEND polls GET /notifications/pending (every 30s)
      ↓
InteractiveNotification Component displays:
  ┌─────────────────────────────────┐
  │ 💊 Take Medication XYZ          │
  │ ___________________________     │
  │ Notes: [optional field]         │
  │ [Done] [Snooze ▼] [Skip] [X]   │
  └─────────────────────────────────┘
```

**Endpoints Used:**
- Frontend → Reminder: `GET /notifications/pending` - Poll for new notifications
- APScheduler internal: Creates Notification records

**Code Location:**
- Backend: `/services/reminder/main.py` line ~217-280 (_send_reminder)
- Frontend: `/frontend/src/components/InteractiveNotification.tsx`

---

### 3. User Action Flow (CRITICAL FOR AI/ML)
```
USER clicks [Done] / [Skip] / [Snooze]
      ↓
FRONTEND → REMINDER POD
           POST /notifications/{id}/confirm
           {
             "action": "completed",
             "notes": "took with breakfast",
             ...
           }
      ↓
REMINDER POD → HABITS POD
               POST /record-reminder-action
               {
                 "reminder_id": 123,
                 "action": "completed",
                 "reminder_text": "Take Med XYZ",
                 "timestamp": "2026-01-17T04:00:00Z",
                 "notes": "took with breakfast"
               }
      ↓
HABITS POD:
  1. Finds associated Habit by name/med_id
  2. Creates HabitCompletion record:
     - habit_id: link to Habit
     - completion_date: today
     - count: 1 (if completed) or 0 (if skipped)
     - reminder_id: link back to reminder
     - status: "completed" | "skipped" | "snoozed"
  3. Sends to AI BRAIN → ML learning
      ↓
AI BRAIN learns:
  - Adherence patterns
  - Time preferences
  - Skip reasons
  - Success/failure predictors
```

**Endpoints Used:**
- Frontend → Reminder: `POST /notifications/{id}/confirm`
- Reminder → Habits: `POST /record-reminder-action` ✅ **NEW - CRITICAL**
- Habits → AI Brain: Background task `_send_completion_to_ai_brain()`

**Code Locations:**
- Reminder confirm: `/services/reminder/main.py` line ~917-995
- Habits record: `/services/habits/main.py` line ~322-405 ✅ **NEWLY ADDED**

---

### 4. Finance Flow (Similar Pattern)
```
USER adds bill/expense → FINANCE POD
                              ↓
                    ┌─────────┴─────────┐
                    ↓                   ↓
              REMINDER POD          HABITS POD
              (bill due date)      (spending habits)
                    ↓                   ↓
                         AI BRAIN
```

**Currently:** Finance → Reminder/Habits communication **NOT IMPLEMENTED**
**Status:** Finance pod does NOT currently notify reminder/habits (needs implementation)

---

## Database Schema for ML Learning

### Notification Table (Reminder Pod)
```sql
CREATE TABLE notification (
    id INTEGER PRIMARY KEY,
    channel VARCHAR,           -- 'reminder', 'med', 'habit'
    payload_json TEXT,          -- {"id": 123, "text": "...", "when": "..."}
    sent BOOLEAN DEFAULT FALSE, -- True after user interacts
    created_at TIMESTAMP
);
```

### HabitCompletion Table (Habits Pod)
```sql
CREATE TABLE habitcompletion (
    id INTEGER PRIMARY KEY,
    habit_id INTEGER,           -- Link to Habit
    completion_date VARCHAR,    -- ISO date "2026-01-17"
    count INTEGER,              -- 1 if completed, 0 if skipped
    reminder_id INTEGER,        -- Link back to Reminder ✅ CRITICAL
    status VARCHAR,             -- "completed" | "skipped" | "snoozed"
    med_id INTEGER              -- Optional link to Med
);
```

**Why reminder_id is critical:**
- Links reminder → action → outcome
- AI can learn: "Reminder at 8am → 90% completion, Reminder at 6am → 40% completion"
- Enables pattern detection for optimal reminder times

---

## Complete Action Types

### 1. **Done/Completed**
- Records HabitCompletion with count=1, status="completed"
- Deletes one-time reminders
- Sends to AI: "User successfully completed task"
- ML learns: Time of day, day of week, context that leads to success

### 2. **Skip**
- Records HabitCompletion with count=0, status="skipped"
- Keeps reminder (if recurring)
- Sends to AI: "User intentionally skipped"
- ML learns: When/why user tends to skip

### 3. **Snooze**
- Creates NEW reminder X minutes later
- Records original as status="snoozed"
- Sends to AI: "User not ready yet"
- ML learns: Snooze patterns, optimal follow-up timing

### 4. **Dismiss (X button)**
- Marks notification.sent=True
- **NO habit record created** (silent dismiss)
- **NO AI learning** (no data sent)
- Used for: Accidental reminders, irrelevant notifications

---

## Gateway Routing

All external traffic goes through Gateway pod:

```
Tablet (192.168.68.61) → HTTPS 8443
      ↓
  Gateway Pod (kilo-gateway)
      ↓
  Routes to backend services:
    /api/meds/* → kilo-meds:9000
    /api/reminder/* → kilo-reminder:9002
    /api/habits/* → kilo-habits:9003
    /api/finance/* → kilo-finance:9001
    /api/ai/* → AI Brain (brain_ai@beelink)
```

---

## Testing the Flow

### Test 1: Add a Medication
```bash
# 1. Add med via tablet
curl -X POST https://192.168.68.61:8443/api/meds/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Med",
    "frequency_per_day": 2,
    "times": ["08:00", "20:00"]
  }'

# 2. Verify reminder created
curl https://192.168.68.61:8443/api/reminder/ | jq

# 3. Verify habit created
curl https://192.168.68.61:8443/api/habits/ | jq
```

### Test 2: Complete a Notification
```bash
# 1. Check for pending notifications
curl https://192.168.68.61:8443/api/reminder/notifications/pending

# 2. Complete notification
curl -X POST https://192.168.68.61:8443/api/reminder/notifications/123/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "action": "completed",
    "notes": "Test completion"
  }'

# 3. Verify habit completion recorded
curl https://192.168.68.61:8443/api/habits/ | jq '.[] | select(.med_id)'
```

---

## Current Status

✅ **WORKING:**
- Meds → Reminder (creates reminder series)
- Meds → Habits (creates habit tracker)
- Reminder → Notification (APScheduler)
- Frontend → Polls notifications
- Frontend → Reminder confirm action
- **Reminder → Habits record action** ✅ NEWLY IMPLEMENTED
- Habits → AI Brain (background tasks)

❌ **NOT IMPLEMENTED:**
- Finance → Reminder (bill due dates)
- Finance → Habits (spending patterns)
- AI Brain feedback loop (AI adjusting reminder times based on learning)

---

## Next Steps for Full AI Integration

1. **Implement Finance Integration**
   - Finance pod should call reminder/habits on bill creation
   - Similar pattern to meds pod

2. **AI Brain Feedback Loop**
   - AI Brain analyzes HabitCompletion patterns
   - Sends recommendations back to Reminder pod
   - Reminder adjusts times based on ML insights

3. **Enhanced Context**
   - Add location data (if available)
   - Add mood/energy tracking
   - Cross-reference with calendar events

4. **Dashboard Analytics**
   - Visualize completion rates
   - Show optimal times
   - Display AI recommendations

---

**Last Updated:** 2026-01-17 04:21:00 UTC
**Author:** KILO Guardian Development Team
