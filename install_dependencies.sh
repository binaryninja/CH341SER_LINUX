#!/bin/bash

# ESP Monitor Database and Reporting Features - Installation Script
# ================================================================
# This script installs all required dependencies for the enhanced ESP monitoring
# system with database persistence and reporting capabilities.

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}ESP Monitor Enhanced Features Installation${NC}"
echo "=========================================="
echo

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo "Please install Python 3.7 or higher before running this script"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo -e "Python version: ${GREEN}${PYTHON_VERSION}${NC}"

# Check Python version (require 3.7+)
if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 7) else 1)'; then
    echo -e "${GREEN}✓ Python version is compatible${NC}"
else
    echo -e "${RED}✗ Python 3.7 or higher is required${NC}"
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}Warning: pip3 not found, attempting to install...${NC}"

    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y python3-pip
    elif command -v yum &> /dev/null; then
        sudo yum install -y python3-pip
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y python3-pip
    else
        echo -e "${RED}Error: Cannot install pip3 automatically${NC}"
        echo "Please install pip3 manually for your distribution"
        exit 1
    fi
fi

# Create virtual environment (optional but recommended)
echo
read -p "Create a virtual environment? (recommended) [Y/n]: " create_venv
create_venv=${create_venv:-Y}

if [[ $create_venv =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Creating virtual environment...${NC}"

    if ! python3 -m venv esp_monitor_env; then
        echo -e "${YELLOW}Warning: Failed to create venv, installing system-wide${NC}"
        USE_VENV=false
    else
        echo -e "${GREEN}✓ Virtual environment created${NC}"
        source esp_monitor_env/bin/activate
        echo -e "${GREEN}✓ Virtual environment activated${NC}"
        USE_VENV=true
    fi
else
    USE_VENV=false
    echo -e "${YELLOW}Installing dependencies system-wide${NC}"
fi

# Upgrade pip
echo -e "${BLUE}Upgrading pip...${NC}"
python3 -m pip install --upgrade pip

# Install system dependencies for matplotlib and other packages
echo -e "${BLUE}Installing system dependencies...${NC}"

if command -v apt-get &> /dev/null; then
    # Debian/Ubuntu
    sudo apt-get update
    sudo apt-get install -y \
        python3-dev \
        python3-tk \
        libfreetype6-dev \
        libpng-dev \
        pkg-config \
        build-essential
elif command -v yum &> /dev/null; then
    # CentOS/RHEL
    sudo yum install -y \
        python3-devel \
        python3-tkinter \
        freetype-devel \
        libpng-devel \
        pkgconfig \
        gcc \
        gcc-c++
elif command -v dnf &> /dev/null; then
    # Fedora
    sudo dnf install -y \
        python3-devel \
        python3-tkinter \
        freetype-devel \
        libpng-devel \
        pkgconf \
        gcc \
        gcc-c++
elif command -v pacman &> /dev/null; then
    # Arch Linux
    sudo pacman -S --needed \
        python-pip \
        tk \
        freetype2 \
        libpng \
        pkgconf \
        base-devel
else
    echo -e "${YELLOW}Warning: Unknown package manager. You may need to install development packages manually${NC}"
fi

# Install Python dependencies
echo -e "${BLUE}Installing Python dependencies...${NC}"

# Install core dependencies
echo "Installing core dependencies..."
python3 -m pip install pyserial>=3.5

# Install data handling dependencies
echo "Installing data handling dependencies..."
python3 -m pip install pandas>=1.3.0

# Install visualization dependencies
echo "Installing visualization dependencies..."
python3 -m pip install matplotlib>=3.5.0 seaborn>=0.11.0

# Install templating engine
echo "Installing templating engine..."
python3 -m pip install jinja2>=3.0.0

# Verify installations
echo
echo -e "${BLUE}Verifying installations...${NC}"

FAILED_IMPORTS=()

# Test imports
for package in pyserial pandas matplotlib seaborn jinja2; do
    if python3 -c "import ${package}" 2>/dev/null; then
        echo -e "${GREEN}✓ ${package}${NC}"
    else
        echo -e "${RED}✗ ${package}${NC}"
        FAILED_IMPORTS+=($package)
    fi
done

# Special check for serial (pyserial import name is different)
if python3 -c "import serial" 2>/dev/null; then
    echo -e "${GREEN}✓ serial (pyserial)${NC}"
else
    echo -e "${RED}✗ serial (pyserial)${NC}"
    FAILED_IMPORTS+=(serial)
fi

# Check if any imports failed
if [ ${#FAILED_IMPORTS[@]} -gt 0 ]; then
    echo
    echo -e "${RED}Some dependencies failed to install:${NC}"
    for package in "${FAILED_IMPORTS[@]}"; do
        echo -e "  ${RED}- ${package}${NC}"
    done
    echo
    echo -e "${YELLOW}You can try installing them manually with:${NC}"
    echo "  pip3 install <package_name>"
    exit 1
fi

# Test database functionality
echo
echo -e "${BLUE}Testing database functionality...${NC}"
if python3 -c "
import sqlite3
import tempfile
import os
with tempfile.NamedTemporaryFile(delete=False) as f:
    db_path = f.name
try:
    conn = sqlite3.connect(db_path)
    conn.execute('CREATE TABLE test (id INTEGER)')
    conn.close()
    print('Database test: OK')
finally:
    os.unlink(db_path)
" 2>/dev/null; then
    echo -e "${GREEN}✓ Database functionality working${NC}"
else
    echo -e "${RED}✗ Database functionality test failed${NC}"
fi

# Test matplotlib backend
echo -e "${BLUE}Testing matplotlib backend...${NC}"
if python3 -c "
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
x = np.linspace(0, 10, 100)
y = np.sin(x)
plt.figure(figsize=(6, 4))
plt.plot(x, y)
plt.savefig('/tmp/test_plot.png')
plt.close()
print('Matplotlib test: OK')
" 2>/dev/null; then
    echo -e "${GREEN}✓ Matplotlib working${NC}"
    rm -f /tmp/test_plot.png
else
    echo -e "${YELLOW}⚠ Matplotlib may have issues with GUI backend${NC}"
    echo "  This won't affect report generation functionality"
fi

# Create sample configuration
echo
echo -e "${BLUE}Creating sample configuration...${NC}"
if [ ! -f "esp_config.json" ]; then
    cat > esp_config.json << EOF
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
EOF
    echo -e "${GREEN}✓ Sample configuration created: esp_config.json${NC}"
else
    echo -e "${YELLOW}Configuration file already exists: esp_config.json${NC}"
fi

# Set up directories
echo -e "${BLUE}Setting up directories...${NC}"
mkdir -p reports exports logs
echo -e "${GREEN}✓ Created directories: reports/, exports/, logs/${NC}"

# Make scripts executable
chmod +x esp_monitor.py 2>/dev/null || true

# Display usage information
echo
echo -e "${GREEN}Installation completed successfully!${NC}"
echo
echo -e "${BLUE}Usage Examples:${NC}"
echo "=================="

if [ "$USE_VENV" = true ]; then
    echo -e "${YELLOW}Remember to activate the virtual environment before use:${NC}"
    echo "  source esp_monitor_env/bin/activate"
    echo
fi

echo "Basic monitoring:"
echo "  python3 esp_monitor.py"
echo
echo "Web interface:"
echo "  python3 esp_monitor.py --web-interface"
echo
echo "Generate HTML report:"
echo "  python3 esp_monitor.py --generate-report html --report-hours 24"
echo
echo "Export data to CSV:"
echo "  python3 esp_monitor.py --export-data csv"
echo
echo "Check for anomalies:"
echo "  python3 esp_monitor.py --detect-anomalies"
echo
echo "Show statistics:"
echo "  python3 esp_monitor.py --statistics --stats-hours 48"
echo
echo "Clean up old data:"
echo "  python3 esp_monitor.py --cleanup-data 30"
echo

echo -e "${BLUE}Configuration:${NC}"
echo "=============="
echo "Edit esp_config.json to customize settings"
echo "Database will be created automatically on first use"
echo
echo -e "${BLUE}Troubleshooting:${NC}"
echo "==============="
echo "If you encounter serial port permissions issues, add your user to the dialout group:"
echo "  sudo usermod -a -G dialout \$USER"
echo "Then log out and log back in."
echo
echo "For GUI display issues with matplotlib on headless systems, the script will"
echo "automatically use a non-interactive backend for report generation."
echo
echo -e "${GREEN}Happy monitoring! 🚀${NC}"
