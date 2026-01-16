#!/usr/bin/env python3
"""
Merkury mi-cw054-199w-a Camera Integration via Tuya Protocol
Device ID: pvf-4c37deba4a4e

This uses tinytuya to communicate with Merkury cameras locally
"""

import sys
import json

def install_tinytuya():
    """Install tinytuya library"""
    import subprocess
    print("Installing tinytuya...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tinytuya"])

def setup_merkury_camera():
    """
    Setup guide for Merkury camera integration
    """
    print("""
╔══════════════════════════════════════════════════════════════════╗
║   Merkury Camera Integration Setup                               ║
║   Model: mi-cw054-199w-a                                         ║
║   Device ID: pvf-4c37deba4a4e                                    ║
╚══════════════════════════════════════════════════════════════════╝

PROBLEM: Merkury cameras use Tuya cloud protocol (encrypted)
         No direct RTSP/HTTP streams exposed
         
SOLUTION OPTIONS:

═══════════════════════════════════════════════════════════════════
OPTION 1: Use tinytuya Library (Recommended)
═══════════════════════════════════════════════════════════════════

1. Install tinytuya:
   pip3 install tinytuya

2. Get Tuya credentials (one-time setup):
   - Go to: https://iot.tuya.com/
   - Create account / Sign in
   - Create Cloud Project
   - Get: Access ID, Access Secret, Device ID, Local Key

3. Run tinytuya scanner:
   python3 -m tinytuya scan
   
4. Find your camera in output:
   Device ID: pvf-4c37deba4a4e
   IP: 10.42.0.212
   Local Key: (will be shown)

5. Test connection:
   python3 -m tinytuya wizard

═══════════════════════════════════════════════════════════════════
OPTION 2: Use go2rtc Stream Proxy (Alternative)
═══════════════════════════════════════════════════════════════════

go2rtc can act as a bridge for proprietary camera protocols:

1. Install go2rtc:
   docker run -d --name go2rtc \\
     --network host \\
     -v /tmp/go2rtc.yaml:/config/go2rtc.yaml \\
     alexxit/go2rtc

2. Configure for Tuya camera:
   (Requires Local Key from Tuya platform)

═══════════════════════════════════════════════════════════════════
OPTION 3: Use Scrypted (Full-Featured)
═══════════════════════════════════════════════════════════════════

Scrypted supports many camera protocols including Tuya:

1. Install Scrypted:
   docker run -d --name scrypted \\
     --restart unless-stopped \\
     --network host \\
     -v ~/.scrypted:/server/volume \\
     koush/scrypted

2. Access web UI: http://localhost:10443
3. Install Tuya plugin
4. Add your Merkury camera

═══════════════════════════════════════════════════════════════════
OPTION 4: RTSP Simple Server + FFmpeg Bridge (Manual)
═══════════════════════════════════════════════════════════════════

If you can get local key, create RTSP bridge:

1. Get video stream from camera (via tinytuya)
2. Re-stream via RTSP:
   
   ffmpeg -re -i pipe:0 -c copy -f rtsp \\
     rtsp://localhost:8554/merkury

═══════════════════════════════════════════════════════════════════
QUICK START (Option 1):
═══════════════════════════════════════════════════════════════════
""")

    choice = input("Install tinytuya now? (y/n): ").lower()
    if choice == 'y':
        try:
            install_tinytuya()
            print("\n✓ tinytuya installed!")
            print("\nNext steps:")
            print("1. Run: python3 -m tinytuya wizard")
            print("2. Follow prompts to get Tuya credentials")
            print("3. Scan for device: python3 -m tinytuya scan")
            print("4. Note down the Local Key for pvf-4c37deba4a4e")
        except Exception as e:
            print(f"\n✗ Installation failed: {e}")
    else:
        print("\nManual setup required. See options above.")

def test_local_connection():
    """Test direct connection to camera"""
    try:
        import tinytuya
        
        print("\n=== Testing Merkury Camera Connection ===")
        print("IP: 10.42.0.212")
        print("Device ID: pvf-4c37deba4a4e")
        print("\nNote: You need the Local Key from Tuya platform")
        print("Run 'python3 -m tinytuya wizard' to get it\n")
        
        local_key = input("Enter Local Key (or press Enter to skip): ").strip()
        
        if local_key:
            device = tinytuya.Device(
                dev_id='pvf-4c37deba4a4e',
                address='10.42.0.212',
                local_key=local_key,
                version=3.3
            )
            
            print("\nConnecting...")
            status = device.status()
            print(f"\nCamera Status: {json.dumps(status, indent=2)}")
        else:
            print("\nSkipping test. Get Local Key first using tinytuya wizard.")
            
    except ImportError:
        print("\n✗ tinytuya not installed")
        print("Run: pip3 install tinytuya")
    except Exception as e:
        print(f"\n✗ Connection failed: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Merkury Camera Integration Helper")
    parser.add_argument("--setup", action="store_true", help="Show setup guide")
    parser.add_argument("--test", action="store_true", help="Test connection")
    parser.add_argument("--install", action="store_true", help="Install tinytuya")
    
    args = parser.parse_args()
    
    if args.install:
        install_tinytuya()
    elif args.test:
        test_local_connection()
    else:
        setup_merkury_camera()
