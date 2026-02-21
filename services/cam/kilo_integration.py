"""
Kilo Integration Module
Add this to each microservice to connect it to Kilo's nervous system.
"""
import httpx
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Service URLs
AI_BRAIN_URL = os.getenv("AI_BRAIN_URL", "http://kilo-ai-brain:9004")
SOCKETIO_URL = os.getenv("SOCKETIO_URL", "http://kilo-socketio:9010")
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://kilo-gateway:8000")

class KiloNerve:
    """
    Connects a microservice to Kilo's nervous system.
    Use this to send events, observations, and alerts to Kilo.
    """

    def __init__(self, service_name: str):
        self.service_name = service_name

    async def send_observation(
        self,
        content: str,
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Send an observation to Kilo's AI Brain.

        Args:
            content: What happened (e.g., "User took Vitamin D")
            priority: "low", "normal", "high", "urgent"
            metadata: Additional context data
        """
        try:
            observation = {
                "type": f"{self.service_name}_event",
                "content": content,
                "priority": priority,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat()
            }

            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{AI_BRAIN_URL}/observations",
                    json=observation
                )
                if resp.status_code == 200:
                    logger.info(f"[{self.service_name}] Observation sent to Kilo: {content[:50]}")
                    return True
                else:
                    logger.warning(f"[{self.service_name}] Failed to send observation: {resp.status_code}")
                    return False
        except Exception as e:
            logger.error(f"[{self.service_name}] Error sending observation: {e}")
            return False

    async def emit_event(
        self,
        event_name: str,
        data: Dict[str, Any]
    ):
        """
        Emit a real-time event via Socket.IO.

        Args:
            event_name: Event type (e.g., "med_taken", "transaction_added")
            data: Event payload
        """
        try:
            payload = {
                "event": event_name,
                "data": {
                    **data,
                    "service": self.service_name,
                    "timestamp": datetime.now().isoformat()
                }
            }

            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.post(
                    f"{GATEWAY_URL}/emit",
                    json=payload
                )
                if resp.status_code == 200:
                    logger.info(f"[{self.service_name}] Event emitted: {event_name}")
                    return True
                else:
                    logger.warning(f"[{self.service_name}] Failed to emit event: {resp.status_code}")
                    return False
        except Exception as e:
            logger.error(f"[{self.service_name}] Error emitting event: {e}")
            return False

    async def alert_kilo(
        self,
        alert_type: str,
        message: str,
        severity: str = "info",
        actionable: bool = False
    ):
        """
        Send an alert that requires Kilo's attention.

        Args:
            alert_type: Category (e.g., "health", "finance", "security")
            message: Alert message
            severity: "info", "warning", "error", "critical"
            actionable: Whether Kilo should take action
        """
        await self.send_observation(
            content=f"[{severity.upper()}] {message}",
            priority="high" if severity in ["error", "critical"] else "normal",
            metadata={
                "alert_type": alert_type,
                "severity": severity,
                "actionable": actionable
            }
        )

        # Also emit real-time if high severity
        if severity in ["error", "critical", "warning"]:
            await self.emit_event(
                "kilo_alert",
                {
                    "alert_type": alert_type,
                    "message": message,
                    "severity": severity,
                    "actionable": actionable
                }
            )

# Global instance - import this in your service
# Example: from kilo_integration import kilo_nerve
# Then in your service init: kilo_nerve = KiloNerve("financial")
