import base64
import hashlib
import os
import sys
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from io import BytesIO

import httpx
import pytesseract
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Request, status
from fastapi.responses import JSONResponse
from PIL import Image
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session, select, create_engine, SQLModel

# Add shared directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shared.models import Transaction, ReceiptItem, Budget, Goal, IngestedDocument
from shared.utils.ocr import preprocess_image_for_ocr, parse_receipt_items, categorize_finance_item
from shared.config import get_service_url
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Add services directory to path for kilo_integration
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from kilo_integration import KiloNerve
from shared.utils.persona import get_quip
from autonomy import check_budgets

# Database setup
_default_db_path = Path(os.getenv("FINANCIAL_DB_PATH", "/tmp/kilo_financial.db"))
_default_db_path.parent.mkdir(parents=True, exist_ok=True)
db_url = os.getenv("DATABASE_URL", f"sqlite:///{_default_db_path}")
engine = create_engine(db_url, connect_args={"check_same_thread": False})

app = FastAPI(title="Kilo Financial Service - Gremlin Edition 😈")


# Initialize Kilo nerve
kilo_nerve = KiloNerve("financial")
@app.on_event("startup")
def on_startup():
    """Initialize database tables on startup."""
    SQLModel.metadata.create_all(engine)

@app.get("/health")
def health():
    return {"status": "ok", "message": "I'm keeping an eye on your shiny gold coins! 💰"}

# ========================================
# TRANSACTIONS CRUD
# ========================================

@app.get("/transactions")
def list_transactions():
    """List all transactions. I'm counting your pennies! 🪙"""
    with Session(engine) as session:
        return session.exec(select(Transaction)).all()

@app.get("/transactions/{tx_id}")
def get_transaction(tx_id: int):
    """Get a specific transaction."""
    with Session(engine) as session:
        tx = session.get(Transaction, tx_id)
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found!")
        return tx

@app.post("/transactions")
async def add_transaction(tx: Transaction, background_tasks: BackgroundTasks):
    """Create a new transaction."""
    tx.category = tx.category or _tx_categorize_item(tx.description or "")
    if tx.amount is not None:
        tx.transaction_type = "income" if tx.amount >= 0 else "expense"
    with Session(engine) as session:
        session.add(tx)
        session.commit()
        session.refresh(tx)
    
    # KILO INTEGRATION
    await kilo_nerve.send_observation(
        content=f"Transaction: ${abs(tx.amount):.2f} - {tx.description} ({tx.category})",
        priority="normal",
        metadata={"transaction_id": tx.id, "amount": tx.amount, "category": tx.category}
    )
    await kilo_nerve.emit_event("transaction_added", {"transaction_id": tx.id, "amount": tx.amount})
    
    return {
        "transaction": tx,
        "gremlin_message": f"Logged {tx.amount} for {tx.description}. Spending money is fun, isn't it? 💸"
    }

@app.put("/transactions/{tx_id}")
def update_transaction(tx_id: int, updated_tx: Transaction):
    """Update an existing transaction."""
    with Session(engine) as session:
        tx = session.get(Transaction, tx_id)
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found!")
        
        # Update fields
        for key, value in updated_tx.dict(exclude_unset=True).items():
            if key != "id":  # Don't update the ID
                setattr(tx, key, value)
        
        session.add(tx)
        session.commit()
        session.refresh(tx)
        return tx

@app.delete("/transactions/{tx_id}")
async def delete_transaction(tx_id: int):
    """Delete a transaction. It never happened! 🤫"""
    with Session(engine) as session:
        tx = session.get(Transaction, tx_id)
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found! I didn't hide it, I swear! 😇")
        session.delete(tx)
        session.commit()
        
        # KILO INTEGRATION
        await kilo_nerve.send_observation(f"Transaction deleted: ${abs(amount):.2f} - {desc}", priority="low")
        
        return {"message": f"Hehehe! I've shredded the evidence of that {tx.amount} purchase! ✂️"}

# ========================================
# BUDGETS CRUD
# ========================================

@app.get("/budgets")
def list_budgets():
    """List all budgets."""
    with Session(engine) as session:
        return session.exec(select(Budget)).all()

@app.get("/budgets/status")
def list_budget_status():
    """Autonomous budget status check with Gremlin flavor."""
    status = check_budgets(engine)
    over = [b for b in status if b["over_budget"]]
    message = get_quip("budget_warning") if over else get_quip("budget_ok")
    return {
        "budgets": status,
        "gremlin_message": message
    }

@app.get("/budgets/{budget_id}")
def get_budget(budget_id: int):
    """Get a specific budget."""
    with Session(engine) as session:
        budget = session.get(Budget, budget_id)
        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found!")
        return budget

@app.post("/budgets")
async def create_budget(budget: Budget):
    """Create a new budget."""
    with Session(engine) as session:
        session.add(budget)
        session.commit()
        session.refresh(budget)
        
        # KILO INTEGRATION
        await kilo_nerve.send_observation(
            content=f"Budget created: {budget.category} - ${budget.monthly_limit:.2f}/month",
            priority="normal",
            metadata={"budget_id": budget.id, "category": budget.category}
        )
        
        return budget

@app.put("/budgets/{budget_id}")
def update_budget(budget_id: int, updated_budget: Budget):
    """Update an existing budget."""
    with Session(engine) as session:
        budget = session.get(Budget, budget_id)
        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found!")
        
        # Update fields
        for key, value in updated_budget.dict(exclude_unset=True).items():
            if key != "id":
                setattr(budget, key, value)
        
        session.add(budget)
        session.commit()
        session.refresh(budget)
        return budget

@app.delete("/budgets/{budget_id}")
def delete_budget(budget_id: int):
    """Delete a budget. Freedom! 🕊️"""
    with Session(engine) as session:
        b = session.get(Budget, budget_id)
        if not b:
            raise HTTPException(status_code=404, detail="Budget not found! Maybe you never had one? 🤷‍♂️")
        session.delete(b)
        session.commit()
        return {"message": f"No more limits on '{b.category}'! Go wild! 😈"}

# ========================================
# GOALS CRUD
# ========================================

@app.get("/goals")
def list_goals():
    """List all financial goals."""
    with Session(engine) as session:
        return session.exec(select(Goal)).all()

@app.get("/goals/{goal_id}")
def get_goal(goal_id: int):
    """Get a specific goal."""
    with Session(engine) as session:
        goal = session.get(Goal, goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found!")
        return goal

@app.post("/goals")
async def create_goal(goal: Goal):
    """Create a new financial goal."""
    with Session(engine) as session:
        session.add(goal)
        session.commit()
        session.refresh(goal)
        
        # KILO INTEGRATION
        await kilo_nerve.send_observation(
            content=f"Goal created: {goal.name} - Target: ${goal.target_amount:.2f}",
            priority="normal",
            metadata={"goal_id": goal.id, "goal_name": goal.name}
        )
        
        return goal

@app.put("/goals/{goal_id}")
def update_goal(goal_id: int, updated_goal: Goal):
    """Update an existing goal."""
    with Session(engine) as session:
        goal = session.get(Goal, goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found!")
        
        # Update fields
        for key, value in updated_goal.dict(exclude_unset=True).items():
            if key != "id":
                setattr(goal, key, value)
        
        session.add(goal)
        session.commit()
        session.refresh(goal)
        return goal

@app.delete("/goals/{goal_id}")
def delete_goal(goal_id: int):
    """Delete a goal. Giving up is easy! 😉"""
    with Session(engine) as session:
        g = session.get(Goal, goal_id)
        if not g:
            raise HTTPException(status_code=404, detail="Goal not found! I didn't steal it! 🤥")
        session.delete(g)
        session.commit()
        return {"message": f"Goal '{g.name}' has been tossed into the digital abyss! 🕳️"}

# ========================================
# BANK ACCOUNTS (Placeholder)
# ========================================

@app.get("/bank_accounts")
def list_bank_accounts():
    """List bank accounts - placeholder for future implementation."""
    # TODO: Add BankAccount model and implement this properly
    return []

# ========================================
# Legacy Routes (for backward compatibility)
# ========================================

@app.get("/")
def root_list_transactions():
    """Legacy route - redirects to /transactions"""
    return list_transactions()

@app.post("/")
def root_add_transaction(tx: Transaction, background_tasks: BackgroundTasks):
    """Legacy route - redirects to POST /transactions"""
    return add_transaction(tx, background_tasks)

@app.delete("/transaction/{tx_id}")
def legacy_delete_transaction(tx_id: int):
    """Legacy route - redirects to DELETE /transactions/{tx_id}"""
    return delete_transaction(tx_id)

@app.delete("/budget/{budget_id}")
def legacy_delete_budget(budget_id: int):
    """Legacy route - redirects to DELETE /budgets/{budget_id}"""
    return delete_budget(budget_id)

@app.delete("/goal/{goal_id}")
def legacy_delete_goal(goal_id: int):
    """Legacy route - redirects to DELETE /goals/{goal_id}"""
    return delete_goal(goal_id)

# ========================================
# Helper Functions
# ========================================

def _tx_categorize_item(name: str) -> str:
    lowered = (name or "").lower()
    mapping = [
        ("coffee", ["starbucks", "latte", "coffee"]),
        ("electronics", ["electronics", "tv", "laptop"]),
        ("transport", ["uber", "lyft", "trip", "taxi"]),
    ]
    for cat, keys in mapping:
        if any(k in lowered for k in keys):
            return cat
    return "miscellaneous"
