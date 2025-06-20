#!/usr/bin/env python3
"""
ESP Monitor Usage Examples
==========================
This script demonstrates various usage patterns and features of the
ESP Monitor with database persistence and reporting capabilities.

Run this script to see examples of:
- Basic monitoring setup
- Database operations
- Report generation
- Data analysis
- Advanced features

Usage:
    python3 usage_examples.py
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from esp_monitor import ESPMonitor
    from database_manager import DatabaseManager, ConnectionEvent, DeviceStatus, PerformanceMetrics
    from report_generator import ReportGenerator
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all dependencies are installed: pip install -r requirements.txt")
    IMPORTS_AVAILABLE = False


class ESPMonitorExamples:
    """Collection of usage examples for ESP Monitor"""

    def __init__(self):
        self.examples = {
            "1": ("Basic Monitoring Setup", self.example_basic_monitoring),
            "2": ("Database Operations", self.example_database_operations),
            "3": ("Report Generation", self.example_report_generation),
            "4": ("Data Export", self.example_data_export),
            "5": ("Performance Analysis", self.example_performance_analysis),
            "6": ("Anomaly Detection", self.example_anomaly_detection),
            "7": ("Historical Data Analysis", self.example_historical_analysis),
            "8": ("Custom Analytics", self.example_custom_analytics),
            "9": ("Maintenance Operations", self.example_maintenance_operations),
            "10": ("Integration Examples", self.example_integration)
        }

    def example_basic_monitoring(self):
        """Example 1: Basic monitoring setup"""
        print("\n" + "="*60)
        print("EXAMPLE 1: Basic Monitoring Setup")
        print("="*60)

        print("""
# Basic ESP monitoring with database persistence
from esp_monitor import ESPMonitor

# Create monitor instance
monitor = ESPMonitor(
    port='/dev/ttyUSB0',        # Serial port
    baudrate=115200,            # Baud rate
    enable_database=True        # Enable database features
)

try:
    # Connect to ESP device
    if monitor.connect():
        print("Connected to ESP device")

        # Start monitoring in background
        monitor.start_monitoring()

        # Monitor for 30 seconds
        time.sleep(30)

        # Get current status
        status = monitor.get_device_status()
        print(f"Device status: {status['status']}")

    else:
        print("Failed to connect to ESP device")

finally:
    # Clean shutdown
    monitor.close()
        """)

        print("\n📝 Key Points:")
        print("• ESP Monitor automatically creates SQLite database")
        print("• All events are stored persistently")
        print("• Use context manager for automatic cleanup")
        print("• Database features can be disabled with enable_database=False")

    def example_database_operations(self):
        """Example 2: Database operations"""
        print("\n" + "="*60)
        print("EXAMPLE 2: Database Operations")
        print("="*60)

        print("""
# Direct database operations
from database_manager import DatabaseManager, ConnectionEvent

# Create database manager
db = DatabaseManager("my_esp_monitoring.db")

# Store connection events
event = ConnectionEvent(
    timestamp=datetime.now(),
    event_type='http_request',
    connection_id=1,
    method='GET',
    path='/api/status',
    length=150,
    raw_data='GET /api/status HTTP/1.1\\r\\nHost: esp-device\\r\\n'
)
db.store_connection_event(event)

# Query recent events
recent_events = db.get_connection_events(
    start_time=datetime.now() - timedelta(hours=1),
    limit=50
)

# Get statistics
stats = db.get_statistics(
    start_time=datetime.now() - timedelta(days=1)
)

print(f"Total HTTP requests: {stats['connections']['http_requests']}")
print(f"WiFi uptime: {stats['device']['wifi_uptime_ratio']*100:.1f}%")

# Close database
db.close()
        """)

        print("\n📊 Available Data Types:")
        print("• connection_events: HTTP requests, connections")
        print("• device_status: WiFi, signal strength, memory, temperature")
        print("• performance_metrics: Rates, totals, response times")
        print("• performance_baselines: Statistical baselines for anomaly detection")

    def example_report_generation(self):
        """Example 3: Report generation"""
        print("\n" + "="*60)
        print("EXAMPLE 3: Report Generation")
        print("="*60)

        print("""
# Generate comprehensive reports
from report_generator import ReportGenerator
from database_manager import DatabaseManager

# Initialize
db = DatabaseManager("esp_monitoring.db")
reporter = ReportGenerator(db)

# Generate HTML report (interactive charts)
html_report = reporter.generate_html_report(
    start_time=datetime.now() - timedelta(hours=24),
    end_time=datetime.now(),
    output_file="daily_report.html"
)
print(f"HTML report generated: {html_report}")

# Generate PDF report (for documentation)
pdf_report = reporter.generate_pdf_report(
    start_time=datetime.now() - timedelta(days=7),
    end_time=datetime.now(),
    output_file="weekly_report.pdf"
)
print(f"PDF report generated: {pdf_report}")

# Generate JSON summary (for APIs)
summary = reporter.generate_summary_report(
    start_time=datetime.now() - timedelta(hours=6)
)
print(f"Requests in last 6 hours: {summary['performance']['avg_requests_per_hour']}")

# Batch export for external analysis
exported_files = reporter.export_data_for_external_analysis(
    start_time=datetime.now() - timedelta(days=30),
    output_dir="exports"
)
print(f"Exported {len(exported_files)} files")
        """)

        print("\n📄 Report Features:")
        print("• HTML: Interactive charts, responsive design, real-time metrics")
        print("• PDF: Professional layout, high-quality charts, print-ready")
        print("• JSON: Machine-readable, structured data, API-friendly")
        print("• Batch exports: Multiple formats, configurable time ranges")

    def example_data_export(self):
        """Example 4: Data export"""
        print("\n" + "="*60)
        print("EXAMPLE 4: Data Export")
        print("="*60)

        print("""
# Export data in various formats
from database_manager import DatabaseManager

db = DatabaseManager("esp_monitoring.db")

# Export to CSV for spreadsheet analysis
db.export_to_csv(
    table_name="connection_events",
    file_path="connection_events.csv",
    start_time=datetime.now() - timedelta(days=7)
)

# Export to JSON for programmatic processing
db.export_to_json(
    table_name="performance_metrics",
    file_path="performance_metrics.json",
    start_time=datetime.now() - timedelta(days=30)
)

# Batch export using ESP Monitor
from esp_monitor import ESPMonitor

monitor = ESPMonitor(enable_database=True)
exported_files = monitor.export_data(
    format_type='csv',
    hours=168  # Last week
)

for table, filename in exported_files.items():
    print(f"Exported {table} to {filename}")
        """)

        print("\n💾 Export Options:")
        print("• CSV: Excel-compatible, easy analysis, pivot tables")
        print("• JSON: Programming-friendly, API integration, web apps")
        print("• Custom time ranges: Hours, days, weeks, months")
        print("• Selective exports: Choose specific tables or metrics")

    def example_performance_analysis(self):
        """Example 5: Performance analysis"""
        print("\n" + "="*60)
        print("EXAMPLE 5: Performance Analysis")
        print("="*60)

        print("""
# Analyze ESP device performance
from esp_monitor import ESPMonitor

monitor = ESPMonitor(enable_database=True)

# Get comprehensive statistics
stats = monitor.get_statistics(hours=48)  # Last 48 hours

print("Performance Summary:")
print(f"Total connections: {stats['connections']['connections_opened']}")
print(f"Total requests: {stats['connections']['http_requests']}")
print(f"Error count: {stats['connections'].get('errors', 0)}")
print(f"WiFi uptime: {stats['device']['wifi_uptime_ratio']*100:.1f}%")
print(f"Avg signal strength: {stats['device']['avg_signal_strength']:.1f} dBm")

# Analyze request patterns
top_paths = stats['requests']['top_paths']
print("\\nMost requested paths:")
for path_info in top_paths[:5]:
    print(f"  {path_info['path']}: {path_info['count']} requests")

# Method distribution
methods = stats['requests']['by_method']
print("\\nRequest methods:")
for method, count in methods.items():
    print(f"  {method}: {count}")

# Historical trends
historical_data = monitor.get_historical_data('metrics', hours=168)
if historical_data:
    recent_metrics = historical_data[:10]  # Last 10 data points
    avg_response_time = sum(m.get('response_time_avg', 0) for m in recent_metrics) / len(recent_metrics)
    print(f"\\nAvg response time: {avg_response_time:.1f} ms")
        """)

        print("\n📈 Analysis Capabilities:")
        print("• Traffic patterns: Peak hours, request frequency")
        print("• Performance trends: Response times, error rates")
        print("• Resource usage: Memory, temperature, signal strength")
        print("• Endpoint analysis: Most/least used paths, methods")

    def example_anomaly_detection(self):
        """Example 6: Anomaly detection"""
        print("\n" + "="*60)
        print("EXAMPLE 6: Anomaly Detection")
        print("="*60)

        print("""
# Automated anomaly detection
from esp_monitor import ESPMonitor

monitor = ESPMonitor(enable_database=True)

# Update performance baselines (run periodically)
monitor.update_baselines()
print("Performance baselines updated")

# Detect current anomalies
anomalies = monitor.detect_anomalies()

if anomalies:
    print(f"⚠️  Found {len(anomalies)} anomalies:")

    for anomaly in anomalies:
        severity_icon = "🔴" if anomaly['severity'] == 'high' else "🟡"
        print(f"{severity_icon} {anomaly['metric_name']}:")
        print(f"   Current: {anomaly['current_value']:.2f}")
        print(f"   Baseline: {anomaly['baseline_value']:.2f}")
        print(f"   Deviation: {anomaly['deviation']:.2f}")
        print(f"   Severity: {anomaly['severity']}")
        print()

    # Take action on high-severity anomalies
    high_severity = [a for a in anomalies if a['severity'] == 'high']
    if high_severity:
        print("🚨 High-severity anomalies detected!")
        print("Recommended actions:")
        print("• Check device connectivity")
        print("• Review recent configuration changes")
        print("• Monitor device temperature and memory")

else:
    print("✅ No anomalies detected - system operating normally")

# Custom anomaly detection with different threshold
custom_anomalies = monitor.db_manager.detect_anomalies(threshold_multiplier=1.5)
print(f"With stricter threshold: {len(custom_anomalies)} anomalies")
        """)

        print("\n🎯 Anomaly Detection Features:")
        print("• Statistical baselines: Z-score based detection")
        print("• Multiple metrics: Connections, requests, response times")
        print("• Severity levels: High, medium alerts")
        print("• Configurable thresholds: Adjust sensitivity")

    def example_historical_analysis(self):
        """Example 7: Historical data analysis"""
        print("\n" + "="*60)
        print("EXAMPLE 7: Historical Data Analysis")
        print("="*60)

        print("""
# Analyze historical trends
from esp_monitor import ESPMonitor
from datetime import datetime, timedelta
import statistics

monitor = ESPMonitor(enable_database=True)

# Get historical metrics for trend analysis
week_ago = datetime.now() - timedelta(days=7)
metrics_history = monitor.db_manager.get_performance_metrics_history(
    start_time=week_ago,
    limit=168  # Hourly data for a week
)

if metrics_history:
    # Calculate trends
    request_rates = [m['requests_per_hour'] for m in metrics_history]
    connection_rates = [m['connections_per_hour'] for m in metrics_history]

    print("Weekly Performance Trends:")
    print(f"Avg requests/hour: {statistics.mean(request_rates):.1f}")
    print(f"Peak requests/hour: {max(request_rates):.1f}")
    print(f"Min requests/hour: {min(request_rates):.1f}")
    print(f"Request rate std dev: {statistics.stdev(request_rates):.1f}")

    # Identify patterns
    print("\\nTraffic Patterns:")

    # Group by day of week
    daily_averages = {}
    for i, metric in enumerate(metrics_history):
        day_of_week = (week_ago + timedelta(hours=i)).strftime('%A')
        if day_of_week not in daily_averages:
            daily_averages[day_of_week] = []
        daily_averages[day_of_week].append(metric['requests_per_hour'])

    for day, rates in daily_averages.items():
        avg_rate = statistics.mean(rates)
        print(f"{day}: {avg_rate:.1f} requests/hour")

# Device health trends
status_history = monitor.db_manager.get_device_status_history(
    start_time=week_ago,
    limit=168
)

if status_history:
    # WiFi stability analysis
    wifi_connected = [s['wifi_connected'] for s in status_history]
    wifi_uptime = sum(wifi_connected) / len(wifi_connected) * 100

    # Temperature analysis
    temperatures = [s['temperature'] for s in status_history if s['temperature']]
    if temperatures:
        avg_temp = statistics.mean(temperatures)
        max_temp = max(temperatures)
        print(f"\\nDevice Health (7 days):")
        print(f"WiFi uptime: {wifi_uptime:.1f}%")
        print(f"Avg temperature: {avg_temp:.1f}°C")
        print(f"Max temperature: {max_temp:.1f}°C")

        if max_temp > 70:
            print("⚠️  High temperature detected - check cooling")
        """)

        print("\n📊 Historical Analysis Features:")
        print("• Trend identification: Growth, decline, stability")
        print("• Pattern recognition: Daily, weekly, seasonal")
        print("• Health monitoring: Temperature, connectivity, memory")
        print("• Comparative analysis: Period-over-period comparison")

    def example_custom_analytics(self):
        """Example 8: Custom analytics"""
        print("\n" + "="*60)
        print("EXAMPLE 8: Custom Analytics")
        print("="*60)

        print("""
# Custom analytics and insights
from database_manager import DatabaseManager
import sqlite3

db = DatabaseManager("esp_monitoring.db")

# Custom SQL queries for specific insights
def analyze_request_patterns():
    \"\"\"Analyze request patterns by time of day\"\"\"

    query = '''
    SELECT
        strftime('%H', timestamp) as hour,
        COUNT(*) as request_count,
        AVG(length) as avg_request_size
    FROM connection_events
    WHERE event_type = 'http_request'
        AND timestamp >= datetime('now', '-7 days')
    GROUP BY strftime('%H', timestamp)
    ORDER BY hour
    '''

    cursor = db.conn.execute(query)
    results = cursor.fetchall()

    print("Hourly Request Patterns (Last 7 days):")
    for row in results:
        print(f"Hour {row['hour']:02d}: {row['request_count']} requests, "
              f"avg size: {row['avg_request_size']:.0f} bytes")

# Custom performance metrics
def calculate_custom_metrics():
    \"\"\"Calculate custom performance metrics\"\"\"

    # Error rate analysis
    error_query = '''
    SELECT
        DATE(timestamp) as date,
        SUM(errors_total) as daily_errors,
        MAX(requests_total) as daily_requests
    FROM performance_metrics
    WHERE timestamp >= datetime('now', '-30 days')
    GROUP BY DATE(timestamp)
    ORDER BY date DESC
    '''

    cursor = db.conn.execute(error_query)
    results = cursor.fetchall()

    print("\\nDaily Error Rates (Last 30 days):")
    for row in results:
        if row['daily_requests'] > 0:
            error_rate = (row['daily_errors'] / row['daily_requests']) * 100
            print(f"{row['date']}: {error_rate:.2f}% error rate")

# Device reliability analysis
def analyze_reliability():
    \"\"\"Analyze device reliability patterns\"\"\"

    uptime_query = '''
    SELECT
        DATE(timestamp) as date,
        AVG(CASE WHEN wifi_connected THEN 1 ELSE 0 END) as wifi_uptime,
        AVG(signal_strength) as avg_signal,
        COUNT(*) as status_checks
    FROM device_status
    WHERE timestamp >= datetime('now', '-30 days')
    GROUP BY DATE(timestamp)
    ORDER BY date DESC
    LIMIT 10
    '''

    cursor = db.conn.execute(uptime_query)
    results = cursor.fetchall()

    print("\\nDaily Reliability Metrics:")
    for row in results:
        print(f"{row['date']}: "
              f"WiFi {row['wifi_uptime']*100:.1f}%, "
              f"Signal {row['avg_signal']:.1f}dBm, "
              f"{row['status_checks']} checks")

# Run custom analytics
analyze_request_patterns()
calculate_custom_metrics()
analyze_reliability()

# Export custom analysis results
custom_data = {
    'analysis_date': datetime.now().isoformat(),
    'request_patterns': dict(cursor.fetchall()),
    'reliability_metrics': 'custom_analysis_results'
}

with open('custom_analysis.json', 'w') as f:
    json.dump(custom_data, f, indent=2, default=str)
        """)

        print("\n🔍 Custom Analytics Benefits:")
        print("• SQL queries: Direct database access for complex analysis")
        print("• Custom metrics: Define your own KPIs and measurements")
        print("• Data correlation: Find relationships between different metrics")
        print("• Flexible reporting: Create reports tailored to your needs")

    def example_maintenance_operations(self):
        """Example 9: Maintenance operations"""
        print("\n" + "="*60)
        print("EXAMPLE 9: Maintenance Operations")
        print("="*60)

        print("""
# Database maintenance and optimization
from esp_monitor import ESPMonitor

monitor = ESPMonitor(enable_database=True)

# Regular maintenance tasks
def perform_maintenance():
    \"\"\"Perform regular database maintenance\"\"\"

    print("🔧 Performing database maintenance...")

    # 1. Clean up old data (keep last 30 days)
    print("Cleaning up old data...")
    monitor.cleanup_old_data(retention_days=30)

    # 2. Update performance baselines
    print("Updating performance baselines...")
    monitor.update_baselines()

    # 3. Database optimization (SQLite specific)
    print("Optimizing database...")
    monitor.db_manager.conn.execute("VACUUM")
    monitor.db_manager.conn.execute("ANALYZE")

    # 4. Check database integrity
    print("Checking database integrity...")
    cursor = monitor.db_manager.conn.execute("PRAGMA integrity_check")
    result = cursor.fetchone()
    if result[0] == 'ok':
        print("✅ Database integrity OK")
    else:
        print("⚠️  Database integrity issues detected")

    # 5. Get database size
    import os
    db_size = os.path.getsize(monitor.db_manager.db_path)
    print(f"Database size: {db_size / 1024 / 1024:.1f} MB")

    print("Maintenance completed!")

# Backup operations
def backup_database():
    \"\"\"Create database backup\"\"\"

    import shutil
    from datetime import datetime

    backup_name = f"esp_monitoring_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(monitor.db_manager.db_path, backup_name)
    print(f"Backup created: {backup_name}")

# Health check
def health_check():
    \"\"\"Perform system health check\"\"\"

    print("🏥 System Health Check:")

    # Check recent data
    recent_events = monitor.db_manager.get_connection_events(limit=10)
    if recent_events:
        last_event = recent_events[0]['timestamp']
        print(f"✅ Recent activity: {last_event}")
    else:
        print("⚠️  No recent activity")

    # Check anomalies
    anomalies = monitor.detect_anomalies()
    if anomalies:
        print(f"⚠️  {len(anomalies)} anomalies detected")
    else:
        print("✅ No anomalies detected")

    # Check database size
    stats = monitor.get_statistics(hours=24)
    print(f"📊 24h stats: {stats['connections']['total_events']} events")

# Schedule maintenance (example with cron-like functionality)
def schedule_maintenance():
    \"\"\"Example of scheduled maintenance\"\"\"

    import schedule
    import time

    # Schedule daily maintenance at 3 AM
    schedule.every().day.at("03:00").do(perform_maintenance)

    # Schedule weekly backup on Sundays
    schedule.every().sunday.at("02:00").do(backup_database)

    # Schedule hourly health checks
    schedule.every().hour.do(health_check)

    print("Maintenance scheduled:")
    print("• Daily maintenance: 3:00 AM")
    print("• Weekly backup: Sunday 2:00 AM")
    print("• Hourly health checks")

    # Run scheduler (in production, this would be a daemon)
    # while True:
    #     schedule.run_pending()
    #     time.sleep(60)

# Run maintenance examples
perform_maintenance()
health_check()
backup_database()
        """)

        print("\n🛠️ Maintenance Best Practices:")
        print("• Regular cleanup: Remove old data to maintain performance")
        print("• Baseline updates: Keep anomaly detection accurate")
        print("• Database optimization: VACUUM and ANALYZE for SQLite")
        print("• Backup strategy: Regular backups before maintenance")

    def example_integration(self):
        """Example 10: Integration examples"""
        print("\n" + "="*60)
        print("EXAMPLE 10: Integration Examples")
        print("="*60)

        print("""
# Integration with external systems
from esp_monitor import ESPMonitor
import requests
import json

monitor = ESPMonitor(enable_database=True)

# 1. REST API Integration
def create_monitoring_api():
    \"\"\"Create REST API endpoints for monitoring data\"\"\"

    from flask import Flask, jsonify

    app = Flask(__name__)

    @app.route('/api/status')
    def get_status():
        if monitor.connected:
            status = monitor.get_device_status()
            return jsonify(status)
        else:
            return jsonify({'error': 'Device not connected'}), 503

    @app.route('/api/stats/<int:hours>')
    def get_stats(hours):
        stats = monitor.get_statistics(hours=hours)
        return jsonify(stats)

    @app.route('/api/anomalies')
    def get_anomalies():
        anomalies = monitor.detect_anomalies()
        return jsonify(anomalies)

    @app.route('/api/export/<format>')
    def export_data(format):
        if format in ['csv', 'json']:
            files = monitor.export_data(format_type=format, hours=24)
            return jsonify({'exported_files': files})
        else:
            return jsonify({'error': 'Invalid format'}), 400

    return app

# 2. Webhook Integration
def setup_webhooks():
    \"\"\"Send data to external webhooks\"\"\"

    def send_webhook(url, data):
        try:
            response = requests.post(url, json=data, timeout=10)
            return response.status_code == 200
        except:
            return False

    # Monitor for anomalies and send alerts
    anomalies = monitor.detect_anomalies()

    if anomalies:
        webhook_data = {
            'timestamp': datetime.now().isoformat(),
            'alert_type': 'anomaly_detected',
            'anomaly_count': len(anomalies),
            'anomalies': anomalies[:5]  # Send top 5
        }

        # Send to Slack webhook
        slack_webhook = "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
        slack_message = {
            'text': f"🚨 ESP Monitor Alert: {len(anomalies)} anomalies detected",
            'attachments': [{
                'color': 'danger',
                'fields': [{
                    'title': f"Anomaly: {a['metric_name']}",
                    'value': f"Current: {a['current_value']:.2f}, Baseline: {a['baseline_value']:.2f}",
                    'short': True
                } for a in anomalies[:3]]
            }]
        }

        success = send_webhook(slack_webhook, slack_message)
        print(f"Slack webhook: {'✅' if success else '❌'}")

# 3. Database Integration
def sync_to_external_db():
    \"\"\"Sync data to external database\"\"\"

    # Example: Sync to PostgreSQL
    import psycopg2
    from psycopg2.extras import RealDictCursor

    # Get recent data
    recent_events = monitor.get_historical_data('connections', hours=1)

    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host="localhost",
            database="esp_monitoring",
            user="monitor_user",
            password="password"
        )

        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Insert events
        for event in recent_events:
            cursor.execute('''
                INSERT INTO esp_events (timestamp, event_type, connection_id, method, path)
                VALUES (%(timestamp)s, %(event_type)s, %(connection_id)s, %(method)s, %(path)s)
                ON CONFLICT DO NOTHING
            ''', event)

        conn.commit()
        print(f"Synced {len(recent_events)} events to PostgreSQL")

    except Exception as e:
        print(f"PostgreSQL sync failed: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

# 4. Monitoring Dashboard Integration
def export_for_grafana():
    \"\"\"Export data for Grafana dashboard\"\"\"

    # Export metrics in Grafana-friendly format
    metrics = monitor.get_historical_data('metrics', hours=24)

    grafana_data = []
    for metric in metrics:
        grafana_data.append({
            'timestamp': int(datetime.fromisoformat(metric['timestamp']).timestamp() * 1000),
            'connections_per_hour': metric['connections_per_hour'],
            'requests_per_hour': metric['requests_per_hour'],
            'errors_total': metric['errors_total']
        })

    # Save for Grafana JSON data source
    with open('grafana_metrics.json', 'w') as f:
        json.dump(grafana_data, f)

    print("Grafana data exported to grafana_metrics.json")

# 5. Home Assistant Integration
def home_assistant_sensors():
    \"\"\"Create Home Assistant sensor configuration\"\"\"

    stats = monitor.get_statistics(hours=1)

    ha_config = {
        'sensor': [
            {
                'platform': 'command_line',
                'name': 'ESP Device Status',
                'command': 'python3 /path/to/esp_monitor.py --status | jq -r .status',
                'scan_interval': 60
            },
            {
                'platform': 'rest',
                'name': 'ESP Request Rate',
                'resource': 'http://localhost:8080/api/stats/1',
                'value_template': '{{ value_json.connections.http_requests }}',
                'unit_of_measurement': 'requests/hour'
            }
        ]
    }

    with open('home_assistant_config.yaml', 'w') as f:
        import yaml
        yaml.dump(ha_config, f)

    print("Home Assistant configuration generated")

# Run integration examples
print("Setting up integrations...")

# Note: These would typically run as separate services
# create_monitoring_api()  # Flask API
# setup_webhooks()         # Webhook alerts
# sync_to_external_db()    # Database sync
export_for_grafana()       # Grafana export
# home_assistant_sensors() # Home Assistant
        """)

        print("\n🔗 Integration Possibilities:")
        print("• REST APIs: Flask, FastAPI, Django integration")
        print("• Webhooks: Slack, Discord, custom endpoints")
        print("• Databases: PostgreSQL, MySQL, InfluxDB sync")
        print("• Dashboards: Grafana, Home Assistant, custom UIs")
        print("• Cloud services: AWS, Azure, Google Cloud")

    def run_all_examples(self):
        """Run all examples"""
        if not IMPORTS_AVAILABLE:
            print("❌ Cannot run examples - dependencies not available")
            print("Please install dependencies: pip install -r requirements.txt")
            return

        print("🚀 ESP Monitor Usage Examples")
        print("=" * 80)
        print("This script demonstrates various features and usage patterns")
        print("of the ESP Monitor with database persistence and reporting.")
        print("\nNote: Examples are for demonstration - actual ESP device not required")
        print("=" * 80)

        for key, (title, example_func) in self.examples.items():
            try:
                example_func()
                input(f"\nPress Enter to continue to next example...")
            except KeyboardInterrupt:
                print("\n\nExamples interrupted by user")
                break
            except Exception as e:
                print(f"\n❌ Error in example {key}: {e}")
                continue

        print("\n🎉 All examples completed!")
        print("\nNext Steps:")
        print("• Try running: python3 esp_monitor.py --help")
        print("• Generate a demo report: python3 demo_database_features.py")
        print("• Test the features: python3 test_database_features.py")
        print("• Start monitoring: python3 esp_monitor.py")

    def run_interactive_menu(self):
        """Run interactive menu for examples"""
        if not IMPORTS_AVAILABLE:
            print("❌ Cannot run examples - dependencies not available")
            print("Please install dependencies: pip install -r requirements.txt")
            return

        while True:
            print("\n" + "="*60)
            print("ESP Monitor Usage Examples - Interactive Menu")
            print("="*60)
            print("Select an example to run:")
            print()

            for key, (title, _) in self.examples.items():
                print(f"{key:2}. {title}")

            print()
            print(" a. Run all examples")
            print(" q. Quit")
            print()

            choice = input("Enter your choice: ").strip().lower()

            if choice == 'q':
                print("Goodbye!")
                break
            elif choice == 'a':
                self.run_all_examples()
                break
            elif choice in self.examples:
                title, example_func = self.examples[choice]
                try:
                    example_func()
                    input("\nPress Enter to return to menu...")
                except KeyboardInterrupt:
                    print("\n\nExample interrupted")
                    break
                except Exception as e:
                    print(f"\n❌ Error: {e}")
                    input("Press Enter to continue...")
            else:
                print("Invalid choice. Please try again.")


def main():
    """Main function"""
    examples = ESPMonitorExamples()

    print("ESP Monitor Usage Examples")
    print("Choose how to run examples:")
    print("1. Interactive menu")
    print("2. Run all examples")
    print("3. Exit")

    choice = input("\nEnter choice (1-3): ").strip()

    if choice == '1':
        examples.run_interactive_menu()
    elif choice == '2':
        examples.run_all_examples()
    elif choice == '3':
        print("Goodbye!")
    else:
        print("Invalid choice")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
