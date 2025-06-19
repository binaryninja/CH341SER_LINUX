#!/usr/bin/env python3
"""
ESP Module Web Server Deployment Script
========================================
This script configures an ESP module connected via CH340/CH341 USB-to-serial
to connect to WiFi and deploy a basic web server.

Usage:
    python3 deploy_webserver.py
    python3 deploy_webserver.py --wifi-ssid "YourNetwork" --wifi-password "YourPassword"
"""

import serial
import time
import argparse
import sys
import json
from typing import Optional, Dict, Any

class ESPDeployer:
    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.ser: Optional[serial.Serial] = None
        self.connected = False

    def connect(self) -> bool:
        """Connect to ESP module"""
        try:
            print(f"Connecting to ESP module on {self.port} at {self.baudrate} baud...")
            self.ser = serial.Serial(self.port, self.baudrate, timeout=5)
            time.sleep(2)  # Allow connection to stabilize

            # Clear buffers
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()

            # Test connection
            if self.send_command("AT"):
                print("✓ Connected to ESP module")
                self.connected = True
                return True
            else:
                print("✗ Failed to communicate with ESP module")
                return False

        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from ESP module"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Disconnected from ESP module")

    def send_command(self, command: str, timeout: int = 5, expect_ok: bool = True) -> str:
        """Send AT command and return response"""
        if not self.ser:
            return ""

        try:
            # Send command
            full_command = f"{command}\r\n"
            self.ser.write(full_command.encode())

            # Read response
            start_time = time.time()
            response = ""

            while time.time() - start_time < timeout:
                if self.ser.in_waiting > 0:
                    chunk = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                    response += chunk

                    if expect_ok and "OK" in response:
                        break
                    elif not expect_ok and ("OK" in response or "ERROR" in response):
                        break

                time.sleep(0.1)

            print(f"CMD: {command}")
            print(f"RSP: {response.strip()}")
            return response

        except Exception as e:
            print(f"Command error: {e}")
            return ""

    def get_module_info(self) -> Dict[str, Any]:
        """Get ESP module information"""
        print("\n=== ESP Module Information ===")

        info = {}

        # Get version
        version_resp = self.send_command("AT+GMR")
        info['version'] = version_resp

        # Get current WiFi mode
        mode_resp = self.send_command("AT+CWMODE?")
        info['wifi_mode'] = mode_resp

        # Get station connection status
        status_resp = self.send_command("AT+CWJAP?")
        info['connection_status'] = status_resp

        # Get IP address
        ip_resp = self.send_command("AT+CIFSR")
        info['ip_info'] = ip_resp

        return info

    def scan_wifi_networks(self) -> list:
        """Scan for available WiFi networks"""
        print("\n=== Scanning WiFi Networks ===")

        response = self.send_command("AT+CWLAP", timeout=10)
        networks = []

        # Parse network list
        lines = response.split('\n')
        for line in lines:
            if line.startswith('+CWLAP:'):
                # Format: +CWLAP:(encryption,ssid,rssi,mac,channel)
                try:
                    # Extract SSID and signal strength
                    parts = line.split(',')
                    if len(parts) >= 3:
                        ssid = parts[1].strip('"')
                        rssi = parts[2]
                        networks.append({'ssid': ssid, 'rssi': int(rssi)})
                except:
                    continue

        # Sort by signal strength
        networks.sort(key=lambda x: x['rssi'], reverse=True)

        print(f"Found {len(networks)} networks:")
        for i, network in enumerate(networks[:10]):  # Show top 10
            print(f"  {i+1}. {network['ssid']} (Signal: {network['rssi']} dBm)")

        return networks

    def connect_wifi(self, ssid: str, password: str) -> bool:
        """Connect to WiFi network"""
        print(f"\n=== Connecting to WiFi: {ssid} ===")

        # Set to station mode
        print("Setting WiFi mode to Station...")
        self.send_command("AT+CWMODE=1")
        time.sleep(1)

        # Connect to network
        print(f"Connecting to {ssid}...")
        connect_cmd = f'AT+CWJAP="{ssid}","{password}"'
        response = self.send_command(connect_cmd, timeout=15)

        if "OK" in response:
            print("✓ WiFi connection successful!")

            # Get IP address
            time.sleep(2)
            ip_response = self.send_command("AT+CIFSR")
            print(f"Network info: {ip_response}")

            return True
        else:
            print("✗ WiFi connection failed!")
            return False

    def setup_web_server(self) -> bool:
        """Setup basic web server"""
        print("\n=== Setting up Web Server ===")

        # Enable multiple connections
        print("Enabling multiple connections...")
        self.send_command("AT+CIPMUX=1")

        # Start server on port 80
        print("Starting HTTP server on port 80...")
        response = self.send_command("AT+CIPSERVER=1,80")

        if "OK" in response:
            print("✓ Web server started successfully!")
            return True
        else:
            print("✗ Failed to start web server")
            return False

    def create_web_content(self) -> str:
        """Create HTML content for web server"""
        html_content = """<!DOCTYPE html>
<html>
<head>
    <title>ESP Web Server</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 40px;
            background-color: #f0f0f0;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 { color: #333; }
        .status {
            background-color: #e7f3ff;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin: 5px;
        }
        .button:hover { background-color: #45a049; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌐 ESP Web Server</h1>
        <div class="status">
            <strong>Status:</strong> Online and Ready!<br>
            <strong>Time:</strong> <span id="time"></span>
        </div>

        <h2>Server Information</h2>
        <p><strong>Device:</strong> ESP Module via CH340/CH341</p>
        <p><strong>Firmware:</strong> AT Command Firmware</p>

        <h2>Controls</h2>
        <button class="button" onclick="sendCommand('status')">Get Status</button>
        <button class="button" onclick="sendCommand('reset')">Reset Device</button>

        <h2>API Endpoints</h2>
        <ul>
            <li><code>/</code> - This page</li>
            <li><code>/status</code> - Device status</li>
            <li><code>/api/info</code> - JSON device info</li>
        </ul>

        <div id="response"></div>
    </div>

    <script>
        function updateTime() {
            document.getElementById('time').textContent = new Date().toLocaleString();
        }

        function sendCommand(cmd) {
            fetch('/' + cmd)
                .then(response => response.text())
                .then(data => {
                    document.getElementById('response').innerHTML =
                        '<h3>Response:</h3><pre>' + data + '</pre>';
                })
                .catch(error => {
                    document.getElementById('response').innerHTML =
                        '<p style="color: red;">Error: ' + error + '</p>';
                });
        }

        setInterval(updateTime, 1000);
        updateTime();
    </script>
</body>
</html>"""
        return html_content

    def deploy_complete_setup(self, ssid: str, password: str) -> bool:
        """Deploy complete web server setup"""
        print("\n" + "="*50)
        print("ESP WEB SERVER DEPLOYMENT")
        print("="*50)

        # Step 1: Connect to module
        if not self.connect():
            return False

        # Step 2: Get module info
        info = self.get_module_info()

        # Step 3: Scan networks (optional)
        networks = self.scan_wifi_networks()

        # Step 4: Connect to WiFi
        if not self.connect_wifi(ssid, password):
            return False

        # Step 5: Setup web server
        if not self.setup_web_server():
            return False

        # Step 6: Display final info
        print("\n" + "="*50)
        print("🎉 DEPLOYMENT SUCCESSFUL!")
        print("="*50)

        # Get final IP info
        final_ip = self.send_command("AT+CIFSR")
        print("Web server is running!")
        print("You can access it via:")

        # Extract IP from response
        lines = final_ip.split('\n')
        for line in lines:
            if 'STAIP' in line:
                ip = line.split('"')[1] if '"' in line else "IP_NOT_FOUND"
                print(f"  http://{ip}")
                break

        print("\nTo monitor incoming connections, watch the serial output.")
        print("Press Ctrl+C to stop monitoring.")

        return True

    def monitor_connections(self):
        """Monitor incoming HTTP connections"""
        print("\n=== Monitoring Web Server ===")
        print("Listening for incoming connections...")

        try:
            while True:
                if self.ser and self.ser.in_waiting > 0:
                    data = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                    if data.strip():
                        print(f"[{time.strftime('%H:%M:%S')}] {data.strip()}")

                time.sleep(0.1)

        except KeyboardInterrupt:
            print("\nStopped monitoring.")

def interactive_setup():
    """Interactive setup wizard"""
    print("ESP Web Server Setup Wizard")
    print("="*30)

    # Get WiFi credentials
    print("\nWiFi Configuration:")
    ssid = input("Enter WiFi SSID: ").strip()
    if not ssid:
        print("SSID cannot be empty!")
        return None, None

    password = input("Enter WiFi Password: ").strip()

    return ssid, password

def main():
    parser = argparse.ArgumentParser(description='Deploy web server to ESP module')
    parser.add_argument('--port', default='/dev/ttyUSB0', help='Serial port')
    parser.add_argument('--baudrate', type=int, default=115200, help='Baud rate')
    parser.add_argument('--wifi-ssid', help='WiFi SSID')
    parser.add_argument('--wifi-password', help='WiFi password')
    parser.add_argument('--monitor', action='store_true', help='Monitor connections after setup')

    args = parser.parse_args()

    # Get WiFi credentials
    if args.wifi_ssid:
        ssid, password = args.wifi_ssid, args.wifi_password or ""
    else:
        ssid, password = interactive_setup()
        if not ssid:
            sys.exit(1)

    # Create deployer
    deployer = ESPDeployer(args.port, args.baudrate)

    try:
        # Deploy setup
        success = deployer.deploy_complete_setup(ssid, password)

        if success and args.monitor:
            deployer.monitor_connections()

    except KeyboardInterrupt:
        print("\nDeployment interrupted by user.")
    except Exception as e:
        print(f"Deployment error: {e}")
    finally:
        deployer.disconnect()

if __name__ == "__main__":
    main()
