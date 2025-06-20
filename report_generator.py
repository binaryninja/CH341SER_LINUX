#!/usr/bin/env python3
"""
Report Generator for ESP Monitor
===============================
Generates comprehensive reports and analytics for ESP monitoring data.

Features:
- PDF report generation with charts and graphs
- HTML reports with interactive elements
- Performance analysis and trend detection
- Automated report scheduling
- Custom report templates
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
import seaborn as sns
import pandas as pd
from jinja2 import Template
import base64
from io import BytesIO

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set matplotlib style
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class ReportGenerator:
    """Generates various types of reports for ESP monitoring data"""

    def __init__(self, database_manager):
        self.db = database_manager
        self.report_templates = self._load_templates()

    def _load_templates(self) -> Dict[str, str]:
        """Load report templates"""
        templates = {}

        # HTML Dashboard template
        templates['html_dashboard'] = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESP Monitor Report - {{ report_date }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                 color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                     gap: 20px; margin-bottom: 30px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-value { font-size: 2em; font-weight: bold; color: #667eea; }
        .stat-label { color: #666; margin-top: 5px; }
        .chart-container { background: white; padding: 20px; border-radius: 8px;
                          box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .alert { padding: 15px; margin: 10px 0; border-radius: 4px; }
        .alert-danger { background-color: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        .alert-warning { background-color: #fff3cd; border: 1px solid #ffeaa7; color: #856404; }
        .alert-info { background-color: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; font-weight: bold; }
        .footer { text-align: center; margin-top: 40px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ESP Device Monitoring Report</h1>
            <p>Generated on: {{ report_date }}</p>
            <p>Period: {{ period_start }} to {{ period_end }}</p>
        </div>

        <!-- Key Statistics -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{{ stats.connections.total_events | default(0) }}</div>
                <div class="stat-label">Total Events</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.connections.http_requests | default(0) }}</div>
                <div class="stat-label">HTTP Requests</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ "%.1f"|format(stats.device.wifi_uptime_ratio * 100) if stats.device.wifi_uptime_ratio else "N/A" }}%</div>
                <div class="stat-label">WiFi Uptime</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.device.avg_signal_strength | round | default("N/A") }}</div>
                <div class="stat-label">Avg Signal Strength</div>
            </div>
        </div>

        <!-- Anomalies Section -->
        {% if anomalies %}
        <div class="alert alert-warning">
            <h3>⚠️ Anomalies Detected</h3>
            <p>{{ anomalies|length }} anomalies detected in the reporting period:</p>
            <ul>
            {% for anomaly in anomalies %}
                <li><strong>{{ anomaly.metric_name }}</strong>: {{ anomaly.current_value }}
                    (baseline: {{ anomaly.baseline_value }}, deviation: {{ "%.2f"|format(anomaly.deviation) }})</li>
            {% endfor %}
            </ul>
        </div>
        {% endif %}

        <!-- Charts Section -->
        {% for chart in charts %}
        <div class="chart-container">
            <h3>{{ chart.title }}</h3>
            <img src="data:image/png;base64,{{ chart.data }}" style="max-width: 100%; height: auto;">
        </div>
        {% endfor %}

        <!-- Top Requested Paths -->
        {% if stats.requests.top_paths %}
        <div class="chart-container">
            <h3>Most Requested Paths</h3>
            <table>
                <thead>
                    <tr><th>Path</th><th>Requests</th></tr>
                </thead>
                <tbody>
                {% for path_stat in stats.requests.top_paths %}
                    <tr><td>{{ path_stat.path }}</td><td>{{ path_stat.count }}</td></tr>
                {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}

        <!-- Request Methods -->
        {% if stats.requests.by_method %}
        <div class="chart-container">
            <h3>Requests by Method</h3>
            <table>
                <thead>
                    <tr><th>Method</th><th>Count</th></tr>
                </thead>
                <tbody>
                {% for method, count in stats.requests.by_method.items() %}
                    <tr><td>{{ method }}</td><td>{{ count }}</td></tr>
                {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}

        <div class="footer">
            <p>Report generated by ESP Monitor v1.0</p>
        </div>
    </div>
</body>
</html>
        '''

        return templates

    def generate_performance_charts(self, start_time: datetime, end_time: datetime) -> List[Dict[str, str]]:
        """Generate performance charts as base64 encoded images"""
        charts = []

        try:
            # Get performance metrics data
            metrics_data = self.db.get_performance_metrics_history(start_time, end_time)

            if not metrics_data:
                logger.warning("No metrics data found for chart generation")
                return charts

            # Convert to DataFrame for easier plotting
            df = pd.DataFrame(metrics_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)

            # Chart 1: Connections and Requests over time
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

            # Connections chart
            ax1.plot(df.index, df['connections_per_hour'], label='Connections/Hour', color='blue', linewidth=2)
            ax1.set_title('Connections per Hour Over Time')
            ax1.set_ylabel('Connections/Hour')
            ax1.grid(True, alpha=0.3)
            ax1.legend()

            # Requests chart
            ax2.plot(df.index, df['requests_per_hour'], label='Requests/Hour', color='green', linewidth=2)
            ax2.set_title('Requests per Hour Over Time')
            ax2.set_ylabel('Requests/Hour')
            ax2.set_xlabel('Time')
            ax2.grid(True, alpha=0.3)
            ax2.legend()

            # Format x-axis
            for ax in [ax1, ax2]:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=4))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

            plt.tight_layout()

            # Convert to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            chart_data = base64.b64encode(buffer.getvalue()).decode()
            plt.close()

            charts.append({
                'title': 'Connection and Request Trends',
                'data': chart_data
            })

            # Chart 2: Error Rate
            if 'errors_total' in df.columns:
                fig, ax = plt.subplots(figsize=(12, 6))

                # Calculate error rate
                df['error_rate'] = df['errors_total'].diff().fillna(0)
                ax.bar(df.index, df['error_rate'], alpha=0.7, color='red', label='Errors')
                ax.set_title('Error Rate Over Time')
                ax.set_ylabel('Errors')
                ax.set_xlabel('Time')
                ax.grid(True, alpha=0.3)
                ax.legend()

                # Format x-axis
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=4))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

                plt.tight_layout()

                # Convert to base64
                buffer = BytesIO()
                plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
                buffer.seek(0)
                chart_data = base64.b64encode(buffer.getvalue()).decode()
                plt.close()

                charts.append({
                    'title': 'Error Rate Analysis',
                    'data': chart_data
                })

            # Chart 3: Device Status Over Time
            status_data = self.db.get_device_status_history(start_time, end_time)
            if status_data:
                status_df = pd.DataFrame(status_data)
                status_df['timestamp'] = pd.to_datetime(status_df['timestamp'])
                status_df.set_index('timestamp', inplace=True)

                fig, axes = plt.subplots(2, 2, figsize=(15, 10))

                # WiFi status
                if 'wifi_connected' in status_df.columns:
                    wifi_status = status_df['wifi_connected'].astype(int)
                    axes[0, 0].fill_between(wifi_status.index, wifi_status, alpha=0.7, color='green')
                    axes[0, 0].set_title('WiFi Connection Status')
                    axes[0, 0].set_ylabel('Connected (1=Yes, 0=No)')
                    axes[0, 0].grid(True, alpha=0.3)

                # Signal strength
                if 'signal_strength' in status_df.columns and status_df['signal_strength'].notna().any():
                    axes[0, 1].plot(status_df.index, status_df['signal_strength'],
                                   color='orange', linewidth=2)
                    axes[0, 1].set_title('Signal Strength')
                    axes[0, 1].set_ylabel('Signal Strength (dBm)')
                    axes[0, 1].grid(True, alpha=0.3)

                # Memory usage
                if 'memory_free' in status_df.columns and status_df['memory_free'].notna().any():
                    axes[1, 0].plot(status_df.index, status_df['memory_free'],
                                   color='purple', linewidth=2)
                    axes[1, 0].set_title('Free Memory')
                    axes[1, 0].set_ylabel('Free Memory (bytes)')
                    axes[1, 0].grid(True, alpha=0.3)

                # Temperature
                if 'temperature' in status_df.columns and status_df['temperature'].notna().any():
                    axes[1, 1].plot(status_df.index, status_df['temperature'],
                                   color='red', linewidth=2)
                    axes[1, 1].set_title('Temperature')
                    axes[1, 1].set_ylabel('Temperature (°C)')
                    axes[1, 1].grid(True, alpha=0.3)

                # Format all x-axes
                for ax in axes.flat:
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
                    ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
                    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

                plt.tight_layout()

                # Convert to base64
                buffer = BytesIO()
                plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
                buffer.seek(0)
                chart_data = base64.b64encode(buffer.getvalue()).decode()
                plt.close()

                charts.append({
                    'title': 'Device Health Metrics',
                    'data': chart_data
                })

        except Exception as e:
            logger.error(f"Failed to generate performance charts: {e}")

        return charts

    def generate_html_report(self,
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           output_file: str = "esp_report.html") -> str:
        """Generate comprehensive HTML report"""

        if not start_time:
            start_time = datetime.now() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.now()

        try:
            # Get statistics
            stats = self.db.get_statistics(start_time, end_time)

            # Get anomalies
            anomalies = self.db.detect_anomalies()

            # Generate charts
            charts = self.generate_performance_charts(start_time, end_time)

            # Prepare template data
            template_data = {
                'report_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'period_start': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'period_end': end_time.strftime('%Y-%m-%d %H:%M:%S'),
                'stats': stats,
                'anomalies': anomalies,
                'charts': charts
            }

            # Render template
            template = Template(self.report_templates['html_dashboard'])
            html_content = template.render(**template_data)

            # Write to file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.info(f"HTML report generated: {output_file}")
            return output_file

        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}")
            return ""

    def generate_pdf_report(self,
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None,
                          output_file: str = "esp_report.pdf") -> str:
        """Generate comprehensive PDF report"""

        if not start_time:
            start_time = datetime.now() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.now()

        try:
            with PdfPages(output_file) as pdf:
                # Title page
                fig = plt.figure(figsize=(8.5, 11))
                fig.suptitle('ESP Device Monitoring Report', fontsize=24, fontweight='bold')

                # Add report info
                plt.text(0.5, 0.7, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                        ha='center', fontsize=14, transform=fig.transFigure)
                plt.text(0.5, 0.65, f'Period: {start_time.strftime("%Y-%m-%d %H:%M")} to {end_time.strftime("%Y-%m-%d %H:%M")}',
                        ha='center', fontsize=12, transform=fig.transFigure)

                # Get statistics for title page
                stats = self.db.get_statistics(start_time, end_time)

                # Add key statistics
                y_pos = 0.5
                stats_text = [
                    f"Total Events: {stats.get('connections', {}).get('total_events', 0)}",
                    f"HTTP Requests: {stats.get('connections', {}).get('http_requests', 0)}",
                    f"Connections Opened: {stats.get('connections', {}).get('connections_opened', 0)}",
                    f"WiFi Uptime: {stats.get('device', {}).get('wifi_uptime_ratio', 0) * 100:.1f}%" if stats.get('device', {}).get('wifi_uptime_ratio') else "WiFi Uptime: N/A"
                ]

                for stat in stats_text:
                    plt.text(0.5, y_pos, stat, ha='center', fontsize=12,
                            transform=fig.transFigure)
                    y_pos -= 0.05

                plt.axis('off')
                pdf.savefig(fig, bbox_inches='tight')
                plt.close()

                # Performance metrics charts
                metrics_data = self.db.get_performance_metrics_history(start_time, end_time)

                if metrics_data:
                    df = pd.DataFrame(metrics_data)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df.set_index('timestamp', inplace=True)

                    # Connections and Requests page
                    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.5, 11))

                    ax1.plot(df.index, df['connections_per_hour'], linewidth=2, color='blue')
                    ax1.set_title('Connections per Hour Over Time', fontsize=14, fontweight='bold')
                    ax1.set_ylabel('Connections/Hour')
                    ax1.grid(True, alpha=0.3)

                    ax2.plot(df.index, df['requests_per_hour'], linewidth=2, color='green')
                    ax2.set_title('Requests per Hour Over Time', fontsize=14, fontweight='bold')
                    ax2.set_ylabel('Requests/Hour')
                    ax2.set_xlabel('Time')
                    ax2.grid(True, alpha=0.3)

                    # Format x-axis
                    for ax in [ax1, ax2]:
                        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
                        ax.xaxis.set_major_locator(mdates.HourLocator(interval=4))
                        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

                    plt.tight_layout()
                    pdf.savefig(fig, bbox_inches='tight')
                    plt.close()

                # Device status page
                status_data = self.db.get_device_status_history(start_time, end_time)
                if status_data:
                    status_df = pd.DataFrame(status_data)
                    status_df['timestamp'] = pd.to_datetime(status_df['timestamp'])
                    status_df.set_index('timestamp', inplace=True)

                    fig, axes = plt.subplots(2, 2, figsize=(8.5, 11))

                    # WiFi status
                    if 'wifi_connected' in status_df.columns:
                        wifi_status = status_df['wifi_connected'].astype(int)
                        axes[0, 0].fill_between(wifi_status.index, wifi_status, alpha=0.7, color='green')
                        axes[0, 0].set_title('WiFi Connection Status')
                        axes[0, 0].set_ylabel('Connected')
                        axes[0, 0].grid(True, alpha=0.3)

                    # Signal strength
                    if 'signal_strength' in status_df.columns and status_df['signal_strength'].notna().any():
                        axes[0, 1].plot(status_df.index, status_df['signal_strength'],
                                       color='orange', linewidth=2)
                        axes[0, 1].set_title('Signal Strength')
                        axes[0, 1].set_ylabel('dBm')
                        axes[0, 1].grid(True, alpha=0.3)

                    # Memory usage
                    if 'memory_free' in status_df.columns and status_df['memory_free'].notna().any():
                        axes[1, 0].plot(status_df.index, status_df['memory_free'],
                                       color='purple', linewidth=2)
                        axes[1, 0].set_title('Free Memory')
                        axes[1, 0].set_ylabel('Bytes')
                        axes[1, 0].grid(True, alpha=0.3)

                    # Temperature
                    if 'temperature' in status_df.columns and status_df['temperature'].notna().any():
                        axes[1, 1].plot(status_df.index, status_df['temperature'],
                                       color='red', linewidth=2)
                        axes[1, 1].set_title('Temperature')
                        axes[1, 1].set_ylabel('°C')
                        axes[1, 1].grid(True, alpha=0.3)

                    # Format all x-axes
                    for ax in axes.flat:
                        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

                    plt.tight_layout()
                    pdf.savefig(fig, bbox_inches='tight')
                    plt.close()

                # Anomalies page
                anomalies = self.db.detect_anomalies()
                if anomalies:
                    fig = plt.figure(figsize=(8.5, 11))
                    fig.suptitle('Detected Anomalies', fontsize=16, fontweight='bold')

                    y_pos = 0.9
                    for i, anomaly in enumerate(anomalies[:10]):  # Show top 10 anomalies
                        anomaly_text = (f"{anomaly['metric_name']}: {anomaly['current_value']:.2f} "
                                      f"(baseline: {anomaly['baseline_value']:.2f}, "
                                      f"severity: {anomaly['severity']})")
                        plt.text(0.1, y_pos, f"{i+1}. {anomaly_text}", fontsize=10,
                                transform=fig.transFigure)
                        y_pos -= 0.05

                    plt.axis('off')
                    pdf.savefig(fig, bbox_inches='tight')
                    plt.close()

            logger.info(f"PDF report generated: {output_file}")
            return output_file

        except Exception as e:
            logger.error(f"Failed to generate PDF report: {e}")
            return ""

    def generate_summary_report(self,
                              start_time: Optional[datetime] = None,
                              end_time: Optional[datetime] = None) -> Dict:
        """Generate a summary report as a dictionary"""

        if not start_time:
            start_time = datetime.now() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.now()

        try:
            # Get basic statistics
            stats = self.db.get_statistics(start_time, end_time)

            # Get anomalies
            anomalies = self.db.detect_anomalies()

            # Calculate additional metrics
            metrics_data = self.db.get_performance_metrics_history(start_time, end_time, limit=100)

            summary = {
                'report_info': {
                    'generated_at': datetime.now().isoformat(),
                    'period_start': start_time.isoformat(),
                    'period_end': end_time.isoformat(),
                    'duration_hours': (end_time - start_time).total_seconds() / 3600
                },
                'statistics': stats,
                'anomalies': {
                    'count': len(anomalies),
                    'high_severity': len([a for a in anomalies if a.get('severity') == 'high']),
                    'medium_severity': len([a for a in anomalies if a.get('severity') == 'medium']),
                    'details': anomalies[:5]  # Top 5 anomalies
                },
                'performance': {
                    'total_data_points': len(metrics_data),
                    'avg_connections_per_hour': sum(m.get('connections_per_hour', 0) for m in metrics_data) / len(metrics_data) if metrics_data else 0,
                    'avg_requests_per_hour': sum(m.get('requests_per_hour', 0) for m in metrics_data) / len(metrics_data) if metrics_data else 0,
                    'total_errors': sum(m.get('errors_total', 0) for m in metrics_data) if metrics_data else 0
                }
            }

            return summary

        except Exception as e:
            logger.error(f"Failed to generate summary report: {e}")
            return {}

    def schedule_report_generation(self,
                                 report_type: str = "html",
                                 interval_hours: int = 24,
                                 output_dir: str = "reports") -> bool:
        """Schedule automatic report generation (placeholder for future implementation)"""
        # This would typically integrate with a task scheduler like celery or cron
        # For now, it's a placeholder that logs the scheduling request

        logger.info(f"Report scheduling requested: {report_type} every {interval_hours} hours to {output_dir}")

        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(exist_ok=True)

        # In a real implementation, this would set up the scheduling
        return True

    def export_data_for_external_analysis(self,
                                        start_time: Optional[datetime] = None,
                                        end_time: Optional[datetime] = None,
                                        output_dir: str = "exports") -> Dict[str, str]:
        """Export data in multiple formats for external analysis"""

        if not start_time:
            start_time = datetime.now() - timedelta(days=7)
        if not end_time:
            end_time = datetime.now()

        # Create output directory
        Path(output_dir).mkdir(exist_ok=True)

        exported_files = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        try:
            # Export connection events
            csv_file = f"{output_dir}/connection_events_{timestamp}.csv"
            self.db.export_to_csv("connection_events", csv_file, start_time, end_time)
            exported_files['connection_events_csv'] = csv_file

            json_file = f"{output_dir}/connection_events_{timestamp}.json"
            self.db.export_to_json("connection_events", json_file, start_time, end_time)
            exported_files['connection_events_json'] = json_file

            # Export device status
            csv_file = f"{output_dir}/device_status_{timestamp}.csv"
            self.db.export_to_csv("device_status", csv_file, start_time, end_time)
            exported_files['device_status_csv'] = csv_file

            # Export performance metrics
            csv_file = f"{output_dir}/performance_metrics_{timestamp}.csv"
            self.db.export_to_csv("performance_metrics", csv_file, start_time, end_time)
            exported_files['performance_metrics_csv'] = csv_file

            logger.info(f"Data exported to {len(exported_files)} files in {output_dir}")

        except Exception as e:
            logger.error(f"Failed to export data: {e}")

        return exported_files
