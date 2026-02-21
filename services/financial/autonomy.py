import datetime
from sqlmodel import Session, select
from shared.models import Transaction, Budget

def check_budgets(engine):
    with Session(engine) as session:
        budgets = session.exec(select(Budget)).all()
        now = datetime.datetime.utcnow()
        # Get first of month
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        
        alerts = []
        for b in budgets:
            if not b or not b.category:
                continue
                
            # Sum expenses for this category this month
            txs = session.exec(
                select(Transaction).where(
                    Transaction.category == b.category,
                    Transaction.date >= month_start,
                    Transaction.transaction_type == "expense"
                )
            ).all()
            
            total_spent = sum(abs(tx.amount) for tx in txs)
            
            limit = b.monthly_limit or 0
            
            alerts.append({
                "category": b.category,
                "limit": limit,
                "spent": total_spent,
                "remaining": limit - total_spent,
                "over_budget": total_spent > limit,
                "usage_percent": round((total_spent / limit) * 100, 2) if limit > 0 else 0
            })
        return alerts