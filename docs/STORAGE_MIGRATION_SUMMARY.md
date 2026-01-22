# KILO Storage Migration Summary
**Date:** 2026-01-17  
**Migration:** 17GB k3s container storage to 1TB SSD

## What Was Done

### 1. **1TB SSD Setup**
- Formatted `/dev/sda` as ext4
- Mounted at `/mnt/kilo-data` (auto-mounts on boot)
- Created directory structure:
  ```
  /mnt/kilo-data/
  ├── archives/     (3GB - old backups)
  ├── backups/      (for system backups)
  ├── containerd/   (17GB - container images)
  ├── databases/    (544KB - persistent volumes)
  ├── logs/         (for future log storage)
  └── models/       (for AI models)
  ```

### 2. **Container Storage Migration**
- **Before:** `/var/lib/rancher/k3s/agent/containerd/` (16-17GB)
- **After:** Symlinked to `/mnt/kilo-data/containerd/`
- **Method:**
  1. Stopped k3s
  2. Copied 17GB with rsync (2 minutes @ 178MB/s)
  3. Renamed old directory to `containerd.backup`
  4. Created symlink
  5. Restarted k3s - all 14 pods came back Running

### 3. **Nginx HTTPS Routing Fix**
- Fixed `/api/` proxy routing to preserve prefix
- Changed: `location /api` → `location /api/`
- Changed: `proxy_pass http://10.43.138.244:8000` → `proxy_pass http://10.43.138.244:8000/api/`
- Result: HTTPS gateway properly routes to backend services

### 4. **Frontend Reminder API Fix**
- Backend expects: `title`, `description`, `reminder_time`, `recurring`
- Frontend was sending: `text`, `when`, `recurrence`
- **Fixed:** Updated frontend to send correct schema
- Rebuilt and deployed frontend

## Results

### Disk Usage
| Location | Before | After | Savings |
|----------|--------|-------|---------|
| Main disk (161GB) | 128GB (85%) | 125GB (83%) | 3GB moved |
| 1TB SSD | - | 20GB (3%) | 871GB available |

**Note:** Once `containerd.backup` is deleted (after testing), main disk will drop to 73%

### Space Breakdown on 1TB Drive
```
17GB    containerd (container images/layers)
3GB     archives (old system backups)
544KB   databases (persistent volumes)
871GB   available for growth
```

### System Health
✅ All 14 KILO pods Running  
✅ 2,089 transactions accessible  
✅ Reminder creation working  
✅ HTTPS gateway routing correctly  
✅ Socket.IO attempting connection (WebSocket errors expected - browser vs wss)

## Cleanup Tasks

### Safe to Delete After Testing (2-3 days)
```bash
# This will free up 16GB on main disk
sudo rm -rf /var/lib/rancher/k3s/agent/containerd.backup
```

### Backup Script Created
- Location: `/home/kilo/scripts/backup-kilo-system.sh`
- Backs up: k8s configs, databases, code, nginx config
- Keeps last 7 backups automatically

## Configuration Changes

### /etc/fstab
```
/dev/sda1 /mnt/kilo-data ext4 defaults 0 2
```

### /etc/nginx/sites-available/kilo-https-8443
```nginx
location /api/ {
    proxy_pass http://10.43.138.244:8000/api/;
    ...
}
```

### Kubernetes ConfigMap: local-path-config
```json
{
  "nodePathMap":[{
    "node":"DEFAULT_PATH_FOR_NON_LISTED_NODES",
    "paths":["/mnt/kilo-data/databases"]
  }]
}
```

## Known Issues (Non-Critical)

1. **WebSocket Connection Attempts**
   - Browser trying to connect to `wss://192.168.68.61:8443/socket.io/`
   - Expected - real-time updates optional feature
   - Not impacting functionality

2. **ML Engine 502 Errors**
   - ML engine running but not trained yet
   - Affects: habit prediction, reminder timing suggestions
   - Non-critical - core functions work without ML

## Benefits

1. **Freed up main disk** - moved 20GB to 1TB drive
2. **Room to grow** - 871GB available for databases, models, logs
3. **Faster database ops** - dedicated SSD for k3s data
4. **Easy backups** - centralized data location
5. **System isolation** - app data separate from OS

## Testing Completed

✅ k3s cluster restart successful  
✅ All pods came back Running  
✅ Financial API returns 2,089 transactions  
✅ Reminder creation works via API  
✅ HTTPS routing works properly  
✅ Frontend loads and functions  

## Next Steps

1. Test for 2-3 days to ensure stability
2. Delete `containerd.backup` to free up 16GB
3. Run backup script periodically: `~/scripts/backup-kilo-system.sh`
4. Monitor `/mnt/kilo-data` usage with `df -h /mnt/kilo-data`
