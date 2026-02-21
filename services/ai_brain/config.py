"""
Configuration for the AI Brain plugin system
"""
import os

# Plugin system configuration
PLUGIN_ENABLED = os.environ.get("PLUGIN_ENABLED", "true").lower() == "true"
PLUGIN_DIR = os.environ.get("PLUGIN_DIR", "plugins")

# Plugin health and watchdog settings
PLUGIN_HEALTH_INTERVAL = int(os.environ.get("PLUGIN_HEALTH_INTERVAL", "20"))
PLUGIN_RESTART_RETRIES = int(os.environ.get("PLUGIN_RESTART_RETRIES", "3"))

# Plugin isolation settings
PLUGIN_ISOLATION_MODE = os.environ.get("PLUGIN_ISOLATION_MODE", "thread")  # "thread" or "process"
PLUGIN_AUTO_ESCALATE_ON_FAILURE = os.environ.get("PLUGIN_AUTO_ESCALATE_ON_FAILURE", "true").lower() == "true"
PLUGIN_FAILURE_THRESHOLD_FOR_ESCALATION = int(os.environ.get("PLUGIN_FAILURE_THRESHOLD_FOR_ESCALATION", "3"))

# Plugin resource limits
PLUGIN_DEFAULT_TIMEOUT = int(os.environ.get("PLUGIN_DEFAULT_TIMEOUT", "30"))
PLUGIN_DEFAULT_MEMORY_LIMIT_MB = int(os.environ.get("PLUGIN_DEFAULT_MEMORY_LIMIT_MB", "512"))
PLUGIN_DEFAULT_CPU_TIME_LIMIT = int(os.environ.get("PLUGIN_DEFAULT_CPU_TIME_LIMIT", "10"))
PLUGIN_ALLOW_NETWORK = os.environ.get("PLUGIN_ALLOW_NETWORK", "true").lower() == "true"
PLUGIN_MAX_RETRIES = int(os.environ.get("PLUGIN_MAX_RETRIES", "3"))

# Plugin discovery mode
PLUGIN_DISCOVERY_MODE = os.environ.get("PLUGIN_DISCOVERY_MODE", "filesystem")  # "filesystem" or "k8s"
