import os
import sys
import datetime
from typing import Optional, List, Dict
from datetime import timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select, create_engine, SQLModel, Field
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
import httpx

# --- Data Models (Autonomous) ---
class Reminder(SQLModel, table=True):
    __tablename__ = "reminder"
    id: Optional[int] = Field(default=None, primary_key=True)
    text: str
    when: str
    recurrence: Optional[str] = None
    sent: bool = False
    escalated: bool = False
    timezone: str = "UTC"
    last_triggered_date: Optional[str] = Field(default=None)  # YYYY-MM-DD, for daily recurrence

# --- Database Setup ---
db_url = os.getenv("DATABASE_URL", "sqlite:////app/kilo_data/kilo_guardian.db")
engine = create_engine(db_url, connect_args={"check_same_thread": False})

_scheduler = BackgroundScheduler()

def _schedule_reminder(r: Reminder):
    job_id = f"reminder_{r.id}"
    try:
        # Handle time-only format (HH:MM) for daily recurrence
        if r.recurrence == "daily" and ":" in r.when and len(r.when) <= 5:
            # Parse time-only string (e.g., "08:00")
            time_parts = r.when.split(":")
            hour = int(time_parts[0])
            minute = int(time_parts[1]) if len(time_parts) > 1 else 0
            trigger = CronTrigger(hour=hour, minute=minute, timezone=r.timezone)
        else:
            # Parse full ISO datetime for one-time reminders
            when_dt = datetime.datetime.fromisoformat(r.when)
            if r.recurrence == "daily":
                trigger = CronTrigger(hour=when_dt.hour, minute=when_dt.minute, timezone=r.timezone)
            else:
                trigger = DateTrigger(run_date=when_dt, timezone=r.timezone)

        _scheduler.add_job(_send_notification_task, trigger, args=[r.id], id=job_id, replace_existing=True)
        print(f"✅ Scheduled reminder {r.id}: '{r.text}' at {r.when} ({r.recurrence})")
    except Exception as e:
        print(f"Scheduling failed for {r.id}: {e}")

def _send_notification_task(reminder_id: int):
    with Session(engine) as session:
        r = session.get(Reminder, reminder_id)
        if r and not r.sent:
            print(f"🔔 REMINDER DUE: {r.text}")
            try:
                httpx.post("http://kilo-gateway:8000/api/agent/notify", json={
                    "type": "reminder",
                    "content": r.text,
                    "metadata": {"id": r.id}
                }, timeout=1)
            except Exception: pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    _scheduler.start()
    with Session(engine) as session:
        active = session.exec(select(Reminder).where(Reminder.sent == False)).all()
        for r in active:
            _schedule_reminder(r)
    yield
    _scheduler.shutdown()

app = FastAPI(title="Kilo Reminder Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "service": "reminder"}

@app.get("/")
def list_reminders():
    with Session(engine) as session:
        return session.exec(select(Reminder)).all()

@app.post("/")
async def add_reminder(r: Reminder):
    with Session(engine) as session:
        session.add(r)
        session.commit()
        session.refresh(r)
        _schedule_reminder(r)
        return r

@app.post("/{reminder_id}/acknowledge")
async def acknowledge(reminder_id: int):
    with Session(engine) as session:
        r = session.get(Reminder, reminder_id)
        if not r: raise HTTPException(status_code=404)
        if r.recurrence == "daily":
            # Daily reminders reset each day — just track the date, not permanently sent
            r.last_triggered_date = datetime.date.today().isoformat()
        else:
            r.sent = True
            try: _scheduler.remove_job(f"reminder_{reminder_id}")
            except: pass
        session.add(r)
        session.commit()
        return {"status": "ok"}

@app.get("/notifications/pending")
def get_pending_notifications():
    """Endpoint for frontend - returns only today's due/overdue reminders (not future)"""
    with Session(engine) as session:
        reminders = session.exec(select(Reminder).where(Reminder.sent == False)).all()

        now_cst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-6)))
        tomorrow_start = (now_cst + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_past = now_cst - datetime.timedelta(hours=24)  # ignore >24h overdue

        result = []
        for r in reminders:
            when_dt = None
            for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M",
                        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%H:%M"):
                try:
                    when_dt = datetime.datetime.strptime(r.when, fmt)
                    when_dt = when_dt.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=-6)))
                    break
                except ValueError:
                    continue

            if when_dt is None:
                continue  # unparseable - skip

            # Daily recurrence: show if not already triggered today and time has passed
            if r.recurrence == "daily":
                today_str = now_cst.date().isoformat()
                if r.last_triggered_date == today_str:
                    continue  # already sent today
                # Show if today's time has passed (or within next 10 min)
                reminder_today = when_dt.replace(
                    year=now_cst.year, month=now_cst.month, day=now_cst.day
                )
                mins_until = (reminder_today - now_cst).total_seconds() / 60
                if -180 <= mins_until <= 10:
                    result.append({
                        "id": r.id,
                        "title": "Reminder",
                        "message": r.text,
                        "timestamp": reminder_today.isoformat(),
                        "type": "info",
                        "priority": "normal"
                    })
            # One-time: show if due today and not more than 24h overdue
            elif when_dt >= cutoff_past and when_dt < tomorrow_start:
                result.append({
                    "id": r.id,
                    "title": "Reminder",
                    "message": r.text,
                    "timestamp": r.when,
                    "type": "info",
                    "priority": "normal"
                })

        return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9002)