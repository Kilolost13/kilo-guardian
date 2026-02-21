"""
Kilo's Tool Definitions - Function calling schemas for Gemini
All microservice integrations for the AI Brain
"""

from typing import Dict, Any, List
import httpx
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# TOOL SCHEMA DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════

KILO_FUNCTION_DECLARATIONS = [
    {
        "name": "get_spending_summary",
        "description": "Get Kyle's spending data. Returns total spent, breakdown by category, and transaction count. Use this when Kyle asks about spending, budgets, or money. By default shows current month only.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Optional: filter by specific category"
                },
                "days_back": {
                    "type": "number",
                    "description": "Number of days to look back (e.g., 15 for last 15 days, 30 for last month). Defaults to current month only.",
                    "default": 0
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
                "amount": {
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
        "description": "Record that Kyle took a medication dose. Use when Kyle says he took his meds or a specific medication. If no specific med is named but Kyle says 'I took my meds', log all of them.",
        "parameters": {
            "type": "object",
            "properties": {
                "medication_name": {
                    "type": "string",
                    "description": "Name of the medication taken (must match existing medication). Use 'all' to log all current medications."
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
        "name": "log_habit_completion",
        "description": "Mark a habit as completed for today. Use when Kyle says he completed a habit, finished a workout, meditated, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "habit_name": {
                    "type": "string",
                    "description": "Name of the habit to mark complete (e.g., 'morning workout', 'meditation', 'reading')"
                }
            },
            "required": ["habit_name"]
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
        "name": "create_reminder",
        "description": "Create a new reminder for Kyle. Use when Kyle asks you to remind him about something. For daily recurring reminders use recurrence='daily' and a time like '15:00'.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "What to remind Kyle about (e.g., 'Take afternoon meds', 'Pay electric bill')"
                },
                "when": {
                    "type": "string",
                    "description": "When to remind. RULES: (1) For one-time reminders use full ISO datetime including date: '2026-02-22T10:00:00'. NEVER use time-only for one-time. (2) For daily recurring: time-only like '15:00'. Today is 2026-02-21, so 'tomorrow at 10am' = '2026-02-22T10:00:00'."
                },
                "recurrence": {
                    "type": "string",
                    "description": "Set to 'daily' for daily reminders, 'weekly' for weekly, or omit for one-time",
                    "enum": ["daily", "weekly", "none"]
                }
            },
            "required": ["text", "when"]
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
    },
    {
        "name": "add_library_entry",
        "description": "Save important information, facts, or advice to the Library of Truth for future reference. Use when Kyle says 'remember this', 'save this', or when you discover a useful fact worth keeping.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Short title for the entry (e.g., 'Buspirone Food Interaction')"
                },
                "content": {
                    "type": "string",
                    "description": "The information to save"
                },
                "category": {
                    "type": "string",
                    "description": "Category for the entry",
                    "enum": ["medical", "health", "finance", "psychology", "cooking", "security", "training", "general"]
                }
            },
            "required": ["title", "content", "category"]
        }
    },
    {
        "name": "search_web",
        "description": "Search the internet for current information, news, weather, prices, or facts not in the Library of Truth. Use when Kyle asks about current events, real-time data, or external information.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g., 'Dallas weather today', 'Bitcoin current price', 'latest SpaceX news')"
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

        elif tool_name == "log_habit_completion":
            return await _log_habit_completion(parameters)

        elif tool_name == "get_upcoming_reminders":
            return await _get_upcoming_reminders(parameters)

        elif tool_name == "create_reminder":
            return await _create_reminder(parameters)

        elif tool_name == "search_library":
            return await _search_library(parameters)

        elif tool_name == "add_library_entry":
            return await _add_library_entry(parameters)

        elif tool_name == "search_web":
            return await _search_web(parameters)

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        logger.error(f"Tool execution error ({tool_name}): {e}", exc_info=True)
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════
# INDIVIDUAL TOOL IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════════════════

def parse_transaction_date(date_str: str) -> datetime:
    """Parse transaction date in multiple formats"""
    if not date_str:
        return datetime(1970, 1, 1)

    # Try YYYY-MM-DD format first (current format)
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        pass

    # Try MM/DD/YYYY format
    try:
        return datetime.strptime(date_str, "%m/%d/%Y")
    except ValueError:
        pass

    # Default fallback
    return datetime(1970, 1, 1)


async def _get_spending_summary(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get spending data from financial microservice"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get("http://kilo-financial:9005/transactions?limit=2000")

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

            # Filter by date
            days_back = params.get("days_back", 0)
            if days_back > 0:
                cutoff = datetime.now() - timedelta(days=days_back)
                transactions = [
                    t for t in transactions
                    if parse_transaction_date(t.get("date", "")) >= cutoff
                ]
            else:
                # Default: current month only
                current_month = datetime.now().month
                current_year = datetime.now().year
                transactions = [
                    t for t in transactions
                    if parse_transaction_date(t.get("date", "")).month == current_month
                    and parse_transaction_date(t.get("date", "")).year == current_year
                ]

            # Calculate totals
            total_spent = 0
            category_totals = {}

            for txn in transactions:
                txn_type = txn.get("transaction_type", "expense")
                if txn_type != "expense":
                    continue

                amount = txn.get("amount", 0)
                total_spent += amount
                category = txn.get("category", "uncategorized")
                category_totals[category] = category_totals.get(category, 0) + amount

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
            resp = await client.get("http://kilo-meds:9000/")

            if resp.status_code != 200:
                return {"medications": [], "message": "No medications tracked yet"}

            data = resp.json()
            meds = data.get("meds", data) if isinstance(data, dict) else data
            if not meds:
                return {"medications": [], "message": "No medications in system"}

            return {"medications": meds, "count": len(meds)}

    except Exception as e:
        logger.error(f"get_medications error: {e}")
        return {"error": str(e)}


async def _log_medication_taken(params: Dict[str, Any]) -> Dict[str, Any]:
    """Log medication dose in meds microservice"""
    try:
        med_name = params.get("medication_name", "")
        if not med_name:
            return {"error": "Missing medication_name parameter"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get all meds
            meds_resp = await client.get("http://kilo-meds:9000/")
            if meds_resp.status_code != 200:
                return {"error": "Could not fetch medications list"}

            meds_data = meds_resp.json()
            meds = meds_data.get("meds", meds_data) if isinstance(meds_data, dict) else meds_data

            # "all" = log everything
            if med_name.lower() == "all":
                results = []
                for med in meds:
                    log_resp = await client.post(f"http://kilo-meds:9000/take/{med['id']}")
                    results.append({
                        "medication": med.get("name"),
                        "success": log_resp.status_code in [200, 201]
                    })
                return {"success": True, "logged": results, "message": f"Logged all {len(results)} medications"}

            # Find by name (case-insensitive, partial match)
            med = next((m for m in meds if med_name.lower() in m.get("name", "").lower()), None)

            if not med:
                return {"error": f"Medication '{med_name}' not found. Available: {', '.join([m.get('name', '') for m in meds])}"}

            log_resp = await client.post(f"http://kilo-meds:9000/take/{med['id']}")

            if log_resp.status_code in [200, 201]:
                return {
                    "success": True,
                    "medication": med.get("name"),
                    "message": f"Logged dose of {med.get('name')}"
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
            resp = await client.get("http://kilo-habits:9000/")

            if resp.status_code != 200:
                return {"habits": [], "message": "No habits tracked yet"}

            data = resp.json()
            habits = data.get("habits", data) if isinstance(data, dict) else data
            if not habits:
                return {"habits": [], "message": "No habits in system"}

            return {"habits": habits, "count": len(habits)}

    except Exception as e:
        logger.error(f"get_habits error: {e}")
        return {"error": str(e)}


async def _log_habit_completion(params: Dict[str, Any]) -> Dict[str, Any]:
    """Mark a habit as completed today"""
    try:
        habit_name = params.get("habit_name", "")
        if not habit_name:
            return {"error": "Missing habit_name parameter"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get all habits to find the ID
            habits_resp = await client.get("http://kilo-habits:9000/")
            if habits_resp.status_code != 200:
                return {"error": "Could not fetch habits list"}

            data = habits_resp.json()
            habits = data.get("habits", data) if isinstance(data, dict) else data

            # Find by name (case-insensitive, partial match)
            habit = next(
                (h for h in habits if habit_name.lower() in h.get("name", "").lower()),
                None
            )

            if not habit:
                available = ", ".join([h.get("name", "") for h in habits])
                return {"error": f"Habit '{habit_name}' not found. Available: {available}"}

            # Mark complete
            complete_resp = await client.post(f"http://kilo-habits:9000/complete/{habit['id']}")

            if complete_resp.status_code in [200, 201]:
                return {
                    "success": True,
                    "habit": habit.get("name"),
                    "message": f"Marked '{habit.get('name')}' as done for today"
                }
            else:
                body = complete_resp.text
                return {"error": f"Failed to log habit (HTTP {complete_resp.status_code}): {body}"}

    except Exception as e:
        logger.error(f"log_habit_completion error: {e}")
        return {"error": str(e)}


async def _get_upcoming_reminders(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get reminders from reminder microservice"""
    try:
        limit = params.get("limit", 10)

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"http://kilo-reminder:9002/notifications/pending?limit={limit}")

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


async def _create_reminder(params: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new reminder in the reminder microservice"""
    try:
        text = params.get("text", "")
        when = params.get("when", "")
        recurrence = params.get("recurrence", "none")

        if not text or not when:
            return {"error": "Missing required fields: text and when"}

        # Clean up recurrence
        if recurrence == "none" or not recurrence:
            recurrence = None

        payload = {
            "text": text,
            "when": when,
            "timezone": "America/Chicago"
        }
        if recurrence:
            payload["recurrence"] = recurrence

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post("http://kilo-reminder:9002/", json=payload)

            if resp.status_code in [200, 201]:
                data = resp.json()
                return {
                    "success": True,
                    "reminder_id": data.get("id"),
                    "text": text,
                    "when": when,
                    "recurrence": recurrence,
                    "message": f"Created reminder: '{text}' at {when}"
                }
            else:
                return {"error": f"Failed to create reminder (HTTP {resp.status_code}): {resp.text}"}

    except Exception as e:
        logger.error(f"create_reminder error: {e}")
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


async def _add_library_entry(params: Dict[str, Any]) -> Dict[str, Any]:
    """Add an entry to the Library of Truth"""
    try:
        title = params.get("title", "")
        content = params.get("content", "")
        category = params.get("category", "general")

        if not title or not content:
            return {"error": "Missing required fields: title and content"}

        payload = {
            "title": title,
            "content": content,
            "category": category,
            "source": "Kilo AI"
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post("http://kilo-library:9006/", json=payload)

            if resp.status_code in [200, 201]:
                return {
                    "success": True,
                    "message": f"Saved '{title}' to Library of Truth under {category}"
                }
            else:
                return {"error": f"Failed to save entry (HTTP {resp.status_code}): {resp.text}"}

    except Exception as e:
        logger.error(f"add_library_entry error: {e}")
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════
# WEB SEARCH FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

async def _search_web(params: Dict[str, Any]) -> Dict[str, Any]:
    """Search the internet using Brave Search API"""
    try:
        import os

        query = params.get("query", "")
        if not query:
            return {"error": "Missing query parameter"}

        api_key = os.environ.get("BRAVE_API_KEY", "")
        if not api_key:
            return {
                "error": "Web search not configured (BRAVE_API_KEY missing). I can check the Library of Truth instead, or tell me what you need and I'll do my best from what I know."
            }

        logger.info(f"🌐 Searching web for: {query}")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={
                    "q": query,
                    "count": 5,
                    "search_lang": "en",
                    "country": "us"
                },
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": api_key
                }
            )

            if resp.status_code == 401:
                return {"error": "Invalid BRAVE_API_KEY. Check your API key."}
            elif resp.status_code == 429:
                return {"error": "Rate limit exceeded. You've used your monthly quota."}
            elif resp.status_code != 200:
                return {"error": f"Search failed with status {resp.status_code}"}

            data = resp.json()

            results = []
            web_results = data.get("web", {}).get("results", [])

            for result in web_results[:5]:
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "description": result.get("description", ""),
                    "age": result.get("age", "")
                })

            if not results:
                return {
                    "results": [],
                    "message": f"No results found for '{query}'",
                    "query": query
                }

            logger.info(f"✅ Found {len(results)} results for: {query}")

            return {
                "results": results,
                "query": query,
                "count": len(results)
            }

    except Exception as e:
        logger.error(f"search_web error: {e}", exc_info=True)
        return {"error": str(e)}
