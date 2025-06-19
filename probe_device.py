#!/usr/bin/env python3
"""
Device Probe Script for CH340/CH341 USB-to-Serial Connection
This script attempts to identify and communicate with the connected device
"""

import serial
import time
import sys

def probe_device(port='/dev/ttyUSB0', baudrates=[115200, 9600, 57600, 38400, 19200]):
    """
    Probe the connected device with different baudrates and commands
    """
    print(f"Probing device on {port}...")

    for baudrate in baudrates:
        print(f"\n--- Trying baudrate: {baudrate} ---")
        try:
            # Open serial connection
            ser = serial.Serial(port, baudrate, timeout=2)
            time.sleep(0.5)  # Allow connection to stabilize

            # Clear any existing data
            ser.reset_input_buffer()
            ser.reset_output_buffer()

            # Test 1: Check for existing data/boot messages
            print("Checking for existing data...")
            existing_data = ser.read_all()
            if existing_data:
                print(f"Found data: {existing_data.decode('utf-8', errors='ignore')}")

            # Test 2: Try AT commands (ESP8266/ESP32)
            print("Testing AT commands...")
            ser.write(b'AT\r\n')
            time.sleep(1)
            response = ser.read_all()
            if response:
                decoded = response.decode('utf-8', errors='ignore')
                print(f"AT response: {decoded}")
                if 'OK' in decoded:
                    print("✓ ESP module detected!")
                    probe_esp_module(ser)
                    ser.close()
                    return 'ESP'

            # Test 3: Try Arduino/generic commands
            print("Testing Arduino commands...")
            ser.write(b'?\r\n')
            time.sleep(1)
            response = ser.read_all()
            if response:
                print(f"? response: {response.decode('utf-8', errors='ignore')}")

            # Test 4: Try Python REPL (MicroPython)
            print("Testing MicroPython REPL...")
            ser.write(b'\x03\x03')  # Ctrl+C twice
            time.sleep(0.5)
            ser.write(b'\r\n')
            time.sleep(0.5)
            response = ser.read_all()
            if response:
                decoded = response.decode('utf-8', errors='ignore')
                print(f"MicroPython test: {decoded}")
                if '>>>' in decoded or 'MicroPython' in decoded:
                    print("✓ MicroPython detected!")
                    probe_micropython(ser)
                    ser.close()
                    return 'MicroPython'

            # Test 5: Try reset/boot detection
            print("Attempting reset...")
            ser.write(b'AT+RST\r\n')
            time.sleep(3)
            boot_data = ser.read_all()
            if boot_data:
                decoded = boot_data.decode('utf-8', errors='ignore')
                print(f"Boot data: {decoded}")
                if 'ESP' in decoded or 'ready' in decoded:
                    print("✓ ESP module detected via reset!")
                    ser.close()
                    return 'ESP'

            ser.close()

        except serial.SerialException as e:
            print(f"Serial error at {baudrate}: {e}")
        except Exception as e:
            print(f"Error at {baudrate}: {e}")

    print("\nNo responsive device detected. Device might be:")
    print("1. Not powered/connected properly")
    print("2. Running custom firmware")
    print("3. In boot/flash mode")
    print("4. Using different baudrate")
    return 'Unknown'

def probe_esp_module(ser):
    """Probe ESP module capabilities"""
    print("\n=== ESP Module Probe ===")

    # Get version
    ser.write(b'AT+GMR\r\n')
    time.sleep(1)
    version = ser.read_all().decode('utf-8', errors='ignore')
    print(f"Version: {version}")

    # Check WiFi status
    ser.write(b'AT+CWMODE?\r\n')
    time.sleep(1)
    mode = ser.read_all().decode('utf-8', errors='ignore')
    print(f"WiFi Mode: {mode}")

    # List available WiFi networks
    ser.write(b'AT+CWLAP\r\n')
    time.sleep(5)
    networks = ser.read_all().decode('utf-8', errors='ignore')
    print(f"Available Networks: {networks}")

def probe_micropython(ser):
    """Probe MicroPython capabilities"""
    print("\n=== MicroPython Probe ===")

    # Get system info
    ser.write(b'import sys; print(sys.implementation)\r\n')
    time.sleep(1)
    impl = ser.read_all().decode('utf-8', errors='ignore')
    print(f"Implementation: {impl}")

    # Check for network capabilities
    ser.write(b'import network; print(dir(network))\r\n')
    time.sleep(1)
    network_info = ser.read_all().decode('utf-8', errors='ignore')
    print(f"Network capabilities: {network_info}")

def main():
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        port = '/dev/ttyUSB0'

    print("CH340/CH341 Device Probe")
    print("========================")

    device_type = probe_device(port)

    print(f"\n=== Results ===")
    print(f"Device type: {device_type}")

    if device_type == 'ESP':
        print("\nNext steps for ESP module:")
        print("1. Connect to WiFi using AT commands")
        print("2. Set up web server")
        print("3. Configure HTTP endpoints")
    elif device_type == 'MicroPython':
        print("\nNext steps for MicroPython:")
        print("1. Upload web server code")
        print("2. Configure WiFi connection")
        print("3. Set up HTTP server")
    else:
        print("\nTroubleshooting:")
        print("1. Check physical connections")
        print("2. Verify power supply")
        print("3. Try different baudrates")
        print("4. Check if device is in programming mode")

if __name__ == "__main__":
    main()
