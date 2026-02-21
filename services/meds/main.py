import os
import sys
import asyncio
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import Response
from PIL import Image
from io import BytesIO
import httpx
from sqlmodel import Session, select, create_engine
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Add shared directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shared.models import Med, OcrJob
from shared.utils.ocr import preprocess_image_for_ocr, parse_frequency, parse_times
from shared.utils.persona import get_quip
from autonomy import get_due_meds, record_taken

# KILO INTEGRATION - Wire this service to Kilo's brain!
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from kilo_integration import KiloNerve

# Use shared database path from PVC
db_url = os.getenv("DATABASE_URL", "sqlite:////app/kilo_data/kilo_guardian.db")
engine = create_engine(db_url, connect_args={"check_same_thread": False})

IMAGE_STORAGE_DIR = Path("/app/kilo_data/prescription_images")

app = FastAPI(title="Kilo Meds Service - Gremlin Edition 😈")

# Initialize Kilo nerve
kilo_nerve = KiloNerve("meds")

@app.on_event("startup")
async def startup():
    IMAGE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    # Tell Kilo we're online
    await kilo_nerve.send_observation(
        content="Meds service online and ready to track pills! 💊",
        priority="low"
    )

@app.get("/health")
def health():
    return {"status": "ok", "message": "I'm alive and lurking! 😈"}

@app.get("/")
def list_meds():
    with Session(engine) as session:
        return {
            "meds": session.exec(select(Med)).all(),
            "gremlin_message": "I've counted every single pill. Don't try to hide them! 💊"
        }

@app.get("/due")
def list_due_meds():
    """Autonomous endpoint to check what is due NOW with Gremlin flavor."""
    due = get_due_meds(engine)
    message = get_quip("meds_due") if due else "Everything is taken! How boringly responsible of you. 🙄"
    return {
        "due": due,
        "count": len(due),
        "gremlin_message": message
    }

@app.post("/take/{med_id}")
async def take_med(med_id: int):
    """Mark a medication as taken and update local state."""
    med = record_taken(engine, med_id)
    if not med:
        raise HTTPException(status_code=404, detail="I couldn't find that bottle! Did you eat it? 🧐")
    
    # KILO INTEGRATION - Tell Kilo what happened!
    await kilo_nerve.send_observation(
        content=f"User took {med.name} ({med.dosage})",
        priority="normal",
        metadata={
            "med_id": med.id,
            "med_name": med.name,
            "dosage": med.dosage,
            "time_taken": datetime.now().isoformat()
        }
    )
    
    # Also emit real-time event
    await kilo_nerve.emit_event(
        "med_taken",
        {
            "med_name": med.name,
            "dosage": med.dosage,
            "med_id": med.id
        }
    )
    
    return {
        "med": med,
        "gremlin_message": get_quip("meds_taken")
    }

@app.post("/add")
async def add_med(med: Med):
    with Session(engine) as session:
        session.add(med)
        session.commit()
        session.refresh(med)
        
        # KILO INTEGRATION - New med added!
        await kilo_nerve.send_observation(
            content=f"New medication added: {med.name} ({med.dosage}) - {med.schedule}",
            priority="normal",
            metadata={
                "med_id": med.id,
                "med_name": med.name,
                "dosage": med.dosage,
                "frequency": med.schedule,
                "times": med.times
            }
        )
        
        await kilo_nerve.emit_event(
            "med_added",
            {
                "med_name": med.name,
                "dosage": med.dosage,
                "frequency": med.schedule
            }
        )
        
        return {
            "med": med,
            "gremlin_message": f"Added {med.name}. More chores for you, more data for ME! 😈"
        }

@app.delete("/{med_id}")
async def delete_med(med_id: int):
    """Delete a medication by ID. Kilo likes deleting things! 😈"""
    with Session(engine) as session:
        med = session.get(Med, med_id)
        if not med:
            raise HTTPException(status_code=404, detail="I couldn't find that med! Maybe a digital rat ate it? 🐀")
        
        med_name = med.name
        session.delete(med)
        session.commit()
        
        # KILO INTEGRATION - Med deleted!
        await kilo_nerve.alert_kilo(
            alert_type="health",
            message=f"Medication deleted: {med_name}",
            severity="info"
        )
        
        return {"message": f"Hehehe! {med_name} has been erased from existence! 💥"}
