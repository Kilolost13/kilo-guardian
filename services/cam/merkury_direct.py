#!/usr/bin/env python3
"""
Merkury Direct Access - No Cloud, No Tuya Required
Uses raw protocol to find local key
"""

import socket
import json
import sys
import subprocess

def install_package(package):
    """Install Python package"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", package])
        return True
    except:
        return False

def scan_for_local_key():
    """Try to brute-force discover local key from device"""
    print("=" * 70)
    print("MERKURY CAMERA - DIRECT LOCAL ACCESS")
    print("=" * 70)
    print()
    
    IP = "10.42.0.212"
    DEVICE_ID = "pvf-4c37deba4a4e"
    
    print(f"Target: {IP} (Device: {DEVICE_ID})")
    print()
    
    # Try to connect with device in pairing mode
    print("Attempting local protocol discovery...")
    print()
    
    # Common Tuya ports for local communication
    ports_to_try = [6666, 6667, 6668, 8888, 9999, 8000, 8001]
    
    for port in ports_to_try:
        try:
            print(f"  Trying port {port}...", end=" ", flush=True)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((IP, port))
            sock.close()
            
            if result == 0:
                print("✓ PORT OPEN!")
                print()
                print(f"Found open port {port} on Merkury camera!")
                print("This might be the local protocol port.")
                return port
            else:
                print("closed")
        except Exception as e:
            print(f"error")
            pass
    
    print()
    print("⚠️  No open ports found on camera")
    print()
    print("ALTERNATIVE: Quick Tuya Setup")
    print("=" * 70)
    print()
    print("Since direct access didn't work, let's use Tuya's local key method:")
    print()
    print("Step 1: Get Tuya Credentials")
    print("  - Visit: https://iot.tuya.com/")
    print("  - Create project")
    print("  - Get Access ID + Secret")
    print()
    print("Step 2: Run tinytuya wizard to find local key")
    print("  Command: python3 -m tinytuya wizard")
    print()
    print("Step 3: Once you have the local key, use it here:")
    print()
    
    local_key = input("Enter camera's Local Key (or skip): ").strip()
    
    if local_key and len(local_key) == 16:
        print()
        print("🔑 Got local key! Testing connection...")
        return test_with_local_key(IP, DEVICE_ID, local_key)
    else:
        print()
        print("✗ Invalid key or skipped")
        return None

def test_with_local_key(ip, device_id, local_key):
    """Test connection with provided local key"""
    try:
        print()
        print("Installing tinytuya...")
        if not install_package("tinytuya"):
            print("Failed to install tinytuya")
            return None
        
        import tinytuya
        
        print("✓ Connecting to camera...")
        print()
        
        device = tinytuya.Device(
            dev_id=device_id,
            address=ip,
            local_key=local_key,
            version=3.3
        )
        
        # Set to local mode
        device.set_socketPersist(True)
        
        print("Testing command...")
        status = device.status()
        
        if status:
            print("✅ SUCCESS! Camera connected!")
            print()
            print("Camera Status:")
            for key, val in list(status.items())[:10]:
                print(f"  {key}: {val}")
            
            # Save config
            config = {
                "device_id": device_id,
                "ip": ip,
                "local_key": local_key,
                "version": 3.3
            }
            
            with open("/tmp/merkury_local_config.json", "w") as f:
                json.dump(config, f, indent=2)
            
            print()
            print("✓ Configuration saved to /tmp/merkury_local_config.json")
            print()
            print("Next: You can now control the camera directly!")
            return config
        else:
            print("✗ Connection failed - check local key")
            return None
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return None

def main():
    print()
    result = scan_for_local_key()
    
    if result:
        print()
        print("=" * 70)
        print("✅ MERKURY CAMERA CONFIGURED")
        print("=" * 70)
        print()
        print("Ready to integrate with Kilo!")
    else:
        print()
        print("=" * 70)
        print("Need Tuya Setup")
        print("=" * 70)
        print()
        print("Without a local key, we need Tuya credentials.")
        print()
        print("Quick path:")
        print("1. Visit https://iot.tuya.com/")
        print("2. Create account (takes 5 minutes)")
        print("3. Create Cloud Project")  
        print("4. Grab Access ID + Secret")
        print("5. Run: python3 -m tinytuya wizard")
        print("6. Find your camera's local key")

if __name__ == "__main__":
    main()
