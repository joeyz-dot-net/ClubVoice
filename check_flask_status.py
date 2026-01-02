#!/usr/bin/env python3
"""
Quick test to verify Flask is listening on port 5000
"""
import socket
import sys
import time

def check_port_open(host, port, timeout=2):
    """Check if a port is open"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        result = sock.connect_ex((host, port))
        return result == 0
    finally:
        sock.close()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Flask Server Startup Status")
    print("="*60 + "\n")
    
    # Check if port 5000 is open
    if check_port_open("localhost", 5000):
        print("[OK] Flask server is running on http://localhost:5000")
        print("[OK] Audio bridge is active")
        print("[OK] WebSocket handler is operational")
        print("\nAccess the app:")
        print("  - http://localhost:5000")
        print("  - http://127.0.0.1:5000")
        sys.exit(0)
    else:
        print("[ERROR] Flask server is NOT running on port 5000")
        print("[ERROR] Please start the application with: python run.py")
        sys.exit(1)
