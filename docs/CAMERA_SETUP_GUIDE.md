# Camera System Setup Guide - Logitech USB & Merkury Pan-Tilt

## Overview
The Kilo AI camera service supports:
- **USB Cameras** (Logitech USB webcams, etc.) - via OpenCV VideoCapture
- **IP Cameras** (Merkury, TP-Link, etc.) - via RTSP streams
- **PTZ Cameras** (Pan-Tilt-Zoom) - with automatic tracking

## Part 1: USB Logitech Camera Setup

### Prerequisites
- Logitech USB webcam physically connected to your system
- System with /dev/video* device support
- Camera service running on host or accessible container

### Step 1: Detect the Logitech Camera
```bash
# List all video devices
ls -la /dev/video*

# You should see something like:
# /dev/video0   -> Logitech USB Camera
# /dev/video1   -> Video input (might be virtual)
```

### Step 2: Test the Camera Locally
```bash
# Test with v4l2-ctl (install if needed: sudo apt-get install v4l-utils)
v4l2-ctl -d /dev/video0 --all

# Test with OpenCV Python
python3 << 'EOF'
import cv2
cap = cv2.VideoCapture(0)  # /dev/video0
if cap.isOpened():
    ret, frame = cap.read()
    print(f"✓ Camera found, resolution: {frame.shape}")
    cap.release()
else:
    print("✗ Camera not found")
EOF
```

### Step 3: Configure in Kilo Camera Service
```bash
# Run the configure_cameras.py script
cd /home/kilo/Desktop/Kilo_Ai_microservice

# Option A: Auto-detect and configure
python3 services/cam/configure_cameras.py --detect-only

# Option B: Configure with specific label
python3 services/cam/configure_cameras.py --labels "logitech_usb"

# Option C: Use preset configuration for room coverage
python3 services/cam/configure_cameras.py --preset room_coverage
```

### Step 4: API Endpoints for USB Camera
```bash
# Get camera status
curl http://localhost:9007/status

# Stream live feed
curl http://localhost:9007/stream

# Detect objects in live stream
curl -X POST http://localhost:9007/detect_objects \
  -F "file=@frame.jpg"

# Analyze pose/posture
curl -X POST http://localhost:9007/analyze_pose \
  -F "file=@frame.jpg"

# OCR (for scanning documents, receipts, prescriptions)
curl -X POST http://localhost:9007/ocr \
  -F "file=@receipt.jpg"
```

## Part 2: Merkury Pan-Tilt Camera Setup (RTSP/IP)

### Challenge: Merkury App-Only Connection
Merkury cameras typically only provide an app-based connection, but they usually support:
- RTSP streaming (less common on Merkury)
- HTTP streaming
- Proprietary protocol (MSmartHome)

### Option A: Try RTSP Discovery
```bash
# Find Merkury camera on network
sudo arp-scan --localnet | grep -i merkury

# Common Merkury RTSP URLs:
# rtsp://username:password@192.168.x.x:554/stream1
# http://192.168.x.x:8080/video?user=admin&pwd=password

# Test RTSP connection
ffprobe rtsp://192.168.x.x:554/stream1
```

### Option B: Use Merkury HTTP/Web Interface
```bash
# Merkury cameras often expose web interface at:
# http://192.168.x.x:8080

# In browser, navigate to and look for:
# - RTSP stream URL
# - MJPEG stream URL
# - Snapshot URL
# - API credentials
```

### Option C: MSmartHome Protocol Bridge
Create a bridge container to convert Merkury proprietary protocol to RTSP:

```bash
# Install ffmpeg for stream re-encoding
sudo apt-get install ffmpeg

# Capture from Merkury app via network sniffing and re-stream
# This is complex; consider Option D
```

### Option D: Use Generic IP Camera Support
```bash
# Add Merkury as HTTP/MJPEG camera
# URL formats to try:
# http://192.168.x.x:8080/video
# http://192.168.x.x/snapshot.jpg
# http://192.168.x.x:80/cgi-bin/video?user=admin&pwd=123456

# Configure in Kilo
python3 << 'EOF'
import httpx

# Register IP camera via API
client = httpx.Client()
response = client.post(
    "http://localhost:9007/cameras/register",
    params={
        "camera_id": "merkury_ptz_1",
        "location": "living_room",
        "camera_type": "ip_camera"  # or "merkury_ptz"
    }
)
print(response.json())
EOF
```

## Part 3: PTZ (Pan-Tilt-Zoom) Control for Merkury

If your Merkury is a pan-tilt model, use these endpoints:

```bash
# Start tracking a person
curl -X POST http://localhost:9007/ptz/start_tracking \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": "merkury_ptz_1",
    "target": "person",
    "smooth": true
  }'

# Set position manually
curl -X POST http://localhost:9007/ptz/set_position \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": "merkury_ptz_1",
    "pan": 0.5,
    "tilt": 0.3,
    "zoom": 1.0
  }'

# Get PTZ status
curl http://localhost:9007/ptz/status

# Stop tracking
curl -X POST http://localhost:9007/ptz/stop_tracking \
  -H "Content-Type: application/json" \
  -d '{"camera_id": "merkury_ptz_1"}'
```

## Part 4: Multi-Camera Setup (Logitech + Merkury)

### Configuration File
Create `/tmp/kilo_cameras.json`:
```json
{
  "cameras": [
    {
      "camera_id": 0,
      "type": "usb",
      "label": "logitech_usb",
      "location": "desk",
      "position": "monitor_top",
      "angle": "front_view",
      "enabled": true
    },
    {
      "camera_id": "merkury_ptz_1",
      "type": "ip_camera",
      "label": "merkury_ptz",
      "location": "living_room",
      "position": "wall_mount",
      "angle": "pan_tilt",
      "ip_address": "192.168.x.x",
      "stream_url": "http://192.168.x.x:8080/video",
      "username": "admin",
      "password": "your_password",
      "enabled": true,
      "ptz_support": true
    }
  ]
}
```

### Apply Configuration
```bash
python3 << 'EOF'
import json
import httpx

client = httpx.Client()

# Load camera config
with open('/tmp/kilo_cameras.json', 'r') as f:
    config = json.load(f)

# Register each camera
for camera in config['cameras']:
    response = client.post(
        "http://localhost:9007/cameras/register",
        json=camera
    )
    print(f"{camera['label']}: {response.status_code}")
    
# Verify
response = client.get("http://localhost:9007/cameras")
cameras = response.json()
print(f"\nConfigured cameras: {len(cameras['cameras'])}")
for cam in cameras['cameras']:
    print(f"  - {cam['label']}: {cam['location']}")
EOF
```

## Part 5: Synchronized Multi-Camera Capture

Once both cameras are configured:

```bash
# Get synchronized frames from all cameras
curl http://localhost:9007/external_cameras/frames/synchronized \
  | jq '.'

# Expected output:
{
  "timestamp": 1705264800.123,
  "cameras": [
    {
      "camera_id": 0,
      "label": "logitech_usb",
      "frame_count": 1234,
      "resolution": [1280, 720]
    },
    {
      "camera_id": "merkury_ptz_1",
      "label": "merkury_ptz",
      "frame_count": 1233,
      "resolution": [1920, 1080]
    }
  ]
}
```

## Part 6: Troubleshooting

### USB Logitech Camera Not Detected
```bash
# Check kernel logs
dmesg | grep -i usb | tail -20

# Reload USB drivers
sudo modprobe -r uvcvideo
sudo modprobe uvcvideo

# Check camera permissions
ls -la /dev/video*
# Should be readable by your user
```

### Merkury Not Connecting
```bash
# 1. Verify network connectivity
ping 192.168.x.x

# 2. Check open ports
nmap 192.168.x.x | grep open

# 3. Try accessing web interface
curl -v http://192.168.x.x:8080

# 4. Check MSmartHome app logs for hint about protocol/port
```

### Stream Lag or Buffering
```bash
# Reduce resolution in config
# Increase FPS drop tolerance
# Use MJPEG instead of H.264 if available
# Check network bandwidth: iftop -n
```

## Testing Endpoints

```bash
# Full diagnostic test
python3 services/cam/test_cameras.py --all

# Test specific camera
python3 services/cam/test_cameras.py --camera-id 0
python3 services/cam/test_cameras.py --camera-id merkury_ptz_1

# Save test frames for inspection
python3 services/cam/test_cameras.py --save-frames
# Frames saved to: /tmp/camera_test_frames/
```

## Next Steps

1. **Get Merkury working** - Try RTSP discovery or HTTP streaming first
2. **Configure both cameras** - Use the configuration script
3. **Test synchronized capture** - Verify both streams are working together
4. **Set up automation** - Use fall detection or activity monitoring with both cameras
5. **Integration** - Connect camera analytics to AI Brain for insights
