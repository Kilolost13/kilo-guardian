import datetime
from sqlmodel import Session, select
from shared.models import Med

def get_due_meds(engine):
    with Session(engine) as session:
        meds = session.exec(select(Med)).all()
        due = []
        now = datetime.datetime.utcnow()
        for med in meds:
            if not med.last_taken:
                due.append(med)
                continue
            
            try:
                last_taken = datetime.datetime.fromisoformat(med.last_taken)
                # Simple daily logic: if last taken is not today
                if last_taken.date() < now.date():
                    due.append(med)
            except ValueError:
                due.append(med)
        return due

def record_taken(engine, med_id: int):
    with Session(engine) as session:
        med = session.get(Med, med_id)
        if med:
            med.last_taken = datetime.datetime.utcnow().isoformat()
            med.taken_count += 1
            session.add(med)
            session.commit()
            session.refresh(med)
            return med
    return None
