# ESP Monitor Database and Reporting Features

## Overview

The ESP Monitor has been enhanced with comprehensive database persistence and reporting capabilities. This upgrade transforms the basic monitoring tool into a full-featured analytics platform for ESP device management.

## 🚀 New Features

### 1. **Data Persistence with SQLite**
- Automatic database initialization
- Historical data storage for all monitoring events
- Structured data model with proper indexing
- Thread-safe database operations

### 2. **Performance Analytics**
- Real-time metrics calculation
- Historical trend analysis
- Performance baseline establishment
- Automated anomaly detection

### 3. **Comprehensive Reporting**
- HTML reports with interactive charts
- PDF reports for documentation
- JSON exports for API integration
- CSV exports for spreadsheet analysis

### 4. **Data Management**
- Configurable data retention policies
- Automated cleanup of old data
- Data export in multiple formats
- Database optimization tools

### 5. **Anomaly Detection**
- Statistical baseline calculation
- Automated anomaly identification
- Configurable detection thresholds
- Alert categorization by severity

## 📊 Database Schema

### Connection Events Table
```sql
CREATE TABLE connection_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    event_type TEXT NOT NULL,           -- 'open', 'closed', 'http_request'
    connection_id INTEGER NOT NULL,
    method TEXT,                        -- HTTP method (GET, POST, etc.)
    path TEXT,                          -- Request path
    length INTEGER,                     -- Content length
    raw_data TEXT,                      -- Raw request data
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Device Status Table
```sql
CREATE TABLE device_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    status TEXT NOT NULL,               -- 'connected', 'disconnected'
    wifi_connected BOOLEAN NOT NULL,
    ip_address TEXT,
    signal_strength INTEGER,            -- WiFi signal in dBm
    memory_free INTEGER,                -- Free memory in bytes
    uptime_seconds INTEGER,             -- Device uptime
    temperature REAL,                   -- Device temperature in °C
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Performance Metrics Table
```sql
CREATE TABLE performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    connections_total INTEGER NOT NULL,
    requests_total INTEGER NOT NULL,
    errors_total INTEGER NOT NULL,
    connections_per_hour REAL NOT NULL,
    requests_per_hour REAL NOT NULL,
    response_time_avg REAL,             -- Average response time in ms
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Performance Baselines Table
```sql
CREATE TABLE performance_baselines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT NOT NULL,
    baseline_value REAL NOT NULL,
    std_deviation REAL NOT NULL,
    sample_count INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 🛠️ Installation

### Prerequisites
- Python 3.7 or higher
- pip package manager

### Quick Installation
```bash
# Clone or download the ESP Monitor files
cd CH341SER_LINUX

# Run the installation script
chmod +x install_dependencies.sh
./install_dependencies.sh

# Or install manually
pip install -r requirements.txt
```

### Required Dependencies
```
pyserial>=3.5          # Serial communication
pandas>=1.3.0          # Data analysis
matplotlib>=3.5.0      # Chart generation
seaborn>=0.11.0        # Statistical visualization
jinja2>=3.0.0          # Template engine
```

### Optional Dependencies
```
reportlab>=3.6.0       # Enhanced PDF generation
influxdb-client>=1.24.0  # InfluxDB integration
psycopg2-binary>=2.9.0   # PostgreSQL support
```

## 📋 Usage Examples

### Basic Monitoring with Database
```bash
# Start monitoring with database features enabled (default)
python3 esp_monitor.py

# Start monitoring without database features
python3 esp_monitor.py --no-database
```

### Report Generation
```bash
# Generate HTML report for last 24 hours
python3 esp_monitor.py --generate-report html --report-hours 24

# Generate PDF report for last week
python3 esp_monitor.py --generate-report pdf --report-hours 168

# Generate JSON summary for last 48 hours
python3 esp_monitor.py --generate-report json --report-hours 48
```

### Data Export
```bash
# Export last 24 hours of data to CSV
python3 esp_monitor.py --export-data csv --report-hours 24

# Export last week of data to JSON
python3 esp_monitor.py --export-data json --report-hours 168
```

### Analytics and Maintenance
```bash
# Show comprehensive statistics
python3 esp_monitor.py --statistics --stats-hours 48

# Detect performance anomalies
python3 esp_monitor.py --detect-anomalies

# Update performance baselines
python3 esp_monitor.py --update-baselines

# Clean up data older than 30 days
python3 esp_monitor.py --cleanup-data 30
```

### Web Interface
```bash
# Start web interface with database features
python3 esp_monitor.py --web-interface --web-port 8080
```

## 🔧 Configuration

### Configuration File (esp_config.json)
```json
{
    "device": {
        "port": "/dev/ttyUSB0",
        "baudrate": 115200
    },
    "monitoring": {
        "log_connections": true,
        "log_requests": true,
        "status_update_interval": 60,
        "metrics_update_interval": 300
    },
    "database": {
        "enabled": true,
        "path": "esp_monitoring.db",
        "retention_days": 30
    },
    "reporting": {
        "auto_generate": false,
        "report_interval_hours": 24,
        "output_directory": "reports"
    },
    "webserver": {
        "port": 8080,
        "enable_cors": false
    },
    "anomaly_detection": {
        "enabled": true,
        "threshold_multiplier": 2.0,
        "baseline_update_interval": 24
    }
}
```

### Environment Variables
```bash
# Override database path
export ESP_DB_PATH="/path/to/custom/database.db"

# Set log level
export ESP_LOG_LEVEL="DEBUG"

# Disable GUI backend for headless systems
export MPLBACKEND="Agg"
```

## 📊 Report Types

### HTML Reports
- **Interactive charts** with zoom and pan capabilities
- **Real-time metrics** with auto-refresh
- **Responsive design** for mobile and desktop
- **Anomaly highlighting** with color-coded alerts
- **Export options** built into the interface

**Features:**
- Connection and request trends over time
- Device health metrics (WiFi, signal strength, temperature)
- Most requested paths and HTTP methods
- Error rate analysis
- Performance anomaly detection

### PDF Reports
- **Professional layout** suitable for documentation
- **High-quality charts** with proper scaling
- **Summary statistics** prominently displayed
- **Multi-page layout** with logical sections
- **Print-ready format** with proper margins

**Sections:**
1. Executive Summary
2. Performance Trends
3. Device Health Analysis
4. Anomaly Detection Results
5. Detailed Statistics

### JSON Reports
- **Machine-readable format** for API integration
- **Structured data** with consistent schema
- **Complete metrics** including raw data
- **Timestamp precision** with ISO format
- **Easy parsing** for automated systems

## 🔍 Analytics Features

### Performance Baselines
The system automatically calculates performance baselines using statistical methods:

- **Rolling averages** over configurable time windows
- **Standard deviation** calculations for variability
- **Minimum sample sizes** to ensure statistical significance
- **Automatic updates** based on recent data patterns

### Anomaly Detection
Sophisticated anomaly detection using statistical analysis:

- **Z-score based detection** with configurable thresholds
- **Multiple metrics** simultaneously monitored
- **Severity classification** (low, medium, high)
- **Timestamp correlation** for event analysis
- **False positive reduction** through baseline stability

### Trend Analysis
Historical trend analysis capabilities:

- **Time series visualization** with multiple time scales
- **Correlation analysis** between different metrics
- **Seasonal pattern detection** for predictable variations
- **Growth rate calculations** for capacity planning

## 🎯 Use Cases

### Development and Testing
- **Monitor ESP device behavior** during development cycles
- **Track performance regressions** across firmware versions
- **Analyze request patterns** for optimization opportunities
- **Debug connectivity issues** with detailed logs

### Production Monitoring
- **Continuous health monitoring** of deployed devices
- **Performance trend analysis** for capacity planning
- **Automated anomaly detection** for proactive maintenance
- **Historical reporting** for compliance and auditing

### Research and Analysis
- **Long-term data collection** for research projects
- **Statistical analysis** of device behavior patterns
- **Data export** for external analysis tools
- **Custom reporting** for specific research needs

## 🔧 Advanced Features

### Custom Data Retention
```python
# Set custom retention policy
monitor.cleanup_old_data(retention_days=90)

# Selective cleanup by data type
db.conn.execute("DELETE FROM connection_events WHERE timestamp < ?", 
                (cutoff_date,))
```

### Custom Baselines
```python
# Manual baseline update
monitor.update_baselines()

# Custom threshold for anomaly detection
anomalies = db.detect_anomalies(threshold_multiplier=3.0)
```

### Batch Data Operations
```python
# Export multiple tables
tables = ['connection_events', 'device_status', 'performance_metrics']
for table in tables:
    db.export_to_csv(table, f"{table}_export.csv")
```

## 🚨 Troubleshooting

### Common Issues

#### Database Initialization Fails
```bash
# Check file permissions
ls -la esp_monitoring.db

# Verify SQLite installation
python3 -c "import sqlite3; print('SQLite OK')"
```

#### Matplotlib/Seaborn Issues
```bash
# For headless systems
export MPLBACKEND="Agg"

# Install system dependencies (Ubuntu/Debian)
sudo apt-get install python3-tk libfreetype6-dev
```

#### Memory Issues with Large Datasets
```bash
# Reduce data retention period
python3 esp_monitor.py --cleanup-data 7

# Limit report time range
python3 esp_monitor.py --generate-report html --report-hours 12
```

#### Serial Port Permission Issues
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER

# Log out and log back in, then verify
groups | grep dialout
```

### Performance Optimization

#### Database Performance
- Regular VACUUM operations for SQLite optimization
- Proper indexing on timestamp columns
- Batch inserts for better performance
- Connection pooling for high-frequency operations

#### Memory Management
- Configurable deque sizes for in-memory logs
- Periodic garbage collection for long-running processes
- Streaming data processing for large exports
- Lazy loading for report generation

## 🧪 Testing and Validation

### Demo Mode
```bash
# Run comprehensive demo
python3 demo_database_features.py

# This will:
# - Create sample database with realistic data
# - Generate sample reports
# - Demonstrate all features
# - Export data in various formats
```

### Unit Testing
```bash
# Run database tests
python3 -m pytest test_database_manager.py

# Run report generation tests
python3 -m pytest test_report_generator.py
```

### Data Validation
```bash
# Verify database integrity
python3 -c "
from database_manager import DatabaseManager
db = DatabaseManager()
print('Database health check passed')
"
```

## 📚 API Reference

### DatabaseManager Class
```python
from database_manager import DatabaseManager, ConnectionEvent

# Initialize database
db = DatabaseManager("monitoring.db")

# Store events
event = ConnectionEvent(
    timestamp=datetime.now(),
    event_type="http_request",
    connection_id=1,
    method="GET",
    path="/api/status"
)
db.store_connection_event(event)

# Retrieve data
events = db.get_connection_events(limit=100)
stats = db.get_statistics()
anomalies = db.detect_anomalies()
```

### ReportGenerator Class
```python
from report_generator import ReportGenerator

# Initialize report generator
reporter = ReportGenerator(database_manager)

# Generate reports
html_file = reporter.generate_html_report()
pdf_file = reporter.generate_pdf_report()
summary = reporter.generate_summary_report()
```

## 🔮 Future Enhancements

### Planned Features
- **InfluxDB integration** for time-series database support
- **PostgreSQL support** for enterprise deployments
- **Real-time dashboards** with WebSocket connections
- **Machine learning** for advanced anomaly detection
- **Multi-device monitoring** with centralized management
- **Alert integrations** (email, Slack, webhooks)

### Contributing
Contributions are welcome! Areas of interest:
- Additional database backends
- Enhanced visualization options
- Machine learning integration
- Performance optimizations
- Additional export formats

## 📄 License

This enhanced version maintains the same license as the original ESP Monitor project.

## 📞 Support

For issues related to database features:
1. Check the troubleshooting section above
2. Run the demo script to verify installation
3. Review log files for detailed error messages
4. Check system requirements and dependencies

---

*ESP Monitor Database Features v1.0 - Transforming ESP monitoring into comprehensive analytics*