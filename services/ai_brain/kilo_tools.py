"""
Kilo's Tool Definitions - Function calling schemas for Gemini
All microservice integrations for the AI Brain
"""

from typing import Dict, Any, List
import httpx
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# TOOL SCHEMA DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════

KILO_FUNCTION_DECLARATIONS = [
    {
        "name": "get_spending_summary",
        "description": "Get Kyle's spending data for the current month. Returns total spent, breakdown by category, and transaction count. Use this when Kyle asks about spending, budgets, or money.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Optional: filter by specific category (streaming, food, utilities, entertainment, shopping, subscriptions, bills, transportation, health, other)",
                    "enum": ["streaming", "food", "utilities", "entertainment", "shopping", "subscriptions", "bills", "transportation", "health", "other"]
                }
            }
        }
    },
    {
        "name": "get_budget_status",
        "description": "Get Kyle's budget limits and current spending against those budgets. Shows budget amount, amount spent, amount remaining, and percentage used for each category.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "create_budget",
        "description": "Create a new monthly budget limit for a spending category. Use this when Kyle wants to set spending limits.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Budget category name",
                    "enum": ["streaming", "food", "utilities", "entertainment", "shopping", "subscriptions", "bills", "transportation", "health", "other"]
                },
                "amount": {  # Note: sent as monthly_limit to backend
                    "type": "number",
                    "description": "Monthly budget limit in dollars (e.g., 100.00)"
                },
                "period": {
                    "type": "string",
                    "description": "Budget period",
                    "enum": ["monthly"],
                    "default": "monthly"
                }
            },
            "required": ["category", "amount"]
        }
    },
    {
        "name": "get_medications",
        "description": "Get Kyle's current medications including names, doses, schedules, and adherence tracking. Use when Kyle asks about meds or pills.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "log_medication_taken",
        "description": "Record that Kyle took a medication dose. Use when Kyle says he took his meds or a specific medication.",
        "parameters": {
            "type": "object",
            "properties": {
                "medication_name": {
                    "type": "string",
                    "description": "Name of the medication taken (must match existing medication)"
                }
            },
            "required": ["medication_name"]
        }
    },
    {
        "name": "get_habits",
        "description": "Get Kyle's tracked habits including completion rates, streaks, and progress. Use when Kyle asks about habits or routines.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_upcoming_reminders",
        "description": "Get Kyle's upcoming reminders and notifications. Shows reminder text, when it's due, and status.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of reminders to return (default 10)",
                    "default": 10
                }
            }
        }
    },
    {
        "name": "search_library",
        "description": "Search the Library of Truth for verified facts about medical advice, health guidelines, financial wisdom, cooking safety, and psychology principles. Use when Kyle asks factual questions.",
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


# ═══════════════════════════════════════════════════════════════════════════
# TOOL EXECUTION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

async def execute_tool_call(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a function call to a microservice.
    Returns structured data that Gemini will use to generate the final response.
    """
    try:
        logger.info(f"🔧 Executing tool: {tool_name} with params: {parameters}")

        if tool_name == "get_spending_summary":
            return await _get_spending_summary(parameters)

        elif tool_name == "get_budget_status":
            return await _get_budget_status()

        elif tool_name == "create_budget":
            return await _create_budget(parameters)

        elif tool_name == "get_medications":
            return await _get_medications()

        elif tool_name == "log_medication_taken":
            return await _log_medication_taken(parameters)

        elif tool_name == "get_habits":
            return await _get_habits()

        elif tool_name == "get_upcoming_reminders":
            return await _get_upcoming_reminders(parameters)

        elif tool_name == "search_library":
            return await _search_library(parameters)

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        logger.error(f"Tool execution error ({tool_name}): {e}", exc_info=True)
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════
# INDIVIDUAL TOOL IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════════════════

async def _get_spending_summary(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get spending data from financial microservice"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get all transactions
            resp = await client.get("http://kilo-financial:9005/transactions")

            if resp.status_code != 200:
                return {"error": "Could not fetch transaction data", "status_code": resp.status_code}

            data = resp.json()
            transactions = data if isinstance(data, list) else data.get("transactions", [])

            if not transactions:
                return {
                    "total_spent": 0,
                    "transaction_count": 0,
                    "by_category": {},
                    "message": "No transactions found"
                }

            # Calculate totals
            total_spent = 0
            category_totals = {}

            for txn in transactions:
                amount = txn.get("amount", 0)
                if amount < 0:  # Expenses are negative
                    spent = abs(amount)
                    total_spent += spent
                    category = txn.get("category", "uncategorized")
                    category_totals[category] = category_totals.get(category, 0) + spent

            # Filter by category if requested
            requested_category = params.get("category")
            if requested_category:
                return {
                    "category": requested_category,
                    "spent": category_totals.get(requested_category, 0),
                    "transaction_count": len([t for t in transactions if t.get("category") == requested_category]),
                    "total_spent": total_spent
                }

            return {
                "total_spent": round(total_spent, 2),
                "by_category": {k: round(v, 2) for k, v in sorted(category_totals.items(), key=lambda x: x[1], reverse=True)},
                "transaction_count": len(transactions)
            }

    except Exception as e:
        logger.error(f"get_spending_summary error: {e}")
        return {"error": str(e)}


async def _get_budget_status() -> Dict[str, Any]:
    """Get budget status from financial microservice"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("http://kilo-financial:9005/budgets")

            if resp.status_code != 200:
                return {"budgets": [], "message": "No budgets set up yet"}

            budgets = resp.json()
            if not budgets:
                return {"budgets": [], "message": "No budgets created yet"}

            return {"budgets": budgets, "count": len(budgets)}

    except Exception as e:
        logger.error(f"get_budget_status error: {e}")
        return {"error": str(e)}


async def _create_budget(params: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new budget in financial microservice"""
    try:
        category = params.get("category")
        amount = params.get("amount")
        period = params.get("period", "monthly")

        if not category or not amount:
            return {"error": "Missing required parameters: category and amount"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "http://kilo-financial:9005/budgets",
                json={
                    "category": category,
                    "monthly_limit": float(amount)
                }
            )

            if resp.status_code in [200, 201]:
                return {
                    "success": True,
                    "budget": resp.json(),
                    "message": f"Created ${amount}/month budget for {category}"
                }
            else:
                return {"error": f"Failed to create budget (HTTP {resp.status_code})"}

    except Exception as e:
        logger.error(f"create_budget error: {e}")
        return {"error": str(e)}


async def _get_medications() -> Dict[str, Any]:
    """Get medications from meds microservice"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("http://kilo-meds:9000/meds/")

            if resp.status_code != 200:
                return {"medications": [], "message": "No medications tracked yet"}

            meds = resp.json()
            if not meds:
                return {"medications": [], "message": "No medications in system"}

            return {"medications": meds, "count": len(meds)}

    except Exception as e:
        logger.error(f"get_medications error: {e}")
        return {"error": str(e)}


async def _log_medication_taken(params: Dict[str, Any]) -> Dict[str, Any]:
    """Log medication dose in meds microservice"""
    try:
        med_name = params.get("medication_name")
        if not med_name:
            return {"error": "Missing medication_name parameter"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            # First, get all meds to find the ID
            meds_resp = await client.get("http://kilo-meds:9000/meds/")
            if meds_resp.status_code != 200:
                return {"error": "Could not fetch medications list"}

            meds = meds_resp.json()
            # Find medication by name (case-insensitive)
            med = next((m for m in meds if m.get("name", "").lower() == med_name.lower()), None)

            if not med:
                return {"error": f"Medication '{med_name}' not found. Available: {', '.join([m.get('name', '') for m in meds])}"}

            # Log the dose
            log_resp = await client.post(f"http://kilo-meds:9000/meds/{med['id']}/take")

            if log_resp.status_code in [200, 201]:
                return {
                    "success": True,
                    "medication": med_name,
                    "message": f"Logged dose of {med_name}"
                }
            else:
                return {"error": f"Failed to log medication (HTTP {log_resp.status_code})"}

    except Exception as e:
        logger.error(f"log_medication_taken error: {e}")
        return {"error": str(e)}


async def _get_habits() -> Dict[str, Any]:
    """Get habits from habits microservice"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("http://kilo-habits:9000/habits/")

            if resp.status_code != 200:
                return {"habits": [], "message": "No habits tracked yet"}

            habits = resp.json()
            if not habits:
                return {"habits": [], "message": "No habits in system"}

            return {"habits": habits, "count": len(habits)}

    except Exception as e:
        logger.error(f"get_habits error: {e}")
        return {"error": str(e)}


async def _get_upcoming_reminders(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get reminders from reminder microservice"""
    try:
        limit = params.get("limit", 10)

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"http://kilo-reminder:9002/reminder/notifications/pending?limit={limit}")

            if resp.status_code != 200:
                return {"reminders": [], "message": "No pending reminders"}

            data = resp.json()
            reminders = data if isinstance(data, list) else data.get("reminders", [])

            if not reminders:
                return {"reminders": [], "message": "No pending reminders"}

            return {"reminders": reminders, "count": len(reminders)}

    except Exception as e:
        logger.error(f"get_upcoming_reminders error: {e}")
        return {"error": str(e)}


async def _search_library(params: Dict[str, Any]) -> Dict[str, Any]:
    """Search Library of Truth"""
    try:
        query = params.get("query", "")
        if not query:
            return {"error": "Missing query parameter"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"http://kilo-library:9006/search?q={query}")

            if resp.status_code != 200:
                return {"results": [], "message": "No results found"}

            data = resp.json()
            results = data if isinstance(data, list) else data.get("results", [])

            return {"results": results, "count": len(results)}

    except Exception as e:
        logger.error(f"search_library error: {e}")
        return {"error": str(e)}
