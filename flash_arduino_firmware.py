#!/usr/bin/env python3
"""
Arduino Firmware Flashing Tool for ESP Modules
==============================================
This script automates the process of flashing Arduino firmware to ESP8266/ESP32
modules connected via CH340/CH341 USB-to-serial converters.

Features:
- Auto-detect ESP module type
- Configure WiFi credentials
- Flash appropriate firmware
- Verify upload success
- Post-flash testing

Usage:
    python3 flash_arduino_firmware.py
    python3 flash_arduino_firmware.py --port /dev/ttyUSB0 --wifi-ssid "MyWiFi" --wifi-password "MyPass"
    python3 flash_arduino_firmware.py --esp32 --compile-only
"""

import os
import sys
import subprocess
import time
import serial
import argparse
import shutil
import tempfile
import json
import re
from pathlib import Path
from typing import Optional, Dict, Tuple

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
    END = '\033[0m'

class ArduinoFlasher:
    def __init__(self, port='/dev/ttyUSB0', verbose=False):
        self.port = port
        self.verbose = verbose
        self.script_dir = Path(__file__).parent
        self.firmware_dir = self.script_dir / "arduino_firmware"
        self.temp_dir = None

        # Arduino CLI configuration
        self.arduino_cli = str(self.script_dir / "bin" / "arduino-cli")
        self.arduino_config = str(self.script_dir / "arduino-cli.yaml")
        self.esp_type = None
        self.board_fqbn = None

        # Firmware configuration
        self.wifi_ssid = ""
        self.wifi_password = ""
        self.device_hostname = "esp-webserver"

    def log(self, message: str, color: str = Colors.WHITE):
        """Log message with color"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"{color}[{timestamp}] {message}{Colors.END}")

    def log_success(self, message: str):
        """Log success message"""
        self.log(f"✓ {message}", Colors.GREEN)

    def log_error(self, message: str):
        """Log error message"""
        self.log(f"✗ {message}", Colors.RED)

    def log_warning(self, message: str):
        """Log warning message"""
        self.log(f"⚠ {message}", Colors.YELLOW)

    def log_info(self, message: str):
        """Log info message"""
        self.log(f"ℹ {message}", Colors.CYAN)

    def verbose_log(self, message: str):
        """Log verbose message"""
        if self.verbose:
            self.log(f"DEBUG: {message}", Colors.MAGENTA)

    def run_command(self, command: str, capture_output: bool = True, timeout: int = 60) -> Tuple[bool, str]:
        """Run shell command and return success status and output"""
        try:
            self.verbose_log(f"Running: {command}")

            if capture_output:
                result = subprocess.run(
                    command, shell=True, capture_output=True, text=True, timeout=timeout
                )
                output = result.stdout + result.stderr
                success = result.returncode == 0
            else:
                result = subprocess.run(command, shell=True, timeout=timeout)
                output = ""
                success = result.returncode == 0

            if self.verbose and output:
                self.verbose_log(f"Output: {output}")

            return success, output

        except subprocess.TimeoutExpired:
            self.log_error(f"Command timed out after {timeout} seconds")
            return False, "Command timed out"
        except Exception as e:
            self.log_error(f"Command failed: {e}")
            return False, str(e)

    def check_dependencies(self) -> bool:
        """Check if required dependencies are installed"""
        self.log("Checking dependencies...", Colors.BLUE)

        # Check Arduino CLI
        success, output = self.run_command("arduino-cli version")
        if success:
            self.log_success("Arduino CLI found")
            # Use local arduino-cli if global not found
            local_cli = self.script_dir / "bin" / "arduino-cli"
            if local_cli.exists():
                self.arduino_cli = str(local_cli)
        else:
            self.log_warning("Arduino CLI not found, will attempt to install")
            if not self.install_arduino_cli():
                return False

        # Check Python serial library
        try:
            import serial
            self.log_success("PySerial library available")
        except ImportError:
            self.log_error("PySerial not found. Install with: pip3 install pyserial")
            return False

        # Check if port exists
        if not os.path.exists(self.port):
            self.log_error(f"Serial port {self.port} not found")
            return False

        self.log_success("All dependencies satisfied")
        return True

    def install_arduino_cli(self) -> bool:
        """Install Arduino CLI"""
        self.log_info("Installing Arduino CLI...")

        # Download and install Arduino CLI
        install_script = """
        curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
        """

        success, output = self.run_command(install_script, timeout=120)
        if success:
            # Try to find arduino-cli in common locations
            common_paths = [
                os.path.expanduser("~/bin/arduino-cli"),
                "/usr/local/bin/arduino-cli",
                "./bin/arduino-cli"
            ]

            for path in common_paths:
                if os.path.exists(path):
                    self.arduino_cli = path
                    self.log_success(f"Arduino CLI installed at {path}")
                    return True

            self.log_error("Arduino CLI installation failed")
            return False
        else:
            self.log_error("Failed to install Arduino CLI")
            return False

    def detect_esp_module(self) -> bool:
        """Detect ESP module type"""
        self.log("Detecting ESP module type...", Colors.BLUE)

        try:
            # Try to communicate with module
            ser = serial.Serial(self.port, 115200, timeout=2)
            time.sleep(1)

            # Send reset command and check response
            ser.write(b'\x03\x03')  # Ctrl+C
            time.sleep(0.5)
            ser.reset_input_buffer()

            # Try to get chip info using esptool
            success, output = self.run_command(f"python3 -m esptool --port {self.port} chip_id")

            if "ESP8266" in output or "esp8266" in output:
                self.esp_type = "ESP8266"
                self.board_fqbn = "esp8266:esp8266:nodemcuv2"
                self.log_success("ESP8266 detected")
            elif "ESP32" in output or "esp32" in output:
                self.esp_type = "ESP32"
                self.board_fqbn = "esp32:esp32:esp32"
                self.log_success("ESP32 detected")
            else:
                # Fallback: try AT commands
                ser.write(b'AT\r\n')
                time.sleep(1)
                response = ser.read_all().decode('utf-8', errors='ignore')

                if 'OK' in response:
                    # Default to ESP8266 for AT firmware
                    self.esp_type = "ESP8266"
                    self.board_fqbn = "esp8266:esp8266:nodemcuv2"
                    self.log_warning("ESP type unclear, defaulting to ESP8266")
                else:
                    self.log_error("Could not detect ESP module type")
                    ser.close()
                    return False

            ser.close()
            return True

        except Exception as e:
            self.log_error(f"Error detecting ESP module: {e}")
            return False

    def setup_arduino_environment(self) -> bool:
        """Setup Arduino CLI environment"""
        self.log("Setting up Arduino environment...", Colors.BLUE)

        # Use existing config file if available
        config_file = self.script_dir / "arduino-cli.yaml"
        if config_file.exists():
            self.log_success("Using existing Arduino CLI config")
        else:
            # Initialize Arduino CLI config
            success, output = self.run_command(f"{self.arduino_cli} config init --dest-dir {self.script_dir}")
            if not success:
                self.log_warning("Config init failed, continuing anyway")

        # Update core index
        self.log_info("Updating Arduino core index...")
        success, output = self.run_command(f"{self.arduino_cli} --config-file {self.arduino_config} core update-index")
        if not success:
            self.log_error("Failed to update core index")
            return False

        # Install appropriate board package
        if self.esp_type == "ESP8266":
            self.log_info("Installing ESP8266 board package...")
            success, output = self.run_command(
                f"{self.arduino_cli} --config-file {self.arduino_config} core install esp8266:esp8266", timeout=300
            )
        elif self.esp_type == "ESP32":
            self.log_info("Installing ESP32 board package...")
            success, output = self.run_command(
                f"{self.arduino_cli} --config-file {self.arduino_config} core install esp32:esp32", timeout=300
            )
        else:
            self.log_error("Unknown ESP type")
            return False

        if not success:
            self.log_error(f"Failed to install {self.esp_type} board package")
            return False

        self.log_success(f"{self.esp_type} board package installed")

        # Install required libraries
        self.log_info("Installing required libraries...")
        libraries = [
            "ArduinoJson"
        ]

        # Simple firmware doesn't need async libraries
        self.log_info("Using simplified firmware - minimal libraries required")

        for lib in libraries:
            self.log_info(f"Installing {lib}...")
            success, output = self.run_command(
                f"{self.arduino_cli} --config-file {self.arduino_config} lib install '{lib}'", timeout=120
            )
            if success:
                self.log_success(f"{lib} installed")
            else:
                self.log_warning(f"Failed to install {lib}, may need manual installation")

        return True

    def configure_wifi_credentials(self, ssid: str = None, password: str = None) -> bool:
        """Configure WiFi credentials interactively or from parameters"""
        self.log("Configuring WiFi credentials...", Colors.BLUE)

        if ssid and password:
            self.wifi_ssid = ssid
            self.wifi_password = password
            self.log_success(f"Using provided WiFi credentials for: {ssid}")
            return True

        # Interactive configuration
        print("\n" + "="*50)
        print("WiFi Configuration")
        print("="*50)

        while not self.wifi_ssid:
            self.wifi_ssid = input("Enter WiFi SSID: ").strip()
            if not self.wifi_ssid:
                self.log_error("SSID cannot be empty!")

        while not self.wifi_password:
            self.wifi_password = input("Enter WiFi Password: ").strip()
            if not self.wifi_password:
                self.log_error("Password cannot be empty!")

        # Optional hostname configuration
        hostname_input = input(f"Enter device hostname [{self.device_hostname}]: ").strip()
        if hostname_input:
            self.device_hostname = hostname_input

        print("\nWiFi Configuration:")
        print(f"SSID: {self.wifi_ssid}")
        print(f"Password: {'*' * len(self.wifi_password)}")
        print(f"Hostname: {self.device_hostname}")

        confirm = input("\nProceed with these settings? (y/n): ").lower()
        if confirm != 'y':
            self.log_info("WiFi configuration cancelled")
            return False

        return True

    def prepare_firmware(self) -> bool:
        """Prepare firmware with WiFi credentials"""
        self.log("Preparing firmware...", Colors.BLUE)

        # Determine source firmware file
        if self.esp_type == "ESP8266":
            source_file = self.firmware_dir / "ESP8266_Simple_WebServer.ino"
        else:
            source_file = self.firmware_dir / "ESP32_WebServer.ino"

        if not source_file.exists():
            self.log_error(f"Firmware file not found: {source_file}")
            return False

        # Create temporary directory for modified firmware
        self.temp_dir = Path(tempfile.mkdtemp(prefix="esp_firmware_"))
        temp_firmware_dir = self.temp_dir / f"{self.esp_type}_Simple_WebServer"
        temp_firmware_dir.mkdir(parents=True, exist_ok=True)

        temp_firmware_file = temp_firmware_dir / f"{self.esp_type}_Simple_WebServer.ino"

        # Read original firmware
        with open(source_file, 'r') as f:
            firmware_content = f.read()

        # Replace WiFi credentials
        firmware_content = firmware_content.replace(
            'const char* ssid = "YOUR_WIFI_SSID";',
            f'const char* ssid = "{self.wifi_ssid}";'
        )
        firmware_content = firmware_content.replace(
            'const char* password = "YOUR_WIFI_PASSWORD";',
            f'const char* password = "{self.wifi_password}";'
        )

        # Replace hostname
        firmware_content = firmware_content.replace(
            'const char* hostname = "esp8266-webserver";',
            f'const char* hostname = "{self.device_hostname}";'
        )
        firmware_content = firmware_content.replace(
            'const char* hostname = "esp32-webserver";',
            f'const char* hostname = "{self.device_hostname}";'
        )

        # Write modified firmware
        with open(temp_firmware_file, 'w') as f:
            f.write(firmware_content)

        self.log_success(f"Firmware prepared in {temp_firmware_dir}")
        return True

    def compile_firmware(self) -> bool:
        """Compile the firmware"""
        self.log("Compiling firmware...", Colors.BLUE)

        firmware_path = self.temp_dir / f"{self.esp_type}_Simple_WebServer"

        # Compile command
        compile_cmd = f"{self.arduino_cli} --config-file {self.arduino_config} compile --fqbn {self.board_fqbn} {firmware_path}"

        self.log_info("Compiling... (this may take a few minutes)")
        success, output = self.run_command(compile_cmd, timeout=300)

        if success:
            self.log_success("Firmware compiled successfully")
            return True
        else:
            self.log_error("Firmware compilation failed")
            self.log_error(f"Error: {output}")
            return False

    def flash_firmware(self) -> bool:
        """Flash firmware to ESP module"""
        self.log("Flashing firmware to ESP module...", Colors.BLUE)

        firmware_path = self.temp_dir / f"{self.esp_type}_Simple_WebServer"

        # Upload command
        upload_cmd = f"{self.arduino_cli} --config-file {self.arduino_config} upload --port {self.port} --fqbn {self.board_fqbn} {firmware_path}"

        self.log_info("Flashing... (this may take a minute)")
        success, output = self.run_command(upload_cmd, timeout=120)

        if success:
            self.log_success("Firmware flashed successfully")
            return True
        else:
            self.log_error("Firmware flashing failed")
            self.log_error(f"Error: {output}")
            return False

    def verify_flash(self) -> bool:
        """Verify that firmware was flashed correctly"""
        self.log("Verifying firmware...", Colors.BLUE)

        # Wait for ESP to boot up
        self.log_info("Waiting for ESP to boot...")
        time.sleep(5)

        try:
            # Connect to serial port and check for boot messages
            ser = serial.Serial(self.port, 115200, timeout=5)
            time.sleep(2)

            # Clear buffer
            ser.reset_input_buffer()

            # Read boot messages
            boot_data = ""
            start_time = time.time()

            while time.time() - start_time < 10:  # Wait up to 10 seconds
                if ser.in_waiting > 0:
                    chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                    boot_data += chunk

                    # Look for successful boot indicators
                    if "Web Server Starting" in boot_data or "HTTP server started" in boot_data:
                        self.log_success("ESP web server started successfully")

                        # Extract IP address if available
                        ip_match = re.search(r'IP address: (\d+\.\d+\.\d+\.\d+)', boot_data)
                        if ip_match:
                            ip_address = ip_match.group(1)
                            self.log_success(f"ESP connected to WiFi with IP: {ip_address}")
                            self.log_info(f"Web interface available at: http://{ip_address}")

                        ser.close()
                        return True

                time.sleep(0.1)

            ser.close()

            # If we get here, no clear success message was found
            if "ESP" in boot_data or "WiFi" in boot_data:
                self.log_warning("ESP appears to be running, but verification incomplete")
                self.verbose_log(f"Boot data: {boot_data}")
                return True
            else:
                self.log_error("No ESP boot messages detected")
                self.verbose_log(f"Received data: {boot_data}")
                return False

        except Exception as e:
            self.log_error(f"Verification failed: {e}")
            return False

    def cleanup(self):
        """Clean up temporary files"""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.verbose_log(f"Cleaned up temporary directory: {self.temp_dir}")

    def flash_process(self, wifi_ssid: str = None, wifi_password: str = None,
                     compile_only: bool = False, force_esp_type: str = None) -> bool:
        """Main flashing process"""

        print(f"{Colors.BOLD}{Colors.CYAN}")
        print("="*60)
        print("ESP Arduino Firmware Flashing Tool")
        print("="*60)
        print(f"{Colors.END}")

        try:
            # Check dependencies
            if not self.check_dependencies():
                return False

            # Override ESP type if specified
            if force_esp_type:
                if force_esp_type.upper() in ["ESP8266", "ESP32"]:
                    self.esp_type = force_esp_type.upper()
                    if self.esp_type == "ESP8266":
                        self.board_fqbn = "esp8266:esp8266:nodemcuv2"
                    else:
                        self.board_fqbn = "esp32:esp32:esp32"
                    self.log_info(f"Using forced ESP type: {self.esp_type}")
                else:
                    self.log_error("Invalid ESP type. Use ESP8266 or ESP32")
                    return False
            else:
                # Detect ESP module
                if not self.detect_esp_module():
                    return False

            # Setup Arduino environment
            if not self.setup_arduino_environment():
                return False

            # Configure WiFi
            if not self.configure_wifi_credentials(wifi_ssid, wifi_password):
                return False

            # Prepare firmware
            if not self.prepare_firmware():
                return False

            # Compile firmware
            if not self.compile_firmware():
                return False

            if compile_only:
                self.log_success("Compilation completed successfully (compile-only mode)")
                return True

            # Flash firmware
            if not self.flash_firmware():
                return False

            # Verify flash
            if not self.verify_flash():
                self.log_warning("Verification incomplete, but flash may have succeeded")
                self.log_info("Check serial monitor for boot messages")

            # Success summary
            print(f"\n{Colors.GREEN}{Colors.BOLD}")
            print("="*60)
            print("🎉 FIRMWARE FLASHING COMPLETED SUCCESSFULLY!")
            print("="*60)
            print(f"{Colors.END}")

            print(f"{Colors.CYAN}")
            print("Next steps:")
            print("1. Open Serial Monitor (115200 baud) to see boot messages")
            print("2. Note the IP address assigned to your ESP")
            print("3. Open web browser and navigate to the IP address")
            print("4. Enjoy your ESP web server with GPIO control!")
            print(f"{Colors.END}")

            return True

        except KeyboardInterrupt:
            self.log_warning("Process interrupted by user")
            return False
        except Exception as e:
            self.log_error(f"Unexpected error: {e}")
            return False
        finally:
            self.cleanup()

def main():
    parser = argparse.ArgumentParser(description='Flash Arduino firmware to ESP modules')
    parser.add_argument('--port', default='/dev/ttyUSB0', help='Serial port')
    parser.add_argument('--wifi-ssid', help='WiFi SSID')
    parser.add_argument('--wifi-password', help='WiFi password')
    parser.add_argument('--hostname', help='Device hostname')
    parser.add_argument('--esp-type', choices=['ESP8266', 'ESP32'], help='Force ESP type')
    parser.add_argument('--compile-only', action='store_true', help='Only compile, do not flash')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()

    flasher = ArduinoFlasher(args.port, args.verbose)

    if args.hostname:
        flasher.device_hostname = args.hostname

    try:
        success = flasher.flash_process(
            wifi_ssid=args.wifi_ssid,
            wifi_password=args.wifi_password,
            compile_only=args.compile_only,
            force_esp_type=args.esp_type
        )
        return 0 if success else 1
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Flashing interrupted by user{Colors.END}")
        return 130
    except Exception as e:
        print(f"\n{Colors.RED}Flashing failed with error: {e}{Colors.END}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
