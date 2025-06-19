#!/usr/bin/env python3
"""
HTTP Response Handler for ESP Web Server
========================================
This script monitors HTTP requests coming to the ESP module and sends
appropriate responses back through the serial connection.

Usage:
    python3 http_handler.py
    python3 http_handler.py --port /dev/ttyUSB0
    python3 http_handler.py --verbose
"""

import serial
import time
import json
import re
import argparse
import threading
from datetime import datetime
from urllib.parse import unquote

class ESPHttpHandler:
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200, verbose=False):
        self.port = port
        self.baudrate = baudrate
        self.verbose = verbose
        self.ser = None
        self.connected = False
        self.running = False

        # Statistics
        self.stats = {
            'requests_handled': 0,
            'start_time': datetime.now(),
            'last_request': None
        }

    def log(self, message):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    def verbose_log(self, message):
        """Log verbose message"""
        if self.verbose:
            self.log(f"DEBUG: {message}")

    def connect(self):
        """Connect to ESP module"""
        try:
            self.log(f"Connecting to ESP module on {self.port}...")
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)

            # Test connection
            self.ser.write(b"AT\r\n")
            time.sleep(1)
            response = self.ser.read_all().decode('utf-8', errors='ignore')

            if "OK" in response:
                self.connected = True
                self.log("✓ Connected to ESP module")
                return True
            else:
                self.log("✗ Failed to communicate with ESP module")
                return False

        except Exception as e:
            self.log(f"Connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from ESP module"""
        self.running = False
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.connected = False
            self.log("Disconnected from ESP module")

    def parse_http_request(self, data):
        """Parse HTTP request data"""
        try:
            # Look for IPD pattern: +IPD,conn_id,length:data
            ipd_match = re.search(r'\+IPD,(\d+),(\d+):(.*)', data, re.DOTALL)
            if not ipd_match:
                return None

            conn_id = int(ipd_match.group(1))
            length = int(ipd_match.group(2))
            content = ipd_match.group(3)

            # Parse HTTP request line
            lines = content.split('\r\n')
            if not lines or not lines[0]:
                return None

            request_line = lines[0]
            parts = request_line.split(' ')

            if len(parts) < 2:
                return None

            method = parts[0]
            path = unquote(parts[1])  # URL decode
            version = parts[2] if len(parts) > 2 else 'HTTP/1.1'

            # Parse headers
            headers = {}
            body = ""
            in_body = False

            for line in lines[1:]:
                if in_body:
                    body += line + '\r\n'
                elif line == '':
                    in_body = True
                elif ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()

            return {
                'connection_id': conn_id,
                'method': method,
                'path': path,
                'version': version,
                'headers': headers,
                'body': body.strip(),
                'raw_data': content
            }

        except Exception as e:
            self.verbose_log(f"Error parsing HTTP request: {e}")
            return None

    def create_html_response(self, title="ESP Web Server", content=""):
        """Create HTML response"""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 40px;
            background-color: #f0f8ff;
            color: #333;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        .status {{
            background-color: #d4edda;
            color: #155724;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 5px solid #28a745;
        }}
        .info {{
            background-color: #e7f3ff;
            color: #004085;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 5px solid #007bff;
        }}
        .button {{
            background-color: #3498db;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            margin: 10px 5px;
            text-decoration: none;
            display: inline-block;
        }}
        .button:hover {{
            background-color: #2980b9;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-box {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            text-align: center;
            border: 1px solid #dee2e6;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #495057;
        }}
        .stat-label {{
            color: #6c757d;
            font-size: 14px;
        }}
        code {{
            background-color: #f8f9fa;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        .api-list {{
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .api-item {{
            margin: 10px 0;
            padding: 10px;
            background: white;
            border-radius: 3px;
            border-left: 3px solid #28a745;
        }}
    </style>
    <script>
        function updateTime() {{
            document.getElementById('current-time').textContent = new Date().toLocaleString();
        }}
        setInterval(updateTime, 1000);
        window.onload = updateTime;

        function refreshPage() {{
            location.reload();
        }}

        function testApi(endpoint) {{
            fetch(endpoint)
                .then(response => response.text())
                .then(data => {{
                    alert('Response from ' + endpoint + ':\\n\\n' + data);
                }})
                .catch(error => {{
                    alert('Error: ' + error);
                }});
        }}
    </script>
</head>
<body>
    <div class="container">
        <h1>🌐 ESP Web Server</h1>

        <div class="status">
            <strong>Status:</strong> Online and Running!<br>
            <strong>Current Time:</strong> <span id="current-time"></span>
        </div>

        {content}

        <div class="info">
            <strong>Device:</strong> ESP Module<br>
            <strong>Connection:</strong> CH340/CH341 USB-to-Serial<br>
            <strong>Firmware:</strong> AT Command Firmware v1.7.4.0<br>
            <strong>Server:</strong> Custom HTTP Handler
        </div>

        <div class="stats">
            <div class="stat-box">
                <div class="stat-value">{self.stats['requests_handled']}</div>
                <div class="stat-label">Requests Handled</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{(datetime.now() - self.stats['start_time']).seconds // 60}</div>
                <div class="stat-label">Minutes Online</div>
            </div>
        </div>

        <h2>Available Endpoints</h2>
        <div class="api-list">
            <div class="api-item">
                <strong>GET /</strong> - This main page
                <button class="button" onclick="refreshPage()">Refresh</button>
            </div>
            <div class="api-item">
                <strong>GET /status</strong> - Server status (JSON)
                <button class="button" onclick="testApi('/status')">Test</button>
            </div>
            <div class="api-item">
                <strong>GET /info</strong> - Device information
                <button class="button" onclick="testApi('/info')">Test</button>
            </div>
            <div class="api-item">
                <strong>GET /time</strong> - Current server time
                <button class="button" onclick="testApi('/time')">Test</button>
            </div>
            <div class="api-item">
                <strong>GET /stats</strong> - Server statistics
                <button class="button" onclick="testApi('/stats')">Test</button>
            </div>
        </div>

        <h2>Quick Actions</h2>
        <button class="button" onclick="refreshPage()">🔄 Refresh Page</button>
        <button class="button" onclick="testApi('/status')">📊 Check Status</button>
        <button class="button" onclick="alert('ESP Web Server is running!\\nIP: Check your router\\'s admin panel\\nPort: 80')">ℹ️ Connection Info</button>
    </div>
</body>
</html>"""
        return html

    def handle_request(self, request):
        """Handle HTTP request and return appropriate response"""
        method = request['method']
        path = request['path']
        conn_id = request['connection_id']

        self.stats['requests_handled'] += 1
        self.stats['last_request'] = datetime.now()

        self.log(f"Request: {method} {path} (Connection: {conn_id})")

        # Route requests
        if path == '/' or path == '/index.html':
            content = self.create_html_response()
            response = self.create_http_response(content, 'text/html')

        elif path == '/status':
            status_data = {
                'status': 'online',
                'timestamp': datetime.now().isoformat(),
                'uptime_seconds': (datetime.now() - self.stats['start_time']).total_seconds(),
                'requests_handled': self.stats['requests_handled'],
                'last_request': self.stats['last_request'].isoformat() if self.stats['last_request'] else None
            }
            content = json.dumps(status_data, indent=2)
            response = self.create_http_response(content, 'application/json')

        elif path == '/info':
            info_data = {
                'device': 'ESP Module',
                'firmware': 'AT Command Firmware v1.7.4.0',
                'connection': 'CH340/CH341 USB-to-Serial',
                'server': 'Custom HTTP Handler',
                'features': ['WiFi', 'HTTP Server', 'AT Commands'],
                'endpoints': ['/', '/status', '/info', '/time', '/stats']
            }
            content = json.dumps(info_data, indent=2)
            response = self.create_http_response(content, 'application/json')

        elif path == '/time':
            time_data = {
                'current_time': datetime.now().isoformat(),
                'timestamp': int(time.time()),
                'timezone': 'System Local Time'
            }
            content = json.dumps(time_data, indent=2)
            response = self.create_http_response(content, 'application/json')

        elif path == '/stats':
            stats_data = dict(self.stats)
            stats_data['start_time'] = stats_data['start_time'].isoformat()
            if stats_data['last_request']:
                stats_data['last_request'] = stats_data['last_request'].isoformat()
            stats_data['uptime_seconds'] = (datetime.now() - self.stats['start_time']).total_seconds()
            content = json.dumps(stats_data, indent=2)
            response = self.create_http_response(content, 'application/json')

        else:
            # 404 Not Found
            content = self.create_html_response(
                "404 - Page Not Found",
                f"<div class='info'>The requested page <code>{path}</code> was not found on this server.</div>"
            )
            response = self.create_http_response(content, 'text/html', status_code=404)

        return response

    def create_http_response(self, content, content_type='text/html', status_code=200):
        """Create HTTP response"""
        status_text = {
            200: 'OK',
            404: 'Not Found',
            500: 'Internal Server Error'
        }.get(status_code, 'OK')

        response = f"HTTP/1.1 {status_code} {status_text}\r\n"
        response += f"Content-Type: {content_type}\r\n"
        response += f"Content-Length: {len(content)}\r\n"
        response += "Connection: close\r\n"
        response += "Server: ESP-HTTP-Handler/1.0\r\n"
        response += "\r\n"
        response += content

        return response

    def send_response(self, conn_id, response):
        """Send HTTP response via ESP"""
        try:
            # Calculate response length
            response_length = len(response)

            # Send CIPSEND command
            send_cmd = f"AT+CIPSEND={conn_id},{response_length}\r\n"
            self.verbose_log(f"Sending: {send_cmd.strip()}")
            self.ser.write(send_cmd.encode())

            # Wait for ">" prompt
            time.sleep(0.5)
            prompt_response = self.ser.read_all().decode('utf-8', errors='ignore')
            self.verbose_log(f"CIPSEND response: {prompt_response.strip()}")

            if ">" in prompt_response:
                # Send actual response data
                self.verbose_log(f"Sending response data ({response_length} bytes)")
                self.ser.write(response.encode())

                # Wait for send confirmation
                time.sleep(0.5)
                send_response = self.ser.read_all().decode('utf-8', errors='ignore')
                self.verbose_log(f"Send response: {send_response.strip()}")

                if "SEND OK" in send_response:
                    self.log(f"✓ Response sent to connection {conn_id}")
                    return True
                else:
                    self.log(f"✗ Failed to send response to connection {conn_id}")
                    return False
            else:
                self.log(f"✗ No '>' prompt received for connection {conn_id}")
                return False

        except Exception as e:
            self.log(f"Error sending response: {e}")
            return False

    def close_connection(self, conn_id):
        """Close connection"""
        try:
            close_cmd = f"AT+CIPCLOSE={conn_id}\r\n"
            self.ser.write(close_cmd.encode())
            time.sleep(0.2)
            self.verbose_log(f"Closed connection {conn_id}")
        except Exception as e:
            self.verbose_log(f"Error closing connection {conn_id}: {e}")

    def handle_incoming_data(self, data):
        """Handle incoming serial data"""
        self.verbose_log(f"Raw data: {repr(data)}")

        # Parse HTTP request
        request = self.parse_http_request(data)
        if request:
            # Handle the request
            response = self.handle_request(request)

            # Send response
            if self.send_response(request['connection_id'], response):
                # Close connection after sending response
                time.sleep(0.1)
                self.close_connection(request['connection_id'])
            else:
                self.log("Failed to send response, closing connection")
                self.close_connection(request['connection_id'])

        # Log other interesting events
        if "CONNECT" in data:
            conn_match = re.search(r'(\d+),CONNECT', data)
            if conn_match:
                conn_id = conn_match.group(1)
                self.log(f"New connection: {conn_id}")

        elif "CLOSED" in data:
            conn_match = re.search(r'(\d+),CLOSED', data)
            if conn_match:
                conn_id = conn_match.group(1)
                self.log(f"Connection closed: {conn_id}")

    def run(self):
        """Main HTTP handler loop"""
        if not self.connect():
            return False

        self.log("🌐 HTTP Handler started - waiting for requests...")
        self.log("Press Ctrl+C to stop")

        self.running = True
        buffer = ""

        try:
            while self.running:
                if self.ser.in_waiting > 0:
                    chunk = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                    buffer += chunk

                    # Process complete messages
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()

                        if line and not line.startswith('AT'):
                            self.handle_incoming_data(line)

                time.sleep(0.1)

        except KeyboardInterrupt:
            self.log("HTTP handler stopped by user")
        except Exception as e:
            self.log(f"Error in HTTP handler: {e}")
        finally:
            self.disconnect()

        return True

def main():
    parser = argparse.ArgumentParser(description='ESP HTTP Response Handler')
    parser.add_argument('--port', default='/dev/ttyUSB0', help='Serial port')
    parser.add_argument('--baudrate', type=int, default=115200, help='Baud rate')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()

    handler = ESPHttpHandler(args.port, args.baudrate, args.verbose)

    try:
        handler.run()
    except KeyboardInterrupt:
        print("\nHandler interrupted by user")
    except Exception as e:
        print(f"Handler error: {e}")

    return 0

if __name__ == "__main__":
    exit(main())
