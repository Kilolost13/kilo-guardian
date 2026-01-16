#!/usr/bin/env python3
"""
Kilo Camera Setup Helper - Detect and configure USB + IP cameras
Supports: Logitech USB cameras, Merkury pan-tilt, and generic IP cameras
"""

import subprocess
import json
import sys
import argparse
from typing import List, Dict, Optional
import socket
import cv2

class CameraSetupHelper:
    def __init__(self):
        self.usb_cameras = []
        self.ip_cameras = []
        
    def detect_usb_cameras(self) -> List[Dict]:
        """Detect USB cameras on /dev/video*"""
        print("\n🔍 Scanning for USB cameras...")
        detected = []
        
        for i in range(10):  # Check /dev/video0 through /dev/video9
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    # Try to read a frame
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                        fps = cap.get(cv2.CAP_PROP_FPS)
                        
                        camera_info = {
                            "device_id": i,
                            "device_path": f"/dev/video{i}",
                            "resolution": f"{int(width)}x{int(height)}",
                            "fps": int(fps) if fps > 0 else 30,
                            "type": "usb"
                        }
                        detected.append(camera_info)
                        print(f"  ✓ Found camera at /dev/video{i}: {camera_info['resolution']}")
                    cap.release()
            except Exception as e:
                pass
        
        self.usb_cameras = detected
        return detected
    
    def scan_network_for_ip_cameras(self, subnet: str = "192.168.1") -> List[Dict]:
        """Scan network for IP cameras (Merkury, TP-Link, etc.)"""
        print(f"\n🔍 Scanning network {subnet}.0/24 for IP cameras...")
        print("   (This may take a minute...)")
        detected = []
        
        # Common IP camera ports
        ports_to_check = [80, 8080, 554, 8081, 8888, 5000]
        
        for i in range(1, 255):
            ip = f"{subnet}.{i}"
            for port in ports_to_check:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.1)
                    result = sock.connect_ex((ip, port))
                    sock.close()
                    
                    if result == 0:
                        # Port is open, likely a camera
                        camera_info = {
                            "ip_address": ip,
                            "port": port,
                            "type": "ip_camera",
                            "accessible": True
                        }
                        
                        # Try to identify camera type
                        if self._is_merkury_camera(ip, port):
                            camera_info["model"] = "Merkury"
                        elif self._is_tp_link_camera(ip, port):
                            camera_info["model"] = "TP-Link"
                        
                        detected.append(camera_info)
                        print(f"  ✓ Found device at {ip}:{port}")
                except:
                    pass
        
        self.ip_cameras = detected
        return detected
    
    def _is_merkury_camera(self, ip: str, port: int) -> bool:
        """Check if device is a Merkury camera"""
        try:
            import requests
            response = requests.get(f"http://{ip}:{port}", timeout=1)
            if "merkury" in response.text.lower() or "msmarthome" in response.text.lower():
                return True
        except:
            pass
        return False
    
    def _is_tp_link_camera(self, ip: str, port: int) -> bool:
        """Check if device is a TP-Link camera"""
        try:
            import requests
            response = requests.get(f"http://{ip}:{port}", timeout=1)
            if "tp-link" in response.text.lower() or "tapo" in response.text.lower():
                return True
        except:
            pass
        return False
    
    def generate_kilo_config(self, output_file: str = "/tmp/kilo_cameras.json"):
        """Generate Kilo camera configuration JSON"""
        config = {
            "cameras": []
        }
        
        # Add USB cameras
        for usb_cam in self.usb_cameras:
            config["cameras"].append({
                "camera_id": usb_cam["device_id"],
                "type": "usb",
                "label": f"usb_camera_{usb_cam['device_id']}",
                "device_path": usb_cam["device_path"],
                "location": "desk",  # User should customize
                "position": "monitor_top",
                "angle": "front_view",
                "resolution": usb_cam["resolution"],
                "fps": usb_cam["fps"],
                "enabled": True
            })
        
        # Add IP cameras
        for idx, ip_cam in enumerate(self.ip_cameras):
            config["cameras"].append({
                "camera_id": f"ip_camera_{idx}",
                "type": "ip_camera",
                "label": ip_cam.get("model", "ip_camera").lower() + f"_{idx}",
                "ip_address": ip_cam["ip_address"],
                "port": ip_cam["port"],
                "location": "living_room",  # User should customize
                "position": "wall_mount",
                "angle": "pan_tilt" if "merkury" in ip_cam.get("model", "").lower() else "fixed",
                "username": "admin",  # User must set
                "password": "password",  # User must set
                "stream_url": f"http://{ip_cam['ip_address']}:{ip_cam['port']}/video",
                "enabled": False,  # Requires manual configuration
                "ptz_support": "merkury" in ip_cam.get("model", "").lower()
            })
        
        with open(output_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n📝 Configuration saved to {output_file}")
        print("\n⚠️  IMPORTANT: Edit the configuration file to set:")
        print("   - IP camera usernames/passwords")
        print("   - Camera locations and angles")
        print("   - Stream URLs (try detection tools if not standard)")
        
        return config

def main():
    parser = argparse.ArgumentParser(description="Kilo Camera Setup Helper")
    parser.add_argument("--detect-usb", action="store_true", help="Detect USB cameras only")
    parser.add_argument("--scan-network", action="store_true", help="Scan network for IP cameras")
    parser.add_argument("--subnet", default="192.168.1", help="Network subnet to scan (default: 192.168.1)")
    parser.add_argument("--full-scan", action="store_true", help="Detect USB + scan network")
    parser.add_argument("--output", default="/tmp/kilo_cameras.json", help="Config output file")
    
    args = parser.parse_args()
    
    helper = CameraSetupHelper()
    
    # Default to full scan
    if not (args.detect_usb or args.scan_network or args.full_scan):
        args.full_scan = True
    
    print("=" * 60)
    print("  Kilo AI Camera Setup Helper")
    print("=" * 60)
    
    if args.detect_usb or args.full_scan:
        helper.detect_usb_cameras()
        if helper.usb_cameras:
            print(f"\n✅ Found {len(helper.usb_cameras)} USB camera(s)")
        else:
            print("\n⚠️  No USB cameras detected")
    
    if args.scan_network or args.full_scan:
        helper.scan_network_for_ip_cameras(args.subnet)
        if helper.ip_cameras:
            print(f"\n✅ Found {len(helper.ip_cameras)} IP device(s)")
        else:
            print("\n⚠️  No IP devices found on network")
    
    # Generate config if any cameras found
    if helper.usb_cameras or helper.ip_cameras:
        helper.generate_kilo_config(args.output)
        
        print("\n" + "=" * 60)
        print("📋 NEXT STEPS:")
        print("=" * 60)
        print(f"1. Edit {args.output}")
        print("2. Set IP camera credentials (username, password, stream_url)")
        print("3. Customize camera locations and angles")
        print("4. Run: python3 services/cam/configure_cameras.py --config-file {args.output}")
        print("=" * 60)
    else:
        print("\n⚠️  No cameras detected. Check:")
        print("   - USB cameras are connected")
        print("   - Correct subnet is specified (--subnet)")
        print("   - Network access and camera power")

if __name__ == "__main__":
    main()
