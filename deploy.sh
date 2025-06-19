#!/bin/bash
# ESP Module Web Server Deployment Orchestrator
# =============================================
# This script provides a complete deployment pipeline for ESP modules
# connected via CH340/CH341 USB-to-serial converters.
#
# Features:
# - Automated environment setup
# - Device detection and verification
# - WiFi configuration
# - Web server deployment
# - Monitoring and management
# - Recovery and troubleshooting
#
# Usage:
#   ./deploy.sh                    # Interactive deployment
#   ./deploy.sh --auto             # Automated deployment with defaults
#   ./deploy.sh --monitor          # Start monitoring existing deployment
#   ./deploy.sh --status           # Check deployment status
#   ./deploy.sh --reset            # Reset and redeploy
#   ./deploy.sh --arduino          # Flash Arduino firmware instead of AT

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/esp_config.json"
LOG_FILE="$SCRIPT_DIR/deployment.log"
DEVICE_PORT="/dev/ttyUSB0"
WEB_PORT=8080

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" >&2
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1" >> "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1" >> "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1" >> "$LOG_FILE"
}

# Banner function
show_banner() {
    echo -e "${BLUE}"
    cat << "EOF"
 ███████╗███████╗██████╗     ██████╗ ███████╗██████╗ ██╗      ██████╗ ██╗   ██╗
 ██╔════╝██╔════╝██╔══██╗    ██╔══██╗██╔════╝██╔══██╗██║     ██╔═══██╗╚██╗ ██╔╝
 █████╗  ███████╗██████╔╝    ██║  ██║█████╗  ██████╔╝██║     ██║   ██║ ╚████╔╝
 ██╔══╝  ╚════██║██╔═══╝     ██║  ██║██╔══╝  ██╔═══╝ ██║     ██║   ██║  ╚██╔╝
 ███████╗███████║██║         ██████╔╝███████╗██║     ███████╗╚██████╔╝   ██║
 ╚══════╝╚══════╝╚═╝         ╚═════╝ ╚══════╝╚═╝     ╚══════╝ ╚═════╝    ╚═╝

           Web Server Deployment for ESP Modules via CH340/CH341
EOF
    echo -e "${NC}"
}

# Check if running as root for certain operations
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root. This is not recommended for normal operation."
    fi
}

# Check system requirements
check_requirements() {
    log "Checking system requirements..."

    local missing_deps=()

    # Check Python3
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    fi

    # Check pip3
    if ! command -v pip3 &> /dev/null; then
        missing_deps+=("python3-pip")
    fi

    # Check if pyserial is installed
    if ! python3 -c "import serial" &> /dev/null; then
        log_info "PySerial not found, will install..."
        pip3 install pyserial
    fi

    # Check if device exists
    if [[ ! -e "$DEVICE_PORT" ]]; then
        log_error "Device $DEVICE_PORT not found!"
        log_error "Please ensure CH340/CH341 driver is loaded and device is connected."
        return 1
    fi

    # Check permissions
    if [[ ! -r "$DEVICE_PORT" ]] || [[ ! -w "$DEVICE_PORT" ]]; then
        log_warning "No read/write permissions for $DEVICE_PORT"
        log_info "Adding user to dialout group..."
        sudo usermod -a -G dialout "$USER"
        log_info "You may need to log out and back in for permissions to take effect."

        # Try to fix permissions temporarily
        sudo chmod 666 "$DEVICE_PORT" 2>/dev/null || true
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_info "Install with: sudo apt-get install ${missing_deps[*]}"
        return 1
    fi

    log "✓ All requirements satisfied"
    return 0
}

# Detect ESP module
detect_esp_module() {
    log "Detecting ESP module..."

    if python3 "$SCRIPT_DIR/probe_device.py" > /tmp/esp_probe.log 2>&1; then
        if grep -q "ESP module detected" /tmp/esp_probe.log; then
            log "✓ ESP module detected and responding"
            return 0
        fi
    fi

    log_error "Failed to detect ESP module"
    log_info "Probe output:"
    cat /tmp/esp_probe.log
    return 1
}

# Interactive WiFi configuration
configure_wifi_interactive() {
    log "WiFi Configuration"
    echo "=================="

    read -p "Enter WiFi SSID: " WIFI_SSID
    if [[ -z "$WIFI_SSID" ]]; then
        log_error "SSID cannot be empty"
        return 1
    fi

    read -s -p "Enter WiFi Password: " WIFI_PASSWORD
    echo

    # Confirm settings
    echo
    echo "WiFi Settings:"
    echo "SSID: $WIFI_SSID"
    echo "Password: [hidden]"
    echo

    read -p "Proceed with these settings? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "WiFi configuration cancelled"
        return 1
    fi

    return 0
}

# Deploy web server
deploy_webserver() {
    log "Deploying web server to ESP module..."

    local deployment_cmd="python3 $SCRIPT_DIR/deploy_webserver.py"

    if [[ -n "$WIFI_SSID" ]]; then
        deployment_cmd+=" --wifi-ssid '$WIFI_SSID'"
        if [[ -n "$WIFI_PASSWORD" ]]; then
            deployment_cmd+=" --wifi-password '$WIFI_PASSWORD'"
        fi
    fi

    log_info "Executing deployment command..."
    if eval "$deployment_cmd"; then
        log "✓ Web server deployment completed successfully"
        return 0
    else
        log_error "Web server deployment failed"
        return 1
    fi
}

# Start monitoring
start_monitoring() {
    log "Starting ESP module monitoring..."

    local monitor_cmd="python3 $SCRIPT_DIR/esp_monitor.py"

    if [[ "$1" == "web" ]]; then
        monitor_cmd+=" --web-interface --web-port $WEB_PORT"
        log_info "Web interface will be available at http://localhost:$WEB_PORT"
    fi

    log_info "Starting monitor (Press Ctrl+C to stop)..."
    exec $monitor_cmd
}

# Get deployment status
get_status() {
    log "Checking ESP module status..."

    if python3 "$SCRIPT_DIR/esp_monitor.py" --status; then
        return 0
    else
        log_error "Failed to get module status"
        return 1
    fi
}

# Reset and redeploy
reset_and_redeploy() {
    log "Resetting ESP module and redeploying..."

    # Reset device
    if python3 "$SCRIPT_DIR/esp_monitor.py" --reset; then
        log "✓ Device reset successful"
        sleep 5
    else
        log_warning "Device reset failed, continuing anyway..."
    fi

    # Redeploy
    deploy_webserver
}

# Recovery mode
recovery_mode() {
    log_warning "Entering recovery mode..."

    echo "Recovery Options:"
    echo "1. Reset ESP module"
    echo "2. Check device connection"
    echo "3. Reinstall dependencies"
    echo "4. Manual AT command interface"
    echo "5. Exit recovery"

    read -p "Select option (1-5): " -n 1 -r
    echo

    case $REPLY in
        1)
            python3 "$SCRIPT_DIR/esp_monitor.py" --reset
            ;;
        2)
            check_requirements
            detect_esp_module
            ;;
        3)
            pip3 install --upgrade pyserial
            ;;
        4)
            log_info "Starting manual AT command interface..."
            log_info "Use 'exit' to quit"
            python3 -c "
import serial
import sys
try:
    ser = serial.Serial('$DEVICE_PORT', 115200, timeout=1)
    print('Connected to $DEVICE_PORT')
    print('Type AT commands (or \"exit\" to quit):')
    while True:
        cmd = input('AT> ')
        if cmd.lower() == 'exit':
            break
        ser.write((cmd + '\r\n').encode())
        import time
        time.sleep(1)
        response = ser.read_all().decode('utf-8', errors='ignore')
        print(response)
    ser.close()
except Exception as e:
    print(f'Error: {e}')
"
            ;;
        5)
            log_info "Exiting recovery mode"
            ;;
        *)
            log_error "Invalid option"
            ;;
    esac
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    # Kill any background processes
    jobs -p | xargs -r kill 2>/dev/null || true
}

# Deploy Arduino firmware
deploy_arduino_firmware() {
    log "Deploying Arduino firmware to ESP module..."

    local arduino_cmd="python3 '$SCRIPT_DIR/flash_arduino_firmware.py'"
    arduino_cmd+=" --port '$DEVICE_PORT'"

    if [[ -n "$WIFI_SSID" ]]; then
        arduino_cmd+=" --wifi-ssid '$WIFI_SSID'"
        if [[ -n "$WIFI_PASSWORD" ]]; then
            arduino_cmd+=" --wifi-password '$WIFI_PASSWORD'"
        fi
    fi

    log_info "Executing Arduino firmware flashing..."
    if eval "$arduino_cmd"; then
        log "✓ Arduino firmware deployment completed successfully"
        return 0
    else
        log_error "Arduino firmware deployment failed"
        return 1
    fi
}

# Main deployment function
main_deploy() {
    log "Starting ESP module deployment pipeline..."

    # Check requirements
    if ! check_requirements; then
        log_error "Requirements check failed"
        return 1
    fi

    # Detect ESP module
    if ! detect_esp_module; then
        log_error "ESP module detection failed"
        return 1
    fi

    # Configure WiFi (if not provided via command line)
    if [[ -z "$WIFI_SSID" ]] && [[ "$AUTO_MODE" != "true" ]]; then
        if ! configure_wifi_interactive; then
            log_error "WiFi configuration failed"
            return 1
        fi
    fi

    # Choose deployment method
    if [[ "$ARDUINO_MODE" == "true" ]]; then
        # Deploy Arduino firmware
        if ! deploy_arduino_firmware; then
            log_error "Arduino firmware deployment failed"
            return 1
        fi
    else
        # Deploy AT firmware web server
        if ! deploy_webserver; then
            log_error "Web server deployment failed"
            return 1
        fi
    fi

    log "🎉 Deployment completed successfully!"
    if [[ "$ARDUINO_MODE" == "true" ]]; then
        log_info "Your ESP Arduino web server should now be accessible via WiFi"
        log_info "Check the serial monitor for the IP address"
    else
        log_info "Your ESP web server should now be accessible via WiFi"
    fi

    # Ask if user wants to start monitoring
    if [[ "$AUTO_MODE" != "true" ]] && [[ "$ARDUINO_MODE" != "true" ]]; then
        echo
        read -p "Start monitoring now? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            start_monitoring
        fi
    fi

    return 0
}

# Help function
show_help() {
    cat << EOF
ESP Module Web Server Deployment Script

Usage: $0 [OPTIONS]

OPTIONS:
    --auto              Automated deployment with defaults
    --monitor           Start monitoring existing deployment
    --web-monitor       Start web-based monitoring interface
    --status            Check deployment status
    --reset             Reset and redeploy
    --recovery          Enter recovery mode
    --wifi-ssid SSID    WiFi network name
    --wifi-password PWD WiFi password
    --device PORT       Serial device (default: $DEVICE_PORT)
    --web-port PORT     Web interface port (default: $WEB_PORT)
    --arduino           Flash Arduino firmware (recommended)
    --help              Show this help message

EXAMPLES:
    $0                                    # Interactive deployment
    $0 --auto                            # Automated deployment
    $0 --wifi-ssid "MyWiFi" --wifi-password "MyPassword"
    $0 --arduino --wifi-ssid "MyWiFi" --wifi-password "MyPassword"
    $0 --monitor                         # Start monitoring
    $0 --web-monitor                     # Start web interface
    $0 --status                          # Check status
    $0 --reset                           # Reset and redeploy

TROUBLESHOOTING:
    $0 --recovery                        # Enter recovery mode
    $0 --device /dev/ttyUSB1            # Use different device
    $0 --arduino                         # Use Arduino firmware (recommended)

For more information, see the README or visit:
https://github.com/your-repo/esp-deployment
EOF
}

# Signal handlers
trap cleanup EXIT
trap 'log_info "Interrupted by user"; exit 130' INT TERM

# Parse command line arguments
AUTO_MODE="false"
MONITOR_MODE="false"
WEB_MONITOR_MODE="false"
STATUS_MODE="false"
RESET_MODE="false"
RECOVERY_MODE="false"
ARDUINO_MODE="false"
WIFI_SSID=""
WIFI_PASSWORD=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --auto)
            AUTO_MODE="true"
            shift
            ;;
        --monitor)
            MONITOR_MODE="true"
            shift
            ;;
        --web-monitor)
            WEB_MONITOR_MODE="true"
            shift
            ;;
        --status)
            STATUS_MODE="true"
            shift
            ;;
        --reset)
            RESET_MODE="true"
            shift
            ;;
        --recovery)
            RECOVERY_MODE="true"
            shift
            ;;
        --arduino)
            ARDUINO_MODE="true"
            shift
            ;;
        --wifi-ssid)
            WIFI_SSID="$2"
            shift 2
            ;;
        --wifi-password)
            WIFI_PASSWORD="$2"
            shift 2
            ;;
        --device)
            DEVICE_PORT="$2"
            shift 2
            ;;
        --web-port)
            WEB_PORT="$2"
            shift 2
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
main() {
    # Initialize log file
    echo "=== ESP Deployment Log - $(date) ===" > "$LOG_FILE"

    # Show banner
    show_banner

    # Check if running as root
    check_root

    # Handle different modes
    if [[ "$STATUS_MODE" == "true" ]]; then
        get_status
    elif [[ "$RESET_MODE" == "true" ]]; then
        reset_and_redeploy
    elif [[ "$RECOVERY_MODE" == "true" ]]; then
        recovery_mode
    elif [[ "$MONITOR_MODE" == "true" ]]; then
        start_monitoring
    elif [[ "$WEB_MONITOR_MODE" == "true" ]]; then
        start_monitoring "web"
    elif [[ "$ARDUINO_MODE" == "true" ]]; then
        # Arduino firmware deployment
        main_deploy
    else
        # Default: run deployment
        main_deploy
    fi
}

# Run main function
main "$@"
