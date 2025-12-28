from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Request
from sqlalchemy import text
from sqlmodel import SQLModel, Session, Field, select
from typing import Optional, List, Dict
import os
import httpx
import datetime
from PIL import Image
from io import BytesIO
import pytesseract
import re
import base64
from contextlib import asynccontextmanager
from db import get_engine
from shared.models import Transaction, ReceiptItem
# Financial models
# Use shared models where appropriate to avoid duplicate definitions during test collection


class Budget(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    category: str
    monthly_limit: float
    created_at: str


class Goal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    target_amount: float
    current_amount: float = 0.0
    deadline: Optional[str] = None
    created_at: str
    completed: bool = False


# Centralized engine selection (prefers in-memory for tests and fallbacks if /data not writable)
engine = get_engine('FINANCIAL_DB_URL', 'sqlite:////data/financial.db')


# Scheduler control defaults (used by lifespan)
ENABLE_NIGHTLY_MAINTENANCE = os.getenv("ENABLE_NIGHTLY_MAINTENANCE", "false").lower() in ("1", "true", "yes")
NIGHTLY_CRON = os.getenv("NIGHTLY_CRON", "0 2 * * *")  # default: daily at 02:00
# runtime scheduler handle (set up at startup if enabled)
_scheduler = None


# Health check endpoint will be attached to the app created with lifespan below


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    try:
        SQLModel.metadata.create_all(engine)
        try:
            from financial.scripts.add_category_column_if_missing import ensure_column
            ensure_column()
        except Exception:
            print("Warning: failed to run migration helper")
        # schedule nightly maintenance if enabled
        global _scheduler
        if ENABLE_NIGHTLY_MAINTENANCE:
            try:
                from apscheduler.schedulers.background import BackgroundScheduler
                from apscheduler.triggers.cron import CronTrigger
                _scheduler = BackgroundScheduler()
                cron_parts = NIGHTLY_CRON.split()
                if len(cron_parts) == 5:
                    minute, hour, day, month, dow = cron_parts
                    trigger = CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=dow)
                else:
                    trigger = CronTrigger.from_crontab(NIGHTLY_CRON)
                _scheduler.add_job(_recalculate_categories_background, trigger=trigger, id='nightly_recat')
                _scheduler.start()
                app.state.scheduler = _scheduler
                print("Nightly maintenance scheduler started")
            except Exception as e:
                print(f"Warning: failed to start scheduler: {e}")
    except Exception:
        pass
    yield
    # shutdown
    try:
        if _scheduler:
            _scheduler.shutdown(wait=False)
            print("Scheduler shut down")
    except Exception:
        pass


app = FastAPI(title="Financial Service", lifespan=lifespan)


# Health check endpoints
@app.get("/status")
@app.get("/health")
def status():
    return {"status": "ok"}


AI_BRAIN_URL = os.getenv("AI_BRAIN_URL", "http://ai_brain:9004/ingest/finance")
# Note: admin credentials are read at call-time to allow tests to set env vars after import


# startup/shutdown handled by lifespan


def _check_admin_auth(request: Request):
    """Centralized admin auth: supports legacy x-admin-token, ADMIN_TOKEN_LIST, and optional Basic auth.
    If no admin credentials are configured, the endpoint is open (same legacy behavior when ADMIN_TOKEN was not set).
    """
    # read admin credentials dynamically from environment
    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
    ADMIN_TOKEN_LIST = set([t for t in (os.getenv("ADMIN_TOKEN_LIST") or "").split(",") if t])
    ADMIN_BASIC_USER = os.getenv("ADMIN_BASIC_USER")
    ADMIN_BASIC_PASS = os.getenv("ADMIN_BASIC_PASS")

    # if no admin credential is configured, allow
    if not (ADMIN_TOKEN or ADMIN_TOKEN_LIST or (ADMIN_BASIC_USER and ADMIN_BASIC_PASS)):
        # no local admin configured; if a header is provided, try gateway centralized validation
        token = request.headers.get("x-admin-token")
        if not token:
            return True
        # lazy import gateway validator
        try:
            from gateway.admin_client import validate_token as _gval
            if _gval(token):
                return True
        except Exception:
            pass
        raise HTTPException(status_code=403, detail="invalid admin credentials")

    # check x-admin-token header
    token = request.headers.get("x-admin-token")
    if token:
        if ADMIN_TOKEN and token == ADMIN_TOKEN:
            return True
        if token in ADMIN_TOKEN_LIST:
            return True

    # check HTTP Basic Authorization header
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("basic ") and ADMIN_BASIC_USER and ADMIN_BASIC_PASS:
        try:
            payload = base64.b64decode(auth.split(None, 1)[1]).decode()
            user, pwd = payload.split(":", 1)
            if user == ADMIN_BASIC_USER and pwd == ADMIN_BASIC_PASS:
                return True
        except Exception:
            pass

    # nothing matched
    raise HTTPException(status_code=403, detail="invalid admin credentials")


# shutdown handled by lifespan


@app.get("/")
@app.get("/transactions")  # Frontend-compatible alias
def list_transactions():
    with Session(engine) as session:
        txs = session.exec(select(Transaction)).all()
        out = []
        for t in txs:
            items = session.exec(select(ReceiptItem).where(ReceiptItem.transaction_id == t.id)).all()
            d = t.dict()
            d["items"] = [it.dict() for it in items]
            out.append(d)
        return out


@app.get("/summary")
def get_financial_summary():
    with Session(engine) as session:
        transactions = session.exec(select(Transaction)).all()
        total_income = sum(t.amount for t in transactions if t.amount > 0)
        total_expenses = sum(t.amount for t in transactions if t.amount < 0)
        balance = total_income + total_expenses
        # Aggregate by category from receipt items for a simple analytics view
        receipt_items = session.exec(select(ReceiptItem)).all()
        by_category: Dict[str, float] = {}
        for it in receipt_items:
            cat = _categorize_item(it.name)
            by_category[cat] = by_category.get(cat, 0) + it.price
        return {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "balance": balance,
            "spend_by_category": by_category,
            "transaction_count": len(transactions)
        }


@app.get("/shopping_habits")
def get_shopping_habits():
    with Session(engine) as session:
        receipt_items = session.exec(select(ReceiptItem)).all()
        item_counts = {}
        for item in receipt_items:
            item_counts[item.name] = item_counts.get(item.name, 0) + 1
        sorted_items = sorted(item_counts.items(), key=lambda item: item[1], reverse=True)
        return {"most_frequent_items": sorted_items[:5]}


@app.get("/spending_trends")
def get_spending_trends():
    with Session(engine) as session:
        transactions = session.exec(select(Transaction)).all()
        monthly_spending = {}
        for t in transactions:
            month = datetime.datetime.fromisoformat(t.date).strftime("%Y-%m")
            monthly_spending[month] = monthly_spending.get(month, 0) + t.amount
        sorted_spending = sorted(monthly_spending.items())
        return {"monthly_spending": sorted_spending}


@app.post("/")
@app.post("/transaction")  # Frontend-compatible alias
def add_transaction(t: Transaction, background_tasks: BackgroundTasks = None):
    # Ensure source field is set safely
    current_source = getattr(t, 'source', None)
    if current_source is None:
        setattr(t, 'source', 'manual')
    with Session(engine) as session:
        session.add(t)
        session.commit()
        session.refresh(t)
    # Send to ai_brain
    if background_tasks:
        background_tasks.add_task(_send_to_ai_brain, t)
    else:
        import asyncio
        asyncio.create_task(_send_to_ai_brain(t))
    return t


@app.put("/{transaction_id}")
def update_transaction(transaction_id: int, t: Transaction, background_tasks: BackgroundTasks = None):
    with Session(engine) as session:
        db_transaction = session.get(Transaction, transaction_id)
        if not db_transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        db_transaction.amount = t.amount
        db_transaction.category = t.category
        db_transaction.description = t.description
        db_transaction.date = t.date
        db_transaction.type = t.type
        session.add(db_transaction)
        session.commit()
        session.refresh(db_transaction)
    if background_tasks:
        background_tasks.add_task(_send_to_ai_brain, db_transaction)
    return db_transaction


@app.delete("/{transaction_id}")
@app.delete("/transactions/{transaction_id}")  # Frontend-compatible alias
def delete_transaction(transaction_id: int):
    with Session(engine) as session:
        transaction = session.get(Transaction, transaction_id)
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        # Delete associated receipt items
        items = session.exec(select(ReceiptItem).where(ReceiptItem.transaction_id == transaction_id)).all()
        for item in items:
            session.delete(item)
        session.delete(transaction)
        session.commit()
    return {"status": "deleted"}


# Budget endpoints
@app.get("/budgets")
def get_budgets():
    with Session(engine) as session:
        budgets = session.exec(select(Budget)).all()
        return budgets


@app.post("/budgets")
@app.post("/budget")  # Frontend-compatible alias
def create_budget(budget: Budget, background_tasks: BackgroundTasks = None):
    budget.created_at = datetime.datetime.utcnow().isoformat()
    with Session(engine) as session:
        session.add(budget)
        session.commit()
        session.refresh(budget)
    if background_tasks:
        background_tasks.add_task(_send_budget_to_ai, budget)
    return budget


@app.put("/budgets/{budget_id}")
def update_budget(budget_id: int, budget: Budget):
    with Session(engine) as session:
        db_budget = session.get(Budget, budget_id)
        if not db_budget:
            raise HTTPException(status_code=404, detail="Budget not found")
        db_budget.category = budget.category
        db_budget.monthly_limit = budget.monthly_limit
        session.add(db_budget)
        session.commit()
        session.refresh(db_budget)
        return db_budget


@app.delete("/budgets/{budget_id}")
def delete_budget(budget_id: int):
    with Session(engine) as session:
        budget = session.get(Budget, budget_id)
        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found")
        session.delete(budget)
        session.commit()
    return {"status": "deleted"}


# Goal endpoints
@app.get("/goals")
def get_goals():
    with Session(engine) as session:
        goals = session.exec(select(Goal)).all()
        return goals


@app.post("/goals")
@app.post("/goal")  # Frontend-compatible alias
def create_goal(goal: Goal, background_tasks: BackgroundTasks = None):
    goal.created_at = datetime.datetime.utcnow().isoformat()
    with Session(engine) as session:
        session.add(goal)
        session.commit()
        session.refresh(goal)
    if background_tasks:
        background_tasks.add_task(_send_goal_to_ai, goal)
    return goal


@app.put("/goals/{goal_id}")
def update_goal(goal_id: int, goal: Goal):
    with Session(engine) as session:
        db_goal = session.get(Goal, goal_id)
        if not db_goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        db_goal.name = goal.name
        db_goal.target_amount = goal.target_amount
        db_goal.current_amount = goal.current_amount
        db_goal.deadline = goal.deadline
        db_goal.completed = goal.completed
        session.add(db_goal)
        session.commit()
        session.refresh(db_goal)
    return db_goal


@app.delete("/goals/{goal_id}")
def delete_goal(goal_id: int):
    with Session(engine) as session:
        goal = session.get(Goal, goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        session.delete(goal)
        session.commit()
    return {"status": "deleted"}


@app.post("/receipt")
def upload_receipt(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    content = file.file.read()
    img = Image.open(BytesIO(content))
    text = pytesseract.image_to_string(img)
    items, detected_total = _parse_receipt_items(text)
    summed = sum(i['price'] for i in items)
    # Prefer a clearly indicated total on the receipt when available and reasonable
    if detected_total is not None:
        # if detected total differs wildly from summed items, trust detected_total
        if abs(detected_total - summed) > max(0.01, 0.1 * abs(summed)):
            total = detected_total
        else:
            total = summed
    else:
        total = summed
    t = Transaction(
        amount=total,
        description="Receipt Upload",
        date=datetime.datetime.utcnow().isoformat(),
        source='ocr',
    )
    with Session(engine) as session:
        session.add(t)
        session.commit()
        session.refresh(t)
        for item in items:
            cat = _categorize_item(item.get('name', ''))
            ri = ReceiptItem(
                transaction_id=t.id,
                name=item['name'],
                price=item['price'],
                category=cat,
            )
            session.add(ri)
        session.commit()
        # serialize within the session so detached-instance issues do not occur
        tx_serialized = {
            "id": getattr(t, "id", None),
            "amount": getattr(t, "amount", None),
            "description": getattr(t, "description", None),
            "date": getattr(t, "date", None),
            "source": getattr(t, "source", None),
        }
    # Send to ai_brain
    if background_tasks:
        background_tasks.add_task(_send_receipt_to_ai_brain, text)
    else:
        import asyncio
        asyncio.create_task(_send_receipt_to_ai_brain(text))
    # ensure the Transaction is serialized to native types for JSON
    # model_dump()/dict() behavior can vary across SQLModel versions; serialize explicitly
        return {"transaction": tx_serialized, "items": items}
    return {"transaction": tx_serialized, "items": items}


@app.post("/admin/recalculate_categories")
def recalculate_categories(request: Request, background_tasks: BackgroundTasks):
    """Trigger re-categorization. Requires ADMIN_TOKEN header when ADMIN_TOKEN is set.
    Runs as a background job to avoid long blocking calls.
    """
    _check_admin_auth(request)

    # schedule background job
    background_tasks.add_task(_recalculate_categories_background)
    return {"status": "scheduled"}


@app.get("/admin/migration_status")
def migration_status(request: Request):
    """Return current DB alembic revision and available heads.
    Requires ADMIN_TOKEN when set.
    """
    _check_admin_auth(request)

    # determine alembic heads
    try:
        from alembic.config import Config as AlembicConfig
        from alembic.script import ScriptDirectory
        alembic_ini = os.path.join(os.getcwd(), 'alembic.ini')
        cfg = AlembicConfig(alembic_ini)
        script = ScriptDirectory.from_config(cfg)
        heads = script.get_heads()
    except Exception:
        heads = []

    # read current revision from alembic_version table if present
    current = None
    try:
        with engine.connect() as conn:
            r = conn.execute(text("SELECT version_num FROM alembic_version"))
            row = r.fetchone()
            if row:
                current = row[0]
    except Exception:
        current = None

    return {"db_revision": current, "heads": heads}


def _recalculate_categories_background(batch_size: int = 200):
    updated = 0
    total = 0
    with Session(engine) as session:
        offset = 0
        while True:
            items = session.exec(select(ReceiptItem).offset(offset).limit(batch_size)).all()
            if not items:
                break
            for it in items:
                total += 1
                new_cat = _categorize_item(it.name or "")
                if it.category != new_cat:
                    it.category = new_cat
                    session.add(it)
                    updated += 1
            session.commit()
            offset += batch_size
    print(f"Recalculate categories completed: updated={updated}, total={total}")
    return {"updated": updated, "total": total}


async def _send_to_ai_brain(t: Transaction):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(AI_BRAIN_URL, json={
                "amount": t.amount,
                "description": t.description,
                "date": t.date
            }, timeout=5)
        except Exception as e:
            print(f"[AI_BRAIN] Failed to send transaction: {e}")


async def _send_receipt_to_ai_brain(text: str):
    async with httpx.AsyncClient() as client:
        try:
            await client.post("http://ai_brain:9004/ingest/receipt", json={"text": text}, timeout=5)
        except Exception as e:
            print(f"[AI_BRAIN] Failed to send receipt: {e}")


async def _send_budget_to_ai(budget: Budget):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                "http://ai_brain:9004/ingest/budget",
                json={
                    "category": budget.category,
                    "monthly_limit": budget.monthly_limit,
                    "created_at": budget.created_at,
                },
                timeout=5,
            )
        except Exception as e:
            print(f"[AI_BRAIN] Failed to send budget: {e}")


async def _send_goal_to_ai(goal: Goal):
    async with httpx.AsyncClient() as client:
        try:
            # Check progress and send motivational message
            progress_percent = (goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0
            remaining = goal.target_amount - goal.current_amount

            message = (
                f"Financial goal '{goal.name}': "
                f"${goal.current_amount:.2f} of ${goal.target_amount:.2f} saved "
                f"({progress_percent:.1f}% complete). ${remaining:.2f} remaining."
            )

            await client.post(
                "http://ai_brain:9004/ingest/goal",
                json={
                    "name": goal.name,
                    "target_amount": goal.target_amount,
                    "current_amount": goal.current_amount,
                    "deadline": goal.deadline,
                    "message": message,
                },
                timeout=5,
            )
        except Exception as e:
            print(f"[AI_BRAIN] Failed to send goal: {e}")


def _parse_receipt_items(text: str):
    """
    Parse receipt text heuristically.
    Returns (items, detected_total) where detected_total is either a found 'total' on the receipt or None.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    items: List[Dict[str, object]] = []
    detected_total: Optional[float] = None

    price_re = re.compile(r"([-+]?\d+[.,]\d{2})")
    # scan for explicit total lines first
    for line in reversed(lines[-10:]):
        if re.search(r"\b(total|amount due|grand total|balance)\b", line, re.IGNORECASE):
            m = price_re.search(line)
            if m:
                detected_total = _normalize_price(m.group(1))
                break

    for line in lines:
        # skip obvious non-item lines
        if re.search(r"\b(total|subtotal|tax|change|amount due|visa|mastercard|card)\b", line, re.IGNORECASE):
            continue
        m = price_re.search(line)
        if m:
            price = _normalize_price(m.group(1))
            # try to extract a name by removing the price token and quantity markers
            name_part = price_re.sub('', line).strip()
            # remove leading quantity like '2 x' or '1x'
            name_part = re.sub(r"^\d+\s*[xX]\s*", '', name_part).strip()
            # remove trailing separators
            name_part = re.sub(r"[\-\.:,\s]+$", '', name_part)
            if not name_part:
                name_part = "item"
            items.append({"name": name_part, "price": float(price)})

    return items, detected_total


def _normalize_price(p: str) -> float:
    # converts strings like '1,99' or '1.99' into float
    s = p.replace(',', '.')
    # strip any non-numeric leading/trailing
    s = re.sub(r"[^0-9.\-+]", "", s)
    try:
        return float(s)
    except Exception:
        return 0.0


def _categorize_item(name: str) -> str:
    n = re.sub(r"[^a-z0-9 ]", " ", name.lower())

    # Expanded keyword mapping to cover many common categories
    mapping = {
        'groceries': [
            'milk', 'bread', 'cheese', 'apple', 'banana', 'eggs', 'butter', 'grocery',
            'supermarket', 'super market', 'aldi', 'lidl', 'wholefoods', 'tesco',
            'sainsbury', 'safeway',
        ],
        'produce': ['vegetable', 'vegetables', 'produce', 'lettuce', 'tomato', 'potato', 'onion', 'carrot', 'cucumber'],
        'bakery': ['bakery', 'baker', 'bread', 'croissant', 'baguette'],
        'coffee': ['coffee', 'latte', 'espresso', 'cappuccino', 'starbucks'],
        'restaurants': ['restaurant', 'cafe', 'diner', 'burger', 'pizza', 'bistro', 'barbecue', 'brasserie'],
        'fast_food': ['mcdonald', 'kfc', 'burgerking', 'burger king', 'tacobell', 'wendys', 'subway'],
        'alcohol': ['beer', 'wine', 'vodka', 'whiskey', 'liquor', 'spirits', 'brewery'],
        'beverages': ['soda', 'cola', 'juice', 'water', 'tea'],
        'fuel': ['gas', 'petrol', 'diesel', 'fuel', 'shell', 'bp', 'esso'],
        'transport': ['uber', 'taxi', 'train', 'bus', 'lyft', 'metro', 'tube'],
        'pharmacy': ['pharm', 'drug', 'pharmacy', 'rx', 'pharmacy'],
        'health': ['doctor', 'clinic', 'hospital', 'dentist', 'optician'],
        'beauty': ['cosmetic', 'cosmetics', 'makeup', 'salon', 'barber', 'hairdresser'],
        'clothing': ['clothing', 'apparel', 'shirt', 'jeans', 'dress', 'h&m', 'zara', 'uniqlo'],
        'electronics': ['iphone', 'samsung', 'laptop', 'computer', 'electronics', 'tv', 'headphone'],
        'entertainment': ['movie', 'cinema', 'netflix', 'spotify', 'concert', 'theatre', 'theater'],
        'utilities': ['electric', 'water', 'gas bill', 'internet', 'utility', 'utilities'],
        'subscription': ['subscription', 'monthly', 'membership', 'netflix', 'spotify', 'amazon prime'],
        'insurance': ['insurance', 'insurer', 'premium'],
        'home': ['ikea', 'home', 'furniture', 'mattress', 'homedepot', 'b&q'],
        'cleaning': ['detergent', 'cleaner', 'soap', 'bleach'],
        'baby': ['diaper', 'nappy', 'formula', 'baby'],
        'pet': ['pet', 'dog food', 'cat food', 'vet'],
        'garden': ['garden', 'plants', 'garden centre', 'nursery'],
        'sports': ['gym', 'fitness', 'sport', 'sports'],
        'books': ['book', 'barnes', 'bookstore', 'amazon books'],
        'other': []
    }

    # Quick heuristics: look for currency-like tokens to help classify
    tokens = n.split()

    # categorical shortcuts / precedence for common semantic keywords
    if re.search(r"\b(subscription|monthly|membership|renewal|auto renew)\b", n):
        return 'subscription'

    # merchant-specific shortcuts for fast food / well-known brands
    if re.search(r"\b(mcdonald|mcdonalds|kfc|burgerking|tacobell|wendys|subway)\b", n):
        return 'fast_food'

    # category precedence: specific merchant names or keywords first
    for cat, keys in mapping.items():
        for k in keys:
            if k in n:
                return cat

    # fallback heuristics
    if any(t.isdigit() for t in tokens):
        # numbers present usually indicate an item line; assume groceries
        return 'groceries'

    return 'other'
