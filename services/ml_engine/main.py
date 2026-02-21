"""
Kilo ML Engine - Learns Kyle's behavioral patterns from real data.

Trains nightly from:
- Habit completions (kilo-habits:9000)
- Medications taken (kilo-meds:9000)  
- Financial transactions (kilo-financial:9005)

Provides:
- /insights  - pattern analysis Kilo reads from chat
- /predict/habit/{id} - should Kilo remind about this habit now?
- /learn - trigger immediate retraining
- /health, /status
"""

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import httpx
import asyncio
import json
import sqlite3
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Kilo ML Engine")

# Use shared PVC so models survive pod restarts
MODELS_DIR = Path("/app/kilo_data/ml_models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = "/app/kilo_data/kilo_guardian.db"
AI_BRAIN_URL = os.environ.get("AI_BRAIN_URL", "http://kilo-ai-brain:9004")
HABITS_URL = os.environ.get("HABITS_URL", "http://kilo-habits:9000")
MEDS_URL = os.environ.get("MEDS_URL", "http://kilo-meds:9000")
FINANCIAL_URL = os.environ.get("FINANCIAL_URL", "http://kilo-financial:9005")

# In-memory pattern cache (refreshed on /learn)
pattern_cache: Dict = {}
last_trained: Optional[str] = None


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


async def notify_kilo(content: str):
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{AI_BRAIN_URL}/observations", json={
                "source": "ml_engine",
                "type": "pattern_insight",
                "content": content,
                "priority": "normal",
                "metadata": {"auto": True}
            })
    except Exception as e:
        logger.error(f"notify_kilo failed: {e}")


# -- PATTERN ANALYSIS ────────────────────────────────────────────────────────

def analyze_habit_patterns(habits: list) -> list:
    """Find day-of-week patterns, streaks, and drop-offs from real completion data."""
    insights = []
    today = datetime.now().date()

    for habit in habits:
        name = habit.get("name", "unknown")
        completions = habit.get("completions", [])
        if not completions:
            continue

        # Parse completion dates
        done_dates = set()
        day_counts = defaultdict(int)
        for c in completions:
            ds = c.get("completion_date") or c.get("date") or c.get("completed_at", "")
            if ds:
                try:
                    d = datetime.fromisoformat(ds[:10]).date()
                    if c.get("count", c.get("completed", 1)) > 0:
                        done_dates.add(d)
                        day_counts[d.strftime("%A")] += 1
                except Exception:
                    pass

        if not done_dates:
            continue

        # Current streak
        streak = 0
        for i in range(60):
            check = today - timedelta(days=i)
            if check in done_dates:
                streak += 1
            elif i > 0:
                break

        # Recent drop-off (no completions in 3 days but had them before)
        recent = any((today - timedelta(days=i)) in done_dates for i in range(3))
        older = any((today - timedelta(days=i)) in done_dates for i in range(4, 14))

        if not recent and older:
            insights.append({
                "type": "dropoff",
                "habit": name,
                "message": f"'{name}' hasn't been completed in 3+ days but was active before."
            })
        elif streak >= 7:
            insights.append({
                "type": "streak",
                "habit": name,
                "streak": streak,
                "message": f"'{name}' is on a {streak}-day streak!"
            })

        # Best day of week
        if day_counts:
            best_day = max(day_counts, key=day_counts.get)
            insights.append({
                "type": "best_day",
                "habit": name,
                "day": best_day,
                "message": f"Kyle completes '{name}' most often on {best_day}s ({day_counts[best_day]} times)."
            })

    return insights


def analyze_med_patterns(meds: list) -> list:
    """Detect medication adherence patterns."""
    insights = []
    today = datetime.now().date()

    for med in meds:
        name = med.get("name", "unknown")
        logs = med.get("logs", med.get("history", []))
        if not logs:
            continue

        taken_dates = set()
        for log in logs:
            ds = log.get("taken_at") or log.get("date") or log.get("timestamp", "")
            if ds:
                try:
                    taken_dates.add(datetime.fromisoformat(ds[:10]).date())
                except Exception:
                    pass

        # Check last 7 days adherence
        last_7 = sum(1 for i in range(7) if (today - timedelta(days=i)) in taken_dates)
        rate = last_7 / 7.0

        if rate < 0.5:
            insights.append({
                "type": "med_adherence",
                "med": name,
                "rate": rate,
                "message": f"Medication adherence for '{name}' is {int(rate*100)}% over the last week."
            })

    return insights


def analyze_spending_patterns(transactions: list) -> list:
    """Find spending patterns and anomalies."""
    insights = []
    if not transactions:
        return insights

    today = datetime.now().date()
    this_month = defaultdict(float)
    last_month = defaultdict(float)

    for tx in transactions:
        ds = tx.get("date") or tx.get("transaction_date", "")
        amount = abs(float(tx.get("amount", 0)))
        category = tx.get("category") or tx.get("merchant_category", "Other")
        if not ds:
            continue
        try:
            d = datetime.fromisoformat(ds[:10]).date()
            months_ago = (today.year - d.year) * 12 + (today.month - d.month)
            if months_ago == 0:
                this_month[category] += amount
            elif months_ago == 1:
                last_month[category] += amount
        except Exception:
            pass

    # Find categories that spiked >30%
    for cat, amt in this_month.items():
        prev = last_month.get(cat, 0)
        if prev > 0 and amt > prev * 1.3:
            insights.append({
                "type": "spending_spike",
                "category": cat,
                "this_month": round(amt, 2),
                "last_month": round(prev, 2),
                "message": f"{cat} spending is up {int((amt/prev-1)*100)}% vs last month (${amt:.0f} vs ${prev:.0f})."
            })

    return insights


async def run_learning() -> Dict:
    """Fetch all data and build pattern cache."""
    global pattern_cache, last_trained

    all_insights = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Habits
        try:
            r = await client.get(f"{HABITS_URL}/")
            habits = r.json().get("habits", r.json()) if r.status_code == 200 else []
            if isinstance(habits, list):
                all_insights.extend(analyze_habit_patterns(habits))
        except Exception as e:
            logger.warning(f"Habits fetch failed: {e}")

        # Meds
        try:
            r = await client.get(f"{MEDS_URL}/")
            meds = r.json().get("meds", r.json()) if r.status_code == 200 else []
            if isinstance(meds, list):
                all_insights.extend(analyze_med_patterns(meds))
        except Exception as e:
            logger.warning(f"Meds fetch failed: {e}")

        # Financial
        try:
            r = await client.get(f"{FINANCIAL_URL}/transactions?limit=500")
            if r.status_code == 200:
                raw = r.json()
                txns = raw if isinstance(raw, list) else raw.get("transactions", [])
            else:
                txns = []
            if isinstance(txns, list):
                all_insights.extend(analyze_spending_patterns(txns))
        except Exception as e:
            logger.warning(f"Financial fetch failed: {e}")

    pattern_cache = {
        "insights": all_insights,
        "generated_at": datetime.now().isoformat(),
        "counts": {
            "habit_insights": sum(1 for i in all_insights if i["type"] in ("streak", "dropoff", "best_day")),
            "med_insights": sum(1 for i in all_insights if i["type"] == "med_adherence"),
            "spending_insights": sum(1 for i in all_insights if i["type"] == "spending_spike"),
        }
    }

    # Save to disk so it survives restarts
    cache_path = MODELS_DIR / "pattern_cache.json"
    cache_path.write_text(json.dumps(pattern_cache, indent=2))

    last_trained = datetime.now().isoformat()
    logger.info(f"Learning complete: {len(all_insights)} patterns found")

    # Send notable insights to Kilo as observations
    notable = [i for i in all_insights if i["type"] in ("dropoff", "spending_spike", "med_adherence")]
    for insight in notable[:3]:
        await notify_kilo(f"Pattern detected: {insight['message']}")

    return pattern_cache


def load_cache():
    """Load cached patterns from disk on startup."""
    global pattern_cache
    cache_path = MODELS_DIR / "pattern_cache.json"
    if cache_path.exists():
        try:
            pattern_cache = json.loads(cache_path.read_text())
            logger.info(f"Loaded {len(pattern_cache.get('insights', []))} cached patterns")
        except Exception as e:
            logger.warning(f"Cache load failed: {e}")


async def nightly_loop():
    """Retrain every night at 2am."""
    await asyncio.sleep(10)  # Initial run shortly after startup
    await run_learning()
    while True:
        now = datetime.now()
        next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
        if now >= next_run:
            next_run += timedelta(days=1)
        wait = (next_run - now).total_seconds()
        logger.info(f"Next learning run in {wait/3600:.1f} hours")
        await asyncio.sleep(wait)
        await run_learning()


# -- ENDPOINTS ───────────────────────────────────────────────────────────────

@app.get("/health")
@app.get("/status")
def health():
    return {"status": "ok", "last_trained": last_trained, "patterns": len(pattern_cache.get("insights", []))}


@app.get("/insights")
def get_insights():
    """Return all current pattern insights. Kilo reads this via tool call."""
    if not pattern_cache:
        return {"insights": [], "message": "No patterns yet — learning runs at startup and nightly at 2am."}
    return pattern_cache


@app.post("/learn")
async def trigger_learning(background_tasks: BackgroundTasks):
    """Trigger immediate retraining. Kilo can call this from chat."""
    background_tasks.add_task(run_learning)
    return {"status": "learning_started", "message": "Analyzing your patterns now. Check /insights in ~10 seconds."}


@app.get("/predict/habit/{habit_id}")
async def predict_habit(habit_id: int):
    """Should Kilo remind about this habit right now?"""
    now = datetime.now()
    day_of_week = now.strftime("%A")
    hour = now.hour

    # Look up this habit's best_day pattern from cache
    insights = pattern_cache.get("insights", [])
    best_day = None
    for i in insights:
        if i.get("type") == "best_day" and i.get("habit_id") == habit_id:
            best_day = i.get("day")
            break

    # Simple heuristic: remind if it's morning/evening and not on best day
    should_remind = hour in range(8, 10) or hour in range(18, 21)
    if best_day and day_of_week == best_day:
        should_remind = False  # Will likely do it anyway

    return {
        "habit_id": habit_id,
        "should_remind": should_remind,
        "day_of_week": day_of_week,
        "best_day": best_day,
        "reasoning": f"It is {day_of_week} at {now.strftime('%H:%M')}. Best day is {best_day or 'unknown'}."
    }


@app.on_event("startup")
async def startup():
    load_cache()
    asyncio.create_task(nightly_loop())
    logger.info("ML Engine started — initial learning will run in 10s")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9009)
