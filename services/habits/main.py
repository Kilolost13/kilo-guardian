import os
import sys
import asyncio
import datetime
import json
from typing import Optional, List

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from sqlmodel import Session, select, create_engine
import httpx

# Add shared directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shared.models import Habit, HabitCompletion
from shared.utils.persona import get_quip
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from kilo_integration import KiloNerve
from autonomy import get_today_habit_status

# Use shared database path from PVC
db_url = os.getenv("DATABASE_URL", "sqlite:////app/kilo_data/kilo_guardian.db")
engine = create_engine(db_url, connect_args={"check_same_thread": False})

app = FastAPI(title="Kilo Habits Service - Gremlin Edition 😈")

# Initialize Kilo nerve
kilo_nerve = KiloNerve("habits")

@app.get("/health")
def health():
    return {"status": "ok", "message": "I'm watching your progress... or lack of it! 😈"}

@app.get("/")
def list_habits():
    with Session(engine) as session:
        habits = session.exec(select(Habit)).all()
        result = []
        for h in habits:
            completions = session.exec(select(HabitCompletion).where(HabitCompletion.habit_id == h.id)).all()
            habit_dict = h.dict()
            habit_dict["completions"] = [c.dict() for c in completions]
            result.append(habit_dict)
        return {
            "habits": result,
            "gremlin_message": "Look at all these rules you made for yourself! 📜"
        }

@app.get("/today")
def list_today_status():
    """Autonomous status check for what is done/pending today with Gremlin flavor."""
    status = get_today_habit_status(engine)
    pending = [h for h in status if not h["is_done"]]
    message = get_quip("habits_pending") if pending else get_quip("habits_done")
    return {
        "status": status,
        "gremlin_message": message
    }

@app.post("/")
async def add_habit(h: Habit):
    with Session(engine) as session:
        session.add(h)
        session.commit()
        session.refresh(h)
        
        # KILO INTEGRATION
        await kilo_nerve.send_observation(f"Habit created: {h.name} ({h.frequency})", priority="normal")
        
        return h

@app.post("/complete/{habit_id}")
async def complete_habit(habit_id: int):
    today = datetime.datetime.utcnow().date().isoformat()
    with Session(engine) as session:
        habit = session.get(Habit, habit_id)
        if not habit:
            raise HTTPException(status_code=404, detail="I lost that habit! It's gone! (Just kidding, it was never there). 😈")
        
        existing = session.exec(
            select(HabitCompletion).where(
                HabitCompletion.habit_id == habit_id,
                HabitCompletion.completion_date == today
            )
        ).first()
        
        if existing:
            existing.count += 1
            session.add(existing)
            session.commit()
            session.refresh(existing)
            result = existing
        else:
            result = HabitCompletion(habit_id=habit_id, completion_date=today, count=1)
            session.add(result)
            session.commit()
            session.refresh(result)
        
        return {
            "completion": result,
            "gremlin_message": f"Did you really do {habit.name}? I'll take your word for it... for now. 😈"
        }

@app.delete("/{habit_id}")
async def delete_habit(habit_id: int):
    """Delete a habit and its history. Poof! 🪄"""
    with Session(engine) as session:
        habit = session.get(Habit, habit_id)
        if not habit:
            raise HTTPException(status_code=404, detail="That habit doesn't exist! Are you seeing things? 👻")
        
        # Delete completions first
        completions = session.exec(select(HabitCompletion).where(HabitCompletion.habit_id == habit_id)).all()
        for c in completions:
            session.delete(c)
            
        session.delete(habit)
        session.commit()
        return {"message": f"I've vaporized the '{habit.name}' habit and all its evidence! 💨"}