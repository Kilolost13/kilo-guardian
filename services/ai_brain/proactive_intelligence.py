"""
Proactive Intelligence Layer for Kilo AI Brain
Makes Kilo contextually aware and proactive by checking:
- Medications due
- Habits not logged
- Pending reminders
- Security alerts
- Financial concerns
- System health issues
"""
import httpx
import datetime
import asyncio
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Service URLs
SERVICE_URLS = {
    "meds": "http://kilo-meds:9000",
    "habits": "http://kilo-habits:9000",
    "reminder": "http://kilo-reminder:9002",
    "security_monitor": "http://security-monitor:8005",
    "financial": "http://kilo-financial:9005",
    "gateway": "http://kilo-gateway:8000"
}


async def check_medications() -> Dict[str, Any]:
    """Check if user has pending medications based on schedule"""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            # Get all medications
            resp = await client.get(f"{SERVICE_URLS['meds']}/meds/")
            if resp.status_code != 200:
                return {"pending": False, "meds": [], "error": None}

            meds = resp.json()
            if not meds:
                return {"pending": False, "meds": [], "error": None}

            now = datetime.datetime.now()
            current_time = now.strftime("%H:%M")
            current_hour = now.hour

            pending_meds = []
            for med in meds:
                med_times = med.get("time", "").split(",")
                for med_time in med_times:
                    med_time = med_time.strip()
                    if ":" in med_time:
                        med_hour = int(med_time.split(":")[0])
                        # If medication time has passed in last 2 hours and not confirmed
                        if 0 <= (current_hour - med_hour) <= 2:
                            pending_meds.append({
                                "name": med.get("name"),
                                "dosage": med.get("dosage"),
                                "time": med_time,
                                "frequency": med.get("frequency")
                            })

            return {
                "pending": len(pending_meds) > 0,
                "meds": pending_meds,
                "current_time": current_time,
                "error": None
            }
    except Exception as e:
        logger.warning(f"Failed to check medications: {e}")
        return {"pending": False, "meds": [], "error": str(e)}


async def check_habits() -> Dict[str, Any]:
    """Check if user has logged today's habits"""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            # Get all habits
            resp = await client.get(f"{SERVICE_URLS['habits']}/habits/")
            if resp.status_code != 200:
                return {"not_logged": False, "habits": [], "error": None}

            habits = resp.json()
            if not habits:
                return {"not_logged": False, "habits": [], "error": None}

            today = datetime.date.today().isoformat()

            # Check completions for today
            resp = await client.get(f"{SERVICE_URLS['habits']}/habits/completions")
            if resp.status_code == 200:
                completions = resp.json()
                completed_today = [c for c in completions if c.get("date", "").startswith(today)]
                completed_habit_ids = {c.get("habit_id") for c in completed_today}

                not_logged = [
                    {"name": h.get("name"), "frequency": h.get("frequency")}
                    for h in habits
                    if h.get("id") not in completed_habit_ids
                ]

                return {
                    "not_logged": len(not_logged) > 0,
                    "habits": not_logged,
                    "total_habits": len(habits),
                    "completed": len(completed_habit_ids),
                    "error": None
                }

            return {"not_logged": False, "habits": [], "error": None}
    except Exception as e:
        logger.warning(f"Failed to check habits: {e}")
        return {"not_logged": False, "habits": [], "error": str(e)}


async def check_pending_reminders() -> Dict[str, Any]:
    """Check for pending reminders"""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{SERVICE_URLS['reminder']}/notifications/pending")
            if resp.status_code == 200:
                reminders = resp.json()
                if isinstance(reminders, list) and len(reminders) > 0:
                    return {
                        "pending": True,
                        "count": len(reminders),
                        "reminders": [r.get("text", str(r)) for r in reminders[:3]],
                        "error": None
                    }
            return {"pending": False, "count": 0, "reminders": [], "error": None}
    except Exception as e:
        logger.warning(f"Failed to check reminders: {e}")
        return {"pending": False, "count": 0, "reminders": [], "error": str(e)}


async def check_security() -> Dict[str, Any]:
    """Check for security alerts or unusual activity"""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{SERVICE_URLS['security_monitor']}/stats")
            if resp.status_code == 200:
                stats = resp.json().get("stats", {})

                alerts = []
                if stats.get("vulnerabilities", 0) > 0:
                    alerts.append(f"{stats['vulnerabilities']} vulnerabilities detected")
                if stats.get("blocked_threats", 0) > 0:
                    alerts.append(f"{stats['blocked_threats']} threats blocked")
                if stats.get("open_ports", 0) > 10:
                    alerts.append(f"{stats['open_ports']} open ports found")

                return {
                    "alerts": len(alerts) > 0,
                    "messages": alerts,
                    "stats": stats,
                    "error": None
                }
            return {"alerts": False, "messages": [], "stats": {}, "error": None}
    except Exception as e:
        logger.warning(f"Failed to check security: {e}")
        return {"alerts": False, "messages": [], "stats": {}, "error": str(e)}


async def check_financial() -> Dict[str, Any]:
    """Check for financial alerts or budget concerns"""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{SERVICE_URLS['financial']}/financial/budgets")
            if resp.status_code == 200:
                budgets = resp.json()

                alerts = []
                for budget in budgets:
                    spent = budget.get("spent", 0)
                    limit = budget.get("limit", 0)
                    if limit > 0:
                        pct = (spent / limit) * 100
                        if pct >= 90:
                            alerts.append(f"{budget['category']}: {pct:.0f}% of budget used")

                return {
                    "alerts": len(alerts) > 0,
                    "messages": alerts,
                    "budgets": budgets,
                    "error": None
                }
            return {"alerts": False, "messages": [], "budgets": [], "error": None}
    except Exception as e:
        logger.warning(f"Failed to check financial: {e}")
        return {"alerts": False, "messages": [], "budgets": [], "error": str(e)}


async def check_system_health() -> Dict[str, Any]:
    """Check overall system health"""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{SERVICE_URLS['gateway']}/admin/status")
            if resp.status_code == 200:
                status = resp.json()

                down_services = []
                for service, health in status.items():
                    if isinstance(health, dict) and not health.get("ok", False):
                        down_services.append(service)

                return {
                    "healthy": len(down_services) == 0,
                    "down_services": down_services,
                    "total_checked": len(status),
                    "error": None
                }
            return {"healthy": True, "down_services": [], "total_checked": 0, "error": None}
    except Exception as e:
        logger.warning(f"Failed to check system health: {e}")
        return {"healthy": True, "down_services": [], "total_checked": 0, "error": str(e)}


async def gather_proactive_context() -> Dict[str, Any]:
    """
    Gather ALL contextual information from microservices in parallel
    Returns a comprehensive context dictionary
    """
    now = datetime.datetime.now()

    # Run all checks in parallel for speed
    results = await asyncio.gather(
        check_medications(),
        check_habits(),
        check_pending_reminders(),
        check_security(),
        check_financial(),
        check_system_health(),
        return_exceptions=True
    )

    # Unpack results (handle any exceptions)
    meds_status = results[0] if not isinstance(results[0], Exception) else {"pending": False, "meds": []}
    habits_status = results[1] if not isinstance(results[1], Exception) else {"not_logged": False, "habits": []}
    reminders = results[2] if not isinstance(results[2], Exception) else {"pending": False, "reminders": []}
    security = results[3] if not isinstance(results[3], Exception) else {"alerts": False, "messages": []}
    financial = results[4] if not isinstance(results[4], Exception) else {"alerts": False, "messages": []}
    system = results[5] if not isinstance(results[5], Exception) else {"healthy": True, "down_services": []}

    return {
        "timestamp": now.isoformat(),
        "current_time": now.strftime("%H:%M"),
        "current_date": now.strftime("%Y-%m-%d"),
        "time_of_day": get_time_of_day(now),
        "medications": meds_status,
        "habits": habits_status,
        "reminders": reminders,
        "security": security,
        "financial": financial,
        "system_health": system
    }


def get_time_of_day(dt: datetime.datetime) -> str:
    """Return 'morning', 'afternoon', 'evening', or 'night'"""
    hour = dt.hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


def build_context_prompt(context: Dict[str, Any]) -> str:
    """
    Convert proactive context into a system prompt that makes Kilo aware
    This gets prepended to the LLM prompt to make it contextually aware
    """
    prompt_parts = ["CONTEXTUAL AWARENESS (Check these items and mention if relevant):"]

    # Time context
    prompt_parts.append(f"Current time: {context['current_time']} ({context['time_of_day']})")

    # Medications
    if context["medications"]["pending"]:
        med_list = ", ".join([f"{m['name']} ({m['dosage']})" for m in context["medications"]["meds"]])
        prompt_parts.append(f"⚕️ PENDING MEDICATIONS: User should take {med_list}. Ask if they've taken their meds.")

    # Habits
    if context["habits"]["not_logged"]:
        total = context["habits"]["total_habits"]
        completed = context["habits"].get("completed", 0)
        habit_names = ", ".join([h["name"] for h in context["habits"]["habits"][:3]])
        prompt_parts.append(f"📋 HABITS NOT LOGGED: User has {total - completed}/{total} habits not logged today ({habit_names}). Remind them to log habits.")

    # Reminders
    if context["reminders"]["pending"]:
        count = context["reminders"]["count"]
        reminder_list = ", ".join(context["reminders"]["reminders"])
        prompt_parts.append(f"🔔 PENDING REMINDERS ({count}): {reminder_list}")

    # Security
    if context["security"]["alerts"]:
        alert_list = ", ".join(context["security"]["messages"])
        prompt_parts.append(f"🔒 SECURITY ALERTS: {alert_list}")

    # Financial
    if context["financial"]["alerts"]:
        alert_list = ", ".join(context["financial"]["messages"])
        prompt_parts.append(f"💰 FINANCIAL ALERTS: {alert_list}")

    # System health
    if not context["system_health"]["healthy"]:
        down = ", ".join(context["system_health"]["down_services"])
        prompt_parts.append(f"⚠️ SYSTEM ISSUES: Services down: {down}")

    if len(prompt_parts) == 1:
        # No alerts, add positive context
        prompt_parts.append("✅ All systems normal, no pending tasks.")

    prompt_parts.append("\nRESPOND NATURALLY: Mention relevant items conversationally, don't just list them.")

    return "\n".join(prompt_parts)


def should_be_proactive(message: str) -> bool:
    """
    Determine if Kilo should be proactive for this message
    Skip proactive checks for technical/system commands
    """
    # Skip for technical commands
    skip_keywords = ["/remember", "/recall", "/forget", "/help", "test", "debug"]
    message_lower = message.lower()

    for keyword in skip_keywords:
        if keyword in message_lower:
            return False

    return True
