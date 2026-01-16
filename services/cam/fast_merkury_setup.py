#!/usr/bin/env python3
"""
Fast Merkury Camera Integration - Direct Approach
Uses tinytuya to get local access without Tuya cloud
"""

import subprocess
import sys

def main():
    print("=" * 70)
    print("MERKURY CAMERA - FAST SETUP")
    print("Model: mi-cw054-199w-a | Device: pvf-4c37deba4a4e | IP: 10.42.0.212")
    print("=" * 70)
    print()
    
    # Step 1: Install tinytuya
    print("📦 Installing tinytuya...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "tinytuya"], 
                      check=True, timeout=60)
        print("✓ tinytuya installed")
    except Exception as e:
        print(f"✗ Failed to install: {e}")
        return
    
    print()
    print("=" * 70)
    print("🔑 NEXT: Get Tuya Local Key")
    print("=" * 70)
    print()
    print("Instructions:")
    print("1. Go to https://iot.tuya.com/")
    print("2. Create account or login (free)")
    print("3. Create new Cloud Project")
    print("4. Get your:")
    print("   - Access ID")
    print("   - Access Secret")
    print("5. In tinytuya, we'll find your device's Local Key")
    print()
    
    access_id = input("Enter your Tuya Access ID: ").strip()
    if not access_id:
        print("Skipping - Local Key required for integration")
        return
    
    access_secret = input("Enter your Tuya Access Secret: ").strip()
    device_id = "pvf-4c37deba4a4e"
    
    print()
    print("🔍 Scanning for local device...")
    print()
    
    try:
        import tinytuya
        
        # Try to find the device
        print("Attempting to connect to 10.42.0.212...")
        print("(If prompted, provide your Tuya credentials)")
        
        # List devices to find local key
        devices = tinytuya.DeviceManager(access_id=access_id, access_secret=access_secret)
        device_list = devices.get_devices()
        
        print(f"\n✓ Found {len(device_list)} device(s)")
        
        # Look for our camera
        camera = None
        for dev in device_list:
            if dev.get('id') == device_id or 'mi-cw054' in str(dev):
                camera = dev
                print(f"\n✓ Camera found: {dev.get('name', 'Unknown')}")
                print(f"  Local Key: {dev.get('local_key', 'NOT AVAILABLE')}")
                break
        
        if not camera:
            print(f"\n⚠️  Camera {device_id} not found in device list")
            print("Available devices:")
            for dev in device_list[:5]:
                print(f"  - {dev.get('name', 'Unknown')} ({dev.get('id', 'unknown')})")
        
        if camera and camera.get('local_key'):
            local_key = camera['local_key']
            print()
            print("=" * 70)
            print("✅ SUCCESS - Got Local Key!")
            print("=" * 70)
            print(f"Device ID: {device_id}")
            print(f"Local Key: {local_key}")
            print(f"IP: 10.42.0.212")
            print()
            
            # Save to file for later use
            config = {
                "device_id": device_id,
                "local_key": local_key,
                "ip": "10.42.0.212",
                "access_id": access_id,
                "access_secret": access_secret
            }
            
            import json
            with open("/tmp/merkury_config.json", "w") as f:
                json.dump(config, f, indent=2)
            
            print("Configuration saved to: /tmp/merkury_config.json")
            print()
            
            # Test connection
            print("Testing connection...")
            try:
                device = tinytuya.Device(
                    dev_id=device_id,
                    address="10.42.0.212",
                    local_key=local_key,
                    version=3.3,
                    persist=True
                )
                status = device.status()
                print(f"✓ Connected! Status: {json.dumps(status, indent=2)[:200]}...")
                
                print()
                print("=" * 70)
                print("🎉 CAMERA READY FOR INTEGRATION")
                print("=" * 70)
                print()
                print("Next steps:")
                print("1. Use Python script to control camera:")
                print()
                print("   import tinytuya, json")
                print("   with open('/tmp/merkury_config.json') as f:")
                print("       cfg = json.load(f)")
                print("   cam = tinytuya.Device(**cfg)")
                print("   print(cam.status())")
                print()
                print("2. Or use Kilo integration script:")
                print("   python3 services/cam/merkury_integration.py --test")
                
            except Exception as e:
                print(f"⚠️  Connection test failed: {e}")
                print("But configuration is saved - try later")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check credentials are correct")
        print("2. Visit https://iot.tuya.com/ to verify")
        print("3. Try again with correct Access ID/Secret")

if __name__ == "__main__":
    main()
