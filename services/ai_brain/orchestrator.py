from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import httpx
import os
import json
import logging
import sys
from sqlmodel import select

# Set up logging
logger = logging.getLogger('Orchestrator')

# Import models lazily via helper to avoid import-order circular issues during tests
from .db import get_session, init_db

def _get_model(name: str):
    try:
        import importlib
        mod = importlib.import_module('ai_brain.models')
        return getattr(mod, name, None)
    except Exception:
        return None

# Import Plugin Manager
try:
    from .plugin_manager import PluginManager
    # In container, plugins are in /app/ai_brain/plugins
    # Locally, they are in /home/kilo/Desktop/Kilo_Ai_microservice/plugins
    PLUGIN_DIR = os.environ.get('PLUGIN_DIR', os.path.join(os.path.dirname(__file__), 'plugins'))
    plugin_manager = PluginManager(plugin_dir=PLUGIN_DIR)
    logger.info(f'Plugin Manager initialized with dir: {PLUGIN_DIR}')
except Exception as e:
    logger.error(f'Failed to initialize Plugin Manager: {e}')
    plugin_manager = None

router = APIRouter()
REMINDER_URL = os.environ.get('REMINDER_URL', 'http://reminder:9002')

# --- DTOs ---

class ChatRequest(BaseModel):
    user_id: Optional[str] = 'default_user'
    message: str
    context: Optional[List[str]] = None

class ChatResponse(BaseModel):
    response: str
    plugin_used: Optional[str] = None
    status: str = 'ok'

class SedentaryCreate(BaseModel):
    user_id: str

class CamReportDTO(BaseModel):
    user_id: Optional[str] = None
    face_id: Optional[str] = None
    posture: str
    timestamp: Optional[datetime] = None
    location_hash: Optional[str] = None
    image_id: Optional[str] = None
    pose_match: Optional[bool] = None
    mse: Optional[float] = None

class MedUploadDTO(BaseModel):
    user_id: str
    med_name: str
    dosage: Optional[str] = None
    schedule_text: Optional[str] = None

class MedConfirmDTO(BaseModel):
    user_id: str
    med_id: int
    taken: bool

class UserSettingsDTO(BaseModel):
    opt_out_camera: Optional[bool] = None
    opt_out_habits: Optional[bool] = None

# --- Utility Functions ---

async def create_reminder(text: str, when_dt: datetime):
    payload = {'text': text, 'when': when_dt.isoformat()}
    try:
        cb = os.environ.get('AI_BRAIN_CALLBACK_URL')
        if cb:
            payload['_callback'] = cb.rstrip('/') + '/reminder/callback'
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(f'{REMINDER_URL}/', json=payload)
            r.raise_for_status()
            return r.json().get('id')
    except Exception as e:
        logger.error(f'Failed to create reminder: {e}')
        return None

def get_user_settings(session, user_id: str):
    UserSettings = _get_model('UserSettings')
    if not UserSettings: return None
    stmt = select(UserSettings).where(UserSettings.user_id == user_id)
    return session.exec(stmt).first()

# --- Endpoints ---

@router.on_event('startup')
async def startup_event():
    if plugin_manager:
        logger.info('Loading plugins on startup...')
        await plugin_manager.load_plugins()
        plugin_manager.start_all()

@router.post('/chat/plugin', response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """
    Unified Chat Endpoint that uses the Plugin Manager to route requests.
    """
    if not plugin_manager:
        return ChatResponse(response='Plugin Manager is not available.', status='error')

    # Try to find a matching plugin
    plugin = plugin_manager.get_action(req.message)
    if plugin:
        try:
            # Most plugins in Bastion return a dict with 'content' -> 'message'
            result = plugin.run(req.message)
            if isinstance(result, dict):
                response_text = result.get('content', {}).get('message', str(result))
            else:
                response_text = str(result)
            
            return ChatResponse(
                response=response_text,
                plugin_used=plugin.get_name()
            )
        except Exception as e:
            logger.error(f'Error executing plugin {plugin.get_name()}: {e}')
            return ChatResponse(response=f'Error executing plugin: {e}', status='error')

    # Fallback: Simple echo or could be connected to LLM/Ollama
    return ChatResponse(response=f'I heard you say: "{req.message}". (No plugin matched)')

@router.post('/reminder/callback')
async def reminder_callback(request: Request):
    body = await request.body()
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    
    rid = payload.get('id') or payload.get('reminder_id')
    text = payload.get('text')
    when = payload.get('when')
    
    with get_session() as session:
        SentReminder = _get_model('SentReminder')
        if SentReminder:
            sr = SentReminder(reminder_id=rid, reminder_text=text, when=when)
            session.add(sr)
            session.commit()
    return {'status': 'ok'}

@router.post('/reminder/sedentary')
async def create_sedentary(s: SedentaryCreate):
    with get_session() as session:
        us = get_user_settings(session, s.user_id)
        if us and us.opt_out_camera:
            return {'status': 'opted_out'}
        
        now = datetime.utcnow()
        SedentaryState = _get_model('SedentaryState')
        if not SedentaryState:
            raise HTTPException(status_code=500, detail='Model SedentaryState not available')
            
        state = SedentaryState(user_id=s.user_id, start_time=now, last_movement=now, active=True)
        session.add(state)
        session.commit()
        session.refresh(state)
        
        reminder_ids = []
        for hrs in (1, 2, 3):
            when = now + timedelta(hours=hrs)
            rid = await create_reminder(f'Sedentary reminder: been sitting for {hrs} hour(s)', when)
            if rid:
                reminder_ids.append(rid)
        
        state.reminder_ids_json = json.dumps(reminder_ids)
        session.add(state)
        session.commit()
        return {'status': 'ok', 'state_id': state.id, 'reminder_ids': reminder_ids}

@router.post('/ingest/cam')
async def ingest_cam(report: CamReportDTO):
    with get_session() as session:
        uid = report.user_id or 'unknown'
        us = get_user_settings(session, uid)
        if us and us.opt_out_camera:
            return {'status': 'opted_out'}
            
        ts = report.timestamp or datetime.utcnow()
        CamReport = _get_model('CamReport')
        if CamReport:
            cr = CamReport(user_id=uid, face_id=report.face_id, posture=report.posture, timestamp=ts)
            session.add(cr)
            session.commit()
            
        return {'status': 'ok', 'feedback': f'Detected posture: {report.posture}'}

@router.post('/meds/upload')
async def meds_upload(payload: MedUploadDTO):
    with get_session() as session:
        times = []
        if payload.schedule_text:
            import re
            times = re.findall(r'(\d{1,2}:\d{2})', payload.schedule_text)
            
        MedRecord = _get_model('MedRecord')
        if not MedRecord:
            raise HTTPException(status_code=500, detail='Model MedRecord not available')
            
        med = MedRecord(user_id=payload.user_id, name=payload.med_name, dosage=payload.dosage, schedule=times)
        session.add(med)
        session.commit()
        session.refresh(med)
        
        return {'status': 'ok', 'med_id': med.med_id}

@router.get('/user/{user_id}/settings')
def get_settings(user_id: str):
    with get_session() as session:
        s = get_user_settings(session, user_id)
        if not s:
            return {'user_id': user_id, 'opt_out_camera': False, 'opt_out_habits': False}
        return {'user_id': user_id, 'opt_out_camera': s.opt_out_camera, 'opt_out_habits': s.opt_out_habits}
