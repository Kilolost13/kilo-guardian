# Server-Side Dashboards - Access Guide

## Available Dashboards

You have **2 professional monitoring dashboards** already installed and running:

### 1. Grafana (Primary Dashboard)
- **Beautiful visualization** - Charts, graphs, gauges, heatmaps
- **Pre-configured dashboards** for Kubernetes metrics
- **Custom dashboards** - Create your own views
- **Alerting** - Set up notifications
- **Data from Prometheus** - All your k3s metrics

### 2. Prometheus (Metrics & Queries)
- **Raw metrics database** - All pod/service metrics
- **Query interface** - Write PromQL queries
- **Service discovery** - Auto-finds all services
- **Targets view** - See what's being monitored

## Access URLs

### Option 1: NodePort (Recommended - Permanent)
```
Grafana:    http://192.168.68.61:30300
Prometheus: http://192.168.68.61:30900
```

### Option 2: Port Forward (Temporary)
```bash
# Grafana on port 3000
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80 --address=0.0.0.0

# Prometheus on port 9090
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090 --address=0.0.0.0
```

Then access:
- Grafana: http://192.168.68.61:3000
- Prometheus: http://192.168.68.61:9090

## Grafana Login Credentials

```
Username: admin
Password: VYYjs2MAmb7KsrVZIyRYv0VLnuxIOWqe4XiG2IQ0
```

**Change this password** after first login!

## What You Can Monitor

### Kubernetes Metrics
- **Pod health** - CPU, memory, restarts
- **Node resources** - Disk, network, load
- **Service metrics** - Request rates, latency
- **Persistent volumes** - Storage usage

### KILO Guardian Specific
All your microservices expose metrics on `/metrics` endpoints:
- Financial service metrics
- AI Brain performance
- Gateway request rates
- Database sizes
- API response times

### Pre-installed Dashboards in Grafana

1. **Kubernetes / Compute Resources / Cluster**
   - Overall cluster health
   - Total CPU/memory usage
   - Pod count across namespaces

2. **Kubernetes / Compute Resources / Namespace (Pods)**
   - Filter by namespace (select `kilo-guardian`)
   - See all your microservices
   - Resource usage per pod

3. **Kubernetes / Compute Resources / Pod**
   - Detailed view of individual pods
   - Container resource usage
   - Network I/O

4. **Kubernetes / Persistent Volumes**
   - Your data PVCs (financial, meds, reminder, library)
   - Storage usage and availability
   - I/O performance

## Quick Start Guide

### First Time Setup

1. **Access Grafana**: http://192.168.68.61:30300
2. **Login** with credentials above
3. **Change password**: Click profile → Change Password
4. **Explore dashboards**: Click menu (☰) → Dashboards → Browse

### View KILO Guardian Metrics

1. In Grafana, go to **Dashboards** → **Kubernetes / Compute Resources / Namespace (Pods)**
2. At the top, set **namespace** filter to `kilo-guardian`
3. You'll see all your microservices with live metrics!

### Create Custom Dashboard for KILO

1. Click **+** → **Create Dashboard**
2. **Add visualization**
3. **Select Prometheus** as data source
4. Use queries like:
   ```promql
   # CPU usage of all KILO pods
   sum(rate(container_cpu_usage_seconds_total{namespace="kilo-guardian"}[5m])) by (pod)
   
   # Memory usage by pod
   sum(container_memory_working_set_bytes{namespace="kilo-guardian"}) by (pod)
   
   # Gateway request rate
   rate(http_requests_total{service="kilo-gateway"}[5m])
   ```

## Useful Dashboards to Create

### KILO System Health Dashboard
- Gateway request rate
- AI Brain response time
- Database sizes (financial, meds, reminder, library)
- Pod restart count
- Error rates per service

### Financial Service Dashboard
- Transaction processing rate
- Database size growth
- API endpoint latencies
- Budget calculations per second

### Tablet Usage Dashboard
- Frontend requests per minute
- Most accessed modules
- User session duration
- API error rates

## Prometheus Queries (Examples)

Access Prometheus at http://192.168.68.61:30900 and try these queries:

```promql
# All running pods in kilo-guardian
kube_pod_status_phase{namespace="kilo-guardian"}

# Gateway memory usage
container_memory_working_set_bytes{pod=~"kilo-gateway.*"}

# Financial DB size (if metrics exported)
sqlite_db_size_bytes{service="kilo-financial"}

# Request rate to gateway
rate(http_requests_total{service="kilo-gateway"}[5m])

# Pod restart count
kube_pod_container_status_restarts_total{namespace="kilo-guardian"}
```

## Accessing from Tablet

The NodePort services are accessible from any device on your network:

From tablet browser:
- Grafana: `http://192.168.68.61:30300`
- Prometheus: `http://192.168.68.61:30900`

Note: These are HTTP (not HTTPS), so you may see browser warnings. This is normal for internal dashboards.

## Alerting Setup

### Email Alerts (Optional)
1. In Grafana, go to **Alerting** → **Contact points**
2. Add email server details
3. Create alert rules for:
   - Pod down/restarting
   - High CPU/memory
   - Disk space low
   - API errors

### Slack/Discord Alerts (Optional)
1. Create webhook in Slack/Discord
2. Add as contact point in Grafana
3. Route alerts to channel

## Maintenance

### Keep Port Forwards Running
The port-forward commands will stop if your terminal closes. To make them persistent:

```bash
# Create systemd service (optional)
sudo tee /etc/systemd/system/grafana-forward.service > /dev/null <<EOF
[Unit]
Description=Grafana Port Forward
After=network.target

[Service]
Type=simple
User=kilo
ExecStart=/usr/local/bin/kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80 --address=0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable grafana-forward
sudo systemctl start grafana-forward
```

### Or Use NodePort (Already Setup!)
NodePort services (30300, 30900) are permanent and survive restarts - **this is already configured for you!**

## Files Created

- `/home/kilo/monitoring-ingress.yaml` - Ingress definitions
- `/home/kilo/monitoring-nodeports.yaml` - NodePort services

## Current Status

✅ **Grafana**: Running and accessible at http://192.168.68.61:30300  
✅ **Prometheus**: Running and accessible at http://192.168.68.61:30900  
✅ **Monitoring**: 17 days of metrics history available  
✅ **NodePorts**: Configured for permanent access  
✅ **Credentials**: admin / VYYjs2MAmb7KsrVZIyRYv0VLnuxIOWqe4XiG2IQ0

## Next Steps

1. **Open Grafana** in your browser: http://192.168.68.61:30300
2. **Login** with the credentials above
3. **Change your password** immediately
4. **Explore** the pre-built Kubernetes dashboards
5. **Filter** to `kilo-guardian` namespace to see your services
6. **Create custom dashboards** for KILO-specific metrics

---
**You now have professional server-side monitoring dashboards!**
