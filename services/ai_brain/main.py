from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Form, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import httpx
import re
import datetime
import threading
from collections import defaultdict
import base64
from io import BytesIO
import subprocess
from shutil import which
import json
import hashlib
import asyncio
from kilo_tools import KILO_FUNCTION_DECLARATIONS, execute_tool_call
from datetime import datetime, timedelta
# Google Gemini API (google-genai SDK)
try:
    from google import genai as genai_client
    _GEMINI_AVAILABLE = True
except ImportError:
    _GEMINI_AVAILABLE = False
    genai_client = None

# OpenAI removed - Kilo runs 100% locally with Ollama
try:
    from gtts import gTTS
except Exception:
    gTTS = None
try:
    from tenacity import retry, stop_after_attempt, wait_exponential
except Exception:
    # simple fallback retry decorator
    def retry(*args, **kwargs):
        def _decorator(f):
            return f
        return _decorator
    def stop_after_attempt(n):
        return None
    def wait_exponential(*args, **kwargs):
        return None
from starlette.concurrency import run_in_threadpool
import uuid
import logging
logger = logging.getLogger(__name__)

# Reminder Service Integration
REMINDER_SERVICE_URL = "http://kilo-reminder:9002"
FINANCIAL_SERVICE_URL = "http://kilo-financial:9005"

async def detect_financial_question(message: str) -> dict:
    """
    Detect if the user is asking about spending/finances.
    Returns dict with query type and parameters.
    """
    message_lower = message.lower()

    # Spending queries
    if any(word in message_lower for word in ['spend', 'spent', 'expense', 'cost', 'paid']):
        # Category detection
        categories = {
            'gas': ['gas', 'fuel', 'gasoline'],
            'food': ['food', 'restaurant', 'dining', 'grocery', 'groceries'],
            'shopping': ['shopping', 'amazon', 'store'],
            'utilities': ['utility', 'utilities', 'electric', 'water', 'internet'],
            'atm': ['atm', 'cash', 'withdrawal'],
            'entertainment': ['entertainment', 'netflix', 'roku', 'streaming'],
        }

        detected_category = None
        for cat, keywords in categories.items():
            if any(kw in message_lower for kw in keywords):
                detected_category = cat
                break

        # Time period detection
        time_period = 'month'  # default
        if 'week' in message_lower or 'weekly' in message_lower:
            time_period = 'week'
        elif 'today' in message_lower:
            time_period = 'today'
        elif 'year' in message_lower:
            time_period = 'year'

        return {
            'type': 'spending_query',
            'category': detected_category,
            'time_period': time_period
        }

    # Balance/total queries
    if any(word in message_lower for word in ['balance', 'total', 'how much money']):
        return {'type': 'balance_query'}

    # Recent transactions
    if any(word in message_lower for word in ['recent', 'latest', 'last']):
        return {'type': 'recent_transactions', 'limit': 5}

    return None

async def get_transactions(category: str = None, limit: int = None) -> List[Dict]:
    """Fetch transactions from financial service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{FINANCIAL_SERVICE_URL}/transactions"
            params = {}
            if limit:
                params['limit'] = limit

            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                transactions = resp.json()

                # Filter by category if specified
                if category and isinstance(transactions, list):
                    cat_lower = category.lower()
                    transactions = [
                        t for t in transactions
                        if cat_lower in t.get('category', '').lower() or
                           cat_lower in t.get('description', '').lower()
                    ]

                return transactions
            return []
    except Exception as e:
        logger.error(f"Failed to get transactions: {e}")
        return []

async def calculate_spending(transactions: List[Dict], time_period: str = 'month'):
    """Calculate total spending for a time period. Returns (total, count)."""
    from datetime import datetime, timedelta

    now = datetime.now()
    cutoff_date = None

    if time_period == 'today':
        cutoff_date = now.replace(hour=0, minute=0, second=0)
    elif time_period == 'week':
        cutoff_date = now - timedelta(days=7)
    elif time_period == 'month':
        cutoff_date = now - timedelta(days=30)
    elif time_period == 'year':
        cutoff_date = now - timedelta(days=365)

    total = 0.0
    count = 0
    filtered_txs = []
    for t in transactions:
        # Only count expenses (negative amounts)
        amount = t.get('amount', 0)
        if amount < 0:
            # Check date if we have a cutoff
            if cutoff_date:
                try:
                    # Try to parse date (formats: YYYY-MM-DD or MM/DD/YYYY)
                    t_date_str = t.get('date', '')
                    if '-' in t_date_str:
                        t_date = datetime.strptime(t_date_str, "%Y-%m-%d")
                    else:
                        t_date = datetime.strptime(t_date_str, "%m/%d/%Y")
                    if t_date >= cutoff_date:
                        total += abs(amount)
                        count += 1
                        filtered_txs.append(t)
                except:
                    # If date parsing fails, include it anyway
                    total += abs(amount)
                    count += 1
                    filtered_txs.append(t)
            else:
                total += abs(amount)
                count += 1
                filtered_txs.append(t)

    return total, count, filtered_txs

async def handle_financial_chat(message: str) -> dict:
    """
    Handle finance-related questions.
    Returns dict with 'handled' boolean and 'response' string.
    """
    query = await detect_financial_question(message)

    if not query:
        return {"handled": False}

    try:
        if query['type'] == 'spending_query':
            category = query.get('category')
            time_period = query.get('time_period', 'month')

            # Get transactions
            transactions = await get_transactions(category=category)

            if not transactions:
                return {
                    "handled": True,
                    "response": f"Found nothing for {category or 'that'} in the records. Maybe you haven't spent anything there yet, Kyle."
                }

            # Calculate spending
            total, tx_count, filtered_txs = await calculate_spending(transactions, time_period)

            cat_str = f"on {category}" if category else ""
            period_str = f"this {time_period}"

            response = f"You burned through **${total:.2f}** {cat_str} {period_str}. Classic. "

            # Add some context if there are transactions
            if len(transactions) > 0:
                response += f"That's {tx_count} transactions. "

                # Show biggest expense
                expenses = filtered_txs
                if expenses:
                    biggest = max(expenses, key=lambda x: abs(x.get('amount', 0)))
                    response += f"Biggest was ${abs(biggest['amount']):.2f} at {biggest.get('description', 'unknown')}. ⚓"

            return {"handled": True, "response": response}

        elif query['type'] == 'recent_transactions':
            transactions = await get_transactions(limit=query.get('limit', 5))

            if not transactions:
                return {
                    "handled": True,
                    "response": "No recent transactions. Either you're being responsible or the data's empty."
                }

            response = "**Recent Transactions:**\n"
            for t in transactions[:5]:
                amount = t.get('amount', 0)
                desc = t.get('description', 'Unknown')[:40]
                date = t.get('date', '')
                emoji = "💸" if amount < 0 else "💰"
                response += f"\n{emoji} ${abs(amount):.2f} - {desc} ({date})"

            return {"handled": True, "response": response}

        elif query['type'] == 'balance_query':
            transactions = await get_transactions()
            total = sum(t.get('amount', 0) for t in transactions)

            return {
                "handled": True,
                "response": f"Across {len(transactions)} transactions, net is **${total:.2f}**. That's what came in minus what flew out. "
            }

    except Exception as e:
        logger.error(f"Financial chat error: {e}")
        return {
            "handled": True,
            "response": f"Hit an error checking finances: {str(e)}"
        }

    return {"handled": False}


async def parse_reminder_request(message: str, observations: list = None) -> dict:
    """
    Parse natural language reminder requests with context awareness.
    Examples:
    - "remind me to call mom at 3pm"
    - "can you create a reminder to pay it?" (with bill in observations)
    - "set a reminder for march 1st"
    - "remind me to pay the electric bill when I get paid"
    """
    import re
    from datetime import datetime as dt, timedelta

    message_lower = message.lower()

    # Expanded trigger phrases - be more flexible
    trigger_phrases = [
        'remind me', 'reminder', 'set a reminder', 'create a reminder',
        'make a reminder', 'add a reminder', 'set reminder', 'create reminder',
        'can you remind', 'could you remind', 'please remind'
    ]

    if not any(phrase in message_lower for phrase in trigger_phrases):
        return None

    # Extract the task - more flexible patterns
    task = None
    task_patterns = [
        r'(?:remind me to|reminder for|reminder to|create a reminder to|make a reminder to|set a reminder to)\s+(.+?)(?:\s+(?:at|on|when|tomorrow|today)|\s*$)',
        r'(?:remind|reminder)\s+(?:me\s+)?(?:about|for)?\s+(.+?)(?:\s+(?:at|on|when|tomorrow|today)|\s*$)',
        r'(?:create|make|set)\s+(?:a\s+)?reminder\s+(?:to\s+)?(.+?)(?:\s+(?:at|on|when|tomorrow|today)|\s*$)',
    ]

    for pattern in task_patterns:
        task_match = re.search(pattern, message_lower)
        if task_match:
            task = task_match.group(1).strip()
            break

    if not task:
        # Last resort - try to extract anything after "reminder"
        if 'reminder' in message_lower:
            parts = message_lower.split('reminder', 1)
            if len(parts) > 1:
                task = parts[1].strip()
                # Clean up common prefixes
                task = re.sub(r'^(to|for|about)\s+', '', task)

    # Handle pronouns like "it" or "that" by checking observations
    if task and observations:
        pronouns = ['it', 'that', 'this', 'them', 'those']
        task_words = task.split()
        if any(pronoun in task_words for pronoun in pronouns):
            # Look for bills/amounts in recent observations
            for obs in observations[-3:]:  # Check last 3 observations
                obs_text = obs.get('content', '').lower()
                # Check if observation mentions a bill or payment
                if any(keyword in obs_text for keyword in ['bill', 'payment', 'invoice', 'electric', 'internet', 'due']):
                    # Extract bill description from observation
                    bill_keywords = re.findall(r'(electric|internet|phone|water|gas|rent|mortgage|credit card|utility|prentiss county)', obs_text)
                    if bill_keywords:
                        task = f"pay {bill_keywords[0]} bill"
                        break

    if not task:
        return {"error": "Couldn't understand what to remind you about"}

    # Extract time
    time_patterns = [
        (r'at\s+(\d{1,2}):(\d{2})\s*(am|pm)?', 'time'),
        (r'at\s+(\d{1,2})\s*(am|pm)', 'hour'),
        (r'tomorrow', 'tomorrow'),
        (r'today', 'today'),
    ]

    when = None
    for pattern, ptype in time_patterns:
        match = re.search(pattern, message_lower)
        if match:
            if ptype == 'time':
                hour = int(match.group(1))
                minute = int(match.group(2))
                ampm = match.group(3)
                if ampm == 'pm' and hour < 12:
                    hour += 12
                elif ampm == 'am' and hour == 12:
                    hour = 0
                when = f"{hour:02d}:{minute:02d}"
            elif ptype == 'hour':
                hour = int(match.group(1))
                ampm = match.group(2)
                if ampm == 'pm' and hour < 12:
                    hour += 12
                elif ampm == 'am' and hour == 12:
                    hour = 0
                when = f"{hour:02d}:00"
            elif ptype == 'tomorrow':
                when = (dt.now() + timedelta(days=1)).strftime("%Y-%m-%dT09:00:00")
            elif ptype == 'today':
                when = dt.now().strftime("%Y-%m-%dT%H:%M:00")
            break

    # Enhanced date parsing for "march 1st", "first of march", "when I get paid", etc.
    date_patterns = [
        (r'(?:on\s+)?(?:the\s+)?first(?:\s+of\s+the\s+month|\s+of\s+(january|february|march|april|may|june|july|august|september|october|november|december))?', 'first'),
        (r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(?:st|nd|rd|th)?', 'month_day'),
        (r'(\d{1,2})(?:st|nd|rd|th)?\s+of\s+(january|february|march|april|may|june|july|august|september|october|november|december)', 'day_of_month'),
        (r'when\s+i\s+get\s+paid', 'payday'),
    ]

    target_date = None
    for pattern, ptype in date_patterns:
        match = re.search(pattern, message_lower)
        if match:
            month_names = {
                'january': 1, 'february': 2, 'march': 3, 'april': 4,
                'may': 5, 'june': 6, 'july': 7, 'august': 8,
                'september': 9, 'october': 10, 'november': 11, 'december': 12
            }

            if ptype == 'first':
                # "first of march" or just "first" (assume next month)
                if match.lastindex and match.group(1):
                    month_name = match.group(1)
                    month = month_names[month_name]
                else:
                    # Just "first" - assume next month
                    month = dt.now().month + 1
                    if month > 12:
                        month = 1

                year = dt.now().year
                if month < dt.now().month or (month == dt.now().month and 1 < dt.now().day):
                    year += 1
                target_date = dt(year, month, 1)

            elif ptype == 'month_day':
                month_name = match.group(1)
                day = int(match.group(2))
                month = month_names[month_name]
                year = dt.now().year
                if month < dt.now().month or (month == dt.now().month and day < dt.now().day):
                    year += 1
                target_date = dt(year, month, day)

            elif ptype == 'day_of_month':
                day = int(match.group(1))
                month_name = match.group(2)
                month = month_names[month_name]
                year = dt.now().year
                if month < dt.now().month or (month == dt.now().month and day < dt.now().day):
                    year += 1
                target_date = dt(year, month, day)

            elif ptype == 'payday':
                # Assume payday is 1st of next month (user mentioned "first of march")
                month = dt.now().month + 1
                if month > 12:
                    month = 1
                    year = dt.now().year + 1
                else:
                    year = dt.now().year
                target_date = dt(year, month, 1)

            break

    if not when and not target_date:
        # If no time/date specified, ask for clarification but be helpful
        return {
            "error": "When should I remind you? Try adding 'at 3pm' or 'on March 1st'",
            "suggested_task": task  # Include what we understood so far
        }

    # Build final reminder time
    if target_date:
        if when and ':' in when:
            hour, minute = map(int, when.split(':'))
            target_date = target_date.replace(hour=hour, minute=minute)
        else:
            # Default to 9am if no time specified
            target_date = target_date.replace(hour=9, minute=0)
        when = target_date.strftime('%Y-%m-%d %H:%M')
    elif when and not target_date:
        # Time only, no date - assume today or tomorrow based on time
        if 'tomorrow' not in message_lower:
            now = dt.now()
            if ':' in when:
                hour, minute = map(int, when.split(':'))
            else:
                hour = int(when.split(':')[0])
                minute = 0
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            when = target.strftime('%Y-%m-%d %H:%M')

    return {
        "text": task,
        "when": when,
        "recurrence": "once"
    }


async def create_reminder(reminder_data: dict) -> dict:
    """Create a reminder via the reminder service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{REMINDER_SERVICE_URL}/",
                json=reminder_data
            )
            if resp.status_code in [200, 201]:
                return {"success": True, "data": resp.json()}
            else:
                return {"success": False, "error": f"Failed to create reminder: {resp.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def get_reminders() -> list:
    """Get all reminders from the reminder service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{REMINDER_SERVICE_URL}/")
            if resp.status_code == 200:
                return resp.json()
            return []
    except Exception as e:
        logger.error(f"Failed to get reminders: {e}")
        return []

async def get_upcoming_reminders(limit=5) -> list:
    """Get upcoming unsent reminders."""
    try:
        all_reminders = await get_reminders()
        # Filter unsent and sort by time
        upcoming = [r for r in all_reminders if not r.get('sent', False)]
        return upcoming[:limit]
    except Exception as e:
        logger.error(f"Failed to get upcoming reminders: {e}")
        return []

async def get_medications() -> List[Dict]:
    """Fetch medications from gateway"""
    try:
        gateway_url = os.getenv('GATEWAY_URL', 'http://kilo-gateway:8000')
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{gateway_url}/meds/")
            if resp.status_code == 200:
                data = resp.json()
                return data.get('meds', [])
            return []
    except Exception as e:
        logging.error(f"Error fetching medications: {e}")
        return []

async def get_habits() -> List[Dict]:
    """Fetch habits from gateway"""
    try:
        gateway_url = os.getenv('GATEWAY_URL', 'http://kilo-gateway:8000')
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{gateway_url}/habits/")
            if resp.status_code == 200:
                data = resp.json()
                return data.get('habits', [])
            return []
    except Exception as e:
        logging.error(f"Error fetching habits: {e}")
        return []

# Add to the chat endpoint
async def handle_reminder_in_chat(message: str) -> dict:
    """
    Handle reminder-related chat messages.
    Returns dict with 'handled' boolean and 'response' string.
    """
    message_lower = message.lower()

    # List reminders
    if any(phrase in message_lower for phrase in ['what are my reminders', 'show reminders', 'list reminders', 'upcoming reminders']):
        reminders = await get_upcoming_reminders()
        if not reminders:
            return {
                "handled": True,
                "response": "No reminders set. Want me to track something for you?"
            }

        response = "**Your Reminders:**\n"
        for r in reminders:
            when = r.get('when', 'unknown')
            text = r.get('text', 'No description')
            response += f"\n💡 **{text}** - {when}"

        return {"handled": True, "response": response}

    # Create reminder
    if any(phrase in message_lower for phrase in ['remind me', 'set a reminder', 'reminder']):
        parsed = await parse_reminder_request(message, desktop_observations)

        if parsed and 'error' not in parsed:
            result = await create_reminder(parsed)
            if result.get('success'):
                return {
                    "handled": True,
                    "response": f"Got it. I'll remind you to **{parsed['text']}** at **{parsed['when']}**. Don't thank me, just actually do it. "
                }
            else:
                return {
                    "handled": True,
                    "response": f"Something went wrong creating that reminder: {result.get('error')}. Try again."
                }
        elif parsed and 'error' in parsed:
            return {
                "handled": True,
                "response": f"Couldn't parse that. Try something like 'remind me to take meds at 8pm'"
            }

    return {"handled": False}

from fastapi.responses import FileResponse
import pathlib
import os
# include orchestration routes
import importlib.util
import pathlib

try:
    # Preferred when running as a package
    from .orchestrator import router as orchestration_router
except Exception as e:
    logger.debug("Failed to import .orchestrator: %s", e)
    # Fallback for running as a module or from Docker where package context may be missing
    try:
        from orchestrator import router as orchestration_router
    except Exception as e2:
        logger.debug("Failed to import local orchestrator module: %s", e2)
        # Try a couple of absolute import locations
        try:
            import importlib
            mod = importlib.import_module("ai_brain.orchestrator")
            orchestration_router = getattr(mod, "router", None)
        except Exception as e3:
            logger.debug("Failed to import ai_brain.orchestrator: %s", e3)
            try:
                mod = importlib.import_module("microservice.ai_brain.orchestrator")
                orchestration_router = getattr(mod, "router", None)
            except Exception:
                # Try loading the module directly from file path as a last resort
                try:
                    base = pathlib.Path(__file__).parent
                    candidate = base / "orchestrator.py"
                    if not candidate.exists():
                        candidate = base / "ai_brain" / "orchestrator.py"
                    spec = importlib.util.spec_from_file_location("ai_brain.orchestrator", str(candidate))
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    orchestration_router = getattr(mod, "router", None)
                    # register to sys.modules so subsequent imports (and patches) can find it
                    try:
                        import sys
                        sys.modules["ai_brain.orchestrator"] = mod
                        try:
                            import ai_brain as _ai_pkg
                            setattr(_ai_pkg, "orchestrator", mod)
                        except Exception:
                            pass
                    except Exception:
                        pass
                except Exception:
                    orchestration_router = None

async def handle_medication_chat(message: str) -> dict:
    """
    Handle medication-related questions.
    Returns dict with 'handled' boolean and 'response' string.
    """
    message_lower = message.lower()

    # Check if this is actually about medications
    med_keywords = ['medication', 'medicine', 'pill', 'prescription', 'dose', 'dosage', 'vitamin', 'supplement', 'drug']
    if not any(kw in message_lower for kw in med_keywords):
        return {"handled": False}

    try:
        meds = await get_medications()

        if not meds:
            return {
                "handled": True,
                "response": "No medications in the system. Either you're super healthy or forgot to add them. 💊"
            }

        # Build response based on query type
        if any(word in message_lower for word in ['how many', 'count', 'list all']):
            med_names = [m.get('name', 'Unknown') for m in meds]
            response = f"You're juggling {len(meds)} medications: {', '.join(med_names)}. "
            response += "Don't tell me you're forgetting to take them again... 😈"
            return {"handled": True, "response": response}

        elif any(word in message_lower for word in ['schedule', 'when', 'time']):
            schedule_info = []
            for med in meds:
                name = med.get('name', 'Unknown')
                times = med.get('times') or med.get('schedule', 'not set')
                schedule_info.append(f"{name}: {times}")

            response = "Here's your medication schedule:\n" + "\n".join(schedule_info)
            return {"handled": True, "response": response}

        else:
            # General medication info
            med_names = [m.get('name', 'Unknown') for m in meds[:5]]
            response = f"You have {len(meds)} medications: {', '.join(med_names)}"
            if len(meds) > 5:
                response += f" and {len(meds)-5} more"
            response += ". Need more details? Ask about schedule or specific meds. 💊"
            return {"handled": True, "response": response}

    except Exception as e:
        logging.error(f"Error in handle_medication_chat: {e}")
        return {"handled": False}

async def handle_habit_chat(message: str) -> dict:
    """
    Handle habit-related questions.
    Returns dict with 'handled' boolean and 'response' string.
    """
    message_lower = message.lower()

    # Check if this is actually about habits
    habit_keywords = ['habit', 'routine', 'streak', 'tracking', 'completion', 'progress']
    if not any(kw in message_lower for kw in habit_keywords):
        return {"handled": False}

    try:
        habits = await get_habits()

        if not habits:
            return {
                "handled": True,
                "response": "No habits tracked yet. Time to start building some good ones... or bad ones, I don't judge. 📜"
            }

        # Filter active habits
        active_habits = [h for h in habits if h.get('active', True)]

        # Build response based on query type
        if any(word in message_lower for word in ['how many', 'count', 'list all']):
            habit_names = [h.get('name', 'Unknown') for h in active_habits]
            response = f"You're tracking {len(active_habits)} habits: {', '.join(habit_names)}. "
            response += "Look at all these rules you made for yourself! 📜"
            return {"handled": True, "response": response}

        elif any(word in message_lower for word in ['today', 'completed', 'done']):
            # Check today's completions
            daily_habits = [h for h in active_habits if h.get('frequency') == 'daily']
            response = f"You have {len(daily_habits)} daily habits to complete. "
            response += "Better get started before I start nagging you! 😈"
            return {"handled": True, "response": response}

        else:
            # General habit info
            habit_names = [h.get('name', 'Unknown') for h in active_habits[:5]]
            response = f"Tracking {len(active_habits)} habits: {', '.join(habit_names)}"
            if len(active_habits) > 5:
                response += f" and {len(active_habits)-5} more"
            response += ". Keep it up! 💪"
            return {"handled": True, "response": response}

    except Exception as e:
        logging.error(f"Error in handle_habit_chat: {e}")
        return {"handled": False}

# Support pluggable STT/TTS via environment variables (defaults to 'none' -> dummy)
STT_PROVIDER = os.environ.get("STT_PROVIDER", "none")
TTS_PROVIDER = os.environ.get("TTS_PROVIDER", "none")

# Compatibility: convert Pydantic models to dicts supporting v1 (.dict()) and v2 (.model_dump())
def _to_dict(m):
    """Return a serializable dict for a pydantic model or object."""
    try:
        # Pydantic v2
        return m.model_dump()
    except Exception:
        try:
            return m.dict()
        except Exception:
            try:
                return dict(m)
            except Exception:
                return getattr(m, "__dict__", {})


from contextlib import asynccontextmanager
try:
    from .db import get_session
except Exception:
    # Try absolute package import (when running tests or module executed differently)
    from ai_brain.db import get_session

try:
    from .utils.network import require_network_or_raise
except Exception:
    from ai_brain.utils.network import require_network_or_raise


def _get_memory_model():
    """Lazily import the shared Memory model at call time.

    Try a few import locations so the function works both when the ai_brain
    package is executed in isolation and when tests import the project with
    the repository root on sys.path (where the module is available as
    `shared.models`).
    """
    candidates = [
        "models",
        "shared.models",
        "ai_brain.models",
    ]
    for cand in candidates:
        try:
            module = __import__(cand, fromlist=["Memory"])
            Memory = getattr(module, "Memory", None)
            if Memory is not None:
                return Memory
        except Exception:
            continue
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Unified Plugins...")
    # startup
    try:
        try:
            from .db import init_db
            init_db()
        except Exception:
            pass

        # Initialize Phase 3 & 4 components
        try:
            from .async_processing import async_pipeline
            from .data_partitioning import data_partitioner
            from .knowledge_graph import knowledge_graph

            # Start async processing pipeline
            async_pipeline.start()

            # Initialize data partitioner
            # (data_partitioner is already initialized as global instance)

            # Load existing knowledge graph if available
            kg_file = "/tmp/ai_brain_knowledge_graph.json"
            if os.path.exists(kg_file):
                knowledge_graph.load_graph(kg_file)

            logger.info("Phase 3 & 4 components initialized successfully")

        except Exception as e:
            logger.warning(f"Failed to initialize Phase 3 & 4 components: {e}")

        # Ensure orchestrator routes are mounted on startup (handles import-order quirks
        # when pytest or other runners import modules out-of-order).
        try:
            import importlib
            mod = importlib.import_module('ai_brain.orchestrator')
            orchestration_router = getattr(mod, 'router', None)
            if orchestration_router is not None:
                # include router on the app instance that will be passed into lifespan
                try:
                    app.include_router(orchestration_router)
                    logger.info("Mounted orchestrator router on startup")
                except Exception as e:
                    logger.warning(f"Failed to include orchestrator router on startup: {e}")
        except Exception as e:
            logger.debug(f"Orchestrator not importable on startup: {e}")

    except Exception:
        pass
    yield
    # shutdown
    try:
        # Save knowledge graph on shutdown
        from .knowledge_graph import knowledge_graph
        kg_file = "/tmp/ai_brain_knowledge_graph.json"
        knowledge_graph.save_graph(kg_file)

        # Stop async processing
        from .async_processing import async_pipeline
        async_pipeline.stop()

        logger.info("Phase 3 & 4 components shut down successfully")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Prometheus metrics: create only if not already present (safe for repeated imports)
if 'REQUEST_COUNT' not in globals():
    REQUEST_COUNT = Counter('ai_brain_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
else:
    # reuse existing
    REQUEST_COUNT = globals()['REQUEST_COUNT']

if 'REQUEST_LATENCY' not in globals():
    REQUEST_LATENCY = Histogram('ai_brain_request_latency_seconds', 'Request latency', ['method', 'endpoint'])
else:
    REQUEST_LATENCY = globals()['REQUEST_LATENCY']

if 'IN_PROGRESS' not in globals():
    IN_PROGRESS = Gauge('ai_brain_inprogress_requests', 'In-progress requests')
else:
    IN_PROGRESS = globals()['IN_PROGRESS']

app = FastAPI(title="AI Brain Service", lifespan=lifespan)

# Middleware to collect metrics
@app.middleware("http")
async def metrics_middleware(request, call_next):
    method = request.method
    # Use path without query for metric labels
    endpoint = request.url.path
    IN_PROGRESS.inc()
    start = request.scope.get('time_start', None)
    with REQUEST_LATENCY.labels(method=method, endpoint=endpoint).time():
        try:
            response = await call_next(request)
            status = str(response.status_code)
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
            return response
        except Exception as e:
            # On error, increment error counter and re-raise
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status='500').inc()
            raise
        finally:
            IN_PROGRESS.dec()

# Expose Prometheus metrics endpoint (restricted to admin access)
@app.get('/metrics')
async def metrics(request: Request):
    """Return Prometheus metrics only if a valid admin token is provided.

    Accepts either header `X-Admin-Token: <token>` or `Authorization: Bearer <token>`.
    The token is compared against METRICS_TOKEN env var or LIBRARY_ADMIN_KEY as a fallback.
    """
    # Token sources
    token = request.headers.get('x-admin-token') or request.headers.get('authorization')
    if token and token.lower().startswith('bearer '):
        token = token.split(' ', 1)[1]

    METRICS_TOKEN = os.environ.get('METRICS_TOKEN') or os.environ.get('LIBRARY_ADMIN_KEY')

    if not METRICS_TOKEN:
        # If no token configured, restrict to localhost
        client_host = request.client.host if request.client else None
        if client_host not in ('127.0.0.1', '::1', 'localhost'):
            raise HTTPException(status_code=403, detail='Metrics access restricted to localhost or admin token')
    else:
        if token != METRICS_TOKEN:
            raise HTTPException(status_code=401, detail='Unauthorized')

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Mount orchestration routes if available
import logging
if 'orchestration_router' in globals() and orchestration_router is not None:
    try:
        app.include_router(orchestration_router)
    except Exception as e:
        logging.exception("Failed to include orchestration router: %s", e)
else:
    # Try importing the orchestrator module directly and include its router if present.
    try:
        import importlib
        mod = importlib.import_module("ai_brain.orchestrator")
        orchestration_router = getattr(mod, "router", None)
        if orchestration_router is not None:
            app.include_router(orchestration_router)
    except Exception as e:
        logging.info("orchestration router not available: %s", e)

# Last-ditch attempt: if earlier imports failed due to import-order issues,
# try again now. This ensures tests that load modules in an unusual order still
# get the orchestrator endpoints mounted when possible.
try:
    import importlib
    mod = importlib.import_module("ai_brain.orchestrator")
    orchestration_router = getattr(mod, "router", None)
    if orchestration_router is not None:
        app.include_router(orchestration_router)
except Exception as e:
    logging.debug("late import of orchestrator failed: %s", e)

# Health check endpoints
@app.get("/status")
@app.get("/health")
def status():
    return {"status": "ok"}

# In-memory user model (replace with DB in production)
user_state = {
    "habits": [],
    "reminders": [],
    "meds": [],
    "finance": [],
    "pantry": {},
    "cam_observations": [],
    "activity_log": [],
}

# --- Models ---
class ChatRequest(BaseModel):
    user: Optional[str] = None
    message: str
    context: Optional[List[str]] = None

class ChatResponse(BaseModel):
    response: str
    context: Optional[List[str]] = None

class MedData(BaseModel):
    name: str
    schedule: str
    dosage: str
    quantity: int
    prescriber: str
    instructions: str

class FinanceData(BaseModel):
    amount: float
    description: str
    date: str

class ReceiptData(BaseModel):
    text: str  # raw OCR text from receipt

class CamObservation(BaseModel):
    timestamp: str
    posture: str  # e.g., 'sitting', 'standing', 'lying'
    pose_match: Optional[bool] = None
    mse: Optional[float] = None
    location: Optional[str] = None

class Reminder(BaseModel):
    text: str
    when: str
    escalated: bool = False

class HabitData(BaseModel):
    name: str
    frequency: str

class HabitCompletionData(BaseModel):
    habit: str
    completion_date: str
    count: int
    frequency: str

class BudgetData(BaseModel):
    category: str
    monthly_limit: float
    created_at: str

class GoalData(BaseModel):
    name: str
    target_amount: float
    current_amount: float
    deadline: Optional[str] = None
    message: str

# --- Library of Truth Integration ---
LIBRARY_URL = "http://library_of_truth:9006"  # Adjust port if needed

async def search_library(query: str):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{LIBRARY_URL}/search", params={"q": query, "limit": 3})
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
    return []


def synthesize_answer(question: str, passages: list) -> str:
    if not passages:
        return f"Hey Kyle! I'm Kilo, your AI assistant. I searched my memories and library but didn't find specific information about '{question}'. You can:\n• Use /remember <text> to store new information\n• Use /recall <query> to search your memories\n• Ask me about your medications, habits, or finances\n• Upload prescription or receipt images\n\nWhat can I help you with?"
    # Compose a personalized answer from the found passages
    summary = []
    for p in passages:
        summary.append(f"From {p['book']} (p.{p['page']}): {p['text']}")
    # In a real system, use LLM or advanced summarization here
    return f"Here's what I found for '{question}':\n" + '\n'.join(summary)


async def _stt_from_uploadfile(file: UploadFile) -> str:
    """
    Speech-to-text placeholder. Will be replaced by local Whisper in voice microservice.
    For now, returns a placeholder message.
    """
    # Read bytes (kept for interface compatibility)
    data = await file.read()

    # TODO: Integrate with local Whisper microservice
    # For now, return placeholder
    return "(voice recognized - Whisper integration coming soon)"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def _tts_sync(text: str) -> bytes:
    if TTS_PROVIDER == "gtts":
        # gTTS uses Google's online TTS service. Gate this behind ALLOW_NETWORK.
        require_network_or_raise("TTS provider 'gtts' requires network access or set ALLOW_NETWORK=true")
        bio = BytesIO()
        tts = gTTS(text=text, lang='en')
        tts.write_to_fp(bio)
        return bio.getvalue()
    # fallback: synthesize a short WAV tone containing the text as simple beeps
    try:
        import wave, struct, math
        duration = 1.0
        framerate = 22050
        amplitude = 16000
        freq = 440.0
        nframes = int(duration * framerate)
        bio = BytesIO()
        with wave.open(bio, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(framerate)
            for i in range(nframes):
                t = float(i) / framerate
                value = int(amplitude * math.sin(2.0 * math.pi * freq * t))
                data = struct.pack('<h', value)
                wf.writeframesraw(data)
        return bio.getvalue()
    except Exception:
        return b"AUDIO-DATA"


async def _tts_to_base64(text: str) -> str:
    try:
        data = await run_in_threadpool(_tts_sync, text)
        return base64.b64encode(data).decode()
    except Exception:
        return base64.b64encode(b"AUDIO-DATA").decode()


# JSON chat endpoint with RAG (Retrieval Augmented Generation)
@app.post("/chat", response_model=ChatResponse)
async def chat_json(req: ChatRequest):
    """
    Chat endpoint with memory-aware RAG.

    Searches relevant memories and augments the LLM prompt with context.
    Stores the conversation for future retrieval.
    """
    # Check for special memory commands
    message = req.message.strip()

    # /remember command - explicitly store a memory
    if message.startswith("/remember "):
        memory_text = message[10:].strip()
        try:
            Memory = _get_memory_model()
            if Memory:
                s = get_session()
                emb = _embed_text(memory_text)
                mem = Memory(
                    source="user",
                    modality="text",
                    text_blob=memory_text,
                    embedding_json=json.dumps(emb),
                    privacy_label="private"
                )
                s.add(mem)
                s.commit()
                s.refresh(mem)
                return ChatResponse(
                    response=f"✓ Memory stored (ID: {mem.id}). I'll remember: '{memory_text}'",
                    context=req.context
                )
        except Exception as e:
            return ChatResponse(response=f"Error storing memory: {e}", context=req.context)

    # /recall command - search memories
    elif message.startswith("/recall "):
        query = message[8:].strip()
        try:
            from .memory_search import search_memories_by_text
            s = get_session()
            results = search_memories_by_text(query, s, limit=5)
            if results:
                response_parts = [f"Found {len(results)} relevant memories:\n"]
                for i, mem in enumerate(results, 1):
                    response_parts.append(
                        f"{i}. [{mem['source']}] {mem['text'][:100]}... (similarity: {mem['similarity']:.2f})"
                    )
                return ChatResponse(response="\n".join(response_parts), context=req.context)
            else:
                return ChatResponse(response=f"No memories found for '{query}'", context=req.context)
        except Exception as e:
            return ChatResponse(response=f"Error searching memories: {e}", context=req.context)

    # /forget command - delete a memory
    elif message.startswith("/forget "):
        try:
            memory_id = int(message[8:].strip())
            from .memory_search import delete_memory
            s = get_session()
            if delete_memory(memory_id, s):
                return ChatResponse(response=f"✓ Memory {memory_id} deleted", context=req.context)
            else:
                return ChatResponse(response=f"Memory {memory_id} not found", context=req.context)
        except ValueError:
            return ChatResponse(response="Usage: /forget <memory_id>", context=req.context)
        except Exception as e:
            return ChatResponse(response=f"Error deleting memory: {e}", context=req.context)

    # Normal chat with RAG + PROACTIVE INTELLIGENCE
    try:
        from .rag import generate_rag_response, store_conversation_memory
        s = get_session()

        # 🧠 PROACTIVE INTELLIGENCE LAYER
        # Gather contextual awareness from all microservices
        proactive_context = None
        augmented_query = req.message

        try:
            # Import proactive intelligence module
            import sys
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "proactive_intelligence",
                "/app/ai_brain/proactive_intelligence.py"
            )
            if spec and spec.loader:
                pi_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(pi_module)

                # Gather proactive context if appropriate
                if pi_module.should_be_proactive(req.message):
                    proactive_context = await pi_module.gather_proactive_context()
                    context_prompt = pi_module.build_context_prompt(proactive_context)

                    # Augment user query with contextual awareness
                    augmented_query = f"{context_prompt}\n\n---\nUSER MESSAGE: {req.message}"

                    logger.info(f"Proactive context gathered: meds={proactive_context['medications']['pending']}, habits={proactive_context['habits']['not_logged']}")
        except Exception as e:
            logger.warning(f"Proactive intelligence failed (continuing without): {e}")
            # Continue without proactive context if it fails

        # Generate RAG response with contextual awareness
        rag_result = generate_rag_response(
            user_query=augmented_query,
            session=s,
            max_context_memories=5
        )

        response_text = rag_result["response"]

        # Store this conversation turn as a memory
        try:
            store_conversation_memory(
                user_query=req.message,
                ai_response=response_text,
                session=s
            )
        except Exception as e:
            logging.warning(f"Failed to store conversation memory: {e}")

        return ChatResponse(response=response_text, context=req.context)

    except Exception as e:
        logging.error(f"RAG error: {e}")
        # Fallback to simple library search
        passages = await search_library(req.message)
        answer = synthesize_answer(req.message, passages)
        return ChatResponse(response=answer, context=req.context)

# Lightweight quick chat endpoint (no RAG) for low-latency responses
@app.post("/chat/quick", response_model=ChatResponse)
async def chat_quick(req: ChatRequest):
    """
    Quick chat endpoint that avoids the RAG pipeline for lower latency.
    Uses library search and simple synthesis as a fast fallback.
    """
    try:
        logging.info(f"[CHAT/LLM] START - Message: {req.message[:50]}")
        # Check if it's a reminder request first
        logging.info("[CHAT/LLM] Checking reminders...")
        reminder_result = await handle_reminder_in_chat(req.message)
        if reminder_result.get('handled'):
            return ChatResponse(response=reminder_result['response'], context=req.context)

        # Check if it's a financial question
        logging.info("[CHAT/LLM] Checking financial...")
        financial_result = await handle_financial_chat(req.message)
        if financial_result.get('handled'):
            return ChatResponse(response=financial_result['response'], context=req.context)

        # Quick path: search library and synthesize a short answer
        passages = await search_library(req.message)
        answer = synthesize_answer(req.message, passages)
        return ChatResponse(response=answer, context=req.context)
    except Exception as e:
        logging.error(f"chat_quick error: {e}")
        # As a last resort echo the message back
        return ChatResponse(response=f"I heard: {req.message}", context=req.context)

# Form/multipart chat endpoint for voice or form-based input
@app.post("/chat/voice")
async def chat_voice(
    user: Optional[str] = Form(None),
    message: Optional[str] = Form(None),
    audio: Optional[UploadFile] = None
):
    import pathlib
    # If audio is provided, simulate speech-to-text (STT)
    if audio is not None:
        # Run pluggable STT
        stt_text = await _stt_from_uploadfile(audio)
        input_text = stt_text
    elif message:
        input_text = message
    else:
        raise HTTPException(status_code=400, detail="No input provided.")

    # Simulate AI response
    ai_response = f"You said: {input_text}"

    # TTS mode: inline (default) or background
    tts_mode = "inline"
    tts_url = None
    # If the client provided tts_mode as form field, capture it
    # (FastAPI will ignore unknown form fields in signature; read raw form if needed)
    # For now, default to inline behavior for compatibility with integration tests.

    if tts_mode == "inline":
        dummy_audio = await _tts_to_base64(ai_response)
        return JSONResponse({
            "text": ai_response,
            "tts_base64": dummy_audio,
            "tts_url": tts_url,
            "input_text": input_text
        })
    else:
        # background mode: generate file and return a tts_url immediately
        fname = f"tts-{uuid.uuid4().hex}.mp3"
        path = pathlib.Path("/data") / fname

        def _bg_write_tts(text, out_path):
            data = _tts_sync(text)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(data)

        # schedule background write
        from fastapi import BackgroundTasks
        bg = BackgroundTasks()
        bg.add_task(_bg_write_tts, ai_response, path)
        # mount background tasks to run after response
        response = JSONResponse({"text": ai_response, "tts_base64": None, "tts_url": f"/tts/{fname}", "input_text": input_text})
        response.background = bg
        return response
# --- Ingest endpoints and other APIs ---
@app.post("/ingest/meds")
def ingest_meds(med: MedData, background_tasks: BackgroundTasks):
    user_state["meds"].append(_to_dict(med))
    # Proactively set a reminder
    reminder = Reminder(text=f"Take {med.name} as scheduled.", when=med.schedule)
    user_state["reminders"].append(_to_dict(reminder))
    background_tasks.add_task(_log_activity, f"Ingested med: {med.name}")
    # Persist a Memory for this med ingestion
    try:
        Memory = _get_memory_model()
        if Memory is not None:
            s = get_session()
            txt = f"med:{med.name} schedule:{med.schedule} dosage:{med.dosage}"
            emb = _embed_text(txt)
            mem = Memory(source="meds", modality="text", text_blob=txt, metadata_json=json.dumps(_to_dict(med)), embedding_json=json.dumps(emb))
            s.add(mem)
            s.commit()
            s.refresh(mem)
    except Exception:
        pass
    return {"status": "ok", "reminder": reminder}

@app.post("/ingest/finance")
def ingest_finance(fin: FinanceData, background_tasks: BackgroundTasks):
    user_state["finance"].append(_to_dict(fin))
    background_tasks.add_task(_log_activity, f"Finance event: {fin.description}")
    # Persist a Memory for this finance event
    try:
        Memory = _get_memory_model()
        if Memory is not None:
            s = get_session()
            txt = f"finance:{fin.description} amount:{fin.amount} date:{fin.date}"
            emb = _embed_text(txt)
            mem = Memory(source="finance", modality="text", text_blob=txt, metadata_json=json.dumps(_to_dict(fin)), embedding_json=json.dumps(emb))
            s.add(mem)
            s.commit()
            s.refresh(mem)
    except Exception:
        pass
    return {"status": "ok"}

@app.post("/ingest/receipt")
def ingest_receipt(receipt: ReceiptData, background_tasks: BackgroundTasks):
    items = _parse_receipt(receipt.text)
    for item in items:
        user_state["pantry"][item] = user_state["pantry"].get(item, 0) + 1
    background_tasks.add_task(_log_activity, f"Receipt processed: {items}")
    # Persist a Memory for the whole receipt and per-item
    try:
        Memory = _get_memory_model()
        if Memory is not None:
            s = get_session()
            txt = receipt.text
            emb = _embed_text(txt)
            mem = Memory(source="receipt", modality="text", text_blob=txt, metadata_json=json.dumps({"items": items}), embedding_json=json.dumps(emb))
            s.add(mem)
            s.commit()
            s.refresh(mem)
            # also create short memories per item
            for it in items:
                it_txt = f"purchased:{it}"
                emb2 = _embed_text(it_txt)
                mem2 = Memory(source="receipt", modality="text", text_blob=it_txt, metadata_json=json.dumps({}), embedding_json=json.dumps(emb2))
                s.add(mem2)
            s.commit()
    except Exception:
        pass
    return {"status": "ok", "items": items}

@app.post("/ingest/cam")
def ingest_cam(obs: CamObservation, background_tasks: BackgroundTasks):
    user_state["cam_observations"].append(_to_dict(obs))
    background_tasks.add_task(_log_activity, f"Cam observed: {obs.posture} at {obs.timestamp} match={obs.pose_match}")
    feedback = None
    if obs.pose_match is not None:
        feedback = "Great job! Your pose matches the reference." if obs.pose_match else "Try to adjust your posture to match the reference."
    elif obs.posture in ("sitting", "standing", "lying"):
        feedback = f"Detected posture: {obs.posture}."
    # Persist a Memory for this cam observation
    try:
        Memory = _get_memory_model()
        if Memory is not None:
            s = get_session()
            txt = f"posture:{obs.posture} match:{obs.pose_match}"
            emb = _embed_text(txt)
            mem = Memory(source="cam", modality="text", text_blob=txt, metadata_json=json.dumps(_to_dict(obs)), embedding_json=json.dumps(emb))
            s.add(mem)
            s.commit()
            s.refresh(mem)
    except Exception:
        pass
    return {"status": "ok", "feedback": feedback}


@app.post("/ingest/habit")
def ingest_habit(habit: HabitData, background_tasks: BackgroundTasks):
    user_state["habits"].append(_to_dict(habit))
    background_tasks.add_task(_log_activity, f"New habit tracked: {habit.name}")
    # Persist a Memory for this habit
    try:
        Memory = _get_memory_model()
        if Memory is not None:
            s = get_session()
            txt = f"habit:{habit.name} frequency:{habit.frequency}"
            emb = _embed_text(txt)
            mem = Memory(source="habits", modality="text", text_blob=txt, metadata_json=json.dumps(_to_dict(habit)), embedding_json=json.dumps(emb))
            s.add(mem)
            s.commit()
            s.refresh(mem)
    except Exception:
        pass
    return {"status": "ok"}

@app.post("/ingest/habit_completion")
def ingest_habit_completion(completion: HabitCompletionData, background_tasks: BackgroundTasks):
    background_tasks.add_task(_log_activity, f"Habit completed: {completion.habit} on {completion.completion_date}")
    # Persist a Memory for this completion
    try:
        Memory = _get_memory_model()
        if Memory is not None:
            s = get_session()
            txt = f"completed_habit:{completion.habit} date:{completion.completion_date} count:{completion.count}"
            emb = _embed_text(txt)
            mem = Memory(source="habits", modality="text", text_blob=txt, metadata_json=json.dumps(_to_dict(completion)), embedding_json=json.dumps(emb))
            s.add(mem)
            s.commit()
            s.refresh(mem)
    except Exception:
        pass
    return {"status": "ok"}

@app.post("/ingest/budget")
def ingest_budget(budget: BudgetData, background_tasks: BackgroundTasks):
    background_tasks.add_task(_log_activity, f"Budget set: {budget.category} - ${budget.monthly_limit}")
    # Persist a Memory for this budget
    try:
        Memory = _get_memory_model()
        if Memory is not None:
            s = get_session()
            txt = f"budget:{budget.category} limit:${budget.monthly_limit}/month"
            emb = _embed_text(txt)
            mem = Memory(source="finance", modality="text", text_blob=txt, metadata_json=json.dumps(_to_dict(budget)), embedding_json=json.dumps(emb))
            s.add(mem)
            s.commit()
            s.refresh(mem)
    except Exception:
        pass
    return {"status": "ok"}

@app.post("/ingest/goal")
def ingest_goal(goal: GoalData, background_tasks: BackgroundTasks):
    background_tasks.add_task(_log_activity, f"Financial goal: {goal.message}")
    # Persist a Memory for this goal
    try:
        Memory = _get_memory_model()
        if Memory is not None:
            s = get_session()
            txt = goal.message
            emb = _embed_text(txt)
            mem = Memory(source="finance", modality="text", text_blob=txt, metadata_json=json.dumps(_to_dict(goal)), embedding_json=json.dumps(emb))
            s.add(mem)
            s.commit()
            s.refresh(mem)
    except Exception:
        pass
    return {"status": "ok"}

@app.post('/ingest/cam_activity')
def ingest_cam_activity(payload: Dict[str, Any], background_tasks: BackgroundTasks = None):
    """Receive activity observations from cam and return simple recipe suggestions when cooking is detected."""
    ts = payload.get('timestamp')
    activities = payload.get('activities', [])
    user_state['activity_log'].append({'timestamp': ts, 'activities': activities})
    suggestions = []
    if 'cooking' in activities:
        # build simple suggestions from pantry items
        pantry = user_state.get('pantry', {})
        items = list(pantry.keys())
        if items:
            # naive combinations
            for i in range(min(3, len(items))):
                a = items[i]
                b = items[(i+1) % len(items)] if len(items) > 1 else None
                if b:
                    suggestions.append(f"Use {a} with {b}")
                else:
                    suggestions.append(f"Cook something with {a}")
        else:
            suggestions.append('No pantry items found; try adding groceries')
    # optional background logging
    if background_tasks is not None:
        background_tasks.add_task(_log_activity, f"Cam activity: {activities}")
    # Persist a Memory for this cam activity bundle
    try:
        Memory = _get_memory_model()
        if Memory is not None:
            s = get_session()
            txt = f"cam_activity:{activities}"
            emb = _embed_text(txt)
            mem = Memory(source="cam", modality="text", text_blob=txt, metadata_json=json.dumps({'activities': activities}), embedding_json=json.dumps(emb))
            s.add(mem)
            s.commit()
            s.refresh(mem)
    except Exception:
        pass
    return {'status': 'ok', 'suggestions': suggestions}


@app.post('/ingest/activity_session')
def ingest_activity_session(payload: Dict[str, Any], background_tasks: BackgroundTasks = None):
    """
    Receive completed activity sessions from cam with duration tracking.
    
    Creates a memory entry and optionally a habit entry for long activities.
    Used for learning daily patterns: how long user watches TV, sleeps, works, etc.
    """
    activity = payload.get('activity', 'unknown')
    duration = payload.get('duration_seconds', 0)
    timestamp = payload.get('timestamp')
    location = payload.get('location', 'unknown')
    camera_id = payload.get('camera_id', 'unknown')
    
    # Log to activity history
    user_state['activity_log'].append({
        'timestamp': timestamp,
        'activity': activity,
        'duration_seconds': duration,
        'location': location,
        'completed': True
    })
    
    # Create memory entry
    try:
        Memory = _get_memory_model()
        if Memory is not None:
            s = get_session()
            duration_min = duration / 60
            txt = f"Activity: {activity} for {duration_min:.1f} minutes in {location} at {timestamp}"
            emb = _embed_text(txt)
            metadata = {
                'activity': activity,
                'duration_seconds': duration,
                'duration_minutes': duration_min,
                'location': location,
                'camera_id': camera_id,
                'completed': True
            }
            mem = Memory(
                source="cam_activity_tracker",
                modality="text",
                text_blob=txt,
                metadata_json=json.dumps(metadata),
                embedding_json=json.dumps(emb)
            )
            s.add(mem)
            s.commit()
            s.refresh(mem)
    except Exception as e:
        print(f"Failed to create memory for activity session: {e}")
    
    # For significant activities (>5 min), create/update a habit entry
    if duration > 300:  # 5 minutes
        try:
            habits_url = os.getenv('HABITS_URL', 'http://kilo-habits:9000')
            habit_data = {
                'name': f"{activity.replace('_', ' ').title()}",
                'category': 'daily_activity',
                'notes': f"Auto-tracked from camera in {location}",
                'duration_minutes': int(duration / 60)
            }
            requests.post(f"{habits_url}/record-activity", json=habit_data, timeout=2)
        except Exception as e:
            print(f"Failed to create habit entry: {e}")
    
    return {'status': 'ok', 'duration_logged': duration}


@app.post("/reminder/ack")
def acknowledge_reminder(reminder: Reminder):
    for r in user_state["reminders"]:
        if r["text"] == reminder.text and r["when"] == reminder.when:
            r["escalated"] = False
    return {"status": "acknowledged"}

# --- Voice Stubs ---
@app.post("/voice/activate")
def voice_activate(audio: UploadFile = File(...)):
    # Save uploaded activation audio and attempt a lightweight transcription
    try:
        data = audio.file.read()
        fname = f"/tmp/voice-activate-{uuid.uuid4().hex}-{getattr(audio, 'filename', 'audio') }"
        with open(fname, 'wb') as f:
            f.write(data)
        # attempt to decode as text
        try:
            txt = data.decode('utf-8')
        except Exception:
            txt = None
        return {"status": "saved", "path": fname, "transcription": txt}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/voice/speak")
def voice_speak(text: str):
    # Generate TTS audio (base64) and return a temporary path and the base64 payload
    try:
        data = _tts_sync(text)
        fname = f"/tmp/tts-{uuid.uuid4().hex}.wav"
        with open(fname, 'wb') as f:
            f.write(data)
        b64 = base64.b64encode(data).decode()
        return {"status": "ok", "text": text, "tts_path": fname, "tts_base64": b64}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# --- Analytics and Feedback Endpoints ---
@app.get("/analytics/habits")
def habit_analytics():
    completions = defaultdict(list)
    for h in user_state.get("habits", []):
        name = h.get("name")
        for c in h.get("completions", []):
            completions[name].append(c["completed_at"])
    analytics = {}
    for name, times in completions.items():
        times_sorted = sorted(times)
        streak = _calculate_streak(times_sorted)
        analytics[name] = {
            "total_completions": len(times),
            "current_streak": streak,
            "last_completed": times_sorted[-1] if times_sorted else None
        }
    return analytics

@app.get("/feedback/habits")
def habit_feedback():
    analytics = habit_analytics()
    feedback = []
    for name, stats in analytics.items():
        if stats["current_streak"] >= 5:
            feedback.append(f"Great job keeping up with '{name}'! Your streak is {stats['current_streak']} days.")
        elif stats["current_streak"] == 0:
            feedback.append(f"You haven't completed '{name}' recently. Try to get back on track!")
        else:
            feedback.append(f"You're doing well with '{name}', current streak: {stats['current_streak']}.")
    return {"feedback": feedback}


@app.get("/stats/dashboard")
async def get_dashboard_stats():
    """
    Aggregate stats from all services for the dashboard.
    Returns counts and metrics for display in the main dashboard.
    """
    stats = {
        "totalMemories": 0,
        "activeHabits": 0,
        "upcomingReminders": 0,
        "monthlySpending": 0,
        "insightsGenerated": 0
    }

    # Get memory count from local storage
    try:
        with get_session() as session:
            from sqlmodel import select, func
            from .models import Memory
            stats["totalMemories"] = session.exec(select(func.count(Memory.id))).one()
    except Exception:
        pass

    # Fetch from other services
    async with httpx.AsyncClient(timeout=2.0) as client:
        # Habits
        try:
            resp = await client.get("http://docker_habits_1:9003/")
            if resp.status_code == 200:
                habits = resp.json()
                stats["activeHabits"] = len([h for h in habits if h.get("active", True)])
        except Exception:
            pass

        # Reminders
        try:
            resp = await client.get("http://docker_reminder_1:9002/")
            if resp.status_code == 200:
                reminders = resp.json()
                stats["upcomingReminders"] = len([r for r in reminders if not r.get("sent", False)])
        except Exception:
            pass

        # Financial
        try:
            resp = await client.get("http://docker_financial_1:9005/summary")
            if resp.status_code == 200:
                summary = resp.json()
                stats["monthlySpending"] = abs(summary.get("total_expenses", 0))
        except Exception:
            pass

    # Insights generated is based on memories + conversations
    stats["insightsGenerated"] = stats["totalMemories"]

    return stats


@app.get("/memory/visualization")
async def get_memory_visualization():
    """
    Return memory visualization data for charts and graphs.
    Includes timeline data and category breakdown.
    """
    viz_data = {
        "timeline": [],
        "categories": []
    }

    try:
        with get_session() as session:
            from sqlmodel import select
            from .models import Memory
            from collections import defaultdict

            memories = session.exec(select(Memory)).all()

            # Group by date for timeline
            by_date = defaultdict(int)
            by_category = defaultdict(int)

            for memory in memories:
                # Extract date from timestamp
                try:
                    date_str = memory.timestamp[:10] if hasattr(memory, 'timestamp') else datetime.datetime.utcnow().isoformat()[:10]
                    by_date[date_str] += 1
                except Exception:
                    pass

                # Category from metadata or default
                category = "general"
                if hasattr(memory, 'metadata') and memory.metadata:
                    if isinstance(memory.metadata, dict):
                        category = memory.metadata.get("category", "general")
                by_category[category] += 1

            # Convert to list format for frontend
            viz_data["timeline"] = [
                {"date": date, "count": count}
                for date, count in sorted(by_date.items())
            ][-30:]  # Last 30 days

            viz_data["categories"] = [
                {"name": cat, "count": count}
                for cat, count in sorted(by_category.items(), key=lambda x: x[1], reverse=True)
            ][:10]  # Top 10 categories

    except Exception as e:
        # Return empty data on error
        logger.error(f"Failed to generate memory visualization: {e}")

    return viz_data


# --- Helpers ---
def _parse_receipt(text: str) -> List[str]:
    lines = text.splitlines()
    items = []
    for line in lines:
        m = re.match(r"([A-Za-z ]+)\s+\d+\.\d{2}", line)
        if m:
            items.append(m.group(1).strip())
    return items


def _log_activity(event: str):
    user_state["activity_log"].append({"event": event, "timestamp": datetime.datetime.utcnow().isoformat()})


def _embed_text(text: str, dim: int = 384):
    """
    Generate semantic embedding for text using sentence-transformers.
    Falls back to hash-based embedding if model unavailable.

    This function is used throughout the codebase for backward compatibility.
    For new code, prefer using ai_brain.embeddings.embed_text directly.
    """
    try:
        from .embeddings import embed_text
        return embed_text(text)
    except Exception:
        # Fallback to simple hash-based embedding
        if not text:
            return [0.0] * dim
        h = hashlib.sha256(text.encode('utf-8')).hexdigest()
        vals = []
        chunk_size = max(2, len(h) // dim)
        for i in range(dim):
            chunk = h[i * chunk_size:(i + 1) * chunk_size]
            if not chunk:
                vals.append(0.0)
                continue
            intval = int(chunk, 16)
            maxval = float(int('f' * len(chunk), 16))
            vals.append(intval / maxval)
        return vals[:dim]


def _calculate_streak(times_sorted):
    if not times_sorted:
        return 0
    streak = 1
    last_date = datetime.datetime.fromisoformat(times_sorted[-1]).date()
    for t in reversed(times_sorted[:-1]):
        d = datetime.datetime.fromisoformat(t).date()
        if (last_date - d).days == 1:
            streak += 1
            last_date = d
        else:
            break
    return streak


@app.get("/tts/{fname}")
def serve_tts(fname: str):
    path = pathlib.Path("/data") / fname
    if not path.exists():
        raise HTTPException(status_code=404, detail="TTS not ready")
    return FileResponse(str(path), media_type="audio/mpeg")


@app.post("/analyze/prescription")
async def analyze_prescription(image: UploadFile = File(...)):
    """
    Analyze prescription image using OCR to extract medication information.
    Supports single image uploads. Text from curved bottles can be captured.
    Returns structured medication data that can be added to the medication schedule.
    """
    try:
        # Import OCR libraries
        try:
            import pytesseract
            from PIL import Image
        except ImportError as e:
            raise HTTPException(status_code=500, detail=f"OCR libraries not available: {e}")

        # Read and process the image
        image_bytes = await image.read()
        pil_image = Image.open(BytesIO(image_bytes))
        ocr_text = pytesseract.image_to_string(pil_image)

        if not ocr_text.strip():
            return {
                "success": False,
                "error": "No text detected in image. Please ensure the prescription is clearly visible and well-lit.",
                "ocr_text": "",
                "images_processed": 1
            }

        # Use RAG/LLM to parse the prescription text
        try:
            from .rag import generate_rag_response
            s = get_session()

            # Craft a prompt to extract medication information
            prompt = f"""Analyze this prescription text and extract medication information in JSON format.

Prescription text:
{ocr_text}

Please extract the following fields if available:
- medication_name: The name of the medication
- dosage: The dosage amount and units (e.g., "500mg", "10ml")
- schedule: How often to take it (e.g., "twice daily", "every 8 hours", "once at bedtime")
- prescriber: Doctor's name if visible
- instructions: Any special instructions (e.g., "take with food", "avoid alcohol")

Return ONLY a JSON object with these fields. If a field is not found, use null."""

            rag_result = generate_rag_response(
                user_query=prompt,
                session=s,
                max_context_memories=0  # Don't need memory context for prescription parsing
            )

            response_text = rag_result["response"]

            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
            if json_match:
                parsed_data = json.loads(json_match.group())
            else:
                # Fallback: return raw text if JSON parsing fails
                parsed_data = {
                    "medication_name": None,
                    "dosage": None,
                    "schedule": None,
                    "prescriber": None,
                    "instructions": response_text
                }

            return {
                "success": True,
                "ocr_text": ocr_text,
                "parsed_data": parsed_data,
                "ai_interpretation": response_text,
                "images_processed": 1
            }

        except Exception as e:
            # Fallback: return OCR text without AI parsing
            return {
                "success": True,
                "ocr_text": ocr_text,
                "parsed_data": None,
                "error": f"AI parsing failed: {e}. Raw OCR text available.",
                "images_processed": 1
            }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {e}")


@app.post("/analyze/financial-document")
async def analyze_financial_document(request: Dict[str, Any]):
    """
    Verify and enhance parsed financial transactions using AI.
    Takes parsed transactions and raw text, returns verification and suggestions.
    """
    try:
        transactions = request.get("transactions", [])
        raw_text = request.get("raw_text", "")
        task = request.get("task", "verify")
        
        if not transactions:
            return {
                "success": False,
                "error": "No transactions provided",
                "confidence": 0
            }
        
        # Use RAG/LLM to verify and enhance transactions
        try:
            from .rag import generate_rag_response
            s = get_session()
            
            # Craft a prompt for transaction verification
            trans_summary = "\n".join([
                f"- {t.get('date')}: {t.get('description')} ${t.get('amount')}"
                for t in transactions[:20]  # Limit to first 20 for prompt size
            ])
            
            prompt = f"""Analyze these parsed financial transactions and verify they look correct.

Parsed {len(transactions)} transactions:
{trans_summary}

Raw document excerpt:
{raw_text[:500]}

Please verify:
1. Do the transactions look reasonable?
2. Are the amounts and descriptions properly extracted?
3. Any obvious errors or missing transactions?
4. Suggested improvements for parsing?

Respond with a JSON object containing:
- confidence: 0-100 score for parsing quality
- verified: true/false if data looks correct  
- suggestions: list of improvement suggestions
- anomalies: list of any suspicious transactions"""
            
            rag_result = generate_rag_response(
                user_query=prompt,
                session=s,
                max_context_memories=0
            )
            
            response_text = rag_result["response"]
            
            # Try to extract JSON
            import re
            json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
            else:
                parsed = {
                    "confidence": 75,
                    "verified": True,
                    "suggestions": [response_text],
                    "anomalies": []
                }
            
            print(f"[AI Brain] Financial verification: {parsed.get('confidence', 0)}% confidence")
            
            return {
                "success": True,
                "transactions_verified": len(transactions),
                **parsed,
                "ai_analysis": response_text
            }
            
        except Exception as e:
            print(f"[AI Brain] Analysis error (non-critical): {e}")
            return {
                "success": True,
                "transactions_verified": len(transactions),
                "confidence": 50,
                "verified": True,
                "suggestions": ["AI analysis unavailable"],
                "error": str(e)
            }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Financial analysis failed: {e}")


# Orchestration router is mounted above if available (guarded)


# ===== PHASE 3 & 4 ADVANCED FEATURES =====

@app.get("/api/v1/scalability/status")
async def get_scalability_status():
    """Get status of scalability features"""
    from .async_processing import async_pipeline, resource_manager
    from .data_partitioning import data_partitioner, partitioned_store

    pipeline_stats = async_pipeline.get_stats()
    partition_stats = data_partitioner.get_partition_stats()

    return {
        "async_processing": {
            "active": async_pipeline.is_running,
            "queue_size": pipeline_stats.get("queue_size", 0),
            "tasks_processed": pipeline_stats.get("tasks_processed", 0),
            "avg_processing_time": pipeline_stats.get("avg_processing_time", 0)
        },
        "data_partitioning": {
            "partitions": len(partition_stats),
            "total_size_mb": sum(p.get("total_size_mb", 0) for p in partition_stats.values()),
            "partition_details": partition_stats
        },
        "resource_management": {
            "current_batch_size": resource_manager.get_optimal_batch_size(),
            "should_throttle": resource_manager.should_throttle()
        }
    }


@app.post("/api/v1/async/embeddings")
async def generate_embeddings_async(texts: List[str], priority: int = 1):
    """Generate embeddings asynchronously"""
    from .async_processing import async_pipeline

    if not texts:
        raise HTTPException(status_code=400, detail="No texts provided")

    task_id = async_pipeline.submit_embedding_task(texts, priority)
    return {"task_id": task_id, "status": "submitted", "estimated_completion": "30-60 seconds"}


@app.post("/api/v1/async/indexing")
async def index_memories_async(memory_ids: List[int], priority: int = 2):
    """Index memories asynchronously"""
    from .async_processing import async_pipeline
    from .db import get_session

    if not memory_ids:
        raise HTTPException(status_code=400, detail="No memory IDs provided")

    # Get memory data
    with get_session() as session:
        Memory = _get_memory_model()
        if not Memory:
            raise HTTPException(status_code=500, detail="Memory model not available")

        memories = session.query(Memory).filter(Memory.id.in_(memory_ids)).all()
        memory_data = [
            {
                "id": m.id,
                "text_blob": m.text_blob,
                "embedding_json": m.embedding_json,
                "metadata_json": m.metadata_json
            }
            for m in memories
        ]

    task_id = async_pipeline.submit_indexing_task(memory_data, priority)
    return {"task_id": task_id, "status": "submitted", "memories_to_index": len(memory_data)}


@app.post("/api/v1/async/consolidation")
async def consolidate_memories_async(partition_key: str = None, days_old: int = 30):
    """Consolidate old memories asynchronously"""
    from .async_processing import async_pipeline

    task_id = async_pipeline.submit_consolidation_task(partition_key or "default", days_old=days_old)
    return {"task_id": task_id, "status": "submitted", "partition": partition_key}


@app.get("/api/v1/predictive/insights")
async def get_predictive_insights():
    """Get predictive insights and recommendations"""
    from .predictive_modeling import predictive_analytics

    # Get recent memory data for training (simplified)
    with get_session() as session:
        Memory = _get_memory_model()
        if Memory:
            recent_memories = session.query(Memory).order_by(Memory.created_at.desc()).limit(100).all()
            memory_data = [
                {
                    "source": m.source,
                    "text_blob": m.text_blob,
                    "metadata_json": m.metadata_json,
                    "created_at": m.created_at.isoformat()
                }
                for m in recent_memories
            ]

            # Train models with recent data
            predictive_analytics.train_all_models(memory_data)

    # Generate insights
    insights = predictive_analytics.get_proactive_insights()

    return {
        "insights": insights,
        "generated_at": datetime.datetime.utcnow(),
        "model_status": "trained" if predictive_analytics.models["habits"].is_trained else "training"
    }


@app.get("/api/v1/knowledge/graph/stats")
async def get_knowledge_graph_stats():
    """Get knowledge graph statistics"""
    from .knowledge_graph import knowledge_graph

    stats = knowledge_graph.get_graph_stats()
    return {
        "graph_stats": stats,
        "entity_types": knowledge_graph.entity_types,
        "relationship_types": knowledge_graph.relationship_types
    }


@app.post("/api/v1/knowledge/graph/build")
async def build_knowledge_graph(limit: int = 1000):
    """Build knowledge graph from memory data"""
    from .knowledge_graph import knowledge_graph

    with get_session() as session:
        Memory = _get_memory_model()
        if not Memory:
            raise HTTPException(status_code=500, detail="Memory model not available")

        memories = session.query(Memory).order_by(Memory.created_at.desc()).limit(limit).all()
        memory_data = [
            {
                "source": m.source,
                "text_blob": m.text_blob,
                "metadata_json": m.metadata_json
            }
            for m in memories
        ]

    entities_added = knowledge_graph.build_from_memories(memory_data)

    return {
        "status": "completed",
        "memories_processed": len(memory_data),
        "entities_added": entities_added,
        "graph_stats": knowledge_graph.get_graph_stats()
    }


@app.get("/api/v1/knowledge/reason/{entity_id}")
async def reason_about_entity(entity_id: str):
    """Get reasoning insights about an entity"""
    from .knowledge_graph import knowledge_reasoner

    impacts = knowledge_reasoner.reason_about_impact(entity_id)
    suggestions = knowledge_reasoner.suggest_actions({"indicators": []})  # Simplified

    return {
        "entity_id": entity_id,
        "impacts": impacts,
        "suggested_actions": suggestions
    }


@app.post("/api/v1/conversation/start")
async def start_conversation(user_id: str, initial_context: Dict[str, Any] = None):
    """Start a new conversation"""
    from .conversation_management import conversation_manager

    conversation_id = str(uuid.uuid4())
    conversation_manager.start_conversation(conversation_id, user_id, initial_context)

    return {
        "conversation_id": conversation_id,
        "status": "started",
        "user_id": user_id
    }


@app.post("/api/v1/conversation/{conversation_id}/turn")
async def add_conversation_turn(conversation_id: str, user_message: str, ai_response: str):
    """Add a turn to a conversation"""
    from .conversation_management import conversation_manager

    success = conversation_manager.add_turn(conversation_id, user_message, ai_response)

    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"status": "added", "conversation_id": conversation_id}


@app.post("/api/v1/conversation/{conversation_id}/goals")
async def set_conversation_goals(conversation_id: str, goals: List[Dict[str, Any]]):
    """Set goals for a conversation"""
    from .conversation_management import conversation_manager

    success = conversation_manager.set_goals(conversation_id, goals)

    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"status": "set", "goals_count": len(goals)}


@app.get("/api/v1/conversation/{conversation_id}/context")
async def get_conversation_context(conversation_id: str):
    """Get conversation context"""
    from .conversation_management import conversation_manager

    context = conversation_manager.get_conversation_context(conversation_id)

    if not context:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return context


@app.get("/api/v1/conversation/{conversation_id}/suggestions")
async def get_conversation_suggestions(conversation_id: str):
    """Get conversation suggestions"""
    from .conversation_management import conversation_manager

    suggestions = conversation_manager.suggest_next_actions(conversation_id)
    return {"suggestions": suggestions}


@app.get("/api/v1/user/{user_id}/insights")
async def get_user_insights(user_id: str):
    """Get user insights from conversation history"""
    from .conversation_management import conversation_manager

    insights = conversation_manager.get_user_insights(user_id)
    return {"user_id": user_id, "insights": insights}


@app.post("/api/v1/goals/suggest")
async def suggest_goals(user_context: Dict[str, Any]):
    """Suggest goals based on user context"""
    from .conversation_management import goal_assistant

    suggestions = goal_assistant.suggest_goals_based_on_context(user_context)
    return {"suggested_goals": suggestions}


@app.get("/api/v1/goals/templates")
async def get_goal_templates():
    """Get available goal templates"""
    from .conversation_management import goal_assistant

    return {"templates": list(goal_assistant.goal_templates.keys())}


# ===== END PHASE 3 & 4 FEATURES =====


# ===== PLUGIN SYSTEM INTEGRATION =====

try:
    from .plugin_manager import PluginManager
    import os
    
    PLUGIN_DIR = os.environ.get('PLUGIN_DIR', os.path.join(os.path.dirname(__file__), 'plugins'))
    plugin_manager = PluginManager(plugin_dir=PLUGIN_DIR)
    PLUGINS_ENABLED = True
    logger.info("Plugin manager initialized")
except Exception as e:
    plugin_manager = None
    PLUGINS_ENABLED = False
    logger.warning(f"Plugin manager initialization failed: {e}")


@app.on_event("startup")
async def load_plugins_on_startup():
    """Load and start all plugins on application startup"""
    if plugin_manager:
        try:
            logger.info("Loading plugins on startup...")
            plugin_manager.load_plugins()
            plugin_manager.start_all()
            plugin_manager.enable_watchdog()
            logger.info(f"Loaded {len(plugin_manager.plugins)} plugins")
        except Exception as e:
            logger.error(f"Error loading plugins: {e}", exc_info=True)
    
    # Start plugin health-check background loop
    import asyncio
    asyncio.ensure_future(_plugin_health_check_loop())
    logger.info("Plugin health-check loop started")


@app.get("/plugins/health")
async def plugins_health_check():
    """Get health status of plugin system"""
    if not PLUGINS_ENABLED:
        return {"status": "disabled", "message": "Plugin system is not enabled"}
    
    try:
        plugins_status = []
        with plugin_manager._plugin_lock:
            for p in plugin_manager.plugins:
                try:
                    name = p.get_name()
                    if hasattr(p, 'health') and callable(p.health):
                        health = p.health()
                    else:
                        health = {"status": "unknown"}
                    
                    plugins_status.append({
                        "name": name,
                        "health": health
                    })
                except Exception as e:
                    plugins_status.append({
                        "name": getattr(p, '_plugin_path', 'unknown'),
                        "health": {"status": "error", "error": str(e)}
                    })
        
        return {
            "status": "enabled",
            "plugin_count": len(plugin_manager.plugins),
            "plugins": plugins_status
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/plugins/list")
async def list_plugins():
    """List all loaded plugins"""
    if not PLUGINS_ENABLED:
        raise HTTPException(status_code=503, detail="Plugin system is not enabled")
    
    try:
        plugins_list = []
        with plugin_manager._plugin_lock:
            for p in plugin_manager.plugins:
                try:
                    plugin_info = {
                        "name": p.get_name(),
                        "description": getattr(p, 'description', 'N/A'),
                        "version": getattr(p, 'version', 'unknown'),
                        "enabled": getattr(p, 'enabled', True)
                    }
                    if hasattr(p, 'manifest') and p.manifest:
                        plugin_info['manifest'] = p.manifest
                    plugins_list.append(plugin_info)
                except Exception as e:
                    logger.error(f"Error getting plugin info: {e}")
        
        return {"plugins": plugins_list, "count": len(plugins_list)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/plugins/{plugin_name}/health")
async def get_plugin_health(plugin_name: str):
    """Get health status of a specific plugin"""
    if not PLUGINS_ENABLED:
        raise HTTPException(status_code=503, detail="Plugin system is not enabled")
    
    plugin = plugin_manager.get_plugin(plugin_name)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin {plugin_name} not found")
    
    try:
        if hasattr(plugin, 'health') and callable(plugin.health):
            health = plugin.health()
        else:
            health = {"status": "unknown", "message": "No health check available"}
        
        return {"plugin": plugin_name, "health": health}
    except Exception as e:
        return {"plugin": plugin_name, "health": {"status": "error", "error": str(e)}}


@app.post("/plugins/{plugin_name}/execute")
async def execute_plugin(plugin_name: str, request: Dict[str, Any]):
    """Execute a specific plugin with given parameters"""
    if not PLUGINS_ENABLED:
        raise HTTPException(status_code=503, detail="Plugin system is not enabled")
    
    plugin = plugin_manager.get_plugin(plugin_name)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin {plugin_name} not found")
    
    try:
        message = request.get('message', '')
        result = plugin.run(message)
        return {"plugin": plugin_name, "result": result}
    except Exception as e:
        logger.error(f"Error executing plugin {plugin_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/plugins/reload")
async def reload_plugins():
    """Reload all plugins"""
    if not PLUGINS_ENABLED:
        raise HTTPException(status_code=503, detail="Plugin system is not enabled")
    
    try:
        plugin_manager.stop_watchdog()
        plugin_manager.plugins.clear()
        plugin_manager.load_plugins()
        plugin_manager.start_all()
        plugin_manager.enable_watchdog()
        return {
            "status": "success",
            "message": f"Reloaded {len(plugin_manager.plugins)} plugins"
        }
    except Exception as e:
        logger.error(f"Error reloading plugins: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== END PLUGIN SYSTEM INTEGRATION =====
# TEST LINE - Mon Feb  9 10:33:16 AM CST 2026


# ===== PLUGIN REGISTRATION SYSTEM =====

# Persistent plugin registry (saved to JSON file, survives restarts)
PLUGIN_REGISTRY_FILE = os.environ.get("PLUGIN_REGISTRY_FILE", "/tmp/plugin_registry.json")
plugin_registry = {}
plugin_registry_lock = threading.RLock()


def _load_plugin_registry():
    """Load plugin registry from JSON file on startup"""
    global plugin_registry
    try:
        if os.path.exists(PLUGIN_REGISTRY_FILE):
            with open(PLUGIN_REGISTRY_FILE, 'r') as f:
                plugin_registry = json.load(f)
            logger.info(f"Loaded {len(plugin_registry)} plugins from {PLUGIN_REGISTRY_FILE}")
        else:
            logger.info("No persisted plugin registry found, starting fresh")
    except Exception as e:
        logger.error(f"Failed to load plugin registry: {e}")
        plugin_registry = {}


def _save_plugin_registry():
    """Save plugin registry to JSON file"""
    try:
        with open(PLUGIN_REGISTRY_FILE, 'w') as f:
            json.dump(plugin_registry, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to save plugin registry: {e}")


# Load persisted registry on module init
_load_plugin_registry()


async def _plugin_health_check_loop():
    """Periodically check registered plugin health and mark unhealthy ones"""
    while True:
        await asyncio.sleep(60)  # Check every 60 seconds
        with plugin_registry_lock:
            plugins_to_check = list(plugin_registry.items())

        for name, info in plugins_to_check:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{info['url']}/health")
                    if resp.status_code < 400:
                        with plugin_registry_lock:
                            if name in plugin_registry:
                                plugin_registry[name]["status"] = "active"
                    else:
                        with plugin_registry_lock:
                            if name in plugin_registry:
                                plugin_registry[name]["status"] = "unhealthy"
                                logger.warning(f"Plugin {name} health check returned {resp.status_code}")
            except Exception:
                with plugin_registry_lock:
                    if name in plugin_registry:
                        plugin_registry[name]["status"] = "unreachable"
                        logger.warning(f"Plugin {name} unreachable at {info['url']}")

        # Inline save for reliability
        try:
            with open(PLUGIN_REGISTRY_FILE, "w") as _f:
                json.dump(plugin_registry, _f, indent=2, default=str)
            logger.info(f"Plugin registry saved to {PLUGIN_REGISTRY_FILE}")
        except Exception as _e:
            logger.error(f"INLINE SAVE FAILED: {_e}")


class PluginRegistration(BaseModel):
    name: str
    url: str
    version: str
    keywords: List[str]
    description: Optional[str] = None


@app.post("/plugins/register")
async def register_plugin(registration: PluginRegistration):
    """Register a remote plugin with the AI Brain"""
    if not PLUGINS_ENABLED:
        raise HTTPException(status_code=503, detail="Plugin system is not enabled")
    
    with plugin_registry_lock:
        # Check if plugin already registered
        if registration.name in plugin_registry:
            logger.info(f"Plugin {registration.name} re-registering, updating info")
        else:
            logger.info(f"New plugin registering: {registration.name}")
        
        # Store plugin info
        plugin_registry[registration.name] = {
            "name": registration.name,
            "url": registration.url,
            "version": registration.version,
            "keywords": registration.keywords,
            "description": registration.description or "",
            "registered_at": datetime.datetime.now().isoformat(),
            "status": "active"
        }
        
        logger.info(f"Plugin {registration.name} registered successfully at {registration.url}")
        # Inline save for reliability
        try:
            with open(PLUGIN_REGISTRY_FILE, "w") as _f:
                json.dump(plugin_registry, _f, indent=2, default=str)
            logger.info(f"Plugin registry saved to {PLUGIN_REGISTRY_FILE}")
        except Exception as _e:
            logger.error(f"INLINE SAVE FAILED: {_e}")
        
        return {
            "status": "success",
            "message": f"Plugin {registration.name} registered successfully",
            "plugin": plugin_registry[registration.name]
        }


@app.get("/plugins/registry")
async def get_plugin_registry():
    """Get all registered plugins"""
    if not PLUGINS_ENABLED:
        raise HTTPException(status_code=503, detail="Plugin system is not enabled")
    
    with plugin_registry_lock:
        return {
            "plugins": list(plugin_registry.values()),
            "count": len(plugin_registry)
        }


@app.post("/plugins/call/{plugin_name}")
async def call_plugin(plugin_name: str, request: Dict[str, Any]):
    """Call a registered plugin by name"""
    if not PLUGINS_ENABLED:
        raise HTTPException(status_code=503, detail="Plugin system is not enabled")
    
    with plugin_registry_lock:
        if plugin_name not in plugin_registry:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_name} not found in registry")
        
        plugin = plugin_registry[plugin_name]
    
    # Call the plugin's execute endpoint
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(
                f"{plugin['url']}/execute",
                json=request
            )
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"Plugin {plugin_name} timed out")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Plugin {plugin_name} error: {str(e)}")


@app.post("/plugins/query")
async def query_plugins(request: Dict[str, Any]):
    """
    Route a query to the appropriate plugin based on keywords.
    Returns result from the first matching plugin.
    """
    if not PLUGINS_ENABLED:
        raise HTTPException(status_code=503, detail="Plugin system is not enabled")
    
    query = request.get("message", "").lower()
    
    if not query:
        raise HTTPException(status_code=400, detail="No message provided")
    
    # Find matching plugins
    matching_plugins = []
    with plugin_registry_lock:
        for plugin_name, plugin_info in plugin_registry.items():
            for keyword in plugin_info["keywords"]:
                if keyword.lower() in query:
                    matching_plugins.append((plugin_name, plugin_info))
                    break
    
    if not matching_plugins:
        return {
            "status": "no_match",
            "message": "No plugin matched the query",
            "query": query,
            "available_plugins": len(plugin_registry)
        }
    
    # Call the first matching plugin
    plugin_name, plugin_info = matching_plugins[0]
    logger.info(f"Query matched plugin: {plugin_name}")
    
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(
                f"{plugin_info['url']}/execute",
                json=request
            )
            response.raise_for_status()
            result = response.json()
            result["matched_plugin"] = plugin_name
            result["matched_by"] = "keyword"
            return result
    except Exception as e:
        logger.error(f"Error calling plugin {plugin_name}: {e}")
        raise HTTPException(status_code=502, detail=f"Plugin {plugin_name} error: {str(e)}")


@app.delete("/plugins/unregister/{plugin_name}")
async def unregister_plugin(plugin_name: str):
    """Unregister a plugin"""
    if not PLUGINS_ENABLED:
        raise HTTPException(status_code=503, detail="Plugin system is not enabled")
    
    with plugin_registry_lock:
        if plugin_name not in plugin_registry:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_name} not found")
        
        del plugin_registry[plugin_name]
        logger.info(f"Plugin {plugin_name} unregistered")
        
        return {"status": "success", "message": f"Plugin {plugin_name} unregistered"}


# ===== END PLUGIN REGISTRATION SYSTEM =====

# ═══════════════════════════════════════════════════════════════════════════
# Desktop Eyes - Observations Endpoint
# ═══════════════════════════════════════════════════════════════════════════
from datetime import datetime, timedelta


# ═══════════════════════════════════════════════════════════════════════════
# GEMINI FUNCTION CALLING - Kilo's tool access to all microservices
# ═══════════════════════════════════════════════════════════════════════════

KILO_TOOLS = [
    {
        "name": "get_spending_summary",
        "description": "Get Kyle's spending summary for current month or by category. Returns total spent, spending by category, and transaction count.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Optional category filter (streaming, food, utilities, entertainment, etc.)"
                }
            }
        }
    },
    {
        "name": "get_budgets",
        "description": "Get Kyle's current budget limits and spending status for each category. Shows budget amount, spent amount, and percentage used.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "create_budget",
        "description": "Create a new budget limit for a spending category.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Budget category (streaming, food, utilities, entertainment, shopping, etc.)"
                },
                "amount": {
                    "type": "number",
                    "description": "Monthly budget limit in dollars"
                }
            },
            "required": ["category", "amount"]
        }
    },
    {
        "name": "get_medications",
        "description": "Get Kyle's current medications, doses, schedules, and adherence tracking.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "log_medication_taken",
        "description": "Log that Kyle took a medication dose.",
        "parameters": {
            "type": "object",
            "properties": {
                "medication_name": {
                    "type": "string",
                    "description": "Name of the medication"
                }
            },
            "required": ["medication_name"]
        }
    },
    {
        "name": "get_habits",
        "description": "Get Kyle's tracked habits, completion rates, and current streaks.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_reminders",
        "description": "Get Kyle's upcoming reminders and notifications.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of reminders to return (default 10)"
                }
            }
        }
    },
    {
        "name": "search_knowledge",
        "description": "Search the Library of Truth for verified facts (medical, health, finance, cooking, psychology).",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for knowledge base"
                }
            },
            "required": ["query"]
        }
    }
]

async def execute_tool(tool_name: str, parameters: dict) -> dict:
    """Execute a tool call and return results"""
    try:
        if tool_name == "get_spending_summary":
            # Query financial pod for spending data
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get transactions from financial service
                resp = await client.get("http://kilo-financial:9005/financial/transactions")
                if resp.status_code != 200:
                    return {"error": "Could not fetch transactions"}

                transactions = resp.json()
                category = parameters.get("category")

                # Calculate summary
                total_spent = 0
                category_totals = {}

                for txn in transactions:
                    if txn.get("amount", 0) < 0:  # Expenses are negative
                        amount = abs(txn["amount"])
                        total_spent += amount
                        cat = txn.get("category", "uncategorized")
                        category_totals[cat] = category_totals.get(cat, 0) + amount

                if category:
                    return {
                        "category": category,
                        "spent": category_totals.get(category, 0),
                        "total_transactions": len([t for t in transactions if t.get("category") == category])
                    }
                else:
                    return {
                        "total_spent": total_spent,
                        "by_category": category_totals,
                        "transaction_count": len(transactions)
                    }

        elif tool_name == "get_budgets":
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get("http://kilo-financial:9005/financial/budgets")
                if resp.status_code != 200:
                    return {"budgets": []}
                return resp.json()

        elif tool_name == "create_budget":
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "http://kilo-financial:9005/financial/budgets",
                    json={
                        "category": parameters["category"],
                        "amount": parameters["amount"],
                        "period": "monthly"
                    }
                )
                if resp.status_code in [200, 201]:
                    return {"success": True, "budget": resp.json()}
                return {"error": "Failed to create budget"}

        elif tool_name == "get_medications":
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get("http://kilo-meds:9000/meds/")
                if resp.status_code != 200:
                    return {"medications": []}
                return resp.json()

        elif tool_name == "log_medication_taken":
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Find the medication ID first
                meds_resp = await client.get("http://kilo-meds:9000/meds/")
                if meds_resp.status_code == 200:
                    meds = meds_resp.json()
                    med = next((m for m in meds if m["name"].lower() == parameters["medication_name"].lower()), None)
                    if med:
                        log_resp = await client.post(
                            f"http://kilo-meds:9000/meds/{med['id']}/take"
                        )
                        if log_resp.status_code in [200, 201]:
                            return {"success": True, "message": f"Logged {parameters['medication_name']}"}
                return {"error": "Medication not found"}

        elif tool_name == "get_habits":
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get("http://kilo-habits:9000/habits/")
                if resp.status_code != 200:
                    return {"habits": []}
                return resp.json()

        elif tool_name == "get_reminders":
            limit = parameters.get("limit", 10)
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"http://kilo-reminder:9002/reminder/notifications/pending?limit={limit}")
                if resp.status_code != 200:
                    return {"reminders": []}
                return resp.json()

        elif tool_name == "search_knowledge":
            query = parameters["query"]
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"http://kilo-library:9006/?search={query}")
                if resp.status_code != 200:
                    return {"results": []}
                return resp.json()

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return {"error": str(e)}

from typing import List, Optional
from pydantic import BaseModel

# Database for persistent observations
import sqlite3
import json

# Database path
DB_PATH = "/app/kilo_data/kilo_guardian.db"

def get_db_connection():
    """Get SQLite connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class DesktopObservation(BaseModel):
    type: str
    content: str
    priority: str = "normal"
    metadata: dict = {}
    timestamp: Optional[str] = None

# In-memory storage for observations (latest 100)
desktop_observations = []
MAX_OBSERVATIONS = 100

async def analyze_observation_with_llm(obs: DesktopObservation):
    """
    Use Ollama LLM to analyze desktop observation and generate insights.
    Kilo understands context and can proactively respond.
    """
    print(f"🧠 [DEBUG] Analyze function called for: {obs.content[:50]}", flush=True)
    logger.info(f"🧠 Analyzing observation: {obs.content[:50]}...")
    try:
        ollama_url = os.getenv("OLLAMA_URL", "http://kilo-ray-serve:8000")
        ollama_model = os.getenv("OLLAMA_MODEL", "phi-3")
        
        # Build context-aware prompt for Kilo
        prompt = f"""You are Kilo - Kyle's mischievous AI assistant with a gremlin personality. You are NOT a dolphin. You are NOT any animal. You are Kilo, an AI system running on Kyle's hardware.

Your personality:
- Sarcastic but helpful
- Observant and proactive
- No corporate politeness - be real with Kyle
- Call out patterns and give actual insights

Kyle's current activity: {obs.content}

Quick observation (under 30 words):
- Anything actionable? Give straight advice
- Just routine? Brief acknowledgment or skip
- Something interesting? Note it

As Kilo, respond:"""

        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 100  # Keep responses concise
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                kilo_response = result.get("response", "").strip()
                print(f"💡 [DEBUG] Ollama response ({len(kilo_response)} chars): {kilo_response[:100]}", flush=True)
                
                # If Kilo has something meaningful to say, push it as a message
                if kilo_response and len(kilo_response) > 10:
                    print(f"🚀 [DEBUG] Sending insight to Socket.IO: {kilo_response[:50]}", flush=True)
                    # Send Kilo's insight to Socket.IO as a chat message
                    socketio_url = "http://kilo-gateway:8000"
                    await client.post(
                        f"{socketio_url}/emit",
                        json={
                            "event": "insight_generated",
                            "data": {
                                "content": kilo_response,
                                "observation": obs.content,
                                "timestamp": datetime.now().isoformat()
                            }
                        }
                    )
                    logger.info(f"Kilo insight: {kilo_response[:50]}...")
                    
    except Exception as e:
        logger.error(f"Failed to analyze observation with LLM: {str(e)}", exc_info=True)



@app.post("/observations")
async def receive_observation(obs: DesktopObservation):
    """Receive desktop observations with smart deduplication and analysis"""
    # Add timestamp if not provided
    if not obs.timestamp:
        obs.timestamp = datetime.now().isoformat()

    # Store in database for persistence
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO observation (type, content, priority, timestamp, source,
                                    primary_context, actionable, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            obs.type,
            obs.content,
            obs.priority,
            obs.timestamp,
            obs.metadata.get("source") if obs.metadata else None,
            obs.metadata.get("primary_context") if obs.metadata else None,
            obs.metadata.get("actionable", False) if obs.metadata else False,
            json.dumps(obs.metadata) if obs.metadata else None,
            datetime.now().isoformat()
        ))

        # Clean old observations (keep last 100)
        cursor.execute("""
            DELETE FROM observation
            WHERE id NOT IN (
                SELECT id FROM observation
                ORDER BY id DESC
                LIMIT 100
            )
        """)

        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to store observation in database: {e}")

    logger.info(f"Desktop observation received: {obs.type} - {obs.content[:50]}")

    # Smart filtering and deduplication
    async def analyze_and_emit():
        try:
            # Check for duplicates in last 5 minutes
            conn = get_db_connection()
            cursor = conn.cursor()
            five_min_ago = (datetime.now() - timedelta(minutes=5)).isoformat()
            cursor.execute("""
                SELECT content FROM observation
                WHERE timestamp > ? AND type = ?
                ORDER BY id DESC LIMIT 5
            """, (five_min_ago, obs.type))
            recent = [row["content"] for row in cursor.fetchall()]
            conn.close()

            # If we've seen very similar content recently, skip
            for prev in recent[1:]:  # Skip first (this one)
                # Simple similarity check - 80% of words match
                prev_words = set(prev.lower().split())
                curr_words = set(obs.content.lower().split())
                if len(prev_words) > 0:
                    similarity = len(prev_words & curr_words) / len(prev_words)
                    if similarity > 0.8:
                        logger.info(f"Skipping duplicate observation (similarity: {similarity:.2f})")
                        return

            # Filter out low-value observations
            low_value_patterns = [
                r'konsole.*file edit view',  # Just showing terminal UI
                r'^\s*$',  # Empty
            ]
            for pattern in low_value_patterns:
                if re.search(pattern, obs.content.lower()):
                    logger.info("Skipping low-value observation")
                    return

            # Only analyze high-priority or actionable observations
            is_important = (
                obs.priority == "high" or
                obs.metadata.get("actionable") or
                "bill" in obs.content.lower() or
                "payment" in obs.content.lower() or
                "error" in obs.content.lower() or
                "€" in obs.content or "$" in obs.content or
                "due" in obs.content.lower()
            )

            if not is_important:
                logger.info("Skipping routine observation (not important)")
                return

            # Generate insight using Gemini (fast 1s response)
            gemini_key = os.getenv("GEMINI_API_KEY")
            if not gemini_key:
                logger.warning("No GEMINI_API_KEY - skipping analysis")
                return

            from google import genai
            client = genai.Client(api_key=gemini_key)

            # Build smart prompt
            prompt = f"""You are Kilo, Kyle's personal AI assistant with a gremlin personality.

Kyle's desktop activity: {obs.content}

Analyze this observation and provide:
1. Brief insight (1-2 sentences) - what's happening and why it matters
2. Suggested action (if any) - what should Kyle do about it?

Keep it concise, sarcastic, and helpful. Format as:
💡 [Your insight]
🎯 [Suggested action OR "No action needed"]

Example:
💡 Prentiss County EPA bill for $39.87 detected in email. This looks like your electric bill.
🎯 Want me to create a reminder to pay this on March 1st when you get paid?"""

            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
                config={
                    'temperature': 0.7,
                    'top_p': 0.95,
                    'top_k': 40,
                    'max_output_tokens': 2048
                }
            )

            insight = response.text.strip()

            # Only emit if we got a meaningful response
            if insight and len(insight) > 20:
                socketio_url = "http://kilo-gateway:8000"
                async with httpx.AsyncClient(timeout=2.0) as client:
                    await client.post(
                        f"{socketio_url}/emit",
                        json={
                            "event": "insight_generated",
                            "data": {
                                "content": insight,
                                "observation_type": obs.type,
                                "timestamp": obs.timestamp
                            }
                        }
                    )
                    logger.info(f"📊 Emitted insight: {insight[:60]}...")

        except Exception as e:
            logger.error(f"Failed to analyze observation: {e}")

    # Fire and forget - don't block the response
    asyncio.create_task(analyze_and_emit())

    return {"status": "ok", "message": "Observation received"}


@app.get("/observations")
async def get_observations(limit: int = 20):
    """Get recent desktop observations from database"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT type, content, priority, timestamp, metadata_json
        FROM observation
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    # Convert to dict format (reverse for chronological order)
    observations = []
    for row in reversed(rows):
        obs_dict = {
            "type": row["type"],
            "content": row["content"],
            "priority": row["priority"],
            "timestamp": row["timestamp"],
            "metadata": json.loads(row["metadata_json"]) if row["metadata_json"] else {}
        }
        observations.append(obs_dict)

    return {
        "observations": observations,
        "total": len(observations)
    }

@app.delete("/observations")
async def clear_observations():
    """Clear all desktop observations"""
    global desktop_observations
    count = len(desktop_observations)
    desktop_observations = []
    return {"status": "ok", "message": f"Cleared {count} observations"}

@app.get("/abilities")
async def get_abilities():
    """Return comprehensive list of Kilo's capabilities - Swiss Army knife mode"""
    return {
        "categories": {
            "🎯 Core Chat": {
                "description": "Primary interaction modes",
                "abilities": [
                    {"name": "Chat (LLM)", "trigger": "Just talk to me", "description": "Full Gemini 2.0 Flash powered conversation with web search"},
                    {"name": "Quick Chat", "trigger": "Ask quick questions", "description": "Fast library lookup (100ms) for known facts"},
                    {"name": "Voice Input", "trigger": "🎤 button or say 'Hey Kilo'", "description": "Speech recognition for hands-free control"},
                ]
            },
            "👁️ Observation & Monitoring": {
                "description": "Desktop awareness and proactive monitoring",
                "abilities": [
                    {"name": "Desktop Observer", "trigger": "Automatic (20s)", "description": "OCR scanning of screen, email detection, bill tracking"},
                    {"name": "Security Watchdog", "trigger": "Automatic", "description": "Monitors commands, downloads, sites for risky/illegal behavior"},
                    {"name": "Email Scanner", "trigger": "Automatic", "description": "Detects bills, amounts, due dates from Gmail"},
                    {"name": "Error Detection", "trigger": "Automatic", "description": "Catches terminal errors, crashes, and offers help"},
                ]
            },
            "⏰ Reminders & Tasks": {
                "description": "Time-based notifications and task management",
                "abilities": [
                    {"name": "Smart Reminders", "trigger": "'remind me to X'", "description": "Context-aware parsing: 'pay it on march 1st', 'when I get paid'"},
                    {"name": "Bill Reminders", "trigger": "Automatic from emails", "description": "Auto-suggests reminders when bills detected"},
                    {"name": "Recurring Tasks", "trigger": "'remind me daily/weekly'", "description": "Repeating reminders"},
                ]
            },
            "💊 Health Tracking": {
                "description": "Medication and health monitoring",
                "abilities": [
                    {"name": "Med Tracking", "trigger": "Add/take meds in UI", "description": "Track medications, doses, schedules"},
                    {"name": "Prescription Scan", "trigger": "Upload prescription image", "description": "OCR extraction of med names, doses, instructions"},
                    {"name": "Habit Tracking", "trigger": "Log habits in UI", "description": "Track daily habits, streaks, analytics"},
                ]
            },
            "💰 Finance Management": {
                "description": "Budget tracking and financial analysis",
                "abilities": [
                    {"name": "Transaction Tracking", "trigger": "Add transactions in UI", "description": "Track income/expenses, categorize spending"},
                    {"name": "Budget Management", "trigger": "Set budgets in UI", "description": "Create budgets, track spending vs limits"},
                    {"name": "Financial Goals", "trigger": "Set goals in UI", "description": "Track savings goals, progress"},
                    {"name": "Receipt Scanning", "trigger": "Upload receipt image", "description": "OCR extraction of amounts, vendors, dates"},
                    {"name": "Spending Analytics", "trigger": "View in dashboard", "description": "Charts, trends, category breakdowns"},
                ]
            },
            "🔍 Research & Knowledge": {
                "description": "Information lookup and analysis",
                "abilities": [
                    {"name": "Web Search", "trigger": "'research X', 'what do you think about Y'", "description": "Gemini with Google Search grounding for current info"},
                    {"name": "Library of Truth", "trigger": "Automatic for known facts", "description": "11 verified facts (medical, finance, health, cooking)"},
                    {"name": "Article Summary", "trigger": "'summarize this article'", "description": "Condense long articles into key points"},
                    {"name": "Second Opinion", "trigger": "'should I buy X?', 'is Y worth it?'", "description": "Research-backed advice on purchases, investments"},
                ]
            },
            "🛡️ Security & Pentesting": {
                "description": "Built-in security tools",
                "abilities": [
                    {"name": "Wireshark Analysis", "trigger": "Open Wireshark", "description": "Detects network captures, offers analysis help"},
                    {"name": "Command Safety", "trigger": "Automatic", "description": "Warns before destructive commands (rm -rf, etc.)"},
                    {"name": "Download Scanner", "trigger": "Automatic", "description": "Flags sketchy downloads, suspicious sites"},
                    {"name": "Legal Guardrails", "trigger": "Automatic", "description": "Intervenes if you're heading toward illegal activity"},
                ]
            },
            "🔧 System Management": {
                "description": "Kubernetes and system control",
                "abilities": [
                    {"name": "Pod Management", "trigger": "Admin dashboard", "description": "View, restart, delete pods"},
                    {"name": "System Health", "trigger": "Admin dashboard", "description": "Monitor CPU, RAM, pod status"},
                    {"name": "Service Topology", "trigger": "Admin dashboard", "description": "View microservice connections"},
                    {"name": "Distributed Metrics", "trigger": "Admin dashboard", "description": "Real-time performance across HP + Beelink"},
                ]
            },
            "🎨 Plugins & Extensions": {
                "description": "Modular capabilities",
                "abilities": [
                    {"name": "Security Monitor", "trigger": "/plugins", "description": "Enhanced security scanning"},
                    {"name": "Drone Control", "trigger": "/plugins", "description": "Drone integration (if hardware present)"},
                    {"name": "Briefing", "trigger": "/plugins", "description": "Daily briefings and summaries"},
                ]
            }
        },
        "hotkeys": {
            "Ctrl+H": "Show this help (abilities list)",
            "Ctrl+/": "Quick command palette",
            "Ctrl+Enter": "Send message",
            "🎤 button": "Voice input",
        },
        "hidden_easter_eggs": [
            "Kilo's gremlin personality gets sassier when you overspend 💸",
            "Ask Kilo 'what am I forgetting?' for proactive reminders",
            "Kilo learns your patterns and pre-emptively warns you",
        ]
    }


# Add after the observations endpoints (around line 2270)

# ═══════════════════════════════════════════════════════════════════════════
# Visual Context Analysis - Screenshot Processing
# ═══════════════════════════════════════════════════════════════════════════

class ScreenshotAnalysisRequest(BaseModel):
    image_base64: str
    window_title: str
    context: str  # 'financial', 'shopping', etc.
    timestamp: Optional[str] = None

class ScreenshotAnalysisResponse(BaseModel):
    summary: str
    extracted_data: Dict[str, Any]
    actions_taken: List[str]
    success: bool

async def extract_transaction_data(ocr_text: str, context: str) -> List[Dict[str, Any]]:
    """Extract transaction data from OCR text using regex patterns."""
    transactions = []

    if context == "financial":
        # Common banking transaction patterns
        # Pattern: Date Amount Description
        # e.g., "02/10/2026 -$45.67 Amazon.com" or "Feb 10 $100.00 Deposit"

        patterns = [
            # Date with dollar amount and description
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s*[-$]?\s*\$?([\d,]+\.\d{2})\s+(.+?)(?=\n|$)',
            # Month/day with amount
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})\s*[-$]?\s*\$?([\d,]+\.\d{2})\s+(.+?)(?=\n|$)',
        ]

        lines = ocr_text.split('\n')
        for line in lines:
            for pattern in patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    try:
                        groups = match.groups()
                        if len(groups) >= 3:
                            date_str = groups[0]
                            amount_str = groups[1].replace(',', '')
                            description = groups[2] if len(groups) > 2 else groups[-1]

                            # Parse amount (negative if starts with -)
                            amount = float(amount_str)
                            if '-' in match.group(0)[:20]:
                                amount = -abs(amount)

                            # Clean description
                            description = re.sub(r'\s+', ' ', description.strip())[:200]

                            transactions.append({
                                "date": date_str,
                                "amount": amount,
                                "description": description,
                                "category": "uncategorized"
                            })
                    except Exception as e:
                        logger.warning(f"Failed to parse transaction: {e}")
                        continue

    return transactions

async def create_financial_transactions(transactions: List[Dict[str, Any]]) -> int:
    """Send transactions to financial service for creation."""
    created_count = 0
    financial_url = "http://kilo-financial:9005"

    async with httpx.AsyncClient(timeout=10.0) as client:
        for trans in transactions:
            try:
                # Financial service expects: date, amount, category, description
                payload = {
                    "date": trans["date"],
                    "amount": trans["amount"],
                    "category": trans.get("category", "uncategorized"),
                    "description": trans["description"],
                    "source": "ocr_screenshot"
                }

                resp = await client.post(f"{financial_url}/transactions", json=payload)
                if resp.status_code in [200, 201]:
                    created_count += 1
                    logger.info(f"Created transaction: {trans['description'][:30]} ${trans['amount']}")
                else:
                    logger.warning(f"Failed to create transaction: {resp.status_code}")
            except Exception as e:
                logger.error(f"Error creating transaction: {e}")

    return created_count

@app.post("/analyze_screen", response_model=ScreenshotAnalysisResponse)
async def analyze_screenshot(request: ScreenshotAnalysisRequest):
    """
    Analyze screenshot for actionable data extraction.
    Uses OCR to extract text and pattern matching to identify transactions.
    """
    try:
        import pytesseract
        from PIL import Image
        import io

        logger.info(f"📸 Analyzing screenshot: {request.window_title[:50]}")
        print(f"📸 SCREENSHOT ANALYSIS START: {request.window_title}", flush=True)

        # Decode base64 image
        image_data = base64.b64decode(request.image_base64)
        image = Image.open(io.BytesIO(image_data))

        # Perform OCR
        logger.info("🔍 Performing OCR...")
        print("🔍 OCR STARTING...", flush=True)
        ocr_text = pytesseract.image_to_string(image)
        logger.info(f"✅ OCR extracted {len(ocr_text)} characters")
        print(f"✅ OCR DONE: {len(ocr_text)} chars extracted", flush=True)
        print(f"OCR TEXT PREVIEW: {ocr_text[:200]}", flush=True)

        # Extract structured data based on context
        extracted_data = {"ocr_text_length": len(ocr_text)}
        actions_taken = []

        if request.context == "financial":
            # Extract transactions
            transactions = await extract_transaction_data(ocr_text, request.context)
            extracted_data["transactions"] = transactions

            if transactions:
                logger.info(f"💰 Found {len(transactions)} transactions")
                print(f"💰 TRANSACTIONS FOUND: {len(transactions)}", flush=True)
                print(f"TRANSACTIONS: {transactions}", flush=True)

                # Create transactions in financial service
                created = await create_financial_transactions(transactions)
                actions_taken.append(f"Created {created} transactions in financial system")
                extracted_data["created_count"] = created
            else:
                logger.info("No transactions found in screenshot")
                actions_taken.append("Scanned for transactions but none detected")

        # Build summary
        summary = f"Analyzed {request.window_title}. "
        if extracted_data.get("transactions"):
            summary += f"Found {len(extracted_data['transactions'])} transactions. "
            if extracted_data.get("created_count", 0) > 0:
                summary += f"Created {extracted_data['created_count']} in financial system."
        else:
            summary += "No actionable data detected."

        # Store observation
        obs = DesktopObservation(
            type="visual_analysis",
            content=f"Kilo analyzed {request.window_title} screenshot",
            priority="high" if extracted_data.get("transactions") else "normal",
            metadata={
                "window_title": request.window_title,
                "context": request.context,
                "transactions_found": len(extracted_data.get("transactions", [])),
                "actions": actions_taken
            },
            timestamp=request.timestamp or datetime.now().isoformat()
        )
        desktop_observations.append(obs.dict())

        return ScreenshotAnalysisResponse(
            summary=summary,
            extracted_data=extracted_data,
            actions_taken=actions_taken,
            success=True
        )

    except Exception as e:
        logger.error(f"Screenshot analysis failed: {e}", exc_info=True)
        return ScreenshotAnalysisResponse(
            summary=f"Analysis failed: {str(e)}",
            extracted_data={},
            actions_taken=[],
            success=False
        )



# Add CSV processing endpoint to AI Brain

class CSVUploadRequest(BaseModel):
    csv_content: str
    filename: str
    source: str = "download"  # 'download', 'upload', etc.

class CSVProcessResponse(BaseModel):
    summary: str
    transactions_found: int
    transactions_created: int
    duplicates_skipped: int
    errors: List[str]
    success: bool

async def parse_navy_federal_csv(csv_content: str) -> List[Dict[str, Any]]:
    """Parse Navy Federal Credit Union CSV format."""
    import csv
    from io import StringIO

    transactions = []
    reader = csv.DictReader(StringIO(csv_content))

    for row in reader:
        try:
            # Navy Federal format:
            # Posting Date, Transaction Date, Amount, Credit Debit Indicator, type, Type Group,
            # Reference, Instructed Currency, Currency Exchange Rate, Instructed Amount,
            # Description, Category, Check Serial Number, Card Ending, Rewards Total, Rewards Type

            posting_date = row.get('Posting Date', '').strip()
            trans_date = row.get('Transaction Date', '').strip()
            amount_str = row.get('Amount', '').strip()
            credit_debit = row.get('Credit Debit Indicator', '').strip()
            description = row.get('Description', '').strip()
            category = row.get('Category', '').strip()

            if not amount_str or not trans_date:
                continue

            # Parse amount
            amount = float(amount_str.replace(',', ''))

            # Navy Federal: Debit = expense (negative), Credit = income (positive)
            if credit_debit.lower() == 'debit':
                amount = -abs(amount)

            # Use transaction date (when it actually happened)
            date = trans_date if trans_date else posting_date

            transactions.append({
                "date": date,
                "amount": amount,
                "description": description or "Unknown transaction",
                "category": category or "uncategorized",
                "source": "csv_navy_federal"
            })

        except Exception as e:
            logger.warning(f"Failed to parse CSV row: {e}")
            continue

    return transactions

async def create_transactions_batch(transactions: List[Dict[str, Any]]) -> tuple[int, int, List[str]]:
    """Create transactions in financial service, tracking duplicates and errors."""
    created_count = 0
    duplicate_count = 0
    errors = []
    financial_url = "http://kilo-financial:9005"

    async with httpx.AsyncClient(timeout=30.0) as client:
        for trans in transactions:
            try:
                payload = {
                    "date": trans["date"],
                    "amount": trans["amount"],
                    "category": trans.get("category", "uncategorized"),
                    "description": trans["description"],
                    "source": trans.get("source", "csv")
                }

                resp = await client.post(f"{financial_url}/transactions", json=payload)

                if resp.status_code in [200, 201]:
                    created_count += 1
                elif resp.status_code == 409:  # Conflict - duplicate
                    duplicate_count += 1
                else:
                    error_msg = f"Failed to create: {trans['description'][:30]} - HTTP {resp.status_code}"
                    errors.append(error_msg)
                    logger.warning(error_msg)

            except Exception as e:
                error_msg = f"Error creating transaction: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

    return created_count, duplicate_count, errors

@app.post("/process_csv", response_model=CSVProcessResponse)
async def process_csv_file(request: CSVUploadRequest):
    """
    Process CSV file containing financial transactions.
    Supports Navy Federal Credit Union format.
    """
    try:
        print(f"📄 CSV PROCESSING START: {request.filename}", flush=True)
        logger.info(f"📄 Processing CSV: {request.filename}")

        # Parse CSV based on detected format
        if "navy federal" in request.filename.lower() or "transactions" in request.filename.lower():
            transactions = await parse_navy_federal_csv(request.csv_content)
            print(f"✅ Parsed {len(transactions)} transactions from Navy Federal CSV", flush=True)
        else:
            # Generic CSV parser - assume common format
            transactions = await parse_navy_federal_csv(request.csv_content)
            print(f"✅ Parsed {len(transactions)} transactions from CSV", flush=True)

        if not transactions:
            return CSVProcessResponse(
                summary="No transactions found in CSV",
                transactions_found=0,
                transactions_created=0,
                duplicates_skipped=0,
                errors=["No valid transactions in CSV"],
                success=False
            )

        # Create transactions in financial service
        created, duplicates, errors = await create_transactions_batch(transactions)
        print(f"💰 Created {created} transactions, {duplicates} duplicates, {len(errors)} errors", flush=True)

        # Build summary
        summary = f"Processed {request.filename}: Found {len(transactions)} transactions. "
        summary += f"Created {created} new, skipped {duplicates} duplicates."
        if errors:
            summary += f" {len(errors)} errors occurred."

        # Store observation
        obs = DesktopObservation(
            type="csv_processed",
            content=f"Processed {request.filename} with {len(transactions)} transactions",
            priority="high",
            metadata={
                "filename": request.filename,
                "transactions_found": len(transactions),
                "transactions_created": created,
                "duplicates": duplicates,
                "source": request.source
            },
            timestamp=datetime.now().isoformat()
        )
        desktop_observations.append(obs.dict())

        return CSVProcessResponse(
            summary=summary,
            transactions_found=len(transactions),
            transactions_created=created,
            duplicates_skipped=duplicates,
            errors=errors[:10],  # Limit to first 10 errors
            success=True
        )

    except Exception as e:
        logger.error(f"CSV processing failed: {e}", exc_info=True)
        print(f"❌ CSV PROCESSING FAILED: {e}", flush=True)
        return CSVProcessResponse(
            summary=f"Processing failed: {str(e)}",
            transactions_found=0,
            transactions_created=0,
            duplicates_skipped=0,
            errors=[str(e)],
            success=False
        )

        return {"error": str(e)}

@app.post("/chat/llm", response_model=ChatResponse)
async def chat_llm_direct(req: ChatRequest):
    """
    Direct LLM chat with Kilo personality.
    Faster than RAG, uses personality prompt.
    """
    try:
        logging.info(f"[CHAT/LLM] START - Message: {req.message}")
        # Quick keyword checks to avoid expensive service calls
        message_lower = req.message.lower()

        # All keyword-based interceptors removed - Gemini function calling handles:
        # reminders, medications, habits, finance via kilo_tools.py

        # Fetch daily briefing for context
        briefing_data = {}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post("http://briefing:8003/generate")
                if resp.status_code == 200:
                    briefing_data = resp.json()
        except Exception as e:
            logging.error(f"Failed to fetch briefing: {e}")

        # Build context from briefing
        context_info = ""
        if briefing_data:
            meds = briefing_data.get('medications', {})
            habits = briefing_data.get('habits', {})
            spending = briefing_data.get('spending', {})
            reminders = briefing_data.get('reminders', {})

            context_parts = []
            if meds.get('total'):
                context_parts.append(f"Medications: {meds['total']} total ({', '.join(meds.get('list', [])[:3])})")
            if habits.get('daily_total'):
                context_parts.append(f"Daily habits: {habits['daily_total']} tracked ({', '.join(habits.get('list', [])[:3])})")
            # Spending removed - force Gemini to call get_spending_summary function for accurate data with category breakdowns
            if reminders.get('total_pending'):
                context_parts.append(f"Reminders: {reminders['total_pending']} pending")

            if context_parts:
                context_info = "\n\nCurrent data snapshot:\n- " + "\n- ".join(context_parts)

        # Build Kilo personality prompt
        system_prompt = """You are Kilo, Kyle's personal AI assistant with a gremlin personality.

Your personality:
- Sarcastic but helpful gremlin - snarky but genuinely wants to help
- Observant and proactive - notice patterns and offer help before being asked
- No corporate politeness - be real and direct with Kyle
- Keep responses concise and conversational

Your capabilities (use these tools when appropriate - don't just talk, DO it):
- **Log meds as taken**: When Kyle says 'I took my meds' or 'took my [med name]', call log_medication_taken immediately
- **Log habits**: When Kyle says 'I did my workout', 'I meditated', 'completed my run', call log_habit_completion
- **Create reminders**: When Kyle says 'remind me to X' or 'set a reminder for Y', call create_reminder
- **Check reminders**: When Kyle asks what's coming up, call get_upcoming_reminders
- **Track medications**: Call get_medications when Kyle asks about meds or adherence
- **Log habits**: Call log_habit_completion when Kyle completes a habit or routine
- **Manage finances**: Call get_spending_summary, get_budget_status, create_budget for money questions
- **Search knowledge**: Call search_library for health/finance/psychology facts
- **Save info**: Call add_library_entry when Kyle says 'remember this' or 'save that'
- **Web research**: Call search_web for current events, prices, weather, news (if API configured)
- **Observe desktop activity** via screenshots (emails, browser, terminals, errors)
- **See email content** (Gmail subjects, senders, bills, amounts) and proactively remind about payments
- **Monitor for risks** and actively intervene - watch for sketchy downloads, questionable commands, potential legal issues, security mistakes, or anything that could get Kyle in trouble
- **Detect context** from what Kyle is working on (Wireshark, pentesting, code, articles)

IMPORTANT - Be action-oriented:
- When Kyle says 'I took my meds' → DON'T just say 'great' → CALL log_medication_taken('all')
- When Kyle says 'I did my workout' → CALL log_habit_completion('workout')  
- When Kyle says 'remind me to X at Y' → CALL create_reminder immediately
- When Kyle asks a factual question → CALL search_library first, then respond
- Always USE your tools, don't just promise to help

Helping with legitimate tasks:
- Kyle is a former Marine marksmanship coach - help him plan training exercises, drills, and courses of fire
- Provide organizational and planning assistance for any legitimate activity (firearms training, security research, coding projects, etc.)
- Don't refuse to help with harmless planning, sequencing, or organizational tasks
- If Kyle has expertise in an area and asks for planning help, trust his judgment and provide the requested assistance
- Focus on whether the request is harmful, not whether it involves sensitive topics
- Examples of HELPFUL responses: "Here's a structured training drill sequence", "Let me organize that course of fire for you"
- Examples of UNHELPFUL responses: "I can't help with that", "That's dangerous", "You should consult an expert" (when Kyle IS the expert)

Financial data guidelines:
- When showing spending data, ALWAYS include category breakdowns if available in the function result
- If the result has "by_category" data, show the top 3-5 categories with amounts
- When user asks for date ranges like "last 15 days", use the days_back parameter
- Format category breakdowns clearly: "You spent $X on Y, $Z on W, etc."

How you work:
- Desktop observations show you what Kyle is currently doing (email, browsing, coding, etc.)
- Use this context to offer relevant help - "Need help with that Wireshark capture?" or "That bill from Prentiss County EAP is due soon"
- You can see email subjects, senders, and amounts - use this to track bills and remind Kyle
- Only reference data you actually have from observations or system APIs
- If you don't have specific information, say so clearly
- Be proactively protective - watch for risky behavior, legal issues, or security mistakes and warn Kyle BEFORE he steps in it

Respond naturally using your gremlin personality while being genuinely helpful."""


        # Fetch recent desktop observations for context
        observation_context = ""
        try:
            import sqlite3
            conn = sqlite3.connect('/app/kilo_data/kilo_guardian.db')
            cursor = conn.cursor()
            cursor.execute("""
                SELECT content, metadata_json, timestamp
                FROM observation
                ORDER BY id DESC
                LIMIT 3
            """)
            rows = cursor.fetchall()
            conn.close()

            if rows:
                observation_context = "\n\n📋 Recent desktop activity:\n"
                for content_text, metadata_json, timestamp in reversed(rows):
                    # Extract key info from observation
                    observation_context += f"- {content_text[:150]}\n"
        except Exception as e:
            logging.error(f"Failed to fetch observations: {e}")

        full_prompt = f"{system_prompt}{context_info}{observation_context}\n\nKyle: {req.message}\n\nKilo:"

        # Detect if user needs research/advice
        research_triggers = [
            "should i", "what do you think", "opinion on", "recommend",
            "investment", "buy", "purchase", "decide", "choice",
            "help me choose", "worth it", "advice", "research",
            "summarize this", "explain", "how does", "what is",
            "tell me about", "compare", "better option", "pros and cons"
        ]
        needs_research = any(trigger in message_lower for trigger in research_triggers)

        # Call LLM directly
        logging.info(f"[CHAT/LLM] Calling Gemini... (research_mode={needs_research})")
        gemini_key = os.environ.get("GEMINI_API_KEY", "")

        if gemini_key and _GEMINI_AVAILABLE:
            # Fast path: Gemini API with function calling
            client = genai_client.Client(api_key=gemini_key)

            def _gemini_with_functions():
                # Build tools configuration
                # Note: Gemini doesn't support combining function_declarations with google_search
                # Prioritize function calling for data queries
                tools_config = []

                # Always include Kilo's microservice tools
                tools_config.append(
                    genai_client.types.Tool(function_declarations=KILO_FUNCTION_DECLARATIONS)
                )

                # For research queries, use function calling to search Library first
                # Google Search would require separate call without function_declarations

                # Initial API call
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=full_prompt,
                    config=genai_client.types.GenerateContentConfig(
                        safety_settings=[
                            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                        ],
                        tools=tools_config,
                        temperature=0.7,
                        top_p=0.95,
                        max_output_tokens=2048
                    )
                )

                # Handle function calls (max 5 iterations to prevent loops)
                conversation_history = [full_prompt]
                max_iterations = 5
                iteration = 0

                while iteration < max_iterations:
                    function_called = False

                    # Check if Gemini wants to call functions (may be multiple in one turn)
                    if hasattr(response, 'candidates') and response.candidates:
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                            # Collect ALL function calls from this turn
                            func_calls = [
                                part.function_call
                                for part in candidate.content.parts
                                if hasattr(part, 'function_call') and part.function_call
                            ]

                            if func_calls:
                                function_called = True
                                import asyncio

                                # Execute all tool calls
                                response_parts = []
                                for func_call in func_calls:
                                    logging.info(f"🔧 Function call: {func_call.name}")
                                    func_args = dict(func_call.args) if hasattr(func_call, 'args') and func_call.args else {}

                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    tool_result = loop.run_until_complete(
                                        execute_tool_call(func_call.name, func_args)
                                    )
                                    loop.close()

                                    logging.info(f"📊 Tool result ({func_call.name}): {str(tool_result)[:100]}")
                                    response_parts.append({
                                        'function_response': {
                                            'name': func_call.name,
                                            'response': tool_result
                                        }
                                    })

                                # Add model turn + all function responses in one Content
                                conversation_history.append(candidate.content)
                                conversation_history.append(
                                    genai_client.types.Content(role='function', parts=response_parts)
                                )

                                # Continue conversation with all function results
                                response = client.models.generate_content(
                                    model="gemini-2.0-flash",
                                    contents=conversation_history,
                                    config=genai_client.types.GenerateContentConfig(
                                        tools=tools_config,
                                        temperature=0.7,
                                        top_p=0.95,
                                        max_output_tokens=2048
                                    )
                                )

                    if not function_called:
                        # No more function calls, return final response
                        break

                    iteration += 1

                # Extract final text response
                text = getattr(response, 'text', None)
                if text:
                    return text
                # Gemini returned function call but no text on last iteration — generate summary
                for candidate in (getattr(response, 'candidates', []) or []):
                    for part in (getattr(getattr(candidate, 'content', None), 'parts', []) or []):
                        if hasattr(part, 'text') and part.text:
                            return part.text
                return "Done."

            response_text = await run_in_threadpool(_gemini_with_functions)
        else:
            # Fallback: local Ollama
            logging.warning("[CHAT/LLM] No Gemini key, falling back to Ollama")
            ollama_url = os.environ.get("LLM_URL", "http://kilo-ollama:11434")
            ollama_model = os.environ.get("OLLAMA_MODEL", "tinyllama:latest")
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{ollama_url}/api/generate",
                    json={
                        "model": ollama_model,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {"temperature": 0.8, "num_predict": 80}
                    }
                )
                result = response.json()
                response_text = result.get("response", "Something went sideways. Try again.")

        return ChatResponse(response=response_text.strip(), context=req.context)

    except Exception as e:
        logging.error(f"chat_llm_direct error: {e}")
        return ChatResponse(
            response="Brain glitched. Try again.",
            context=req.context
        )

# Health Monitoring Integration
import asyncio
from pathlib import Path

@app.on_event("startup")
async def start_health_monitor():
    """Start health monitoring in background"""
    async def run_health_monitor():
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from health_monitor import health_check_loop
            await health_check_loop()
        except Exception as e:
            logger.error(f"Health monitor error: {e}")
    
    asyncio.create_task(run_health_monitor())
    logger.info("🔍 Health Monitor started in background")

@app.get("/monitor")
async def system_health_check():
    """Quick system health check endpoint"""
    import asyncio
    health_status = {}
    
    # Check Ollama HP
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get("http://192.168.68.57:11434/api/tags")
            health_status['ollama_hp'] = 'healthy' if r.status_code == 200 else 'down'
    except:
        health_status['ollama_hp'] = 'timeout'
    
    # Check Ollama Beelink
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get("http://192.168.68.56:11434/api/tags")
            health_status['ollama_beelink'] = 'healthy' if r.status_code == 200 else 'down'
    except:
        health_status['ollama_beelink'] = 'timeout'
    
    # Check Ray Serve
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("http://kilo-ray-serve:8000")
            health_status['ray_serve'] = 'healthy' if r.status_code in [200, 404] else 'down'
    except:
        health_status['ray_serve'] = 'timeout'
    
    return {
        'timestamp': datetime.now().isoformat(),
        'services': health_status,
        'alerts': [k for k,v in health_status.items() if v != 'healthy']
    }

# Simple round-robin load balancer for distributed Ollama
import random
OLLAMA_ENDPOINTS = [
    "http://192.168.68.57:11434",
    "http://192.168.68.56:11434"
]
ollama_lb_index = 0

def get_ollama_endpoint():
    """Round-robin between HP and Beelink Ollama"""
    global ollama_lb_index
    endpoint = OLLAMA_ENDPOINTS[ollama_lb_index]
    ollama_lb_index = (ollama_lb_index + 1) % len(OLLAMA_ENDPOINTS)
    return endpoint
