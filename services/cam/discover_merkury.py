#!/usr/bin/env python3
"""
Merkury Camera Discovery Tool
Helps find Merkury pan-tilt camera stream URLs and credentials
"""

import sys
import json
import socket
import subprocess
from typing import Optional, Dict, List
import time

class MerkuryDiscovery:
    """Discover and test Merkury camera connections"""
    
    MERKURY_PORTS = [80, 8080, 554, 8081, 8888]
    MERKURY_RTSP_PORTS = [554, 8554]
    
    # Common Merkury stream paths
    MERKURY_PATHS = {
        "rtsp": [
            "rtsp://{}:554/stream1",
            "rtsp://{}:554/stream",
            "rtsp://{}:8554/stream1",
            "rtsp://{}:554/h264/ch1",
        ],
        "http": [
            "http://{}:8080/mjpg/video.mjpg",
            "http://{}:8080/stream",
            "http://{}:80/video.mjpg",
        ],
        "mjpeg": [
            "http://{}:8080/stream?type=mjpeg",
            "http://{}:8080/stream.mjpeg",
        ]
    }
    
    def __init__(self, ip_address: str):
        self.ip = ip_address
        self.found_streams = []
        print(f"🔍 Discovering Merkury camera at {ip_address}")
    
    def scan_ports(self) -> List[int]:
        """Scan for open ports"""
        print(f"\n📡 Scanning ports...")
        open_ports = []
        
        for port in self.MERKURY_PORTS:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex((self.ip, port))
                sock.close()
                
                if result == 0:
                    open_ports.append(port)
                    print(f"   ✓ Port {port} is open")
            except:
                pass
        
        return open_ports
    
    def test_rtsp_stream(self, stream_url: str) -> bool:
        """Test RTSP stream with ffprobe"""
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_format", "-show_streams", stream_url],
                timeout=3,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"   ✓ RTSP stream valid: {stream_url}")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return False
    
    def test_http_stream(self, stream_url: str) -> bool:
        """Test HTTP/MJPEG stream"""
        try:
            import requests
            response = requests.get(stream_url, timeout=3, stream=True)
            if response.status_code == 200:
                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                if 'image' in content_type or 'video' in content_type or 'stream' in content_type:
                    print(f"   ✓ HTTP stream valid: {stream_url}")
                    return True
        except:
            pass
        return False
    
    def discover_streams(self) -> Dict:
        """Attempt to discover all available streams"""
        print(f"\n🎥 Testing Merkury stream paths...")
        
        results = {
            "ip_address": self.ip,
            "rtsp_streams": [],
            "http_streams": [],
            "web_interface": None,
            "credentials_hint": None
        }
        
        # Test RTSP streams
        for path_template in self.MERKURY_PATHS["rtsp"]:
            stream_url = path_template.format(self.ip)
            
            # Try with basic auth if available
            for user in ["admin", "root"]:
                for pwd in ["password", "12345", "admin", ""]:
                    if user and pwd:
                        auth_url = stream_url.replace("rtsp://", f"rtsp://{user}:{pwd}@")
                    else:
                        auth_url = stream_url
                    
                    if self.test_rtsp_stream(auth_url):
                        results["rtsp_streams"].append({
                            "url": auth_url,
                            "username": user if user else None,
                            "password": pwd if pwd else None,
                            "tested": True
                        })
                        break
        
        # Test HTTP streams
        for path_template in self.MERKURY_PATHS["http"] + self.MERKURY_PATHS["mjpeg"]:
            stream_url = path_template.format(self.ip)
            
            for user in ["admin", "root"]:
                for pwd in ["password", "12345", "admin", ""]:
                    if user and pwd:
                        auth_url = stream_url.replace("http://", f"http://{user}:{pwd}@")
                    else:
                        auth_url = stream_url
                    
                    if self.test_http_stream(auth_url):
                        results["http_streams"].append({
                            "url": auth_url,
                            "username": user if user else None,
                            "password": pwd if pwd else None,
                            "type": "mjpeg" if "mjpeg" in stream_url else "http",
                            "tested": True
                        })
                        break
        
        # Try to access web interface
        print(f"\n🌐 Testing web interface...")
        for port in [80, 8080]:
            try:
                import requests
                url = f"http://{self.ip}:{port}"
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    results["web_interface"] = url
                    print(f"   ✓ Web interface found at {url}")
            except:
                pass
        
        return results
    
    def print_summary(self, results: Dict):
        """Print discovery results"""
        print("\n" + "=" * 60)
        print("  Merkury Camera Discovery Results")
        print("=" * 60)
        
        if results["rtsp_streams"]:
            print("\n✓ RTSP Streams Found:")
            for stream in results["rtsp_streams"]:
                print(f"  URL: {stream['url']}")
                if stream.get("username"):
                    print(f"  Username: {stream['username']}, Password: {stream['password']}")
        
        if results["http_streams"]:
            print("\n✓ HTTP/MJPEG Streams Found:")
            for stream in results["http_streams"]:
                print(f"  URL: {stream['url']}")
                print(f"  Type: {stream.get('type', 'http')}")
                if stream.get("username"):
                    print(f"  Username: {stream['username']}, Password: {stream['password']}")
        
        if results["web_interface"]:
            print(f"\n✓ Web Interface: {results['web_interface']}")
            print("  Access to configure camera via web browser")
        
        if not (results["rtsp_streams"] or results["http_streams"]):
            print("\n⚠️  No standard streams found. Try:")
            print("  1. Check default Merkury credentials (admin/password or admin/12345)")
            print("  2. Check camera app's network traffic (Wireshark)")
            print("  3. Check camera log files for stream endpoints")
            print("  4. Try MSmartHome protocol bridge (see documentation)")
        
        # Save results
        output_file = f"/tmp/merkury_{self.ip.replace('.', '_')}_discovery.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")
        print("=" * 60)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Merkury Camera Discovery Tool")
    parser.add_argument("ip_address", help="IP address of Merkury camera")
    parser.add_argument("--user", default="admin", help="Username (default: admin)")
    parser.add_argument("--password", default="password", help="Password (default: password)")
    
    args = parser.parse_args()
    
    try:
        # Verify IP is reachable
        result = subprocess.run(
            ["ping", "-c", "1", args.ip_address],
            timeout=2,
            capture_output=True
        )
        
        if result.returncode != 0:
            print(f"⚠️  Warning: Camera {args.ip_address} is not responding to ping")
            print("   Make sure it's powered on and connected to the network")
    except:
        pass
    
    discoverer = MerkuryDiscovery(args.ip_address)
    open_ports = discoverer.scan_ports()
    
    if not open_ports:
        print("\n⚠️  No open ports found. Camera may be:")
        print("   - Powered off")
        print("   - Not on the network")
        print("   - Behind a firewall")
        sys.exit(1)
    
    results = discoverer.discover_streams()
    discoverer.print_summary(results)
    
    # Provide next steps
    print("\n📝 Next Steps:")
    if results["rtsp_streams"]:
        print("1. Use RTSP stream URL in Kilo camera configuration")
    elif results["http_streams"]:
        print("1. Use HTTP stream URL in Kilo camera configuration")
    else:
        print("1. Check camera credentials and try again")
    
    print("2. Add to cameras.json with:")
    print(f'   {{"camera_id": "merkury_ptz", "type": "ip_camera", "ip_address": "{args.ip_address}", ...}}')
    print("3. Run: curl http://localhost:9007/cameras/register -X POST -d @camera_config.json")

if __name__ == "__main__":
    main()
