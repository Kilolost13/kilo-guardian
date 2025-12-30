from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from PIL import Image, ImageEnhance, ImageFilter
from io import BytesIO
import pytesseract
import re
from sqlmodel import SQLModel, create_engine, Session, Field
from typing import Optional, List
import os
import httpx
import numpy as np
import cv2

# Med model definition
from datetime import datetime

class Med(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    schedule: str
    dosage: str
    quantity: int = 0
    prescriber: str = ""
    instructions: str = ""
    last_taken: Optional[str] = None  # ISO format datetime string
    taken_count: int = 0  # Track how many times taken

db_url = "sqlite:////data/meds.db"
engine = create_engine(db_url, echo=False)


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        os.makedirs("/data", exist_ok=True)
        SQLModel.metadata.create_all(engine)
    except Exception:
        pass
    yield


app = FastAPI(title="Meds OCR Service", lifespan=lifespan)

# Health check endpoints
@app.get("/status")
@app.get("/health")
def status():
    return {"status": "ok"}

AI_BRAIN_URL = os.getenv("AI_BRAIN_URL", "http://ai_brain:9004/ingest/meds")

# startup handled by lifespan

@app.get("/")
def list_meds():
    with Session(engine) as session:
        meds = session.query(Med).all()
        return meds

def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """
    Preprocess image to improve OCR accuracy:
    - Convert to grayscale
    - Enhance contrast
    - Apply denoising
    - Apply adaptive thresholding
    - Upscale for better character recognition
    """
    # Convert PIL image to numpy array
    img_array = np.array(image)

    # Convert to grayscale
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array

    # Upscale image 2x for better OCR (helps with small text)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

    # Apply adaptive thresholding to handle varying lighting
    thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    # Morphological operations to clean up noise
    kernel = np.ones((1, 1), np.uint8)
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # Convert back to PIL Image
    return Image.fromarray(cleaned)

@app.post("/extract")
def extract_med_from_image(
    file: UploadFile = File(None),
    files: List[UploadFile] = File(None),
    background_tasks: BackgroundTasks = None
):
    # Handle multiple images (stitch) or single image
    if files and len(files) > 0:
        # Multiple images - stitch them horizontally
        images = []
        for f in files:
            if not f.content_type.startswith("image/"):
                continue
            img_bytes = f.file.read()
            img = Image.open(BytesIO(img_bytes))
            images.append(img)

        if len(images) == 0:
            raise HTTPException(status_code=400, detail="No valid images provided.")

        # Stitch images horizontally
        widths, heights = zip(*(i.size for i in images))
        total_width = sum(widths)
        max_height = max(heights)
        stitched = Image.new('RGB', (total_width, max_height))
        x_offset = 0
        for img in images:
            stitched.paste(img, (x_offset, 0))
            x_offset += img.width

        # Preprocess stitched image for better OCR
        processed = preprocess_image_for_ocr(stitched)
        text = pytesseract.image_to_string(processed, config='--psm 6')
    elif file:
        # Single image
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image.")
        img_bytes = file.file.read()
        img = Image.open(BytesIO(img_bytes))
        # Preprocess single image for better OCR
        processed = preprocess_image_for_ocr(img)
        text = pytesseract.image_to_string(processed, config='--psm 6')
    else:
        raise HTTPException(status_code=400, detail="No image provided.")
    # Simple regex-based extraction with improved patterns
    name = re.search(r"(?:Name|Drug|Medication|Med|Rx):?\s*[:]*\s*([A-Z][A-Za-z0-9\-]+)", text, re.I)
    schedule = re.search(r"(?:Take|Sig|Schedule):?\s*[:]*\s*([^\n]+)", text, re.I)
    dosage = re.search(r"(?:Dosage|Dose):?\s*[:]*\s*(\d+\s*(?:mg|ml|mcg))", text, re.I)
    quantity = re.search(r"(?:Qty|Quantity|Qiy|Q|iy)[:\.\s]*(\d+)", text, re.I)
    prescriber = re.search(r"(?:Dr|Doctor)\.?\s*([A-Za-z\s]+?)(?:\n|$)", text, re.I)
    instructions = re.search(r"(?:Directions|Instructions|Notes):?\s*[:]*\s*([^\n]+)", text, re.I)
    med = Med(
        name=name.group(1).strip() if name else "",
        schedule=schedule.group(1).strip() if schedule else "",
        dosage=dosage.group(1).strip() if dosage else "",
        quantity=int(quantity.group(1)) if quantity else 0,
        prescriber=prescriber.group(1).strip() if prescriber else "",
        instructions=instructions.group(1).strip() if instructions else ""
    )
    with Session(engine) as session:
        session.add(med)
        session.commit()
        session.refresh(med)
    # Send to ai_brain
    if background_tasks:
        background_tasks.add_task(_send_to_ai_brain, med)
    else:
        import asyncio
        asyncio.create_task(_send_to_ai_brain(med))
    return med

@app.put("/{med_id}")
def update_med(med_id: int, med: Med, background_tasks: BackgroundTasks = None):
    with Session(engine) as session:
        db_med = session.get(Med, med_id)
        if not db_med:
            raise HTTPException(status_code=404, detail="Medication not found")
        db_med.name = med.name
        db_med.dosage = med.dosage
        db_med.schedule = med.schedule
        db_med.quantity = med.quantity
        db_med.prescriber = med.prescriber
        db_med.instructions = med.instructions
        session.add(db_med)
        session.commit()
        session.refresh(db_med)
    if background_tasks:
        background_tasks.add_task(_send_to_ai_brain, db_med)
    return db_med

@app.post("/add")
def add_med(med: Med, background_tasks: BackgroundTasks = None):
    with Session(engine) as session:
        session.add(med)
        session.commit()
        session.refresh(med)
    # Send to ai_brain
    if background_tasks:
        background_tasks.add_task(_send_to_ai_brain, med)
    else:
        import asyncio
        asyncio.create_task(_send_to_ai_brain(med))
    return med

@app.delete("/{med_id}")
def delete_med(med_id: int):
    with Session(engine) as session:
        med = session.get(Med, med_id)
        if not med:
            raise HTTPException(status_code=404, detail="Medication not found")
        session.delete(med)
        session.commit()
    return {"status": "deleted"}

@app.post("/{med_id}/take")
def mark_med_taken(med_id: int):
    """Mark a medication as taken right now"""
    with Session(engine) as session:
        med = session.get(Med, med_id)
        if not med:
            raise HTTPException(status_code=404, detail="Medication not found")

        # Update last taken time and increment counter
        med.last_taken = datetime.utcnow().isoformat()
        med.taken_count = (med.taken_count or 0) + 1

        session.add(med)
        session.commit()
        session.refresh(med)

    return {
        "status": "taken",
        "med_id": med.id,
        "med_name": med.name,
        "last_taken": med.last_taken,
        "taken_count": med.taken_count
    }

async def _send_to_ai_brain(med: Med):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(AI_BRAIN_URL, json={
                "name": med.name,
                "schedule": med.schedule,
                "dosage": med.dosage,
                "quantity": med.quantity,
                "prescriber": med.prescriber,
                "instructions": med.instructions
            }, timeout=5)
        except Exception as e:
            print(f"[AI_BRAIN] Failed to send med: {e}")
