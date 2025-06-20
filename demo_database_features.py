#!/usr/bin/env python3
"""
ESP Monitor Database Features Demo
==================================
This script demonstrates all the new database persistence and reporting features
added to the ESP Monitor system.

Features demonstrated:
- Database initialization and data storage
- Historical data analysis
- Performance metrics tracking
- Anomaly detection
- Report generation (HTML, PDF, JSON)
- Data export capabilities
- Baseline management
- Data retention policies

Usage:
    python3 demo_database_features.py
"""

import os
import sys
import time
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from database_manager import DatabaseManager, ConnectionEvent, DeviceStatus, PerformanceMetrics
    from report_generator import ReportGenerator
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)

class ESPMonitorDemo:
    """Demo class to showcase database features"""

    def __init__(self):
        self.db_manager = None
        self.report_generator = None
        self.demo_data_generated = False

    def initialize_database(self):
        """Initialize database connection"""
        print("🔧 Initializing database...")
        try:
            # Use a demo database file
            self.db_manager = DatabaseManager("demo_esp_monitoring.db")
            self.report_generator = ReportGenerator(self.db_manager)
            print("✅ Database initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            return False

    def generate_sample_data(self, days_back: int = 7, events_per_hour: int = 10):
        """Generate sample monitoring data for demonstration"""
        print(f"📊 Generating sample data for {days_back} days...")

        start_time = datetime.now() - timedelta(days=days_back)
        current_time = start_time

        connection_id_counter = 0
        total_connections = 0
        total_requests = 0
        total_errors = 0

        # Generate data hour by hour
        while current_time < datetime.now():
            # Generate connection events for this hour
            events_this_hour = random.randint(max(1, events_per_hour - 5), events_per_hour + 10)

            for _ in range(events_this_hour):
                # Random event time within the hour
                event_time = current_time + timedelta(
                    minutes=random.randint(0, 59),
                    seconds=random.randint(0, 59)
                )

                # Generate different types of events
                event_type = random.choices(
                    ['connection_open', 'http_request', 'connection_closed'],
                    weights=[2, 7, 1]  # More HTTP requests than connections
                )[0]

                if event_type == 'connection_open':
                    connection_id_counter += 1
                    event = ConnectionEvent(
                        timestamp=event_time,
                        event_type='open',
                        connection_id=connection_id_counter
                    )
                    total_connections += 1

                elif event_type == 'http_request':
                    # Sample HTTP methods and paths
                    methods = ['GET', 'POST', 'PUT', 'DELETE']
                    paths = ['/', '/api/status', '/api/data', '/config', '/update', '/info', '/metrics']

                    method = random.choice(methods)
                    path = random.choice(paths)

                    event = ConnectionEvent(
                        timestamp=event_time,
                        event_type='http_request',
                        connection_id=random.randint(1, max(1, connection_id_counter)),
                        method=method,
                        path=path,
                        length=random.randint(50, 1500),
                        raw_data=f"{method} {path} HTTP/1.1\r\nHost: esp-device\r\n\r\n"
                    )
                    total_requests += 1

                elif event_type == 'connection_closed':
                    event = ConnectionEvent(
                        timestamp=event_time,
                        event_type='closed',
                        connection_id=random.randint(1, max(1, connection_id_counter))
                    )

                # Store event in database
                self.db_manager.store_connection_event(event)

            # Generate device status for this hour
            # Simulate some variability in device health
            wifi_connected = random.random() > 0.05  # 95% uptime
            signal_strength = random.randint(-80, -30) if wifi_connected else None
            memory_free = random.randint(50000, 150000)
            temperature = random.uniform(25.0, 45.0)
            uptime = int((current_time - start_time).total_seconds())

            device_status = DeviceStatus(
                timestamp=current_time,
                status='connected' if wifi_connected else 'disconnected',
                wifi_connected=wifi_connected,
                ip_address="192.168.1.100" if wifi_connected else None,
                signal_strength=signal_strength,
                memory_free=memory_free,
                uptime_seconds=uptime,
                temperature=temperature
            )

            self.db_manager.store_device_status(device_status)

            # Generate performance metrics
            hours_elapsed = (current_time - start_time).total_seconds() / 3600
            connections_per_hour = total_connections / max(hours_elapsed, 1)
            requests_per_hour = total_requests / max(hours_elapsed, 1)

            # Simulate some errors occasionally
            if random.random() < 0.1:  # 10% chance of errors
                total_errors += random.randint(1, 3)

            performance_metrics = PerformanceMetrics(
                timestamp=current_time,
                connections_total=total_connections,
                requests_total=total_requests,
                errors_total=total_errors,
                connections_per_hour=connections_per_hour,
                requests_per_hour=requests_per_hour,
                response_time_avg=random.uniform(50, 200)  # Simulated response time in ms
            )

            self.db_manager.store_performance_metrics(performance_metrics)

            # Move to next hour
            current_time += timedelta(hours=1)

        print(f"✅ Generated {total_connections} connections, {total_requests} requests, {total_errors} errors")
        self.demo_data_generated = True

    def demonstrate_data_retrieval(self):
        """Demonstrate various data retrieval methods"""
        print("\n📋 Demonstrating data retrieval...")

        # Get recent connection events
        print("🔗 Recent connection events:")
        events = self.db_manager.get_connection_events(limit=5)
        for event in events[:3]:  # Show first 3
            print(f"  [{event['timestamp']}] {event['event_type']}: "
                  f"conn_id={event['connection_id']}, "
                  f"method={event.get('method', 'N/A')}, "
                  f"path={event.get('path', 'N/A')}")
        print(f"  ... and {len(events)-3} more events")

        # Get device status history
        print("\n📱 Recent device status:")
        status_history = self.db_manager.get_device_status_history(limit=5)
        for status in status_history[:3]:
            print(f"  [{status['timestamp']}] Status: {status['status']}, "
                  f"WiFi: {'✅' if status['wifi_connected'] else '❌'}, "
                  f"Signal: {status['signal_strength']}dBm, "
                  f"Temp: {status['temperature']:.1f}°C")

        # Get performance metrics
        print("\n📈 Recent performance metrics:")
        metrics = self.db_manager.get_performance_metrics_history(limit=5)
        for metric in metrics[:3]:
            print(f"  [{metric['timestamp']}] "
                  f"Connections/h: {metric['connections_per_hour']:.1f}, "
                  f"Requests/h: {metric['requests_per_hour']:.1f}, "
                  f"Errors: {metric['errors_total']}")

    def demonstrate_statistics(self):
        """Demonstrate statistical analysis"""
        print("\n📊 Demonstrating statistical analysis...")

        # Get statistics for last 24 hours
        start_time = datetime.now() - timedelta(hours=24)
        stats = self.db_manager.get_statistics(start_time)

        print("📈 Statistics for last 24 hours:")
        print(f"  Total events: {stats.get('connections', {}).get('total_events', 0)}")
        print(f"  HTTP requests: {stats.get('connections', {}).get('http_requests', 0)}")
        print(f"  Connections opened: {stats.get('connections', {}).get('connections_opened', 0)}")
        print(f"  WiFi uptime: {stats.get('device', {}).get('wifi_uptime_ratio', 0)*100:.1f}%")
        print(f"  Avg signal strength: {stats.get('device', {}).get('avg_signal_strength', 0):.1f}dBm")
        print(f"  Avg temperature: {stats.get('device', {}).get('avg_temperature', 0):.1f}°C")

        # Show top requested paths
        top_paths = stats.get('requests', {}).get('top_paths', [])
        if top_paths:
            print("\n🔝 Most requested paths:")
            for path_info in top_paths[:5]:
                print(f"  {path_info['path']}: {path_info['count']} requests")

        # Show request methods breakdown
        by_method = stats.get('requests', {}).get('by_method', {})
        if by_method:
            print("\n🔧 Requests by method:")
            for method, count in by_method.items():
                print(f"  {method}: {count}")

    def demonstrate_baselines_and_anomalies(self):
        """Demonstrate baseline calculation and anomaly detection"""
        print("\n🎯 Demonstrating baseline calculation and anomaly detection...")

        # Update performance baselines
        print("📏 Updating performance baselines...")
        self.db_manager.update_performance_baselines()

        # Inject some anomalous data to demonstrate detection
        print("⚠️  Injecting anomalous data...")

        # Add some unusual high traffic
        anomaly_time = datetime.now() - timedelta(minutes=10)

        anomalous_metrics = PerformanceMetrics(
            timestamp=anomaly_time,
            connections_total=1000,  # Abnormally high
            requests_total=5000,     # Abnormally high
            errors_total=50,         # Many errors
            connections_per_hour=500,  # Very high rate
            requests_per_hour=2500,    # Very high rate
            response_time_avg=5000     # Very slow response
        )

        self.db_manager.store_performance_metrics(anomalous_metrics)

        # Detect anomalies
        print("🔍 Detecting anomalies...")
        anomalies = self.db_manager.detect_anomalies()

        if anomalies:
            print(f"🚨 Found {len(anomalies)} anomalies:")
            for anomaly in anomalies:
                severity_emoji = "🔴" if anomaly['severity'] == 'high' else "🟡"
                print(f"  {severity_emoji} {anomaly['metric_name']}: "
                      f"current={anomaly['current_value']:.2f}, "
                      f"baseline={anomaly['baseline_value']:.2f}, "
                      f"deviation={anomaly['deviation']:.2f}")
        else:
            print("✅ No anomalies detected")

    def demonstrate_data_export(self):
        """Demonstrate data export capabilities"""
        print("\n💾 Demonstrating data export...")

        # Create exports directory
        Path("demo_exports").mkdir(exist_ok=True)

        start_time = datetime.now() - timedelta(hours=24)

        # Export to CSV
        print("📄 Exporting to CSV...")
        csv_files = [
            ("connection_events", "demo_exports/connection_events_demo.csv"),
            ("device_status", "demo_exports/device_status_demo.csv"),
            ("performance_metrics", "demo_exports/performance_metrics_demo.csv")
        ]

        for table, filename in csv_files:
            self.db_manager.export_to_csv(table, filename, start_time)
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                print(f"  ✅ {filename} ({file_size} bytes)")

        # Export to JSON
        print("📋 Exporting to JSON...")
        json_file = "demo_exports/connection_events_demo.json"
        self.db_manager.export_to_json("connection_events", json_file, start_time)
        if os.path.exists(json_file):
            file_size = os.path.getsize(json_file)
            print(f"  ✅ {json_file} ({file_size} bytes)")

    def demonstrate_report_generation(self):
        """Demonstrate report generation"""
        print("\n📄 Demonstrating report generation...")

        # Create reports directory
        Path("demo_reports").mkdir(exist_ok=True)

        start_time = datetime.now() - timedelta(hours=48)
        end_time = datetime.now()

        # Generate HTML report
        print("🌐 Generating HTML report...")
        try:
            html_report = self.report_generator.generate_html_report(
                start_time, end_time, "demo_reports/esp_demo_report.html"
            )
            if html_report and os.path.exists(html_report):
                file_size = os.path.getsize(html_report)
                print(f"  ✅ HTML report: {html_report} ({file_size} bytes)")
        except Exception as e:
            print(f"  ❌ HTML report failed: {e}")

        # Generate PDF report
        print("📑 Generating PDF report...")
        try:
            pdf_report = self.report_generator.generate_pdf_report(
                start_time, end_time, "demo_reports/esp_demo_report.pdf"
            )
            if pdf_report and os.path.exists(pdf_report):
                file_size = os.path.getsize(pdf_report)
                print(f"  ✅ PDF report: {pdf_report} ({file_size} bytes)")
        except Exception as e:
            print(f"  ❌ PDF report failed: {e}")

        # Generate JSON summary
        print("📊 Generating summary report...")
        try:
            summary = self.report_generator.generate_summary_report(start_time, end_time)
            if summary:
                json_file = "demo_reports/esp_demo_summary.json"
                with open(json_file, 'w') as f:
                    json.dump(summary, f, indent=2, default=str)
                file_size = os.path.getsize(json_file)
                print(f"  ✅ Summary report: {json_file} ({file_size} bytes)")

                # Show some key metrics from summary
                print("  📈 Key metrics from summary:")
                perf = summary.get('performance', {})
                print(f"    Avg connections/hour: {perf.get('avg_connections_per_hour', 0):.1f}")
                print(f"    Avg requests/hour: {perf.get('avg_requests_per_hour', 0):.1f}")
                print(f"    Total data points: {perf.get('total_data_points', 0)}")

                anomalies = summary.get('anomalies', {})
                print(f"    Anomalies detected: {anomalies.get('count', 0)}")
                print(f"    High severity: {anomalies.get('high_severity', 0)}")
        except Exception as e:
            print(f"  ❌ Summary report failed: {e}")

    def demonstrate_data_retention(self):
        """Demonstrate data retention policies"""
        print("\n🧹 Demonstrating data retention...")

        # Show current data counts
        print("📊 Current data counts:")
        tables = ['connection_events', 'device_status', 'performance_metrics']

        initial_counts = {}
        for table in tables:
            cursor = self.db_manager.conn.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            initial_counts[table] = count
            print(f"  {table}: {count} records")

        # Simulate cleanup of old data (only very old data to preserve demo)
        print("\n🗑️  Cleaning up data older than 1 day (for demo purposes)...")
        self.db_manager.cleanup_old_data(retention_days=1)

        # Show counts after cleanup
        print("\n📊 Data counts after cleanup:")
        for table in tables:
            cursor = self.db_manager.conn.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            removed = initial_counts[table] - count
            print(f"  {table}: {count} records (removed {removed})")

    def run_complete_demo(self):
        """Run the complete demonstration"""
        print("🚀 ESP Monitor Database Features Demo")
        print("=" * 50)

        # Initialize database
        if not self.initialize_database():
            return False

        # Check if we already have demo data
        cursor = self.db_manager.conn.execute("SELECT COUNT(*) FROM connection_events")
        existing_events = cursor.fetchone()[0]

        if existing_events < 100:
            print("\n📅 No sufficient demo data found, generating sample data...")
            self.generate_sample_data(days_back=3, events_per_hour=15)
        else:
            print(f"\n📅 Found {existing_events} existing events, using existing data")
            self.demo_data_generated = True

        # Run all demonstrations
        try:
            self.demonstrate_data_retrieval()
            self.demonstrate_statistics()
            self.demonstrate_baselines_and_anomalies()
            self.demonstrate_data_export()
            self.demonstrate_report_generation()
            self.demonstrate_data_retention()

            print("\n" + "=" * 50)
            print("✅ Demo completed successfully!")
            print("\n📁 Generated files:")
            print("  📊 Database: demo_esp_monitoring.db")
            print("  📄 Reports: demo_reports/")
            print("  💾 Exports: demo_exports/")

            print("\n🎯 Next steps:")
            print("  1. Examine the generated HTML report in demo_reports/")
            print("  2. Check the exported CSV files in demo_exports/")
            print("  3. Review the database structure using any SQLite browser")
            print("  4. Run the actual ESP monitor with database features enabled")

            return True

        except Exception as e:
            print(f"\n❌ Demo failed: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            # Clean up
            if self.db_manager:
                self.db_manager.close()

def main():
    """Main function to run the demo"""
    demo = ESPMonitorDemo()

    try:
        success = demo.run_complete_demo()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
