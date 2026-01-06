# Logging Configuration Guide

**Kilo Guardian** - Production Logging Best Practices

---

## Overview

All Kilo Guardian services now use Python's standard `logging` module for consistent, production-grade logging output. This guide explains how to configure and use logging across the system.

---

## Current State

### Services with Logging
All 13 microservices now use the `logging` module:
- ✅ Gateway
- ✅ Medications
- ✅ Habits
- ✅ Financial
- ✅ Reminder
- ✅ AI Brain
- ✅ Camera
- ✅ ML Engine
- ✅ Voice
- ✅ Library of Truth
- ✅ USB Transfer
- ✅ SocketIO Relay
- ✅ Integration

### Log Levels Used

| Level | Usage | Example |
|-------|-------|---------|
| `logger.debug()` | Detailed diagnostic information | Cache hits, PTZ position reads |
| `logger.info()` | General informational messages | Service startup, job completion |
| `logger.warning()` | Warning messages for recoverable issues | Missing optional dependencies, fallback behavior |
| `logger.error()` | Error messages for failures | API call failures, processing errors |
| `logger.critical()` | Critical failures requiring attention | Database connection loss, service shutdown |

---

## Configuration

### Environment-Based Log Level

Set the log level using the `LOG_LEVEL` environment variable:

```bash
# In .env or environment
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Service-Level Configuration

Each service includes a logger instance:

```python
import logging

logger = logging.getLogger(__name__)
```

### Kubernetes/K3s Deployment

Configure logging via ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kilo-logging-config
  namespace: kilo-guardian
data:
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "json"  # or "text"
```

Then mount in deployments:

```yaml
envFrom:
  - configMapRef:
      name: kilo-logging-config
```

---

## Log Output Format

### Default Format (Text)
```
2026-01-06 10:30:15,123 - camera - INFO - Starting Kilo AI Camera Service
2026-01-06 10:30:16,234 - camera - INFO - YOLO object detector loaded successfully
2026-01-06 10:30:20,456 - camera - ERROR - Failed to send activity data to AI brain: Connection refused
```

### JSON Format (Recommended for Production)
Add this to each service's startup:

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'service': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_data)

# Configure
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.basicConfig(handlers=[handler], level=os.getenv('LOG_LEVEL', 'INFO'))
```

---

## Viewing Logs

### Local Development
```bash
# Follow logs for specific service
kubectl logs -f deployment/kilo-camera -n kilo-guardian

# Get last 100 lines
kubectl logs deployment/kilo-gateway -n kilo-guardian --tail=100

# All services in namespace
kubectl logs -l app=kilo --all-containers=true -n kilo-guardian
```

### Production Monitoring

#### Option 1: Centralized Logging (ELK Stack)
```yaml
# Install Fluent Bit for log collection
kubectl apply -f infra/logging/fluent-bit-config.yaml
```

#### Option 2: Loki + Grafana
```bash
# Install Loki for log aggregation
helm install loki grafana/loki-stack \
  --namespace kilo-guardian \
  --set grafana.enabled=true
```

#### Option 3: CloudWatch/Datadog (if using cloud)
Configure via environment variables in each service.

---

## Best Practices

### 1. Use Appropriate Log Levels
```python
# ✅ Good
logger.info("Starting medication reminder check")
logger.debug(f"Checking {len(meds)} medications")
logger.error("Failed to send notification", exc_info=True)

# ❌ Bad
logger.info("Checking med #1")  # Too verbose for INFO
logger.error("User clicked button")  # Not an error
```

### 2. Include Context
```python
# ✅ Good
logger.error(f"Failed to process transaction {transaction_id}: {error}")

# ❌ Bad
logger.error("Error occurred")
```

### 3. Use Structured Logging
```python
# ✅ Good (with extra context)
logger.info("Transaction processed", extra={
    'transaction_id': txn_id,
    'amount': amount,
    'user_id': user_id
})

# ❌ Less ideal
logger.info(f"Transaction {txn_id} for ${amount} by user {user_id}")
```

### 4. Log Exceptions Properly
```python
# ✅ Good
try:
    process_data()
except Exception as e:
    logger.error("Failed to process data", exc_info=True)

# ❌ Bad
except Exception as e:
    logger.error(str(e))  # Loses stack trace
```

### 5. Avoid Logging Sensitive Data
```python
# ✅ Good
logger.info(f"User {user_id[:8]}... authenticated")

# ❌ Bad - Exposes sensitive data
logger.info(f"User password: {password}")
logger.debug(f"API Key: {api_key}")
```

---

## Performance Considerations

### 1. Use Lazy Formatting
```python
# ✅ Good - Only formats if DEBUG level is enabled
logger.debug("Processing %d items", len(items))

# ❌ Bad - Always formats string even if not logged
logger.debug(f"Processing {len(items)} items")
```

### 2. Conditional Debug Logging
```python
if logger.isEnabledFor(logging.DEBUG):
    expensive_debug_info = compute_debug_data()
    logger.debug(f"Debug info: {expensive_debug_info}")
```

### 3. Sampling for High-Volume Logs
```python
if random.random() < 0.01:  # Log 1% of requests
    logger.debug(f"Request processed: {request_id}")
```

---

## Migration from print()

Most services have been migrated from `print()` to `logger` calls:

| Before | After |
|--------|-------|
| `print("Starting service")` | `logger.info("Starting service")` |
| `print(f"Error: {e}")` | `logger.error(f"Error: {e}")` |
| `print("[DEBUG]", data)` | `logger.debug(f"Data: {data}")` |

**Remaining:** Some test files and utility scripts still use `print()`, which is acceptable for development tools.

---

## Monitoring and Alerts

### Set Up Log-Based Alerts

```yaml
# Example Prometheus AlertManager rule
groups:
  - name: kilo_logging
    rules:
      - alert: HighErrorRate
        expr: rate(log_messages{level="error"}[5m]) > 0.1
        annotations:
          summary: "High error rate in {{ $labels.service }}"
```

### Common Queries

```promql
# Error rate per service
rate(log_messages{level="error"}[5m]) by (service)

# Top error messages
topk(10, count by (message) (log_messages{level="error"}))
```

---

## Troubleshooting

### Logs Not Appearing
1. Check log level: `LOG_LEVEL` environment variable
2. Verify stdout/stderr in container: `kubectl logs <pod>`
3. Check if logging is configured: Look for `import logging` in service

### Too Many Logs
1. Increase log level from DEBUG to INFO
2. Implement sampling for high-frequency events
3. Use log aggregation filters

### Log Rotation (If Using Files)
```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    '/var/log/kilo/service.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

---

## Future Enhancements

- [ ] Implement JSON structured logging across all services
- [ ] Add correlation IDs for request tracing
- [ ] Set up ELK stack for centralized logging
- [ ] Create Grafana dashboards for log visualization
- [ ] Add log sampling for high-volume services
- [ ] Implement log rotation policies

---

## References

- [Python Logging Documentation](https://docs.python.org/3/library/logging.html)
- [12-Factor App Logs](https://12factor.net/logs)
- [Kubernetes Logging Architecture](https://kubernetes.io/docs/concepts/cluster-administration/logging/)

---

**Last Updated:** 2026-01-06
**Status:** ✅ Implemented in all services
