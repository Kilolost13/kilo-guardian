from fastapi import FastAPI, HTTPException, BackgroundTasks
from sqlmodel import SQLModel, create_engine, Session, Field
from typing import Optional, List
import os
import httpx
import datetime

# Habit models
class Habit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    frequency: str = "daily"
    target_count: int = 1
    active: bool = True

class HabitCompletion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    habit_id: int
    completion_date: str
    count: int = 1

db_url = "sqlite:////tmp/habits.db"
engine = create_engine(db_url, echo=False)


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        SQLModel.metadata.create_all(engine)
    except Exception:
        pass
    yield


app = FastAPI(title="Habits Service", lifespan=lifespan)

# Health check endpoints
@app.get("/status")
@app.get("/health")
def status():
    return {"status": "ok"}

AI_BRAIN_URL = os.getenv("AI_BRAIN_URL", "http://ai_brain:9004/ingest/habit")

# optional centralized admin validation client (gateway) - lazy import
gateway_validate_token = None


def _require_admin(headers: dict = None) -> bool:
    """If an X-Admin-Token header is present, validate it via gateway; otherwise permissive when no local ADMIN_TOKEN is set."""
    token_required = os.getenv("ADMIN_TOKEN")
    token = None
    if headers:
        token = headers.get('x-admin-token') or headers.get('X-Admin-Token')
    if token_required:
        if token == token_required:
            return True
        raise Exception("invalid admin token")
    # no local token: permissive if no header; if header provided, attempt gateway validation
    if not token:
        return True
    global gateway_validate_token
    if gateway_validate_token is None:
        try:
            from microservice.gateway.admin_client import validate_token as _gval
            gateway_validate_token = _gval
        except Exception:
            gateway_validate_token = None
    if gateway_validate_token:
        try:
            return gateway_validate_token(token)
        except Exception:
            return False
    return False

# startup handled by lifespan

@app.get("/")
def list_habits():
    with Session(engine) as session:
        habits = session.query(Habit).all()
        result = []
        for h in habits:
            # Get completions for this habit
            completions = session.query(HabitCompletion).filter(HabitCompletion.habit_id == h.id).all()
            # Convert to dict and add completions
            habit_dict = {
                "id": h.id,
                "name": h.name,
                "frequency": h.frequency,
                "target_count": h.target_count,
                "active": h.active,
                "completions": [
                    {
                        "id": c.id,
                        "habit_id": c.habit_id,
                        "completion_date": c.completion_date,
                        "count": c.count
                    } for c in completions
                ]
            }
            result.append(habit_dict)
        return result

@app.post("/")
def add_habit(h: Habit, background_tasks: BackgroundTasks = None):
    with Session(engine) as session:
        session.add(h)
        session.commit()
        session.refresh(h)
    # Send to ai_brain
    if background_tasks:
        background_tasks.add_task(_send_to_ai_brain, h)
    else:
        import asyncio
        asyncio.create_task(_send_to_ai_brain(h))
    return h

@app.put("/{habit_id}")
def update_habit(habit_id: int, h: Habit):
    with Session(engine) as session:
        db_habit = session.get(Habit, habit_id)
        if not db_habit:
            raise HTTPException(status_code=404, detail="Habit not found")
        db_habit.name = h.name
        db_habit.frequency = h.frequency
        db_habit.target_count = h.target_count
        db_habit.active = h.active
        session.add(db_habit)
        session.commit()
        session.refresh(db_habit)
        return db_habit

@app.delete("/{habit_id}")
def delete_habit(habit_id: int):
    with Session(engine) as session:
        habit = session.get(Habit, habit_id)
        if not habit:
            raise HTTPException(status_code=404, detail="Habit not found")
        # Delete associated completions
        completions = session.query(HabitCompletion).filter(HabitCompletion.habit_id == habit_id).all()
        for c in completions:
            session.delete(c)
        session.delete(habit)
        session.commit()
    return {"status": "deleted"}

@app.post("/complete/{habit_id}")
def complete_habit(habit_id: int, background_tasks: BackgroundTasks = None):
    today = datetime.datetime.utcnow().date().isoformat()
    with Session(engine) as session:
        habit = session.get(Habit, habit_id)
        if not habit:
            raise HTTPException(status_code=404, detail="Habit not found")

        # Check if already completed today
        existing = session.query(HabitCompletion).filter(
            HabitCompletion.habit_id == habit_id,
            HabitCompletion.completion_date == today
        ).first()

        if existing:
            existing.count += 1
            session.commit()
            session.refresh(existing)
            completion = existing
        else:
            completion = HabitCompletion(
                habit_id=habit_id,
                completion_date=today,
                count=1
            )
            session.add(completion)
            session.commit()
            session.refresh(completion)

    # Send to ai_brain
    if background_tasks:
        background_tasks.add_task(_send_completion_to_ai_brain, habit, completion)
    else:
        import asyncio
        asyncio.create_task(_send_completion_to_ai_brain(habit, completion))
    return completion

async def _send_to_ai_brain(h: Habit):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(AI_BRAIN_URL, json={
                "name": h.name,
                "frequency": h.frequency
            }, timeout=5)
        except Exception as e:
            print(f"[AI_BRAIN] Failed to send habit: {e}")

async def _send_completion_to_ai_brain(h: Habit, c: HabitCompletion):
    async with httpx.AsyncClient() as client:
        try:
            await client.post("http://ai_brain:9004/ingest/habit_completion", json={
                "habit": h.name,
                "completion_date": c.completion_date,
                "count": c.count,
                "frequency": h.frequency
            }, timeout=5)
        except Exception as e:
            print(f"[AI_BRAIN] Failed to send habit completion: {e}")
