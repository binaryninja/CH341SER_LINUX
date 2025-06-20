#!/usr/bin/env python3
"""
Database Manager for ESP Monitor
================================
Handles data persistence, historical analysis, and reporting for ESP monitoring data.

Features:
- SQLite database with automatic schema management
- Historical data storage and retrieval
- Data export functionality (CSV, JSON, PDF)
- Data retention policies
- Performance baselines and anomaly detection
"""

import sqlite3
import json
import csv
import io
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ConnectionEvent:
    """Data class for connection events"""
    timestamp: datetime
    event_type: str  # 'open', 'closed', 'http_request'
    connection_id: int
    method: Optional[str] = None
    path: Optional[str] = None
    length: Optional[int] = None
    raw_data: Optional[str] = None

@dataclass
class DeviceStatus:
    """Data class for device status snapshots"""
    timestamp: datetime
    status: str
    wifi_connected: bool
    ip_address: Optional[str] = None
    signal_strength: Optional[int] = None
    memory_free: Optional[int] = None
    uptime_seconds: Optional[int] = None
    temperature: Optional[float] = None

@dataclass
class PerformanceMetrics:
    """Data class for performance metrics"""
    timestamp: datetime
    connections_total: int
    requests_total: int
    errors_total: int
    connections_per_hour: float
    requests_per_hour: float
    response_time_avg: Optional[float] = None

class DatabaseManager:
    """Manages SQLite database for ESP monitoring data"""

    def __init__(self, db_path: str = "esp_monitoring.db"):
        self.db_path = db_path
        self.conn = None
        self._init_database()

    def _init_database(self):
        """Initialize database connection and create tables"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Enable dict-like access
            self._create_tables()
            logger.info(f"Database initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    def _create_tables(self):
        """Create database tables if they don't exist"""

        # Connection events table
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS connection_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                event_type TEXT NOT NULL,
                connection_id INTEGER NOT NULL,
                method TEXT,
                path TEXT,
                length INTEGER,
                raw_data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Device status table
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS device_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                status TEXT NOT NULL,
                wifi_connected BOOLEAN NOT NULL,
                ip_address TEXT,
                signal_strength INTEGER,
                memory_free INTEGER,
                uptime_seconds INTEGER,
                temperature REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Performance metrics table
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                connections_total INTEGER NOT NULL,
                requests_total INTEGER NOT NULL,
                errors_total INTEGER NOT NULL,
                connections_per_hour REAL NOT NULL,
                requests_per_hour REAL NOT NULL,
                response_time_avg REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Baselines table for anomaly detection
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS performance_baselines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                baseline_value REAL NOT NULL,
                std_deviation REAL NOT NULL,
                sample_count INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create indexes for better query performance
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_connection_events_timestamp ON connection_events(timestamp)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_device_status_timestamp ON device_status(timestamp)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp ON performance_metrics(timestamp)')

        self.conn.commit()
        logger.info("Database tables created/verified")

    def store_connection_event(self, event: ConnectionEvent):
        """Store a connection event in the database"""
        try:
            self.conn.execute('''
                INSERT INTO connection_events
                (timestamp, event_type, connection_id, method, path, length, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.timestamp,
                event.event_type,
                event.connection_id,
                event.method,
                event.path,
                event.length,
                event.raw_data
            ))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to store connection event: {e}")

    def store_device_status(self, status: DeviceStatus):
        """Store device status snapshot in the database"""
        try:
            self.conn.execute('''
                INSERT INTO device_status
                (timestamp, status, wifi_connected, ip_address, signal_strength,
                 memory_free, uptime_seconds, temperature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                status.timestamp,
                status.status,
                status.wifi_connected,
                status.ip_address,
                status.signal_strength,
                status.memory_free,
                status.uptime_seconds,
                status.temperature
            ))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to store device status: {e}")

    def store_performance_metrics(self, metrics: PerformanceMetrics):
        """Store performance metrics in the database"""
        try:
            self.conn.execute('''
                INSERT INTO performance_metrics
                (timestamp, connections_total, requests_total, errors_total,
                 connections_per_hour, requests_per_hour, response_time_avg)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.timestamp,
                metrics.connections_total,
                metrics.requests_total,
                metrics.errors_total,
                metrics.connections_per_hour,
                metrics.requests_per_hour,
                metrics.response_time_avg
            ))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to store performance metrics: {e}")

    def get_connection_events(self,
                            start_time: Optional[datetime] = None,
                            end_time: Optional[datetime] = None,
                            event_type: Optional[str] = None,
                            limit: int = 1000) -> List[Dict]:
        """Retrieve connection events from database"""
        query = "SELECT * FROM connection_events WHERE 1=1"
        params = []

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        try:
            cursor = self.conn.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to retrieve connection events: {e}")
            return []

    def get_device_status_history(self,
                                start_time: Optional[datetime] = None,
                                end_time: Optional[datetime] = None,
                                limit: int = 1000) -> List[Dict]:
        """Retrieve device status history from database"""
        query = "SELECT * FROM device_status WHERE 1=1"
        params = []

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        try:
            cursor = self.conn.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to retrieve device status history: {e}")
            return []

    def get_performance_metrics_history(self,
                                      start_time: Optional[datetime] = None,
                                      end_time: Optional[datetime] = None,
                                      limit: int = 1000) -> List[Dict]:
        """Retrieve performance metrics history from database"""
        query = "SELECT * FROM performance_metrics WHERE 1=1"
        params = []

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        try:
            cursor = self.conn.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to retrieve performance metrics history: {e}")
            return []

    def get_statistics(self,
                      start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None) -> Dict:
        """Get statistical summary of monitoring data"""
        if not start_time:
            start_time = datetime.now() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.now()

        stats = {
            'period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            },
            'connections': {},
            'requests': {},
            'errors': {},
            'uptime': {}
        }

        try:
            # Connection statistics
            cursor = self.conn.execute('''
                SELECT
                    COUNT(*) as total_events,
                    COUNT(CASE WHEN event_type = 'open' THEN 1 END) as connections_opened,
                    COUNT(CASE WHEN event_type = 'closed' THEN 1 END) as connections_closed,
                    COUNT(CASE WHEN event_type = 'http_request' THEN 1 END) as http_requests
                FROM connection_events
                WHERE timestamp BETWEEN ? AND ?
            ''', (start_time, end_time))

            row = cursor.fetchone()
            if row:
                stats['connections'] = dict(row)

            # Request method breakdown
            cursor = self.conn.execute('''
                SELECT method, COUNT(*) as count
                FROM connection_events
                WHERE event_type = 'http_request' AND timestamp BETWEEN ? AND ?
                GROUP BY method
            ''', (start_time, end_time))

            stats['requests']['by_method'] = {row['method']: row['count'] for row in cursor.fetchall()}

            # Most requested paths
            cursor = self.conn.execute('''
                SELECT path, COUNT(*) as count
                FROM connection_events
                WHERE event_type = 'http_request' AND timestamp BETWEEN ? AND ?
                GROUP BY path
                ORDER BY count DESC
                LIMIT 10
            ''', (start_time, end_time))

            stats['requests']['top_paths'] = [dict(row) for row in cursor.fetchall()]

            # Device status statistics
            cursor = self.conn.execute('''
                SELECT
                    AVG(CASE WHEN wifi_connected THEN 1.0 ELSE 0.0 END) as wifi_uptime_ratio,
                    AVG(signal_strength) as avg_signal_strength,
                    AVG(memory_free) as avg_memory_free,
                    AVG(temperature) as avg_temperature,
                    MAX(uptime_seconds) as max_uptime
                FROM device_status
                WHERE timestamp BETWEEN ? AND ?
            ''', (start_time, end_time))

            row = cursor.fetchone()
            if row:
                stats['device'] = dict(row)

        except Exception as e:
            logger.error(f"Failed to calculate statistics: {e}")

        return stats

    def export_to_csv(self, table_name: str, file_path: str,
                     start_time: Optional[datetime] = None,
                     end_time: Optional[datetime] = None):
        """Export table data to CSV file"""
        query = f"SELECT * FROM {table_name} WHERE 1=1"
        params = []

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp"

        try:
            cursor = self.conn.execute(query, params)
            rows = cursor.fetchall()

            if not rows:
                logger.warning(f"No data found for export from {table_name}")
                return

            with open(file_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                # Write header
                writer.writerow(rows[0].keys())
                # Write data
                for row in rows:
                    writer.writerow(row)

            logger.info(f"Data exported to {file_path}")

        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")

    def export_to_json(self, table_name: str, file_path: str,
                      start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None):
        """Export table data to JSON file"""
        query = f"SELECT * FROM {table_name} WHERE 1=1"
        params = []

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp"

        try:
            cursor = self.conn.execute(query, params)
            rows = cursor.fetchall()

            data = [dict(row) for row in rows]

            with open(file_path, 'w') as jsonfile:
                json.dump(data, jsonfile, indent=2, default=str)

            logger.info(f"Data exported to {file_path}")

        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")

    def cleanup_old_data(self, retention_days: int = 30):
        """Remove old data based on retention policy"""
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        try:
            # Clean up connection events
            cursor = self.conn.execute(
                "DELETE FROM connection_events WHERE timestamp < ?",
                (cutoff_date,)
            )
            events_deleted = cursor.rowcount

            # Clean up device status
            cursor = self.conn.execute(
                "DELETE FROM device_status WHERE timestamp < ?",
                (cutoff_date,)
            )
            status_deleted = cursor.rowcount

            # Clean up performance metrics
            cursor = self.conn.execute(
                "DELETE FROM performance_metrics WHERE timestamp < ?",
                (cutoff_date,)
            )
            metrics_deleted = cursor.rowcount

            self.conn.commit()

            logger.info(f"Cleanup completed: {events_deleted} events, "
                       f"{status_deleted} status records, "
                       f"{metrics_deleted} metrics records deleted")

        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")

    def update_performance_baselines(self):
        """Update performance baselines for anomaly detection"""
        # Calculate baselines from last 7 days of data
        cutoff_date = datetime.now() - timedelta(days=7)

        metrics_to_baseline = [
            'connections_per_hour',
            'requests_per_hour',
            'response_time_avg'
        ]

        try:
            for metric in metrics_to_baseline:
                # Get recent metric values
                cursor = self.conn.execute(f'''
                    SELECT {metric} FROM performance_metrics
                    WHERE timestamp >= ? AND {metric} IS NOT NULL
                ''', (cutoff_date,))

                values = [row[0] for row in cursor.fetchall()]

                if len(values) >= 10:  # Need at least 10 samples
                    baseline_value = statistics.mean(values)
                    std_dev = statistics.stdev(values) if len(values) > 1 else 0

                    # Update or insert baseline
                    self.conn.execute('''
                        INSERT OR REPLACE INTO performance_baselines
                        (metric_name, baseline_value, std_deviation, sample_count, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (metric, baseline_value, std_dev, len(values), datetime.now()))

            self.conn.commit()
            logger.info("Performance baselines updated")

        except Exception as e:
            logger.error(f"Failed to update performance baselines: {e}")

    def detect_anomalies(self, threshold_multiplier: float = 2.0) -> List[Dict]:
        """Detect anomalies based on performance baselines"""
        anomalies = []

        try:
            # Get current baselines
            cursor = self.conn.execute(
                "SELECT metric_name, baseline_value, std_deviation FROM performance_baselines"
            )
            baselines = {row['metric_name']: row for row in cursor.fetchall()}

            # Check recent metrics against baselines
            recent_cutoff = datetime.now() - timedelta(hours=1)
            cursor = self.conn.execute('''
                SELECT * FROM performance_metrics
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            ''', (recent_cutoff,))

            recent_metrics = cursor.fetchall()

            for metric_row in recent_metrics:
                for metric_name, baseline_info in baselines.items():
                    if metric_name in metric_row.keys():
                        current_value = metric_row[metric_name]
                        if current_value is not None:
                            baseline_value = baseline_info['baseline_value']
                            std_dev = baseline_info['std_deviation']

                            # Check if current value is outside acceptable range
                            threshold = std_dev * threshold_multiplier
                            if abs(current_value - baseline_value) > threshold:
                                anomalies.append({
                                    'timestamp': metric_row['timestamp'],
                                    'metric_name': metric_name,
                                    'current_value': current_value,
                                    'baseline_value': baseline_value,
                                    'deviation': abs(current_value - baseline_value),
                                    'threshold': threshold,
                                    'severity': 'high' if abs(current_value - baseline_value) > threshold * 1.5 else 'medium'
                                })

        except Exception as e:
            logger.error(f"Failed to detect anomalies: {e}")

        return anomalies

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
