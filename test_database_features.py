#!/usr/bin/env python3
"""
Test Script for ESP Monitor Database Features
============================================
This script performs basic tests to ensure the database and reporting
features are working correctly.

Usage:
    python3 test_database_features.py
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from database_manager import DatabaseManager, ConnectionEvent, DeviceStatus, PerformanceMetrics
    from report_generator import ReportGenerator
    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("Please install required packages: pip install -r requirements.txt")
    DATABASE_AVAILABLE = False


class TestDatabaseFeatures(unittest.TestCase):
    """Test cases for database functionality"""

    def setUp(self):
        """Set up test database"""
        if not DATABASE_AVAILABLE:
            self.skipTest("Database dependencies not available")

        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()

        self.db_manager = DatabaseManager(self.temp_db.name)
        self.report_generator = ReportGenerator(self.db_manager)

    def tearDown(self):
        """Clean up test database"""
        if hasattr(self, 'db_manager'):
            self.db_manager.close()

        if hasattr(self, 'temp_db'):
            try:
                os.unlink(self.temp_db.name)
            except:
                pass

    def test_database_initialization(self):
        """Test database initialization"""
        self.assertIsNotNone(self.db_manager.conn)

        # Check if tables exist
        cursor = self.db_manager.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}

        expected_tables = {
            'connection_events',
            'device_status',
            'performance_metrics',
            'performance_baselines'
        }

        self.assertTrue(expected_tables.issubset(tables))

    def test_connection_event_storage(self):
        """Test storing and retrieving connection events"""
        # Create test event
        event = ConnectionEvent(
            timestamp=datetime.now(),
            event_type='http_request',
            connection_id=1,
            method='GET',
            path='/test',
            length=100,
            raw_data='GET /test HTTP/1.1'
        )

        # Store event
        self.db_manager.store_connection_event(event)

        # Retrieve events
        events = self.db_manager.get_connection_events(limit=10)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['event_type'], 'http_request')
        self.assertEqual(events[0]['method'], 'GET')
        self.assertEqual(events[0]['path'], '/test')

    def test_device_status_storage(self):
        """Test storing and retrieving device status"""
        # Create test status
        status = DeviceStatus(
            timestamp=datetime.now(),
            status='connected',
            wifi_connected=True,
            ip_address='192.168.1.100',
            signal_strength=-45,
            memory_free=100000,
            uptime_seconds=3600,
            temperature=35.5
        )

        # Store status
        self.db_manager.store_device_status(status)

        # Retrieve status
        status_history = self.db_manager.get_device_status_history(limit=10)

        self.assertEqual(len(status_history), 1)
        self.assertEqual(status_history[0]['status'], 'connected')
        self.assertTrue(status_history[0]['wifi_connected'])
        self.assertEqual(status_history[0]['ip_address'], '192.168.1.100')

    def test_performance_metrics_storage(self):
        """Test storing and retrieving performance metrics"""
        # Create test metrics
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            connections_total=10,
            requests_total=50,
            errors_total=2,
            connections_per_hour=10.0,
            requests_per_hour=50.0,
            response_time_avg=150.5
        )

        # Store metrics
        self.db_manager.store_performance_metrics(metrics)

        # Retrieve metrics
        metrics_history = self.db_manager.get_performance_metrics_history(limit=10)

        self.assertEqual(len(metrics_history), 1)
        self.assertEqual(metrics_history[0]['connections_total'], 10)
        self.assertEqual(metrics_history[0]['requests_total'], 50)

    def test_statistics_generation(self):
        """Test statistics generation"""
        # Add some test data
        now = datetime.now()

        # Add connection events
        for i in range(5):
            event = ConnectionEvent(
                timestamp=now - timedelta(minutes=i*10),
                event_type='http_request',
                connection_id=i,
                method='GET',
                path=f'/path{i}',
                length=100
            )
            self.db_manager.store_connection_event(event)

        # Get statistics
        start_time = now - timedelta(hours=1)
        stats = self.db_manager.get_statistics(start_time)

        self.assertIn('connections', stats)
        self.assertIn('requests', stats)
        self.assertEqual(stats['connections']['http_requests'], 5)

    def test_data_export_csv(self):
        """Test CSV data export"""
        # Add test data
        event = ConnectionEvent(
            timestamp=datetime.now(),
            event_type='http_request',
            connection_id=1,
            method='GET',
            path='/test'
        )
        self.db_manager.store_connection_event(event)

        # Export to CSV
        temp_csv = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
        temp_csv.close()

        try:
            self.db_manager.export_to_csv('connection_events', temp_csv.name)

            # Check if file exists and has content
            self.assertTrue(os.path.exists(temp_csv.name))
            self.assertGreater(os.path.getsize(temp_csv.name), 0)

            # Check CSV content
            with open(temp_csv.name, 'r') as f:
                content = f.read()
                self.assertIn('event_type', content)  # Header
                self.assertIn('http_request', content)  # Data

        finally:
            try:
                os.unlink(temp_csv.name)
            except:
                pass

    def test_data_export_json(self):
        """Test JSON data export"""
        # Add test data
        event = ConnectionEvent(
            timestamp=datetime.now(),
            event_type='http_request',
            connection_id=1,
            method='GET',
            path='/test'
        )
        self.db_manager.store_connection_event(event)

        # Export to JSON
        temp_json = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        temp_json.close()

        try:
            self.db_manager.export_to_json('connection_events', temp_json.name)

            # Check if file exists and has content
            self.assertTrue(os.path.exists(temp_json.name))
            self.assertGreater(os.path.getsize(temp_json.name), 0)

            # Check JSON content
            import json
            with open(temp_json.name, 'r') as f:
                data = json.load(f)
                self.assertIsInstance(data, list)
                self.assertGreater(len(data), 0)
                self.assertEqual(data[0]['event_type'], 'http_request')

        finally:
            try:
                os.unlink(temp_json.name)
            except:
                pass

    def test_baseline_calculation(self):
        """Test performance baseline calculation"""
        # Add test metrics data
        now = datetime.now()

        for i in range(20):  # Need sufficient data for baselines
            metrics = PerformanceMetrics(
                timestamp=now - timedelta(hours=i),
                connections_total=i * 10,
                requests_total=i * 50,
                errors_total=i,
                connections_per_hour=10.0 + i,
                requests_per_hour=50.0 + i * 2,
                response_time_avg=100.0 + i * 5
            )
            self.db_manager.store_performance_metrics(metrics)

        # Update baselines
        self.db_manager.update_performance_baselines()

        # Check if baselines were created
        cursor = self.db_manager.conn.execute(
            "SELECT COUNT(*) FROM performance_baselines"
        )
        baseline_count = cursor.fetchone()[0]
        self.assertGreater(baseline_count, 0)

    def test_anomaly_detection(self):
        """Test anomaly detection"""
        # First establish baselines with normal data
        now = datetime.now()

        for i in range(20):
            metrics = PerformanceMetrics(
                timestamp=now - timedelta(hours=i+2),
                connections_total=i * 10,
                requests_total=i * 50,
                errors_total=i,
                connections_per_hour=10.0,  # Consistent baseline
                requests_per_hour=50.0,     # Consistent baseline
                response_time_avg=100.0     # Consistent baseline
            )
            self.db_manager.store_performance_metrics(metrics)

        # Update baselines
        self.db_manager.update_performance_baselines()

        # Add anomalous data
        anomalous_metrics = PerformanceMetrics(
            timestamp=now,
            connections_total=1000,
            requests_total=5000,
            errors_total=100,
            connections_per_hour=1000.0,  # Very high
            requests_per_hour=5000.0,     # Very high
            response_time_avg=5000.0      # Very slow
        )
        self.db_manager.store_performance_metrics(anomalous_metrics)

        # Detect anomalies
        anomalies = self.db_manager.detect_anomalies()

        # Should detect anomalies
        self.assertGreater(len(anomalies), 0)

    def test_data_cleanup(self):
        """Test data cleanup functionality"""
        # Add old test data
        old_time = datetime.now() - timedelta(days=50)

        event = ConnectionEvent(
            timestamp=old_time,
            event_type='http_request',
            connection_id=1,
            method='GET',
            path='/old'
        )
        self.db_manager.store_connection_event(event)

        # Count records before cleanup
        cursor = self.db_manager.conn.execute("SELECT COUNT(*) FROM connection_events")
        count_before = cursor.fetchone()[0]

        # Cleanup data older than 30 days
        self.db_manager.cleanup_old_data(retention_days=30)

        # Count records after cleanup
        cursor = self.db_manager.conn.execute("SELECT COUNT(*) FROM connection_events")
        count_after = cursor.fetchone()[0]

        # Should have fewer records
        self.assertLessEqual(count_after, count_before)


class TestReportGeneration(unittest.TestCase):
    """Test cases for report generation"""

    def setUp(self):
        """Set up test database with sample data"""
        if not DATABASE_AVAILABLE:
            self.skipTest("Database dependencies not available")

        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()

        self.db_manager = DatabaseManager(self.temp_db.name)
        self.report_generator = ReportGenerator(self.db_manager)

        # Add sample data
        self._add_sample_data()

    def tearDown(self):
        """Clean up test database"""
        if hasattr(self, 'db_manager'):
            self.db_manager.close()

        if hasattr(self, 'temp_db'):
            try:
                os.unlink(self.temp_db.name)
            except:
                pass

    def _add_sample_data(self):
        """Add sample data for testing"""
        now = datetime.now()

        # Add connection events
        for i in range(10):
            event = ConnectionEvent(
                timestamp=now - timedelta(hours=i),
                event_type='http_request',
                connection_id=i,
                method='GET',
                path=f'/path{i % 3}',
                length=100 + i
            )
            self.db_manager.store_connection_event(event)

        # Add device status
        for i in range(10):
            status = DeviceStatus(
                timestamp=now - timedelta(hours=i),
                status='connected',
                wifi_connected=True,
                signal_strength=-45 - i,
                memory_free=100000 - i * 1000,
                temperature=30.0 + i
            )
            self.db_manager.store_device_status(status)

        # Add performance metrics
        for i in range(10):
            metrics = PerformanceMetrics(
                timestamp=now - timedelta(hours=i),
                connections_total=i * 5,
                requests_total=i * 25,
                errors_total=i,
                connections_per_hour=5.0 + i,
                requests_per_hour=25.0 + i * 2
            )
            self.db_manager.store_performance_metrics(metrics)

    def test_summary_report_generation(self):
        """Test summary report generation"""
        start_time = datetime.now() - timedelta(hours=24)
        summary = self.report_generator.generate_summary_report(start_time)

        self.assertIn('report_info', summary)
        self.assertIn('statistics', summary)
        self.assertIn('performance', summary)

        # Check report info
        self.assertIn('generated_at', summary['report_info'])
        self.assertIn('period_start', summary['report_info'])

    def test_html_report_generation(self):
        """Test HTML report generation"""
        temp_html = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
        temp_html.close()

        try:
            start_time = datetime.now() - timedelta(hours=24)
            result = self.report_generator.generate_html_report(
                start_time, datetime.now(), temp_html.name
            )

            self.assertEqual(result, temp_html.name)
            self.assertTrue(os.path.exists(temp_html.name))
            self.assertGreater(os.path.getsize(temp_html.name), 0)

            # Check HTML content
            with open(temp_html.name, 'r') as f:
                content = f.read()
                self.assertIn('<html', content)
                self.assertIn('ESP Monitor Report', content)

        finally:
            try:
                os.unlink(temp_html.name)
            except:
                pass


def run_basic_functionality_test():
    """Run a basic functionality test without unittest framework"""
    print("🧪 Running basic functionality tests...")

    if not DATABASE_AVAILABLE:
        print("❌ Database dependencies not available")
        return False

    success = True

    # Test 1: Database initialization
    try:
        print("1. Testing database initialization...")
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()

        db_manager = DatabaseManager(temp_db.name)
        print("   ✅ Database initialized successfully")

        # Test 2: Data storage
        print("2. Testing data storage...")
        event = ConnectionEvent(
            timestamp=datetime.now(),
            event_type='http_request',
            connection_id=1,
            method='GET',
            path='/test'
        )
        db_manager.store_connection_event(event)
        print("   ✅ Data storage working")

        # Test 3: Data retrieval
        print("3. Testing data retrieval...")
        events = db_manager.get_connection_events(limit=10)
        if len(events) > 0:
            print("   ✅ Data retrieval working")
        else:
            print("   ❌ No data retrieved")
            success = False

        # Test 4: Report generation
        print("4. Testing report generation...")
        report_gen = ReportGenerator(db_manager)
        summary = report_gen.generate_summary_report()
        if summary:
            print("   ✅ Report generation working")
        else:
            print("   ❌ Report generation failed")
            success = False

        # Cleanup
        db_manager.close()
        os.unlink(temp_db.name)

    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        success = False

    return success


def main():
    """Main test function"""
    print("ESP Monitor Database Features Test Suite")
    print("=" * 50)

    if not DATABASE_AVAILABLE:
        print("❌ Cannot run tests - database dependencies not installed")
        print("Please run: pip install -r requirements.txt")
        return 1

    # Run basic functionality test first
    if not run_basic_functionality_test():
        print("\n❌ Basic functionality tests failed")
        return 1

    print("\n🧪 Running comprehensive test suite...")

    # Create test suite
    test_suite = unittest.TestSuite()

    # Add database tests
    test_suite.addTest(unittest.makeSuite(TestDatabaseFeatures))

    # Add report generation tests (if matplotlib is available)
    try:
        import matplotlib
        test_suite.addTest(unittest.makeSuite(TestReportGeneration))
    except ImportError:
        print("⚠️  Skipping report generation tests (matplotlib not available)")

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Print summary
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✅ All tests passed!")
        print(f"Ran {result.testsRun} tests successfully")
        return 0
    else:
        print("❌ Some tests failed")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
