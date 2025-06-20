#!/usr/bin/env python3
"""
ESP Module Monitor and Management Utility
=========================================
This utility provides real-time monitoring and management of ESP modules
connected via CH340/CH341 USB-to-serial converters.

Features:
- Real-time connection monitoring
- HTTP request/response logging
- Device status monitoring
- Remote command execution
- Performance metrics
- Web interface management
- Historical data persistence with SQLite
- Performance analytics and reporting
- Anomaly detection and alerting
- Data export capabilities

Usage:
    python3 esp_monitor.py                    # Start monitoring
    python3 esp_monitor.py --command status   # Get device status
    python3 esp_monitor.py --web-interface    # Launch web management interface
    python3 esp_monitor.py --generate-report  # Generate performance report
"""

import serial
import time
import json
import argparse
import threading
import queue
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import deque
import http.server
import socketserver
from urllib.parse import parse_qs, urlparse
import logging

# Import our new modules
try:
    from database_manager import DatabaseManager, ConnectionEvent, DeviceStatus, PerformanceMetrics
    from report_generator import ReportGenerator
    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Database features not available: {e}")
    print("Install required packages: pip install matplotlib seaborn pandas jinja2")
    DATABASE_AVAILABLE = False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ESPMonitor:
    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 115200, enable_database: bool = True):
        self.port = port
        self.baudrate = baudrate
        self.ser: Optional[serial.Serial] = None
        self.connected = False
        self.monitoring = False

        # Data storage (legacy deques for backward compatibility)
        self.connection_log = deque(maxlen=1000)
        self.request_log = deque(maxlen=500)
        self.status_history = deque(maxlen=100)
        self.metrics = {
            'connections_total': 0,
            'requests_total': 0,
            'errors_total': 0,
            'uptime_start': None,
            'last_activity': None
        }

        # Database integration
        self.database_enabled = enable_database and DATABASE_AVAILABLE
        self.db_manager = None
        self.report_generator = None

        if self.database_enabled:
            try:
                self.db_manager = DatabaseManager()
                self.report_generator = ReportGenerator(self.db_manager)
                logger.info("Database persistence enabled")
            except Exception as e:
                logger.error(f"Failed to initialize database: {e}")
                self.database_enabled = False

        # Performance tracking
        self.last_metrics_update = datetime.now()
        self.metrics_update_interval = 300  # 5 minutes

        # Status tracking
        self.last_status_update = datetime.now()
        self.status_update_interval = 60  # 1 minute

        # Threading
        self.monitor_thread = None
        self.command_queue = queue.Queue()
        self.response_queue = queue.Queue()

        # Load configuration
        self.config = self.load_config()

    def load_config(self) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open('esp_config.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return self.get_default_config()
        except json.JSONDecodeError:
            print("Warning: Invalid config file, using defaults")
            return self.get_default_config()

    def get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            "device": {"port": "/dev/ttyUSB0", "baudrate": 115200},
            "monitoring": {"log_connections": True, "log_requests": True},
            "webserver": {"port": 80}
        }

    def connect(self) -> bool:
        """Connect to ESP module"""
        try:
            print(f"Connecting to ESP module on {self.port}...")
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)

            # Test connection
            self.ser.write(b"AT\r\n")
            time.sleep(1)
            response = self.ser.read_all().decode('utf-8', errors='ignore')

            if "OK" in response:
                self.connected = True
                self.metrics['uptime_start'] = datetime.now()
                print("✓ Connected to ESP module")
                return True
            else:
                print("✗ Failed to communicate with ESP module")
                return False

        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from ESP module"""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)

        if self.ser and self.ser.is_open:
            self.ser.close()
            self.connected = False
            print("Disconnected from ESP module")

    def send_at_command(self, command: str, timeout: int = 5) -> str:
        """Send AT command and get response"""
        if not self.connected or not self.ser:
            return ""

        try:
            cmd = f"{command}\r\n"
            self.ser.write(cmd.encode())

            start_time = time.time()
            response = ""

            while time.time() - start_time < timeout:
                if self.ser.in_waiting > 0:
                    chunk = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                    response += chunk

                    if "OK" in response or "ERROR" in response:
                        break

                time.sleep(0.1)

            return response.strip()

        except Exception as e:
            print(f"Command error: {e}")
            return ""

    def parse_connection_data(self, data: str) -> Optional[Dict]:
        """Parse incoming connection data"""
        # Look for connection patterns like +IPD,0,GET /path HTTP/1.1
        ipd_pattern = r'\+IPD,(\d+),(\d+):(.*)'
        connect_pattern = r'(\d+),CONNECT'
        closed_pattern = r'(\d+),CLOSED'

        if "+IPD" in data:
            match = re.search(ipd_pattern, data, re.DOTALL)
            if match:
                conn_id = int(match.group(1))
                length = int(match.group(2))
                content = match.group(3)

                # Parse HTTP request
                lines = content.split('\r\n')
                if lines and lines[0].startswith(('GET', 'POST', 'PUT', 'DELETE')):
                    parts = lines[0].split(' ')
                    method = parts[0]
                    path = parts[1] if len(parts) > 1 else '/'

                    return {
                        'type': 'http_request',
                        'connection_id': conn_id,
                        'method': method,
                        'path': path,
                        'length': length,
                        'timestamp': datetime.now(),
                        'raw_data': content
                    }

        elif "CONNECT" in data:
            match = re.search(connect_pattern, data)
            if match:
                conn_id = int(match.group(1))
                return {
                    'type': 'connection_open',
                    'connection_id': conn_id,
                    'timestamp': datetime.now()
                }

        elif "CLOSED" in data:
            match = re.search(closed_pattern, data)
            if match:
                conn_id = int(match.group(1))
                return {
                    'type': 'connection_closed',
                    'connection_id': conn_id,
                    'timestamp': datetime.now()
                }

        return None

    def log_event(self, event: Dict):
        """Log monitoring event"""
        timestamp_str = event['timestamp'].strftime("%H:%M:%S")

        if event['type'] == 'http_request':
            print(f"[{timestamp_str}] HTTP {event['method']} {event['path']} (conn: {event['connection_id']})")
            self.request_log.append(event)
            self.metrics['requests_total'] += 1

        elif event['type'] == 'connection_open':
            print(f"[{timestamp_str}] Connection {event['connection_id']} opened")
            self.connection_log.append(event)
            self.metrics['connections_total'] += 1

        elif event['type'] == 'connection_closed':
            print(f"[{timestamp_str}] Connection {event['connection_id']} closed")
            self.connection_log.append(event)

        self.metrics['last_activity'] = event['timestamp']

        # Store in database if enabled
        if self.database_enabled and self.db_manager:
            try:
                connection_event = ConnectionEvent(
                    timestamp=event['timestamp'],
                    event_type=event['type'],
                    connection_id=event['connection_id'],
                    method=event.get('method'),
                    path=event.get('path'),
                    length=event.get('length'),
                    raw_data=event.get('raw_data')
                )
                self.db_manager.store_connection_event(connection_event)
            except Exception as e:
                logger.warning(f"Failed to store event in database: {e}")

    def monitor_loop(self):
        """Main monitoring loop"""
        print("Starting ESP module monitoring...")
        print("Press Ctrl+C to stop")

        buffer = ""

        while self.monitoring and self.connected:
            try:
                # Check for commands from other threads
                try:
                    command = self.command_queue.get_nowait()
                    response = self.send_at_command(command)
                    self.response_queue.put(response)
                except queue.Empty:
                    pass

                # Read serial data
                if self.ser and self.ser.in_waiting > 0:
                    chunk = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                    buffer += chunk

                    # Process complete lines
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()

                        if line:
                            # Parse and log events
                            event = self.parse_connection_data(line)
                            if event:
                                self.log_event(event)
                            elif line and not line.startswith('AT'):
                                # Log other interesting data
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] {line}")

                # Periodic database updates
                now = datetime.now()

                # Update device status periodically
                if (now - self.last_status_update).total_seconds() >= self.status_update_interval:
                    self._update_device_status()
                    self.last_status_update = now

                # Update performance metrics periodically
                if (now - self.last_metrics_update).total_seconds() >= self.metrics_update_interval:
                    self._update_performance_metrics()
                    self.last_metrics_update = now

                time.sleep(0.1)

            except Exception as e:
                print(f"Monitoring error: {e}")
                self.metrics['errors_total'] += 1
                time.sleep(1)

    def start_monitoring(self):
        """Start monitoring in background thread"""
        if not self.connected:
            print("Not connected to ESP module")
            return False

        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        return True

    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)

    def get_device_status(self) -> Dict:
        """Get current device status"""
        if not self.connected:
            return {'status': 'disconnected', 'error': 'Not connected to device'}

        status = {
            'status': 'connected',
            'timestamp': datetime.now().isoformat(),
            'metrics': dict(self.metrics),
            'connection_info': {},
            'server_info': {}
        }

        # Get device info
        version_info = self.send_at_command("AT+GMR")
        status['device_info'] = version_info

        # Get WiFi status
        wifi_status = self.send_at_command("AT+CWJAP?")
        status['wifi_status'] = wifi_status

        # Get IP info
        ip_info = self.send_at_command("AT+CIFSR")
        status['ip_info'] = ip_info

        # Calculate uptime
        if self.metrics['uptime_start']:
            uptime = datetime.now() - self.metrics['uptime_start']
            status['uptime_seconds'] = int(uptime.total_seconds())
            status['uptime_formatted'] = str(uptime).split('.')[0]

        return status

    def get_logs(self, log_type: str = 'all', limit: int = 50) -> List[Dict]:
        """Get monitoring logs"""
        logs = []

        if log_type in ['all', 'connections']:
            logs.extend(list(self.connection_log)[-limit:])

        if log_type in ['all', 'requests']:
            logs.extend(list(self.request_log)[-limit:])

        # Sort by timestamp
        logs.sort(key=lambda x: x['timestamp'], reverse=True)

        # Convert timestamps to strings for JSON serialization
        for log in logs:
            log['timestamp'] = log['timestamp'].isoformat()

        return logs[:limit]

    def execute_command(self, command: str) -> str:
        """Execute AT command via monitoring thread"""
        if not self.monitoring:
            return self.send_at_command(command)

        # Send command via queue
        self.command_queue.put(command)

        # Wait for response
        try:
            response = self.response_queue.get(timeout=10)
            return response
        except queue.Empty:
            return "Command timeout"

    def reset_device(self) -> bool:
        """Reset ESP device"""
        print("Resetting ESP device...")
        response = self.execute_command("AT+RST")

        if "OK" in response:
            print("Device reset initiated")
            time.sleep(5)  # Wait for reset
            return True
        else:
            print("Reset failed")
            return False

    def get_metrics_summary(self) -> Dict:
        """Get performance metrics summary"""
        summary = dict(self.metrics)

        # Calculate rates
        if self.metrics['uptime_start']:
            uptime_hours = (datetime.now() - self.metrics['uptime_start']).total_seconds() / 3600
            if uptime_hours > 0:
                summary['connections_per_hour'] = round(self.metrics['connections_total'] / uptime_hours, 2)
                summary['requests_per_hour'] = round(self.metrics['requests_total'] / uptime_hours, 2)

        # Recent activity stats
        recent_requests = [r for r in self.request_log if (datetime.now() - r['timestamp']).seconds < 3600]
        summary['requests_last_hour'] = len(recent_requests)

        recent_connections = [c for c in self.connection_log if (datetime.now() - c['timestamp']).seconds < 3600]
        summary['connections_last_hour'] = len(recent_connections)

        return summary

    def _update_device_status(self):
        """Update device status in database"""
        if not self.database_enabled or not self.db_manager:
            return

        try:
            # Parse current device status
            wifi_status = self.send_at_command("AT+CWJAP?")
            ip_info = self.send_at_command("AT+CIFSR")

            # Extract WiFi connection status
            wifi_connected = "OK" in wifi_status and "No AP" not in wifi_status

            # Extract IP address
            ip_address = None
            if ip_info:
                ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', ip_info)
                if ip_match:
                    ip_address = ip_match.group(1)

            # Create device status record
            device_status = DeviceStatus(
                timestamp=datetime.now(),
                status='connected' if self.connected else 'disconnected',
                wifi_connected=wifi_connected,
                ip_address=ip_address,
                uptime_seconds=int((datetime.now() - self.metrics['uptime_start']).total_seconds()) if self.metrics['uptime_start'] else None
            )

            self.db_manager.store_device_status(device_status)

        except Exception as e:
            logger.warning(f"Failed to update device status: {e}")

    def _update_performance_metrics(self):
        """Update performance metrics in database"""
        if not self.database_enabled or not self.db_manager:
            return

        try:
            # Calculate rates
            uptime_hours = 0
            if self.metrics['uptime_start']:
                uptime_hours = (datetime.now() - self.metrics['uptime_start']).total_seconds() / 3600

            connections_per_hour = self.metrics['connections_total'] / max(uptime_hours, 1)
            requests_per_hour = self.metrics['requests_total'] / max(uptime_hours, 1)

            # Create performance metrics record
            performance_metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                connections_total=self.metrics['connections_total'],
                requests_total=self.metrics['requests_total'],
                errors_total=self.metrics['errors_total'],
                connections_per_hour=connections_per_hour,
                requests_per_hour=requests_per_hour
            )

            self.db_manager.store_performance_metrics(performance_metrics)

        except Exception as e:
            logger.warning(f"Failed to update performance metrics: {e}")

    def get_historical_data(self, data_type: str, hours: int = 24) -> List[Dict]:
        """Get historical data from database"""
        if not self.database_enabled or not self.db_manager:
            return []

        start_time = datetime.now() - timedelta(hours=hours)

        try:
            if data_type == 'connections':
                return self.db_manager.get_connection_events(start_time=start_time)
            elif data_type == 'status':
                return self.db_manager.get_device_status_history(start_time=start_time)
            elif data_type == 'metrics':
                return self.db_manager.get_performance_metrics_history(start_time=start_time)
            else:
                return []
        except Exception as e:
            logger.error(f"Failed to get historical data: {e}")
            return []

    def generate_report(self, report_type: str = 'html', hours: int = 24) -> str:
        """Generate performance report"""
        if not self.database_enabled or not self.report_generator:
            print("Database features not available. Cannot generate report.")
            return ""

        start_time = datetime.now() - timedelta(hours=hours)
        end_time = datetime.now()

        try:
            if report_type.lower() == 'html':
                filename = f"esp_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                return self.report_generator.generate_html_report(start_time, end_time, filename)
            elif report_type.lower() == 'pdf':
                filename = f"esp_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                return self.report_generator.generate_pdf_report(start_time, end_time, filename)
            else:
                return json.dumps(self.report_generator.generate_summary_report(start_time, end_time), indent=2)
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return ""

    def export_data(self, format_type: str = 'csv', hours: int = 24) -> Dict[str, str]:
        """Export monitoring data"""
        if not self.database_enabled or not self.db_manager:
            print("Database features not available. Cannot export data.")
            return {}

        start_time = datetime.now() - timedelta(hours=hours)
        end_time = datetime.now()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        try:
            exported_files = {}

            if format_type.lower() == 'csv':
                # Export connection events
                filename = f"connection_events_{timestamp}.csv"
                self.db_manager.export_to_csv("connection_events", filename, start_time, end_time)
                exported_files['connection_events'] = filename

                # Export device status
                filename = f"device_status_{timestamp}.csv"
                self.db_manager.export_to_csv("device_status", filename, start_time, end_time)
                exported_files['device_status'] = filename

                # Export performance metrics
                filename = f"performance_metrics_{timestamp}.csv"
                self.db_manager.export_to_csv("performance_metrics", filename, start_time, end_time)
                exported_files['performance_metrics'] = filename

            elif format_type.lower() == 'json':
                # Export connection events
                filename = f"connection_events_{timestamp}.json"
                self.db_manager.export_to_json("connection_events", filename, start_time, end_time)
                exported_files['connection_events'] = filename

            return exported_files

        except Exception as e:
            logger.error(f"Failed to export data: {e}")
            return {}

    def detect_anomalies(self) -> List[Dict]:
        """Detect performance anomalies"""
        if not self.database_enabled or not self.db_manager:
            return []

        try:
            return self.db_manager.detect_anomalies()
        except Exception as e:
            logger.error(f"Failed to detect anomalies: {e}")
            return []

    def cleanup_old_data(self, retention_days: int = 30):
        """Clean up old data based on retention policy"""
        if not self.database_enabled or not self.db_manager:
            return

        try:
            self.db_manager.cleanup_old_data(retention_days)
            print(f"Cleaned up data older than {retention_days} days")
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")

    def update_baselines(self):
        """Update performance baselines for anomaly detection"""
        if not self.database_enabled or not self.db_manager:
            return

        try:
            self.db_manager.update_performance_baselines()
            print("Performance baselines updated")
        except Exception as e:
            logger.error(f"Failed to update baselines: {e}")

    def get_statistics(self, hours: int = 24) -> Dict:
        """Get comprehensive statistics"""
        if not self.database_enabled or not self.db_manager:
            return self.get_metrics_summary()

        start_time = datetime.now() - timedelta(hours=hours)

        try:
            return self.db_manager.get_statistics(start_time)
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return self.get_metrics_summary()

    def close(self):
        """Clean shutdown of monitor"""
        self.stop_monitoring()
        self.disconnect()

        if self.database_enabled and self.db_manager:
            self.db_manager.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

class WebManagementServer:
    """Web interface for ESP monitoring"""

    def __init__(self, esp_monitor: ESPMonitor, port: int = 8080):
        self.esp_monitor = esp_monitor
        self.port = port
        self.httpd = None

    def start_server(self):
        """Start web management server"""
        handler = self.create_handler()
        self.httpd = socketserver.TCPServer(("", self.port), handler)
        print(f"Web management interface available at http://localhost:{self.port}")
        self.httpd.serve_forever()

    def create_handler(self):
        """Create HTTP request handler"""
        esp_monitor = self.esp_monitor

        class ESPHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/':
                    self.serve_dashboard()
                elif self.path == '/api/status':
                    self.serve_json(esp_monitor.get_device_status())
                elif self.path == '/api/logs':
                    self.serve_json(esp_monitor.get_logs())
                elif self.path == '/api/metrics':
                    self.serve_json(esp_monitor.get_metrics_summary())
                else:
                    self.send_error(404)

            def do_POST(self):
                if self.path == '/api/command':
                    self.handle_command()
                elif self.path == '/api/reset':
                    result = esp_monitor.reset_device()
                    self.serve_json({'success': result})
                else:
                    self.send_error(404)

            def serve_dashboard(self):
                html = self.get_dashboard_html()
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(html.encode())

            def serve_json(self, data):
                json_data = json.dumps(data, indent=2, default=str)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json_data.encode())

            def handle_command(self):
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length).decode('utf-8')
                data = json.loads(post_data)

                command = data.get('command', '')
                if command:
                    response = esp_monitor.execute_command(command)
                    self.serve_json({'command': command, 'response': response})
                else:
                    self.send_error(400)

            def get_dashboard_html(self):
                return """<!DOCTYPE html>
<html>
<head>
    <title>ESP Monitor Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status { padding: 10px; border-radius: 4px; margin: 10px 0; }
        .status.connected { background: #d4edda; color: #155724; }
        .status.disconnected { background: #f8d7da; color: #721c24; }
        .metric { display: inline-block; margin: 10px; padding: 10px; background: #e9ecef; border-radius: 4px; }
        .log-entry { padding: 5px; border-bottom: 1px solid #eee; font-family: monospace; font-size: 12px; }
        button { padding: 8px 16px; margin: 5px; border: none; border-radius: 4px; cursor: pointer; }
        .btn-primary { background: #007bff; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        #logs { max-height: 400px; overflow-y: auto; }
        input[type="text"] { padding: 8px; margin: 5px; border: 1px solid #ccc; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 ESP Monitor Dashboard</h1>

        <div class="card">
            <h2>Device Status</h2>
            <div id="device-status" class="status">Loading...</div>
            <button class="btn-primary" onclick="refreshStatus()">Refresh Status</button>
            <button class="btn-danger" onclick="resetDevice()">Reset Device</button>
        </div>

        <div class="card">
            <h2>Performance Metrics</h2>
            <div id="metrics">Loading...</div>
        </div>

        <div class="card">
            <h2>Command Interface</h2>
            <input type="text" id="command-input" placeholder="Enter AT command (e.g., AT+GMR)" style="width: 300px;">
            <button class="btn-primary" onclick="sendCommand()">Send Command</button>
            <div id="command-response" style="margin-top: 10px; font-family: monospace; background: #f8f9fa; padding: 10px; border-radius: 4px;"></div>
        </div>

        <div class="card">
            <h2>Activity Logs</h2>
            <button class="btn-primary" onclick="refreshLogs()">Refresh Logs</button>
            <div id="logs">Loading...</div>
        </div>
    </div>

    <script>
        function refreshStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    const statusDiv = document.getElementById('device-status');
                    const connected = data.status === 'connected';

                    statusDiv.className = 'status ' + (connected ? 'connected' : 'disconnected');
                    statusDiv.innerHTML = connected ?
                        `✓ Connected - Uptime: ${data.uptime_formatted || 'Unknown'}` :
                        '✗ Disconnected';

                    if (connected && data.ip_info) {
                        statusDiv.innerHTML += `<br>IP Info: ${data.ip_info.replace(/\\n/g, '<br>')}`;
                    }
                });
        }

        function refreshMetrics() {
            fetch('/api/metrics')
                .then(response => response.json())
                .then(data => {
                    const metricsDiv = document.getElementById('metrics');
                    metricsDiv.innerHTML = `
                        <div class="metric">Total Connections: ${data.connections_total}</div>
                        <div class="metric">Total Requests: ${data.requests_total}</div>
                        <div class="metric">Errors: ${data.errors_total}</div>
                        <div class="metric">Requests/Hour: ${data.requests_per_hour || 0}</div>
                        <div class="metric">Connections/Hour: ${data.connections_per_hour || 0}</div>
                    `;
                });
        }

        function refreshLogs() {
            fetch('/api/logs')
                .then(response => response.json())
                .then(data => {
                    const logsDiv = document.getElementById('logs');
                    logsDiv.innerHTML = data.map(log =>
                        `<div class="log-entry">[${log.timestamp}] ${log.type}: ${JSON.stringify(log)}</div>`
                    ).join('');
                });
        }

        function sendCommand() {
            const command = document.getElementById('command-input').value;
            if (!command) return;

            fetch('/api/command', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({command: command})
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('command-response').innerHTML =
                    `<strong>Command:</strong> ${data.command}<br><strong>Response:</strong><br>${data.response.replace(/\\n/g, '<br>')}`;
            });
        }

        function resetDevice() {
            if (confirm('Are you sure you want to reset the ESP device?')) {
                fetch('/api/reset', {method: 'POST'})
                    .then(response => response.json())
                    .then(data => {
                        alert(data.success ? 'Device reset successfully' : 'Reset failed');
                        setTimeout(refreshStatus, 5000);
                    });
            }
        }

        // Auto-refresh every 5 seconds
        setInterval(() => {
            refreshStatus();
            refreshMetrics();
        }, 5000);

        // Initial load
        refreshStatus();
        refreshMetrics();
        refreshLogs();

        // Enter key support for command input
        document.getElementById('command-input').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendCommand();
            }
        });
    </script>
</body>
</html>"""

        return ESPHandler

def main():
    parser = argparse.ArgumentParser(description='ESP Module Monitor and Management')
    parser.add_argument('--port', default='/dev/ttyUSB0', help='Serial port')
    parser.add_argument('--baudrate', type=int, default=115200, help='Baud rate')
    parser.add_argument('--command', help='Execute single AT command')
    parser.add_argument('--status', action='store_true', help='Get device status')
    parser.add_argument('--logs', action='store_true', help='Show recent logs')
    parser.add_argument('--reset', action='store_true', help='Reset ESP device')
    parser.add_argument('--web-interface', action='store_true', help='Start web management interface')
    parser.add_argument('--web-port', type=int, default=8080, help='Web interface port')
    parser.add_argument('--no-database', action='store_true', help='Disable database features')

    # New database and reporting arguments
    parser.add_argument('--generate-report', choices=['html', 'pdf', 'json'], help='Generate performance report')
    parser.add_argument('--report-hours', type=int, default=24, help='Hours of data to include in report')
    parser.add_argument('--export-data', choices=['csv', 'json'], help='Export monitoring data')
    parser.add_argument('--cleanup-data', type=int, metavar='DAYS', help='Clean up data older than specified days')
    parser.add_argument('--update-baselines', action='store_true', help='Update performance baselines')
    parser.add_argument('--detect-anomalies', action='store_true', help='Detect and display anomalies')
    parser.add_argument('--statistics', action='store_true', help='Show comprehensive statistics')
    parser.add_argument('--stats-hours', type=int, default=24, help='Hours of data for statistics')

    args = parser.parse_args()

    # Create monitor with database option
    enable_database = not args.no_database
    monitor = ESPMonitor(args.port, args.baudrate, enable_database=enable_database)

    try:
        # Handle database-only operations (don't require device connection)
        if args.generate_report:
            if not monitor.database_enabled:
                print("Database features not available. Cannot generate report.")
                return 1

            print(f"Generating {args.generate_report} report for last {args.report_hours} hours...")
            report_file = monitor.generate_report(args.generate_report, args.report_hours)
            if report_file:
                print(f"Report generated: {report_file}")
                return 0
            else:
                print("Failed to generate report")
                return 1

        if args.export_data:
            if not monitor.database_enabled:
                print("Database features not available. Cannot export data.")
                return 1

            print(f"Exporting data in {args.export_data} format...")
            exported_files = monitor.export_data(args.export_data, args.report_hours)
            if exported_files:
                print("Data exported to:")
                for table, filename in exported_files.items():
                    print(f"  {table}: {filename}")
                return 0
            else:
                print("Failed to export data")
                return 1

        if args.cleanup_data:
            if not monitor.database_enabled:
                print("Database features not available. Cannot cleanup data.")
                return 1

            monitor.cleanup_old_data(args.cleanup_data)
            return 0

        if args.update_baselines:
            if not monitor.database_enabled:
                print("Database features not available. Cannot update baselines.")
                return 1

            monitor.update_baselines()
            return 0

        if args.detect_anomalies:
            if not monitor.database_enabled:
                print("Database features not available. Cannot detect anomalies.")
                return 1

            anomalies = monitor.detect_anomalies()
            if anomalies:
                print(f"\n🚨 Found {len(anomalies)} anomalies:")
                for anomaly in anomalies:
                    print(f"  - {anomaly['metric_name']}: {anomaly['current_value']:.2f} "
                          f"(baseline: {anomaly['baseline_value']:.2f}, "
                          f"deviation: {anomaly['deviation']:.2f}, "
                          f"severity: {anomaly['severity']})")
            else:
                print("✅ No anomalies detected")
            return 0

        if args.statistics:
            stats = monitor.get_statistics(args.stats_hours)
            print(f"\n📊 Statistics for last {args.stats_hours} hours:")
            print(json.dumps(stats, indent=2, default=str))
            return 0

        # Connect to device for operations that require it
        if not monitor.connect():
            print("Failed to connect to ESP module")
            return 1

        # Handle single commands
        if args.command:
            response = monitor.send_at_command(args.command)
            print(f"Command: {args.command}")
            print(f"Response: {response}")
            return 0

        elif args.status:
            status = monitor.get_device_status()
            print(json.dumps(status, indent=2, default=str))
            return 0

        elif args.logs:
            logs = monitor.get_logs()
            for log in logs:
                print(f"[{log['timestamp']}] {log['type']}: {log}")
            return 0

        elif args.reset:
            success = monitor.reset_device()
            return 0 if success else 1

        elif args.web_interface:
            # Start monitoring in background
            monitor.start_monitoring()

            # Start web server
            web_server = WebManagementServer(monitor, args.web_port)
            try:
                web_server.start_server()
            except KeyboardInterrupt:
                print("\nStopping web server...")
            return 0

        else:
            # Default: start interactive monitoring
            monitor.start_monitoring()

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping monitoring...")
                return 0

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        # Clean shutdown
        monitor.close()

if __name__ == "__main__":
    import sys
    sys.exit(main())
