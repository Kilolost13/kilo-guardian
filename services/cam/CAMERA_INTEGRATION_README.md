# Kilo Camera Integration Tools

This directory contains tools to detect, configure, and register USB and IP cameras with the Kilo AI Guardian system.

## Quick Start

### 1. Detect Cameras (USB + IP)

```bash
python3 services/cam/setup_cameras.py --full-scan
```

This will:
- Scan `/dev/video*` for USB cameras (Logitech, etc.)
- Scan your network for IP cameras (Merkury, TP-Link, etc.)
- Generate a camera configuration file

### 2. Discover Merkury Camera Stream

If you have a Merkury pan-tilt camera that only works with the app:

```bash
python3 services/cam/discover_merkury.py 192.168.1.100
```

This will attempt to find:
- RTSP stream URL
- HTTP/MJPEG stream URL
- Web interface credentials

### 3. Register Cameras with Kilo

Once you have detected your cameras:

#### Option A: Interactive Setup
```bash
python3 services/cam/register_cameras.py
# Answer prompts for USB and IP cameras
```

#### Option B: Quick Setup (Default Config)
```bash
python3 services/cam/register_cameras.py --quick-setup
```

#### Option C: From Config File
```bash
python3 services/cam/register_cameras.py --config-file /tmp/kilo_cameras.json
```

## Detailed Guide for Your Setup

### USB Logitech Camera

1. **Connect** the Logitech camera to your system
2. **Verify** it's detected:
   ```bash
   ls -la /dev/video*
   ```
3. **Test** with OpenCV:
   ```bash
   python3 -c "import cv2; cap = cv2.VideoCapture(0); print(cap.isOpened())"
   ```
4. **Register** with Kilo:
   ```bash
   python3 services/cam/register_cameras.py
   # Choose USB camera option, set device_id=0
   ```

### Merkury Pan-Tilt Camera

The challenge: Merkury only provides a proprietary app connection. We need to find the underlying RTSP or HTTP stream.

#### Step 1: Find the IP Address
```bash
# Method 1: Check your router's connected devices
# Look for "Merkury" or similar
# Or scan your network:
python3 services/cam/setup_cameras.py --scan-network --subnet 192.168.1
```

#### Step 2: Discover Stream URL
```bash
# Run discovery tool (replace with actual IP)
python3 services/cam/discover_merkury.py 192.168.1.100
```

This tries common stream paths with default credentials:
- RTSP: `rtsp://admin:password@192.168.1.100:554/stream1`
- HTTP: `http://192.168.1.100:8080/stream`
- MJPEG: `http://192.168.1.100:8080/stream.mjpeg`

#### Step 3: If Standard Paths Don't Work

Try these troubleshooting steps:

**Option A: Check Web Interface**
```bash
# Open in browser
http://192.168.1.100:80
http://192.168.1.100:8080
# Look for streaming settings/status page
```

**Option B: Monitor App Network Traffic**
```bash
# On Mac/Linux, capture Merkury app traffic:
sudo tcpdump -i any -n 'host 192.168.1.100' | grep -E "GET|POST"
# Look for stream URLs or API endpoints
```

**Option C: Check Camera Logs**
```bash
# Some cameras log stream requests
# Try accessing camera via web interface settings
# Look for "Stream Settings" or "Network Settings"
```

**Option D: Extract from MSmartHome Protocol**
If the app uses MSmartHome protocol, the stream might be:
- Encoded in app authentication response
- Retrievable via camera's HTTP API

#### Step 4: Register the Merkury Camera

Once you have the stream URL:

```bash
python3 services/cam/register_cameras.py --quick-setup
# Edit configuration for Merkury camera details
# Then:
python3 services/cam/register_cameras.py --config-file /path/to/config.json
```

## Testing Cameras

### 1. Check Service Status
```bash
curl http://localhost:9007/status
curl http://localhost:9007/external_cameras/status
```

### 2. View Live Stream
```bash
# USB camera
curl http://localhost:9007/stream?camera_id=usb_0

# IP camera
curl http://localhost:9007/stream?camera_id=merkury_ptz
```

### 3. Test Object Detection
```bash
# Capture frame and detect objects
curl -X POST http://localhost:9007/detect_objects \
  -F 'file=@/path/to/image.jpg'
```

### 4. Test Pose Analysis
```bash
curl -X POST http://localhost:9007/analyze_pose \
  -F 'file=@/path/to/image.jpg'
```

### 5. Test PTZ Control (if supported)
```bash
# Start auto-tracking
curl -X POST http://localhost:9007/ptz/start_tracking \
  -H 'Content-Type: application/json' \
  -d '{
    "camera_id": "merkury_ptz",
    "target_x": 0.5,
    "target_y": 0.5
  }'

# Manually set position
curl -X POST http://localhost:9007/ptz/set_position \
  -H 'Content-Type: application/json' \
  -d '{
    "camera_id": "merkury_ptz",
    "pan": 0,
    "tilt": 0,
    "zoom": 1.0
  }'
```

## Configuration File Format

The tools generate a `cameras.json` file like this:

```json
{
  "cameras": [
    {
      "camera_id": "usb_0",
      "type": "usb",
      "label": "logitech_desk",
      "device_path": "/dev/video0",
      "location": "desk",
      "position": "monitor_top",
      "resolution": "1280x720",
      "fps": 30,
      "enabled": true
    },
    {
      "camera_id": "merkury_ptz",
      "type": "ip_camera",
      "label": "merkury_pan_tilt",
      "ip_address": "192.168.1.100",
      "stream_url": "rtsp://admin:password@192.168.1.100:554/stream1",
      "location": "living_room",
      "position": "wall_mount",
      "username": "admin",
      "password": "password",
      "ptz_support": true,
      "enabled": true
    }
  ]
}
```

## Troubleshooting

### USB Camera Not Detected
```bash
# Check if device exists
ls -la /dev/video*

# Install v4l2 tools
apt-get install v4l-utils

# List camera info
v4l2-ctl --all

# Check kernel logs
dmesg | grep -i video
```

### Merkury Camera Not Discoverable
1. Verify camera is powered and connected
2. Check IP address is correct
3. Ping the camera: `ping 192.168.1.100`
4. Check if default credentials work: `admin/password` or `admin/12345`
5. Try accessing web interface directly in browser
6. Check Merkury app settings for stream URL hints

### Streams Working But No Video
1. Check firewall rules
2. Verify firewall isn't blocking camera ports
3. Check camera bandwidth capacity
4. Try reducing resolution in configuration
5. Check logs for codec compatibility

### PTZ Commands Not Working
1. Not all cameras support PTZ
2. Check camera specifications
3. Verify `ptz_support: true` in configuration
4. Ensure authentication credentials are correct

## Advanced: Custom Camera Configuration

If auto-detection doesn't work, manually edit `/tmp/kilo_cameras.json` and add:

```json
{
  "camera_id": "custom_cam",
  "type": "ip_camera",
  "label": "custom_camera",
  "ip_address": "192.168.x.x",
  "stream_url": "rtsp://user:pass@192.168.x.x:554/stream",
  "username": "user",
  "password": "pass",
  "ptz_support": false,
  "location": "room_name",
  "position": "description"
}
```

Then register:
```bash
python3 services/cam/register_cameras.py --config-file /tmp/kilo_cameras.json
```

## Multi-Camera Synchronized Capture

Once both cameras are registered:

```bash
# Get synchronized frames from all cameras
curl http://localhost:9007/external_cameras/frames/synchronized

# Response includes all camera frames with matching timestamps
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/status` | GET | Camera service health check |
| `/stream` | GET | Live video stream |
| `/detect_objects` | POST | YOLO object detection |
| `/analyze_pose` | POST | MediaPipe pose analysis |
| `/cameras/register` | POST | Register new camera |
| `/cameras/remove` | POST | Unregister camera |
| `/cameras/list` | GET | List all cameras |
| `/external_cameras/status` | GET | Multi-camera system status |
| `/external_cameras/frames/synchronized` | GET | Get synchronized frames |
| `/ptz/start_tracking` | POST | Enable auto-tracking |
| `/ptz/set_position` | POST | Manual pan/tilt/zoom |
| `/ptz/stop_tracking` | POST | Disable tracking |

## Support

For issues:
1. Check camera service logs: `kubectl logs deployment/kilo-cam -n kilo-guardian`
2. Verify network connectivity: `ping <camera-ip>`
3. Test stream directly with ffplay: `ffplay rtsp://user:pass@ip:port/stream`
4. Check camera firmware is up to date
