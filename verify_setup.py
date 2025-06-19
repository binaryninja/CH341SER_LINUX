#!/usr/bin/env python3
"""
ESP Deployment System Verification Script
=========================================
This script verifies that the ESP deployment system is properly configured
and ready for use. It checks hardware, software, and configuration.

Usage:
    python3 verify_setup.py
    python3 verify_setup.py --detailed
    python3 verify_setup.py --fix-issues
"""

import os
import sys
import subprocess
import json
import serial
import time
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class SystemVerifier:
    def __init__(self, detailed: bool = False, fix_issues: bool = False):
        self.detailed = detailed
        self.fix_issues = fix_issues
        self.script_dir = Path(__file__).parent
        self.results = {
            'passed': [],
            'failed': [],
            'warnings': [],
            'fixed': []
        }

    def print_header(self, text: str):
        """Print formatted header"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")

    def print_success(self, text: str):
        """Print success message"""
        print(f"{Colors.GREEN}✓ {text}{Colors.END}")
        self.results['passed'].append(text)

    def print_error(self, text: str):
        """Print error message"""
        print(f"{Colors.RED}✗ {text}{Colors.END}")
        self.results['failed'].append(text)

    def print_warning(self, text: str):
        """Print warning message"""
        print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")
        self.results['warnings'].append(text)

    def print_info(self, text: str):
        """Print info message"""
        if self.detailed:
            print(f"{Colors.CYAN}ℹ {text}{Colors.END}")

    def print_fixed(self, text: str):
        """Print fixed issue message"""
        print(f"{Colors.MAGENTA}🔧 {text}{Colors.END}")
        self.results['fixed'].append(text)

    def run_command(self, command: str, capture_output: bool = True) -> Tuple[bool, str]:
        """Run shell command and return success status and output"""
        try:
            if capture_output:
                result = subprocess.run(
                    command, shell=True, capture_output=True, text=True, timeout=30
                )
                return result.returncode == 0, result.stdout + result.stderr
            else:
                result = subprocess.run(command, shell=True, timeout=30)
                return result.returncode == 0, ""
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    def check_python_environment(self) -> bool:
        """Check Python environment and dependencies"""
        self.print_header("PYTHON ENVIRONMENT")

        # Check Python version
        python_version = sys.version_info
        if python_version.major == 3 and python_version.minor >= 6:
            self.print_success(f"Python {python_version.major}.{python_version.minor}.{python_version.micro}")
        else:
            self.print_error(f"Python version {python_version.major}.{python_version.minor} is too old (need 3.6+)")
            return False

        # Check pip
        success, output = self.run_command("pip3 --version")
        if success:
            self.print_success("pip3 is available")
        else:
            self.print_error("pip3 not found")
            if self.fix_issues:
                self.print_info("Installing pip3...")
                success, _ = self.run_command("sudo apt-get update && sudo apt-get install -y python3-pip")
                if success:
                    self.print_fixed("pip3 installed successfully")
                else:
                    self.print_error("Failed to install pip3")
                    return False
            else:
                return False

        # Check required Python packages
        required_packages = ['serial', 'json', 'threading', 'queue', 'http.server']
        for package in required_packages:
            try:
                __import__(package)
                self.print_success(f"Package '{package}' is available")
            except ImportError:
                if package == 'serial':
                    self.print_error(f"Package 'pyserial' not found")
                    if self.fix_issues:
                        self.print_info("Installing pyserial...")
                        success, _ = self.run_command("pip3 install pyserial")
                        if success:
                            self.print_fixed("pyserial installed successfully")
                        else:
                            self.print_error("Failed to install pyserial")
                            return False
                    else:
                        return False
                else:
                    self.print_error(f"Package '{package}' not found")
                    return False

        return True

    def check_system_permissions(self) -> bool:
        """Check system permissions and user groups"""
        self.print_header("SYSTEM PERMISSIONS")

        # Check if user is in dialout group
        success, output = self.run_command("groups")
        if 'dialout' in output:
            self.print_success("User is in dialout group")
        else:
            self.print_warning("User is not in dialout group")
            if self.fix_issues:
                self.print_info("Adding user to dialout group...")
                username = os.getenv('USER')
                success, _ = self.run_command(f"sudo usermod -a -G dialout {username}")
                if success:
                    self.print_fixed("User added to dialout group (logout/login required)")
                else:
                    self.print_error("Failed to add user to dialout group")

        # Check sudo privileges
        success, _ = self.run_command("sudo -n true")
        if success:
            self.print_success("Sudo privileges available")
        else:
            self.print_warning("Sudo privileges may be required for some operations")

        return True

    def check_hardware_drivers(self) -> bool:
        """Check CH340/CH341 drivers and hardware"""
        self.print_header("HARDWARE & DRIVERS")

        # Check if CH340/CH341 module is loaded
        success, output = self.run_command("lsmod | grep ch34x")
        if success and output.strip():
            self.print_success("CH34x driver module is loaded")
        else:
            self.print_warning("CH34x driver module not loaded")
            if self.fix_issues:
                self.print_info("Loading CH34x driver...")
                success, _ = self.run_command("sudo modprobe usbserial")
                if success:
                    driver_path = self.script_dir / "ch34x.ko"
                    if driver_path.exists():
                        success, _ = self.run_command(f"sudo insmod {driver_path}")
                        if success:
                            self.print_fixed("CH34x driver loaded successfully")
                        else:
                            self.print_error("Failed to load CH34x driver")
                    else:
                        self.print_error("CH34x driver file not found")

        # Check for CH340/CH341 USB devices
        success, output = self.run_command("lsusb | grep -i ch34")
        if success and output.strip():
            self.print_success("CH340/CH341 USB device detected")
            if self.detailed:
                for line in output.strip().split('\n'):
                    self.print_info(f"Device: {line.strip()}")
        else:
            self.print_error("No CH340/CH341 USB devices found")
            self.print_info("Make sure your device is connected and powered")
            return False

        # Check for serial devices
        success, output = self.run_command("ls -la /dev/ttyUSB*")
        if success:
            self.print_success("Serial devices found")
            if self.detailed:
                for line in output.strip().split('\n'):
                    if 'ttyUSB' in line:
                        self.print_info(f"Device: {line.strip()}")
        else:
            self.print_error("No /dev/ttyUSB* devices found")
            return False

        return True

    def check_serial_communication(self) -> bool:
        """Test serial communication with ESP device"""
        self.print_header("SERIAL COMMUNICATION")

        # Find available serial ports
        serial_ports = []
        for i in range(10):  # Check ttyUSB0 to ttyUSB9
            port = f'/dev/ttyUSB{i}'
            if os.path.exists(port):
                serial_ports.append(port)

        if not serial_ports:
            self.print_error("No serial ports found")
            return False

        self.print_success(f"Found {len(serial_ports)} serial port(s)")

        # Test communication on each port
        for port in serial_ports:
            self.print_info(f"Testing {port}...")

            # Check port permissions
            if not os.access(port, os.R_OK | os.W_OK):
                self.print_warning(f"No read/write permissions for {port}")
                if self.fix_issues:
                    success, _ = self.run_command(f"sudo chmod 666 {port}")
                    if success:
                        self.print_fixed(f"Fixed permissions for {port}")
                    else:
                        self.print_error(f"Failed to fix permissions for {port}")
                        continue
                else:
                    continue

            # Test serial communication
            baudrates = [115200, 9600, 57600, 38400, 19200]
            for baudrate in baudrates:
                try:
                    ser = serial.Serial(port, baudrate, timeout=2)
                    time.sleep(1)

                    # Send AT command
                    ser.write(b'AT\r\n')
                    time.sleep(1)
                    response = ser.read_all().decode('utf-8', errors='ignore')

                    ser.close()

                    if 'OK' in response:
                        self.print_success(f"ESP device responds on {port} at {baudrate} baud")
                        if self.detailed:
                            self.print_info(f"Response: {response.strip()}")
                        return True

                except Exception as e:
                    if self.detailed:
                        self.print_info(f"Failed {port} at {baudrate}: {str(e)}")
                    continue

        self.print_error("No responsive ESP device found")
        self.print_info("Check device power, connections, and firmware")
        return False

    def check_project_files(self) -> bool:
        """Check project files and configuration"""
        self.print_header("PROJECT FILES")

        required_files = [
            'deploy.sh',
            'deploy_webserver.py',
            'esp_monitor.py',
            'probe_device.py',
            'esp_config.json'
        ]

        all_present = True
        for filename in required_files:
            filepath = self.script_dir / filename
            if filepath.exists():
                self.print_success(f"{filename} exists")

                # Check if executable
                if filename.endswith('.sh'):
                    if os.access(filepath, os.X_OK):
                        self.print_success(f"{filename} is executable")
                    else:
                        self.print_warning(f"{filename} is not executable")
                        if self.fix_issues:
                            success, _ = self.run_command(f"chmod +x {filepath}")
                            if success:
                                self.print_fixed(f"Made {filename} executable")
                            else:
                                self.print_error(f"Failed to make {filename} executable")

            else:
                self.print_error(f"{filename} not found")
                all_present = False

        # Check configuration file
        config_file = self.script_dir / 'esp_config.json'
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    self.print_success("Configuration file is valid JSON")

                    # Check required sections
                    required_sections = ['device', 'wifi', 'webserver']
                    for section in required_sections:
                        if section in config:
                            self.print_success(f"Config section '{section}' present")
                        else:
                            self.print_warning(f"Config section '{section}' missing")

            except json.JSONDecodeError as e:
                self.print_error(f"Configuration file has invalid JSON: {e}")
                all_present = False

        return all_present

    def check_network_connectivity(self) -> bool:
        """Check network connectivity"""
        self.print_header("NETWORK CONNECTIVITY")

        # Check internet connectivity
        success, _ = self.run_command("ping -c 1 google.com")
        if success:
            self.print_success("Internet connectivity available")
        else:
            self.print_warning("No internet connectivity (may affect some features)")

        # Check local network interfaces
        success, output = self.run_command("ip addr show")
        if success:
            interfaces = []
            for line in output.split('\n'):
                if 'inet ' in line and '127.0.0.1' not in line:
                    interfaces.append(line.strip())

            if interfaces:
                self.print_success(f"Found {len(interfaces)} network interface(s)")
                if self.detailed:
                    for interface in interfaces:
                        self.print_info(f"Interface: {interface}")
            else:
                self.print_warning("No active network interfaces found")

        return True

    def test_deployment_pipeline(self) -> bool:
        """Test the deployment pipeline components"""
        self.print_header("DEPLOYMENT PIPELINE")

        # Test device probe
        probe_script = self.script_dir / 'probe_device.py'
        if probe_script.exists():
            self.print_info("Testing device probe...")
            success, output = self.run_command(f"timeout 10 python3 {probe_script}")
            if success:
                self.print_success("Device probe script works")
            else:
                self.print_warning("Device probe script failed or timed out")

        # Test web server deployment script
        deploy_script = self.script_dir / 'deploy_webserver.py'
        if deploy_script.exists():
            self.print_info("Testing deployment script syntax...")
            success, output = self.run_command(f"python3 -m py_compile {deploy_script}")
            if success:
                self.print_success("Deployment script syntax is valid")
            else:
                self.print_error(f"Deployment script syntax error: {output}")
                return False

        # Test monitoring script
        monitor_script = self.script_dir / 'esp_monitor.py'
        if monitor_script.exists():
            self.print_info("Testing monitoring script syntax...")
            success, output = self.run_command(f"python3 -m py_compile {monitor_script}")
            if success:
                self.print_success("Monitoring script syntax is valid")
            else:
                self.print_error(f"Monitoring script syntax error: {output}")
                return False

        return True

    def generate_report(self):
        """Generate verification report"""
        self.print_header("VERIFICATION REPORT")

        total_checks = (len(self.results['passed']) +
                       len(self.results['failed']) +
                       len(self.results['warnings']))

        print(f"\n{Colors.BOLD}Summary:{Colors.END}")
        print(f"  {Colors.GREEN}✓ Passed: {len(self.results['passed'])}{Colors.END}")
        print(f"  {Colors.RED}✗ Failed: {len(self.results['failed'])}{Colors.END}")
        print(f"  {Colors.YELLOW}⚠ Warnings: {len(self.results['warnings'])}{Colors.END}")

        if self.fix_issues:
            print(f"  {Colors.MAGENTA}🔧 Fixed: {len(self.results['fixed'])}{Colors.END}")

        print(f"  Total checks: {total_checks}")

        # Calculate health score
        health_score = (len(self.results['passed']) / max(total_checks, 1)) * 100

        print(f"\n{Colors.BOLD}System Health: {health_score:.1f}%{Colors.END}")

        if health_score >= 90:
            print(f"{Colors.GREEN}🎉 System is ready for ESP deployment!{Colors.END}")
        elif health_score >= 70:
            print(f"{Colors.YELLOW}⚠ System has some issues but should work{Colors.END}")
        else:
            print(f"{Colors.RED}❌ System needs attention before deployment{Colors.END}")

        # Recommendations
        if len(self.results['failed']) > 0:
            print(f"\n{Colors.BOLD}Critical Issues:{Colors.END}")
            for issue in self.results['failed']:
                print(f"  • {issue}")

        if len(self.results['warnings']) > 0:
            print(f"\n{Colors.BOLD}Warnings:{Colors.END}")
            for warning in self.results['warnings']:
                print(f"  • {warning}")

        # Next steps
        print(f"\n{Colors.BOLD}Next Steps:{Colors.END}")
        if len(self.results['failed']) == 0:
            print("  1. Run deployment: ./deploy.sh")
            print("  2. Configure WiFi settings")
            print("  3. Start monitoring: ./deploy.sh --monitor")
        else:
            print("  1. Fix critical issues listed above")
            print("  2. Re-run verification: python3 verify_setup.py --fix-issues")
            print("  3. Try deployment when all issues are resolved")

    def run_verification(self) -> bool:
        """Run complete verification"""
        print(f"{Colors.BOLD}{Colors.CYAN}")
        print("ESP Deployment System Verification")
        print("=" * 40)
        print(f"{Colors.END}")

        checks = [
            self.check_python_environment,
            self.check_system_permissions,
            self.check_hardware_drivers,
            self.check_serial_communication,
            self.check_project_files,
            self.check_network_connectivity,
            self.test_deployment_pipeline
        ]

        all_passed = True
        for check in checks:
            try:
                result = check()
                if not result:
                    all_passed = False
            except Exception as e:
                self.print_error(f"Check failed with exception: {e}")
                all_passed = False

        self.generate_report()
        return all_passed


def main():
    parser = argparse.ArgumentParser(description='ESP Deployment System Verification')
    parser.add_argument('--detailed', action='store_true',
                       help='Show detailed output')
    parser.add_argument('--fix-issues', action='store_true',
                       help='Attempt to fix issues automatically')

    args = parser.parse_args()

    verifier = SystemVerifier(detailed=args.detailed, fix_issues=args.fix_issues)

    try:
        success = verifier.run_verification()
        return 0 if success else 1
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Verification interrupted by user{Colors.END}")
        return 130
    except Exception as e:
        print(f"\n{Colors.RED}Verification failed with error: {e}{Colors.END}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
