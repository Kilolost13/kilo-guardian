#!/usr/bin/env python3
"""
Kilo Camera Registration Script
Registers USB and IP cameras with the Kilo camera service
"""

import requests
import json
import sys
from typing import Dict, List

class KiloCameraRegistrar:
    """Register cameras with Kilo camera service"""
    
    def __init__(self, camera_service_url: str = "http://localhost:9007"):
        self.base_url = camera_service_url
        self.cameras = []
    
    def add_usb_camera(self, camera_id: int, label: str, location: str = "desk") -> Dict:
        """Add USB camera"""
        camera = {
            "camera_id": f"usb_{camera_id}",
            "type": "usb",
            "label": label,
            "device_path": f"/dev/video{camera_id}",
            "location": location,
            "position": "monitor_top",
            "resolution": "1280x720",
            "fps": 30
        }
        self.cameras.append(camera)
        return camera
    
    def add_ip_camera(self, ip_address: str, camera_id: str, label: str, 
                     stream_url: str, username: str = "", password: str = "",
                     ptz_enabled: bool = False) -> Dict:
        """Add IP camera (Merkury, TP-Link, etc.)"""
        camera = {
            "camera_id": camera_id,
            "type": "ip_camera",
            "label": label,
            "ip_address": ip_address,
            "stream_url": stream_url,
            "location": "living_room",
            "position": "wall_mount",
            "ptz_support": ptz_enabled
        }
        
        if username:
            camera["username"] = username
        if password:
            camera["password"] = password
        
        self.cameras.append(camera)
        return camera
    
    def register_camera(self, camera: Dict) -> bool:
        """Register single camera with service"""
        try:
            endpoint = f"{self.base_url}/cameras/register"
            response = requests.post(endpoint, json=camera, timeout=5)
            
            if response.status_code in [200, 201]:
                print(f"✓ Registered {camera['label']}")
                return True
            else:
                print(f"✗ Failed to register {camera['label']}: {response.status_code}")
                print(f"  Response: {response.text}")
                return False
        except Exception as e:
            print(f"✗ Error registering {camera['label']}: {e}")
            return False
    
    def register_all(self) -> Dict:
        """Register all cameras"""
        results = {"registered": [], "failed": []}
        
        print("📝 Registering cameras with Kilo service...")
        print(f"   Service URL: {self.base_url}\n")
        
        for camera in self.cameras:
            if self.register_camera(camera):
                results["registered"].append(camera["label"])
            else:
                results["failed"].append(camera["label"])
        
        return results
    
    def get_status(self) -> Dict:
        """Get camera service status"""
        try:
            response = requests.get(f"{self.base_url}/status", timeout=5)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return {"error": "Cannot connect to camera service"}
    
    def test_stream(self, camera_id: str) -> bool:
        """Test if camera stream is accessible"""
        try:
            response = requests.get(f"{self.base_url}/stream", 
                                   params={"camera_id": camera_id},
                                   timeout=5)
            return response.status_code == 200
        except:
            return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Kilo Camera Registration")
    parser.add_argument("--service-url", default="http://localhost:9007", 
                       help="Camera service URL (default: http://localhost:9007)")
    parser.add_argument("--quick-setup", action="store_true",
                       help="Quick setup with default camera configuration")
    parser.add_argument("--list-cameras", action="store_true",
                       help="List configured cameras from service")
    parser.add_argument("--config-file", help="Load cameras from JSON config file")
    
    args = parser.parse_args()
    
    registrar = KiloCameraRegistrar(args.service_url)
    
    # Check if service is running
    print("🔍 Checking camera service...")
    status = registrar.get_status()
    if "error" in status:
        print(f"⚠️  Camera service not responding at {args.service_url}")
        print("   Make sure the camera pod is running:")
        print("   kubectl get pods -n kilo-guardian | grep cam")
        sys.exit(1)
    
    print(f"✓ Camera service is responding\n")
    
    if args.list_cameras:
        print("📋 Configured cameras:")
        if "cameras" in status:
            for cam in status["cameras"]:
                print(f"  - {cam.get('label', 'unknown')}: {cam.get('type', 'unknown')}")
        else:
            print("  No cameras configured")
        sys.exit(0)
    
    if args.config_file:
        print(f"📂 Loading configuration from {args.config_file}")
        try:
            with open(args.config_file, 'r') as f:
                config = json.load(f)
            
            for camera in config.get("cameras", []):
                registrar.cameras.append(camera)
            
            print(f"✓ Loaded {len(registrar.cameras)} cameras from config\n")
        except Exception as e:
            print(f"✗ Error loading config: {e}")
            sys.exit(1)
    
    elif args.quick_setup:
        print("⚡ Quick Setup - Configuring default cameras")
        print("   Add USB camera at /dev/video0 (Logitech)...")
        registrar.add_usb_camera(0, "logitech_usb", location="desk")
        
        print("   Add IP camera (example Merkury)...")
        registrar.add_ip_camera(
            ip_address="192.168.1.100",
            camera_id="merkury_ptz",
            label="merkury_pan_tilt",
            stream_url="rtsp://192.168.1.100:554/stream1",
            username="admin",
            password="password",
            ptz_enabled=True
        )
        print()
    
    else:
        # Interactive setup
        print("📷 Interactive Camera Setup\n")
        
        add_usb = input("Add USB camera? (y/n): ").lower() == 'y'
        if add_usb:
            device_id = input("USB camera device ID (0-9, usually 0): ").strip() or "0"
            label = input("Camera label (e.g., 'logitech_desk'): ").strip()
            location = input("Location (e.g., 'desk', 'bedroom'): ").strip() or "desk"
            registrar.add_usb_camera(int(device_id), label, location)
        
        add_ip = input("\nAdd IP camera? (y/n): ").lower() == 'y'
        if add_ip:
            ip = input("Camera IP address (e.g., 192.168.1.100): ").strip()
            cam_id = input("Camera ID (e.g., 'merkury_ptz'): ").strip()
            label = input("Camera label: ").strip()
            stream_url = input("Stream URL (rtsp:// or http://): ").strip()
            username = input("Username (empty for none): ").strip()
            password = input("Password (empty for none): ").strip()
            ptz = input("Supports PTZ? (y/n): ").lower() == 'y'
            
            registrar.add_ip_camera(ip, cam_id, label, stream_url, username, password, ptz)
        
        print()
    
    if not registrar.cameras:
        print("⚠️  No cameras configured!")
        print("   Use --quick-setup or --config-file, or run interactively")
        sys.exit(1)
    
    # Register cameras
    results = registrar.register_all()
    
    print(f"\n{'='*60}")
    print(f"  Registration Summary")
    print(f"{'='*60}")
    print(f"✓ Registered: {len(results['registered'])} camera(s)")
    if results['registered']:
        for cam in results['registered']:
            print(f"  - {cam}")
    
    if results['failed']:
        print(f"\n✗ Failed: {len(results['failed'])} camera(s)")
        for cam in results['failed']:
            print(f"  - {cam}")
    
    # Test streams
    print(f"\n🧪 Testing streams...")
    for camera in registrar.cameras:
        if registrar.test_stream(camera['camera_id']):
            print(f"  ✓ {camera['label']} stream accessible")
        else:
            print(f"  ✗ {camera['label']} stream not accessible")
    
    print(f"\n{'='*60}")
    print("📝 Next Steps:")
    print(f"{'='*60}")
    print("1. Test camera endpoints:")
    print(f"   curl {args.service_url}/status")
    print(f"   curl {args.service_url}/external_cameras/status")
    print("\n2. View live stream:")
    print(f"   {args.service_url}/stream?camera_id=usb_0")
    print("\n3. Run object detection:")
    print(f"   curl -X POST {args.service_url}/detect_objects \\")
    print("      -F 'file=@frame.jpg'")
    
    if any(cam.get('ptz_support') for cam in registrar.cameras):
        print("\n4. Test PTZ control:")
        print(f"   curl -X POST {args.service_url}/ptz/start_tracking \\")
        print("      -H 'Content-Type: application/json' \\")
        print("      -d '{{\"camera_id\":\"merkury_ptz\",\"target_x\":0.5,\"target_y\":0.5}}'")
    
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
