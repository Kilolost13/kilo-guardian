import datetime
from sqlmodel import Session, select
from shared.models import Habit, HabitCompletion

def get_today_habit_status(engine):
    today = datetime.datetime.utcnow().date().isoformat()
    with Session(engine) as session:
        habits = session.exec(select(Habit).where(Habit.active == True)).all()
        status = []
        for h in habits:
            completion = session.exec(
                select(HabitCompletion).where(
                    HabitCompletion.habit_id == h.id,
                    HabitCompletion.completion_date == today
                )
            ).first()
            
            status.append({
                "habit": h.name,
                "id": h.id,
                "target": h.target_count,
                "completed_today": completion.count if completion else 0,
                "is_done": (completion.count >= h.target_count) if completion else False
            })
        return status
