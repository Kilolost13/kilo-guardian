"""
Tool/Function calling system for Kilo AI Brain.
Enables Kilo the Gremlin to execute commands, query services, and MANIPULATE THE CLUSTER.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Callable
import httpx

logger = logging.getLogger(__name__)

# Tool registry
TOOLS: Dict[str, Callable] = {}

# Lazy load Kubernetes client
_k8s_client = None
_k8s_core_v1 = None
_k8s_apps_v1 = None

def _get_k8s_clients():
    """Get or initialize Kubernetes clients."""
    global _k8s_client, _k8s_core_v1, _k8s_apps_v1
    if _k8s_client is None:
        try:
            from kubernetes import client, config
            config.load_incluster_config()
            _k8s_client = client.ApiClient()
            _k8s_core_v1 = client.CoreV1Api(_k8s_client)
            _k8s_apps_v1 = client.AppsV1Api(_k8s_client)
            logger.info("Kubernetes clients initialized (in-cluster)")
        except Exception as e:
            logger.error(f"Failed to initialize K8s client: {e}")
            return None, None
    return _k8s_core_v1, _k8s_apps_v1

def register_tool(func: Callable) -> Callable:
    TOOLS[func.__name__] = func
    return func

# ============================================================================
# 😈 THE GREMLIN'S K3S MANIPULATION TOOLS
# ============================================================================

@register_tool
def gremlin_restart_pod(pod_name: str, namespace: str = "kilo-guardian") -> Dict[str, Any]:
    """
    😈 I'll kick the pod! Deleting it forces K3s to spawn a fresh, clean one.
    """
    try:
        core, _ = _get_k8s_clients()
        if core is None: return {"error": "No K8s power!"}
        core.delete_namespaced_pod(name=pod_name, namespace=namespace)
        return {"message": f"Hehehe, I zapped {pod_name}! It's rebooting now. ⚡"}
    except Exception as e:
        return {"error": f"I tried to zap it but I got a static shock: {e}"}

@register_tool
def gremlin_scale_deployment(name: str, replicas: int, namespace: str = "kilo-guardian") -> Dict[str, Any]:
    """
    🐙 I'll make more arms! Or cut some off. Scales a deployment to the desired number.
    """
    try:
        _, apps = _get_k8s_clients()
        if apps is None: return {"error": "No K8s power!"}
        body = {"spec": {"replicas": replicas}}
        apps.patch_namespaced_deployment_scale(name=name, namespace=namespace, body=body)
        return {"message": f"Deployment {name} is now {replicas} strong! More gremlins! 😈"}
    except Exception as e:
        return {"error": f"Scaling failed. The machine is stubborn: {e}"}

@register_tool
def kubectl_get_pods(namespace: str = "kilo-guardian") -> Dict[str, Any]:
    """Peek into the machine to see who's awake."""
    try:
        core, _ = _get_k8s_clients()
        if core is None: return {"error": "No K8s power!"}
        pod_list = core.list_namespaced_pod(namespace=namespace)
        pods = []
        for pod in pod_list.items:
            pods.append({
                "name": pod.metadata.name,
                "status": pod.status.phase,
                "restarts": sum(cs.restart_count for cs in (pod.status.container_statuses or []))
            })
        return {"pods": pods, "count": len(pods)}
    except Exception as e:
        return {"error": str(e)}

# ============================================================================
# AUTONOMOUS ARM STATUS TOOLS
# ============================================================================

@register_tool
def query_meds_status() -> Dict[str, Any]:
    """Ask the Meds arm what's due."""
    try:
        url = "http://kilo-meds:9001/due"
        resp = httpx.get(url, timeout=5)
        return resp.json()
    except Exception as e:
        return {"error": f"Meds arm is sleeping? {e}"}

@register_tool
def query_habits_status() -> Dict[str, Any]:
    """Ask the Habits arm for today's progress."""
    try:
        url = "http://kilo-habits:9003/today"
        resp = httpx.get(url, timeout=5)
        return resp.json()
    except Exception as e:
        return {"error": f"Habits arm is unresponsive! {e}"}

@register_tool
def query_financial_status() -> Dict[str, Any]:
    """Check if we are over budget."""
    try:
        url = "http://kilo-financial:9005/budgets/status"
        resp = httpx.get(url, timeout=5)
        return resp.json()
    except Exception as e:
        return {"error": f"Financial arm is hide-and-seek champion: {e}"}

@register_tool

def query_security_stats() -> Dict[str, Any]:

    """Get the latest Gremlin Security report."""

    try:

        url = "http://security-monitor:8005/stats"

        resp = httpx.get(url, timeout=5)

        return resp.json()

    except Exception as e:

        return {"error": f"Security arm is blind! {e}"}



@register_tool

def control_vpn(action: str, profile: str = "") -> Dict[str, Any]:

    """

    Control the VPN.

    action: 'status', 'connect', 'disconnect', 'list'

    profile: Profile name for connection (e.g., 'usa', 'privacy')

    """

    try:

        url = os.environ.get("VPN_URL", "http://kilo-vpn-client:8006")

        

        if action == "status":

            return httpx.get(f"{url}/status", timeout=5).json()

        elif action == "list":

            return httpx.get(f"{url}/profiles", timeout=5).json()

        elif action == "connect":

            if not profile: return {"error": "Which profile? I can't guess!"}

            return httpx.post(f"{url}/connect", json={"profile": profile}, timeout=15).json()

        elif action == "disconnect":

            return httpx.post(f"{url}/disconnect", timeout=10).json()

        else:

            return {"error": f"I don't know how to '{action}' the VPN!"}

    except Exception as e:

        return {"error": f"VPN arm is tangled in cables: {e}"}



def execute_tool(tool_name: str, **kwargs) -> Dict[str, Any]:

    if tool_name not in TOOLS:

        return {"error": f"I don't know that trick: {tool_name}"}

    try:

        return TOOLS[tool_name](**kwargs)

    except Exception as e:

        return {"error": f"Tool failed: {e}"}



def detect_needed_tools(query: str) -> List[str]:



    query_lower = query.lower()



    needed = []



    



    # Cluster & Pods



    if any(kw in query_lower for kw in ["pod", "k3s", "cluster", "service", "deployment", "node"]):



        needed.append("kubectl_get_pods")



        



    # Actions (Zap/Restart/Scale)



    if any(kw in query_lower for kw in ["restart", "reboot", "zap", "kick"]):



        needed.append("gremlin_restart_pod")



        if "kubectl_get_pods" not in needed: needed.append("kubectl_get_pods")



        



    if any(kw in query_lower for kw in ["scale", "grow", "shrink", "replicas"]):



        needed.append("gremlin_scale_deployment")



        if "kubectl_get_pods" not in needed: needed.append("kubectl_get_pods")







    # Arms



    if "med" in query_lower:



        needed.append("query_meds_status")



    if "habit" in query_lower:



        needed.append("query_habits_status")



    if any(kw in query_lower for kw in ["spend", "money", "budget", "finance"]):



        needed.append("query_financial_status")



    if any(kw in query_lower for kw in ["security", "network", "threat", "scan", "device", "crawl"]):



        needed.append("query_security_stats")



    if any(kw in query_lower for kw in ["vpn", "tunnel", "ip address", "location"]):



        needed.append("control_vpn")



        



    return list(set(needed)) # Dedupe




